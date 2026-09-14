"""Structured outputs for the moderator and judge, plus the reconciled judge result."""
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

Side = Literal["pro", "con"]
Label = Literal["A", "B"]

CRITERIA = ("argument_strength", "evidence_and_logic", "rebuttal_effectiveness", "clarity_persuasion")


def _clamp_score(value: int) -> int:
    return max(1, min(10, value))


# Range is described rather than constrained so the schema stays valid for OpenAI strict mode.
Score = Annotated[
    int,
    Field(description="Integer from 1 (very poor) to 10 (exceptional)."),
    AfterValidator(_clamp_score),
]


class MotionFraming(BaseModel):
    rejected: bool = Field(
        description="True only if no responsible version of the topic can be debated. Prefer reframing over rejecting."
    )
    rejection_reason: str = Field(description="Why the topic was rejected. Empty string if not rejected.")
    motion: str = Field(
        description="One clear, balanced, debatable motion phrased as 'This house believes that ...'. Empty string if rejected."
    )
    pro_position: str = Field(description="One sentence describing what the side FOR the motion must argue.")
    con_position: str = Field(description="One sentence describing what the side AGAINST the motion must argue.")


class DecisiveMoment(BaseModel):
    speech: str = Field(
        description="The speech the quote comes from, as titled in the transcript, e.g. 'Debater A (FOR): Rebuttal 1'."
    )
    quote: str = Field(description="A short excerpt (under 30 words) copied verbatim from that speech.")
    analysis: str = Field(description="Why this moment mattered, based only on what the transcript actually says.")


class Scorecard(BaseModel):
    # Issues come before scores so the scores reflect them.
    unsupported_claims: list[str] = Field(
        description=(
            "Verbatim quotes of claims resting on unverified authority: vague appeals ('studies show ...', "
            "'experts agree ...') and specific statistics or studies that are not common knowledge. Empty list if none."
        )
    )
    fallacies: list[str] = Field(
        description="Logical fallacies and dropped arguments (opponent points never answered). Empty list if none."
    )
    argument_strength: Score
    evidence_and_logic: Score
    rebuttal_effectiveness: Score
    clarity_persuasion: Score

    @property
    def total(self) -> int:
        return sum(getattr(self, criterion) for criterion in CRITERIA)


class Verdict(BaseModel):
    # Field order matters: evidence first, then scores, then reasoning, and only then the winner.
    decisive_moments: list[DecisiveMoment] = Field(
        description="The 2-4 moments that most influenced the decision, each grounded in a verbatim quote."
    )
    debater_a: Scorecard
    debater_b: Scorecard
    rationale: str = Field(description="Reasoned explanation of the decision, written before choosing the winner.")
    winner: Label = Field(description="The debater who won. Ties are not allowed.")


class JudgeRun(BaseModel):
    label_map: dict[Label, Side]
    verdict: Verdict
    grounded: list[bool]  # per decisive moment: was its quote found in the transcript?

    @property
    def winner(self) -> Side:
        return self.label_map[self.verdict.winner]

    def scorecard(self, side: Side) -> Scorecard:
        return self.verdict.debater_a if self.label_map["A"] == side else self.verdict.debater_b


class JudgeResult(BaseModel):
    winner: Side
    method: Literal["single", "unanimous", "score_aggregate", "tiebreak_run"]
    runs: list[JudgeRun]

    def average_scores(self, side: Side) -> dict[str, float]:
        return {
            criterion: sum(getattr(run.scorecard(side), criterion) for run in self.runs) / len(self.runs)
            for criterion in CRITERIA
        }

    @property
    def deciding_run(self) -> JudgeRun:
        return next(run for run in self.runs if run.winner == self.winner)
