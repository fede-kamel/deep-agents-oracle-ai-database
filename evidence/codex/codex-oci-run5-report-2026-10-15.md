**Prerequisites**
| Requirement | Check | Passes when | Result |
|---|---|---|---|
| Terraform | `terraform version` | prints a version | 1.5.7 |
| OCI CLI | `oci --version` | prints a version | 3.84.0 |
| jq, ssh | `jq --version; ssh -V` | print versions | jq 1.8.1; OpenSSH 10.2 |
| the profile works | `oci iam region list --profile <oci_profile> --auth api_key --query 'length(data)'` | prints a number | 44 |
| the inputs exist | `test -f deploy/terraform/terraform.tfvars && test -f ~/.config/deepagents-oracle-health/config.json` | exit 0 | ok |

**OCI Report**
- Terraform: initialized; plan result was `No changes.`
- Vault: all required secret names are present; no missing names.
- Provisioning: passed with `provisioned: https://…`; duration was about 48 seconds.
- VM checks: `PREFLIGHT OK`; `PROBE OK (7/7)`; `VERIFY OK (25/25)`.
- Brief Y: passed final verify; 329.6 seconds; 45 tool calls; 12 SQL queries; 9 searches; 6 delegations; 151 citations; 5 actions.
- Web checks: VM API returned `200`; public URL returned `HTTP/1.1 401 Unauthorized` and `Alt-Svc: clear`.
- Section 4 symptoms: none encountered.
- Post-conditions: no `brief-*` or `probe-*` sandboxes listed; `git status` is clean; this report includes no OCID, secret value, or key.

This is personal work with synthetic data.