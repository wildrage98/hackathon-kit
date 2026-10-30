#!/usr/bin/env bash
# 명령을 실행하고 stdout/stderr를 logs/ 에 타임스탬프 파일로 저장한다.
# 사용: tools/run_and_log.sh <태그> <명령...>
#   예: tools/run_and_log.sh test python -m pytest -q
#       tools/run_and_log.sh run  python src/main.py --input data/sample.csv
set -uo pipefail

if [ $# -lt 2 ]; then
  echo "사용: $0 <태그> <명령...>" >&2
  exit 2
fi

TAG="$1"; shift
mkdir -p logs
TS="$(date '+%Y%m%d_%H%M%S')"
LOG="logs/${TS}_${TAG}.log"

{
  echo "# cmd : $*"
  echo "# cwd : $(pwd)"
  echo "# time: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "# ----"
} > "$LOG"

"$@" 2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}

{
  echo "# ----"
  echo "# exit: $RC"
  echo "# end : $(date '+%Y-%m-%d %H:%M:%S')"
} >> "$LOG"

echo "[log] $LOG (exit $RC)"
exit "$RC"
