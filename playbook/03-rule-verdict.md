# C. 규칙 기반 판정 · 검사 자동화

1차 예선에서 반복된 유형(조건별 분류·판단, 규정 위반 식별, 출하 판정). 2차에서는 "규정 문서 + 케이스
파일 여러 개 → 자동 판정 + 근거 + 재검 목록" 형태가 유력. 핵심 모듈: `kitlib.rules`

## 단서
적합/부적합, 출하 가능 여부, 규정·기준서, 스펙 in/out, 등급(A/B/C), 체크리스트, 예외 조건, 케이스 파일 N개 중 1개 예시.

## 담당자 인터뷰 추가 질문
1. 기준서의 **모든 조건을 표로** 만들어 보여주고 빠진 것·모순을 확인 (`rules.rules_to_markdown`)
2. 경계값: "이상/이하/초과/미만" 정확히. 기준과 같으면? → `inclusive`
3. 조건 간 우선순위: 예외가 일반 규칙을 이기나? 하나라도 CRIT면 불합격? → 등급 합성 규칙
4. 판정 불가(값 누락)는 '보류'인가 '불합격'인가 → rules는 값 없으면 판정 안 함 → 별도 '보류' 처리
5. 재검 대상 기준(경계 근처 ±x%?)이 있나
6. 출력 형식: 케이스별 판정 + 걸린 조건 + 값 + 기준 (근거 열 필수)
7. 케이스 파일이 여러 개면 형식이 전부 같은가, 다르면 어떻게 다른가

## 아키텍처
기준서 → `config/rules.json` (사람이 읽는 표와 1:1) → 케이스 로드(csvio) → `rules.evaluate_row` → 등급 합성 → 결과 CSV(판정, 근거) + 보류/재검 목록 → Report

## 모듈 순서
```python
RULES = rules.load_rules("config/rules.json")      # 기준을 코드 밖으로
for case in cases:
    hits = rules.evaluate_row(case, RULES)
    level = None
    for h in hits: level = rules.max_sev(level, h.severity)
    verdict = "FAIL" if level == "CRIT" else "RECHECK" if level == "WARN" else "HOLD" if missing(case) else "PASS"
    case.update(_verdict=verdict, _reasons="; ".join(h.reason for h in hits))
```
범주형 조건은 `Rule(allowed=[...])`, 복합 조건(A이면서 B)은 `when={...}` 으로 A를 걸고 B를 판정.
`when`으로 못 쓰는 복잡한 조건(합계, 비율)은 **파생 컬럼을 먼저 만들고** 단순 룰로 판정 — 룰 테이블이 기준서와 1:1을 유지해야 설명이 된다.

## 최소 실행본
케이스 1개 파일 → 룰 3개 → 판정/근거 CSV. 콘솔에 PASS/FAIL/HOLD 건수.

## 검증
- **경계값 테스트가 전부다**: 기준값과 같은 값, ±최소단위, 결측, 문자열로 들어온 숫자("12.0"), 음수
- 기준서의 조건 수 == rules.json 룰 수 (빠짐 없음을 표로 증명)
- 예시 케이스(정답이 주어진 것)로 100% 일치 → 틀리면 룰 해석 문제 → 담당자 재확인
- 랜덤 케이스 100개 생성해 HOLD 비율·예외 발생 0 확인

## 함정
- 기준을 코드에 하드코딩 → "기준 바뀌면?" 질문에 약함. json 외부화
- 결측을 PASS로 흘림 (가장 위험한 버그) → HOLD 명시
- 단위 불일치(mm vs um) → profile에서 min/max 보고 담당자 확인
- 케이스 파일 형식이 미묘하게 다름(컬럼명 공백, 대소문자) → csvio가 strip하지만 매핑표를 두고 로그에 남길 것

## 서술형 예상 질문 → 골격
- "기준값과 정확히 같으면 어떻게 판정되나?" → inclusive 설정과 기준서 문구("이하") 근거, 테스트 케이스 이름
- "조건이 서로 충돌하면?" → max_sev로 보수적 합성(가장 나쁜 등급). 예외 룰은 when으로 범위를 좁혀 먼저 적용. 한계: 명시적 우선순위 필드 없음 → 개선: rule.priority
- "규정이 바뀌면 어디를 고치나?" → config/rules.json 한 곳, 테스트로 회귀 확인
- "값이 비어 있으면?" → 판정 안 하고 HOLD, 운영자에게 목록 제공. PASS로 흘리지 않는 이유
