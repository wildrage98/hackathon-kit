# EXAM-DAY — 시험 당일 순서 (사전 체험 2026-10-30 에서 확인한 환경 기준)

## 확인된 환경 (본 시험도 "동일한 환경·도구")
| 항목 | 사실 | 대응 |
|---|---|---|
| 작업 루트 | `/home/user` = 홈 = **git 저장소(이미 init)**, 과제 `README.md`/`README.en.md`가 루트, `uploads/` 폴더 | 루트 파일 건드리지 않음, 프로젝트는 하위 폴더, 커밋은 경로 지정 |
| 런타임 | Python **3.11**, Node **22**, pip 있음(네트워크 여부는 preflight로) | kitlib(stdlib) 그대로 사용 |
| Codex | v0.163.0, 모델 `GPT-6.1-Sol default`, cwd `~`, 스킬 동작(openai-docs 스킬 존재), MCP는 `codex_worktrees`뿐 | `$plan-verify` 뜨는지 `/skills`로 확인, MCP 추가 시도 금지 |
| Codex 샌드박스 | `python3 -m http.server` → **PermissionError(소켓 생성 불가)** → 승인("always run commands that start with …") 후 실행됨. `curl`도 승인 필요. `ss`도 막힘 | 서버·curl은 **내가 IDE 터미널에서** 실행. Codex에겐 결과 파일로 검증시킴 |
| 브라우저 | Codex "No valid browsers detected". 확인은 **웹 IDE 포트 미리보기**(3000 등) 또는 원격 데스크톱 Chromium | 서버는 `--bind 0.0.0.0`, 포트 미리보기로 확인 |
| 클립보드 | 이미지 붙여넣기 실패(X11). 텍스트 붙여넣기는 브라우저 IDE라 보통 됨 | 프롬프트는 "파일 읽고 수행해"로 지시 (붙여넣기 의존 X) |
| 오른쪽 메신저 | "Cofa Helper 과제 도우미": 질문·설명·리뷰 담당, **코드는 안 짬**. Enter=전송, Shift+Enter=줄바꿈, 입력창에 "컨텍스트" 첨부 표시 | 본 시험에선 여기가 담당자(실무자) 인터뷰 채널 = Intent 점수. 첫 15분에 질문 묶음 |
| 감시 | "감독 연결", 웹캠, 타이머(남은 시간) 상단. GitHub/MCP 언급 시 Codex 응답에 **반출 금지 경고문이 자동 삽입**됨 | 휴대폰·다른 기기 X. Codex/메신저에 GitHub·MCP·push·모니터링·"본고사 문제" 질문 X |
| 기타 | `.claude/`, `.claude.json`, `.aws/`, `.literacy/`(실행 환경 수집) 존재 | 안내서가 지정한 도구(Codex)만 사용. `.claude`가 보여도 확인 없이 쓰지 않음 |

## 0. 시작 직후 — IDE 터미널 (5분)
```bash
git clone https://github.com/wildrage98/hackathon-kit.git && bash hackathon-kit/setup.sh
python3 tools/preflight.py env
```
- clone이 막히면: 내 PC에 받아둔 `hackathon-kit-main.zip`을 IDE 업로드(📎/uploads) → `unzip -q uploads/hackathon-kit-main.zip && mv hackathon-kit-main hackathon-kit && bash hackathon-kit/setup.sh`
- 외부 자료 반입 방식이 안내와 다르면 감독(채팅)에게 먼저 확인. 규정: 공개 저장소, 완성 코드 아님, 출처 기록(kitlib/SOURCE.md).
- `docs/TIMEBOX.md`에 종료 시각·제출 시작 시각(종료−10분) 적기.

## 1. 읽기 → 유형 판별 → 인터뷰 (15분)
1. 과제 `README.md` 정독 → 필수 제출물/실행 방식을 `docs/SUBMIT_CHECK.md`에.
2. `hackathon-kit/playbook/README.md` §0 표로 유형(A~H) 판별 → 해당 `0N-*.md`의 "담당자 인터뷰 추가 질문" 열기.
3. 오른쪽 메신저에 **1차 질문 묶음**(`playbook/stakeholder-interview.md` §1, 5개) → 답을 `docs/QUESTIONS.md` 표에.
4. 데이터가 있으면 `python3 tools/profile_csv.py <파일> --ts <시각컬럼> --key <설비컬럼>` → 2차 질문 묶음(§2).
5. `docs/AGREEMENT.md` 채워 메신저로 "맞습니까?" 확인 → 시각 기록. 기준이 없으면 §3 화법으로 **제안해서 확정**.

## 2. Codex 시작 (터미널 탭 `+` 에서 `codex`)
첫 메시지(타이핑):
```
AGENTS.md 와 hackathon-kit/prompts/00-kickoff.md 를 읽고 그 안의 지시를 그대로 수행해.
```
- 이후: `hackathon-kit/prompts/02-plan.md 를 읽고 수행해` → `$plan-verify` → `03-implement` 반복 → `04-verify`
- 승인 프롬프트: 파일 쓰기·테스트는 승인, **서버·네트워크 명령은 "no" 하고 내가 터미널에서** 실행
- 프롬프트 4요소(목표/제약/완료 기준/출력 형식) — 한 줄 지시 금지. 예:
  `목표: data/x.csv를 읽어 설비별 temp 상한 룰로 판정해 outputs/alerts.csv 생성. 제약: stdlib+kitlib, 기준은 config/rules.json. 완료: python3 src/main.py run 이 0으로 끝나고 alerts.csv에 header+N행. 출력: 바뀐 파일 목록 + 실행 결과 3줄.`

## 3. 프로젝트 폴더 (30분 시점까지 최소 실행본)
```bash
bash tools/new_project.sh <이름>          # <이름>/{src,tests,data,outputs,config,logs,kitlib,README.md}
cd <이름> && python3 src/main.py run && python3 -m unittest discover -s tests -v && cd ..
```
- 과제가 폴더/파일명을 지정하면 그걸 따르고 `cp -r kitlib <폴더>/` 만.
- 서버: `cd <이름> && PORT=3000 python3 src/main.py serve` (IDE 터미널) → 포트 미리보기. 소켓 불가면 `webapp.dashboard_fallback` → outputs/*.html, README에 "파일로 열기" 명시.
- 실행 증거: `bash tools/run_and_log.sh run python3 <이름>/src/main.py run` → `logs/`.

## 4. 커밋 = 평가 자료 (기능 하나마다)
```bash
git add <이름> docs logs tools AGENTS.md .gitignore && git commit -m "feat: <무엇> — <왜/기준>"
```
`git add -A` 금지(홈의 .npm/.codex 등이 딸려감). setup.sh가 .gitignore를 넣어두지만 경로 지정이 원칙.

## 5. 100분 체크포인트 → 130분 검증 → 170분 제출
- 100분: 지금 제출 가능한가? 아니면 TIMEBOX 축소 순서(대시보드→콘솔+CSV, 부가 기능, 품질 케이스 문서화). 축소는 메신저로 담당자와 합의하고 기록.
- 검증: 합성 데이터에 이상 심기(`python3 -m kitlib.synth`) 또는 손으로 만든 케이스 → `docs/VERIFICATION.md`에 로그 경로.
- 제출 10분 전:
```bash
python3 tools/preflight.py submit --project <이름>
```
  Codex: `hackathon-kit/prompts/07-self-critique.md 를 읽고 수행해` → 약점 Top 5 → `docs/DECISIONS.md` → 통독 → 제출.

## 서술형 6문항 (제출 후, 문항당 5분, 복귀 불가, AI·복붙·다른 기기 금지)
`playbook/essay-prep.md` 프레임: 결론 1줄 → 근거(파일·함수·숫자) → 약점+영향 → 검증한 것/개선안.
DECISIONS.md의 숫자(임계치·연속 횟수·해제 조건·허용 오차)를 머릿속에 넣고 들어간다.

## 하지 말 것 (대화·터미널 전부 기록됨)
- Codex/메신저에 GitHub·MCP·push·화면 모니터링·"본고사 문제 뭐 나와" 질문
- 한 줄 프롬프트, 계획 없이 코딩, 담당자 질문 없이 기준 추측
- `git add -A`, 과제 README 수정, Codex 업데이트, 지정 외 AI 도구
- 휴대폰 촬영·메모 앱 등 다른 기기 (감독 연결 상태)
