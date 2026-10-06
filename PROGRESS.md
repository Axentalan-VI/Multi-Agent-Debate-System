# Progress

## Current status

Complete and working. LLM agents argue a motion across rebuttal rounds and are
judged twice with the side labels swapped, which cancels position bias. **32
tests pass.** Not a competition, so there is no score.

## Last session (2026-10-06)

- Added this file; the repo had no state files.

## Open issues

- The README carries one long example debate inline, which makes it hard to
  skim. The example is good; it belongs in `examples/` with a link.
- Nothing measures judge agreement across the two label orders. The swap is the
  central idea of the project, and whether it actually changes verdicts is
  unrecorded.

## Next steps (prioritized)

1. Run N motions twice each and report how often the swap flips the verdict.
   That number is the project's whole claim and it does not exist yet.
2. Move the long example out of the README.

## Decisions & rationale

- Each debate is judged twice with the sides swapped, because an LLM judge
  favours whichever argument it read second; swapping and averaging is the
  cheapest correction that does not need a second model.
