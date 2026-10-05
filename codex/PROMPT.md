Build and verify this Deep Agents demo by following `codex/SPEC.md` exactly.
Read the spec in full before you run anything, and obey `AGENTS.md`.

If I put an "Operator context" block above this prompt, use it as my answers.
Otherwise ask only for the inputs SPEC section 1 requires and you cannot detect.

Show me the preflight table from SPEC section 2. For the two operator steps
(SPEC 4.3 and 4.4), hand me the script to run in my own terminal and tell me
to reply `done` without pasting output; skip a step whose checkpoint already
passes.

Run SPEC sections 4.5 to 4.8 from the repository root, foreground, with stdin
from `/dev/null`. If a run prints `ABORT:` or a check fails, match it against
SPEC section 7 before doing anything else, tell me what happened, and retry at
most twice.

Verify SPEC section 5, then give me the report in SPEC section 9.
