"""timeparse — 타임스탬프 파싱.

  parse_ts(value, default_tz=None) → datetime|None   ('Z', ±HH:MM, ±HHMM, epoch 초/밀리초, YYYYMMDDHHMMSS, 여러 strptime 형식)
  add_parsed_time(rows, col, out="_ts", default_tz=None, unify="naive") → {parsed, failed}   aware/naive 통일
  sort_by_time(rows, ts_col), infer_interval(ts_list), fmt(dt), KST
"""
from __future__ import annotations

import re
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

_OFFSET = re.compile(r"([+-])(\d{2}):?(\d{2})$")
_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%Y%m%d%H%M%S", "%Y%m%d %H%M%S", "%Y%m%d",
    "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M",
)
KST = timezone(timedelta(hours=9))


def parse_ts(value, default_tz: Optional[timezone] = None) -> Optional[datetime]:
    """문자열/숫자 → datetime. 실패하면 None (예외를 던지지 않는다: 품질 점검 단계에서 센다)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        v = float(value)
        if v > 1e11:  # 밀리초 epoch (2001년 이후 값은 1e12 근처)
            v /= 1000.0
        dt = datetime.fromtimestamp(v, tz=timezone.utc)
    else:
        s = str(value).strip()
        if not s:
            return None
        if re.fullmatch(r"\d{10}(\.\d+)?|\d{13}", s):  # 숫자 문자열 epoch
            return parse_ts(float(s), default_tz)
        tz = None
        if s.endswith("Z") or s.endswith("z"):
            tz, s = timezone.utc, s[:-1]
        else:
            m = _OFFSET.search(s)
            if m and ("T" in s or " " in s or ":" in s):
                sign = 1 if m.group(1) == "+" else -1
                tz = timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))
                s = s[: m.start()]
        s = s.replace("T", " ")
        dt = None
        for fmt in _FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return None
        if tz is not None:
            dt = dt.replace(tzinfo=tz)
    if dt.tzinfo is None and default_tz is not None:
        dt = dt.replace(tzinfo=default_tz)
    return dt


def add_parsed_time(rows: List[Dict], col: str, out: str = "_ts",
                    default_tz: Optional[timezone] = None, unify: str = "naive") -> Dict[str, int]:
    """각 행에 row[out] = datetime을 넣는다. aware/naive가 섞이면 unify('naive'|'utc')로 통일.
    반환: {'parsed': n, 'failed': n}. 실패한 행은 out=None (quality에서 결측으로 잡힌다)."""
    parsed = failed = 0
    for r in rows:
        dt = parse_ts(r.get(col), default_tz)
        if dt is None:
            failed += 1
        else:
            parsed += 1
            if unify == "naive" and dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None) if default_tz is None else dt.astimezone(default_tz).replace(tzinfo=None)
            elif unify == "utc":
                dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        r[out] = dt
    return {"parsed": parsed, "failed": failed}


def sort_by_time(rows: List[Dict], ts_col: str = "_ts", key_cols: Iterable[str] = ()) -> List[Dict]:
    """키(설비 등) → 시각 순으로 안정 정렬. 시각이 None인 행은 맨 뒤로."""
    key_cols = list(key_cols)

    def k(r):
        t = r.get(ts_col)
        return tuple(str(r.get(c)) for c in key_cols) + ((t is None), t or datetime.min)

    return sorted(rows, key=k)


def infer_interval(times: List[datetime]) -> Optional[float]:
    """연속 시각 차이의 중앙값(초). 샘플링 주기 추정 → 수신 끊김 판정 기준으로 쓴다."""
    ts = [t for t in times if t is not None]
    if len(ts) < 2:
        return None
    ts = sorted(ts)
    diffs = [(b - a).total_seconds() for a, b in zip(ts, ts[1:]) if (b - a).total_seconds() > 0]
    return statistics.median(diffs) if diffs else None


def fmt(dt: Optional[datetime]) -> str:
    return "" if dt is None else dt.strftime("%Y-%m-%d %H:%M:%S")
