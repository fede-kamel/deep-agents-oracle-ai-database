# The sample, end to end (2026-10-20)

The `sample/` folder, built and run by following `sample/codex/SPEC.md` step by
step, against Oracle AI Database 26ai Free (23.26.3) in a local container, with
OpenShell 0.1.2 (Docker driver) and `openai.gpt-5.5` on OCI Generative AI.

| Step | Checkpoint | Result |
|---|---|---|
| 1. Dry run | `DRY RUN OK` | passed |
| 2. Image | `deep-agent-sample:0.1` exists, imports work | passed |
| 3. Users (`sql/01_users.sql`, typed at a terminal prompt) | both users created, grants succeeded, no password in the output | passed |
| 4. Schema (`sql/02_schema.sql`) | 5 tables, procedure, trigger, policy function, 4 policies, 12 rows, no errors | passed |
| Rules, as `SAMPLE_AGENT_A`, no model | `rules-check-2026-10-20.log` | `RULES OK (9/9)` |
| 5. Provider and login | provider present; login file 0600 | passed |
| 6. Run in a fresh sandbox | `run5-2026-10-20.log` | `BRIEF OK`, 8 ids, 0 missing, 137 s, no sandbox left |

In both runs the care coordinator's medication change was refused by the
trigger (ORA-20014) and logged; the medication-safety agent re-read the chart
and proposed it, with status `needs_physician`. In the first run the
coordinator had proposed stopping metformin "because eGFR is below 30"; the
medication-safety agent saw eGFR 47, declined that, and proposed stopping
ibuprofen instead.

What the test found and fixed in the sample:

| Found | Fix |
|---|---|
| `QUOTA ... ON data` exists only on Autonomous Database | `01_users.sql` uses DATA where it exists, USERS elsewhere |
| SQL*Plus prints a failing statement, with the substituted password | the password is used only inside PL/SQL; an error prints the ORA code |
| `care_action` has an identity column, which needs `CREATE SEQUENCE` | granted to `SAMPLE_OWNER` |
| the gate checked only `LAB-A-001`-shaped ids, so `[LAB-SYN-A-EGFR]` in `run4` was never looked up | any bracketed id is looked up; unknown kinds count as missing |
| OpenShell refuses an IP literal and denies a private address by default | a DNS name for the host, and `SAMPLE_DB_ALLOWED_IP` for a private address |

Logs are redacted of temporary paths. No password, key, or connect string for
any cloud database appears; the database here was a throwaway local container.
