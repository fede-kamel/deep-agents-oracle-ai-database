# Sandbox image for the pre-visit brief agent.
# Same base as the OpenShell kill-switch demo; the provider profile names its
# interpreter, /usr/local/bin/python3.12, as the one binary allowed to egress.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --system --no-cache -r /tmp/requirements.txt && rm /tmp/requirements.txt
RUN useradd --create-home --uid 1500 sandbox
USER sandbox
WORKDIR /sandbox
