"""logparse — 텍스트 로그 파싱·분류·집계 (stdlib only).

언제 쓰나: 설비 로그/알람 로그/정비 메모처럼 **비정형 텍스트 줄**이 입력일 때.
"에러 코드별 건수", "설비별 알람 빈도", "메모를 카테고리로 분류", "특정 패턴 전후 추적".

  PatternSet.add(name, regex)  이름 있는 그룹 (?P<ts>...) (?P<level>...) 으로 필드 추출
  parse_lines(lines, ps)       매칭된 dict 목록 + 매칭 안 된 줄 (unmatched는 반드시 보고한다)
  classify_text(text, cats)    키워드/정규식 사전으로 카테고리 + 근거(어떤 단어가 걸렸나)
  aggregate(rows, by)          groupby count
  context_window(lines, pred)  조건 줄 전후 N줄 (원인 추적용)

서술형 포인트: 정규식이 못 잡은 줄(unmatched)을 몇 %인지 밝히고, 샘플을 보여 담당자에게
형식을 확인받는 것이 "검증"이다.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .timeparse import parse_ts

COMMON_PATTERNS = {
    # 2026-10-31 10:00:00,123 [ERROR] EQP01 E1234 message
    "bracket": r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\s*\[?(?P<level>[A-Z]+)\]?\s+(?P<source>\S+)\s+(?P<code>[A-Z]?\d{3,6})?\s*(?P<msg>.*)$",
    # key=value 나열
    "kv": r"(?P<key>\w+)=(?P<val>\"[^\"]*\"|\S+)",
    # syslog 유사: Oct 31 10:00:00 host proc[123]: msg
    "syslog": r"^(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s\d{2}:\d{2}:\d{2})\s(?P<host>\S+)\s(?P<proc>[^\[:]+)(?:\[(?P<pid>\d+)\])?:\s(?P<msg>.*)$",
}


class PatternSet:
    def __init__(self):
        self.patterns: List[Tuple[str, "re.Pattern"]] = []

    def add(self, name: str, regex: str, flags: int = 0) -> "PatternSet":
        self.patterns.append((name, re.compile(regex, flags)))
        return self

    def match(self, line: str) -> Optional[Dict]:
        for name, rx in self.patterns:
            m = rx.search(line)
            if m:
                d = {k: v for k, v in m.groupdict().items()}
                d["_pattern"] = name
                return d
        return None


def parse_lines(lines: Iterable[str], ps: PatternSet, ts_field: str = "ts") -> Tuple[List[Dict], List[Tuple[int, str]]]:
    """반환 (rows, unmatched). rows에는 _line(번호), _raw, _ts(파싱 시각) 포함."""
    rows, unmatched = [], []
    for i, line in enumerate(lines, 1):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        d = ps.match(line)
        if d is None:
            unmatched.append((i, line))
            continue
        d["_line"], d["_raw"] = i, line
        if ts_field in d and d[ts_field]:
            d["_ts"] = parse_ts(d[ts_field].replace(",", "."))
        rows.append(d)
    return rows, unmatched


def parse_kv(line: str) -> Dict[str, str]:
    """'a=1 b="x y"' → {'a':'1','b':'x y'}"""
    return {m.group("key"): m.group("val").strip('"') for m in re.finditer(COMMON_PATTERNS["kv"], line)}


def classify_text(text: str, categories: Dict[str, Sequence[str]], default: str = "기타") -> Tuple[str, List[str]]:
    """categories={'전원':['power','전원','PWR'], '온도':[r'temp\\w*','과열']} → (카테고리, 근거 단어들).
    여러 카테고리가 걸리면 근거 수가 많은 쪽, 동률이면 먼저 정의된 쪽."""
    hits: Dict[str, List[str]] = {}
    low = text.lower()
    for cat, pats in categories.items():
        found = []
        for p in pats:
            try:
                m = re.search(p, text, re.IGNORECASE)
            except re.error:
                m = None
            if m:
                found.append(m.group(0))
            elif p.lower() in low:
                found.append(p)
        if found:
            hits[cat] = found
    if not hits:
        return default, []
    best = max(hits, key=lambda c: (len(hits[c]), -list(categories).index(c)))
    return best, hits[best]


def aggregate(rows: List[Dict], by: Sequence[str], top: Optional[int] = None) -> List[Dict]:
    cnt = Counter(tuple(r.get(b) for b in by) for r in rows)
    out = [dict(zip(by, k), count=v) for k, v in cnt.most_common(top)]
    return out


def context_window(lines: Sequence[str], pred: Callable[[str], bool], before: int = 3, after: int = 3) -> List[Dict]:
    """pred가 참인 줄의 전후 문맥. 원인 추적/담당자 질문용 샘플 만들기."""
    out = []
    for i, line in enumerate(lines):
        if pred(line):
            out.append({"line": i + 1, "match": line.rstrip("\n"),
                        "before": [l.rstrip("\n") for l in lines[max(0, i - before): i]],
                        "after": [l.rstrip("\n") for l in lines[i + 1: i + 1 + after]]})
    return out
