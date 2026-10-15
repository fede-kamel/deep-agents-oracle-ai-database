Deploy and verify this demo in OCI by following `codex/SPEC-OCI.md` exactly.
Read it and `AGENTS.md` in full before you run anything.

Show me the prerequisites table from SPEC-OCI section 2. If the Terraform plan
proposes changes, show me only the Plan line and the resource addresses, and wait
for me to reply `apply`. For the Vault step, hand me the script to run in my own
terminal and tell me to reply `done` without pasting output; skip it if its
checkpoint already passes.

Run every command from the repository root, in the foreground, with stdin from
`/dev/null`. Never print an OCID, a secret, or a key. If a check fails, match it
against SPEC-OCI section 4 before doing anything else, tell me what happened, and
retry at most twice. Give me the report in SPEC-OCI section 7.
