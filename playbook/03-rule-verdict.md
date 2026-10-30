# C. 규칙 기반 판정

## 단서
적합/부적합, 출하 가능, 규정·기준서, 스펙 in/out, 등급, 체크리스트, 예외, 케이스 파일

## 질문
1. 기준서 조건 전부 표로 (`rules.rules_to_markdown`) → 빠짐·모순 확인
2. 경계: 이상/이하/초과/미만, 같으면? → `inclusive`
3. 우선순위: 예외가 일반을 이기나? 하나라도 CRIT면 불합격? → 등급 합성
4. 판정 불가(누락) = 보류? 불합격? → HOLD
5. 재검 기준(경계 ±x%?)
6. 출력: 케이스별 판정 + 걸린 조건 + 값 + 기준
7. 케이스 파일 여러 개면 형식 동일?

## 순서
```python
RULES = rules.load_rules("config/rules.json")
for case in cases:
    hits = rules.evaluate_row(case, RULES)
    level = None
    for h in hits: level = rules.max_sev(level, h.severity)
    verdict = "FAIL" if level == "CRIT" else "RECHECK" if level == "WARN" else "HOLD" if missing(case) else "PASS"
    case.update(_verdict=verdict, _reasons="; ".join(h.reason for h in hits))
```
범주 → `allowed=[...]`. 복합(A이면서 B) → `when`. 합계·비율 → 파생 컬럼 먼저, 단순 룰

## 최소
케이스 1파일 → 룰 3개 → 판정/근거 CSV. PASS/FAIL/HOLD 건수

## 검증
- 경계값: 같은 값, ±최소단위, 결측, 문자열 숫자("12.0"), 음수
- 기준서 조건 수 == 룰 수
- 정답 있는 예시 케이스 100% 일치
- 랜덤 100건 → HOLD 비율, 예외 0

## 함정
- 기준 하드코딩 → json
- 결측 PASS
- 단위(mm/um) → profile min/max
- 컬럼명 공백·대소문자 → 매핑표 + 로그

## Q
같은 값 판정 근거 / 충돌 시 max_sev, 우선순위 필드 없음 / 규정 변경 위치 / 누락 HOLD 이유
