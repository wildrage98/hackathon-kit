"""report — 마크다운/HTML 리포트 빌더.

  r = Report(title)
  r.h2(t).h3(t).text(s).kv(dict).table(rows, cols=None, max_rows=50).bullets(list).code(s).svg(svg).raw_md(md)
  r.to_markdown() / r.to_html() / r.save_md(path) / r.save_html(path)
  md_table(rows, cols, max_rows)
"""
from __future__ import annotations

import html
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence

_CSS = """
body{font-family:-apple-system,Segoe UI,Malgun Gothic,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px;color:#222;background:#fff}
h1{border-bottom:2px solid #333;padding-bottom:6px}h2{margin-top:28px;border-left:5px solid #2a6fdb;padding-left:8px}
table{border-collapse:collapse;margin:8px 0;font-size:14px}th,td{border:1px solid #ccc;padding:4px 8px;text-align:left}
th{background:#f0f3f8}tr:nth-child(even){background:#fafafa}code,pre{background:#f5f5f5;border-radius:4px;padding:2px 4px}
pre{padding:8px;overflow-x:auto}.kv td:first-child{font-weight:600;background:#f7f7f7}
.crit{color:#b00020;font-weight:700}.warn{color:#b26a00;font-weight:600}.ok{color:#0a7a2f}
.muted{color:#777;font-size:12px}svg{max-width:100%;height:auto}
"""


def md_table(rows: Sequence[Dict], columns: Optional[Sequence[str]] = None, max_rows: Optional[int] = None) -> str:
    rows = list(rows)
    if not rows:
        return "_(없음)_"
    cols = list(columns) if columns else list(rows[0].keys())
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for r in rows[:max_rows]:
        lines.append("| " + " | ".join(_cell(r.get(c)) for c in cols) + " |")
    if max_rows and len(rows) > max_rows:
        lines.append("| … %d행 더 있음 |" % (len(rows) - max_rows) + " |" * (len(cols) - 1))
    return "\n".join(lines)


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return ("%.4f" % v).rstrip("0").rstrip(".") if abs(v) < 1e6 else "%.3e" % v
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v).replace("|", "\\|").replace("\n", " ")


class Report:
    def __init__(self, title: str):
        self.title = title
        self.blocks: List[tuple] = []

    # --- 빌더 ---
    def h2(self, t: str) -> "Report":
        self.blocks.append(("h2", t)); return self

    def h3(self, t: str) -> "Report":
        self.blocks.append(("h3", t)); return self

    def text(self, t: str) -> "Report":
        self.blocks.append(("p", t)); return self

    def kv(self, d: Dict) -> "Report":
        self.blocks.append(("kv", d)); return self

    def table(self, rows: Sequence[Dict], columns: Optional[Sequence[str]] = None, max_rows: Optional[int] = 50) -> "Report":
        self.blocks.append(("table", (list(rows), columns, max_rows))); return self

    def bullets(self, items: Iterable[str]) -> "Report":
        self.blocks.append(("ul", list(items))); return self

    def code(self, s: str, lang: str = "") -> "Report":
        self.blocks.append(("code", (s, lang))); return self

    def svg(self, svg_str: str) -> "Report":
        self.blocks.append(("svg", svg_str)); return self

    def raw_md(self, md: str) -> "Report":
        self.blocks.append(("md", md)); return self

    # --- 출력 ---
    def to_markdown(self) -> str:
        out = ["# " + self.title, "", "_생성: %s_" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ""]
        for kind, v in self.blocks:
            if kind == "h2":
                out += ["## " + v, ""]
            elif kind == "h3":
                out += ["### " + v, ""]
            elif kind == "p":
                out += [v, ""]
            elif kind == "kv":
                out += ["| 항목 | 값 |", "|---|---|"] + ["| %s | %s |" % (k, _cell(x)) for k, x in v.items()] + [""]
            elif kind == "table":
                rows, cols, mx = v
                out += [md_table(rows, cols, mx), ""]
            elif kind == "ul":
                out += ["- " + x for x in v] + [""]
            elif kind == "code":
                out += ["```" + v[1], v[0], "```", ""]
            elif kind == "svg":
                out += ["_(차트는 HTML 버전에서 표시)_", ""]
            elif kind == "md":
                out += [v, ""]
        return "\n".join(out)

    def to_html(self) -> str:
        e = html.escape
        parts = ["<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>%s</title><style>%s</style></head><body>" % (e(self.title), _CSS),
                 "<h1>%s</h1><div class='muted'>생성: %s</div>" % (e(self.title), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))]
        for kind, v in self.blocks:
            if kind in ("h2", "h3"):
                parts.append("<%s>%s</%s>" % (kind, e(v), kind))
            elif kind == "p":
                parts.append("<p>%s</p>" % e(v).replace("\n", "<br>"))
            elif kind == "kv":
                parts.append("<table class='kv'>" + "".join("<tr><td>%s</td><td>%s</td></tr>" % (e(str(k)), e(_cell(x))) for k, x in v.items()) + "</table>")
            elif kind == "table":
                rows, cols, mx = v
                if not rows:
                    parts.append("<p class='muted'>(없음)</p>")
                    continue
                cols = list(cols) if cols else list(rows[0].keys())
                body = ""
                for r in rows[:mx]:
                    body += "<tr>" + "".join("<td class='%s'>%s</td>" % (_cls(r.get(c)), e(_cell(r.get(c)))) for c in cols) + "</tr>"
                parts.append("<table><thead><tr>" + "".join("<th>%s</th>" % e(str(c)) for c in cols) + "</tr></thead><tbody>" + body + "</tbody></table>")
                if mx and len(rows) > mx:
                    parts.append("<div class='muted'>… %d행 더 있음</div>" % (len(rows) - mx))
            elif kind == "ul":
                parts.append("<ul>" + "".join("<li>%s</li>" % e(x) for x in v) + "</ul>")
            elif kind == "code":
                parts.append("<pre><code>%s</code></pre>" % e(v[0]))
            elif kind == "svg":
                parts.append(v)  # svgchart가 만든 신뢰할 수 있는 문자열
            elif kind == "md":
                parts.append("<pre>%s</pre>" % e(v))
        parts.append("</body></html>")
        return "\n".join(parts)

    def save_md(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        return path

    def save_html(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_html())
        return path


def _cls(v) -> str:
    s = str(v).upper() if v is not None else ""
    return "crit" if s in ("CRIT", "CRITICAL", "FAIL", "NG") else "warn" if s in ("WARN", "WARNING") else "ok" if s in ("OK", "PASS", "INFO") else ""
