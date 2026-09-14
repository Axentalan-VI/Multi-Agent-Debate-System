"""Run a debate from the command line.

    python main.py "Remote work is better than working in an office" --rounds 2
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from debate import DebateConfig, build_graph, render, run_config
from debate.state import stance

PROJECT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Two AI debaters argue a topic; an AI judge declares the winner.")
    parser.add_argument("topic", nargs="+", help="Topic or motion to debate.")
    parser.add_argument("--rounds", type=int, default=2, help="Number of rebuttal rounds (default: 2).")
    parser.add_argument("--word-limit", type=int, default=250, help="Word limit per speech (default: 250).")
    parser.add_argument(
        "--single-judge", action="store_true", help="Skip the label-swapped second judge run (cheaper, less robust)."
    )
    parser.add_argument("--seed", type=int, help="Seed for the speaking-order coin flip.")
    parser.add_argument("--out", default=str(PROJECT_DIR / "transcripts"), help="Directory for saved transcripts.")
    return parser.parse_args()


def status_message(schedule: list, cfg: DebateConfig) -> str:
    if schedule:
        side, phase, rnd = schedule[0]
        speech = f"rebuttal {rnd}" if phase == "rebuttal" else f"{phase} statement"
        return f"{stance(side)} is preparing the {speech}..."
    runs = "2 runs, labels swapped" if cfg.judge_consistency_runs else "1 run"
    return f"Judge ({cfg.judge_model.model}) is deliberating ({runs})..."


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env")
    args = parse_args()
    try:
        cfg = DebateConfig(
            rounds=args.rounds,
            word_limit=args.word_limit,
            judge_consistency_runs=not args.single_judge,
            seed=args.seed,
        )
    except ValueError as exc:
        render.console.print(f"[red]{exc}[/]")
        return 2

    models = (cfg.debater_model, cfg.moderator_model, cfg.judge_model)
    missing = sorted({model.api_key_env for model in models if not model.api_key})
    if missing:
        render.console.print(f"[red]Missing API key(s):[/] {', '.join(missing)}. Add them to .env (see .env.example).")
        return 1

    graph = build_graph(cfg)
    final: dict = {}
    with render.console.status("Moderator is framing the motion...") as status:
        for mode, chunk in graph.stream(
            {"topic": " ".join(args.topic)}, run_config(cfg), stream_mode=["updates", "values"]
        ):
            if mode == "values":
                final = chunk
                continue
            for node, update in chunk.items():
                if node == "frame_motion":
                    if update["framing"].rejected:
                        continue
                    render.print_framing(update["framing"], update["first_speaker"])
                elif node == "speak":
                    render.print_turn(update["transcript"][0])
                else:
                    continue
                status.update(status_message(update["schedule"], cfg))

    if final["framing"].rejected:
        render.print_rejection(final["framing"])
        return 1
    render.print_verdict(final["result"])
    path = render.save_transcript(final, cfg, Path(args.out))
    render.console.print(f"[dim]Transcript saved to {path}[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
