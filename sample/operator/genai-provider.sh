#!/usr/bin/env bash
# OPERATOR STEP, in your own terminal (never the coding agent's): store the OCI
# Generative AI API key in the OpenShell gateway as provider `sample-genai`.
# The key is read without echo, handed to the gateway, and unset; sandboxes see
# only a placeholder that the proxy swaps on the way to OCI.
set -euo pipefail
cd "$(dirname "$0")/.."
openshell provider profile import --file sandbox/oci-genai-python.yaml --global </dev/null >/dev/null 2>&1 || true
read -rsp "OCI Generative AI API key (not echoed): " OCI_GENAI_API_KEY; echo
export OCI_GENAI_API_KEY
if openshell provider get sample-genai </dev/null >/dev/null 2>&1; then
  openshell provider update sample-genai --credential OCI_GENAI_API_KEY </dev/null
else
  openshell provider create --name sample-genai --type oci-genai-python --credential OCI_GENAI_API_KEY </dev/null
fi
unset OCI_GENAI_API_KEY
echo "Provider sample-genai is ready. Reply 'done'; do not paste this output."
