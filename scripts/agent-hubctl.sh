#!/usr/bin/env bash
# Control the local Agent Hub (Cursor ↔ Claude Code).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PID_FILE="$REPO/.agents/hub.pid"
LOG_FILE="$REPO/.agents/hub.log"
PORT="${AGENT_HUB_PORT:-8765}"
HOST="${AGENT_HUB_HOST:-127.0.0.1}"
URL="http://${HOST}:${PORT}"

cmd="${1:-status}"
case "$cmd" in
  start)
    mkdir -p "$REPO/.agents"
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "already running pid $(cat "$PID_FILE") — $URL"
      exit 0
    fi
    nohup python3 "$HERE/agent_hub.py" >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    sleep 0.5
    if curl -sf "$URL/v1/health" >/dev/null; then
      echo "Agent Hub started — $URL (pid $(cat "$PID_FILE"))"
    else
      echo "failed to start — see $LOG_FILE" >&2
      exit 1
    fi
    ;;
  stop)
    if [[ -f "$PID_FILE" ]]; then
      kill "$(cat "$PID_FILE")" 2>/dev/null || true
      rm -f "$PID_FILE"
    fi
    pkill -f "python3.*agent_hub.py" 2>/dev/null || true
    echo "stopped"
    ;;
  status)
    if curl -sf "$URL/v1/health" >/dev/null 2>&1; then
      echo "running — $URL"
      curl -sf "$URL/v1/health" | python3 -m json.tool 2>/dev/null || true
    else
      echo "not running (try: $0 start)"
      exit 1
    fi
    ;;
  context)
    curl -sf "$URL/v1/context" | python3 -c "import sys,json; print(json.load(sys.stdin)['briefing'])"
    ;;
  handoff)
    shift
    curl -sf -X POST "$URL/v1/handoff" -H 'Content-Type: application/json' \
      -d "$(python3 -c "import json,sys; print(json.dumps({'from':sys.argv[1],'to':sys.argv[2],'message':' '.join(sys.argv[3:])}))" "${AGENT_BRIDGE_ID:-human}" "$@")"
    echo
    ;;
  task)
    # agent-hubctl.sh task claude-code "audit stealth stack"
    target="${2:-claude-code}"
    shift 2 || shift
    curl -sf -X POST "$URL/v1/task" -H 'Content-Type: application/json' \
      -d "$(python3 -c "import json,os,sys; print(json.dumps({'from':os.environ.get('AGENT_BRIDGE_ID','human'),'target':sys.argv[1],'prompt':' '.join(sys.argv[2:])}))" "$target" "$@")"
    echo
    ;;
  dispatch)
    target="${2:-claude-code}"
    shift 2 || shift
    curl -sf -X POST "$URL/v1/dispatch" -H 'Content-Type: application/json' \
      -d "$(python3 -c "import json,sys; print(json.dumps({'target':sys.argv[1],'prompt':' '.join(sys.argv[2:]),'run':True}))" "$target" "$@")" | python3 -m json.tool
    ;;
  *)
    echo "Usage: $0 {start|stop|status|context|handoff FROM TO MSG|task TARGET PROMPT|dispatch TARGET PROMPT}"
    exit 1
    ;;
esac
