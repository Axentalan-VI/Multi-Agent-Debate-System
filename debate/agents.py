"""Agent factories, the message builders each agent uses, and judge reconciliation."""
import random
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from debate.config import DebateConfig, ModelSettings
from debate.prompts import DEBATER_SYSTEM, JUDGE_SYSTEM, JUDGE_USER, MODERATOR_SYSTEM, PHASE_INSTRUCTIONS
from debate.schemas import JudgeResult, JudgeRun, Label, MotionFraming, Side, Verdict
from debate.state import DebateState, Phase, Turn, stance, turn_title

LABEL_MAPS: list[dict[Label, Side]] = [{"A": "pro", "B": "con"}, {"A": "con", "B": "pro"}]


def _chat(settings: ModelSettings, temperature: float, **kwargs) -> BaseChatModel:
    # Each model has its own endpoint and key: <MODEL>_ENDPOINT and <MODEL>_API_KEY in .env.
    endpoint = settings.resolved_endpoint
    if endpoint.azure_endpoint:
        return AzureChatOpenAI(
            model=settings.model,
            azure_deployment=settings.model,
            azure_endpoint=endpoint.azure_endpoint,
            api_version=endpoint.api_version,
            api_key=settings.api_key,
            temperature=temperature,
            **kwargs,
        )
    return ChatOpenAI(
        model=settings.model,
        base_url=endpoint.base_url,
        api_key=settings.api_key,
        temperature=temperature,
        **kwargs,
    )


def make_moderator(cfg: DebateConfig) -> Runnable:
    llm = _chat(cfg.moderator_model, cfg.moderator_temperature)
    return llm.with_structured_output(MotionFraming, method="json_schema")


def make_debater_llm(cfg: DebateConfig) -> BaseChatModel:
    # The word limit is enforced by the prompt; max_tokens is only a safety net against runaway output.
    return _chat(cfg.debater_model, cfg.debater_temperature, max_tokens=cfg.word_limit * 2 + 100)


def make_judge(cfg: DebateConfig) -> Runnable:
    llm = _chat(cfg.judge_model, cfg.judge_temperature)
    return llm.with_structured_output(Verdict, method="json_schema")


def moderator_messages(topic: str) -> list[BaseMessage]:
    return [SystemMessage(MODERATOR_SYSTEM), HumanMessage(f"Topic: {topic}")]


def debater_messages(state: DebateState, side: Side, phase: Phase, rnd: int, cfg: DebateConfig) -> list[BaseMessage]:
    """Build the conversation from one debater's point of view.

    Its own speeches are AI messages and the opponent's are human messages, so each debater
    experiences the debate as a dialogue with its opponent.
    """
    framing = state["framing"]
    position = framing.pro_position if side == "pro" else framing.con_position
    messages: list[BaseMessage] = [
        SystemMessage(
            DEBATER_SYSTEM.format(
                stance=stance(side), motion=framing.motion, position=position, word_limit=cfg.word_limit
            )
        )
    ]
    for turn in state.get("transcript", []):
        if turn["side"] == side:
            messages.append(AIMessage(turn["content"]))
        else:
            messages.append(HumanMessage(f"[Opponent: {turn_title(turn)}]\n{turn['content']}"))
    instruction = PHASE_INSTRUCTIONS[phase].format(round=rnd, word_limit=cfg.word_limit)
    messages.append(HumanMessage(f"[Moderator] {instruction}"))
    return messages


# An unnamed subject followed by an evidential verb, optionally with an auxiliary and an adverb:
# "studies show", "numerous studies have linked", "research consistently shows", "the evidence points to".
# Named sources ("Research by Twenge et al. indicates") do not match.
_VAGUE_EVIDENCE = re.compile(
    r"\b(?:studies|research|researchers|experts|evidence|data|scientists|surveys|statistics)\s+"
    r"(?:(?:have|has|had)\s+)?(?:\w+ly\s+)?"
    r"(?:show|shows|showed|shown|suggest|suggests|suggested|indicate|indicates|indicated|"
    r"prove|proves|proved|proven|agree|agrees|find|finds|found|confirm|confirms|confirmed|"
    r"link|links|linked|tie|ties|tied|demonstrate|demonstrates|demonstrated|reveal|reveals|revealed|"
    r"point|points|pointed|warn|warns|warned)\b",
    re.IGNORECASE,
)


def vague_evidence_claims(transcript: list[Turn]) -> dict[Side, list[str]]:
    """Sentences, per side, that appeal to unnamed research. The judge was seen missing these on its own."""
    found: dict[Side, list[str]] = {"pro": [], "con": []}
    for turn in transcript:
        for sentence in re.split(r"(?<=[.!?])\s+", turn["content"]):
            if _VAGUE_EVIDENCE.search(sentence):
                found[turn["side"]].append(sentence.strip())
    return found


def judge_messages(state: DebateState, label_map: dict[Label, Side]) -> list[BaseMessage]:
    side_to_label = {side: label for label, side in label_map.items()}
    blocks = [
        f"### Debater {side_to_label[turn['side']]} ({stance(turn['side'])}): {turn_title(turn)}\n\n{turn['content']}"
        for turn in state["transcript"]
    ]
    flagged = vague_evidence_claims(state["transcript"])
    flagged_lines: list[str] = []
    for label in ("A", "B"):
        flagged_lines.append(f"Debater {label}:")
        flagged_lines += [f'- "{claim}"' for claim in flagged[label_map[label]]] or ["- none"]
    user = JUDGE_USER.format(
        motion=state["framing"].motion,
        a_stance=stance(label_map["A"]),
        b_stance=stance(label_map["B"]),
        transcript="\n\n".join(blocks),
        flagged="\n".join(flagged_lines),
    )
    return [SystemMessage(JUDGE_SYSTEM), HumanMessage(user)]


# Quote marks are dropped entirely: judges often swap " for ' when quoting text that itself contains quotes.
_TYPOGRAPHY = str.maketrans({"'": None, '"': None, "‘": None, "’": None, "“": None, "”": None, "–": "-", "—": "-"})


def _normalise(text: str) -> str:
    return " ".join(text.translate(_TYPOGRAPHY).lower().split())


def quote_in_transcript(quote: str, transcript: list[Turn]) -> bool:
    """True if the quote appears in a single speech, ignoring case, whitespace and quote marks.

    Ellipses are treated as elisions: every fragment around them must appear in that same speech.
    """
    fragments = [part.strip(" .,;:!?\"'") for part in re.split(r"\.\.\.|…", _normalise(quote))]
    fragments = [part for part in fragments if part]
    if not fragments:
        return False
    speeches = (_normalise(turn["content"]) for turn in transcript)
    return any(all(part in speech for part in fragments) for speech in speeches)


def _judge_once(judge: Runnable, state: DebateState, label_map: dict[Label, Side]) -> JudgeRun:
    verdict = judge.invoke(judge_messages(state, label_map))
    grounded = [quote_in_transcript(moment.quote, state["transcript"]) for moment in verdict.decisive_moments]
    return JudgeRun(label_map=label_map, verdict=verdict, grounded=grounded)


def run_judge(judge: Runnable, state: DebateState, cfg: DebateConfig, rng: random.Random) -> JudgeResult:
    """Judge the debate, optionally twice with A/B labels swapped to catch label bias.

    Agreement is final. On disagreement the combined rubric totals decide, and an exact
    score tie falls back to a third run with randomly assigned labels.
    """
    if not cfg.judge_consistency_runs:
        runs = [_judge_once(judge, state, rng.choice(LABEL_MAPS))]
        return JudgeResult(winner=runs[0].winner, method="single", runs=runs)

    runs = [_judge_once(judge, state, label_map) for label_map in LABEL_MAPS]
    if runs[0].winner == runs[1].winner:
        return JudgeResult(winner=runs[0].winner, method="unanimous", runs=runs)

    pro_total = sum(run.scorecard("pro").total for run in runs)
    con_total = sum(run.scorecard("con").total for run in runs)
    if pro_total != con_total:
        winner: Side = "pro" if pro_total > con_total else "con"
        return JudgeResult(winner=winner, method="score_aggregate", runs=runs)

    runs.append(_judge_once(judge, state, rng.choice(LABEL_MAPS)))
    return JudgeResult(winner=runs[2].winner, method="tiebreak_run", runs=runs)
