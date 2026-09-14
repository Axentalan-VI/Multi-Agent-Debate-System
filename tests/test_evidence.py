from debate.agents import judge_messages, vague_evidence_claims
from debate.state import Turn

TRANSCRIPT = [
    Turn(
        side="pro",
        phase="opening",
        round=0,
        content="Screens matter. Yet studies show that heavy users feel isolated. Research by Twenge et al. (2018) indicates a decline.",
    ),
    Turn(side="con", phase="rebuttal", round=1, content="Experts agree this is overstated! Teens build real friendships online."),
]


def test_vague_appeals_are_flagged_with_their_sentence():
    assert vague_evidence_claims(TRANSCRIPT) == {
        "pro": ["Yet studies show that heavy users feel isolated."],
        "con": ["Experts agree this is overstated!"],
    }


def test_auxiliaries_adverbs_and_other_evidential_verbs_are_caught():
    # Seen live: "Numerous studies have linked ..." slipped past the first version of the detector.
    speech = [
        Turn(
            side="pro",
            phase="opening",
            round=0,
            content=(
                "Numerous studies have linked social media usage to anxiety. "
                "Research consistently shows harm. "
                "In conclusion, the overwhelming evidence points to real damage."
            ),
        )
    ]
    assert len(vague_evidence_claims(speech)["pro"]) == 3


def test_named_sources_are_not_flagged():
    named = [
        Turn(
            side="pro",
            phase="opening",
            round=0,
            content=(
                "Research by Twenge et al. (2018) indicates a decline. "
                "Studies like those from Primack et al. (2017) show isolation. A 2017 RSPH survey found harm."
            ),
        )
    ]
    assert vague_evidence_claims(named) == {"pro": [], "con": []}


def test_judge_sees_flagged_claims_under_the_right_labels(framing):
    state = {"framing": framing, "transcript": TRANSCRIPT}

    text = judge_messages(state, {"A": "con", "B": "pro"})[-1].content

    assert 'Debater A:\n- "Experts agree this is overstated!"' in text
    assert 'Debater B:\n- "Yet studies show that heavy users feel isolated."' in text


def test_judge_is_told_when_nothing_was_flagged(debate_state):
    text = judge_messages(debate_state, {"A": "pro", "B": "con"})[-1].content

    assert "Debater A:\n- none\nDebater B:\n- none" in text
