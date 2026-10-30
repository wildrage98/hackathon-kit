# F. 스케줄링 · 디스패칭 · 자원 배정

"로트를 어느 설비에 어떤 순서로", "정비 일정 배치", "납기 지연 최소화" 류. 1차 예선의 SCM 데이터
문제가 2차에서 도구 형태로 나올 수 있다. 핵심 모듈: `kitlib.schedule`

## 단서
배정, 순서, 우선순위, 납기, 처리시간, 설비 가용/다운타임, 가동률, 대기시간, 간트.

## 담당자 인터뷰 추가 질문
1. **목표 하나만 고르면?** 납기 지연 최소 / 처리량(완료 시각) 최소 / 급한 것 우선 / 설비 균등 → 규칙 선택 근거
2. 제약: 설비별 처리 가능 작업(eligible), 준비(setup) 시간, 다운타임, 작업 도착 시각(ready)
3. 작업 분할 가능? 선점(중단 후 재개) 가능? → 둘 다 불가가 기본 가정(합의서에 명시)
4. 동률 처리 규칙(같은 납기면?) → 결정적이어야 재현 가능
5. 평가 지표: 지연 건수 / 총 지연 / 최대 지연 / makespan / 가동률 중 무엇을 보고하나
6. 수동 조정(운영자가 특정 작업 고정)이 필요한가 → 있으면 '고정 작업 먼저 배치' 단계 추가

## 아키텍처
CSV(작업, 설비) → Job/Machine 객체 → `compare_rules` 로 규칙 5개 지표 비교 → 담당자 목표에 맞는 규칙 선택 →
`dispatch(rule)` → 간트 표(`to_gantt_markdown`) + 지표 → Report. 선택 근거 = 비교표.

## 모듈 순서
```python
jobs = [schedule.Job(r["id"], r["dur"], ready=r.get("ready",0), due=r.get("due"), priority=r.get("prio",0), eligible=r.get("eligible")) for r in rows]
machines = [schedule.Machine(m, down=downtimes.get(m, [])) for m in machine_ids]
table = schedule.compare_rules(jobs, machines)            # FIFO/SPT/EDD/PRIORITY/CR 지표
best = schedule.dispatch(jobs, machines, rule="EDD")      # 담당자 목표가 '지연 최소'면 EDD
report.Report("배정 결과").table(table).raw_md(schedule.to_gantt_markdown(best))
```

## 최소 실행본
작업 CSV → EDD 한 규칙으로 배정표 + 지연 건수. 30분.

## 검증
- 손으로 풀 수 있는 작은 예(작업 4개, 설비 2개)로 **정답 배정표와 일치**
- 제약 테스트: eligible 위반 0건, 다운타임과 겹치는 작업 0건, 한 설비에 동시에 2개 없음 (겹침 검사 함수 1개)
- 규칙 비교표가 목표 지표에서 선택 규칙이 최선임을 보여줌 (아니면 선택 근거를 다시)
- 동일 입력 2회 실행 → 동일 출력 (재현성)

## 함정
- 최적화(MILP/유전알고리즘)에 손대기 → 180분에 검증 불가. 규칙 기반 + 비교표가 정답
- 단위 혼동(분 vs 초, 시각 vs 기간)
- 다운타임 안에 걸친 작업을 분할 → 모델은 비선점이므로 다운타임 뒤로 미룬다(코드 `_earliest_start`) — 이 가정을 명시
- "가동률 100%"가 좋은 게 아닐 수 있음(여유 없음) → 담당자 목표 확인

## 서술형 예상 질문 → 골격
- "왜 EDD인가?" → 담당자 목표=지연 최소, 비교표에서 total_tardiness 최소. 한계: 그리디, 전역 최적 아님 → 개선: 룩어헤드/국소탐색
- "작업이 1000개면?" → 매 결정마다 정렬 O(n log n), n회 → O(n² log n). 1000개는 수초. 10만이면 힙 사용
- "설비가 갑자기 고장나면?" → 현재는 사전 다운타임만. 개선: 남은 작업을 현재 시각부터 재배정(함수 재호출)하는 재계획 모드
