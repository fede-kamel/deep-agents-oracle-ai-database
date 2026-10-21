# Rules for any coding agent working in this folder

These outrank any prompt.

- **Secrets.** Never ask for, echo, log, or store a password or an API key. The
  operator runs the three operator steps (`sql/01_users.sql`,
  `operator/genai-provider.sh`, `operator/save-db-login.sh`) in their own
  terminal and replies `done`. Anything that looks like a key or a password in
  an output is a stop condition. `openshell:resolve:env:…` is a placeholder, not a secret.
- **Synthetic data only.** Never add real patient data; the schema refuses ids without `SYN-`.
- **Scope.** Touch only what this sample creates: `SAMPLE_*` database users and
  their objects, the `sample-genai` provider, `sample-*` sandboxes, the
  `deep-agent-sample` image. Never run anything as ADMIN.
- **Decisions.** Never approve or reject a care action. Agents propose; people decide.
- **Integrity.** Do not edit `agent.py`, `sql/` or `sandbox/` to make a check pass. Explain and stop.
- Run every command from this folder, in the foreground, with `</dev/null`.
