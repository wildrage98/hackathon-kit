# PLAYBOOK — 어떤 상황에 무엇을 쓰나

> 조사 근거: 1차 예선 출제 유형(불량 원인 분석·조건별 판정·SCM/CRM 데이터 분석·자료 비교·사무행정),
> 2차 모의시험(설비 센서 이상 탐지 + 대시보드), Cofa-Probe 평가 3축(Technique/Intent/Cognition),
> 7월 코파톤 참가 후기(합의서 요구, 후속질문 = 약점→영향→개선안). 공식 기출이 아니므로 **구조만 믿고 내용은 현장에서 확인**한다.

## 0. 30초 유형 판별

과제 README·담당자 첫 메시지에서 아래 단어를 찾는다. 둘 이상 겹치면 "주 유형 + 보조 유형"으로 본다.

| 단서 (README/담당자 말) | 유형 | 플레이북 |
|---|---|---|
| 센서, 시계열, 설비 상태, 이상 징후, 경보, 임계치, 모니터링 | **A. 센서 이상 탐지/모니터링** | [01](01-sensor-anomaly.md) |
| 불량률, 수율, 원인, 로트/웨이퍼, 어느 설비에서, 요인 | **B. 불량·수율 요인 분석** | [02](02-yield-rootcause.md) |
| 판정, 적합/부적합, 출하 가능, 규정 위반, 스펙 in/out, 등급 분류, 체크리스트 | **C. 규칙 기반 판정/검사 자동화** | [03](03-rule-verdict.md) |
| 로그, 알람 이력, 에러 코드, 정비 메모, 텍스트, 집계 리포트 | **D. 로그/텍스트 파싱·집계** | [04](04-log-report.md) |
| 화면, 대시보드, 운영자가 본다, 조회, 시각화 | **E. 대시보드/리포트** (대부분 다른 유형의 보조) | [05](05-dashboard.md) |
| 배정, 순서, 일정, 납기, 우선순위, 설비 가동률, 정비 계획 | **F. 스케줄링/디스패칭** | [06](06-scheduling.md) |
| 두 자료 비교, 정합성, 불일치 찾기, 마스터 대조, 중복 | **G. 데이터 정합성/대사** | [07](07-data-reconcile.md) |
| 관리도, SPC, Cpk, 공정능력, 관리한계 | **H. SPC/공정 능력** (A·B의 보조) | [08](08-spc.md) |

판별이 안 되면: 담당자에게 "최종 사용자가 **화면에서 매일 보는 것**인가, **한 번 분석해서 보고하는 것**인가, **자동으로 판정해 주는 것**인가"를 묻는다. 답이 각각 E, B/D, C다.

## 1. 모든 유형 공통 순서 (시간표는 docs/TIMEBOX.md)

```
0-15분   clone+setup → tools/preflight.py env → README 정독 → 오른쪽 메신저로 담당자 인터뷰 (playbook/stakeholder-interview.md)
15-30분  합의서(docs/AGREEMENT.md) 담당자 확인 → Codex 시작(prompts/00) → PLAN.md → $plan-verify → tools/new_project.sh <이름>
30-60분  최소 실행본: 입력 읽기(csvio) → 핵심 로직 1개 → 결과 파일. 반드시 돌아가게. (프로젝트는 하위 폴더, 명령 순서는 EXAM-DAY.md)
60-100분 기능 추가 (한 번에 하나, 실행 확인, DECISIONS 한 줄)
100분    체크포인트: 지금 제출 가능? 아니면 범위 축소 (TIMEBOX 우선순위)
100-130  보조 유형(대시보드/리포트), 품질 처리
130-155  검증: synth/evalmetrics 또는 손으로 만든 케이스 → VERIFICATION.md (로그 경로!)
155-170  README, DECISIONS 정리, prompts/07-self-critique.md 로 약점 목록 뽑기
170-180  tools/preflight.py submit → 제출
```

## 2. 유형 × kitlib 모듈 매트릭스

| 단계 | A 센서 | B 수율 | C 판정 | D 로그 | E 대시보드 | F 스케줄 | G 대사 | H SPC |
|---|---|---|---|---|---|---|---|---|
| 읽기 | csvio, timeparse | csvio | csvio | logparse | - | csvio | csvio | csvio |
| 파악 | profile | profile | profile | aggregate | - | profile | profile | profile |
| 품질 | quality | quality | quality | unmatched 보고 | - | quality | quality(duplicate) | quality |
| 핵심 | rules, stats_detect | groupstats | rules | classify_text | - | schedule | (G 플레이북의 diff 함수) | spc |
| 이력 | alerts | - | - | context_window | - | - | - | - |
| 출력 | report, svgchart | report, svgchart | report | report | webapp, svgchart | report(gantt) | report | report, svgchart |
| 검증 | synth, evalmetrics | 심은 요인 | 경계값 테스트 | unmatched 비율 | /health, 스크린샷 | compare_rules | 심은 불일치 | 심은 이탈 |

## 3. 상황별 대처 (문제가 생겼을 때)

| 상황 | 대처 |
|---|---|
| pip install이 안 됨 | kitlib은 stdlib 전용. pandas 없이 간다. requirements.txt 비워둔다. preflight가 알려줌 |
| Codex가 서버/curl 실행 시 PermissionError·승인 반복 (사전 체험에서 실제 발생) | Codex 샌드박스가 소켓을 막는다. 서버·curl은 **내가 IDE 터미널 탭에서** 실행하고 Codex에겐 결과 파일(outputs/)로 검증시킨다. 승인을 주더라도 "always run commands that start with python3 src/main.py" 처럼 접두어 한정 |
| 터미널에서도 서버가 안 뜸 | `webapp.serve()`가 False → `dashboard_fallback()`으로 정적 HTML 저장, README에 "파일로 열기" 명시. 15분 이상 씨름 금지 |
| Codex가 브라우저를 못 엶 ("No valid browsers detected") | 정상. 웹 IDE의 포트 미리보기(3000 등) 또는 원격 데스크톱 Chromium으로 내가 확인 |
| 붙여넣기가 안 됨 (이미지는 확실히 불가) | 프롬프트는 `hackathon-kit/prompts/0N-*.md 를 읽고 수행해` 로 지시. 스크린샷 대신 텍스트로 설명 |
| 과제 README가 루트에 있고 루트가 git 저장소(홈) | 루트 파일 수정 X. `tools/new_project.sh <이름>` 하위 폴더에 작업. 커밋은 `git add <이름> docs logs` (−A 금지) |
| 외부 CDN 안 됨 (차트 안 그려짐) | svgchart로 inline SVG. JS 라이브러리 금지 |
| 담당자가 기준(정상 범위)을 안 줌 | `stats_detect.iqr_bounds`로 **제안**해서 확정받는다. "제가 정상 구간 데이터로 이렇게 잡겠습니다. 괜찮습니까?" 대화 기록이 점수 |
| 샘플 데이터가 없음/적음 | `python -m kitlib.synth` 로 합성 + 정답. 담당자에게 스키마만 확인. 합성 성능≠실제 성능 명시 |
| 데이터가 큼(수십만 행) | profile은 sample=20000. 처리는 키별로 나눠서. 시간 재서 README에 적기 |
| Codex가 같은 걸 반복/헛돎 | 세션 새로 열고 prompts/05-handoff.md 로 넘긴다. 컨텍스트 3/4 차면 품질 급락(1차 후기) |
| 시간 부족 (100분 체크포인트) | TIMEBOX 축소 순서: 대시보드→콘솔+CSV, 부가 기능, 품질 케이스 일부 "정책만 문서화" |
| 테스트 짤 시간 없음 | 최소 1개: 경계값(기준과 같을 때) 테스트. tests/test_basic.py 에 이미 있음 |
| 요구사항이 서로 모순 | 담당자에게 둘 중 뭐가 우선인지 묻고, 답을 AGREEMENT.md에 적는다. 추측 금지 |
| 담당자 에이전트 응답이 느림 | 질문을 한 번에 3~5개 묶어 보낸다. 기다리는 동안 preflight/scaffold 진행 |
| 담당자 채널이 어디인지 모르겠음 | 오른쪽 메신저(사전 체험의 "Cofa Helper 과제 도우미" 자리). Enter=전송, Shift+Enter=줄바꿈. 코드는 안 짜주고 질문·설명·리뷰만 — 그게 Intent 채점 자료 |
| GitHub·MCP·외부 연결이 궁금함 | 묻지 않는다. 사전 체험에서 언급만으로 반출 금지 경고문이 Codex 응답에 삽입됐다(기록 남음). 필요한 건 전부 hackathon-kit 안에 있다 |

## 4. 절대 하지 말 것 (평가 축 기준)

- **Technique**: 실행 안 되는 제출. 경로 하드코딩. 0.0.0.0 아닌 127.0.0.1 바인딩. 비밀키.
- **Intent**: 질문 없이 추측으로 기준 확정. 계획 없이 코딩. "다 만들어줘" 한 방 프롬프트.
- **Cognition**: Codex 출력을 안 읽고 다음으로. "테스트 통과"라고 썼는데 로그 없음. 약점을 모름.
- 외부 자료로 결과물 통째 대체. kitlib도 **쓴 모듈만, 출처 명시, 설명 가능한 만큼만**.

## 5. 파일 지도

```
EXAM-DAY.md                  시험 당일 순서표 (환경 사실 + 명령 그대로) ← 09:55에 이것부터
playbook/
  README.md                  ← 지금 이 문서
  stakeholder-interview.md   담당자 에이전트 인터뷰 순서·질문 묶음·합의서 쓰는 법
  essay-prep.md              후속 서술형 6문항 대비: 답변 프레임 + 예상 질문 30개
  codex-tactics.md           Codex 운용: 프롬프트 순서, 컨텍스트 관리, 토큰 절약, 승인/샌드박스
  01-sensor-anomaly.md … 08-spc.md   유형별 상세
prompts/                     Codex에 붙여넣는 단계별 프롬프트 (00~07)
examples/                    모듈을 엮는 배선 예시 2개 (복사 금지, 읽고 적용)
kitlib/                      stdlib 전용 모듈 18개 (각 파일 머리말에 "언제 쓰나")
```
