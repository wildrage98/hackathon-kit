"""examples/yield_rootcause.py — 불량/수율 요인 분석 배선 예시 (학습용, 그대로 복사 금지).

입력: 로트/웨이퍼 단위 CSV (요인 컬럼 여러 개 + 결과 컬럼 PASS/FAIL 또는 0/1)
출력: 요인 순위표, 최악 그룹, 수치 변수 차이, 교차표 → report.md/html

실행:
    python examples/yield_rootcause.py --input data/lots.csv --result result --factors eqp recipe shift --numeric thk temp
    python examples/yield_rootcause.py --demo          # 합성 예시 데이터로 실행
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kitlib import csvio, groupstats, report, svgchart  # noqa: E402


def demo_rows(n=800, seed=1):
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        r = {"lot": "L%04d" % i, "eqp": rnd.choice(["ETCH01", "ETCH02", "ETCH03"]), "recipe": rnd.choice(["R-A", "R-B"]),
             "shift": rnd.choice(["D", "N"]), "thk": rnd.gauss(100, 4), "temp": rnd.gauss(350, 3)}
        p = 0.04 + (0.25 if r["eqp"] == "ETCH03" and r["recipe"] == "R-B" else 0) + (0.05 if r["temp"] > 354 else 0)
        r["result"] = "FAIL" if rnd.random() < p else "PASS"
        rows.append(r)
    return rows


def analyze(rows, result_col, factors, numerics, min_n=20):
    rep = report.Report("불량 요인 분석")
    overall = groupstats.rate_by(rows, lambda r: "ALL", result_col)[0]
    rep.h2("전체").kv({"표본": overall["n"], "불량": overall["bad"], "불량률": "%.2f%%" % (100 * overall["rate"])})
    ranked = groupstats.rank_factors(rows, factors, result_col, min_n=min_n)
    rep.h2("요인 순위 (카이제곱 통계량 내림차순)").table(ranked)
    for f in factors:
        g = groupstats.rate_by(rows, f, result_col, min_n=min_n)
        rep.h3("요인: %s" % f).table(g).svg(svgchart.bar_chart([x["group"] for x in g], [round(100 * x["rate"], 2) for x in g],
                                                              title="%s별 불량률(%%)" % f, highlight=[g[0]["group"]] if g else None))
    if numerics:
        rep.h2("수치 변수 양/불량 비교 (Cohen's d)").table([groupstats.numeric_compare(rows, c, result_col) for c in numerics])
    if len(factors) >= 2:
        top2 = [r["factor"] for r in ranked[:2]] if len(ranked) >= 2 else factors[:2]
        ct = groupstats.crosstab(rows, top2[0], top2[1], result_col)
        rep.h2("교차표 %s × %s (불량률)" % tuple(top2)).raw_md(groupstats.crosstab_markdown(ct))
        rep.text("교차표에서 특정 셀만 높으면 '조합 요인'(교호작용) 가능성. 단일 요인 결론 전에 확인할 것.")
    rep.h2("해석 주의").bullets([
        "상관은 인과가 아니다 — 설비 차이가 실제 원인인지 담당자 확인 필요 (예: 해당 설비에 특정 제품이 몰림)",
        "표본 n<%d 그룹은 제외했다 (min_n)" % min_n,
        "카이제곱은 기대도수<5 셀이 있으면 신뢰도가 떨어진다 (표의 low_expected_cells)",
    ])
    return rep, ranked


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input")
    ap.add_argument("--result", default="result")
    ap.add_argument("--factors", nargs="*", default=["eqp", "recipe", "shift"])
    ap.add_argument("--numeric", nargs="*", default=["thk", "temp"])
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args(argv)
    rows = demo_rows() if a.demo or not a.input else csvio.read_csv(a.input)[0]
    rep, ranked = analyze(rows, a.result, a.factors, a.numeric)
    os.makedirs(a.out, exist_ok=True)
    rep.save_md(os.path.join(a.out, "yield_report.md"))
    rep.save_html(os.path.join(a.out, "yield_report.html"))
    for r in ranked:
        print("%-10s chi2=%8.2f sig=%s worst=%s rate=%.3f lift=%s n=%d" % (r["factor"], r["chi2"], r["sig_0.05"], r["worst_group"], r["worst_rate"], r["worst_lift"], r["worst_n"]))
    print("->", a.out)


if __name__ == "__main__":
    main()
