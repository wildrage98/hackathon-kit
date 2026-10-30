# D. 로그 · 텍스트 파싱 · 집계 리포트

설비 로그/알람 이력/정비 메모가 입력일 때. "사무행정 처리", "자료 정리" 류도 여기(표 만들기·집계).
핵심 모듈: `kitlib.logparse`, `report`

## 단서
로그 파일(.log/.txt), 에러 코드, 알람 이력, 정비 메모(자유 텍스트), 건수 집계, 일/주 리포트, 패턴 찾기.

## 담당자 인터뷰 추가 질문
1. 로그 포맷 샘플 10줄과 **형식이 다른 줄**이 있는지 (멀티라인 스택트레이스, 헤더)
2. 시각 형식·타임존, 로그 순서가 시간순인지
3. 집계 단위(설비/코드/시간대/교대), 리포트 주기, 상위 몇 개까지
4. 텍스트 분류가 필요하면: 카테고리 목록과 각 카테고리의 대표 단어 (담당자가 준 단어가 분류 근거)
5. "중요 이벤트" 정의(ERROR만? 특정 코드?) 와 그 전후 몇 줄을 보고 싶은지
6. 출력: 표/CSV/HTML, 그래프 필요 여부

## 아키텍처
라인 읽기 → `PatternSet` 정규식(1~3개) → `parse_lines` (매칭 + **unmatched 보고**) → 시각 파싱 → `aggregate` → (분류 필요 시 `classify_text`) → `context_window`로 중요 이벤트 전후 → Report

## 모듈 순서
```python
ps = logparse.PatternSet().add("main", r"^(?P<ts>\S+ \S+)\s+\[(?P<level>\w+)\]\s+(?P<eqp>\w+)\s+(?P<code>E\d+)?\s*(?P<msg>.*)$")
rows, unmatched = logparse.parse_lines(open(path, encoding="utf-8", errors="replace"), ps)
print("unmatched %.1f%%" % (100*len(unmatched)/max(1,len(rows)+len(unmatched))))   # 반드시 보고
for r in rows: r["cat"], r["evidence"] = logparse.classify_text(r["msg"], CATEGORIES)
logparse.aggregate(rows, ["eqp", "level"]); logparse.aggregate(rows, ["code"], top=10)
logparse.context_window(lines, lambda l: "E1234" in l, 5, 5)
```
정규식은 담당자 샘플로 만들고, unmatched 샘플 5줄을 담당자에게 보여 "이 줄들은 무시해도 되나"를 확정받는다.

## 최소 실행본
로그 → 레벨별/설비별 건수 표(CSV). unmatched 건수 출력.

## 검증
- 알려진 줄 수의 샘플 로그로 매칭 수 == 기대 수
- unmatched가 0이 아니면 그 줄들을 전부 열거(샘플) — "못 잡은 것을 안다"가 검증
- 분류: 담당자가 준 예문 10개로 정확도 (evalmetrics.classification_report)
- 시간 파싱 실패 0건, 시간 역전 건수 보고

## 함정
- 정규식 하나로 전부 잡으려다 시간 소모 → 패턴 2~3개 + unmatched 보고가 정답
- 인코딩(cp949) → csvio._read_text 로직 참고하거나 errors="replace"
- 멀티라인(스택트레이스)을 별도 줄로 세어 건수 부풀림 → 연속 들여쓰기 줄은 이전 줄에 합치는 전처리
- 키워드 분류의 동률/중복 → classify_text는 근거 수→정의 순서로 결정, 그 규칙을 문서화

## 서술형 예상 질문 → 골격
- "정규식이 못 잡은 줄은 어떻게 했나?" → unmatched n건(%) 보고, 샘플 담당자 확인, 집계에서 제외하고 리포트에 명시. 개선: 패턴 추가 or 수동 검토 큐
- "분류 정확도는?" → 예문 기준 x%, 틀린 예 유형. 키워드 방식의 한계(동의어·부정문) → 개선: 사전 확장, 담당자 피드백 루프
- "로그가 하루 1GB면?" → 현재 한 줄씩 스트리밍이라 메모리 OK, 속도는 정규식 수에 비례 → 컴파일 캐시, 날짜별 분할
