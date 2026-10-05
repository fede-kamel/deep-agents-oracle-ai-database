#!/usr/bin/env bash
# Run the pre-visit brief agent for one synthetic patient inside an NVIDIA
# OpenShell sandbox.
#
#   scripts/sandbox.sh run X [question]   create, upload, run, stream JSON events, stop
#   scripts/sandbox.sh status             demo sandboxes on the gateway
#   scripts/sandbox.sh cleanup            delete every sandbox this script created
#
# What the sandbox holds:
#   - OCI_GENAI_API_KEY: a placeholder. The provider `deepagents-genai` keeps the
#     key in the gateway; the proxy swaps it in only on the way to OCI GenAI.
#   - the database login of DA_AGENT_<patient>: uploaded as a 0600 file, never
#     on a command line. That user can SELECT and nothing else, and row-level
#     security shows it one patient.
#   - egress: OCI GenAI (from the provider profile) and the database listener
#     (policy.template.yaml), for /usr/local/bin/python3.12 only.
#
# stdout carries only the agent's JSON events; progress goes to stderr.
# Every exec reads stdin from /dev/null (OpenShell 0.1.2 reads piped stdin to EOF).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${DA_SANDBOX_IMAGE:-deepagents-oracle-health:0.1}"
PROVIDER="${DA_PROVIDER:-deepagents-genai}"
CONFIG="${DA_CONFIG:-$HOME/.config/deepagents-oracle-health/config.json}"
SECRETS="$(dirname "$CONFIG")/secrets"
LABEL="app=deepagents-oracle-health"

say() { printf '%s\n' "$*" >&2; }
step() { printf '\033[1;32m$\033[0m %s\n' "$*" >&2; }
die() { say "ABORT: $*"; exit 1; }

cfg() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$CONFIG" "$1"; }

render_policy() {
  local out="$1"
  sed -e "s|__DB_HOST__|$(cfg db_host)|" -e "s|__DB_PORT__|$(cfg db_port)|" \
    "$ROOT/sandbox/policy.template.yaml" >"$out"
}

run() {
  local key="${1:-}" question="${2:-}"
  [[ "$key" =~ ^[XYZ]$ ]] || die "usage: scripts/sandbox.sh run X|Y|Z [question]"
  [[ -f "$CONFIG" ]] || die "$CONFIG is missing (SPEC section 1)"
  [[ -f "$SECRETS/DA_AGENT_$key" ]] || die "no database secret for DA_AGENT_$key (SPEC section 3)"
  openshell provider get "$PROVIDER" </dev/null >/dev/null 2>&1 || die "provider $PROVIDER is missing (SPEC section 4)"

  SB="brief-$(echo "$key" | tr 'XYZ' 'xyz')-$(date +%H%M%S)"
  WORK="$(mktemp -d)"
  LOGS_PID=""
  trap on_exit EXIT
  chmod 700 "$WORK"
  local sb="$SB" work="$WORK"

  render_policy "$work/policy.yaml"
  mkdir -p "$work/app/data" "$work/secrets"
  cp -R "$ROOT/agent" "$work/app/agent"
  cp "$ROOT/data/__init__.py" "$ROOT/data/patients.py" "$work/app/data/"
  find "$work/app" -name __pycache__ -prune -exec rm -rf {} +
  # The env file is written with umask 077 and never printed.
  (
    umask 077
    {
      printf 'DA_DSN=%q\n' "$(cfg dsn)"
      printf 'DA_DB_PASSWORD=%q\n' "$(cat "$SECRETS/DA_AGENT_$key")"
      printf 'DA_GENAI_REGION=%q\n' "$(cfg genai_region)"
      printf 'DA_RUN_ID=%q\n' "${DA_RUN_ID:-cli-$(date +%Y%m%d-%H%M%S)}"
      printf 'DA_CHAT_MODEL=%q\n' "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('chat_model','openai.gpt-5.5'))" "$CONFIG")"
      printf 'DA_WORKER_MODEL=%q\n' "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('worker_model','google.gemini-2.5-flash'))" "$CONFIG")"
    } >"$work/secrets/db.env"
  )

  step "openshell sandbox create --name $sb --from $IMAGE --provider $PROVIDER --policy policy.yaml --label $LABEL --detach"
  openshell sandbox create --name "$sb" --from "$IMAGE" --provider "$PROVIDER" \
    --policy "$work/policy.yaml" --label "$LABEL" --label "patient=SYN-$key" \
    --no-auto-providers --detach -- sleep infinity </dev/null >&2 \
    || die "could not create $sb"

  for _ in $(seq 1 60); do
    openshell sandbox exec --name "$sb" -- /usr/local/bin/python3.12 -c "print('ready')" </dev/null 2>/dev/null | grep -q ready && break
    sleep 2
  done
  # OpenShell 0.1.2: the supervisor's first settings poll (about 10 s after
  # start) reloads the provider environment and bumps the policy generation,
  # which closes every connection opened before it (fixed upstream, unreleased;
  # NVIDIA/OpenShell#3994). Start the agent only after that reload.
  step "waiting for the sandbox's first policy reload"
  for _ in $(seq 1 30); do
    openshell logs "$sb" -n 400 --source sandbox </dev/null 2>/dev/null |
      grep -q "Settings poll: config change detected" && break
    sleep 1
  done

  step "openshell sandbox upload $sb app/ /sandbox/app   (agent code)"
  openshell sandbox upload "$sb" "$work/app" /sandbox </dev/null >&2 || die "upload failed"
  step "openshell sandbox upload $sb secrets/ /sandbox/secrets   (0600 db.env, not shown)"
  openshell sandbox upload "$sb" "$work/secrets" /sandbox </dev/null >&2 || die "upload failed"
  rm -rf "$work/secrets"

  # The sandbox console: gateway and supervisor logs, including every network
  # decision (NET:OPEN ALLOWED / DENIED), streamed to stderr while the agent runs.
  openshell logs "$sb" --tail --source all </dev/null 2>&1 | sed -u 's/^/[openshell] /' >&2 &
  LOGS_PID=$!

  local args=(--patient "$key")
  [[ -n "$question" ]] && args+=(--question "$question")
  step "openshell sandbox exec --name $sb -- python3.12 -m agent.run ${args[*]}"
  local rc=0
  openshell sandbox exec --name "$sb" --workdir /sandbox/app -- /bin/sh -c \
    'set -a; . /sandbox/secrets/db.env; set +a; rm -f /sandbox/secrets/db.env; exec /usr/local/bin/python3.12 -m agent.run "$@"' \
    sh "${args[@]}" </dev/null || rc=$?

  sleep 1
  [[ -n "$LOGS_PID" ]] && kill "$LOGS_PID" 2>/dev/null || true
  LOGS_PID=""
  step "openshell sandbox delete $sb"
  openshell sandbox delete "$sb" </dev/null >&2 || true
  SB=""
  return "$rc"
}

on_exit() {
  [[ -n "${LOGS_PID:-}" ]] && kill "$LOGS_PID" 2>/dev/null || true
  [[ -n "${WORK:-}" ]] && rm -rf "$WORK"
  [[ -n "${SB:-}" ]] && openshell sandbox delete "$SB" </dev/null >/dev/null 2>&1 || true
}

status() {
  openshell sandbox list </dev/null
}

cleanup() {
  openshell sandbox list </dev/null 2>/dev/null | awk 'NR>1 && $1 ~ /^brief-[xyz]-[0-9]{6}$/ {print $1}' |
    while read -r sb; do
      step "openshell sandbox delete $sb"
      openshell sandbox delete "$sb" </dev/null >&2 || true
    done
}

case "${1:-}" in
  run) shift; run "$@" ;;
  status) status ;;
  cleanup) cleanup ;;
  *) die "usage: scripts/sandbox.sh run X|Y|Z [question] | status | cleanup" ;;
esac
