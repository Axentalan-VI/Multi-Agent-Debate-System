from debate.graph import build_schedule, run_config
from debate import DebateConfig


def test_first_speaker_leads_every_stage():
    assert build_schedule("con", rounds=2) == [
        ("con", "opening", 0),
        ("pro", "opening", 0),
        ("con", "rebuttal", 1),
        ("pro", "rebuttal", 1),
        ("con", "rebuttal", 2),
        ("pro", "rebuttal", 2),
        ("con", "closing", 3),
        ("pro", "closing", 3),
    ]


def test_zero_rounds_is_openings_and_closings_only():
    assert [phase for _, phase, _ in build_schedule("pro", rounds=0)] == ["opening", "opening", "closing", "closing"]


def test_recursion_limit_covers_every_step():
    cfg = DebateConfig(rounds=12)
    graph_steps = len(build_schedule("pro", cfg.rounds)) + 2  # speeches + framing + judging
    assert run_config(cfg)["recursion_limit"] > graph_steps
