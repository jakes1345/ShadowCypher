#!/bin/bash
# ShadowCypher Sovereign IRC — Launch/Stop/Status
# Usage: ./sovereign.sh [start|stop|status|restart]

DIR="$(cd "$(dirname "$0")" && pwd)"
ERGO="$DIR/ergo"
CONF="$DIR/ircd.yaml"
PIDFILE="$DIR/ergo.pid"
LOGFILE="$DIR/irc.log"

case "${1:-start}" in
    start)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "[SOVEREIGN] Already running (PID $(cat "$PIDFILE"))"
            exit 0
        fi

        # Generate certs if missing
        if [ ! -f "$DIR/fullchain.pem" ]; then
            echo "[SOVEREIGN] Generating TLS certificates..."
            "$ERGO" mkcerts --conf "$CONF"
        fi

        # Init DB if missing
        if [ ! -f "$DIR/ircd.db" ]; then
            echo "[SOVEREIGN] Initializing database..."
            "$ERGO" initdb --conf "$CONF"
        fi

        echo "[SOVEREIGN] Starting Ergo IRC server..."
        cd "$DIR"
        nohup "$ERGO" run --conf "$CONF" >> "$LOGFILE" 2>&1 &
        echo $! > "$PIDFILE"
        sleep 1

        if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "[SOVEREIGN] Server running (PID $(cat "$PIDFILE"))"
            echo "[SOVEREIGN] IRC:       127.0.0.1:6667 (plain) / :6697 (TLS)"
            echo "[SOVEREIGN] WebSocket: 127.0.0.1:8097 (plain) / :8098 (TLS)"
        else
            echo "[SOVEREIGN] FAILED to start. Check $LOGFILE"
            exit 1
        fi
        ;;

    stop)
        if [ -f "$PIDFILE" ]; then
            PID=$(cat "$PIDFILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                echo "[SOVEREIGN] Stopped (PID $PID)"
            else
                echo "[SOVEREIGN] Not running (stale PID)"
            fi
            rm -f "$PIDFILE"
        else
            echo "[SOVEREIGN] Not running"
        fi
        ;;

    restart)
        "$0" stop
        sleep 1
        "$0" start
        ;;

    status)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "[SOVEREIGN] Running (PID $(cat "$PIDFILE"))"
            # Test connection
            if command -v nc &>/dev/null; then
                echo "QUIT" | nc -w1 127.0.0.1 6667 2>/dev/null | head -1
            fi
        else
            echo "[SOVEREIGN] Not running"
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
