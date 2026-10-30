# A. 센서 시계열 이상 탐지 / 설비 모니터링

가장 유력한 유형 (2차 모의시험이 이것). 배선 예시: `examples/sensor_pipeline.py`

## 이 유형이라는 단서
센서값, 시간에 따른, 설비 N대, 이상 징후, 경보/알람, 정상 범위, 운영자가 판단 근거를 본다.

## 담당자 인터뷰 추가 질문 (QUESTIONS.md C섹션 위에 얹는다)
1. 설비마다 센서 종류·정상 범위가 다른가? → 다르면 **룰을 설비별 when={'equipment':…}** 로
2. 운영 상태(RUN/IDLE/MAINT)가 데이터에 있는가, 없으면 어떻게 추정하나(전류 0 = 정지?) → 상태 밖은 판정 제외
3. "이상"은 단발 초과인가, N초 지속인가 → `min_consecutive`
4. 등급(주의/경고/위험)과 각 기준 → severity 2~3단
5. 경보 해제 조건(정상 M회 연속? 운영자 확인?) 재발은 새 경보인가 → `AlertManager(close_after=M)`
6. 결측·중복·역전·끊김 처리 — 특히 **끊김 자체를 경보로 볼 것인가** (센서 장애 vs 설비 이상)
7. 오탐과 미탐 중 어느 쪽이 비싼가 → 임계치 보수/민감 방향 결정 근거
8. 운영자 화면 필수인가, CSV/리포트로 충분한가

## 아키텍처 (한 줄)
CSV → timeparse → quality(check→policy) → 상태별 룰(rules) + 보조 통계(stats_detect) → alerts 상태머신 → report/webapp

## 모듈 순서
```python
rows, meta = csvio.read_csv(path)
timeparse.add_parsed_time(rows, "timestamp")                       # 'Z', '+09:00' 섞여도 OK
q = quality.check_quality(rows, key_cols=["equipment"], value_cols=SENSORS, limits=PHYSICAL)
clean, qlog = quality.apply_policy(rows, q["issues"], POLICY, key_cols=["equipment"], value_cols=SENSORS)
rules.evaluate_series(clean, RULES, key_cols=["equipment"])        # row['_level'], row['_hits']
am = alerts.run_from_levels(clean, ["equipment"], open_after=N, close_after=M)
Report(...).table(am.to_rows()).svg(svgchart.line_chart(..., thresholds=..., bands=...))
```

## 최소 실행본 (30분 시점에 있어야 하는 것)
- 입력 CSV 1개 → 설비별 임계치 1개(예: temp hi) 판정 → `outputs/alerts.csv` + 콘솔 요약
- 이것만 있으면 제출은 된다. 이후는 전부 추가 기능.

## 기준이 없을 때
- 정상(RUN) 구간 앞부분으로 `stats_detect.iqr_bounds(k=2~3)` → Rule 제안 → **담당자 확정** → `config/rules.json`에 저장(`rules.load_rules`)
- 드리프트 요구가 있으면 `ewma_detect`/`cusum`을 WARN 보조로. 설명: "EWMA가 기준평균에서 kσ 벗어남"

## 검증 (VERIFICATION.md에 적을 것)
1. `python -m kitlib.synth --out data/synth.csv` → 정답 포함 데이터
2. 파이프라인 실행 → `evalmetrics.event_prf(truth, STARTs, tolerance, keys)` → P/R/F1/latency 표
3. 품질 케이스: 심은 결측/중복/역전/끊김 수 vs 탐지 수 (예시 파이프라인은 100% 일치)
4. 경계값 단위테스트: 기준값과 같을 때, 첫 샘플, 상태 전환 직후
5. 담당자 샘플 데이터가 있으면 거기서 **오탐 건수**를 세서 보고 (합성 성능≠실제 성능 명시)

## 함정
- 설비별 평균이 다른데 전역 기준 하나 → 오탐 폭발 (설비별 when 필수)
- 기준 구간에 이상이 섞이면 IQR 경계가 넓어져 미탐 → 기준 구간 선정 근거 기록
- aware/naive datetime 섞임 → 비교 TypeError. add_parsed_time의 unify가 해결하지만 **왜 KST로 통일했는지** 적어둘 것
- 경보가 깜빡임(START/END 반복) → close_after 올리기. 그 숫자의 근거(샘플 주기×몇 분)를 말할 수 있어야
- 대시보드에 매달리다 검증을 못 함 → 100분 체크포인트

## 서술형 예상 질문 → 답변 골격
- "임계치를 어떻게 정했고 바뀌면 어디를 고치나?" → 담당자 확정값/IQR 제안, `config/rules.json` 한 곳, 코드 수정 없음
- "센서가 10분 끊겼다 돌아오면 코드는 어떻게 동작하나?" → quality.gap 플래그 → (정책) 끊김 구간 판정 제외 + 복귀 첫 샘플은 min_consecutive 리셋 상태라 단발로는 확정 안 됨. 약점: 끊김 자체를 경보화 안 했다면 그걸 말하고 개선안 제시
- "같은 시각 중복 행이 다른 값이면?" → 현재는 첫 행 유지(drop). 약점: 어느 쪽이 맞는지 모름 → 개선: 둘 다 플래그 후 담당자 정책
- "오탐을 줄이려면?" → min_consecutive↑, close_after↑, 상태별 룰, 트레이드오프는 지연(latency) 증가 — evalmetrics의 mean_latency로 수치화
- "왜 ML을 안 썼나?" → 라벨 없음·설명 가능성·180분. 룰 기준선 위에 통계 보조. ML은 다음 단계
