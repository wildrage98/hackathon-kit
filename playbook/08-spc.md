# H. SPC (보조)

## 단서
관리도, 관리한계, UCL/LCL, USL/LSL, Cp/Cpk, 공정능력, 런 룰, 부분군, 이동범위

## 질문
1. 관리한계 주어지나 vs 계산 → 기준 기간
2. 부분군 크기 (1 = I-MR, n = Xbar-R)
3. 스펙 한계 별도 여부 (스펙 이탈 = 불량, 관리 이탈 = 공정 변화)
4. 런 룰 1·2·3·4 중 적용, 룰별 등급
5. Cpk 판정 기준 (1.33? 1.0?)

## 순서
```python
lim = spc.imr_limits(baseline_values)
viol = spc.western_electric(values, lim["mean"], lim["sigma_est"])
cap = spc.cp_cpk(values, LSL, USL)
# rules.Rule(lo=lcl, hi=ucl, severity="WARN") 로 A 파이프라인에 합류
# 부분군: spc.xbar_r_limits([[...],[...]])
```

## 최소
I-MR 한계 + 룰1 표 + 차트(ucl/lcl threshold)

## 검증
- 알려진 평균/σ 합성 → UCL ≈ mean+3σ
- 룰 1~4 각각 트리거 시퀀스 (`TestSPC`)
- Cpk: 중심 = 스펙 중앙이면 Cp==Cpk

## 함정
- 기준 기간에 이상 섞임 → σ 과대
- 설비별 중심 다른데 전역 한계 → 룰4 폭발 → 설비별
- 관리한계 vs 스펙한계 혼동 → 다른 색/라벨
- 자기상관 센서 I-MR 과탐 → 간격 늘리기/EWMA

## Q
UCL 계산(2.66·MRbar, 가정) / 스펙 vs 관리 이탈 / Cpk 0.9 의미
