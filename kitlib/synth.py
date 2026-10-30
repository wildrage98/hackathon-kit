"""synth — 합성 센서 데이터 + 이상/품질 문제 주입 + 정답.

  rows, truth = generate(n_equipment=5, minutes=240, interval_s=10, seed=7, ...)
  write(rows, truth, csv_path, truth_path)
  anomaly: spike / drift / level_shift / stuck / noise    quality: missing / duplicate / reversal / gap    state: RUN/IDLE/MAINT
CLI: python -m kitlib.synth --out data/synth.csv --minutes 240
"""
from __future__ import annotations

import argparse
import json
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_SENSORS = {  # name: (정상 평균, 표준편차, 단위)
    "temp": (65.0, 1.5, "C"),
    "pressure": (2.0, 0.05, "bar"),
    "vibration": (0.30, 0.03, "g"),
    "current": (12.0, 0.4, "A"),
}


def generate(n_equipment: int = 5, minutes: int = 240, interval_s: int = 10, seed: int = 7,
             sensors: Optional[Dict[str, Tuple[float, float, str]]] = None, start: Optional[datetime] = None,
             n_anomalies: int = 6, quality_issues: bool = True, state_changes: bool = True) -> Tuple[List[Dict], Dict]:
    rnd = random.Random(seed)
    sensors = sensors or DEFAULT_SENSORS
    start = start or datetime(2026, 10, 31, 10, 0, 0)
    n = minutes * 60 // interval_s
    equips = ["EQP%02d" % (i + 1) for i in range(n_equipment)]
    truth: Dict = {"anomalies": [], "quality": [], "states": [], "sensors": {k: {"mean": v[0], "std": v[1], "unit": v[2]} for k, v in sensors.items()},
                   "interval_s": interval_s, "equipment": equips}
    rows: List[Dict] = []

    for eq in equips:
        # 설비별 고유 오프셋 (서로 다른 설비 = 기준이 다르다는 점을 흉내)
        offs = {s: rnd.uniform(-0.5, 0.5) * sensors[s][1] * 3 for s in sensors}
        # 상태 구간
        states = [("RUN", 0, n)]
        if state_changes and n > 200:
            a = rnd.randint(n // 5, n // 3)
            b = a + rnd.randint(20, 60)
            c = rnd.randint(2 * n // 3, n - 60)
            d = c + rnd.randint(20, 50)
            states = [("RUN", 0, a), ("IDLE", a, b), ("RUN", b, c), ("MAINT", c, d), ("RUN", d, n)]
            for st, s0, s1 in states:
                if st != "RUN":
                    truth["states"].append({"equipment": eq, "state": st, "start_idx": s0, "end_idx": s1,
                                            "start": (start + timedelta(seconds=s0 * interval_s)).isoformat(),
                                            "end": (start + timedelta(seconds=s1 * interval_s)).isoformat()})
        state_at = [None] * n
        for st, s0, s1 in states:
            for i in range(s0, min(s1, n)):
                state_at[i] = st
        # 이상 주입 계획
        plans = []
        for _ in range(max(0, n_anomalies // n_equipment + (1 if rnd.random() < 0.5 else 0))):
            kind = rnd.choice(["spike", "drift", "level_shift", "stuck", "noise"])
            s = rnd.choice(list(sensors))
            run_idx = [i for i in range(n) if state_at[i] == "RUN"]
            if len(run_idx) < 100:
                continue
            i0 = rnd.choice(run_idx[20:-60])
            length = {"spike": rnd.randint(1, 3), "drift": rnd.randint(60, 150), "level_shift": rnd.randint(30, 90),
                      "stuck": rnd.randint(20, 50), "noise": rnd.randint(30, 80)}[kind]
            i1 = min(n, i0 + length)
            plans.append((kind, s, i0, i1))
            truth["anomalies"].append({"equipment": eq, "sensor": s, "kind": kind, "start_idx": i0, "end_idx": i1,
                                       "start": (start + timedelta(seconds=i0 * interval_s)).isoformat(),
                                       "end": (start + timedelta(seconds=i1 * interval_s)).isoformat()})
        stuck_val: Dict[str, float] = {}
        for i in range(n):
            ts = start + timedelta(seconds=i * interval_s)
            st = state_at[i]
            r: Dict = {"timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"), "equipment": eq, "state": st}
            for s, (mu, sd, _) in sensors.items():
                base = mu + offs[s]
                if st == "IDLE":
                    base = mu * 0.6
                elif st == "MAINT":
                    base = mu * 0.3
                v = rnd.gauss(base, sd)
                for kind, ps, i0, i1 in plans:
                    if ps != s or not (i0 <= i < i1):
                        continue
                    if kind == "spike":
                        v += 6 * sd * (1 if rnd.random() < 0.8 else -1)
                    elif kind == "drift":
                        v += 5 * sd * (i - i0) / max(1, i1 - i0)
                    elif kind == "level_shift":
                        v += 4 * sd
                    elif kind == "stuck":
                        v = stuck_val.setdefault("%s%s%d" % (eq, s, i0), round(base, 3))
                    elif kind == "noise":
                        v = rnd.gauss(base, sd * 4)
                r[s] = round(v, 4)
            rows.append(r)

    if quality_issues:
        _inject_quality(rows, truth, rnd, list(sensors), interval_s)
    return rows, truth


def _inject_quality(rows: List[Dict], truth: Dict, rnd: random.Random, sensors: Sequence[str], interval_s: int):
    n = len(rows)
    # 결측
    for _ in range(max(3, n // 400)):
        i, s = rnd.randrange(n), rnd.choice(sensors)
        rows[i][s] = None
        truth["quality"].append({"kind": "missing", "row": i, "sensor": s, "equipment": rows[i]["equipment"], "timestamp": rows[i]["timestamp"]})
    # 중복
    for _ in range(max(2, n // 800)):
        i = rnd.randrange(n)
        rows.insert(i + 1, dict(rows[i]))
        truth["quality"].append({"kind": "duplicate", "row": i + 1, "equipment": rows[i]["equipment"], "timestamp": rows[i]["timestamp"]})
    # 시간 역전 (인접 두 행 교환)
    for _ in range(max(2, n // 1000)):
        i = rnd.randrange(1, len(rows) - 1)
        if rows[i]["equipment"] == rows[i - 1]["equipment"]:
            rows[i], rows[i - 1] = rows[i - 1], rows[i]
            truth["quality"].append({"kind": "reversal", "row": i, "equipment": rows[i]["equipment"], "timestamp": rows[i]["timestamp"]})
    # 수신 끊김 (연속 구간 삭제)
    for _ in range(2):
        i = rnd.randrange(50, len(rows) - 50)
        eq = rows[i]["equipment"]
        k = rnd.randint(6, 20)
        j = i
        removed = 0
        while removed < k and j < len(rows):
            if rows[j]["equipment"] == eq:
                rows.pop(j)
                removed += 1
            else:
                j += 1
        truth["quality"].append({"kind": "gap", "after_row": i - 1, "equipment": eq, "n_removed": removed,
                                 "approx_seconds": removed * interval_s, "timestamp": rows[i - 1]["timestamp"]})


def write(rows: List[Dict], truth: Dict, csv_path: str, truth_path: Optional[str] = None) -> None:
    from .csvio import write_csv
    write_csv(csv_path, rows)
    if truth_path:
        with open(truth_path, "w", encoding="utf-8") as f:
            json.dump(truth, f, ensure_ascii=False, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="합성 센서 데이터 생성")
    ap.add_argument("--out", default="data/synth.csv")
    ap.add_argument("--truth", default=None, help="기본: <out>_truth.json")
    ap.add_argument("--equipment", type=int, default=5)
    ap.add_argument("--minutes", type=int, default=240)
    ap.add_argument("--interval", type=int, default=10)
    ap.add_argument("--anomalies", type=int, default=6)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--clean", action="store_true", help="품질 문제 주입 안 함")
    a = ap.parse_args(argv)
    import os
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    rows, truth = generate(a.equipment, a.minutes, a.interval, a.seed, n_anomalies=a.anomalies, quality_issues=not a.clean)
    tp = a.truth or a.out.rsplit(".", 1)[0] + "_truth.json"
    write(rows, truth, a.out, tp)
    print("rows=%d anomalies=%d quality_issues=%d -> %s, %s" % (len(rows), len(truth["anomalies"]), len(truth["quality"]), a.out, tp))


if __name__ == "__main__":
    main()
