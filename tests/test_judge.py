import random

from langchain_core.runnables import RunnableLambda

from debate import DebateConfig
from debate.agents import run_judge
from debate.schemas import Scorecard


def scripted_judge(*verdicts) -> RunnableLambda:
    """Returns the given verdicts in order. Run 1 labels pro as A; run 2 labels con as A."""
    remaining = iter(verdicts)
    return RunnableLambda(lambda _: next(remaining))


def test_agreement_across_label_swap_is_unanimous(debate_state, verdict):
    judge = scripted_judge(verdict("A"), verdict("B"))  # pro both times

    result = run_judge(judge, debate_state, DebateConfig(), random.Random(0))

    assert (result.winner, result.method, len(result.runs)) == ("pro", "unanimous", 2)


def test_label_biased_judge_falls_back_to_combined_scores(debate_state, verdict):
    # Always picks "A", but the scores favour con: pro 24 + 28 = 52, con 32 + 28 = 60.
    judge = scripted_judge(verdict("A", a=6, b=8), verdict("A", a=7, b=7))

    result = run_judge(judge, debate_state, DebateConfig(), random.Random(0))

    assert (result.winner, result.method) == ("con", "score_aggregate")


def test_disagreement_with_tied_scores_uses_third_run(debate_state, verdict):
    judge = scripted_judge(verdict("A"), verdict("A"), verdict("B"))

    result = run_judge(judge, debate_state, DebateConfig(), random.Random(0))

    assert result.method == "tiebreak_run"
    assert len(result.runs) == 3
    assert result.winner == result.runs[2].winner
    assert result.deciding_run.winner == result.winner


def test_single_judge_mode_makes_one_call(debate_state, verdict):
    result = run_judge(
        scripted_judge(verdict("B")), debate_state, DebateConfig(judge_consistency_runs=False), random.Random(0)
    )

    assert (result.method, len(result.runs)) == ("single", 1)


def test_scores_are_clamped_to_rubric_range():
    card = Scorecard(
        unsupported_claims=[],
        fallacies=[],
        argument_strength=14,
        evidence_and_logic=0,
        rebuttal_effectiveness=5,
        clarity_persuasion=10,
    )

    assert (card.argument_strength, card.evidence_and_logic) == (10, 1)
