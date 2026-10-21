# Security

## Reporting a problem

Open a private security advisory on this repository (GitHub, **Security** tab,
**Report a vulnerability**). Do not open a public issue for a security problem,
and never include a password, an API key, an OCID or a connect string.

## What the design guarantees, and where it is tested

| Guarantee | Enforced by | Tested by |
|---|---|---|
| The agent never holds the OCI Generative AI key | the OpenShell provider: sandboxes see a placeholder the proxy swaps in transit | `scripts/safety_probe.sh` (7/7) |
| The sandbox reaches OCI Generative AI and the database, nothing else, from `python3.12` only | `sandbox/policy.template.yaml` and the provider profile | `scripts/safety_probe.sh` |
| Each agent user sees one synthetic patient and may only propose | row-level security and grants (migrations 0004-0008) | `scripts/verify.py --rls-only` (25/25) |
| Only the medication-safety agent may propose a medication change; only a physician may approve one | policies CP-03 and CP-02 (migrations 0007-0008) | `scripts/verify.py --rls-only` |
| Every cited source exists for this patient | the gate in `agent/verify.py` | every run; `scripts/verify.py <brief>` |
| Real-looking identifiers never reach the model | `agent/guards.py` | `tests/test_guards.py` |

## Secrets

No script takes a secret as an argument or prints one. The two operator scripts
(`scripts/operator/`) read them with `read -rs`; database passwords live in
owner-only files under `~/.config/deepagents-oracle-health/secrets/`; the GenAI
key lives in the OpenShell gateway, or in OCI Vault for the OCI deployment.
Coding agents follow `AGENTS.md`, which makes any secret in an output a stop condition.

## Scope

This is a demonstration on synthetic data. It is not hardened for production
use or for real patient data; see "What it is, and what it is not" in the README.
