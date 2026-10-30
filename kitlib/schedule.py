"""schedule — 단순 디스패칭/스케줄링 (stdlib only).

언제 쓰나: "작업(로트/정비/검사)을 설비에 배정", "우선순위대로 처리 순서 결정", "납기 지연 최소화"
같은 운영 과제. 최적화 솔버 없이 **규칙 기반 디스패칭**으로 설명 가능한 기준선을 만든다.
(180분 안에 MILP를 돌리는 것보다, 규칙 3개를 비교해 지표로 고르는 편이 설명·검증이 쉽다)

디스패칭 규칙
  FIFO      도착 순
  SPT       처리시간 짧은 것 먼저 (평균 흐름시간 최소)
  EDD       납기 빠른 것 먼저 (최대 지연 최소)
  PRIORITY  priority 값 큰 것 먼저 (동률은 EDD)
  CR        Critical Ratio = (납기-현재)/남은 처리시간 작은 것 먼저 (동적)

모델: 각 job은 한 번만 처리, 각 machine은 한 번에 한 job. eligible로 설비 제약.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence


@dataclass
class Job:
    id: str
    duration: float                 # 처리 시간 (단위 자유: 분)
    ready: float = 0.0              # 도착/가능 시각
    due: Optional[float] = None     # 납기
    priority: float = 0.0           # 클수록 급함
    eligible: Optional[Sequence[str]] = None   # 처리 가능한 설비 id 목록 (None=전부)
    setup: float = 0.0              # 준비 시간


@dataclass
class Machine:
    id: str
    available_at: float = 0.0
    speed: float = 1.0              # 처리 시간 배율의 역수 (2.0이면 절반 시간)
    down: List = field(default_factory=list)  # [(start, end)] 가동 불가 구간


def _rank_key(rule: str, now: float):
    def key(j: Job):
        due = j.due if j.due is not None else float("inf")
        if rule == "FIFO":
            return (j.ready, j.id)
        if rule == "SPT":
            return (j.duration, j.id)
        if rule == "EDD":
            return (due, j.id)
        if rule == "PRIORITY":
            return (-j.priority, due, j.id)
        if rule == "CR":
            cr = (due - now) / j.duration if j.duration > 0 else float("inf")
            return (cr, j.id)
        raise ValueError("unknown rule %s" % rule)
    return key


def _earliest_start(m: Machine, t: float, dur: float) -> float:
    """m에서 t 이후 dur만큼 연속 가동 가능한 가장 빠른 시작 시각 (다운타임 회피)."""
    start = max(t, m.available_at)
    changed = True
    while changed:
        changed = False
        for s, e in sorted(m.down):
            if start < e and start + dur > s:  # 겹침
                start, changed = e, True
    return start


def dispatch(jobs: Sequence[Job], machines: Sequence[Machine], rule: str = "EDD") -> List[Dict]:
    """이벤트 기반 리스트 스케줄링. 반환: [{job, machine, start, end, due, late, tardiness}]"""
    pending = list(jobs)
    ms = [Machine(m.id, m.available_at, m.speed, list(m.down)) for m in machines]
    out: List[Dict] = []
    while pending:
        # 가장 먼저 비는 설비 기준으로 '지금' 결정
        m = min(ms, key=lambda x: x.available_at)
        now = m.available_at
        ready = [j for j in pending if j.ready <= now and (j.eligible is None or m.id in j.eligible)]
        if not ready:
            future = [j for j in pending if (j.eligible is None or m.id in j.eligible)]
            if not future:
                # 이 설비는 아무 것도 못 함 → 제외
                ms = [x for x in ms if x is not m]
                if not ms:
                    raise ValueError("no eligible machine for jobs: %s" % [j.id for j in pending])
                continue
            m.available_at = min(j.ready for j in future)
            continue
        ready.sort(key=_rank_key(rule, now))
        j = ready[0]
        dur = (j.duration / m.speed) + j.setup
        start = _earliest_start(m, now, dur)
        end = start + dur
        late = j.due is not None and end > j.due
        out.append({"job": j.id, "machine": m.id, "start": start, "end": end, "due": j.due,
                    "late": late, "tardiness": max(0.0, end - j.due) if j.due is not None else 0.0, "rule": rule})
        m.available_at = end
        pending.remove(j)
    return sorted(out, key=lambda d: (d["start"], d["machine"]))


def metrics(sched: List[Dict], machines: Sequence[Machine]) -> Dict:
    if not sched:
        return {}
    makespan = max(d["end"] for d in sched) - min(min(d["start"] for d in sched), min(m.available_at for m in machines))
    busy: Dict[str, float] = {}
    for d in sched:
        busy[d["machine"]] = busy.get(d["machine"], 0.0) + (d["end"] - d["start"])
    return {"rule": sched[0]["rule"], "n_jobs": len(sched), "makespan": round(makespan, 2),
            "n_late": sum(1 for d in sched if d["late"]),
            "total_tardiness": round(sum(d["tardiness"] for d in sched), 2),
            "max_tardiness": round(max(d["tardiness"] for d in sched), 2),
            "mean_flow": round(sum(d["end"] for d in sched) / len(sched), 2),
            "utilization": {m: round(busy.get(m, 0.0) / makespan, 3) if makespan else 0 for m in sorted({d["machine"] for d in sched})}}


def compare_rules(jobs, machines, rules=("FIFO", "SPT", "EDD", "PRIORITY", "CR")) -> List[Dict]:
    """여러 규칙을 돌려 지표를 나란히 — 담당자에게 '어떤 목표(지연 vs 처리량)인가'를 확인받는 근거."""
    return [metrics(dispatch(jobs, machines, r), machines) for r in rules]


def to_gantt_markdown(sched: List[Dict]) -> str:
    lines = ["| 설비 | 작업 | 시작 | 종료 | 납기 | 지연 |", "|---|---|---|---|---|---|"]
    for d in sorted(sched, key=lambda x: (x["machine"], x["start"])):
        lines.append("| %s | %s | %.1f | %.1f | %s | %s |" % (d["machine"], d["job"], d["start"], d["end"],
                                                           "" if d["due"] is None else "%.1f" % d["due"],
                                                           "+%.1f" % d["tardiness"] if d["late"] else ""))
    return "\n".join(lines)
