# E. 대시보드 · 리포트 (보조, 100분 이후)

## 제약
- `0.0.0.0`, `PORT` env, 포트 미리보기
- CDN X → inline SVG + inline CSS
- 서버 소켓 막힐 수 있음 → `preflight env` bind 결과로 15분 안에 결정
- JS 최소, meta refresh

## 결정
```
bind 가능?
 ├─ 예 → webapp.serve(pages, json_routes)  → /, /api/state, /health
 └─ 아니오 → webapp.dashboard_fallback(pages, "outputs") → outputs/index.html, README에 "파일로 열기"
```

## 화면 필수
1. 설비별 최신 등급 (CRIT/WARN/정상 색) — `report._cls`
2. 경보 이력 표 — `alerts.to_rows`
3. 추세 + 임계선 + 이상 구간 — `svgchart.line_chart(thresholds=, bands=)`
4. 품질 요약 (결측/끊김)
5. 적용 기준 표 — `rules.rules_to_markdown`

## 순서
```python
def page():
    rep = report.Report("모니터링").h2("현재 상태").kv(state).h2("경보").table(am.to_rows()[-50:])
    rep.svg(svgchart.line_chart({"temp": pts}, thresholds=[("hi", 70)], bands=bands))
    return webapp.wrap_page(rep.to_html(), refresh=30)
ok = webapp.serve({"/": page}, {"/api/state": lambda: am.active()}, port=None)
if ok is False: webapp.dashboard_fallback({"/": page}, "outputs")
```

## 검증
- `curl http://127.0.0.1:$PORT/health` → 로그
- /api/state == 경보 CSV 1건 비교
- 폴백 HTML 열림 (`<svg` 포함)

## 함정
- 127.0.0.1 바인딩
- 서버 터미널 닫음 → 별도 탭
- 꾸미기 30분
- 매 요청 재계산 → 시작 시 1회

## Q
서버 죽으면 / 실시간인가(배치+새로고침) / 왜 Flask·Streamlit 아님
