# D. 로그 · 텍스트 · 집계

## 단서
.log/.txt, 에러 코드, 알람 이력, 자유 텍스트 메모, 건수 집계, 일/주 리포트, 패턴

## 질문
1. 포맷 샘플 10줄, 형식 다른 줄(멀티라인, 헤더)
2. 시각 형식·타임존, 시간순 여부
3. 집계 단위(설비/코드/시간대/교대), 주기, 상위 N
4. 분류 필요 시 카테고리 목록 + 대표 단어
5. "중요 이벤트" 정의, 전후 몇 줄
6. 출력 형식, 그래프 여부

## 순서
```python
ps = logparse.PatternSet().add("main", r"^(?P<ts>\S+ \S+)\s+\[(?P<level>\w+)\]\s+(?P<eqp>\w+)\s+(?P<code>E\d+)?\s*(?P<msg>.*)$")
rows, unmatched = logparse.parse_lines(open(path, encoding="utf-8", errors="replace"), ps)
print("unmatched %.1f%%" % (100*len(unmatched)/max(1,len(rows)+len(unmatched))))
for r in rows: r["cat"], r["evidence"] = logparse.classify_text(r["msg"], CATEGORIES)
logparse.aggregate(rows, ["eqp", "level"]); logparse.aggregate(rows, ["code"], top=10)
logparse.context_window(lines, lambda l: "E1234" in l, 5, 5)
```
unmatched 샘플 5줄 → 무시 가능 여부 확인

## 최소
레벨별/설비별 건수 표(CSV) + unmatched 건수

## 검증
- 줄 수 알려진 샘플 → 매칭 수 == 기대
- unmatched ≠ 0이면 전부 열거
- 분류: 예문 10개 (`evalmetrics.classification_report`)
- 시간 파싱 실패 0, 역전 건수

## 함정
- 정규식 하나로 전부 → 패턴 2~3개 + unmatched
- cp949 → errors="replace"
- 멀티라인 건수 부풀림 → 들여쓰기 줄 합치기
- 분류 동률 → 근거 수 → 정의 순서, 문서화

## Q
못 잡은 줄 처리·비율 / 분류 정확도·키워드 한계 / 1GB 로그 스트리밍
