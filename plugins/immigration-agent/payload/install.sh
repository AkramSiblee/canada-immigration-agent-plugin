#!/bin/sh
# Canada Immigration Agent: installer for macOS and Linux.  Run:  sh install.sh
cd "$(dirname "$0")" || exit 1
PY=""
for name in python3 python; do
  if command -v "$name" >/dev/null 2>&1 && "$name" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then PY="$name"; break; fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 or newer was not found. Install it from python.org (macOS) or your package manager, then run this again."
  exit 1
fi
echo "Installing the Python libraries..."
"$PY" -m pip install --user -r requirements.txt || "$PY" -m pip install --user --break-system-packages -r requirements.txt
echo
"$PY" scripts/setup_check.py --install
