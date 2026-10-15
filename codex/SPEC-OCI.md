# Specification: the demo in OCI, built and verified by a coding agent

Version 1, 2026-10-15. The OCI half of [`SPEC.md`](SPEC.md): the same rules
(`AGENTS.md`), the same report discipline, and a checkpoint for every step. It
drives `deploy/`, which puts the whole demo on one VM in a private subnet behind
a Network Load Balancer, with OCI Bastion for SSH and OCI Vault for the secrets
(see [`deploy/README.md`](../deploy/README.md)). The prompt is
[`PROMPT-OCI.md`](PROMPT-OCI.md). Where this file and a script differ, the
script wins, and the difference is a bug to report.

## 0. Done means

1. `terraform plan` for `deploy/terraform` reports no changes, after any apply the operator approved.
2. The Vault holds every secret the VM needs (names only are checked, never values).
3. `deploy/server/provision.sh </dev/null` ends with `provisioned: https://…`.
4. On the VM: `scripts/preflight.sh` ends with `PREFLIGHT OK`, `scripts/safety_probe.sh`
   with `PROBE OK (7/7)`, and `uv run python scripts/verify.py --rls-only` with `VERIFY OK (25/25)`.
5. On the VM: `scripts/sandbox.sh run Y` exits 0 and its final `verify` event passed.
6. The deployed web app answers on the VM (`/api/patients` 200) and the public URL answers
   `401` over HTTP/1.1 with `Alt-Svc: clear`.
7. Post-conditions (section 5) hold, and the operator has the report in section 7.

Out of scope: creating the VCN, its gateways, or the database; destroying anything.

## 1. Inputs and the identity

| Input | Supplied by | How the agent gets it |
|---|---|---|
| `deploy/terraform/terraform.tfvars` | the operator, from the example | the file exists; **never print it**: it holds OCIDs |
| `~/.config/deepagents-oracle-health/config.json` and the database secrets | the laptop build, `SPEC.md` section 4 | the files exist; never read the secrets |
| An OCI CLI profile (`oci_profile` in the tfvars), API-key auth | the operator | the CLI uses it with `--auth api_key`, as the deploy scripts do (an `OCI_CLI_AUTH` in the environment would otherwise win); the agent never opens `~/.oci` |
| The web login and the GenAI key in the Vault | the operator, with `deploy/server/operator/vault-put.sh` | section 3.3 |

The identity rule. The profile's key sits on disk, so a coding agent that runs
the CLI can use it. Give that profile the least it needs: a group that manages
only the families this Terraform creates, in the one compartment. The statements
are in [`deploy/terraform/least-privilege.policy`](../deploy/terraform/least-privilege.policy);
a tenancy administrator creates the group and the policy once. Use a broader
key only for a supervised run, and say so in the report.

## 2. Prerequisites

| Requirement | Check | Passes when |
|---|---|---|
| Terraform | `terraform version` | prints a version |
| OCI CLI | `oci --version` | prints a version |
| jq, ssh | `jq --version; ssh -V` | print versions |
| the profile works | `oci iam region list --profile <oci_profile> --auth api_key --query 'length(data)'` | prints a number |
| the inputs exist | `test -f deploy/terraform/terraform.tfvars && test -f ~/.config/deepagents-oracle-health/config.json` | exit 0 |

## 3. Steps

Run from the repository root, in the foreground, with `</dev/null`. Never echo an
OCID, a secret OCID, a public key, or a secret value; report pass or fail.

### 3.1 Terraform plan

```shell
terraform -chdir=deploy/terraform init -input=false </dev/null
terraform -chdir=deploy/terraform plan -input=false -detailed-exitcode -no-color </dev/null | grep -E '^(Plan:|No changes)'
```

Checkpoint: `No changes.` (exit 0). If the plan proposes changes (exit 2), show the
operator only the `Plan:` line and the resource addresses, and wait. Run
`terraform -chdir=deploy/terraform apply -input=false -auto-approve </dev/null` only
after the operator replies `apply`. If the plan would destroy or replace the VM,
the Vault, or the load balancer, stop.

### 3.2 Outputs

```shell
terraform -chdir=deploy/terraform output -raw url
```

Checkpoint: prints `https://<host>`. The other outputs are identifiers: use them, do not print them.

### 3.3 Secrets in the Vault (operator step)

List the names only:

```shell
cd deploy/terraform && oci vault secret list --auth api_key --profile "$(sed -nE 's/^oci_profile *= *"(.*)"/\1/p' terraform.tfvars)" \
  --compartment-id "$(sed -nE 's/^compartment_id *= *"(.*)"/\1/p' terraform.tfvars)" \
  --vault-id "$(terraform output -raw vault_id)" --lifecycle-state ACTIVE --all \
  --query 'data[]."secret-name"' --raw-output </dev/null
```

Checkpoint: the list holds `deepagents-genai-key`, `deepagents-login`, and one
`deepagents-db-<FILE>` for every file in `~/.config/deepagents-oracle-health/secrets/`.
If any is missing, hand the operator `deploy/server/operator/vault-put.sh` to run in
their own terminal, wait for `done`, and check again.

### 3.4 Provision the VM

```shell
deploy/server/provision.sh </dev/null
```

It opens the Bastion tunnel, copies the code and the built front end, installs the
system (one reboot for Landlock on a new VM), OpenShell, the sandbox image, the Python
environment, the web service and Caddy, and reads the secrets from the Vault. It waits
for a run in progress before restarting the web service. About 5 minutes on an existing
VM, 20 on a new one.

Checkpoint: ends with `provisioned: https://<host>`.

### 3.5 Checks on the VM

Through the tunnel the provisioning opened (`deploy/server/connect.sh` reopens it):

```shell
ssh -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null opc@127.0.0.1 \
  'cd deepagents && scripts/preflight.sh </dev/null && scripts/safety_probe.sh </dev/null \
   && ~/.local/bin/uv run python scripts/verify.py --rls-only </dev/null' </dev/null
```

Checkpoint: `PREFLIGHT OK`, `PROBE OK (7/7)`, `VERIFY OK (25/25)`.

### 3.6 One brief on the VM

```shell
ssh -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null opc@127.0.0.1 \
  'cd deepagents && scripts/sandbox.sh run Y </dev/null 2>/dev/null | tail -c 20000' </dev/null \
  | grep -o '"type": "verify"[^}]*"final": true' | tail -1
```

About 5 minutes. Checkpoint: the final verify event shows `"passed": true`.
If the web application is running a brief, wait for it (`/api/runs` on the VM).
Never approve or reject a care action.

### 3.7 The web application and the public URL

```shell
ssh -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null opc@127.0.0.1 \
  'curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/api/patients' </dev/null
curl -sI "$(terraform -chdir=deploy/terraform output -raw url)/" | grep -iE '^(HTTP|alt-svc)'
```

Checkpoint: `200`; then `HTTP/1.1 401` and `Alt-Svc: clear`.

## 4. Known behaviour and troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| `Permission denied (publickey)` once from the Bastion | a new session refuses the key for a few seconds | `connect.sh` retries; re-run it |
| `Connection refused` on port 2222 | the 3-hour Bastion session expired | `deploy/server/connect.sh </dev/null` |
| `Landlock is not active` | the reboot did not take | re-run `provision.sh` |
| `NotAuthorizedOrNotFound` from the CLI or Terraform | the profile lacks a grant, or the resource is outside the compartment | report the service and stop; never widen a policy yourself |
| `transparent TCP mapping is expired` on the VM | OpenShell DNS mapping TTL | the Unbound cache prevents it; `agent/db.py` retries; re-run once |
| `a run is in progress; waiting` | the web app is driving a brief | expected; wait |

## 5. Post-conditions

- `openshell sandbox list` on the VM shows no `brief-*` or `probe-*` sandbox.
- No OCID, secret value, or key appears in the conversation or the report.
- `git status` shows no change to tracked files.

## 6. Rules for the agent

All of `AGENTS.md`, plus: never run `terraform destroy`, `terraform apply` without
the operator's `apply`, `vault-put.sh`, or any `oci` command that creates, updates,
or deletes a resource; never edit `terraform.tfvars`, the Terraform files, or the
deploy scripts to make a step pass; never open `~/.oci`.

## 7. Report

The prerequisites table; the plan result; the secret-name check (names only, as
present or missing); the provisioning result and duration; the three VM checks; the
brief's seconds, tool calls, citations and verify result; the web and URL checks;
any section-4 symptom and what was done; and confirmation of section 5.
