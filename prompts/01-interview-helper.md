# 01 — 인터뷰 보조 (데이터를 받은 직후)

데이터 원본을 Codex에 통째로 읽히지 않는다. 먼저 터미널에서:
```bash
python tools/profile_csv.py data/<파일>.csv --key equipment --ts timestamp > docs/PROFILE.md
```
그 다음 Codex에:
```
docs/PROFILE.md 를 읽어라 (원본 CSV는 열지 마라, 토큰 절약).
1. 이 데이터로 과제를 수행하려면 담당자에게 반드시 확인해야 할 질문을 중요도순 7개 이내로 써라.
   각 질문에 "답이 없으면 내가 가정할 기본값"을 붙여라. (예: 결측 → 표시 후 판정 제외)
2. 데이터 품질 위험(결측/중복/역전/끊김/단위) 중 PROFILE에서 보이는 것을 수치와 함께 적어라.
3. 이 데이터에 맞는 kitlib 모듈 조합을 playbook/README.md 의 매트릭스에서 골라 한 줄로 제안해라.
출력은 세 섹션, 각 10줄 이내.
```
질문은 **내가** 담당자 채팅에 보낸다 (playbook/stakeholder-interview.md 의 묶음 형식으로).
