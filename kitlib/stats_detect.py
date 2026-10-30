"""stats_detect — 설명 가능한 통계 기반 이상 탐지 (stdlib only).

언제 쓰나: 담당자가 정상 범위를 숫자로 못 줄 때("평소와 다르면 알려달라"). 임계치 룰(rules.py)의
보조로 쓴다. 모두 단변량·온라인 계산이라 "왜 이상인가"를 숫자로 설명할 수 있다.

탐지기 선택 가이드
  rolling_zscore  갑작스런 스파이크. 최근 window개 평균/표준편차 대비 몇 σ인가.
  ewma            느린 드리프트. 지수가중 이동평균이 기준선에서 k·σ 벗어나면.
  cusum           작은 평균 이동이 누적될 때 (공정 중심 이동). 양/음 누적합이 h를 넘으면.
  iqr_bounds      분포 기반 정적 경계. 정상 구간 데이터로 (Q1-1.5IQR, Q3+1.5IQR)을 구해 rules로 넘긴다.
  rate_of_change  급변(단위시간당 변화량). 온도 급상승 등.
  stuck           센서 고착(값이 n개 연속 동일) — quality.py에도 있지만 값 단위로 쓰고 싶을 때.

반환은 전부 list[dict]이고 각 dict에 index, value, score, flag, reason 이 들어간다.
NaN/None은 건너뛴다(점수 None).
"""
from __future__ import annotations

import math
import statistics
from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple


def _clean(values: Sequence) -> List[Optional[float]]:
    return [float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v)) else None for v in values]


def rolling_zscore(values: Sequence, window: int = 30, threshold: float = 3.0, min_periods: int = 10) -> List[Dict]:
    """직전 window개(현재 제외)의 평균/표준편차로 z-score. |z|>threshold면 flag."""
    xs = _clean(values)
    buf: deque = deque(maxlen=window)
    out = []
    for i, v in enumerate(xs):
        res = {"index": i, "value": v, "score": None, "flag": False, "reason": ""}
        if v is not None and len(buf) >= min_periods:
            m = statistics.fmean(buf)
            sd = statistics.pstdev(buf)
            z = (v - m) / sd if sd > 0 else (0.0 if v == m else math.inf)
            res["score"] = round(z, 3)
            if abs(z) > threshold:
                res["flag"] = True
                res["reason"] = "z=%.2f (mean=%.3f, sd=%.3f, window=%d)" % (z, m, sd, len(buf))
        if v is not None:
            buf.append(v)
        out.append(res)
    return out


def ewma(values: Sequence, alpha: float = 0.2) -> List[Optional[float]]:
    xs = _clean(values)
    s: Optional[float] = None
    out = []
    for v in xs:
        if v is not None:
            s = v if s is None else alpha * v + (1 - alpha) * s
        out.append(s)
    return out


def ewma_detect(values: Sequence, alpha: float = 0.2, k: float = 3.0, baseline_n: int = 50) -> List[Dict]:
    """앞 baseline_n개로 기준 평균/σ를 잡고, EWMA가 mean ± k·σ·sqrt(alpha/(2-alpha)) 를 벗어나면 flag."""
    xs = _clean(values)
    base = [v for v in xs[:baseline_n] if v is not None]
    out = []
    if len(base) < 2:
        return [{"index": i, "value": v, "score": None, "flag": False, "reason": "baseline too short"} for i, v in enumerate(xs)]
    mu, sd = statistics.fmean(base), statistics.pstdev(base)
    lim = k * sd * math.sqrt(alpha / (2 - alpha))
    s: Optional[float] = None
    for i, v in enumerate(xs):
        res = {"index": i, "value": v, "score": None, "flag": False, "reason": ""}
        if v is not None:
            s = v if s is None else alpha * v + (1 - alpha) * s
            dev = s - mu
            res["score"] = round(dev / lim, 3) if lim > 0 else None
            if lim > 0 and abs(dev) > lim and i >= baseline_n:
                res["flag"] = True
                res["reason"] = "ewma=%.3f drift %+.3f beyond ±%.3f (mu=%.3f)" % (s, dev, lim, mu)
        out.append(res)
    return out


def cusum(values: Sequence, target: Optional[float] = None, k: Optional[float] = None,
          h: Optional[float] = None, baseline_n: int = 50) -> List[Dict]:
    """양측 CUSUM. 기본: target=기준 평균, k=0.5σ(허용 슬랙), h=5σ(결정 한계)."""
    xs = _clean(values)
    base = [v for v in xs[:baseline_n] if v is not None]
    if len(base) < 2:
        return [{"index": i, "value": v, "score": None, "flag": False, "reason": "baseline too short"} for i, v in enumerate(xs)]
    mu, sd = statistics.fmean(base), statistics.pstdev(base) or 1e-9
    target = mu if target is None else target
    k = 0.5 * sd if k is None else k
    h = 5.0 * sd if h is None else h
    sp = sn = 0.0
    out = []
    for i, v in enumerate(xs):
        res = {"index": i, "value": v, "score": None, "flag": False, "reason": ""}
        if v is not None:
            sp = max(0.0, sp + (v - target) - k)
            sn = max(0.0, sn + (target - v) - k)
            res["score"] = round(max(sp, sn) / h, 3)
            if sp > h or sn > h:
                res["flag"] = True
                res["reason"] = "cusum %s=%.3f > h=%.3f (target=%.3f)" % ("S+" if sp > h else "S-", max(sp, sn), h, target)
                sp = sn = 0.0  # 알람 후 리셋 (연속 알람 방지)
        out.append(res)
    return out


def iqr_bounds(values: Sequence, k: float = 1.5) -> Tuple[Optional[float], Optional[float], Dict]:
    """(lo, hi, info). 정상 구간 데이터로 계산해 rules.Rule(lo, hi)로 넘긴다."""
    xs = sorted(v for v in _clean(values) if v is not None)
    if len(xs) < 4:
        return None, None, {"n": len(xs)}
    q1, _, q3 = statistics.quantiles(xs, n=4)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr, {"q1": q1, "q3": q3, "iqr": iqr, "n": len(xs)}


def rate_of_change(values: Sequence, seconds: Sequence[float], threshold: float) -> List[Dict]:
    """단위 시간(초)당 변화량 |dv/dt| > threshold 이면 flag. seconds는 각 값의 시각(초)."""
    xs = _clean(values)
    out = []
    prev: Optional[Tuple[float, float]] = None
    for i, (v, t) in enumerate(zip(xs, seconds)):
        res = {"index": i, "value": v, "score": None, "flag": False, "reason": ""}
        if v is not None and t is not None:
            if prev is not None and t > prev[1]:
                rate = (v - prev[0]) / (t - prev[1])
                res["score"] = round(rate, 6)
                if abs(rate) > threshold:
                    res["flag"] = True
                    res["reason"] = "rate=%.4f/s > %.4f" % (rate, threshold)
            prev = (v, t)
        out.append(res)
    return out


def stuck(values: Sequence, n: int = 10) -> List[Dict]:
    xs = _clean(values)
    out, run, last = [], 0, object()
    for i, v in enumerate(xs):
        run = run + 1 if (v is not None and v == last) else 1
        last = v
        flag = v is not None and run >= n
        out.append({"index": i, "value": v, "score": run, "flag": flag,
                    "reason": "same value %r for %d samples" % (v, run) if flag else ""})
    return out


def summarize(results: List[Dict]) -> Dict:
    flags = [r for r in results if r["flag"]]
    return {"n": len(results), "n_flag": len(flags), "first_flag": flags[0]["index"] if flags else None,
            "pct": round(100.0 * len(flags) / max(1, len(results)), 2)}
