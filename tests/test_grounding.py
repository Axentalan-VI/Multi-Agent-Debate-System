import random

from langchain_core.runnables import RunnableLambda

from debate import DebateConfig
from debate.agents import quote_in_transcript, run_judge
from debate.state import Turn

TRANSCRIPT = [
    Turn(side="pro", phase="opening", round=0, content="Studies show teens\nsleep less. The algorithm’s pull is relentless."),
    Turn(side="con", phase="opening", round=0, content="Connection matters. Isolated teens find community online."),
]


def test_exact_quote_is_grounded():
    assert quote_in_transcript("Connection matters.", TRANSCRIPT)


def test_case_whitespace_and_typographic_quotes_are_ignored():
    assert quote_in_transcript('"studies show teens sleep less. The algorithm\'s pull"', TRANSCRIPT)


def test_nested_quote_marks_may_differ():
    # Seen live: the judge quoted "JAMA Psychiatry" as 'JAMA Psychiatry'.
    transcript = [Turn(side="pro", phase="opening", round=0, content='A study in "JAMA Psychiatry" (2019) found a link.')]
    assert quote_in_transcript("A study in 'JAMA Psychiatry' (2019) found a link.", transcript)


def test_ellipsis_fragments_must_come_from_the_same_speech():
    assert quote_in_transcript("Studies show teens ... pull is relentless", TRANSCRIPT)
    assert not quote_in_transcript("Studies show teens ... find community online", TRANSCRIPT)


def test_paraphrase_or_invented_quote_is_not_grounded():
    assert not quote_in_transcript("Social media is inherently addictive.", TRANSCRIPT)
    assert not quote_in_transcript("...", TRANSCRIPT)


def test_run_judge_records_grounding_per_moment(debate_state, verdict):
    judge = RunnableLambda(lambda _: verdict("A", quote="a point nobody made"))

    result = run_judge(judge, debate_state, DebateConfig(judge_consistency_runs=False), random.Random(0))

    assert result.runs[0].grounded == [False]
