"""reconcile — 두 자료 대사.

  compare(rows_a, rows_b, key_cols, compare_cols, tol={col: 허용오차}, upper=False, strip_zeros=False)
    → only_in_a / only_in_b / mismatch / dup_a / dup_b / summary
  normalize_key(value, upper, strip_zeros)   공백 제거·대문자·선행 0 제거
  summary_markdown(diff)
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple


def normalize_key(v, upper: bool = True, strip_zeros: bool = False) -> str:
    s = "" if v is None else str(v).strip()
    s = " ".join(s.split())          # 내부 다중 공백 → 1칸
    if upper:
        s = s.upper()
    if strip_zeros and s.isdigit():
        s = s.lstrip("0") or "0"
    return s


def _key(r: Dict, key_cols: Sequence[str], **opt) -> Tuple:
    return tuple(normalize_key(r.get(c), **opt) for c in key_cols)


def _eq(a, b, tol: Optional[float]) -> bool:
    if a is None and b is None:
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(float(a) - float(b)) <= (tol or 0.0)
    return normalize_key(a) == normalize_key(b)


def compare(rows_a: List[Dict], rows_b: List[Dict], key_cols: Sequence[str], compare_cols: Optional[Sequence[str]] = None,
            tol: Optional[Dict[str, float]] = None, upper: bool = True, strip_zeros: bool = False) -> Dict:
    """키 기준으로 A·B를 대사한다. compare_cols가 None이면 공통 컬럼 전부(키 제외)."""
    tol = tol or {}
    opt = dict(upper=upper, strip_zeros=strip_zeros)
    ia: Dict[Tuple, Dict] = {}
    ib: Dict[Tuple, Dict] = {}
    dup_a = [k for k, n in Counter(_key(r, key_cols, **opt) for r in rows_a).items() if n > 1]
    dup_b = [k for k, n in Counter(_key(r, key_cols, **opt) for r in rows_b).items() if n > 1]
    for r in rows_a:
        ia.setdefault(_key(r, key_cols, **opt), r)   # 중복이면 첫 행 기준 (dup 목록으로 따로 보고)
    for r in rows_b:
        ib.setdefault(_key(r, key_cols, **opt), r)
    if compare_cols is None:
        ca = set().union(*(r.keys() for r in rows_a[:1])) if rows_a else set()
        cb = set().union(*(r.keys() for r in rows_b[:1])) if rows_b else set()
        compare_cols = sorted((ca & cb) - set(key_cols))
    only_a = [dict(zip(key_cols, k)) for k in ia if k not in ib]
    only_b = [dict(zip(key_cols, k)) for k in ib if k not in ia]
    mismatch = []
    matched = 0
    for k in ia:
        if k not in ib:
            continue
        matched += 1
        ra, rb = ia[k], ib[k]
        for c in compare_cols:
            if not _eq(ra.get(c), rb.get(c), tol.get(c)):
                d = dict(zip(key_cols, k))
                d.update(column=c, a=ra.get(c), b=rb.get(c))
                mismatch.append(d)
    by_col = Counter(m["column"] for m in mismatch)
    summary = {"n_a": len(rows_a), "n_b": len(rows_b), "keys_a": len(ia), "keys_b": len(ib), "matched_keys": matched,
               "only_in_a": len(only_a), "only_in_b": len(only_b), "mismatch_rows": len({tuple(m[c] for c in key_cols) for m in mismatch}),
               "mismatch_cells": len(mismatch), "mismatch_by_column": dict(by_col), "dup_a": len(dup_a), "dup_b": len(dup_b),
               "normalization": "strip+collapse_ws" + ("+upper" if upper else "") + ("+strip_zeros" if strip_zeros else ""),
               "tolerance": tol, "compare_cols": list(compare_cols)}
    return {"only_in_a": only_a, "only_in_b": only_b, "mismatch": mismatch, "dup_a": dup_a, "dup_b": dup_b, "summary": summary}


def summary_markdown(diff: Dict) -> str:
    s = diff["summary"]
    lines = ["| 항목 | 값 |", "|---|---|"]
    for k in ("n_a", "n_b", "keys_a", "keys_b", "matched_keys", "only_in_a", "only_in_b", "mismatch_rows", "mismatch_cells", "dup_a", "dup_b", "normalization", "tolerance"):
        lines.append("| %s | %s |" % (k, s[k]))
    if s["mismatch_by_column"]:
        lines.append("")
        lines.append("불일치 컬럼별: " + ", ".join("%s=%d" % kv for kv in sorted(s["mismatch_by_column"].items(), key=lambda x: -x[1])))
    return "\n".join(lines)
