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
  --add-dir ~/.rd --add-dir ~/.cache/uv \
  "$(cat codex/PROMPT.md)"
```

Non-interactive rerun, once the database users and the provider exist:

```shell
{ cat codex/operator-context.example.md; echo; cat codex/PROMPT.md; } | codex exec \
  -s workspace-write -c sandbox_workspace_write.network_access=true \
  --add-dir ~/.config/openshell --add-dir ~/.config/deepagents-oracle-health \
  --add-dir ~/.rd --add-dir ~/.cache/uv -
```

`workspace-write` is enough: the flags grant network access (the gateway, the
database, OCI Generative AI), the OpenShell and demo config directories, Docker's
socket directory (Rancher Desktop keeps it under `~/.rd`), and uv's cache.
Codex never needs a secret: the two steps that do are `scripts/operator/*.sh`,
which you run in your own terminal.
