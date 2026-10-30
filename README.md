# hackathon-kit

AI 해커톤(Codex 응시 환경) 개인 작업 하네스.
**문제 풀이 코드는 포함하지 않는다.** 절차·양식·검증 도구·stdlib 전용 빌딩블록·유형별 플레이북만 담는다.
쓴 모듈은 `docs/DECISIONS.md`에 출처를 적고, 서술형에서 설명할 수 있는 만큼만 쓴다.

## 응시 환경에서 (한 줄)

```bash
git clone https://github.com/wildrage98/hackathon-kit.git && bash hackathon-kit/setup.sh
```

setup.sh가 하는 일
1. `AGENTS.md` → 작업 폴더 루트 (Codex가 자동으로 읽음)
2. `skills/` → `~/.codex/skills`, `.agents/skills`, `.codex/skills` (`$plan-verify`, `$decision-log`)
3. `kitlib/` → 작업 폴더 루트 (stdlib 전용 모듈 18개, `from kitlib import rules` 로 사용)
4. `templates/` → `./docs/` (TIMEBOX / QUESTIONS / AGREEMENT / PLAN / DECISIONS / VERIFICATION / SUBMIT_CHECK)
5. `scripts/` → `./tools/` (run_and_log.sh, smoke.sh, new_project.sh, preflight.py, profile_csv.py)

사전 체험(15분)에서 할 것: 위 명령 → `python tools/preflight.py env` → `codex` 에서 `/skills` 에 plan-verify가 보이는지.

## 어떤 상황에 무엇을 쓰나 → [playbook/README.md](playbook/README.md)

| 과제 단서 | 유형 | 핵심 모듈 | 플레이북 |
|---|---|---|---|
| 센서·시계열·이상 징후·경보 | A 센서 이상 탐지 | rules, stats_detect, alerts | [01](playbook/01-sensor-anomaly.md) |
| 불량률·수율·원인·요인 | B 수율 요인 분석 | groupstats | [02](playbook/02-yield-rootcause.md) |
| 판정·적합/부적합·규정·스펙 | C 규칙 기반 판정 | rules | [03](playbook/03-rule-verdict.md) |
| 로그·알람 이력·텍스트·집계 | D 로그 파싱·리포트 | logparse, report | [04](playbook/04-log-report.md) |
| 화면·대시보드·운영자 | E 대시보드 (보조) | webapp, svgchart | [05](playbook/05-dashboard.md) |
| 배정·순서·납기·가동률 | F 스케줄링 | schedule | [06](playbook/06-scheduling.md) |
| 두 자료 비교·정합성·누락 | G 데이터 대사 | reconcile | [07](playbook/07-data-reconcile.md) |
| 관리도·Cpk·관리한계 | H SPC (보조) | spc | [08](playbook/08-spc.md) |

공통: [담당자 인터뷰](playbook/stakeholder-interview.md) · [서술형 대비](playbook/essay-prep.md) · [Codex 전술](playbook/codex-tactics.md) · [Codex 프롬프트 00~07](prompts/)

## 구성

```
AGENTS.md            Codex 행동 규칙 (계획 먼저, 최소 실행본, stdlib 우선, 0.0.0.0, 로그 없는 통과 금지, 결정 기록)
setup.sh             설치
kitlib/              stdlib 전용 빌딩블록 (Python 3.8+, 외부 의존성 0)
  csvio timeparse quality profile            읽기·품질
  rules stats_detect alerts spc              판정·탐지·경보
  groupstats schedule logparse reconcile     요인분석·스케줄·로그·대사
  report svgchart webapp cli                 출력·대시보드·CLI
  synth evalmetrics                          합성데이터·검증지표
playbook/            유형별(01~08) + 인터뷰·서술형·Codex 전술
prompts/             Codex 단계별 프롬프트 (kickoff → plan → implement → verify → handoff → review → self-critique)
examples/            모듈 배선 예시 2개 (sensor_pipeline, yield_rootcause) — 읽고 적용, 복사 금지
templates/           docs/ 양식 7개
scripts/             preflight(환경·제출 점검, exit 2=미점검), profile_csv, new_project(뼈대), run_and_log, smoke
skills/              plan-verify, decision-log
tests/               kitlib 회귀 테스트 27개 (python -m unittest discover -s tests)
```

## kitlib 10초 사용법

```python
from kitlib import csvio, timeparse, quality, rules, alerts, report
rows, meta = csvio.read_csv("data/x.csv")                       # cp949/utf-8-sig, 구분자 자동
timeparse.add_parsed_time(rows, "timestamp")                    # 'Z', '+09:00', epoch 전부 OK
q = quality.check_quality(rows, key_cols=["equipment"], value_cols=["temp"])
clean, log = quality.apply_policy(rows, q["issues"], key_cols=["equipment"], value_cols=["temp"])
rules.evaluate_series(clean, [rules.Rule("temp_hi", "temp", hi=70, when={"state": "RUN"}, min_consecutive=2)], key_cols=["equipment"])
am = alerts.run_from_levels(clean, ["equipment"], close_after=6)
report.Report("리포트").table(am.to_rows()).save_html("outputs/report.html")
```
검증: `python -m kitlib.synth --out data/synth.csv` → 정답 포함 데이터 → `kitlib.evalmetrics.event_prf(...)`

## 조사 근거 (2026-10-30)
- 플랫폼 Cofa-Probe: 브라우저 IDE(탐색기·에디터·bash·실무자 AI 채팅), 대화·터미널·git·테스트 자동 수집, 평가 3축 Technique/Intent/Cognition, 후속 질문 채점 = 약점 지목→영향→검증·개선안
- 1차 예선 유형: 불량 원인 분석, 조건별 분류·판정, SCM/CRM/BI 데이터 분석, 자료 비교, 사무행정 처리
- 2차 모의: 설비 센서 이상 탐지 + 판단 근거 + 대시보드
- 환경 위험: pip 불확실, 서버 소켓 차단 사례, 외부 CDN 차단, Codex 버전 고정
출처 목록은 playbook/README.md 머리말과 docs 참고.

## 규칙 (대회 규정)
- 이 저장소는 결과 통지 전까지 Public 유지
- 과제 완성 코드를 넣지 않는다 (결과물 통째 대체 금지). 예시는 합성 데이터용 배선 참고
- Codex 버전 업데이트 금지 — 설치 스크립트는 codex 를 건드리지 않는다
- 시험 중 git push·외부 전송 금지 — 이 저장소는 clone만 한다
