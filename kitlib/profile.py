"""profile — 낯선 데이터를 3분 안에 파악하는 요약 (stdlib only).

언제 쓰나: 데이터를 받자마자. 원본을 눈으로 훑는 대신 이 요약을 Codex와 나에게 보여주고,
담당자에게 할 질문(단위? 상태 코드 의미? 결측 이유?)을 뽑는다. 토큰 절약 효과도 크다
(원본 CSV를 통째로 Codex에 읽히지 않는다).

출력: 컬럼별 타입/결측률/고유값/최소·최대·평균·표준편차(숫자) 또는 상위 값(범주),
시각 컬럼이 있으면 범위·추정 주기, 키 컬럼별 행 수.
"""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from .timeparse import infer_interval


def profile(rows: List[Dict], ts_col: Optional[str] = None, key_cols: Sequence[str] = (),
            top_k: int = 5, sample: int = 20000) -> Dict:
    """rows → 요약 dict. 큰 데이터는 앞 sample행만 본다 (속도)."""
    data = rows[:sample]
    cols: List[str] = []
    for r in data:
        for k in r:
            if k not in cols:
                cols.append(k)
    out: Dict = {"n_rows": len(rows), "n_cols": len(cols), "sampled": len(data) < len(rows), "columns": {}}
    for c in cols:
        vals = [r.get(c) for r in data]
        nonnull = [v for v in vals if v is not None]
        nums = [float(v) for v in nonnull if isinstance(v, (int, float)) and not isinstance(v, bool)]
        info: Dict = {
            "missing_pct": round(100.0 * (len(vals) - len(nonnull)) / max(1, len(vals)), 2),
            "unique": len(set(map(str, nonnull))),
        }
        if nonnull and len(nums) >= 0.9 * len(nonnull):
            info["type"] = "numeric"
            info.update(min=min(nums), max=max(nums), mean=round(statistics.fmean(nums), 4),
                        std=round(statistics.pstdev(nums), 4) if len(nums) > 1 else 0.0)
        elif nonnull and all(isinstance(v, datetime) for v in nonnull):
            info["type"] = "datetime"
            info.update(min=str(min(nonnull)), max=str(max(nonnull)))
        else:
            info["type"] = "categorical"
            info["top"] = Counter(map(str, nonnull)).most_common(top_k)
        out["columns"][c] = info
    if ts_col and any(isinstance(r.get(ts_col), datetime) for r in data):
        ts = [r.get(ts_col) for r in data if isinstance(r.get(ts_col), datetime)]
        out["time"] = {"col": ts_col, "min": str(min(ts)), "max": str(max(ts)),
                       "interval_seconds": infer_interval(ts), "n_parsed": len(ts)}
    if key_cols:
        cnt = Counter(tuple(str(r.get(k)) for k in key_cols) for r in data)
        out["keys"] = {"cols": list(key_cols), "n_groups": len(cnt), "rows_per_group": cnt.most_common(top_k)}
    return out


def to_markdown(p: Dict) -> str:
    lines = ["**행 %d × 열 %d**%s" % (p["n_rows"], p["n_cols"], " (샘플 기준)" if p.get("sampled") else ""), ""]
    if "time" in p:
        t = p["time"]
        iv = t.get("interval_seconds")
        lines += ["시간: `%s` %s ~ %s, 추정 주기 %s초, 파싱 %d건" % (t["col"], t["min"], t["max"], ("%.0f" % iv) if iv else "?", t["n_parsed"]), ""]
    if "keys" in p:
        k = p["keys"]
        lines += ["키 %s: 그룹 %d개, 상위 %s" % (k["cols"], k["n_groups"], k["rows_per_group"]), ""]
    lines += ["| 컬럼 | 타입 | 결측% | 고유 | 요약 |", "|---|---|---|---|---|"]
    for c, i in p["columns"].items():
        if i["type"] == "numeric":
            s = "min %s / max %s / mean %s / std %s" % (i["min"], i["max"], i["mean"], i["std"])
        elif i["type"] == "datetime":
            s = "%s ~ %s" % (i["min"], i["max"])
        else:
            s = ", ".join("%s(%d)" % (v, n) for v, n in i.get("top", []))
        lines.append("| %s | %s | %s | %s | %s |" % (c, i["type"], i["missing_pct"], i["unique"], s))
    return "\n".join(lines)


def questions_from_profile(p: Dict) -> List[str]:
    """프로파일에서 담당자에게 물을 질문 후보를 자동 생성한다."""
    qs: List[str] = []
    for c, i in p["columns"].items():
        if i["missing_pct"] > 0:
            qs.append("`%s` 결측 %.1f%%는 수집 실패인가요, 해당 없음인가요? (처리 정책 확정 필요)" % (c, i["missing_pct"]))
        if i["type"] == "categorical" and i["unique"] <= 10:
            qs.append("`%s` 값 %s 각각의 의미와, 판정에서 제외할 값이 있나요?" % (c, [v for v, _ in i.get("top", [])]))
        if i["type"] == "numeric":
            qs.append("`%s` 단위와 물리적으로 가능한 범위(min %s~max %s 관측)는요? 정상 운전 기준이 있나요?" % (c, i["min"], i["max"]))
    if "time" in p and p["time"].get("interval_seconds"):
        qs.append("샘플링 주기가 %.0f초로 보이는데 맞나요? 몇 배 이상 끊기면 '수신 장애'로 볼까요?" % p["time"]["interval_seconds"])
    return qs
