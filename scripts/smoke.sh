#!/usr/bin/env bash
# 최소 실행 확인. 결과는 logs/ 에 남는다.
# 사용: tools/smoke.sh [실행명령]   예: tools/smoke.sh "python src/main.py --help"
set -uo pipefail
mkdir -p logs
LOG="logs/$(date '+%Y%m%d_%H%M%S')_smoke.log"
exec > >(tee -a "$LOG") 2>&1

echo "== smoke $(date '+%H:%M:%S') =="
echo "-- python"; python --version 2>&1 || python3 --version
echo "-- node";   node --version 2>/dev/null || echo "(없음)"
echo "-- 필수 파일"
for f in README.md requirements.txt; do
  [ -f "$f" ] && echo "  ok  $f" || echo "  MISSING $f"
done
if [ -f requirements.txt ]; then
  echo "-- import 확인"
  python - <<'PY' 2>&1 || true
import re, importlib, sys
for line in open("requirements.txt"):
    name = re.split(r"[<>=\[; ]", line.strip())[0]
    if not name or name.startswith("#"): continue
    mod = {"scikit-learn":"sklearn","pyyaml":"yaml","pillow":"PIL","beautifulsoup4":"bs4"}.get(name.lower(), name.replace("-","_"))
    try: importlib.import_module(mod); print(f"  ok  {name}")
    except Exception as e: print(f"  FAIL {name}: {e}")
PY
fi
if [ $# -ge 1 ]; then
  echo "-- 실행: $*"
  timeout 60 bash -c "$*"; echo "  exit=$?"
fi
echo "-- 열린 포트"
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | grep -E 'LISTEN' | awk '{print "  "$4}' || echo "  (확인 불가)"
echo "== end =="
echo "[log] $LOG"
