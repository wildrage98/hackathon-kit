"""cli — argparse 서브커맨드 + 파일 로깅 (logs/<시각>_<cmd>.log).

    from kitlib.cli import App
    app = App("name")
    @app.command("run", help="...")
    def run(args, log): ...
    app.add_argument("run", "--input", default="data/x.csv")
    if __name__ == "__main__": app.main()
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Callable, Dict, List, Optional


class App:
    def __init__(self, description: str = "", log_dir: str = "logs"):
        self.parser = argparse.ArgumentParser(description=description)
        self.sub = self.parser.add_subparsers(dest="cmd")
        self._cmds: Dict[str, Callable] = {}
        self._subparsers: Dict[str, argparse.ArgumentParser] = {}
        self.log_dir = log_dir
        self.parser.add_argument("--log-level", default="INFO")

    def command(self, name: str, help: str = ""):
        def deco(fn):
            self._cmds[name] = fn
            self._subparsers[name] = self.sub.add_parser(name, help=help)
            return fn
        return deco

    def add_argument(self, cmd: str, *a, **kw):
        self._subparsers[cmd].add_argument(*a, **kw)

    def _logger(self, cmd: str) -> logging.Logger:
        os.makedirs(self.log_dir, exist_ok=True)
        path = os.path.join(self.log_dir, "%s_%s.log" % (time.strftime("%Y%m%d_%H%M%S"), cmd))
        log = logging.getLogger("app")
        log.handlers.clear()
        log.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        for h in (logging.StreamHandler(sys.stdout), logging.FileHandler(path, encoding="utf-8")):
            h.setFormatter(fmt)
            log.addHandler(h)
        log.info("log file: %s", path)
        return log

    def main(self, argv: Optional[List[str]] = None) -> int:
        args = self.parser.parse_args(argv)
        if not args.cmd:
            self.parser.print_help()
            return 2
        log = self._logger(args.cmd)
        log.setLevel(getattr(logging, str(args.log_level).upper(), logging.INFO))
        log.info("start %s args=%s", args.cmd, {k: v for k, v in vars(args).items() if k not in ("cmd", "log_level")})
        t0 = time.time()
        try:
            rc = self._cmds[args.cmd](args, log) or 0
        except Exception:
            log.exception("command failed")
            rc = 1
        log.info("end %s rc=%s elapsed=%.1fs", args.cmd, rc, time.time() - t0)
        return int(rc)
