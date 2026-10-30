# B. 불량 · 수율 요인

예시: `examples/yield_rootcause.py`

## 단서
불량률, 수율, 로트/웨이퍼/칩, 원인, 설비·레시피·작업자·시간대, 요인, 상관

## 질문
1. 결과 컬럼 정의: PASS/FAIL? 코드 여러 개? 연속값? → 이진화 기준
2. 요인 후보 컬럼, 그중 바꿀 수 있는 것
3. 로트 내 독립성 → 집계 단위
4. 기간, 기간 중 공정 변경(레시피, PM) → 전/후 분리
5. "원인 찾음"의 기준: 몇 배? 유의? 납득하는 표?
6. 수치 공정 변수 스펙 한계 → spc/rules
7. 결과물: 순위표 + 근거 + 권고? 반복 도구 vs 1회 보고서

## 순서
```python
rows, _ = csvio.read_csv(path)
ranked = groupstats.rank_factors(rows, FACTORS, "result", min_n=20)
for f in FACTORS: groupstats.rate_by(rows, f, "result")
groupstats.numeric_compare(rows, "temp", "result")
ct = groupstats.crosstab(rows, top1, top2, "result"); groupstats.crosstab_markdown(ct)
```

## 최소
요인 1개(설비)별 불량률 표 + lift. CSV/콘솔

## 검증
- 심은 요인(예: 설비×레시피 +25%p) → rank_factors 1위
- 셔플 → 유의하지 않음 (음성 대조)
- min_n 제외 동작, 결과 토큰('불량','NG','1') 인식

## 함정
- 상관≠인과 미명시
- 소표본 큰 lift → min_n, n 표기
- 심슨 → crosstab
- 기대도수<5 → `low_expected_cells`
- 이진화 기준 미기록

## Q
1위 요인 근거(비율·lift·chi2·교차표) 와 한계 / 카이제곱 대안 / 10배 데이터
