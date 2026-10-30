# F. 스케줄링 · 디스패칭

## 단서
배정, 순서, 우선순위, 납기, 처리시간, 가용/다운타임, 가동률, 대기, 간트

## 질문
1. 목표 하나: 지연 최소 / 완료 시각 최소 / 급한 것 우선 / 균등
2. 제약: eligible, setup, 다운타임, ready
3. 분할·선점 가능? (기본 불가, 명시)
4. 동률 규칙 → 결정적
5. 보고 지표: 지연 건수 / 총 지연 / 최대 지연 / makespan / 가동률
6. 수동 고정 작업 → 먼저 배치

## 순서
```python
jobs = [schedule.Job(r["id"], r["dur"], ready=r.get("ready",0), due=r.get("due"), priority=r.get("prio",0), eligible=r.get("eligible")) for r in rows]
machines = [schedule.Machine(m, down=downtimes.get(m, [])) for m in machine_ids]
table = schedule.compare_rules(jobs, machines)
best = schedule.dispatch(jobs, machines, rule="EDD")
report.Report("배정").table(table).raw_md(schedule.to_gantt_markdown(best))
```

## 최소
작업 CSV → EDD 배정표 + 지연 건수

## 검증
- 작업 4·설비 2 손 풀이와 일치
- eligible 위반 0, 다운타임 겹침 0, 동시 2개 0
- 비교표에서 선택 규칙이 목표 지표 최선
- 2회 실행 동일

## 함정
- MILP/GA 손대기
- 분 vs 초, 시각 vs 기간
- 다운타임 걸친 작업 → 뒤로 미룸(비선점) 명시
- 가동률 100% ≠ 좋음

## Q
왜 EDD(비교표), 그리디 한계 / 1000개 복잡도 / 돌발 고장 재계획
