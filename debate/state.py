"""Graph state shared by every node."""
import operator
from typing import Annotated, Literal, TypedDict

from debate.schemas import JudgeResult, MotionFraming, Side

Phase = Literal["opening", "rebuttal", "closing"]


class Turn(TypedDict):
    side: Side
    phase: Phase
    round: int
    content: str


class DebateState(TypedDict, total=False):
    topic: str
    framing: MotionFraming
    first_speaker: Side
    schedule: list[tuple[Side, Phase, int]]  # turns still to be spoken
    transcript: Annotated[list[Turn], operator.add]
    result: JudgeResult


def stance(side: Side) -> str:
    return "FOR" if side == "pro" else "AGAINST"


def turn_title(turn: Turn) -> str:
    if turn["phase"] == "rebuttal":
        return f"Rebuttal {turn['round']}"
    return f"{turn['phase'].capitalize()} statement"
