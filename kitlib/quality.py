"""quality — 데이터 품질 점검과 처리 정책.

  check_quality(rows, ts_col="_ts", key_cols, value_cols, required_cols, expected_interval, gap_factor=3.0, limits, stuck_n=10)
    → issues[{type,row,key,...}], counts, interval_seconds, summary_md
  issue type: missing / duplicate / time_reversal / gap / out_of_range / stuck / unparsed_time
  apply_policy(rows, issues, policy, ts_col, key_cols, value_cols) → (new_rows(_quality_flags 포함), log)
    duplicate: drop|flag   missing: flag|drop|ffill   time_reversal: sort|drop   out_of_range: flag|null   unparsed_time: drop
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .timeparse import infer_interval, sort_by_time


def _key(r: Dict, key_cols: Sequence[str]) -> Tuple:
    return tuple(r.get(c) for c in key_cols)


def check_quality(rows: List[Dict], ts_col: str = "_ts", key_cols: Sequence[str] = (),
                  value_cols: Sequence[str] = (), required_cols: Sequence[str] = (),
                  expected_interval: Optional[float] = None, gap_factor: float = 3.0,
                  limits: Optional[Dict[str, Tuple[Optional[float], Optional[float]]]] = None,
                  stuck_n: int = 10) -> Dict:
    """rows(원본 순서 유지, 인덱스는 원본 기준)를 점검해 issue 목록과 요약을 돌려준다."""
    limits = limits or {}
    issues: List[Dict] = []
    add = lambda t, i, **d: issues.append(dict(type=t, row=i, **d))  # noqa: E731

    # 1) 결측 / 파싱 실패 / 범위 이탈 — 행 단위
    for i, r in enumerate(rows):
        if ts_col in r and r.get(ts_col) is None:
            add("unparsed_time", i)
        for c in list(required_cols) + list(value_cols):
            if r.get(c) is None:
                add("missing", i, col=c)
        for c, (lo, hi) in limits.items():
            v = r.get(c)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if (lo is not None and v < lo) or (hi is not None and v > hi):
                    add("out_of_range", i, col=c, value=v, lo=lo, hi=hi)

    # 2) 키별 시계열 점검 — 원본 순서대로 보되 시각은 비교
    groups: Dict[Tuple, List[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        groups[_key(r, key_cols)].append(i)

    interval = expected_interval
    if interval is None and ts_col:
        all_t = [rows[i].get(ts_col) for idxs in groups.values() for i in idxs[:2000]]
        interval = infer_interval([t for t in all_t if isinstance(t, datetime)])

    for key, idxs in groups.items():
        seen_ts: Dict[datetime, int] = {}
        prev_t: Optional[datetime] = None
        run_val = {c: (None, 0, None) for c in value_cols}  # col -> (value, count, start_idx)
        for i in idxs:
            r = rows[i]
            t = r.get(ts_col) if ts_col else None
            if isinstance(t, datetime):
                if t in seen_ts:
                    add("duplicate", i, key=key, first_row=seen_ts[t], ts=t)
                else:
                    seen_ts[t] = i
                if prev_t is not None:
                    d = (t - prev_t).total_seconds()
                    if d < 0:
                        add("time_reversal", i, key=key, prev_ts=prev_t, ts=t)
                    elif interval and d > gap_factor * interval:
                        add("gap", i, key=key, prev_ts=prev_t, ts=t, seconds=d)
                prev_t = t
            for c in value_cols:
                v = r.get(c)
                val, cnt, start = run_val[c]
                if v is not None and v == val:
                    cnt += 1
                    if cnt == stuck_n:
                        add("stuck", i, key=key, col=c, value=v, start_row=start, n=cnt)
                    run_val[c] = (val, cnt, start)
                else:
                    run_val[c] = (v, 1, i)

    counts: Dict[str, int] = defaultdict(int)
    for it in issues:
        counts[it["type"]] += 1
    return {
        "issues": issues,
        "counts": dict(counts),
        "interval_seconds": interval,
        "n_rows": len(rows),
        "n_groups": len(groups),
        "summary_md": summary_md(dict(counts), len(rows), interval),
    }


def summary_md(counts: Dict[str, int], n_rows: int, interval: Optional[float]) -> str:
    lines = ["| 점검 항목 | 건수 |", "|---|---|"]
    for t in ("missing", "unparsed_time", "duplicate", "time_reversal", "gap", "out_of_range", "stuck"):
        lines.append("| %s | %d |" % (t, counts.get(t, 0)))
    head = "총 %d행, 추정 샘플링 주기 %s초" % (n_rows, ("%.0f" % interval) if interval else "?")
    return head + "\n\n" + "\n".join(lines)


def apply_policy(rows: List[Dict], issues: List[Dict], policy: Optional[Dict[str, str]] = None,
                 ts_col: str = "_ts", key_cols: Sequence[str] = (),
                 value_cols: Sequence[str] = ()) -> Tuple[List[Dict], List[str]]:
    """issue 목록을 바탕으로 정책을 적용한 새 rows와 처리 로그를 돌려준다. 원본은 바꾸지 않는다."""
    p = {"duplicate": "drop", "missing": "flag", "time_reversal": "sort",
         "out_of_range": "flag", "unparsed_time": "drop"}
    p.update(policy or {})
    log: List[str] = []
    drop = set()
    flagged: Dict[int, List[str]] = defaultdict(list)
    null_cols: Dict[int, set] = defaultdict(set)

    for it in issues:
        t, i = it["type"], it["row"]
        action = p.get(t, "flag")
        if action == "drop":
            drop.add(i)
        elif action == "null" and "col" in it:
            null_cols[i].add(it["col"])
            flagged[i].append("%s:%s->null" % (t, it["col"]))
        else:
            flagged[i].append(t if "col" not in it else "%s:%s" % (t, it["col"]))

    out: List[Dict] = []
    n_null = 0
    for i, r in enumerate(rows):
        if i in drop:
            continue
        nr = dict(r)
        for c in null_cols.get(i, ()):
            nr[c] = None
            n_null += 1
        nr["_quality_flags"] = ";".join(flagged.get(i, []))
        out.append(nr)

    if p.get("missing") == "ffill" and value_cols:
        last: Dict[Tuple, Dict[str, object]] = defaultdict(dict)
        for nr in sort_by_time(out, ts_col, key_cols):
            k = _key(nr, key_cols)
            for c in value_cols:
                if nr.get(c) is None and c in last[k]:
                    nr[c] = last[k][c]
                    nr["_quality_flags"] = (nr["_quality_flags"] + ";ffill:%s" % c).strip(";")
                elif nr.get(c) is not None:
                    last[k][c] = nr[c]

    if p.get("time_reversal") == "sort":
        out = sort_by_time(out, ts_col, key_cols)

    log.append("dropped %d rows (%s)" % (len(drop), ",".join(sorted({it['type'] for it in issues if p.get(it['type'], 'flag') == 'drop'}))))
    log.append("flagged %d rows" % len(flagged))
    if n_null:
        log.append("nullified %d values" % n_null)
    if p.get("time_reversal") == "sort":
        log.append("sorted by (%s, %s)" % (",".join(key_cols) or "-", ts_col))
    return out, log
