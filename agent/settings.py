"""Runtime settings for the agent, inside or outside the sandbox.

Inside the OpenShell sandbox everything comes from the environment the run
script sets up: the database login of the one patient's read-only user, and
`OCI_GENAI_API_KEY`, which there is only a placeholder that the OpenShell proxy
swaps for the real key on the way to OCI Generative AI. Outside the sandbox
(local development) the same values come from the host config and secrets
files, and the key from the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    patient_key: str
    dsn: str
    db_user: str
    db_password: str
    genai_region: str
    chat_model: str
    worker_model: str
    genai_api_key: str

    @property
    def patient_id(self) -> str:
        return f"SYN-{self.patient_key}"

    @property
    def genai_base_url(self) -> str:
        return f"https://inference.generativeai.{self.genai_region}.oci.oraclecloud.com/openai/v1"


def load(patient_key: str) -> Settings:
    key = patient_key.upper()
    if key not in ("X", "Y", "Z"):
        raise SystemExit(f"ABORT: unknown patient {patient_key!r}; expected X, Y or Z.")
    user = f"DA_AGENT_{key}"

    if os.environ.get("DA_DSN"):  # sandbox: the run script provides everything
        dsn = os.environ["DA_DSN"]
        db_password = os.environ["DA_DB_PASSWORD"]
        region = os.environ.get("DA_GENAI_REGION", "us-chicago-1")
        chat = os.environ.get("DA_CHAT_MODEL", "openai.gpt-5.5")
        worker = os.environ.get("DA_WORKER_MODEL", "google.gemini-2.5-flash")
    else:  # host development
        from common.config import load_config, password

        cfg = load_config()
        dsn, db_password = cfg["dsn"], password(user)
        region = cfg.get("genai_region", "us-chicago-1")
        chat = cfg.get("chat_model", "openai.gpt-5.5")
        worker = cfg.get("worker_model", "google.gemini-2.5-flash")

    api_key = os.environ.get("OCI_GENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("ABORT: OCI_GENAI_API_KEY is not set (in the sandbox the provider injects it).")
    return Settings(key, dsn, user, db_password, region, chat, worker, api_key)
