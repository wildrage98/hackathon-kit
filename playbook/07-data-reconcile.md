# G. 데이터 정합성 · 대사 · 자료 비교

1차 예선 "자료 정렬·비교" 유형의 도구화. "A 시스템(MES)과 B 자료(엑셀 집계)가 왜 안 맞나",
"마스터 대비 누락", "전일 대비 변경분". 핵심 모듈: `kitlib.reconcile`, `quality`

## 단서
두 개 이상의 파일, 불일치, 누락, 대조, 마스터, 정합성, 차이 리포트, 중복 키.

## 담당자 인터뷰 추가 질문
1. **키**가 무엇인가 (로트ID? 로트+웨이퍼? 날짜+설비?) 두 자료에서 표기가 같은가 (대소문자, 공백, 앞의 0)
2. 어느 쪽이 기준(source of truth)인가 → 불일치 시 어느 값을 믿나
3. 비교 컬럼과 허용 오차(수량 ±1? 금액 반올림?) 날짜 포맷 차이
4. 중복 키가 있으면 정상인가(다건 허용) 오류인가
5. 결과물: 불일치 목록(사람이 처리) + 요약 건수 + 원인 분류?
6. 주기 실행인가 1회인가 → 주기면 CLI 인자로 파일 경로

## 아키텍처
두 CSV → 키 정규화 → `reconcile.compare` → only_a / only_b / mismatch / dup → 원인 유형 분류(정규화로 해결된 것 vs 진짜 불일치) → Report + 불일치 CSV

## 모듈 순서
```python
a, _ = csvio.read_csv("mes.csv"); b, _ = csvio.read_csv("excel.csv")
raw = reconcile.compare(a, b, KEY, COLS, tol=TOL, upper=False)     # 정규화 전
norm = reconcile.compare(a, b, KEY, COLS, tol=TOL, upper=True, strip_zeros=True)   # 정규화 후
# raw→norm에서 줄어든 only_in 건수 = "표기 차이"였던 것 (리포트에 분리 표기)
csvio.write_csv("outputs/mismatch.csv", norm["mismatch"])
report.Report("대사 결과").raw_md(reconcile.summary_markdown(norm)).table(norm["only_in_a"]).table(norm["mismatch"])
```

## 최소 실행본
키 하나로 only_in_a/only_in_b 건수와 목록 CSV. 30분.

## 검증
- 자료 A를 복사해 B를 만들고 **알려진 변경**(3건 삭제, 2건 값 변경, 1건 키 공백 추가)을 심어 정확히 그 건수가 나오는지
- 정규화 on/off 비교 표 (표기 차이 몇 건을 흡수했는지)
- 허용 오차 경계: tol=0.5에서 차이 0.5는 일치, 0.51은 불일치 (테스트)
- 대사 결과 총합이 맞는지: keys_a = matched + only_in_a

## 함정
- 키 정규화를 안 해서 전부 불일치 → 첫 실행에서 only_in이 50% 넘으면 키 표기부터 의심
- 숫자가 문자열("1,234")로 들어옴 → csvio가 변환하지만, 한쪽만 문자열이면 _eq가 문자열 비교 → profile에서 타입 확인
- 중복 키를 첫 행으로 눌러버림 → dup 목록을 반드시 별도 보고
- 어느 쪽이 맞는지 판단을 내가 함 → 담당자 기준 자료 확정 전엔 "불일치"로만 표기

## 서술형 예상 질문 → 골격
- "불일치 1,200건 중 진짜 오류는 몇 건인가?" → 정규화 전후 비교로 표기 차이 n건 제외, 허용오차 내 m건 제외, 남은 k건이 검토 대상. 한계: 허용오차는 담당자 기준
- "키가 복합키일 때 성능은?" → dict 해시 O(n). 10만 행 수초. 메모리는 양쪽 행 전부 → 개선: 한쪽만 적재하고 다른 쪽 스트리밍
- "날짜 포맷이 다르면?" → timeparse로 정규화 후 비교(현재는 문자열 비교) — 개선 과제로 명시
