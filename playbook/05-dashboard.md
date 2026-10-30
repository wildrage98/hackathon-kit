# E. 대시보드 · 운영자 화면 · 리포트

거의 항상 다른 유형의 **보조**다. 화면은 평가에서 "운영자가 사용할 수 있는 기능" 한 줄을 채우는 것이고,
핵심 로직·검증보다 뒤에 온다 (TIMEBOX 100분 이후). 핵심 모듈: `webapp`, `svgchart`, `report`

## 응시 환경 제약 (가이드·후기 기준)
- 서버는 **0.0.0.0** 바인딩, 포트는 `PORT` 환경변수, 내장 Browser 탭에서 포트/경로 입력
- 외부 브라우저 접근 금지 → **CDN(Chart.js, Bootstrap) 로드 실패 가정** → inline SVG + inline CSS만
- 샌드박스가 서버 소켓을 막거나 승인 프롬프트가 반복된 사례 → `preflight env`의 bind 결과로 15분 안에 결정
- JS는 최소. meta refresh로 "실시간처럼" 보이게

## 결정 트리
```
preflight: bind 가능?
 ├─ 예 → webapp.serve(pages, json_routes)  (http.server, Flask 불필요)
 │        → /health, /api/state(JSON), / (HTML)  세 개면 충분
 └─ 아니오 → webapp.dashboard_fallback(pages, "outputs")  → outputs/index.html
          README에 "서버 미지원 환경: outputs/index.html 파일을 브라우저로 열기" 명시
pandas/flask가 있고 익숙해도 → 같은 HTML을 만드는 데 시간이 더 든다면 쓰지 않는다
```

## 화면에 꼭 있어야 하는 것 (모니터링 과제 기준)
1. 현재 상태 요약: 설비별 최신 등급 (CRIT 빨강/WARN 주황/정상 초록) — `report._cls`가 색 입힘
2. 경보 이력 표: 시작·변경·종료·사유 (`alerts.to_rows`)
3. 추세 차트 + 임계선 + 이상 구간 음영 (`svgchart.line_chart(thresholds=, bands=)`)
4. 데이터 품질 요약 (결측/끊김 건수) — 운영자가 "데이터를 믿어도 되는가"를 봄
5. 적용 기준 표 (`rules.rules_to_markdown`) — 판단 근거 추적 요구 충족

## 모듈 순서
```python
def page():  # 요청마다 다시 계산하거나, 캐시한 결과를 렌더
    rep = report.Report("설비 모니터링").h2("현재 상태").kv(state).h2("경보").table(am.to_rows()[-50:])
    rep.svg(svgchart.line_chart({"temp": pts}, thresholds=[("hi", 70)], bands=bands))
    return webapp.wrap_page(rep.to_html(), refresh=30)
ok = webapp.serve({"/": page}, {"/api/state": lambda: am.active()}, port=None)   # PORT env
if ok is False: webapp.dashboard_fallback({"/": page}, "outputs")
```

## 검증
- `curl http://127.0.0.1:$PORT/health` → `{"ok":true}` 를 로그로 남김 (내장 브라우저 스크린샷도 docs/에)
- /api/state JSON이 경보 CSV와 일치하는지 1개 비교
- 폴백 HTML이 열리는지 (파일 크기, `<svg` 포함 여부)

## 함정
- 127.0.0.1에 바인딩 → 내장 브라우저에서 안 보임
- 서버 켜둔 터미널을 닫음 → 죽음. 별도 터미널 탭
- 화면 꾸미기에 30분 → 검증·문서가 빈다. 표+SVG 선 하나면 충분
- 큰 데이터 매 요청 재계산 → 시작 시 1회 계산, 페이지는 렌더만

## 서술형 예상 질문 → 골격
- "서버가 죽으면 운영자는?" → 현재 단일 프로세스, 재시작 필요. 폴백 정적 리포트 존재. 개선: 결과를 파일로 주기 저장 + 별도 뷰어
- "실시간인가?" → 아니다. 배치 결과를 N초마다 새로고침. 진짜 스트리밍은 큐/웹소켓 필요 — 요구사항에 없어 제외(합의서 근거)
- "왜 Flask/Streamlit 안 썼나?" → 설치 불확실·CDN 차단·stdlib로 요구 충족. 트레이드오프: 인터랙션 부족
