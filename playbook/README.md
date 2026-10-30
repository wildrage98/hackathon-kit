# PLAYBOOK

## 0. 유형 판별

| 단서 | 유형 | 파일 |
|---|---|---|
| 센서, 시계열, 설비 상태, 이상 징후, 경보, 임계치, 모니터링 | A | [01](01-sensor-anomaly.md) |
| 불량률, 수율, 원인, 로트/웨이퍼, 어느 설비, 요인 | B | [02](02-yield-rootcause.md) |
| 판정, 적합/부적합, 출하, 규정, 스펙 in/out, 등급, 체크리스트 | C | [03](03-rule-verdict.md) |
| 로그, 알람 이력, 에러 코드, 메모, 텍스트, 집계 | D | [04](04-log-report.md) |
| 화면, 대시보드, 조회, 시각화 (보조) | E | [05](05-dashboard.md) |
| 배정, 순서, 일정, 납기, 우선순위, 가동률 | F | [06](06-scheduling.md) |
| 두 자료 비교, 정합성, 불일치, 마스터 대조, 중복 | G | [07](07-data-reconcile.md) |
| 관리도, SPC, Cpk, 관리한계 (보조) | H | [08](08-spc.md) |

판별 안 되면 질문: 매일 화면에서 보는 것 / 한 번 분석해 보고하는 것 / 자동 판정 → E / B·D / C

## 1. 공통 순서 (TIMEBOX)

```
0-15     clone+setup → preflight env → README → 메신저 질문 1차 (stakeholder-interview §1)
15-30    질문 2차 → AGREEMENT 확인 → 에이전트 시작(prompts/00) → PLAN → $plan-verify → new_project.sh <이름>
30-60    최소 실행본: 읽기 → 핵심 로직 1개 → 결과 파일
60-100   기능 추가 (하나씩, 실행 확인, DECISIONS 1줄)
100      체크포인트: 제출 가능? 아니면 축소
100-130  보조(화면/리포트), 품질 처리
130-155  검증: synth/evalmetrics 또는 손 케이스 → VERIFICATION (로그 경로)
155-170  README, DECISIONS, prompts/07
170-180  preflight submit → 제출
```

## 2. 유형 × 모듈

| 단계 | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|
| 읽기 | csvio, timeparse | csvio | csvio | logparse | - | csvio | csvio | csvio |
| 파악 | profile | profile | profile | aggregate | - | profile | profile | profile |
| 품질 | quality | quality | quality | unmatched | - | quality | quality | quality |
| 핵심 | rules, stats_detect | groupstats | rules | classify_text | - | schedule | reconcile | spc |
| 이력 | alerts | - | - | context_window | - | - | - | - |
| 출력 | report, svgchart | report, svgchart | report | report | webapp, svgchart | report | report | report, svgchart |
| 검증 | synth, evalmetrics | 심은 요인 | 경계값 | unmatched 비율 | /health | compare_rules | 심은 불일치 | 심은 이탈 |

## 3. 상황별

| 상황 | 대처 |
|---|---|
| pip 불가 | stdlib + kitlib. requirements.txt 비움 |
| 에이전트가 서버/curl에서 PermissionError·승인 반복 | 서버·curl은 내가 터미널에서. 에이전트는 결과 파일로 검증 |
| 터미널에서도 서버 불가 | `webapp.dashboard_fallback` → 정적 HTML. README에 "파일로 열기". 15분 한도 |
| 브라우저 못 엶 | 포트 미리보기 |
| 붙여넣기 불안정 | `hackathon-kit/prompts/0N-*.md 를 읽고 수행해` |
| 루트 = 홈 = git 저장소 | 루트 파일 수정 X. `new_project.sh <이름>`. `git add <이름> docs logs tools` |
| CDN 불가 | svgchart inline SVG |
| 기준 없음 | `stats_detect.iqr_bounds` → 제안 → 확정 (stakeholder-interview §3) |
| 데이터 없음/적음 | `python -m kitlib.synth`. 스키마만 확인. 합성≠실제 명시 |
| 데이터 큼 | profile sample=20000. 키별 분할. 시간 측정 기록 |
| 에이전트 반복/헛돎 | 새 세션 + prompts/05 |
| 시간 부족 | TIMEBOX 축소 순서 |
| 테스트 시간 없음 | 경계값 1개 (tests/test_basic.py) |
| 요구 모순 | 우선순위 질문 → AGREEMENT |
| 답 느림 | 3~5개 묶음. 대기 중 preflight/scaffold |
| 메신저 사용 | Enter 전송, Shift+Enter 줄바꿈. 질문·설명·리뷰 전용 |
| 외부 연결 | 묻지 않음 |

## 4. 금지

- 실행 안 되는 제출, 경로 하드코딩, 127.0.0.1 바인딩, 비밀키
- 질문 없이 기준 확정, 계획 없이 코딩, 한 줄 지시
- 출력 안 읽고 다음, 로그 없는 "통과", 약점 모름
- 외부 자료로 결과물 통째 대체. 쓴 모듈만, 출처 기록

## 5. 파일

```
EXAM-DAY.md
playbook/README.md  stakeholder-interview.md  essay-prep.md  codex-tactics.md  01~08
prompts/00~07
examples/  kitlib/
```
