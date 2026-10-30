"""rules — 설명 가능한 임계치 판정 엔진 (stdlib only).

언제 쓰나: "정상 범위를 벗어나면 경보", "스펙 in/out 판정", "조건별 등급 분류", "출하 가능/불가"
같이 기준이 숫자/범주로 주어지는 모든 과제. ML보다 먼저 이것으로 기준선을 만든다 —
담당자가 준 기준을 그대로 코드화하므로 판단 근거를 100% 설명할 수 있다.

설계 포인트 (서술형 단골)
- 경계값: inclusive=(True, True)면 lo<=v<=hi 가 정상. "기준값과 정확히 같을 때"를 명시적으로 다룬다.
- 등급: severity 문자열은 SEVERITY 순서로 비교한다 (INFO < WARN < CRIT). 여러 룰이 걸리면 최고 등급.
- 지속 조건: min_consecutive=N 이면 같은 키에서 N회 연속 위반해야 '확정'(단발 노이즈 억제).
- 상태별 기준: when={'state': 'RUN'} 처럼 조건이 맞는 행에만 룰을 적용한다 (정비 중엔 판정 안 함).
- 근거: Hit에 값·기준·룰 이름·메시지가 남는다 → 리포트/대시보드에 그대로 노출.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SEVERITY = ["INFO", "WARN", "CRIT"]


def sev_rank(s: Optional[str]) -> int:
    return SEVERITY.index(s) if s in SEVERITY else -1


def max_sev(a: Optional[str], b: Optional[str]) -> Optional[str]:
    return a if sev_rank(a) >= sev_rank(b) else b


@dataclass
class Rule:
    name: str
    column: str
    lo: Optional[float] = None          # None이면 하한 없음
    hi: Optional[float] = None          # None이면 상한 없음
    inclusive: Tuple[bool, bool] = (True, True)  # (lo 포함, hi 포함) → 포함이면 경계값은 정상
    severity: str = "WARN"
    when: Dict[str, Any] = field(default_factory=dict)   # 이 조건이 맞는 행에만 적용 (예: {'equipment':'E1','state':'RUN'})
    min_consecutive: int = 1            # N회 연속 위반해야 확정
    message: str = ""                   # 비어 있으면 자동 생성
    allowed: Optional[Sequence[Any]] = None  # 범주형: 이 값들만 정상

    def applies(self, row: Dict) -> bool:
        return all(row.get(k) == v for k, v in self.when.items())

    def violation(self, row: Dict) -> Optional[str]:
        """위반이면 이유 문자열, 정상이면 None. 값이 없으면 판정하지 않는다(None)."""
        v = row.get(self.column)
        if v is None:
            return None
        if self.allowed is not None:
            return None if v in self.allowed else "%s=%r not in %s" % (self.column, v, list(self.allowed))
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return None
        lo_in, hi_in = self.inclusive
        if self.lo is not None and (v < self.lo if lo_in else v <= self.lo):
            return "%s=%g %s lo=%g" % (self.column, v, "<" if lo_in else "<=", self.lo)
        if self.hi is not None and (v > self.hi if hi_in else v >= self.hi):
            return "%s=%g %s hi=%g" % (self.column, v, ">" if hi_in else ">=", self.hi)
        return None


@dataclass
class Hit:
    rule: str
    column: str
    severity: str
    value: Any
    reason: str
    consecutive: int = 1
    confirmed: bool = True   # min_consecutive 충족 여부

    def as_dict(self) -> Dict:
        return dict(rule=self.rule, column=self.column, severity=self.severity, value=self.value,
                    reason=self.reason, consecutive=self.consecutive, confirmed=self.confirmed)


def evaluate_row(row: Dict, rules: Iterable[Rule]) -> List[Hit]:
    """한 행에 대한 모든 위반(지속조건 미적용). 단건 판정/스펙 검사에 쓴다."""
    hits = []
    for rule in rules:
        if not rule.applies(row):
            continue
        reason = rule.violation(row)
        if reason:
            hits.append(Hit(rule.name, rule.column, rule.severity, row.get(rule.column),
                            rule.message or reason))
    return hits


def evaluate_series(rows: List[Dict], rules: Sequence[Rule], key_cols: Sequence[str] = (),
                    out_col: str = "_hits", level_col: str = "_level") -> List[Dict]:
    """시간순으로 정렬된 rows에 대해 키별 연속 위반 횟수를 세며 판정한다.
    row[out_col] = [Hit dict...], row[level_col] = 확정된 최고 등급(없으면 None)."""
    streak: Dict[Tuple, Dict[str, int]] = {}
    for r in rows:
        k = tuple(r.get(c) for c in key_cols)
        st = streak.setdefault(k, {})
        hits: List[Hit] = []
        level: Optional[str] = None
        for rule in rules:
            if not rule.applies(r):
                continue
            reason = rule.violation(r)
            if reason:
                st[rule.name] = st.get(rule.name, 0) + 1
                h = Hit(rule.name, rule.column, rule.severity, r.get(rule.column),
                        rule.message or reason, st[rule.name], st[rule.name] >= rule.min_consecutive)
                hits.append(h)
                if h.confirmed:
                    level = max_sev(level, rule.severity)
            elif r.get(rule.column) is not None:   # 값이 있고 정상이면 연속 카운트 리셋
                st[rule.name] = 0
        r[out_col] = [h.as_dict() for h in hits]
        r[level_col] = level
    return rows


def load_rules(obj) -> List[Rule]:
    """JSON(list of dict) 또는 파일 경로 → Rule 목록. config/rules.json으로 기준을 외부화할 때."""
    if isinstance(obj, str):
        with open(obj, "r", encoding="utf-8") as f:
            obj = json.load(f)
    rules = []
    for d in obj:
        d = dict(d)
        if "inclusive" in d:
            d["inclusive"] = tuple(d["inclusive"])
        rules.append(Rule(**d))
    return rules


def rules_to_markdown(rules: Iterable[Rule]) -> str:
    lines = ["| 룰 | 컬럼 | 하한 | 상한 | 경계포함 | 등급 | 조건 | 연속 |", "|---|---|---|---|---|---|---|---|"]
    for r in rules:
        rng = "allowed=%s" % list(r.allowed) if r.allowed is not None else ""
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %d |" % (
            r.name, r.column, r.lo if r.lo is not None else "", r.hi if r.hi is not None else "",
            r.inclusive, r.severity, r.when or rng, r.min_consecutive))
    return "\n".join(lines)
