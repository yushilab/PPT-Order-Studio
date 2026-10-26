#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="${PPTSTUDIO_PYTHON:-python3}"
"$PYTHON" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
if [ ! -x .venv/bin/python ]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install --upgrade pip
case "${1:-}" in
  --dev) spec='.[extract,dev]' ;;
  --core-only) spec='.' ;;
  '') spec='.[extract]' ;;
  *) echo 'Usage: sh bootstrap.sh [--dev|--core-only]' >&2; exit 2 ;;
esac
.venv/bin/python -m pip install -e "$spec"
.venv/bin/python -m pptstudio doctor
echo 'Ready. Run: .venv/bin/python -m pptstudio demo orders/demo'
