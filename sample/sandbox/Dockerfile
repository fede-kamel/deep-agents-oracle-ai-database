# Sandbox image for the sample agent. Dependencies are baked in, so the sandbox
# needs no package registry at run time (the policy refuses PyPI anyway).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN uv pip install --system --no-cache \
      langchain-oci==0.3.2 langchain-openai==1.6.7 langchain==1.4.3 deepagents==0.7.21 \
      langgraph-oracledb==1.0.1 oracledb==3.4.2
RUN useradd --create-home --uid 1500 sandbox
USER sandbox
WORKDIR /sandbox
