"""Terminal rendering with Rich, and transcript export to Markdown and JSON."""
import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from debate.config import DebateConfig
from debate.schemas import CRITERIA, JudgeResult, MotionFraming, Side
from debate.state import DebateState, Turn, stance, turn_title

console = Console()

COLORS: dict[Side, str] = {"pro": "green", "con": "red"}

METHOD_NOTES = {
    "single": "Single judge run.",
    "unanimous": "Both judge runs (A/B labels swapped) agreed.",
    "score_aggregate": "Judge runs disagreed after swapping labels; decided on combined rubric scores.",
    "tiebreak_run": "Judge runs disagreed and scores tied; decided by a third run.",
}


def _criterion_name(criterion: str) -> str:
    return criterion.replace("_", " ").capitalize()


def verdict_markdown(result: JudgeResult) -> str:
    run = result.deciding_run
    labels = f"_Debater A argued {stance(run.label_map['A'])}; Debater B argued {stance(run.label_map['B'])}._"
    lines = [labels, "", run.verdict.rationale, "", "**Decisive moments**", ""]
    for moment, grounded in zip(run.verdict.decisive_moments, run.grounded):
        warning = "" if grounded else " **(quote not found in transcript)**"
        lines.append(f'- {moment.speech}: "{moment.quote}"{warning} {moment.analysis}')
    for side in ("pro", "con"):
        card = run.scorecard(side)
        issues = [f'Unsupported claim: "{claim}"' for claim in card.unsupported_claims] + card.fallacies
        if issues:
            lines += ["", f"**Issues flagged ({stance(side)})**", ""] + [f"- {issue}" for issue in issues]
    return "\n".join(lines)


def print_framing(framing: MotionFraming, first_speaker: Side) -> None:
    body = (
        f"[bold]{escape(framing.motion)}[/]\n\n"
        f"[green]FOR:[/] {escape(framing.pro_position)}\n"
        f"[red]AGAINST:[/] {escape(framing.con_position)}\n\n"
        f"[dim]Coin flip: {stance(first_speaker)} speaks first.[/]"
    )
    console.print(Panel(body, title="Motion", border_style="cyan"))


def print_rejection(framing: MotionFraming) -> None:
    console.print(Panel(escape(framing.rejection_reason), title="Topic rejected by moderator", border_style="yellow"))


def print_turn(turn: Turn) -> None:
    color = COLORS[turn["side"]]
    console.print(
        Panel(
            Markdown(turn["content"]),
            title=f"[bold {color}]{stance(turn['side'])}[/]: {turn_title(turn)}",
            title_align="left",
            subtitle=f"[dim]{len(turn['content'].split())} words[/]",
            border_style=color,
        )
    )


def print_verdict(result: JudgeResult) -> None:
    pro, con = result.average_scores("pro"), result.average_scores("con")
    table = Table(title="Judge scorecard (average across runs)")
    table.add_column("Criterion")
    table.add_column("FOR", justify="right", style="green")
    table.add_column("AGAINST", justify="right", style="red")
    for criterion in CRITERIA:
        table.add_row(_criterion_name(criterion), f"{pro[criterion]:.1f}", f"{con[criterion]:.1f}")
    table.add_row("[bold]Total[/]", f"[bold]{sum(pro.values()):.1f}[/]", f"[bold]{sum(con.values()):.1f}[/]")
    console.print(table)

    color = COLORS[result.winner]
    console.print(
        Panel(
            Markdown(verdict_markdown(result)),
            title=f"[bold {color}]Winner: {stance(result.winner)} the motion[/]",
            border_style=color,
        )
    )
    # Printed below the panel rather than as its subtitle, which gets cut off on narrow terminals.
    console.print(f"[dim]{METHOD_NOTES[result.method]}[/]")


def save_transcript(state: DebateState, cfg: DebateConfig, out_dir: Path) -> Path:
    """Write the debate as Markdown (for reading) and JSON (for analysis). Returns the Markdown path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    framing, result = state["framing"], state["result"]
    slug = re.sub(r"[^a-z0-9]+", "-", framing.motion.lower()).strip("-")[:60]
    stem = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"

    pro, con = result.average_scores("pro"), result.average_scores("con")
    lines = [
        f"# {framing.motion}",
        "",
        f"- **FOR:** {framing.pro_position}",
        f"- **AGAINST:** {framing.con_position}",
        f"- **Debaters:** {cfg.debater_model.model} | **Judge:** {cfg.judge_model.model}",
        "",
    ]
    for turn in state["transcript"]:
        lines += [f"## {stance(turn['side'])}: {turn_title(turn)}", "", turn["content"], ""]
    lines += [
        f"## Verdict: {stance(result.winner)} wins",
        "",
        f"_{METHOD_NOTES[result.method]}_",
        "",
        "| Criterion | FOR | AGAINST |",
        "|---|---:|---:|",
    ]
    lines += [f"| {_criterion_name(c)} | {pro[c]:.1f} | {con[c]:.1f} |" for c in CRITERIA]
    lines += [f"| **Total** | **{sum(pro.values()):.1f}** | **{sum(con.values()):.1f}** |", "", verdict_markdown(result), ""]

    md_path = stem.with_suffix(".md")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    record = {
        "topic": state["topic"],
        "config": asdict(cfg),
        "framing": framing.model_dump(),
        "first_speaker": state["first_speaker"],
        "transcript": state["transcript"],
        "result": result.model_dump(),
    }
    stem.with_suffix(".json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return md_path
