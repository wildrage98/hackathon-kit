# 에이전트 운용

## 1. 세션
- 메인 1개: 구현. `prompts/00`으로 시작
- 검토 1개(선택): `prompts/06`
- 길어지면 새 세션 + `prompts/05`

## 2. 프롬프트 순서
| 시점 | 파일 |
|---|---|
| 시작 | 00-kickoff |
| 데이터 받은 직후 | 01-interview-helper |
| 계획 | 02-plan |
| 구현 반복 | 03-implement |
| 검증 | 04-verify |
| 세션 교체 | 05-handoff |
| 제출 20분 전 | 06-presubmit-review |
| 제출 10분 전 | 07-self-critique |

## 3. 토큰·시간
- 원본 데이터 읽히지 않음 → `profile.to_markdown()`만
- "함수 X만", "마지막 20줄만"
- 실패 → 가설 → 수정 → 1회 실행
- 긴 작업: 계획 3줄 → 승인 → 실행
- 대기 중 DECISIONS/README

## 4. 지시 4요소
```
목표: 설비별 temp 상한 룰로 판정해 outputs/alerts.csv
제약: stdlib + kitlib, 입력 data/sample.csv, 기준 config/rules.json
완료: python src/main.py run exit 0, alerts.csv header+N행, tools/run_and_log.sh 로그
출력: 바뀐 파일 + 실행 명령 + 결과 3줄
```
X: "시스템 만들어줘", "알아서 개선해줘", "테스트도 추가해줘"

## 5. 출력 확인 (기능마다)
1. 로그 파일 경로 있나
2. 핵심 함수 1개 직접 읽기 → DECISIONS 1줄
3. "틀리는 입력 3개" → 1개 테스트

## 6. 승인·서버
- 파일·테스트 승인, 서버·네트워크 거절 → 터미널에서 직접
- 서버 15분 넘기지 않음 → 정적 폴백
- 승인 모드 변경은 내가 터미널에서. 도구 업데이트 X

## 7. 모델
- 계획·검토 = 추론형, 반복 구현 = 빠른 것. `/model` 가능하면
- 안 되면 신경 쓰지 않음

## 8. 스킬
- `$plan-verify`, `$decision-log`
- 안 뜨면 AGENTS.md로 충분
