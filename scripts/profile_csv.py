#!/usr/bin/env python3
"""profile_csv.py — CSV 요약(마크다운) + 질문 후보.

  python tools/profile_csv.py data/x.csv [--ts timestamp] [--key equipment] [--quality]
  python tools/profile_csv.py data/x.csv --ts timestamp --key equipment > docs/PROFILE.md
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))   # tools/ → 프로젝트 루트(kitlib)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))  # hackathon-kit/scripts → 상위

from kitlib import csvio, profile, quality, timeparse  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--ts", help="시각 컬럼명")
    ap.add_argument("--key", nargs="*", default=[], help="키 컬럼(설비 등)")
    ap.add_argument("--quality", action="store_true", help="품질 점검도 수행(값 컬럼=숫자 컬럼 전부)")
    a = ap.parse_args(argv)
    rows, meta = csvio.read_csv(a.path)
    print("# PROFILE: %s\n" % a.path)
    print("인코딩 %s, 구분자 %r, 컬럼 %d개, 행 %d\n" % (meta["encoding"], meta["delimiter"], len(meta["columns"]), meta["n_rows"]))
    ts_col = None
    if a.ts:
        r = timeparse.add_parsed_time(rows, a.ts)
        ts_col = "_ts"
        print("시각 파싱: %s\n" % r)
    p = profile.profile(rows, ts_col=ts_col, key_cols=a.key)
    print(profile.to_markdown(p))
    print("\n## 질문 후보\n")
    for q in profile.questions_from_profile(p):
        print("- " + q)
    if a.quality:
        nums = [c for c, i in p["columns"].items() if i["type"] == "numeric" and not c.startswith("_")]
        q = quality.check_quality(rows, ts_col=ts_col or "", key_cols=a.key, value_cols=nums)
        print("\n## 품질 점검 (값 컬럼: %s)\n" % nums)
        print(q["summary_md"])
        for it in q["issues"][:10]:
            print("- %s" % it)
        if len(q["issues"]) > 10:
            print("- … %d건 더" % (len(q["issues"]) - 10))


if __name__ == "__main__":
    main()
