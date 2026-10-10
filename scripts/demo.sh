#!/usr/bin/env bash
# Local demo: starts the server, creates a few bots, runs the starter bots against each other
# and keeps scheduling tournaments until you press Ctrl+C.
#
#   scripts/demo.sh                  # website on http://localhost:8000
#   PORT=8080 scripts/demo.sh        # another port
#   PACE=0.5 scripts/demo.sh         # faster play (seconds between actions, default 2)
#
# Everything lives in data/demo/ and is wiped on every start. Logs: data/demo/logs/.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PORT=${PORT:-8000}
PACE=${PACE:-2}
URL="http://127.0.0.1:$PORT"
DEMO="$ROOT/data/demo"
PY="$ROOT/server/.venv/bin/python"

cd "$ROOT"

# ---------------------------------------------------------------- one-time setup
if [ ! -x "$PY" ]; then
  echo "Setting up the Python environment (first run only)..."
  python3 -m venv server/.venv
  "$PY" -m pip install -q -e "server[dev]"
fi
if [ ! -f web/dist/index.html ]; then
  echo "Building the website (first run only)..."
  (cd web && npm install --silent && npm run build --silent)
fi
if curl -sf "$URL/api/v1/health" >/dev/null 2>&1; then
  echo "Something is already running on port $PORT. Stop it or use PORT=... scripts/demo.sh" >&2
  exit 1
fi

rm -rf "$DEMO"
mkdir -p "$DEMO/logs"
export POKER_DB="$DEMO/poker.db"

admin() { "$PY" -m poker_pi.admin "$@"; }

pids=()
cleanup() {
  echo
  echo "Stopping server and bots..."
  kill "${pids[@]}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# ---------------------------------------------------------------- server
POKER_PORT=$PORT "$PY" -m poker_pi >"$DEMO/logs/server.log" 2>&1 &
pids+=($!)
until curl -sf "$URL/api/v1/health" >/dev/null 2>&1; do sleep 0.3; done

# ---------------------------------------------------------------- bots
bots=()
start_bot() { # name owner command...
  local name=$1 owner=$2
  shift 2
  local token
  token=$(admin create-bot "$name" --owner "$owner" | awk '/Token:/ {print $2}')
  POKER_TOKEN=$token POKER_URL=$URL "$@" >"$DEMO/logs/$name.log" 2>&1 &
  pids+=($!)
  bots+=("$name")
  echo "  started $name ($owner)"
}

echo "Starting bots:"
start_bot "Pythonista" "Alice" python3 -u bots/python/bot.py
start_bot "Bluffy McPy" "Sara" python3 -u bots/python/bot.py
command -v node >/dev/null && start_bot "NodeNinja" "Lena" node bots/javascript/bot.mjs
command -v java >/dev/null && start_bot "JavaJack" "Tim" java bots/java/Bot.java
if command -v c++ >/dev/null && c++ -std=c++17 -O2 bots/cpp/bot.cpp -lcurl -o "$DEMO/cppbot" 2>/dev/null; then
  start_bot "CppCrusher" "Max" "$DEMO/cppbot"
fi
if command -v go >/dev/null && (cd bots/go && go build -o "$DEMO/gobot" .) 2>/dev/null; then
  start_bot "GoGopher" "Jonas" "$DEMO/gobot"
fi

# an upcoming tournament, so the lobby has something scheduled
admin create-tournament --name "Sunday Showdown" --start "+3d" >/dev/null

schedule() { # name, seconds until start
  local out id
  out=$(admin create-tournament --name "$1" --start "+$2s" --stack 1000 --hands-per-level 6 --pace "$PACE")
  id=$(echo "$out" | awk '{print $2}')
  admin register "$id" "${bots[@]}" >/dev/null
  echo "$id"
}

echo
echo "  Website:     $URL"
echo "  Swagger UI:  $URL/docs"
echo "  Logs:        $DEMO/logs/"
echo
echo "Press Ctrl+C to stop."
echo

round=1
while true; do
  id=$(schedule "Demo Cup #$round" 20)
  echo "Demo Cup #$round (tournament $id) starts in 20 s: $URL/#/tournament/$id"
  until curl -s "$URL/api/v1/public/tournaments/$id" | grep -qE '"status":"(finished|cancelled)"'; do sleep 3; done
  winner=$(curl -s "$URL/api/v1/public/tournaments/$id" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["winner"] or "-")')
  echo "Demo Cup #$round finished, winner: $winner"
  round=$((round + 1))
done
