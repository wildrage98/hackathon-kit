"""alerts — 경보 상태머신.

  AlertManager(open_after=N, close_after=M).feed(key, ts, level, reason)
    level None=정상, 'WARN'/'CRIT'… (rules.SEVERITY 순서)
    N회 연속 이상 → START, M회 연속 정상 → END, 등급 변화 → ESCALATE/DEESCALATE, 종료 후 재발 → 새 alert_id
  .events / .active() / .close_all() / .to_rows()
  run_from_levels(rows, key_cols, ts_col, level_col, reason_col, open_after, close_after)
이벤트: dict(event, alert_id, key, ts, level, prev_level, reason, duration_s)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .rules import sev_rank


class AlertManager:
    def __init__(self, open_after: int = 1, close_after: int = 1):
        self.open_after = max(1, open_after)
        self.close_after = max(1, close_after)
        self._state: Dict[Any, Dict] = {}
        self.events: List[Dict] = []
        self._seq = 0

    def _emit(self, event: str, st: Dict, key, ts, level, reason, prev_level=None):
        dur = None
        if st.get("start_ts") is not None and isinstance(ts, datetime) and isinstance(st["start_ts"], datetime):
            dur = (ts - st["start_ts"]).total_seconds()
        self.events.append(dict(event=event, alert_id=st.get("id"), key=key, ts=ts, level=level,
                                prev_level=prev_level, reason=reason, duration_s=dur))

    def feed(self, key, ts, level: Optional[str], reason: str = "") -> Optional[Dict]:
        """한 관측을 넣고, 이벤트가 발생했으면 그 이벤트를 돌려준다."""
        st = self._state.setdefault(key, {"id": None, "level": None, "bad": 0, "good": 0,
                                          "start_ts": None, "pending_level": None, "pending_reason": ""})
        before = len(self.events)
        if level is not None:
            st["bad"] += 1
            st["good"] = 0
            if st["id"] is None:
                # 아직 열린 경보 없음: 연속 횟수 채우면 START
                if sev_rank(level) > sev_rank(st["pending_level"]):
                    st["pending_level"], st["pending_reason"] = level, reason
                if st["bad"] >= self.open_after:
                    self._seq += 1
                    st.update(id="A%04d" % self._seq, level=st["pending_level"], start_ts=ts)
                    self._emit("START", st, key, ts, st["level"], st["pending_reason"] or reason)
                    st["pending_level"], st["pending_reason"] = None, ""
            else:
                if sev_rank(level) > sev_rank(st["level"]):
                    prev, st["level"] = st["level"], level
                    self._emit("ESCALATE", st, key, ts, level, reason, prev)
                elif sev_rank(level) < sev_rank(st["level"]):
                    prev, st["level"] = st["level"], level
                    self._emit("DEESCALATE", st, key, ts, level, reason, prev)
        else:
            st["good"] += 1
            st["bad"] = 0
            st["pending_level"], st["pending_reason"] = None, ""
            if st["id"] is not None and st["good"] >= self.close_after:
                self._emit("END", st, key, ts, st["level"], "normal for %d samples" % st["good"])
                st.update(id=None, level=None, start_ts=None, good=0)
        return self.events[-1] if len(self.events) > before else None

    def active(self) -> Dict[Any, Dict]:
        return {k: dict(alert_id=v["id"], level=v["level"], since=v["start_ts"]) for k, v in self._state.items() if v["id"]}

    def close_all(self, ts, reason: str = "end of data"):
        """데이터 끝에서 열린 경보를 명시적으로 닫을지 말지는 정책. 닫으면 END(reason) 이벤트."""
        for k, st in self._state.items():
            if st["id"] is not None:
                self._emit("END", st, k, ts, st["level"], reason)
                st.update(id=None, level=None, start_ts=None, good=0, bad=0)

    def to_rows(self) -> List[Dict]:
        """CSV 저장용 (ts를 문자열로)."""
        out = []
        for e in self.events:
            d = dict(e)
            d["ts"] = d["ts"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(d["ts"], datetime) else d["ts"]
            d["key"] = "|".join(map(str, d["key"])) if isinstance(d["key"], tuple) else d["key"]
            out.append(d)
        return out


def run_from_levels(rows: List[Dict], key_cols, ts_col: str = "_ts", level_col: str = "_level",
                    reason_col: str = "_hits", open_after: int = 1, close_after: int = 1) -> AlertManager:
    """rules.evaluate_series 결과(rows에 _level/_hits가 있는 상태)를 한 번에 먹인다."""
    am = AlertManager(open_after, close_after)
    for r in rows:
        key = tuple(r.get(c) for c in key_cols) if key_cols else ("ALL",)
        hits = r.get(reason_col) or []
        reason = "; ".join(h.get("reason", "") for h in hits if h.get("confirmed", True)) if isinstance(hits, list) else str(hits)
        am.feed(key, r.get(ts_col), r.get(level_col), reason)
    return am
