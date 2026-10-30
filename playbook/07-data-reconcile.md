# G. 데이터 대사

## 단서
파일 2개 이상, 불일치, 누락, 대조, 마스터, 정합성, 차이, 중복 키

## 질문
1. 키 (로트? 로트+웨이퍼? 날짜+설비?), 표기 동일? (대소문자, 공백, 선행 0)
2. 기준(source of truth) 쪽
3. 비교 컬럼, 허용 오차, 날짜 포맷
4. 중복 키 정상? 오류?
5. 결과물: 불일치 목록 + 요약 + 원인 분류?
6. 주기 실행? → CLI 인자

## 순서
```python
a, _ = csvio.read_csv("a.csv"); b, _ = csvio.read_csv("b.csv")
raw = reconcile.compare(a, b, KEY, COLS, tol=TOL, upper=False)
norm = reconcile.compare(a, b, KEY, COLS, tol=TOL, upper=True, strip_zeros=True)
# raw→norm 감소분 = 표기 차이
csvio.write_csv("outputs/mismatch.csv", norm["mismatch"])
report.Report("대사").raw_md(reconcile.summary_markdown(norm)).table(norm["only_in_a"]).table(norm["mismatch"])
```

## 최소
키 하나로 only_in_a/only_in_b 건수 + 목록 CSV

## 검증
- A 복사 → B에 변경 심기(삭제 3, 값 변경 2, 키 공백 1) → 건수 일치
- 정규화 on/off 비교
- tol=0.5: 0.5 일치, 0.51 불일치
- keys_a = matched + only_in_a

## 함정
- 정규화 안 함 → only_in 50% 넘으면 키 표기 의심
- 한쪽만 문자열 숫자 → profile 타입
- 중복 키 첫 행으로 눌림 → dup 별도 보고
- 어느 쪽이 맞는지 내가 판단 → "불일치"로만

## Q
진짜 오류 건수 (정규화·오차 제외 후) / 복합키 성능 / 날짜 포맷 다르면
