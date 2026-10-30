"""groupstats — 이진 결과(양/불량) × 요인 컬럼 집계.

  rate_by(rows, group_col|fn, flag_col, min_n) → [{group, n, bad, rate, lift}]  (rate 내림차순)
  chi_square(table) → chi2, dof, sig_0.05, sig_0.01, low_expected_cells
  rank_factors(rows, factors, flag_col, min_n) → 요인별 chi2 순위 + worst_group/rate/lift
  numeric_compare(rows, col, flag_col) → 양/불량 평균·표준편차, Cohen's d
  crosstab(rows, a, b, flag_col), crosstab_markdown(ct)
불량 토큰: BAD_TOKENS / GOOD_TOKENS (_is_bad)
"""
from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from typing import Callable, Dict, List, Optional, Sequence, Union

# 자유도별 카이제곱 임계값 (유의수준 0.05 / 0.01)
_CHI_CRIT = {1: (3.841, 6.635), 2: (5.991, 9.210), 3: (7.815, 11.345), 4: (9.488, 13.277), 5: (11.070, 15.086),
             6: (12.592, 16.812), 7: (14.067, 18.475), 8: (15.507, 20.090), 9: (16.919, 21.666), 10: (18.307, 23.209)}


BAD_TOKENS = {"1", "Y", "YES", "TRUE", "FAIL", "NG", "BAD", "DEFECT", "REJECT", "불량", "실패", "부적합"}
GOOD_TOKENS = {"0", "N", "NO", "FALSE", "PASS", "OK", "GOOD", "양품", "정상", "적합"}


def _is_bad(flag: Union[str, Callable], r: Dict) -> Optional[bool]:
    """불량이면 True, 양품이면 False, 판단 불가면 None. flag는 컬럼명 또는 row->bool 함수."""
    v = flag(r) if callable(flag) else r.get(flag)
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip().upper()
        if s in BAD_TOKENS:
            return True
        if s in GOOD_TOKENS:
            return False
        return None
    return bool(v)


def rate_by(rows: List[Dict], group_col: str, flag: Union[str, Callable], min_n: int = 1) -> List[Dict]:
    """그룹별 n/bad/rate/lift(전체 대비 배수). rate 내림차순."""
    tot_n = tot_b = 0
    n: Counter = Counter()
    b: Counter = Counter()
    for r in rows:
        bad = _is_bad(flag, r)
        if bad is None:
            continue
        g = r.get(group_col)
        n[g] += 1
        b[g] += int(bad)
        tot_n += 1
        tot_b += int(bad)
    overall = tot_b / tot_n if tot_n else 0.0
    out = []
    for g in n:
        if n[g] < min_n:
            continue
        rate = b[g] / n[g]
        out.append({"group": g, "n": n[g], "bad": b[g], "rate": round(rate, 4),
                    "lift": round(rate / overall, 2) if overall > 0 else None,
                    "share_of_bad": round(b[g] / tot_b, 4) if tot_b else 0.0})
    out.sort(key=lambda d: (-d["rate"], -d["n"]))
    return out


def chi_square(table: Sequence[Sequence[int]]) -> Dict:
    """r×c 분할표 → chi2, dof, 유의 여부(0.05/0.01 임계값 비교). 기대도수<5 셀이 많으면 경고."""
    rows_ = [list(map(float, r)) for r in table]
    R, C = len(rows_), len(rows_[0])
    row_t = [sum(r) for r in rows_]
    col_t = [sum(rows_[i][j] for i in range(R)) for j in range(C)]
    N = sum(row_t)
    chi2, low_expected = 0.0, 0
    for i in range(R):
        for j in range(C):
            e = row_t[i] * col_t[j] / N if N else 0
            if e > 0:
                chi2 += (rows_[i][j] - e) ** 2 / e
            if e < 5:
                low_expected += 1
    dof = (R - 1) * (C - 1)
    crit = _CHI_CRIT.get(dof)
    return {"chi2": round(chi2, 3), "dof": dof, "n": N,
            "sig_0.05": (chi2 > crit[0]) if crit else None, "sig_0.01": (chi2 > crit[1]) if crit else None,
            "low_expected_cells": low_expected,
            "note": "dof>10: 임계값 표 없음, chi2만 참고" if not crit else ("기대도수<5 셀 있음: 해석 주의" if low_expected else "")}


def rank_factors(rows: List[Dict], factor_cols: Sequence[str], flag: Union[str, Callable], min_n: int = 10) -> List[Dict]:
    """요인 컬럼별로 (최대 lift, chi2) 를 계산해 설명력 순으로 정렬."""
    out = []
    for col in factor_cols:
        groups = rate_by(rows, col, flag, min_n=min_n)
        if len(groups) < 2:
            continue
        table = [[g["bad"], g["n"] - g["bad"]] for g in groups]
        chi = chi_square(table)
        worst = groups[0]
        out.append({"factor": col, "n_groups": len(groups), "chi2": chi["chi2"], "dof": chi["dof"],
                    "sig_0.05": chi["sig_0.05"], "worst_group": worst["group"], "worst_rate": worst["rate"],
                    "worst_lift": worst["lift"], "worst_n": worst["n"]})
    out.sort(key=lambda d: -(d["chi2"] or 0))
    return out


def numeric_compare(rows: List[Dict], value_col: str, flag: Union[str, Callable]) -> Dict:
    """수치 변수의 양품/불량 분포 차이. Cohen's d: 0.2 작음, 0.5 중간, 0.8 큼."""
    good, bad = [], []
    for r in rows:
        v, b = r.get(value_col), _is_bad(flag, r)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and b is not None:
            (bad if b else good).append(float(v))
    if len(good) < 2 or len(bad) < 2:
        return {"col": value_col, "n_good": len(good), "n_bad": len(bad), "d": None}
    mg, mb = statistics.fmean(good), statistics.fmean(bad)
    sg, sb = statistics.pstdev(good), statistics.pstdev(bad)
    pooled = math.sqrt((sg ** 2 + sb ** 2) / 2) or 1e-9
    return {"col": value_col, "n_good": len(good), "n_bad": len(bad),
            "mean_good": round(mg, 4), "mean_bad": round(mb, 4), "median_good": statistics.median(good),
            "median_bad": statistics.median(bad), "d": round((mb - mg) / pooled, 3)}


def crosstab(rows: List[Dict], row_col: str, col_col: str, flag: Union[str, Callable]) -> Dict:
    """두 요인 교차 불량률 표. 반환: {'rows': [...], 'cols': [...], 'cells': {(r,c): {'n','bad','rate'}}}"""
    cells: Dict = defaultdict(lambda: {"n": 0, "bad": 0})
    for r in rows:
        b = _is_bad(flag, r)
        if b is None:
            continue
        k = (r.get(row_col), r.get(col_col))
        cells[k]["n"] += 1
        cells[k]["bad"] += int(b)
    for v in cells.values():
        v["rate"] = round(v["bad"] / v["n"], 4) if v["n"] else None
    rs = sorted({k[0] for k in cells}, key=str)
    cs = sorted({k[1] for k in cells}, key=str)
    return {"rows": rs, "cols": cs, "cells": dict(cells)}


def crosstab_markdown(ct: Dict, metric: str = "rate") -> str:
    lines = ["| | " + " | ".join(map(str, ct["cols"])) + " |", "|---|" + "---|" * len(ct["cols"])]
    for r in ct["rows"]:
        cells = []
        for c in ct["cols"]:
            v = ct["cells"].get((r, c))
            cells.append("" if not v else ("%s (n=%d)" % (v[metric], v["n"])))
        lines.append("| %s | " % r + " | ".join(cells) + " |")
    return "\n".join(lines)
