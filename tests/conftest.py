import pytest

from debate.schemas import DecisiveMoment, MotionFraming, Scorecard, Verdict
from debate.state import DebateState, Turn


def _make_verdict(winner: str, a: int = 7, b: int = 7, quote: str = "Cars choke our city centres.") -> Verdict:
    def card(score: int) -> Scorecard:
        return Scorecard(
            unsupported_claims=[],
            fallacies=[],
            argument_strength=score,
            evidence_and_logic=score,
            rebuttal_effectiveness=score,
            clarity_persuasion=score,
        )

    moment = DecisiveMoment(speech="Debater A (FOR): Opening statement", quote=quote, analysis="Set the terms.")
    return Verdict(decisive_moments=[moment], debater_a=card(a), debater_b=card(b), rationale="Reasoning.", winner=winner)


@pytest.fixture
def verdict():
    """Factory: verdict(winner_label, a_score, b_score)."""
    return _make_verdict


@pytest.fixture
def framing() -> MotionFraming:
    return MotionFraming(
        rejected=False,
        rejection_reason="",
        motion="This house believes that cities should ban private cars from downtown areas.",
        pro_position="Downtown car bans make cities better places to live and work.",
        con_position="Downtown car bans do more harm than good.",
    )


@pytest.fixture
def debate_state(framing) -> DebateState:
    return DebateState(
        topic="car bans",
        framing=framing,
        first_speaker="pro",
        transcript=[
            Turn(side="pro", phase="opening", round=0, content="Cars choke our city centres."),
            Turn(side="con", phase="opening", round=0, content="Bans hurt workers and small businesses."),
        ],
    )
