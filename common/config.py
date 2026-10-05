"""Non-secret configuration and secret lookup for every component.

Non-secret settings (DSN, region, model) live in a JSON file outside the
repository. Database passwords live in owner-only files beside it (directory
0700, files 0600), written once by `db/setup_admin.py` and read here by name,
so no script ever needs a password on its command line or in an environment
the coding agent can see, and nothing prints them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path(
    os.environ.get(
        "DA_CONFIG", Path.home() / ".config" / "deepagents-oracle-health" / "config.json"
    )
)
SECRETS_DIR = CONFIG_PATH.parent / "secrets"

OWNER = "DA_OWNER"
PATIENT_KEYS = ("X", "Y", "Z")
REFERENCE_TABLES = ("CLINICAL_REFERENCE", "RESEARCH_EVIDENCE")
VECTOR_TABLES = ("PATIENT_NOTE_VEC", *REFERENCE_TABLES)
EMBEDDING_MODEL = "MINILM_L12"


def agent_user(key: str) -> str:
    """The read-only database user that can see exactly one patient."""
    return f"DA_AGENT_{key}"


def patient_id(key: str) -> str:
    return f"SYN-{key}"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"ABORT: {CONFIG_PATH} is missing. Copy config.example.json there "
            "and fill in the DSN (see codex/SPEC.md section 1)."
        )
    return json.loads(CONFIG_PATH.read_text())


def password(user: str) -> str:
    """Read a database password from its owner-only file without printing it."""
    path = SECRETS_DIR / user
    if not path.exists():
        raise SystemExit(
            f"ABORT: no secret for {user}. Run db/setup_admin.py first "
            "(operator step, SPEC section 3)."
        )
    return path.read_text().strip()


def store_password(user: str, value: str) -> None:
    SECRETS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    SECRETS_DIR.chmod(0o700)
    path = SECRETS_DIR / user
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(value)
