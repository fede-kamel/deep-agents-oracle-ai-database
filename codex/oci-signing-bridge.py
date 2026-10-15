"""Run Codex on OCI Generative AI: a local pass-through that signs each request.

OCI Generative AI serves OpenAI models through an OpenAI-compatible API,
including the Responses API that Codex speaks. This listens on 127.0.0.1,
signs every request with an OCI CLI API-key profile, forwards it to the
regional endpoint, and streams the answer back unchanged. The key never leaves
the OCI configuration; Codex only sees a local URL.

    uv run --with oci --with requests python codex/oci-signing-bridge.py <profile> [port] [region]

Then point Codex at it:

    codex -c 'model_providers.ocigenai={name="OCI Generative AI", base_url="http://127.0.0.1:8899/openai/v1", wire_api="responses", requires_openai_auth=false}' \\
          -c model_provider=ocigenai -m openai.gpt-5.5 ...

The profile needs `use generative-ai-family` in the compartment it bills to:
OCI_GENAI_COMPARTMENT, or the profile's tenancy when that is unset.
"""

from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import oci
import requests

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "DEFAULT"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8899
REGION = sys.argv[3] if len(sys.argv) > 3 else "us-chicago-1"

config = oci.config.from_file(profile_name=PROFILE)
signer = oci.signer.Signer(config["tenancy"], config["user"], config["fingerprint"], config["key_file"],
                           pass_phrase=config.get("pass_phrase"))
UPSTREAM = f"https://inference.generativeai.{REGION}.oci.oraclecloud.com"
COMPARTMENT = os.environ.get("OCI_GENAI_COMPARTMENT", config["tenancy"])


class Bridge(BaseHTTPRequestHandler):
    def _forward(self, method: str) -> None:
        if not self.path.startswith("/openai/v1/"):
            self.send_error(404)
            return
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {"content-type": self.headers.get("content-type", "application/json"),
                   "accept": self.headers.get("accept", "*/*"), "opc-compartment-id": COMPARTMENT}
        upstream = requests.request(method, UPSTREAM + self.path, data=body, headers=headers,
                                    auth=signer, stream=True, timeout=600)
        self.send_response(upstream.status_code)
        self.send_header("content-type", upstream.headers.get("content-type", "application/json"))
        self.end_headers()
        for chunk in upstream.iter_content(chunk_size=None):
            self.wfile.write(chunk)
            self.wfile.flush()

    def do_POST(self) -> None:  # noqa: N802 (http.server naming)
        self._forward("POST")

    def do_GET(self) -> None:  # noqa: N802
        self._forward("GET")

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")


if __name__ == "__main__":
    print(f"signing bridge on http://127.0.0.1:{PORT}/openai/v1 -> {UPSTREAM}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Bridge).serve_forever()
