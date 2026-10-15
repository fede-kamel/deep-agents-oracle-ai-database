Vault checkpoint failed. This is not a SPEC-OCI section 4 symptom; it is the expected section 3.3 operator step.

Missing secret names:

- `deepagents-db-DA_AGENT_Y`
- `deepagents-db-DA_AGENT_Z`
- `deepagents-db-DA_CLINICIAN`
- `deepagents-db-DA_OWNER`
- `deepagents-db-DA_PHYSICIAN`
- `deepagents-genai-key`
- `deepagents-login`

Run this in your own terminal from the repository root:

```shell
deploy/server/operator/vault-put.sh
```

Reply `done` when it finishes. Do not paste the output.