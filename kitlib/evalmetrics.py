"""evalmetrics — 탐지/분류 지표.

  event_prf(truth_intervals, detections, tolerance_s=60, truth_keys=None, det_keys=None)
     truth_intervals [(start, end)], detections [ts] 또는 [(start, end)] → tp/fp/fn/precision/recall/f1/mean_latency_s/missed
     탐지가 정답 구간(±tolerance) 안이면 TP(정답당 1회), 어디에도 안 들면 FP. 키를 주면 같은 키끼리만 매칭.
  point_prf(y_true_bool, y_pred_bool)
  classification_report(y_true, y_pred) → 클래스별 P/R/F1, accuracy, confusion
  report_markdown(m)
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Sequence, Tuple, Union

T = Union[datetime, float, int]


def _sec(x: T) -> float:
    return x.timestamp() if isinstance(x, datetime) else float(x)


def event_prf(truth_intervals: Sequence[Tuple[T, T]], detections: Sequence, tolerance_s: float = 60.0,
              truth_keys: Sequence = None, det_keys: Sequence = None) -> Dict:
    """truth_keys/det_keys(설비 등)를 주면 같은 키끼리만 매칭한다 — 다른 설비의 경보가 정답으로 잡히는 착시 방지."""
    truths = [(_sec(a), _sec(b)) for a, b in truth_intervals]
    tkeys = list(truth_keys) if truth_keys is not None else [None] * len(truths)
    dets: List[Tuple[float, float]] = []
    for d in detections:
        if isinstance(d, (tuple, list)):
            dets.append((_sec(d[0]), _sec(d[1])))
        else:
            dets.append((_sec(d), _sec(d)))
    dkeys = list(det_keys) if det_keys is not None else [None] * len(dets)
    matched_truth = {}
    fp = []
    for (ds, de), dk in zip(dets, dkeys):
        hit = None
        for i, (ts, te) in enumerate(truths):
            if tkeys[i] != dk:
                continue
            if ds <= te + tolerance_s and de >= ts - tolerance_s:
                hit = i
                break
        if hit is None:
            fp.append((ds, de, dk))
        else:
            matched_truth.setdefault(hit, []).append(ds)
    tp = len(matched_truth)
    fn = len(truths) - tp
    precision = tp / (tp + len(fp)) if (tp + len(fp)) else 0.0
    recall = tp / len(truths) if truths else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    latencies = [max(0.0, min(v) - truths[i][0]) for i, v in matched_truth.items()]
    return {"n_truth": len(truths), "n_detections": len(dets), "tp": tp, "fp": len(fp), "fn": fn,
            "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
            "mean_latency_s": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "missed": [i for i in range(len(truths)) if i not in matched_truth], "false_positives": fp[:20]}


def point_prf(y_true: Sequence[bool], y_pred: Sequence[bool]) -> Dict:
    tp = sum(1 for a, b in zip(y_true, y_pred) if a and b)
    fp = sum(1 for a, b in zip(y_true, y_pred) if not a and b)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a and not b)
    tn = sum(1 for a, b in zip(y_true, y_pred) if not a and not b)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0, "accuracy": round((tp + tn) / max(1, len(y_true)), 4)}


def classification_report(y_true: Sequence, y_pred: Sequence) -> Dict:
    labels = sorted(set(y_true) | set(y_pred), key=str)
    conf: Dict = defaultdict(Counter)
    for a, b in zip(y_true, y_pred):
        conf[a][b] += 1
    per = {}
    for l in labels:
        tp = conf[l][l]
        fp = sum(conf[o][l] for o in labels if o != l)
        fn = sum(conf[l][o] for o in labels if o != l)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        per[l] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0, "support": tp + fn}
    acc = sum(conf[l][l] for l in labels) / max(1, len(y_true))
    return {"labels": labels, "per_class": per, "accuracy": round(acc, 4),
            "confusion": {str(a): {str(b): conf[a][b] for b in labels} for a in labels}}


def report_markdown(m: Dict) -> str:
    if "per_class" in m:
        lines = ["| 클래스 | P | R | F1 | n |", "|---|---|---|---|---|"]
        for l, d in m["per_class"].items():
            lines.append("| %s | %s | %s | %s | %d |" % (l, d["precision"], d["recall"], d["f1"], d["support"]))
        lines.append("\naccuracy = %s" % m["accuracy"])
        return "\n".join(lines)
    keys = ["n_truth", "n_detections", "tp", "fp", "fn", "precision", "recall", "f1", "mean_latency_s"]
    return "| " + " | ".join(keys) + " |\n|" + "---|" * len(keys) + "\n| " + " | ".join(str(m.get(k)) for k in keys) + " |"
