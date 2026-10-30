#!/usr/bin/env bash
# hackathon-kit 설치: 작업 루트에서 실행
# 사용: bash hackathon-kit/setup.sh
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

echo "[kit] 작업 루트: $ROOT"
if [ "$ROOT" = "$HOME" ]; then
  echo "[kit] 작업 루트가 홈 디렉터리 — 커밋은 경로 지정(git add <폴더> docs logs), git add -A 금지"
fi

# 1. AGENTS.md — 기존 파일이 있으면 보존하고 뒤에 덧붙인다
if [ -f "$ROOT/AGENTS.md" ]; then
  if grep -q "hackathon-kit 추가 규칙" "$ROOT/AGENTS.md"; then
    echo "[kit] AGENTS.md 에 kit 규칙이 이미 병합되어 있음 — 건너뜀"
  else
    cp "$ROOT/AGENTS.md" "$ROOT/AGENTS.md.orig"
    {
      printf '\n\n---\n## (아래는 hackathon-kit 추가 규칙 — 위의 과제 지시와 충돌하면 과제 지시가 우선)\n\n'
      cat "$KIT/AGENTS.md"
    } >> "$ROOT/AGENTS.md"
    echo "[kit] 기존 AGENTS.md 보존(AGENTS.md.orig) + kit 규칙을 끝에 병합"
  fi
else
  cp "$KIT/AGENTS.md" "$ROOT/AGENTS.md"
  echo "[kit] AGENTS.md 설치"
fi

# 2. 스킬 — 세 위치 모두 (기존 다른 스킬은 유지)
for dest in "$CODEX_HOME/skills" "$ROOT/.agents/skills" "$ROOT/.codex/skills"; do
  mkdir -p "$dest"
  for d in "$KIT"/skills/*/; do
    name="$(basename "$d")"
    rm -rf "$dest/$name"
    cp -r "$d" "$dest/$name"
  done
done
echo "[kit] skills 설치: \$plan-verify \$decision-log → ~/.codex/skills, .agents/skills, .codex/skills"

# 3. kitlib (stdlib 전용 모듈) → 작업 루트. new_project.sh 가 프로젝트 폴더로 다시 복사한다
if [ -d "$ROOT/kitlib" ]; then
  echo "[kit] kitlib/ 이미 있음 — 건너뜀 (갱신하려면 rm -rf kitlib 후 재실행)"
else
  cp -r "$KIT/kitlib" "$ROOT/kitlib"
  find "$ROOT/kitlib" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
  printf 'kitlib — 출처: https://github.com/wildrage98/hackathon-kit (공개 저장소, MIT)\n설치 시각: %s\n사용한 모듈과 수정 내용은 docs/DECISIONS.md 에 기록한다.\n' "$(date '+%Y-%m-%d %H:%M:%S')" > "$ROOT/kitlib/SOURCE.md"
  echo "[kit] kitlib/ 설치 (stdlib only, $(ls "$ROOT"/kitlib/*.py | grep -vc __init__ | tr -d ' ')개 모듈)"
fi

# 4. 문서 양식 (있는 파일은 건드리지 않음)
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

# 6. .gitignore — kit 폴더·캐시는 커밋에서 제외. 작업 루트가 홈이면 도구 상태/캐시 폴더도 제외
GI="$ROOT/.gitignore"
touch "$GI"
add_ignore() { grep -qxF "$1" "$GI" || echo "$1" >> "$GI"; }
add_ignore "# --- hackathon-kit ---"
add_ignore "hackathon-kit/"
add_ignore "__pycache__/"
add_ignore "*.pyc"
if [ "$ROOT" = "$HOME" ]; then
  for p in .npm/ .cache/ .aws/ .config/ .literacy/ .claude/ .claude.json .codex/ .bash_history .sudo_as_admin_successful .local/ .pki/; do
    add_ignore "$p"
  done
fi
echo "[kit] .gitignore 갱신 (hackathon-kit/, 캐시$( [ "$ROOT" = "$HOME" ] && echo ', 홈의 도구 상태 폴더'))"

# 7. git — 저장소면 커밋 가능하도록 신원 확인 (없을 때만 로컬 설정)
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ -z "$(git -C "$ROOT" config user.email || true)" ]; then
    git -C "$ROOT" config user.name "${USER:-candidate}"
    git -C "$ROOT" config user.email "${USER:-candidate}@local"
    echo "[kit] git 신원 없음 → 로컬 설정: $(git -C "$ROOT" config user.name) <$(git -C "$ROOT" config user.email)> (바꾸려면 git config user.name/email)"
  else
    echo "[kit] git 신원: $(git -C "$ROOT" config user.name) <$(git -C "$ROOT" config user.email)>"
  fi
else
  echo "[kit] git 저장소 아님 — 커밋 이력이 평가 자료이므로 'git init' 권장"
fi

# 8. 시작 시각 기록
date '+%Y-%m-%d %H:%M:%S' > "$ROOT/docs/START_TIME.txt"
echo "[kit] 시작 시각 기록: $(cat "$ROOT/docs/START_TIME.txt")"

echo
echo "[kit] 완료. 다음: hackathon-kit/EXAM-DAY.md"
