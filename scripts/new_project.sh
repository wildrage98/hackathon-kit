#!/usr/bin/env bash
# new_project.sh — 제출물 뼈대 생성 (과제 루트에서 실행). 이미 있는 파일은 건드리지 않는다.
# 사용: bash tools/new_project.sh [프로젝트명]
set -euo pipefail
NAME="${1:-project}"
mkdir -p src config data outputs tests docs logs
[ -f requirements.txt ] || printf '# stdlib만 사용하면 비워둔다. 추가 시 즉시 기록.\n' > requirements.txt
[ -f .gitignore ] || printf '__pycache__/\n*.pyc\n.venv/\noutputs/*.tmp\n' > .gitignore
if [ ! -f src/main.py ]; then
cat > src/main.py <<'PY'
"""실행 진입점. README의 명령은 전부 이 파일을 가리킨다.
    python src/main.py run      --input data/xxx.csv --out outputs
    python src/main.py validate --input data/xxx.csv
    python src/main.py report
    python src/main.py serve    # 0.0.0.0:$PORT
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # kitlib/ 를 루트에서 import
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
sed -i "s/PROJECT_NAME/${NAME}/" src/main.py
fi
if [ ! -f tests/test_basic.py ]; then
cat > tests/test_basic.py <<'PY'
"""요구사항 1개 = 테스트 1개. 실행: python -m unittest discover -s tests -v  (pytest 없어도 됨)"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestRequirements(unittest.TestCase):
    def test_R1_placeholder(self):
        """R1: (요구사항을 여기에 한 줄로) — 입력 X를 주면 Y가 나온다"""
        self.assertTrue(True)

    def test_boundary_equal_to_limit(self):
        """경계값: 기준값과 정확히 같을 때의 판정을 고정한다 (서술형 단골)"""
        from kitlib.rules import Rule
        r = Rule("hi", "v", hi=10, inclusive=(True, True))
        self.assertIsNone(r.violation({"v": 10}))      # 포함 → 정상
        self.assertIsNotNone(r.violation({"v": 10.0001}))


if __name__ == "__main__":
    unittest.main()
PY
fi
if [ ! -f README.md ]; then
cat > README.md <<MD
# ${NAME}

## 실행 방법
\`\`\`bash
python src/main.py run --input data/input.csv --out outputs
python src/main.py validate --input data/input.csv
python src/main.py serve            # http://0.0.0.0:8000  (PORT 환경변수로 변경)
python -m unittest discover -s tests -v
\`\`\`

## 입력 / 출력
- 입력:
- 출력: outputs/

## 판단 로직 요약 (근거 출력 방식)

## 데이터 품질 처리 정책

## 검증 결과
docs/VERIFICATION.md 참고 (로그: logs/)

## 미구현 · 미검증 · 한계
-
MD
fi
echo "[new_project] 생성 완료: src/main.py tests/test_basic.py README.md config/ data/ outputs/ logs/"
echo "  실행: python src/main.py run && python -m unittest discover -s tests -v"
