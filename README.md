# hackathon-kit

개인 작업 하네스. 문제 풀이 코드 없음 — 절차 양식, 점검 도구, stdlib 전용 빌딩블록, 체크리스트.

```bash
git clone https://github.com/wildrage98/hackathon-kit.git && bash hackathon-kit/setup.sh
python3 tools/preflight.py env
bash tools/new_project.sh <이름>
```

```
EXAM-DAY.md          순서표
AGENTS.md            에이전트 작업 규칙
setup.sh             설치 (AGENTS.md, skills/, kitlib/, templates→docs/, scripts→tools/, .gitignore)
kitlib/              stdlib 전용 모듈 18개 (각 파일 머리말에 API)
playbook/            유형별 체크리스트 01~08, 인터뷰, 질문 목록, 에이전트 운용
prompts/             단계별 프롬프트 00~07
examples/            배선 예시 2개 (참고용)
templates/           docs/ 양식 7개
scripts/             preflight, profile_csv, new_project, run_and_log, smoke
skills/              plan-verify, decision-log
tests/               kitlib 테스트 27개 (python -m unittest discover -s tests)
```

```python
from kitlib import csvio, timeparse, quality, rules, alerts, report
rows, meta = csvio.read_csv("data/x.csv")
timeparse.add_parsed_time(rows, "timestamp")
q = quality.check_quality(rows, key_cols=["equipment"], value_cols=["temp"])
clean, log = quality.apply_policy(rows, q["issues"], key_cols=["equipment"], value_cols=["temp"])
rules.evaluate_series(clean, [rules.Rule("temp_hi", "temp", hi=70, when={"state": "RUN"}, min_consecutive=2)], key_cols=["equipment"])
am = alerts.run_from_levels(clean, ["equipment"], close_after=6)
report.Report("리포트").table(am.to_rows()).save_html("outputs/report.html")
```

- 공개 유지. 완성 코드 없음. clone만 한다 (push·외부 전송 없음).
- MIT
