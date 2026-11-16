#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# tests/run.sh: static checks, the speaker helper check, then the end-to-end
# scenarios on a private X display (tests/e2e.py). Never touches the desktop,
# the user's windows or data/. See docs/TESTING.md.
#
#   tests/run.sh                    static checks + all scenarios except the slow one (about 8 minutes)
#   tests/run.sh --static           static checks only (seconds)
#   tests/run.sh dictation tune     static checks + the named scenarios
#   tests/run.sh --slow --keep      also the 2.5-minute monologue; keep the work folder
set -u
REPO="$(cd "$(dirname "$(realpath "$0")")/.." && pwd)"
cd "$REPO" || exit 1
FAILED=0
ok() { printf 'PASS  %s\n' "$1"; }
bad() { printf 'FAIL  %s\n' "$1"; FAILED=$((FAILED + 1)); }

echo "== Static checks"
/usr/bin/python3 -m py_compile bin/dictate-live bin/dictate-stats lib/log_session.py tests/e2e.py && ok "Python compiles" || bad "Python compile"
.venv/bin/python -m py_compile lib/speakers.py && ok "speaker helper compiles" || bad "speaker helper compile"
bash -n bin/dictate bin/dictate-compare lib/active-app install.sh tests/run.sh && ok "shell syntax" || bad "shell syntax"
if command -v uvx >/dev/null; then
  uvx -q pyflakes bin/dictate-live lib/speakers.py tests/e2e.py && ok "pyflakes" || bad "pyflakes"
else
  echo "SKIP  pyflakes (uvx not installed)"
fi
rm -rf bin/__pycache__ lib/__pycache__ tests/__pycache__
missing=$(grep -L "SPDX-License-Identifier: AGPL-3.0-only" bin/* lib/* install.sh tests/*.py tests/*.sh)
[ -z "$missing" ] && ok "SPDX headers" || bad "SPDX header missing in: $missing"

echo "== Speaker helper"
# Three phrases, two voices (the clip and a pitch-shifted copy): two speakers, helper survives.
/usr/bin/python3 - <<'EOF' && ok "speaker helper separates two voices" || bad "speaker helper"
import json, os, subprocess, sys, tempfile
sys.path.insert(0, "tests")
import e2e
d = tempfile.mkdtemp(prefix="dictate-spk-")
a = e2e.fetch_jfk()
e2e.shifted(a, 0.80, os.path.join(d, "b.wav"))
lines = [{"cmd": "assign", "id": 1, "path": a}, {"cmd": "assign", "id": 2, "path": os.path.join(d, "b.wav")},
         {"cmd": "assign", "id": 3, "path": a}, {"cmd": "final"}]
out = subprocess.run([".venv/bin/python", "-I", "lib/speakers.py", "models/nemo_en_titanet_small.onnx"],
                     input="".join(json.dumps(l) + "\n" for l in lines), capture_output=True, text=True).stdout.splitlines()
final = json.loads(out[-1])
sys.exit(0 if len(out) == 4 and final["speakers"] == 2 and final["labels"]["1"] == final["labels"]["3"] else 1)
EOF
rm -rf tests/__pycache__

if [ "${1:-}" = "--static" ]; then
  echo; [ "$FAILED" -eq 0 ] && echo "All static checks passed." || echo "$FAILED check(s) failed."
  exit "$FAILED"
fi

if pgrep -x Xvfb >/dev/null; then
  echo "NOTE  another Xvfb is running; the tests use a free display number and leave it alone"
fi
echo "== End-to-end scenarios (private display)"
dbus-run-session -- /usr/bin/python3 tests/e2e.py "$@" || FAILED=$((FAILED + 1))
rm -rf tests/__pycache__
exit "$FAILED"
