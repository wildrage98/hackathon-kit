"""kitlib — 해커톤용 표준라이브러리 전용 빌딩블록.

외부 패키지 없이(Python 3.8+) 동작한다. pandas가 있으면 더 빠르지만, 응시 환경에서
pip 설치가 막힐 수 있으므로 모든 모듈은 stdlib만 쓴다.

모듈 지도 (언제 무엇을 쓰는지는 playbook/README.md 참고)
  csvio        CSV 읽기/쓰기 (인코딩·구분자 자동 판별, 숫자 변환)
  timeparse    타임스탬프 파싱(Z, +09:00, epoch 등), 정렬, 간격 추정
  quality      결측/중복/시간역전/수신끊김/범위이탈/고착 센서 점검 + 처리 정책
  profile      데이터 한눈에 보기(스키마·통계·시간범위) → 마크다운
  rules        임계치 기반 판정 엔진 (경계 포함/제외, 등급, 지속조건, 근거 출력)
  stats_detect 통계 기반 이상 탐지 (rolling z, EWMA, CUSUM, IQR, 변화율)
  alerts       경보 상태머신 (START/ESCALATE/DEESCALATE/END 이벤트 로그)
  spc          관리도 (I-MR, Xbar-R), Western Electric 룰, Cp/Cpk
  groupstats   불량률 요인 분석 (그룹별 비율, lift, 카이제곱, 수치 비교)
  schedule     단순 스케줄링/디스패칭 (FIFO/SPT/EDD/우선순위/CR) + 지표
  logparse     로그 라인 정규식 파서, 키워드 분류, 집계
  report       마크다운/HTML 리포트 빌더
  svgchart     의존성 없는 SVG 선/막대 차트 (CDN 없이 대시보드용)
  webapp       http.server 기반 대시보드 (0.0.0.0, PORT env, 바인딩 실패 시 폴백)
  synth        합성 센서 데이터 + 이상/품질문제 주입 + 정답(ground truth)
  evalmetrics  탐지 성능(허용오차 기반 P/R/F1), 분류 리포트
  cli          argparse 서브커맨드 스켈레톤 + 파일 로깅

사용 규칙: 쓰는 모듈만 남기고 나머지는 지워도 된다. 가져다 쓴 모듈은 DECISIONS.md에
"출처: hackathon-kit kitlib/<모듈>, 수정: ..." 한 줄을 남긴다. 서술형에서 설명할 수
있는 코드만 쓴다.
"""

__version__ = "0.2.0"
