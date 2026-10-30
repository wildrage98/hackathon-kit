#!/usr/bin/env bash
# new_project.sh — 제출물 뼈대를 **하위 폴더**에 생성 (작업 루트에서 실행). 이미 있는 파일은 건드리지 않는다.
# 사용: bash tools/new_project.sh <이름>        예: bash tools/new_project.sh sensor-monitor
# 결과: <이름>/{src/main.py, tests/test_basic.py, README.md, requirements.txt, .gitignore, kitlib/, config, data, outputs, logs}
set -euo pipefail
NAME="${1:-project}"
ROOT="$(pwd)"
P="$ROOT/$NAME"
mkdir -p "$P"/{src,config,data,outputs,tests,logs}

# kitlib 복사 (작업 루트의 kitlib → 프로젝트 안). 프로젝트 폴더가 자급자족하도록.
if [ ! -d "$P/kitlib" ]; then
  if [ -d "$ROOT/kitlib" ]; then
    cp -r "$ROOT/kitlib" "$P/kitlib"
  elif [ -d "$ROOT/hackathon-kit/kitlib" ]; then
    cp -r "$ROOT/hackathon-kit/kitlib" "$P/kitlib"
    printf 'kitlib — 출처: https://github.com/wildrage98/hackathon-kit (공개 저장소, MIT)\n사용한 모듈과 수정 내용은 docs/DECISIONS.md 에 기록한다.\n' > "$P/kitlib/SOURCE.md"
  else
    echo "[new_project] 경고: kitlib 을 찾지 못함 (setup.sh 먼저 실행)" >&2
  fi
  find "$P/kitlib" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
fi

[ -f "$P/requirements.txt" ] || printf '# stdlib만 사용하면 비워둔다. 추가 시 즉시 기록.\n' > "$P/requirements.txt"
[ -f "$P/.gitignore" ] || printf '__pycache__/\n*.pyc\n.venv/\noutputs/*.tmp\n' > "$P/.gitignore"

if [ ! -f "$P/src/main.py" ]; then
cat > "$P/src/main.py" <<'PY'
"""실행 진입점. README의 명령은 전부 이 파일을 가리킨다. (프로젝트 폴더에서 실행)
    python3 src/main.py run      --input data/xxx.csv --out outputs
    python3 src/main.py validate --input data/xxx.csv
    python3 src/main.py report
    python3 src/main.py serve    # 0.0.0.0:$PORT (터미널에서 직접 실행)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # 프로젝트 폴더의 kitlib/
from kitlib.cli import App  # noqa: E402

app = App("PROJECT_NAME")


@app.command("run", help="입력 → 분석 → outputs/")
def run(args, log):
    log.info("TODO: load → quality → analyze → write outputs")
    return 0


@app.command("validate", help="검증: 심은 케이스/정답 대비 결과")
def validate(args, log):
    log.info("TODO: evalmetrics 로 숫자 남기기")
    return 0


@app.command("report", help="리포트 생성 (md/html)")
def report(args, log):
    log.info("TODO: kitlib.report.Report")
    return 0


@app.command("serve", help="대시보드 0.0.0.0:$PORT (실패 시 정적 폴백)")
def serve(args, log):
    log.info("TODO: kitlib.webapp.serve / dashboard_fallback")
    return 0


for c in ("run", "validate"):
    app.add_argument(c, "--input", default="data/input.csv")
app.add_argument("run", "--out", default="outputs")
app.add_argument("serve", "--port", type=int, default=None)

if __name__ == "__main__":
    sys.exit(app.main())
PY
sed -i "s/PROJECT_NAME/${NAME}/" "$P/src/main.py"
fi

if [ ! -f "$P/tests/test_basic.py" ]; then
cat > "$P/tests/test_basic.py" <<'PY'
"""요구사항 1개 = 테스트 1개. 실행(프로젝트 폴더에서): python3 -m unittest discover -s tests -v  (pytest 없어도 됨)"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


class TestRequirements(unittest.TestCase):
    def test_R1_placeholder(self):
        """R1: (요구사항을 여기에 한 줄로) — 입력 X를 주면 Y가 나온다"""
        self.assertTrue(True)

    def test_boundary_equal_to_limit(self):
        """경계값: 기준값과 정확히 같을 때의 판정을 고정한다"""
        from kitlib.rules import Rule
        r = Rule("hi", "v", hi=10, inclusive=(True, True))
        self.assertIsNone(r.violation({"v": 10}))      # 포함 → 정상
        self.assertIsNotNone(r.violation({"v": 10.0001}))


if __name__ == "__main__":
    unittest.main()
PY
fi

if [ ! -f "$P/README.md" ]; then
cat > "$P/README.md" <<MD
# ${NAME}

## 실행 방법
\`\`\`bash
cd ${NAME}
python3 src/main.py run --input data/input.csv --out outputs
python3 src/main.py validate --input data/input.csv
PORT=3000 python3 src/main.py serve      # http://0.0.0.0:3000 (IDE 포트 미리보기로 확인)
python3 -m unittest discover -s tests -v
\`\`\`
외부 패키지 없음 (표준 라이브러리 + kitlib/). kitlib 출처: kitlib/SOURCE.md

## 입력 / 출력
- 입력:
- 출력: outputs/

## 판단 로직 요약 (근거 출력 방식)

## 데이터 품질 처리 정책

## 검증 결과
../docs/VERIFICATION.md 참고 (로그: logs/, ../logs/)

## 미구현 · 미검증 · 한계
-
MD
fi

echo "[new_project] 생성: ${NAME}/ (src/main.py tests/test_basic.py README.md kitlib/ config data outputs logs)"
echo "  실행 확인: cd ${NAME} && python3 src/main.py run && python3 -m unittest discover -s tests -v"
echo "  제출 점검: python3 tools/preflight.py submit --project ${NAME}   (작업 루트에서)"
