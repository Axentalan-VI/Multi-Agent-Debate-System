"""LangGraph wiring: frame the motion, loop through the speaking schedule, then judge."""
import random

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph import END, START, StateGraph

from debate.agents import (
    debater_messages,
    make_debater_llm,
    make_judge,
    make_moderator,
    moderator_messages,
    run_judge,
)
from debate.config import DebateConfig
from debate.schemas import Side
from debate.state import DebateState, Phase, Turn


def build_schedule(first_speaker: Side, rounds: int) -> list[tuple[Side, Phase, int]]:
    """Openings, `rounds` rebuttal rounds, then closings; the coin-flip winner leads every stage."""
    second: Side = "con" if first_speaker == "pro" else "pro"
    order = (first_speaker, second)
    schedule: list[tuple[Side, Phase, int]] = [(side, "opening", 0) for side in order]
    for rnd in range(1, rounds + 1):
        schedule += [(side, "rebuttal", rnd) for side in order]
    schedule += [(side, "closing", rounds + 1) for side in order]
    return schedule


def build_graph(
    cfg: DebateConfig,
    *,
    moderator: Runnable | None = None,
    debater_llm: BaseChatModel | None = None,
    judge: Runnable | None = None,
):
    """Compile the debate graph. Pass fakes for any agent to run without the OpenAI API."""
    moderator = moderator or make_moderator(cfg)
    debater_llm = debater_llm or make_debater_llm(cfg)
    judge = judge or make_judge(cfg)
    rng = random.Random(cfg.seed)

    def frame_motion(state: DebateState) -> dict:
        framing = moderator.invoke(moderator_messages(state["topic"]))
        if framing.rejected:
            return {"framing": framing, "schedule": []}
        first: Side = rng.choice(["pro", "con"])
        return {"framing": framing, "first_speaker": first, "schedule": build_schedule(first, cfg.rounds)}

    def speak(state: DebateState) -> dict:
        (side, phase, rnd), *remaining = state["schedule"]
        reply = debater_llm.invoke(debater_messages(state, side, phase, rnd, cfg))
        turn = Turn(side=side, phase=phase, round=rnd, content=reply.text.strip())
        return {"schedule": remaining, "transcript": [turn]}

    def adjudicate(state: DebateState) -> dict:
        return {"result": run_judge(judge, state, cfg, rng)}

    builder = StateGraph(DebateState)
    builder.add_node("frame_motion", frame_motion)
    builder.add_node("speak", speak)
    builder.add_node("judge", adjudicate)
    builder.add_edge(START, "frame_motion")
    builder.add_conditional_edges(
        "frame_motion", lambda state: END if state["framing"].rejected else "speak", ["speak", END]
    )
    builder.add_conditional_edges(
        "speak", lambda state: "speak" if state["schedule"] else "judge", ["speak", "judge"]
    )
    builder.add_edge("judge", END)
    return builder.compile()


def run_config(cfg: DebateConfig) -> RunnableConfig:
    # One graph step per speech plus framing and judging; the default limit of 25 is too low for long debates.
    return {"recursion_limit": 2 * (cfg.rounds + 2) + 10}
