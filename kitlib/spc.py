"""spc — 관리도·공정능력.

  imr_limits(values) → mean, ucl, lcl, sigma_est (MRbar/1.128, ±2.66·MRbar)
  xbar_r_limits(subgroups) → n=2~10, A2/D3/D4
  western_electric(values, mean, sigma) → [{index, z, rules:[1..4]}]
  cp_cpk(values, lsl, usl) → cp, cpk, mean, sigma, verdict
"""
from __future__ import annotations

import statistics
from typing import Dict, List, Optional, Sequence, Tuple

# n: (A2, D3, D4) — Xbar-R 관리도 상수
_CONST = {2: (1.880, 0.0, 3.267), 3: (1.023, 0.0, 2.574), 4: (0.729, 0.0, 2.282), 5: (0.577, 0.0, 2.114),
          6: (0.483, 0.0, 2.004), 7: (0.419, 0.076, 1.924), 8: (0.373, 0.136, 1.864),
          9: (0.337, 0.184, 1.816), 10: (0.308, 0.223, 1.777)}


def _nums(values: Sequence) -> List[float]:
    return [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]


def imr_limits(values: Sequence) -> Dict:
    """개별값 관리도. 반환: mean, ucl, lcl, sigma_est(=MRbar/1.128), mr_bar, mr_ucl."""
    xs = _nums(values)
    if len(xs) < 3:
        raise ValueError("need >= 3 values")
    mrs = [abs(b - a) for a, b in zip(xs, xs[1:])]
    mr_bar = statistics.fmean(mrs)
    mean = statistics.fmean(xs)
    sigma = mr_bar / 1.128
    return {"mean": mean, "ucl": mean + 2.66 * mr_bar, "lcl": mean - 2.66 * mr_bar,
            "sigma_est": sigma, "mr_bar": mr_bar, "mr_ucl": 3.267 * mr_bar, "n": len(xs)}


def xbar_r_limits(subgroups: Sequence[Sequence[float]]) -> Dict:
    """부분군 리스트 → Xbar/R 관리한계. 모든 부분군 크기가 같아야 한다 (2~10)."""
    groups = [_nums(g) for g in subgroups if len(_nums(g)) >= 2]
    if not groups:
        raise ValueError("no valid subgroups")
    n = len(groups[0])
    if n not in _CONST or any(len(g) != n for g in groups):
        raise ValueError("subgroup size must be equal and in 2..10")
    a2, d3, d4 = _CONST[n]
    xbars = [statistics.fmean(g) for g in groups]
    ranges = [max(g) - min(g) for g in groups]
    xbb, rbar = statistics.fmean(xbars), statistics.fmean(ranges)
    return {"n": n, "k": len(groups), "xbar_bar": xbb, "r_bar": rbar,
            "x_ucl": xbb + a2 * rbar, "x_lcl": xbb - a2 * rbar, "r_ucl": d4 * rbar, "r_lcl": d3 * rbar,
            "xbars": xbars, "ranges": ranges}


def western_electric(values: Sequence, mean: float, sigma: float) -> List[Dict]:
    """각 인덱스에서 걸린 룰 목록. 반환 dict: index, value, rules(list[int]), reason."""
    xs = _nums(values)
    out = []
    if sigma <= 0:
        return [{"index": i, "value": v, "rules": [], "reason": "sigma<=0"} for i, v in enumerate(xs)]
    z = [(v - mean) / sigma for v in xs]
    for i in range(len(xs)):
        rules = []
        if abs(z[i]) > 3:
            rules.append(1)
        w = z[max(0, i - 2): i + 1]
        if len(w) == 3 and (sum(1 for a in w if a > 2) >= 2 or sum(1 for a in w if a < -2) >= 2):
            rules.append(2)
        w = z[max(0, i - 4): i + 1]
        if len(w) == 5 and (sum(1 for a in w if a > 1) >= 4 or sum(1 for a in w if a < -1) >= 4):
            rules.append(3)
        w = z[max(0, i - 7): i + 1]
        if len(w) == 8 and (all(a > 0 for a in w) or all(a < 0 for a in w)):
            rules.append(4)
        out.append({"index": i, "value": xs[i], "z": round(z[i], 3), "rules": rules,
                    "reason": ("WE rule %s" % rules) if rules else ""})
    return out


def cp_cpk(values: Sequence, lsl: Optional[float], usl: Optional[float]) -> Dict:
    xs = _nums(values)
    if len(xs) < 2:
        raise ValueError("need >= 2 values")
    mu, sd = statistics.fmean(xs), statistics.stdev(xs)
    res: Dict = {"mean": mu, "std": sd, "n": len(xs), "cp": None, "cpk": None}
    if sd <= 0:
        return res
    cpu = (usl - mu) / (3 * sd) if usl is not None else None
    cpl = (mu - lsl) / (3 * sd) if lsl is not None else None
    if usl is not None and lsl is not None:
        res["cp"] = (usl - lsl) / (6 * sd)
    sides = [c for c in (cpu, cpl) if c is not None]
    res["cpk"] = min(sides) if sides else None
    res["verdict"] = None if res["cpk"] is None else ("양호(>=1.33)" if res["cpk"] >= 1.33 else "보통(1.0~1.33)" if res["cpk"] >= 1.0 else "부족(<1.0)")
    return res
