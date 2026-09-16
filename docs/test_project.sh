#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "[WebShield] Basic validation"
test -x "$ROOT/Script/firewall.sh"
echo "[PASS] firewall.sh exists and is executable"
python3 -m py_compile "$ROOT/Script/web.py"
echo "[PASS] web.py syntax check passed"
echo "[PASS] Repository validation completed"
