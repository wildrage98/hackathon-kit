# B. 불량 · 수율 요인 분석

1차 예선에 "반도체 불량 원인 분석"이 나왔다. 2차에서 "설비/레시피/시간대별 불량 원인을 찾아
보고하는 도구"로 변형될 가능성. 배선 예시: `examples/yield_rootcause.py`

## 단서
불량률, 수율, 로트/웨이퍼/칩, 원인, 어느 설비·레시피·작업자·시간대, 요인, 상관.

## 담당자 인터뷰 추가 질문
1. 결과 컬럼 정의: PASS/FAIL? 불량 코드 여러 개? 수율(연속값)? → 이진으로 바꿀 기준
2. 요인 후보 컬럼은 무엇이고, 그중 **운영자가 바꿀 수 있는 것**은? (바꿀 수 없는 요인은 우선순위↓)
3. 로트 간 독립인가? (같은 로트 웨이퍼들은 독립이 아님 → 로트 단위로 집계)
4. 분석 기간, 기간 중 공정 변경 이벤트(레시피 변경, PM) 있었나 → 전/후 분리
5. "원인을 찾았다"의 기준: 불량률 차이가 몇 배? 통계적 유의? 담당자가 납득하는 표?
6. 수치 공정 변수(온도·두께 등)가 있으면 스펙 한계가 있나 → spc/rules 연결
7. 결과물: 요인 순위표 + 근거 + 권고 조치? 반복 실행 도구인가 1회 보고서인가

## 아키텍처
CSV → profile → (품질: 중복 로트, 결과 결측) → `groupstats.rank_factors` → 상위 요인 `rate_by` 막대 →
수치 변수 `numeric_compare` → 상위 2요인 `crosstab` (교호작용/심슨 확인) → Report

## 모듈 순서
```python
rows, _ = csvio.read_csv(path)
ranked = groupstats.rank_factors(rows, FACTORS, "result", min_n=20)   # chi2 내림차순
for f in FACTORS: groupstats.rate_by(rows, f, "result")               # 그룹별 n/bad/rate/lift
groupstats.numeric_compare(rows, "temp", "result")                     # Cohen's d
ct = groupstats.crosstab(rows, top1, top2, "result"); groupstats.crosstab_markdown(ct)
```

## 최소 실행본
요인 1개(설비)별 불량률 표 + 전체 대비 lift. 이것이 30분 안에 CSV/콘솔로 나와야 한다.

## 검증
- 합성 데이터에 **알려진 요인**(예: ETCH03×R-B에서 +25%p)을 심고 rank_factors가 1위로 찾는지
- 요인을 섞어도(셔플) 유의하지 않게 나오는지 (음성 대조군)
- min_n 미만 그룹 제외가 동작하는지, 결과 컬럼 토큰('불량','NG','1') 인식 테스트

## 함정
- **상관≠인과**를 리포트에 명시 안 함 → 서술형에서 바로 찔린다
- 표본 적은 그룹의 큰 lift에 속음 → min_n, n 같이 표기
- 심슨의 역설: 설비별로는 A가 나쁜데 레시피 통제하면 반대 → crosstab 필수
- 기대도수<5 셀에서 카이제곱 과신 → `low_expected_cells` 경고 표기
- 수율(연속값)을 이진화한 기준을 안 적음

## 서술형 예상 질문 → 골격
- "ETCH03이 원인이라고 결론 낸 근거는?" → 불량률 x% vs 전체 y%(lift z), chi2 유의, 교차표에서 레시피 통제해도 유지. 한계: 관측 데이터, 해당 설비에 특정 제품 편중 가능성 → 개선: 제품 통제 분석/실험
- "카이제곱 대신 다른 방법은?" → Fisher(소표본), 로지스틱 회귀(다요인 동시) — 180분이라 집계+chi2 선택
- "데이터가 10배 커지면?" → 집계는 O(n) 한 번 훑기, Counter 기반이라 문제없음. 메모리는 행 dict라 큼 → 컬럼 지향/CSV 스트리밍으로 개선
