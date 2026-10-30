#!/usr/bin/env python3
"""preflight.py — 응시 환경 점검 + 제출 전 점검 (stdlib only, Python 3.8+).

  python tools/preflight.py env        # 시작 직후/사전체험: 파이썬·패키지·소켓·쓰기권한·git·codex
  python tools/preflight.py submit     # 제출 10분 전: 필수 파일·로그 증거·비밀키·테스트 실행 여부
  python tools/preflight.py all

종료 코드: 0 = 점검한 항목 모두 OK / 1 = 문제 있음 / 2 = 점검한 항목이 없음(통과로 읽지 말 것)
출력은 logs/preflight_<시각>.log 에도 저장된다 (실행 증거).
"""
from __future__ import annotations

import importlib
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time

CHECKED = []   # (name, ok, detail)


def check(name, ok, detail=""):
    CHECKED.append((name, bool(ok), detail))
    print("  [%s] %-28s %s" % ("OK " if ok else "NG ", name, detail))
    return ok


def warn(name, detail=""):
    print("  [-- ] %-28s %s" % (name, detail))


def env_checks():
    print("== 환경 점검 ==")
    v = sys.version_info
    check("python >= 3.8", v >= (3, 8), "%s (%s)" % (platform.python_version(), sys.executable))
    if v < (3, 11):
        warn("python < 3.11", "datetime.fromisoformat이 'Z'를 못 읽음 → kitlib.timeparse 사용")
    for mod in ("csv", "json", "sqlite3", "statistics", "http.server", "unittest", "argparse"):
        try:
            importlib.import_module(mod)
            ok = True
        except Exception:
            ok = False
        check("stdlib " + mod, ok)
    ext = {}
    import warnings
    for mod, dist in (("pandas", "pandas"), ("numpy", "numpy"), ("matplotlib", "matplotlib"), ("flask", "flask"), ("fastapi", "fastapi"),
                      ("uvicorn", "uvicorn"), ("streamlit", "streamlit"), ("sklearn", "scikit-learn"), ("pytest", "pytest"), ("requests", "requests")):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                importlib.import_module(mod)
            try:
                from importlib.metadata import version
                ext[mod] = version(dist)
            except Exception:
                ext[mod] = "?"
        except Exception:
            ext[mod] = None
    have = [k for k, x in ext.items() if x]
    warn("외부 패키지", "있음: %s / 없음: %s" % (", ".join("%s %s" % (k, ext[k]) for k in have) or "-", ", ".join(k for k, x in ext.items() if not x) or "-"))
    pip = shutil.which("pip") or shutil.which("pip3")
    warn("pip", pip or "없음 → stdlib만 사용")
    if pip:
        import tempfile
        try:
            with tempfile.TemporaryDirectory() as td:
                r = subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps", "-d", td, "six==1.16.0"],
                                   capture_output=True, text=True, timeout=25)
            warn("pip 네트워크", "가능 (pip install 됨)" if r.returncode == 0 else "불가(또는 차단) → stdlib만: %s" % ((r.stderr.strip().splitlines() or [str(r.returncode)])[-1][:80]))
        except Exception as e:
            warn("pip 네트워크", "확인 실패(타임아웃 등): %r" % e)
    for tool in ("git", "node", "npm", "codex", "make", "sqlite3"):
        warn("cli " + tool, shutil.which(tool) or "없음")
    # 서버 소켓
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        check("server socket bind 0.0.0.0", True, "가능 (임시 포트 %d)" % port)
    except OSError as e:
        check("server socket bind 0.0.0.0", False, "불가: %s → 대시보드는 정적 HTML 폴백" % e)
    # 쓰기 권한
    try:
        p = ".preflight_write_test"
        with open(p, "w") as f:
            f.write("x")
        os.remove(p)
        check("cwd 쓰기 권한", True, os.getcwd())
    except Exception as e:
        check("cwd 쓰기 권한", False, repr(e))
    # 타임존/시각
    warn("현재 시각", time.strftime("%Y-%m-%d %H:%M:%S %Z") + " (TZ=%s)" % os.environ.get("TZ", "-"))
    # git
    if shutil.which("git"):
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
        warn("git repo", "예" if r.returncode == 0 else "아니오 (git init 권장: 커밋 이력이 평가 자료)")
    # codex 설정 힌트
    codex_home = os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex"))
    warn("CODEX_HOME", "%s (skills: %s)" % (codex_home, "있음" if os.path.isdir(os.path.join(codex_home, "skills")) else "없음"))
    for p in (".agents/skills", ".codex/skills"):
        if os.path.isdir(p):
            warn("repo skills", "%s: %s" % (p, ", ".join(sorted(os.listdir(p)))))


SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI 키 형태"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
    (r"(?i)(api[_-]?key|secret|password|passwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]", "하드코딩된 비밀값"),
]


def submit_checks(required=("README.md",), test_cmd=None):
    print("== 제출 전 점검 ==")
    for f in required:
        check("필수 파일 " + f, os.path.exists(f))
    # README에 실행 명령이 있나
    if os.path.exists("README.md"):
        txt = open("README.md", encoding="utf-8", errors="ignore").read()
        check("README 실행 명령(python/bash)", bool(re.search(r"(python3?|bash|make)\s+\S+", txt)), "실행 방법이 코드블록으로 있어야 함")
        check("README 미구현/미검증 섹션", bool(re.search(r"미구현|미검증|한계|Known|TODO|제한", txt)), "정직하게 적었는지")
    # 로그 증거
    logs = [f for f in (os.listdir("logs") if os.path.isdir("logs") else []) if f.endswith(".log")]
    check("logs/ 실행 로그 존재", len(logs) > 0, "%d개" % len(logs))
    # 검증 문서에 로그 경로가 실제로 있나
    vpath = os.path.join("docs", "VERIFICATION.md")
    if os.path.exists(vpath):
        txt = open(vpath, encoding="utf-8", errors="ignore").read()
        refs = re.findall(r"logs/[\w./-]+\.log", txt)
        missing = [p for p in refs if not os.path.exists(p)]
        check("VERIFICATION.md 로그 참조", len(refs) > 0 and not missing, "참조 %d개, 없는 파일 %s" % (len(refs), missing or "-"))
    else:
        warn("docs/VERIFICATION.md", "없음")
    # DECISIONS.md가 비어있지 않은가
    dpath = os.path.join("docs", "DECISIONS.md")
    if os.path.exists(dpath):
        n = len(re.findall(r"^- \[\d{1,2}:\d{2}\]", open(dpath, encoding="utf-8", errors="ignore").read(), re.M))
        check("DECISIONS.md 기록 줄", n >= 3, "%d줄 (서술형 재료)" % n)
    # 비밀키 스캔
    scanned, found = 0, []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", "hackathon-kit")]
        for fn in files:
            if fn.endswith((".py", ".md", ".json", ".txt", ".yaml", ".yml", ".toml", ".env", ".sh", ".js", ".html", ".cfg", ".ini")):
                p = os.path.join(root, fn)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                scanned += 1
                for pat, label in SECRET_PATTERNS:
                    if re.search(pat, txt):
                        found.append("%s (%s)" % (p, label))
    if scanned == 0:
        warn("비밀키 스캔", "스캔한 파일 없음 (SKIP)")
    else:
        check("비밀키 없음 (%d 파일 스캔)" % scanned, not found, "; ".join(found[:5]))
    # 테스트 실행
    cmd = test_cmd or (["python3", "-m", "pytest", "-q", "tests"] if os.path.isdir("tests") and shutil.which("pytest") else
                       ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"] if os.path.isdir("tests") else None)
    if cmd:
        r = subprocess.run(cmd, capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
        check("tests 실행 (%s)" % " ".join(cmd), r.returncode == 0, tail[0][:100])
    else:
        warn("tests/", "없음 — 최소 1개 테스트 권장")
    # 캐시/대용량
    big = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "hackathon-kit")]
        for fn in files:
            p = os.path.join(root, fn)
            try:
                if os.path.getsize(p) > 50_000_000:
                    big.append(p)
            except OSError:
                pass
    check("50MB 초과 파일 없음", not big, ", ".join(big[:3]))


def main(argv):
    mode = argv[1] if len(argv) > 1 else "all"
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "preflight_%s.log" % time.strftime("%Y%m%d_%H%M%S"))

    class Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.stdout

        def write(self, s):
            self.f.write(s); self.o.write(s)

        def flush(self):
            self.f.flush(); self.o.flush()

    with open(log_path, "w", encoding="utf-8") as f:
        sys.stdout = Tee(f)
        try:
            if mode in ("env", "all"):
                env_checks()
            if mode in ("submit", "all"):
                submit_checks()
            n_ng = sum(1 for _, ok, _ in CHECKED if not ok)
            print("== 결과: 점검 %d개, 실패 %d개 → %s" % (len(CHECKED), n_ng, log_path))
        finally:
            sys.stdout = sys.__stdout__
    if not CHECKED:
        print("!! 점검한 항목이 없습니다. 통과로 읽지 마세요. (exit 2)")
        return 2
    return 1 if n_ng else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
