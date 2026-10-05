#!/usr/bin/env bash
# OPERATOR STEP (your own terminal, not the coding agent's): store the OCI
# Generative AI API key in the OpenShell gateway as provider `deepagents-genai`.
# The key is read without echoing, handed to the gateway, and unset. Sandboxes
# only ever see a placeholder that the proxy swaps on the way to OCI.
#
# Create the key first (policy before key; see sandbox/profile/oci-genai-python.yaml).
set -euo pipefail
cd "$(dirname "$0")/../.."
openshell provider profile import --file sandbox/profile/oci-genai-python.yaml --global </dev/null >/dev/null 2>&1 || true
read -rsp "OCI Generative AI API key (not echoed): " OCI_GENAI_API_KEY; echo
export OCI_GENAI_API_KEY
if openshell provider get deepagents-genai </dev/null >/dev/null 2>&1; then
  openshell provider update deepagents-genai --credential OCI_GENAI_API_KEY </dev/null
else
  openshell provider create --name deepagents-genai --type oci-genai-python --credential OCI_GENAI_API_KEY </dev/null
fi
unset OCI_GENAI_API_KEY
echo "Provider deepagents-genai is ready. Reply 'done' to the coding agent; do not paste this output."
