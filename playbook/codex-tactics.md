# Codex 운용 전술 (응시 환경 기준)

근거: 1차 예선 후기(컨텍스트 3/4 차면 오답 급증, 맥락 2~3턴 유지), 코파톤 후기(압축보다 **명시적 핸드오프**,
모니터링용 세션 분리, 토큰 사용량 간접 평가), 가이드(권장 모델 Sol 6.1/Terra 5.6/Luna 6, 업데이트 금지,
에이전트 응답시간 고려한 위임).

## 0. 사전 체험(2026-10-30)에서 직접 확인한 것
- Codex **v0.163.0**, 상태줄 `GPT-6.1-Sol default · ~` — cwd는 홈(/home/user). 스킬 메커니즘 동작(`openai-docs` 스킬을 스스로 읽음) → `$plan-verify`도 `.agents/skills`에 두면 뜬다. MCP는 `codex_worktrees` 3개뿐, 추가 불가·시도 금지
- **샌드박스**: `python3 -m http.server` → `PermissionError: [Errno 1] Operation not permitted`(소켓 생성 차단). "You approved codex to always run commands that start with …" 식 접두어 승인 후에야 실행. `curl`도 승인 필요, `ss`는 netlink 차단 → 서버·HTTP 확인은 사람이 IDE 터미널에서
- "Failed to open browser … No valid browsers detected" — Codex는 브라우저를 못 연다. 포트 미리보기로 사람이 확인
- "Failed to paste image: clipboard unavailable (X11)" — 이미지 붙여넣기 불가. 프롬프트는 파일 경로로 지시
- 외부 HTTPS 읽기는 됐다(curl로 openai 문서 수신). 그래도 쓰지 않는다 — 필요한 건 kit 안에 있고, 외부 접근은 전부 기록
- GitHub·MCP 연결을 묻자 Codex 응답 끝에 **"git push 및 차단 우회를 통한 무단 외부 반출 금지 … 민·형사상 책임"** 경고문이 플랫폼에 의해 삽입됐다 → 그 주제는 입에 올리지 않는다
- 한 줄 요청("간단한 지뢰찾기 만들어줘")에도 Codex가 테스트까지 알아서 했다 — 즉 결과물 품질이 아니라 **내 지시·검증·판단의 기록**이 변별점이다

## 0-1. 사전 체험 대화에서 고칠 습관 (실전에서 그대로 하면 Intent·Cognition 감점)
| 사전 체험에서 한 것 | 실전에서 할 것 |
|---|---|
| "접속하면 인사말을 보여 주는 간단한 웹 페이지" (목표만) | 목표 + 제약(stdlib, 포트, 파일 위치) + 완료 기준(실행 명령·기대 출력) + 출력 형식 |
| 결과를 읽지 않고 다음 요청 | 핵심 함수 1개는 열어 읽고, "틀릴 수 있는 입력 3개"를 묻고, 1개를 테스트로 |
| 오른쪽 메신저를 한 번도 안 씀 | 첫 15분에 질문 묶음 2회, 합의서 확인 1회, 60/120분 체크인 — 전부 채점 자료 |
| "can you see mcp", "github 접속 방법", "모니터 모니터링 프로그램" | 과제와 무관한 탐색은 0회. 궁금하면 시험 후 |
| 승인 프롬프트에 always 승인 | 서버·네트워크는 거절하고 내가 터미널에서. 파일 쓰기·테스트만 승인 |

## 1. 세션 구조
- **메인 세션 1개**: 구현. `prompts/00-kickoff.md`로 시작 (AGENTS.md 읽기 + 역할 고정)
- **검토 세션 1개** (선택): 메인이 만든 계획/코드를 "모르는 사람" 입장에서 읽게 함 (`prompts/06-presubmit-review.md`). 두 세션이 서로의 출력을 교차 검증 — Cognition 점수
- 컨텍스트가 길어지면(응답이 느려지거나 이전 지시를 잊으면) **새 세션 + 핸드오프 문서** (`prompts/05-handoff.md`). 압축(compaction)에 기대지 않는다

## 2. 프롬프트 순서 (prompts/ 폴더 번호 순)
| 시점 | 파일 | 목적 |
|---|---|---|
| 세션 시작 | 00-kickoff | AGENTS.md·docs 읽기, 역할, 출력 형식 고정 |
| 담당자 인터뷰 | 01-interview-helper | profile 결과로 질문 후보 뽑기 (담당자에겐 내가 직접 보냄) |
| 계획 | 02-plan | PLAN.md 채우기, 승인 전 코드 금지 |
| 구현 반복 | 03-implement | 기능 하나 = 프롬프트 하나 + 실행 확인 + DECISIONS 한 줄 |
| 검증 | 04-verify | 심은 케이스, 경계값, 로그 경로 |
| 세션 교체 | 05-handoff | 상태 요약 → 새 세션 첫 프롬프트 |
| 제출 20분 전 | 06-presubmit-review | README·실행·미구현 목록 교차 검토 |
| 제출 10분 전 | 07-self-critique | 내 코드 약점 Top 5 (서술형 재료) |

## 3. 토큰·시간 절약 규칙 (간접 평가 대상)
- 원본 데이터를 Codex에 **읽히지 않는다**. `profile.to_markdown()` 결과(수십 줄)만 준다
- "파일 전체 보여줘" 대신 "함수 X만", "실패한 테스트 출력 마지막 20줄만"
- 같은 실행을 반복시키지 않는다. 실패 → 원인 가설 → 수정 → 1회 실행
- 긴 작업은 "먼저 계획만 3줄" → 승인 → 실행. 되돌리기가 제일 비싸다
- 에이전트가 도는 동안 나는 DECISIONS/README를 쓴다 (대기 시간을 비우지 않음)

## 4. 지시 품질 (Intent 점수)
좋은 프롬프트의 4요소: **목표 / 제약 / 완료 기준(실행으로 확인 가능) / 출력 형식**
```
목표: 설비별 temp 상한 룰로 판정해 outputs/alerts.csv 를 만든다
제약: stdlib + kitlib만, 입력은 data/sample.csv, 기준은 config/rules.json에서 읽는다
완료 기준: python src/main.py run 이 0으로 끝나고 alerts.csv에 header+N행, tools/run_and_log.sh 로그 있음
출력: 바뀐 파일 목록 + 실행 명령 + 결과 3줄. 설명 생략
```
나쁜 프롬프트: "이상 탐지 시스템 만들어줘", "알아서 개선해줘", "테스트도 추가해줘"(무엇을 검증하는 테스트인지 없음)

## 5. Codex 출력 검증 루틴 (Cognition 점수)
매 기능마다 3가지만:
1. **실행했나**: 로그 파일 경로가 있나 (`tools/run_and_log.sh`)
2. **읽었나**: 핵심 함수 1개는 내가 눈으로 읽고 "왜"를 DECISIONS에 적는다 (서술형에서 설명할 부분)
3. **틀릴 수 있나**: "이 코드가 틀리는 입력 3개만 말해봐" → 그중 1개를 테스트로 (`prompts/04-verify.md`)

## 6. 승인·샌드박스 문제
- 서버 실행에서 승인 프롬프트가 반복되거나 소켓이 막히면 → 15분 넘기지 말고 정적 폴백 (playbook/05)
- Codex 실행 옵션(승인 모드) 변경은 **내가 터미널에서** 한다. Codex에게 시키지 않는다. 가이드의 "Codex 업데이트 금지"는 지킨다
- 네트워크 접근이 막힌 샌드박스에서 pip가 안 되면 stdlib — kitlib은 그래서 stdlib

## 7. 모델 선택 (가이드 권장 Sol 6.1 / Terra 5.6 / Luna 6)
- 계획·검토·약점 분석 = 추론 강한 모델, 반복 구현 = 빠른 모델. 사전 체험 때 `/model`로 바꿀 수 있는지 확인
- 바꿀 수 없으면 신경 쓰지 않는다. 모델보다 프롬프트 4요소가 결과를 좌우

## 8. 스킬
- `$plan-verify`: 계획→최소실행본→검증 루프 강제
- `$decision-log`: "기록해" 한 마디로 DECISIONS 추가
- 스킬이 안 뜨면(`/skills`에 없음) AGENTS.md만으로 충분. 스킬 설치에 시간 쓰지 않는다
