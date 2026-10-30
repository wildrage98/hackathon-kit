"""csvio — CSV를 안전하게 읽고 쓴다 (stdlib only).

언제 쓰나: 과제 데이터가 CSV/TSV로 주어졌는데 인코딩(cp949/utf-8-sig)이나 구분자가
불확실할 때. pandas가 없어도 list[dict]로 바로 다룰 수 있게 한다.

핵심 판단
- 인코딩은 utf-8-sig → utf-8 → cp949 → euc-kr → latin-1 순서로 시도한다.
  (한국 현장 데이터는 cp949가 흔하고, 엑셀 저장본은 BOM이 붙는다)
- 구분자는 첫 줄에서 , \t ; | 중 가장 많이 나온 것을 택한다.
- 숫자처럼 보이는 값은 int/float로 바꾸고 빈 문자열은 None으로 둔다 (결측 추적용).
"""
from __future__ import annotations

import csv
import io
import re
from typing import Dict, Iterable, List, Optional, Tuple

ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1")
DELIMS = (",", "\t", ";", "|")
NA_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-", "--"}


def _read_text(path: str, encoding: Optional[str]) -> Tuple[str, str]:
    """파일을 텍스트로 읽는다. 성공한 인코딩을 함께 돌려준다."""
    if encoding:
        with open(path, "r", encoding=encoding, newline="") as f:
            return f.read(), encoding
    last_err: Optional[Exception] = None
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return f.read(), enc
        except UnicodeDecodeError as e:  # 다음 인코딩 시도
            last_err = e
    raise ValueError("encoding detection failed: %s" % last_err)


def sniff_delimiter(first_line: str) -> str:
    counts = {d: first_line.count(d) for d in DELIMS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
_INT = re.compile(r"^-?\d+$")


def coerce(value: Optional[str]):
    """문자열 → int/float/None/str. 천단위 콤마(1,234)도 숫자로 본다."""
    if value is None:
        return None
    s = value.strip()
    if s.lower() in NA_TOKENS:
        return None
    t = s.replace(",", "") if _THOUSANDS.match(s) else s
    if _INT.match(t):
        return int(t)
    try:
        return float(t)
    except ValueError:
        return s


def read_csv(path: str, encoding: Optional[str] = None, delimiter: Optional[str] = None,
             coerce_types: bool = True) -> Tuple[List[Dict], Dict]:
    """CSV → (rows, meta). rows는 list[dict], meta는 인코딩/구분자/컬럼/행수."""
    text, enc = _read_text(path, encoding)
    if not text.strip():
        return [], {"encoding": enc, "delimiter": delimiter or ",", "columns": [], "n_rows": 0}
    first = text.splitlines()[0]
    delim = delimiter or sniff_delimiter(first)
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    cols = [c.strip().lstrip("﻿") for c in (reader.fieldnames or [])]
    rows: List[Dict] = []
    for raw in reader:
        row = {}
        for k, v in raw.items():
            key = (k or "").strip().lstrip("﻿")
            if isinstance(v, list):  # 열이 더 많은 줄
                v = ",".join(v)
            row[key] = coerce(v) if coerce_types else v
        rows.append(row)
    meta = {"encoding": enc, "delimiter": delim, "columns": cols, "n_rows": len(rows)}
    return rows, meta


def write_csv(path: str, rows: Iterable[Dict], fieldnames: Optional[List[str]] = None,
              encoding: str = "utf-8-sig") -> int:
    """list[dict] → CSV. 엑셀에서 바로 열리도록 기본 utf-8-sig. 쓴 행 수를 돌려준다."""
    rows = list(rows)
    if fieldnames is None:
        seen: Dict[str, None] = {}
        for r in rows:
            for k in r:
                seen.setdefault(k, None)
        fieldnames = list(seen)
    with open(path, "w", encoding=encoding, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames})
    return len(rows)


def to_columns(rows: List[Dict]) -> Dict[str, list]:
    """행 지향 → 열 지향 (통계 계산용)."""
    out: Dict[str, list] = {}
    for r in rows:
        for k, v in r.items():
            out.setdefault(k, []).append(v)
    return out


def numeric(values: Iterable) -> List[float]:
    """None/문자열을 제외한 숫자만 float 리스트로."""
    return [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
