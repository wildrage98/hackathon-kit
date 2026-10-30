# A. 센서 시계열 이상 탐지 / 모니터링

예시: `examples/sensor_pipeline.py`

## 단서
센서값, 시간, 설비 N대, 이상 징후, 경보, 정상 범위, 판단 근거

## 질문
1. 설비마다 센서·정상 범위 다른가 → `when={'equipment':…}`
2. 운영 상태(RUN/IDLE/MAINT) 컬럼 있나, 없으면 추정 기준 → 상태 밖 판정 제외
3. 단발 초과 vs N초 지속 → `min_consecutive`
4. 등급과 기준 → severity
5. 해제 조건(정상 M회?), 재발은 새 경보? → `close_after`
6. 결측·중복·역전·끊김 처리. 끊김 자체 경보 여부
7. 오탐 vs 미탐 어느 쪽이 비싼가
8. 화면 필수? CSV/리포트로 충분?

## 순서
```python
rows, meta = csvio.read_csv(path)
timeparse.add_parsed_time(rows, "timestamp")
q = quality.check_quality(rows, key_cols=["equipment"], value_cols=SENSORS, limits=PHYSICAL)
clean, qlog = quality.apply_policy(rows, q["issues"], POLICY, key_cols=["equipment"], value_cols=SENSORS)
rules.evaluate_series(clean, RULES, key_cols=["equipment"])
am = alerts.run_from_levels(clean, ["equipment"], open_after=N, close_after=M)
Report(...).table(am.to_rows()).svg(svgchart.line_chart(..., thresholds=..., bands=...))
```

## 최소 (30분)
CSV 1개 → 설비별 임계치 1개 → `outputs/alerts.csv` + 콘솔 요약

## 기준 없을 때
RUN 앞부분 `stats_detect.iqr_bounds(k=2~3)` → Rule 제안 → 확정 → `config/rules.json` (`rules.load_rules`). 드리프트 요구 시 `ewma_detect`/`cusum` WARN 보조

## 검증
1. `python -m kitlib.synth --out data/synth.csv`
2. `evalmetrics.event_prf(truth, STARTs, tolerance, keys)` → P/R/F1/latency
3. 심은 결측/중복/역전/끊김 수 vs 탐지 수
4. 경계값: 기준값과 같을 때, 첫 샘플, 상태 전환 직후
5. 실제 샘플 있으면 오탐 건수 (합성≠실제)

## 함정
- 전역 기준 하나 → 설비별 when
- 기준 구간에 이상 섞임 → 경계 넓어짐 → 선정 근거 기록
- aware/naive 혼합 → unify, 통일 기준 기록
- 깜빡임 → close_after (샘플 주기 × 분)
- 화면에 매달림 → 100분 체크포인트

## Q
임계치 결정·변경 위치 / 끊김 후 복귀 동작 / 중복 다른 값 / 오탐 줄이기와 지연 / 왜 ML 아님
