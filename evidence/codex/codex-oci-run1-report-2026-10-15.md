Blocked at SPEC-OCI section 2.

- **Passed:** `terraform version`, `oci --version`, `jq --version`, `ssh -V`, input file existence started but did not complete after profile failure.
- **Failed:** OCI profile check.
- **Error:** The selected OCI CLI profile uses `security_token` auth but has no `security_token_file`.
- **SPEC-OCI Section 4 Match:** No exact match. This is a prerequisite/profile configuration issue, not a runtime OCI/Terraform symptom.
- **Retries:** Retried once with a safer profile parse. Same failure.

Please fix or refresh the OCI CLI profile referenced by `deploy/terraform/terraform.tfvars`, then reply `done`. Do not paste any OCI output.