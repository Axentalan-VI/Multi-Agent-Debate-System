# Multi-Agent Debate System

Two AI debaters argue any topic from opposite sides, and an impartial AI judge declares the winner.

Built with **LangGraph** (LangChain). Debaters and moderator run on **GPT-4o-mini**, the judge on **GPT-4o**, through OpenAI or Azure OpenAI.

## How it works

1. **Moderator** turns your topic into a debatable motion and flips a coin for speaking order.
2. **Debaters** give opening statements, rebuttal rounds, and closing statements. Each one sees its own speeches as its turns and the opponent's as the other side of the conversation.
3. **Judge** scores both sides on argument strength, evidence and logic, rebuttal effectiveness, and clarity, then picks a winner. Safeguards:
   - It judges twice with the A/B labels swapped. If the runs disagree, the combined scores decide.
   - Every decisive moment must quote the transcript, and each quote is checked in code.
   - Vague appeals such as "studies show" are detected in code and must be listed as unsupported claims. Citations are treated as unverified.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

In `.env`, set an endpoint and key for each model. For Azure OpenAI, paste the deployment URL: the deployment name and `api-version` are read from it. Leave an endpoint empty to use api.openai.com.

## Run

```powershell
.\.venv\Scripts\python main.py "Remote work is better than office work" --rounds 2
```

| Option | Default | Meaning |
|---|---|---|
| `--rounds` | 2 | Rebuttal rounds |
| `--word-limit` | 250 | Words per speech |
| `--single-judge` | off | Skip the label-swapped second judge run |
| `--seed` | random | Seed for the speaking-order coin flip |
| `--out` | `transcripts/` | Where Markdown and JSON transcripts are saved |

## Tests

```powershell
.\.venv\Scripts\python -m pytest
```

The tests use fake models and make no API calls.

## Layout

```
main.py             CLI entry point
debate/
  config.py         Per-model endpoints and keys, debate settings
  graph.py          LangGraph wiring: frame motion, speaking loop, judge
  agents.py         Agent factories, message builders, judge reconciliation, quote and evidence checks
  prompts.py        Moderator, debater and judge prompts
  schemas.py        Structured outputs (motion, scorecard, verdict)
  state.py          Graph state
  render.py         Terminal output and transcript export
tests/
```

## Known limitations

- The vague-evidence detector matches common phrasings, not every one.
- The judge cannot verify citations; debaters are steered toward reasoning instead.
- The word limit is enforced by the prompt, so speeches can run slightly over.
