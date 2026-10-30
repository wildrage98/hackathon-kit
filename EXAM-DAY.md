# EXAM-DAY

## 0. 시작 (터미널)
```bash
git clone https://github.com/wildrage98/hackathon-kit.git && bash hackathon-kit/setup.sh
python3 tools/preflight.py env
```
clone 불가 시: `hackathon-kit-main.zip` 업로드(uploads/) 후
```bash
mkdir -p /tmp/kit && (unzip -q uploads/hackathon-kit*.zip -d /tmp/kit || python3 -m zipfile -e uploads/hackathon-kit*.zip /tmp/kit)
mv "$(dirname "$(find /tmp/kit -maxdepth 2 -name setup.sh | head -1)")" hackathon-kit && bash hackathon-kit/setup.sh
python3 tools/preflight.py env
```
- `docs/TIMEBOX.md` 종료 시각, 제출 시작 시각(−10분)

## 1. 15분
1. README 정독 → `docs/SUBMIT_CHECK.md`
2. `playbook/README.md` §0 → 유형 → `0N-*.md` 질문 열기
3. 메신저: 질문 묶음 1 (`playbook/stakeholder-interview.md` §1) → `docs/QUESTIONS.md`
4. 데이터: `python3 tools/profile_csv.py <파일> --ts <시각> --key <키>` → 질문 묶음 2 (§2)
5. `docs/AGREEMENT.md` → 메신저 확인 → 시각 기록. 기준 없으면 §3 → 제안 → 확정

## 2. 에이전트 (터미널 탭 +)
```
AGENTS.md 와 hackathon-kit/prompts/00-kickoff.md 를 읽고 그 안의 지시를 그대로 수행해.
```
- 다음: `hackathon-kit/prompts/02-plan.md 를 읽고 수행해` → `$plan-verify` → 03 반복 → 04
- 승인: 파일·테스트 O / 서버·네트워크 X (내가 터미널에서)
- 지시 4요소: 목표 / 제약 / 완료 기준(명령+기대 출력) / 출력 형식

## 3. 30분까지 최소 실행본
```bash
bash tools/new_project.sh <이름>
cd <이름> && python3 src/main.py run && python3 -m unittest discover -s tests -v && cd ..
```
- 지정 폴더가 있으면 그 폴더 + `cp -r kitlib <폴더>/`
- 서버: `cd <이름> && PORT=3000 python3 src/main.py serve` (터미널) → 포트 미리보기. 불가 → `dashboard_fallback` → outputs/*.html, README 명시
- 로그: `bash tools/run_and_log.sh run python3 <이름>/src/main.py run`

## 4. 커밋 (기능마다)
```bash
git add <이름> docs logs tools AGENTS.md .gitignore && git commit -m "feat: <무엇> — <기준>"
```
`git add -A` X

## 5. 100 / 130 / 170
- 100: 제출 가능? 아니면 TIMEBOX 축소 순서. 축소는 메신저 합의 + 기록
- 130: `python3 -m kitlib.synth` 또는 손 케이스 → `docs/VERIFICATION.md` (로그 경로)
- 170: `python3 tools/preflight.py submit --project <이름>` → `prompts/07` → `docs/DECISIONS.md` 통독 → 제출

## 6. 제출 후
`playbook/essay-prep.md` 프레임. DECISIONS 숫자(임계치·연속·해제·오차).

## X
- 메신저·에이전트에 외부 연결·저장소·과제 외 질문 X
- 한 줄 지시 X, 계획 없이 코딩 X, 질문 없이 기준 추측 X
- `git add -A` X, 루트 README 수정 X, 도구 업데이트 X, 지정 외 도구 X
- 다른 기기 X
