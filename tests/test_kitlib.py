"""kitlib 회귀 테스트 (stdlib unittest). 실행: python -m unittest discover -s tests -v
각 테스트는 '서술형에서 물을 법한 경계 조건'을 고정한다."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kitlib import (alerts, csvio, evalmetrics, groupstats, logparse, profile, quality, report, rules,  # noqa: E402
                    schedule, spc, stats_detect, svgchart, synth, timeparse, webapp)


class TestCsvio(unittest.TestCase):
    def test_roundtrip_and_coerce(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.csv")
            with open(p, "w", encoding="cp949", newline="") as f:
                f.write("설비,값,비고\nE1,\"1,234\",\nE2,3.5,n/a\nE3,abc,x\n")
            rows, meta = csvio.read_csv(p)
            self.assertEqual(meta["encoding"], "cp949")
            self.assertEqual(rows[0]["값"], 1234)
            self.assertIsNone(rows[0]["비고"])
            self.assertEqual(rows[1]["값"], 3.5)
            self.assertIsNone(rows[1]["비고"])  # n/a → None
            self.assertEqual(rows[2]["값"], "abc")
            n = csvio.write_csv(os.path.join(td, "b.csv"), rows)
            self.assertEqual(n, 3)
            rows2, _ = csvio.read_csv(os.path.join(td, "b.csv"))
            self.assertEqual(rows2[0]["설비"], "E1")

    def test_tsv_sniff(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.tsv")
            open(p, "w", encoding="utf-8").write("a\tb\n1\t2\n")
            rows, meta = csvio.read_csv(p)
            self.assertEqual(meta["delimiter"], "\t")
            self.assertEqual(rows[0]["b"], 2)


class TestTimeparse(unittest.TestCase):
    def test_formats(self):
        cases = {
            "2026-10-31T10:00:00Z": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "2026-10-31 10:00:00+09:00": datetime(2026, 10, 31, 10, 0, tzinfo=timezone(timedelta(hours=9))),
            "2026-10-31 10:00:00.250": datetime(2026, 10, 31, 10, 0, 0, 250000),
            "2026/10/31 10:00": datetime(2026, 10, 31, 10, 0),
            "20261031100000": datetime(2026, 10, 31, 10, 0),
            1793440800: datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
            "1793440800000": datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc),
        }
        for s, exp in cases.items():
            self.assertEqual(timeparse.parse_ts(s), exp, s)
        self.assertIsNone(timeparse.parse_ts("not a date"))
        self.assertIsNone(timeparse.parse_ts(""))

    def test_unify_mixed(self):
        rows = [{"t": "2026-10-31T01:00:00Z"}, {"t": "2026-10-31 10:00:00"}]
        r = timeparse.add_parsed_time(rows, "t", default_tz=timeparse.KST)
        self.assertEqual(r["parsed"], 2)
        self.assertTrue(all(x["_ts"].tzinfo is None for x in rows))
        self.assertEqual(rows[0]["_ts"], rows[1]["_ts"])  # 01:00Z == 10:00 KST

    def test_interval(self):
        base = datetime(2026, 1, 1)
        ts = [base + timedelta(seconds=10 * i) for i in range(20)]
        self.assertEqual(timeparse.infer_interval(ts), 10.0)


class TestQuality(unittest.TestCase):
    def _rows(self):
        base = datetime(2026, 1, 1)
        rows = [{"eq": "A", "_ts": base + timedelta(seconds=10 * i), "v": 1.0 + i * 0.01} for i in range(30)]
        rows.insert(6, dict(rows[5]))                                    # duplicate (바로 뒤에)
        rows.append({"eq": "A", "_ts": base + timedelta(seconds=255), "v": 2.0})   # reversal (290 다음에 255)
        rows.append({"eq": "A", "_ts": base + timedelta(seconds=1000), "v": None})  # gap + missing
        rows.append({"eq": "A", "_ts": None, "v": 999.0})                 # unparsed + out of range
        return rows

    def test_checks(self):
        q = quality.check_quality(self._rows(), key_cols=["eq"], value_cols=["v"], limits={"v": (0, 100)})
        c = q["counts"]
        self.assertEqual(c.get("duplicate"), 1)
        self.assertEqual(c.get("time_reversal"), 1)
        self.assertEqual(c.get("gap"), 1)
        self.assertEqual(c.get("missing"), 1)
        self.assertEqual(c.get("unparsed_time"), 1)
        self.assertEqual(c.get("out_of_range"), 1)
        self.assertEqual(q["interval_seconds"], 10.0)

    def test_policy(self):
        rows = self._rows()
        q = quality.check_quality(rows, key_cols=["eq"], value_cols=["v"], limits={"v": (0, 100)})
        out, log = quality.apply_policy(rows, q["issues"], {"duplicate": "drop", "missing": "ffill", "out_of_range": "null"}, key_cols=["eq"], value_cols=["v"])
        self.assertEqual(len(out), len(rows) - 2)   # duplicate 1 + unparsed_time 1 dropped
        self.assertTrue(all(r["v"] is not None or r["_ts"] is None for r in out))
        ts = [r["_ts"] for r in out if r["_ts"]]
        self.assertEqual(ts, sorted(ts))             # time_reversal → sort
        self.assertTrue(any("ffill" in r["_quality_flags"] for r in out))

    def test_stuck(self):
        rows = [{"eq": "A", "_ts": datetime(2026, 1, 1) + timedelta(seconds=i), "v": 5.0} for i in range(12)]
        q = quality.check_quality(rows, key_cols=["eq"], value_cols=["v"], stuck_n=10)
        self.assertEqual(q["counts"].get("stuck"), 1)


class TestRules(unittest.TestCase):
    def test_boundary_inclusive(self):
        r = rules.Rule("hi", "v", lo=0, hi=10, inclusive=(True, True))
        self.assertIsNone(r.violation({"v": 10}))
        self.assertIsNone(r.violation({"v": 0}))
        self.assertIsNotNone(r.violation({"v": 10.01}))
        r2 = rules.Rule("hi", "v", lo=0, hi=10, inclusive=(False, False))
        self.assertIsNotNone(r2.violation({"v": 10}))
        self.assertIsNotNone(r2.violation({"v": 0}))
        self.assertIsNone(r.violation({"v": None}))   # 값 없음 → 판정 안 함

    def test_consecutive_and_when(self):
        rs = [rules.Rule("hi", "v", hi=10, min_consecutive=3, when={"state": "RUN"})]
        rows = [{"k": 1, "state": "RUN", "v": v} for v in [11, 11, 9, 11, 11, 11]] + [{"k": 1, "state": "MAINT", "v": 99}]
        rules.evaluate_series(rows, rs, key_cols=["k"])
        levels = [r["_level"] for r in rows]
        self.assertEqual(levels, [None, None, None, None, None, "WARN", None])  # 3연속에서만 확정, MAINT 제외

    def test_allowed_and_severity(self):
        rs = [rules.Rule("st", "state", allowed=["RUN", "IDLE"], severity="CRIT"), rules.Rule("v", "v", hi=1, severity="WARN")]
        hits = rules.evaluate_row({"state": "X", "v": 5}, rs)
        self.assertEqual(len(hits), 2)
        self.assertEqual(rules.max_sev("WARN", "CRIT"), "CRIT")
        self.assertEqual(rules.max_sev(None, "INFO"), "INFO")

    def test_load_json(self):
        rs = rules.load_rules([{"name": "a", "column": "v", "hi": 1, "inclusive": [True, False]}])
        self.assertEqual(rs[0].inclusive, (True, False))
        self.assertIn("| a |", rules.rules_to_markdown(rs))


class TestStatsDetect(unittest.TestCase):
    def test_zscore_spike(self):
        vals = [10.0 + (i % 3) * 0.1 for i in range(50)] + [20.0] + [10.0] * 5
        res = stats_detect.rolling_zscore(vals, window=20, threshold=4)
        self.assertTrue(res[50]["flag"])
        self.assertFalse(any(r["flag"] for r in res[:50]))

    def test_cusum_shift(self):
        vals = [10.0 + ((i * 7) % 5 - 2) * 0.1 for i in range(60)] + [10.8] * 40
        res = stats_detect.cusum(vals, baseline_n=50)
        self.assertTrue(any(r["flag"] for r in res[60:]))
        self.assertFalse(any(r["flag"] for r in res[:60]))

    def test_ewma_and_iqr(self):
        vals = [1.0, 1.1, 0.9, 1.0, 1.2, 0.8, 1.0, 1.1, 0.9, 1.0] * 6 + [3.0] * 30
        res = stats_detect.ewma_detect(vals, alpha=0.3, k=3, baseline_n=50)
        self.assertTrue(any(r["flag"] for r in res[60:]))
        lo, hi, info = stats_detect.iqr_bounds(vals[:60])
        self.assertLess(lo, 0.8)
        self.assertGreater(hi, 1.2)
        self.assertLess(hi, 3.0)

    def test_rate_and_stuck(self):
        r = stats_detect.rate_of_change([0, 1, 10], [0, 1, 2], threshold=5)
        self.assertTrue(r[2]["flag"] and not r[1]["flag"])
        s = stats_detect.stuck([1, 1, 1, 1, 2], n=4)
        self.assertTrue(s[3]["flag"] and not s[4]["flag"])


class TestAlerts(unittest.TestCase):
    def test_lifecycle(self):
        am = alerts.AlertManager(open_after=2, close_after=2)
        t = datetime(2026, 1, 1)
        seq = [None, "WARN", "WARN", "CRIT", "WARN", None, None, None, "WARN", "WARN"]
        for i, lv in enumerate(seq):
            am.feed("E1", t + timedelta(minutes=i), lv, "r%d" % i)
        ev = [e["event"] for e in am.events]
        self.assertEqual(ev, ["START", "ESCALATE", "DEESCALATE", "END", "START"])
        self.assertEqual(am.events[0]["ts"], t + timedelta(minutes=2))  # 2연속에서 시작
        self.assertEqual(am.events[3]["duration_s"], 4 * 60)
        self.assertNotEqual(am.events[0]["alert_id"], am.events[4]["alert_id"])  # 재발 = 새 경보
        self.assertEqual(list(am.active()), ["E1"])
        rows = am.to_rows()
        self.assertIsInstance(rows[0]["ts"], str)


class TestSPC(unittest.TestCase):
    def test_imr_we_cpk(self):
        vals = [10 + ((i * 7) % 5 - 2) * 0.1 for i in range(40)]
        lim = spc.imr_limits(vals)
        self.assertAlmostEqual(lim["mean"], 10.0, places=1)
        self.assertGreater(lim["ucl"], lim["mean"])
        we = spc.western_electric(vals + [10 + 1.0], lim["mean"], lim["sigma_est"])
        self.assertIn(1, we[-1]["rules"])
        c = spc.cp_cpk(vals, 9, 11)
        self.assertIsNotNone(c["cpk"])
        self.assertEqual(c["cp"], c["cpk"] if abs(c["mean"] - 10) < 1e-9 else c["cp"])
        x = spc.xbar_r_limits([vals[i:i + 5] for i in range(0, 40, 5)])
        self.assertEqual(x["n"], 5)
        with self.assertRaises(ValueError):
            spc.xbar_r_limits([[1, 2], [1, 2, 3]])


class TestGroupstats(unittest.TestCase):
    def setUp(self):
        self.rows = [{"g": "A", "f": "x", "v": 1.0, "r": "PASS"} for _ in range(90)] + [{"g": "A", "f": "x", "v": 1.0, "r": "FAIL"} for _ in range(10)] \
            + [{"g": "B", "f": "y", "v": 2.0, "r": "PASS"} for _ in range(60)] + [{"g": "B", "f": "y", "v": 2.0, "r": "FAIL"} for _ in range(40)]

    def test_rate_lift_chi(self):
        rb = groupstats.rate_by(self.rows, "g", "r")
        self.assertEqual(rb[0]["group"], "B")
        self.assertAlmostEqual(rb[0]["rate"], 0.4)
        self.assertAlmostEqual(rb[0]["lift"], 1.6)   # 0.4 / 0.25
        chi = groupstats.chi_square([[10, 90], [40, 60]])
        self.assertTrue(chi["sig_0.01"])
        rf = groupstats.rank_factors(self.rows, ["g", "f"], "r")
        self.assertEqual(rf[0]["worst_group"], "B")
        nc = groupstats.numeric_compare(self.rows, "v", "r")
        self.assertGreater(nc["d"], 0)
        ct = groupstats.crosstab(self.rows, "g", "f", "r")
        self.assertIn("| A |", groupstats.crosstab_markdown(ct))

    def test_tokens(self):
        self.assertTrue(groupstats._is_bad("r", {"r": "불량"}))
        self.assertFalse(groupstats._is_bad("r", {"r": "ok"}))
        self.assertIsNone(groupstats._is_bad("r", {"r": "???"}))
        self.assertTrue(groupstats._is_bad("r", {"r": 1}))


class TestSchedule(unittest.TestCase):
    def test_rules_and_constraints(self):
        jobs = [schedule.Job("J1", 30, due=60), schedule.Job("J2", 10, due=20), schedule.Job("J3", 20, ready=5, due=100),
                schedule.Job("J4", 15, due=40, eligible=["M2"])]
        ms = [schedule.Machine("M1"), schedule.Machine("M2", down=[(10, 20)])]
        s = schedule.dispatch(jobs, ms, "EDD")
        self.assertEqual(len(s), 4)
        j4 = next(d for d in s if d["job"] == "J4")
        self.assertEqual(j4["machine"], "M2")
        self.assertFalse(10 < j4["start"] < 20)   # 다운타임 회피
        spt = schedule.dispatch(jobs, ms, "SPT")
        self.assertEqual(spt[0]["job"], "J2")
        m = schedule.metrics(s, ms)
        self.assertIn("utilization", m)
        self.assertEqual(len(schedule.compare_rules(jobs, ms)), 5)
        with self.assertRaises(ValueError):
            schedule.dispatch([schedule.Job("X", 1, eligible=["NOPE"])], ms)


class TestLogparse(unittest.TestCase):
    def test_parse_classify(self):
        ps = logparse.PatternSet().add("b", logparse.COMMON_PATTERNS["bracket"])
        rows, un = logparse.parse_lines(["2026-10-31 10:00:00,123 [ERROR] EQP01 E1234 heater over temp", "junk"], ps)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "E1234")
        self.assertEqual(rows[0]["_ts"].microsecond, 123000)
        self.assertEqual(un, [(2, "junk")])
        cat, ev = logparse.classify_text("Heater over TEMP alarm", {"전원": ["power"], "온도": ["temp", "과열"]})
        self.assertEqual(cat, "온도")
        self.assertEqual(logparse.classify_text("zzz", {"a": ["b"]}), ("기타", []))
        self.assertEqual(logparse.parse_kv('a=1 b="x y"'), {"a": "1", "b": "x y"})
        self.assertEqual(logparse.aggregate(rows, ["level"]), [{"level": "ERROR", "count": 1}])
        cw = logparse.context_window(["a", "ERR", "b"], lambda l: "ERR" in l, 1, 1)
        self.assertEqual(cw[0]["before"], ["a"])


class TestReportSvg(unittest.TestCase):
    def test_report(self):
        r = report.Report("T").h2("h").kv({"a": 1.23456}).table([{"x": 1, "lv": "CRIT"}]).bullets(["b"]).code("x=1").svg("<svg></svg>")
        md, html_ = r.to_markdown(), r.to_html()
        self.assertIn("| a | 1.2346 |", md)
        self.assertIn("class='crit'", html_)
        self.assertIn("<svg></svg>", html_)
        self.assertEqual(report.md_table([]), "_(없음)_")
        self.assertIn("더 있음", report.md_table([{"a": i} for i in range(5)], max_rows=2))

    def test_svg(self):
        t0 = datetime(2026, 1, 1)
        s = svgchart.line_chart({"a": [(t0 + timedelta(minutes=i), i * 1.0) for i in range(100)]}, thresholds=[("hi", 50)], bands=[(t0, t0 + timedelta(minutes=10), "x")], points=[(t0, 0, "p")])
        self.assertTrue(s.startswith("<svg") and s.endswith("</svg>"))
        self.assertIn("hi=50", s)
        self.assertIn("no data", svgchart.line_chart({"a": []}))
        b = svgchart.bar_chart(["a", "b"], [1, 2], highlight=["b"])
        self.assertIn("#e03131", b)


class TestWebapp(unittest.TestCase):
    def test_serve_and_fallback(self):
        import urllib.request
        srv = webapp.serve({"/": lambda: webapp.wrap_page("<b>ok</b>", refresh=None)}, {"/api/x": lambda: {"n": 1}}, port=0, block=False, quiet=True)
        if srv is False:
            self.skipTest("socket bind not allowed")
        port = srv.server_address[1]
        self.assertEqual(json.loads(urllib.request.urlopen("http://127.0.0.1:%d/api/x" % port).read()), {"n": 1})
        self.assertIn(b"<b>ok</b>", urllib.request.urlopen("http://127.0.0.1:%d/" % port).read())
        with self.assertRaises(Exception):
            urllib.request.urlopen("http://127.0.0.1:%d/nope" % port)
        srv.shutdown()
        with tempfile.TemporaryDirectory() as td:
            w = webapp.dashboard_fallback({"/": lambda: "<p>x</p>", "/a/b": lambda: "y"}, td)
            self.assertTrue(os.path.exists(w["/"]) and w["/a/b"].endswith("a_b.html"))


class TestSynthEval(unittest.TestCase):
    def test_generate_and_eval(self):
        rows, truth = synth.generate(n_equipment=2, minutes=60, interval_s=10, seed=5)
        self.assertGreater(len(rows), 600)
        self.assertEqual(set(truth["equipment"]), {"EQP01", "EQP02"})
        kinds = {q["kind"] for q in truth["quality"]}
        self.assertTrue({"missing", "duplicate", "gap"} <= kinds)
        t0 = datetime(2026, 1, 1)
        m = evalmetrics.event_prf([(t0, t0 + timedelta(minutes=5)), (t0 + timedelta(hours=1), t0 + timedelta(hours=1, minutes=5))],
                                  [t0 + timedelta(minutes=1), t0 + timedelta(minutes=2), t0 + timedelta(hours=3)], tolerance_s=60)
        self.assertEqual((m["tp"], m["fp"], m["fn"]), (1, 1, 1))
        self.assertEqual(m["mean_latency_s"], 60.0)
        mk = evalmetrics.event_prf([(0, 10)], [5], 0, truth_keys=["A"], det_keys=["B"])
        self.assertEqual(mk["tp"], 0)   # 키가 다르면 매칭 안 됨
        cr = evalmetrics.classification_report(["a", "b", "a"], ["a", "a", "a"])
        self.assertAlmostEqual(cr["accuracy"], 0.6667, places=3)
        self.assertIn("accuracy", evalmetrics.report_markdown(cr))
        p = profile.profile(rows, key_cols=["equipment"])
        self.assertEqual(p["columns"]["temp"]["type"], "numeric")
        self.assertTrue(profile.questions_from_profile(p))



class TestReconcile(unittest.TestCase):
    def test_compare(self):
        from kitlib import reconcile
        a = [{"lot": " l001", "qty": 10, "st": "OK"}, {"lot": "L002", "qty": 5, "st": "OK"}, {"lot": "L003", "qty": 1, "st": "NG"}, {"lot": "L003", "qty": 1, "st": "NG"}]
        b = [{"lot": "L001", "qty": 10.3, "st": "ok"}, {"lot": "L002", "qty": 7, "st": "OK"}, {"lot": "L004", "qty": 2, "st": "OK"}]
        d = reconcile.compare(a, b, ["lot"], ["qty", "st"], tol={"qty": 0.5})
        s = d["summary"]
        self.assertEqual(s["matched_keys"], 2)
        self.assertEqual(s["only_in_a"], 1)    # L003
        self.assertEqual(s["only_in_b"], 1)    # L004
        self.assertEqual(s["mismatch_cells"], 1)   # L002 qty (L001은 tol·대소문자 허용)
        self.assertEqual(d["mismatch"][0]["lot"], "L002")
        self.assertEqual(s["dup_a"], 1)
        self.assertIn("| matched_keys | 2 |", reconcile.summary_markdown(d))
        self.assertEqual(reconcile.normalize_key("007", strip_zeros=True), "7")

if __name__ == "__main__":
    unittest.main()
