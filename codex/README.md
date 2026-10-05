# Build and run this with Codex

| File | What it is |
|---|---|
| [`SPEC.md`](SPEC.md) | the specification: inputs, preflight, every build step with its checkpoint, acceptance, rules, known behaviour, report |
| [`PROMPT.md`](PROMPT.md) | the prompt that drives Codex through the specification |
| [`operator-context.example.md`](operator-context.example.md) | answers for a rerun once the two operator steps are done |
| [`../AGENTS.md`](../AGENTS.md) | what Codex loads automatically here: the hard rules and the layout |

Interactive, from a clone:

```shell
codex -s workspace-write -c sandbox_workspace_write.network_access=true \
  --add-dir ~/.config/openshell --add-dir ~/.config/deepagents-oracle-health \
  --add-dir ~/.rd --add-dir ~/.cache/uv --add-dir ~/.local/share/uv --add-dir ~/.npm \
  "$(cat codex/PROMPT.md)"
```

Non-interactive rerun, once the database users and the provider exist:

```shell
{ cat codex/operator-context.example.md; echo; cat codex/PROMPT.md; } | codex exec \
  -s workspace-write -c sandbox_workspace_write.network_access=true \
  --add-dir ~/.config/openshell --add-dir ~/.config/deepagents-oracle-health \
  --add-dir ~/.rd --add-dir ~/.cache/uv --add-dir ~/.local/share/uv --add-dir ~/.npm \
  -
```

`workspace-write` is enough: the flags grant network access (the gateway, the
database, OCI Generative AI), the OpenShell and demo config directories, Docker's
socket directory (Rancher Desktop keeps it under `~/.rd`), uv's cache and
Python installs, and npm's cache for the web build.
Codex never needs a secret: the two steps that do are `scripts/operator/*.sh`,
which you run in your own terminal.

## Recorded runs

| Run | What it did | Outcome |
|---|---|---|
| [1](../evidence/codex/codex-run1-report-2026-10-05.md) | full build | stopped at SPEC 7 when the machine's egress IP left the database ACL; reported, no workaround |
| [2](../evidence/codex/codex-run2-report-2026-10-05.md) | SPEC 4.1 to 5 on the first version | three verified briefs, probe 7/7, every check green |
| [3](../evidence/codex/codex-run3-webapp-report-2026-10-05.md) | SPEC 4.8 | `WEBAPP OK (7/7)` |
| [4](../evidence/codex/codex-run4-report-2026-10-05.md) | SPEC 2, 4.6, 4.7 (Y) and 4.8 after the policies and the escalation agent | `PREFLIGHT OK` at 0008, `PROBE OK (7/7)`, `VERIFY OK (25/25)`, a Y brief through CP-03 → escalation → medication-safety, `WEBAPP OK (7/7)`; one gate repair |
| [5](../evidence/codex/codex-run5-report-2026-10-05.md) | the same, on the final code (connection retries, honest gate status) | all green; the Y brief passed the gate on the first draft (149 citations), 0 connection retries, `WEBAPP OK (7/7)` |
