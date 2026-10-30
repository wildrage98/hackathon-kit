"""webapp — http.server 기반 초경량 대시보드 (stdlib only).

언제 쓰나: "운영자가 화면에서 본다"가 요구사항이고, 서버를 띄울 수 있을 때. Flask가 없어도 된다.
응시 환경 규칙: 0.0.0.0 바인딩, 내장 Browser 탭에서 포트·경로로 접속. 포트는 PORT 환경변수.

  serve(pages={"/": lambda: html_str}, json={"/api/state": lambda: dict}, port=8000)
  - 바인딩 실패(샌드박스가 소켓을 막음 등)하면 예외 대신 False를 돌려주고 폴백 안내를 출력한다.
    → 그때는 같은 html_str을 report.html 파일로 저장해 제출한다 (dashboard_fallback 참고).
  - 페이지는 refresh초마다 자동 새로고침(meta refresh) — JS 없이도 '라이브'처럼 보인다.
"""
from __future__ import annotations

import json as _json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Dict, Optional
from urllib.parse import urlparse

PageFn = Callable[[], str]
JsonFn = Callable[[], object]


def wrap_page(body_html: str, title: str = "Dashboard", refresh: Optional[int] = 10) -> str:
    """본문 HTML을 완성된 페이지로 감싼다 (report._CSS 재사용)."""
    from .report import _CSS
    meta = "<meta http-equiv='refresh' content='%d'>" % refresh if refresh else ""
    return ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>%s<title>%s</title>"
            "<style>%s</style></head><body>%s</body></html>") % (meta, title, _CSS, body_html)


def _make_handler(pages: Dict[str, PageFn], json_routes: Dict[str, JsonFn], quiet: bool):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path.rstrip("/") or "/"
            try:
                if path in json_routes:
                    body = _json.dumps(json_routes[path](), ensure_ascii=False, default=str).encode("utf-8")
                    self._send(200, body, "application/json; charset=utf-8")
                elif path in pages:
                    self._send(200, pages[path]().encode("utf-8"), "text/html; charset=utf-8")
                elif path == "/health":
                    self._send(200, b'{"ok":true}', "application/json")
                else:
                    self._send(404, ("not found: %s\navailable: %s" % (path, sorted(list(pages) + list(json_routes)))).encode(), "text/plain; charset=utf-8")
            except Exception as e:  # 핸들러 오류가 서버를 죽이지 않게
                self._send(500, ("error: %r" % e).encode(), "text/plain; charset=utf-8")

        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            if not quiet:
                sys.stderr.write("[web] %s\n" % (fmt % args))
    return H


def can_bind(host: str = "0.0.0.0", port: int = 0) -> bool:
    """샌드박스가 서버 소켓을 허용하는지 1초 안에 확인 (preflight에서 쓴다)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(1)
        s.close()
        return True
    except OSError:
        return False


def serve(pages: Dict[str, PageFn], json_routes: Optional[Dict[str, JsonFn]] = None, port: Optional[int] = None,
          host: str = "0.0.0.0", block: bool = True, quiet: bool = False):
    """서버 시작. block=False면 스레드로 띄우고 server 객체를 돌려준다. 실패 시 False."""
    port = int(port or os.environ.get("PORT", "8000"))
    handler = _make_handler(pages, json_routes or {}, quiet)
    try:
        httpd = HTTPServer((host, port), handler)
    except OSError as e:
        print("[web] 바인딩 실패 %s:%d (%s)" % (host, port, e))
        if isinstance(e, PermissionError):
            print("[web] 소켓 생성 자체가 막힘 → Codex 샌드박스 안일 가능성. 사람이 IDE 터미널에서 직접 실행하거나 승인 후 재시도.")
        print("[web] 그래도 안 되면 폴백: 같은 HTML을 파일로 저장 → webapp.dashboard_fallback(pages, 'outputs')")
        return False
    print("[web] Serving on http://%s:%d  (routes: %s)" % (host, port, ", ".join(sorted(list(pages) + list(json_routes or {})))))
    sys.stdout.flush()
    if block:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
        return True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def dashboard_fallback(pages: Dict[str, PageFn], out_dir: str = ".") -> Dict[str, str]:
    """서버를 못 띄울 때: 각 페이지를 정적 HTML 파일로 저장. 반환 {route: path}"""
    os.makedirs(out_dir, exist_ok=True)
    written = {}
    for route, fn in pages.items():
        name = "index.html" if route == "/" else route.strip("/").replace("/", "_") + ".html"
        p = os.path.join(out_dir, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(fn())
        written[route] = p
    print("[web] 정적 파일 저장:", written)
    return written
