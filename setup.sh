#!/usr/bin/env bash
# hackathon-kit 설치: 현재 작업 폴더(과제 루트)에서 실행
# 사용: bash hackathon-kit/setup.sh
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

echo "[kit] 작업 루트: $ROOT"

# 1. AGENTS.md (기존 파일이 있으면 덮어쓰지 않고 .kit 로 둔다)
if [ -f "$ROOT/AGENTS.md" ]; then
  cp "$KIT/AGENTS.md" "$ROOT/AGENTS.kit.md"
  echo "[kit] AGENTS.md 가 이미 있어 AGENTS.kit.md 로 복사함 — 내용 병합 필요"
else
  cp "$KIT/AGENTS.md" "$ROOT/AGENTS.md"
  echo "[kit] AGENTS.md 설치"
fi

# 2. 스킬
mkdir -p "$CODEX_HOME/skills"
for d in "$KIT"/skills/*/; do
  name="$(basename "$d")"
  rm -rf "$CODEX_HOME/skills/$name"
  cp -r "$d" "$CODEX_HOME/skills/$name"
  echo "[kit] skill 설치: \$$name"
done

# 3. 문서 양식
mkdir -p "$ROOT/docs" "$ROOT/logs"
for f in "$KIT"/templates/*.md; do
  base="$(basename "$f")"
  if [ ! -f "$ROOT/docs/$base" ]; then
    cp "$f" "$ROOT/docs/$base"
  fi
done
echo "[kit] docs/ 양식 설치 (TIMEBOX, QUESTIONS, PLAN, DECISIONS, VERIFICATION, SUBMIT_CHECK)"

# 4. 스크립트
mkdir -p "$ROOT/tools"
cp "$KIT"/scripts/*.sh "$ROOT/tools/"
chmod +x "$ROOT/tools/"*.sh
echo "[kit] tools/ 설치 (run_and_log.sh, smoke.sh)"

# 5. 시작 시각 기록
date '+%Y-%m-%d %H:%M:%S' > "$ROOT/docs/START_TIME.txt"
echo "[kit] 시작 시각 기록: $(cat "$ROOT/docs/START_TIME.txt")"

echo
echo "[kit] 완료. 다음 순서:"
echo "  1) docs/TIMEBOX.md 에 종료 시각 계산해 적기"
echo "  2) 과제 README 읽고 docs/SUBMIT_CHECK.md 에 필수 파일 옮기기"
echo "  3) docs/QUESTIONS.md 보며 담당자 에이전트에 질문"
echo "  4) codex 실행 후: \$plan-verify 로 계획 작성 시작"
