# hackathon-kit

AI 해커톤(Codex 환경) 응시용 개인 작업 하네스.
문제 풀이 코드는 포함하지 않으며, **절차·양식·검증 스크립트**만 담는다.

## 응시 환경에서 쓰는 법 (한 줄)

```bash
git clone https://github.com/wildrage98/hackathon-kit.git && bash hackathon-kit/setup.sh
```

setup.sh가 하는 일
1. `AGENTS.md` → 현재 작업 폴더 루트로 복사 (Codex가 자동으로 읽음)
2. `skills/*` → `~/.codex/skills/` 로 복사 (`$plan-verify`, `$decision-log` 로 호출)
3. `templates/*` → `./docs/` 로 복사 (PLAN / DECISIONS / VERIFICATION / QUESTIONS)
4. `scripts/*` → `./tools/` 로 복사

## 구성

```
AGENTS.md            Codex 행동 규칙 (얇게, 토큰 절약)
setup.sh             설치 스크립트
templates/
  TIMEBOX.md         180분 시간표
  QUESTIONS.md       요구사항 협의 질문 체크리스트
  PLAN.md            아키텍처·개발 계획서 양식
  DECISIONS.md       판단 기록 (서술형 답변 재료)
  VERIFICATION.md    검증 결과 양식 (증거 기반)
  SUBMIT_CHECK.md    제출 직전 체크리스트
scripts/
  run_and_log.sh     명령 실행 + 로그 파일 자동 저장
  smoke.sh           최소 실행 확인 (의존성·실행·포트)
skills/
  plan-verify/       계획 → 구현 → 검증 루프 스킬
  decision-log/      작업 중 판단을 DECISIONS.md에 기록하는 스킬
```

## 규칙 (대회 규정)
- 이 저장소는 결과 통지 전까지 Public 유지
- 과제 완성 코드를 넣지 않는다 (결과물 통째 대체 금지)
- Codex 버전 업데이트 금지 — 설치 스크립트는 codex 를 건드리지 않는다
