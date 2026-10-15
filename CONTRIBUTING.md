# Contributing

Issues and pull requests are welcome. Two rules come first: synthetic data
only (the schema refuses anything else), and never a secret in a file, an
issue, a commit, or a log.

## Checks that run anywhere

These need no cloud account and run in CI on every pull request:

```shell
uv sync
uv run ruff check .
uv run pytest -q
(cd web && npm ci && npm run lint && npm run build)
shellcheck -S warning scripts/*.sh scripts/operator/*.sh deploy/*.sh deploy/server/*.sh deploy/server/operator/*.sh
terraform -chdir=deploy/terraform fmt -check
```

## Checks that need the environment

With a database, an OpenShell gateway and a GenAI provider (`codex/SPEC.md`
section 4), a change to the agent, the database, the sandbox or the scripts
also needs:

| Change | Run | Ends with |
|---|---|---|
| sandbox policy or provider | `scripts/safety_probe.sh </dev/null` | `PROBE OK (7/7)` |
| migrations, grants, policies | `uv run python scripts/verify.py --rls-only` | `VERIFY OK (25/25)` |
| agent, prompts, tools | `scripts/sandbox.sh run Y </dev/null` | a final `verify` event that passed |
| web app | `scripts/webapp-check.sh Y </dev/null` | `WEBAPP OK (7/7)` |

Say in the pull request which of these you ran, with the last lines of each.

## Conventions

- `web/package-lock.json` resolves from `https://registry.npmjs.org/` only; CI refuses any other
  registry. If your npm uses a private mirror, rewrite the `resolved` URLs before committing.

- Schema changes are new Alembic migrations with a working `downgrade()`.
- Scripts run from the repository root, in the foreground, with `</dev/null`.
- Keep `codex/SPEC.md` in step with the scripts: where they differ, the script wins and the spec is the bug.
- Writing: active voice, short sentences, commands in `shell` fences.
