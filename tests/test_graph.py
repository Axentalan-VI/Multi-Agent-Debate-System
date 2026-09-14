from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

from debate import DebateConfig, build_graph, run_config
from debate.agents import debater_messages


def judge_favouring_pro(verdict) -> RunnableLambda:
    """A fake judge that always picks whichever label is arguing FOR the motion."""

    def judge(messages):
        pro_label = "A" if "Debater A argues FOR" in messages[-1].content else "B"
        return verdict(pro_label)

    return RunnableLambda(judge)


def test_full_debate_runs_without_api(framing, verdict):
    cfg = DebateConfig(rounds=1, seed=0)
    speeches = [f"speech {i}" for i in range(6)]
    graph = build_graph(
        cfg,
        moderator=RunnableLambda(lambda _: framing),
        debater_llm=FakeListChatModel(responses=speeches),
        judge=judge_favouring_pro(verdict),
    )

    final = graph.invoke({"topic": "car bans"}, run_config(cfg))

    transcript = final["transcript"]
    assert [turn["content"] for turn in transcript] == speeches
    assert [turn["phase"] for turn in transcript] == ["opening"] * 2 + ["rebuttal"] * 2 + ["closing"] * 2
    assert transcript[0]["side"] == final["first_speaker"]
    assert all(a["side"] != b["side"] for a, b in zip(transcript, transcript[1:]))
    assert final["result"].winner == "pro"
    assert final["result"].method == "unanimous"


def test_long_debate_stays_within_recursion_limit(framing, verdict):
    cfg = DebateConfig(rounds=12, seed=1)
    graph = build_graph(
        cfg,
        moderator=RunnableLambda(lambda _: framing),
        debater_llm=FakeListChatModel(responses=["speech"]),
        judge=judge_favouring_pro(verdict),
    )

    final = graph.invoke({"topic": "car bans"}, run_config(cfg))

    assert len(final["transcript"]) == 2 * (cfg.rounds + 2)


def test_rejected_topic_skips_debate_and_judge(framing):
    rejected = framing.model_copy(update={"rejected": True, "rejection_reason": "Not debatable.", "motion": ""})

    def no_judge(_):
        raise AssertionError("judge should not run for a rejected topic")

    cfg = DebateConfig(seed=0)
    graph = build_graph(
        cfg,
        moderator=RunnableLambda(lambda _: rejected),
        debater_llm=FakeListChatModel(responses=["speech"]),
        judge=RunnableLambda(no_judge),
    )

    final = graph.invoke({"topic": "something"}, run_config(cfg))

    assert final["framing"].rejected
    assert not final.get("transcript")
    assert "result" not in final


def test_each_debater_sees_own_speeches_as_ai_and_opponent_as_human(debate_state):
    cfg = DebateConfig()

    pro = debater_messages(debate_state, "pro", "rebuttal", 1, cfg)
    con = debater_messages(debate_state, "con", "rebuttal", 1, cfg)

    assert [type(m) for m in pro] == [SystemMessage, AIMessage, HumanMessage, HumanMessage]
    assert [type(m) for m in con] == [SystemMessage, HumanMessage, AIMessage, HumanMessage]
    assert "arguing FOR" in pro[0].content
    assert "arguing AGAINST" in con[0].content
    assert pro[-1].content.startswith("[Moderator] Deliver rebuttal 1")
