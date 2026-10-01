#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! /usr/bin/env python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "ProspectSignal needs Python 3.10 or newer."
  echo "Install it from https://www.python.org/downloads/ and try again."
  read -r -p "Press Return to close..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating ProspectSignal's private Python environment..."
  /usr/bin/env python3 -m venv .venv
fi

source .venv/bin/activate
export ARROW_DEFAULT_MEMORY_POOL="${ARROW_DEFAULT_MEMORY_POOL:-system}"

REQUIREMENTS_HASH="$(/usr/bin/shasum -a 256 requirements.txt | /usr/bin/awk '{print $1}')"
READY_FILE=".venv/.prospectsignal-requirements-${REQUIREMENTS_HASH}"
if [ ! -f "$READY_FILE" ]; then
  echo "First launch: downloading ProspectSignal's packages. Later launches will be faster."
  python -m pip --disable-pip-version-check install --prefer-binary -r requirements.txt
  /bin/rm -f .venv/.prospectsignal-requirements-*
  /usr/bin/touch "$READY_FILE"
fi

PORT="${PROSPECTSIGNAL_PORT:-8589}"
echo "Starting ProspectSignal at http://127.0.0.1:${PORT} ..."
exec python -m streamlit run app.py \
  --server.headless=false \
  --server.address=127.0.0.1 \
  --server.port="$PORT" \
  --server.fileWatcherType=none \
  --browser.gatherUsageStats=false
