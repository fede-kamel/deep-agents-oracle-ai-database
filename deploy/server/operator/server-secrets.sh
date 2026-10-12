#!/usr/bin/env bash
# OPERATOR STEP (your own terminal, on the laptop): open the bastion tunnel,
# then store the GenAI key in the server's gateway and set the web login.
# Both prompts run on the VM and hide what you type; nothing passes through
# the coding agent or this laptop's shell history.
set -euo pipefail
cd "$(dirname "$0")/../../.."
deploy/server/connect.sh
SSH=(ssh -t -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR opc@127.0.0.1)
"${SSH[@]}" 'cd deepagents && scripts/operator/genai-provider.sh'
"${SSH[@]}" 'deepagents/deploy/server/operator/set-login.sh'
echo "Server secrets set. Tell the coding agent 'done'."
