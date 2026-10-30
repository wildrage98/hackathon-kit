"""examples/sensor_pipeline.py — kitlib 모듈을 어떻게 엮는지 보여주는 참고 배선 (학습용).

과제에 그대로 복사하지 말 것. 스키마·기준·정책은 담당자와 확정한 값으로 바꾸고, 가져다 쓴
부분은 DECISIONS.md에 출처를 적는다. (이 파일 자체가 서술형에서 "왜 이렇게 했나"를 답할 수
있는 구조의 예시다: 단계마다 근거 파일이 남는다)

흐름:  CSV → 시각 파싱 → 품질 점검/정책 → (기준 없으면) 정상 구간 IQR로 기준 제안
       → 룰 판정(상태별·지속조건) → 경보 상태머신 → 리포트/대시보드 → 정답 대비 검증

실행:
    python examples/sensor_pipeline.py synth --out data/synth.csv
    python examples/sensor_pipeline.py run --input data/synth.csv --out outputs
    python examples/sensor_pipeline.py validate --input data/synth.csv --truth data/synth_truth.json
    python examples/sensor_pipeline.py serve --input data/synth.csv            # 0.0.0.0:$PORT
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # kitlib 경로 (제출물에선 kitlib/를 루트에 둔다)

from kitlib import alerts, csvio, evalmetrics, profile, quality, report, rules, stats_detect, svgchart, synth, timeparse, webapp  # noqa: E402
from kitlib.cli import App  # noqa: E402

SENSORS = ["temp", "pressure", "vibration", "current"]
KEY = ["equipment"]
app = App("설비 센서 이상 징후 파이프라인 (예시)")


def load(path: str):
    rows, meta = csvio.read_csv(path)
    tp = timeparse.add_parsed_time(rows, "timestamp")
    q = quality.check_quality(rows, key_cols=KEY, value_cols=SENSORS, limits={"temp": (-50, 300), "pressure": (0, 20)})
    clean, qlog = quality.apply_policy(rows, q["issues"], {"duplicate": "drop", "missing": "flag", "time_reversal": "sort"}, key_cols=KEY, value_cols=SENSORS)
    return clean, {"meta": meta, "time_parse": tp, "quality": q, "quality_log": qlog, "raw": rows}


def propose_rules(clean, baseline_state: str = "RUN", k_warn: float = 2.0, k_crit: float = 4.0):
    """담당자 기준이 없을 때: 설비별·센서별 정상(RUN) 구간 앞 1/3을 기준 구간으로 보고 IQR 경계를 제안.
    WARN = Q1-2·IQR ~ Q3+2·IQR (2회 연속), CRIT = Q1-4·IQR ~ Q3+4·IQR (1회).
    → 이 표를 담당자에게 보여주고 확정받는다 (QUESTIONS.md '확정 기준 메모'에 기록).
    주의: 기준 구간 안에 이상이 섞여 있으면 경계가 넓어진다(=미탐). 기준 구간 선정 근거를 DECISIONS에 적을 것."""
    out = []
    for eq in sorted({r["equipment"] for r in clean}):
        for s in SENSORS:
            vals = [r[s] for r in clean if r["equipment"] == eq and r.get("state") == baseline_state and r.get(s) is not None]
            base = vals[: max(50, len(vals) // 3)]
            lo, hi, _ = stats_detect.iqr_bounds(base, k_warn)
            lo2, hi2, _ = stats_detect.iqr_bounds(base, k_crit)
            if lo is None:
                continue
            out.append(rules.Rule("%s_%s_warn" % (eq, s), s, lo, hi, severity="WARN", when={"equipment": eq, "state": baseline_state}, min_consecutive=2))
            out.append(rules.Rule("%s_%s_crit" % (eq, s), s, lo2, hi2, severity="CRIT", when={"equipment": eq, "state": baseline_state}, min_consecutive=1))
    return out


def analyze(clean, rule_list):
    rules.evaluate_series(clean, rule_list, key_cols=KEY)
    am = alerts.run_from_levels(clean, KEY, open_after=1, close_after=6)  # 6샘플(=1분) 정상이면 종료
    return am


def build_report(clean, am, info, rule_list, title="설비 이상 징후 리포트"):
    r = report.Report(title)
    r.h2("데이터 품질").raw_md(info["quality"]["summary_md"]).bullets(info["quality_log"])
    r.h2("적용 기준").raw_md(rules.rules_to_markdown(rule_list))
    r.h2("경보 이력").table(am.to_rows(), ["event", "alert_id", "key", "ts", "level", "reason", "duration_s"], 100)
    r.h2("현재 상태").kv({str(k): "%s (%s since %s)" % (v["level"], v["alert_id"], v["since"]) for k, v in am.active().items()} or {"-": "열린 경보 없음"})
    for eq in sorted({x["equipment"] for x in clean}):
        pts = {s: [(x["_ts"], x.get(s)) for x in clean if x["equipment"] == eq] for s in SENSORS[:2]}
        bands = [(e["ts"], next((f["ts"] for f in am.events if f["alert_id"] == e["alert_id"] and f["event"] == "END"), clean[-1]["_ts"]), e["level"])
                 for e in am.events if e["event"] == "START" and e["key"] == (eq,)]
        r.h3(eq).svg(svgchart.line_chart({"temp": pts["temp"]}, title="%s temp" % eq, bands=bands, height=220))
    return r


@app.command("synth", help="합성 데이터 + 정답 생성")
def cmd_synth(args, log):
    rows, truth = synth.generate(5, args.minutes, 10, args.seed)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    tp = args.out.rsplit(".", 1)[0] + "_truth.json"
    synth.write(rows, truth, args.out, tp)
    log.info("wrote %s (%d rows), truth %s (%d anomalies)", args.out, len(rows), tp, len(truth["anomalies"]))


@app.command("run", help="분석 → outputs/ (alerts.csv, report.md/html, rules.json)")
def cmd_run(args, log):
    clean, info = load(args.input)
    log.info("loaded %s: %s", args.input, info["meta"])
    log.info("quality: %s", info["quality"]["counts"])
    rl = propose_rules(clean)
    am = analyze(clean, rl)
    os.makedirs(args.out, exist_ok=True)
    csvio.write_csv(os.path.join(args.out, "alerts.csv"), am.to_rows())
    with open(os.path.join(args.out, "rules.json"), "w", encoding="utf-8") as f:
        json.dump([x.__dict__ for x in rl], f, ensure_ascii=False, indent=1, default=str)
    rep = build_report(clean, am, info, rl)
    rep.save_md(os.path.join(args.out, "report.md"))
    rep.save_html(os.path.join(args.out, "report.html"))
    log.info("events=%d active=%d → %s", len(am.events), len(am.active()), args.out)


@app.command("validate", help="정답(truth.json) 대비 탐지 성능")
def cmd_validate(args, log):
    clean, info = load(args.input)
    am = analyze(clean, propose_rules(clean))
    with open(args.truth, encoding="utf-8") as f:
        truth = json.load(f)
    tr = [(datetime.fromisoformat(a["start"]), datetime.fromisoformat(a["end"])) for a in truth["anomalies"]]
    tkeys = [a["equipment"] for a in truth["anomalies"]]
    # 탐지 = 경보 START + 품질 점검에서 잡힌 센서 고착(stuck). quality issue의 row는 원본(raw) 인덱스다.
    dets = [e["ts"] for e in am.events if e["event"] == "START"]
    dkeys = [e["key"][0] for e in am.events if e["event"] == "START"]
    for it in info["quality"]["issues"]:
        if it["type"] == "stuck":
            raw_row = info["raw"][it["row"]]
            dets.append(raw_row["_ts"])
            dkeys.append(raw_row["equipment"])
    m = evalmetrics.event_prf(tr, dets, tolerance_s=args.tolerance, truth_keys=tkeys, det_keys=dkeys)
    log.info("event P/R/F1 = %s/%s/%s  (tp=%d fp=%d fn=%d, latency=%ss)", m["precision"], m["recall"], m["f1"], m["tp"], m["fp"], m["fn"], m["mean_latency_s"])
    for i in m["missed"]:
        log.info("missed: %s", truth["anomalies"][i])
    qc = info["quality"]["counts"]
    qt = {}
    for q in truth["quality"]:
        qt[q["kind"]] = qt.get(q["kind"], 0) + 1
    log.info("quality detected=%s vs injected=%s", qc, qt)
    print(evalmetrics.report_markdown(m))


@app.command("serve", help="대시보드 (0.0.0.0:$PORT). 바인딩 실패 시 정적 파일 폴백")
def cmd_serve(args, log):
    clean, info = load(args.input)
    rl = propose_rules(clean)
    am = analyze(clean, rl)
    page = lambda: webapp.wrap_page(build_report(clean, am, info, rl, "설비 모니터링 대시보드").to_html(), refresh=30)  # noqa: E731
    state = lambda: {"active": {str(k): v for k, v in am.active().items()}, "n_events": len(am.events)}  # noqa: E731
    ok = webapp.serve({"/": page}, {"/api/state": state}, port=args.port)
    if ok is False:
        webapp.dashboard_fallback({"/": page}, "outputs")
        return 0


app.add_argument("synth", "--out", default="data/synth.csv")
app.add_argument("synth", "--minutes", type=int, default=240)
app.add_argument("synth", "--seed", type=int, default=7)
app.add_argument("run", "--input", default="data/synth.csv")
app.add_argument("run", "--out", default="outputs")
app.add_argument("validate", "--input", default="data/synth.csv")
app.add_argument("validate", "--truth", default="data/synth_truth.json")
app.add_argument("validate", "--tolerance", type=float, default=120.0)
app.add_argument("serve", "--input", default="data/synth.csv")
app.add_argument("serve", "--port", type=int, default=None)

if __name__ == "__main__":
    sys.exit(app.main())
