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
  echo "[kit] AGENTS.md 가 이미 있어 AGENTS.kit.md 로 복사함 — 기존 파일 끝에 'cat AGENTS.kit.md >> AGENTS.md' 로 병합"
else
  cp "$KIT/AGENTS.md" "$ROOT/AGENTS.md"
  echo "[kit] AGENTS.md 설치"
fi

# 2. 스킬 — Codex 버전에 따라 위치가 달라서 세 곳 모두에 넣는다
for dest in "$CODEX_HOME/skills" "$ROOT/.agents/skills" "$ROOT/.codex/skills"; do
  mkdir -p "$dest"
  for d in "$KIT"/skills/*/; do
    name="$(basename "$d")"
    rm -rf "$dest/$name"
    cp -r "$d" "$dest/$name"
  done
done
echo "[kit] skills 설치: \$plan-verify \$decision-log → ~/.codex/skills, .agents/skills, .codex/skills"

# 3. kitlib (stdlib 전용 모듈) → 프로젝트 루트. 제출물에 포함되므로 출처 파일을 같이 둔다
if [ -d "$ROOT/kitlib" ]; then
  echo "[kit] kitlib/ 이미 있음 — 건너뜀 (갱신하려면 rm -rf kitlib 후 재실행)"
else
  cp -r "$KIT/kitlib" "$ROOT/kitlib"
  find "$ROOT/kitlib" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
  printf 'kitlib — 출처: https://github.com/wildrage98/hackathon-kit (공개 저장소, MIT)\n설치 시각: %s\n사용한 모듈과 수정 내용은 docs/DECISIONS.md 에 기록한다.\n' "$(date '+%Y-%m-%d %H:%M:%S')" > "$ROOT/kitlib/SOURCE.md"
  echo "[kit] kitlib/ 설치 (stdlib only, $(ls "$ROOT"/kitlib/*.py | grep -vc __init__ | tr -d ' ')개 모듈)"
fi

# 4. 문서 양식
mkdir -p "$ROOT/docs" "$ROOT/logs"
for f in "$KIT"/templates/*.md; do
  base="$(basename "$f")"
  if [ ! -f "$ROOT/docs/$base" ]; then
    cp "$f" "$ROOT/docs/$base"
  fi
done
echo "[kit] docs/ 양식 설치 (TIMEBOX, QUESTIONS, AGREEMENT, PLAN, DECISIONS, VERIFICATION, SUBMIT_CHECK)"

# 5. 도구
mkdir -p "$ROOT/tools"
cp "$KIT"/scripts/*.sh "$KIT"/scripts/*.py "$ROOT/tools/"
chmod +x "$ROOT/tools/"*.sh "$ROOT/tools/"*.py
echo "[kit] tools/ 설치 (run_and_log.sh, smoke.sh, new_project.sh, preflight.py, profile_csv.py)"

# 6. 시작 시각 기록
date '+%Y-%m-%d %H:%M:%S' > "$ROOT/docs/START_TIME.txt"
echo "[kit] 시작 시각 기록: $(cat "$ROOT/docs/START_TIME.txt")"

echo
echo "[kit] 완료. 다음 순서:"
echo "  1) python tools/preflight.py env        # 환경 확인 (소켓/pip/파이썬)"
echo "  2) docs/TIMEBOX.md 에 종료 시각 적기"
echo "  3) 과제 README 정독 → docs/SUBMIT_CHECK.md 에 필수 파일 → playbook/README.md 로 유형 판별"
echo "  4) 담당자 인터뷰 (hackathon-kit/playbook/stakeholder-interview.md) → docs/AGREEMENT.md"
echo "  5) codex → prompts/00-kickoff.md 붙여넣기 → \$plan-verify"
echo "  6) 뼈대 필요하면: bash tools/new_project.sh <이름>"
