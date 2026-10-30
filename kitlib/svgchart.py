"""svgchart — 의존성 없는 inline SVG 차트 (문자열 반환).

  line_chart({"name": [(x, y), ...]}, width, height, title, thresholds=[(label, y)], bands=[(x0, x1, label)], points=[(x, y, label)], y_label, max_points)
  bar_chart(labels, values, width, height, title, highlight=[label])
x: 숫자 또는 datetime. max_points 초과 시 다운샘플.
"""
from __future__ import annotations

import html
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

COLORS = ["#2a6fdb", "#d9480f", "#2b8a3e", "#862e9c", "#e67700", "#0b7285", "#c2255c", "#5c940d"]


def _x(v):
    return v.timestamp() if isinstance(v, datetime) else float(v)


def _fmt_x(v, is_time: bool) -> str:
    return datetime.fromtimestamp(v).strftime("%m-%d %H:%M") if is_time else ("%g" % v)


def line_chart(series: Dict[str, Sequence[Tuple]], width: int = 900, height: int = 300, title: str = "",
               thresholds: Sequence[Tuple[str, float]] = (), bands: Sequence[Tuple] = (),
               points: Sequence[Tuple] = (), y_label: str = "", max_points: int = 2000) -> str:
    """series: name -> [(x, y)], thresholds: [(label, y)], bands: [(x0, x1, label)], points: [(x, y, label)] 강조점."""
    pad_l, pad_r, pad_t, pad_b = 60, 20, 30 if title else 10, 40
    W, H = width - pad_l - pad_r, height - pad_t - pad_b
    data: Dict[str, List[Tuple[float, float]]] = {}
    is_time = False
    for name, pts in series.items():
        clean = [(p[0], p[1]) for p in pts if p[1] is not None]
        if clean and isinstance(clean[0][0], datetime):
            is_time = True
        clean = [(_x(a), float(b)) for a, b in clean]
        if len(clean) > max_points:
            step = len(clean) // max_points + 1
            clean = clean[::step]
        data[name] = clean
    allx = [x for v in data.values() for x, _ in v]
    ally = [y for v in data.values() for _, y in v] + [t[1] for t in thresholds]
    if not allx:
        return "<svg width='%d' height='%d'><text x='10' y='20'>no data</text></svg>" % (width, height)
    x0, x1 = min(allx), max(allx)
    y0, y1 = min(ally), max(ally)
    if x1 == x0:
        x1 = x0 + 1
    if y1 == y0:
        y0, y1 = y0 - 1, y1 + 1
    yr = (y1 - y0) * 0.08
    y0, y1 = y0 - yr, y1 + yr
    sx = lambda x: pad_l + (x - x0) / (x1 - x0) * W  # noqa: E731
    sy = lambda y: pad_t + (1 - (y - y0) / (y1 - y0)) * H  # noqa: E731
    out = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d' font-family='sans-serif' font-size='11'>" % (width, height, width, height)]
    if title:
        out.append("<text x='%d' y='18' font-size='14' font-weight='bold'>%s</text>" % (pad_l, html.escape(title)))
    for xa, xb, label in bands:  # 이상 구간 음영
        a, b = sx(_x(xa)), sx(_x(xb))
        out.append("<rect x='%.1f' y='%d' width='%.1f' height='%d' fill='#ff6b6b' opacity='0.15'/>" % (a, pad_t, max(1.0, b - a), H))
        if label:
            out.append("<text x='%.1f' y='%d' fill='#c92a2a' font-size='10'>%s</text>" % (a + 2, pad_t + 12, html.escape(str(label))))
    # 격자 + y축 눈금
    for i in range(5):
        y = y0 + (y1 - y0) * i / 4
        out.append("<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='#e5e5e5'/>" % (pad_l, sy(y), width - pad_r, sy(y)))
        out.append("<text x='%d' y='%.1f' text-anchor='end' dy='4'>%s</text>" % (pad_l - 6, sy(y), ("%.4g" % y)))
    for i in range(5):  # x축 눈금
        x = x0 + (x1 - x0) * i / 4
        out.append("<text x='%.1f' y='%d' text-anchor='middle'>%s</text>" % (sx(x), height - pad_b + 16, _fmt_x(x, is_time)))
    out.append("<rect x='%d' y='%d' width='%d' height='%d' fill='none' stroke='#999'/>" % (pad_l, pad_t, W, H))
    if y_label:
        out.append("<text x='12' y='%d' transform='rotate(-90 12 %d)' text-anchor='middle'>%s</text>" % (pad_t + H // 2, pad_t + H // 2, html.escape(y_label)))
    for label, ty in thresholds:  # 임계선
        out.append("<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='#e03131' stroke-dasharray='5,4'/>" % (pad_l, sy(ty), width - pad_r, sy(ty)))
        out.append("<text x='%d' y='%.1f' text-anchor='end' dy='-3' fill='#e03131'>%s=%g</text>" % (width - pad_r, sy(ty), html.escape(str(label)), ty))
    for i, (name, pts) in enumerate(data.items()):  # 선
        if not pts:
            continue
        col = COLORS[i % len(COLORS)]
        d = " ".join("%s%.1f,%.1f" % ("M" if j == 0 else "L", sx(x), sy(y)) for j, (x, y) in enumerate(pts))
        out.append("<path d='%s' fill='none' stroke='%s' stroke-width='1.5'/>" % (d, col))
        out.append("<rect x='%d' y='%d' width='10' height='10' fill='%s'/><text x='%d' y='%d'>%s</text>" % (
            pad_l + 90 * i, height - 12, col, pad_l + 90 * i + 14, height - 3, html.escape(name)))
    for p in points:  # 강조점
        x, y = sx(_x(p[0])), sy(float(p[1]))
        out.append("<circle cx='%.1f' cy='%.1f' r='4' fill='#e03131'><title>%s</title></circle>" % (x, y, html.escape(str(p[2]) if len(p) > 2 else "")))
    out.append("</svg>")
    return "\n".join(out)


def bar_chart(labels: Sequence, values: Sequence[float], width: int = 600, height: int = 260, title: str = "",
              color: str = "#2a6fdb", highlight: Optional[Sequence] = None) -> str:
    pad_l, pad_t, pad_b = 50, 30 if title else 10, 50
    W, H = width - pad_l - 20, height - pad_t - pad_b
    vals = [float(v or 0) for v in values]
    vmax = max(vals + [0]) or 1.0
    n = max(1, len(vals))
    bw = W / n * 0.7
    out = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' font-family='sans-serif' font-size='11'>" % (width, height)]
    if title:
        out.append("<text x='%d' y='18' font-size='14' font-weight='bold'>%s</text>" % (pad_l, html.escape(title)))
    for i in range(5):
        y = pad_t + H * (1 - i / 4)
        out.append("<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='#e5e5e5'/><text x='%d' y='%.1f' text-anchor='end' dy='4'>%.4g</text>" % (pad_l, y, width - 20, y, pad_l - 6, y, vmax * i / 4))
    hl = set(highlight or [])
    for i, (lab, v) in enumerate(zip(labels, vals)):
        x = pad_l + W / n * i + (W / n - bw) / 2
        h = H * v / vmax
        c = "#e03131" if lab in hl else color
        out.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s'><title>%s: %g</title></rect>" % (x, pad_t + H - h, bw, h, c, html.escape(str(lab)), v))
        out.append("<text x='%.1f' y='%d' text-anchor='middle'>%s</text>" % (x + bw / 2, pad_t + H + 14, html.escape(str(lab))[:12]))
        out.append("<text x='%.1f' y='%.1f' text-anchor='middle' font-size='10'>%g</text>" % (x + bw / 2, pad_t + H - h - 3, v))
    out.append("</svg>")
    return "\n".join(out)
