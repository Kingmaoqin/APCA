#!/usr/bin/env python3
"""Per-condition aggregates and paired-task inference from the episode tables.

    python recompute.py            # writes results/condition_summary.csv, results/paired_effects.csv

Repeats are averaged within (task, condition); conditions are paired on common task support.
Intervals: 20,000 task-bootstrap draws (percentile). Tests: two-sided sign flips, exact when at
most 20 task differences are nonzero, otherwise 50,000 draws with the (k+1)/(B+1) correction.
Seed 20260903 (paper Appendix D.1).
"""
from __future__ import annotations

import csv
import itertools
import pathlib
from collections import defaultdict

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "results"
SEED = 20260903
N_BOOT = 20_000
N_FLIP = 50_000
METRICS = ["Q", "Z", "W", "ZWF", "all_reads", "reads_before_first_mutation", "total_tool_calls",
           "success"]
PCT = {"Z", "W", "ZWF", "success"}  # reported in percent / percentage points
CONTRASTS = {
    "primary": [("apca", "neutral"), ("static", "neutral"), ("apca", "static")],
    "controls": [("apca", "neutral"), ("static", "neutral"), ("apca", "static"),
                 ("explicit", "neutral"), ("native", "neutral"), ("alt_neutral", "neutral")],
}


def load(batch: str) -> list[dict]:
    with open(ROOT / f"{batch}_episodes.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def task_means(rows, family, cond, metric, category=None):
    acc = defaultdict(list)
    for r in rows:
        if r["family"] == family and r["condition_name"] == cond and \
                (category is None or r["category"] == category):
            acc[r["task_id"]].append(float(r[metric]))
    return {t: float(np.mean(v)) for t, v in acc.items()}


def sign_flip_p(d: np.ndarray, rng) -> float:
    obs = abs(d.mean())
    nz = d[d != 0]
    if len(nz) == 0:
        return 1.0
    if len(nz) <= 20:
        signs = np.array(list(itertools.product([-1, 1], repeat=len(nz))))
        stats = np.abs((signs * nz).sum(axis=1) / len(d))
        return float(np.mean(stats >= obs - 1e-12))
    signs = rng.choice([-1, 1], size=(N_FLIP, len(nz)))
    stats = np.abs((signs * nz).sum(axis=1) / len(d))
    return float((np.sum(stats >= obs - 1e-12) + 1) / (N_FLIP + 1))


def paired(a: dict, b: dict, rng):
    tasks = sorted(set(a) & set(b))
    d = np.array([a[t] - b[t] for t in tasks])
    boot = d[rng.integers(0, len(d), size=(N_BOOT, len(d)))].mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return len(tasks), d.mean(), lo, hi, sign_flip_p(d, rng)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    summary, effects = [], []
    for batch, contrasts in CONTRASTS.items():
        rows = load(batch)
        for family in ("compression", "inflation"):
            conds = sorted({r["condition_name"] for r in rows if r["family"] == family})
            for cond in conds:
                line = {"batch": batch, "family": family, "condition": cond}
                for m in METRICS:
                    tm = task_means(rows, family, cond, m)
                    scale = 100 if m in PCT else 1
                    line["n_tasks"] = len(tm)
                    line[m] = round(scale * float(np.mean(list(tm.values()))), 4)
                summary.append(line)
            for category in (None, "base", "miss_param"):
                for treat, base in contrasts:
                    if treat not in conds or base not in conds:
                        continue
                    for m in METRICS:
                        rng = np.random.default_rng(SEED)
                        n, est, lo, hi, p = paired(task_means(rows, family, treat, m, category),
                                                   task_means(rows, family, base, m, category), rng)
                        s = 100 if m in PCT else 1
                        effects.append({"batch": batch, "family": family,
                                        "subset": category or "all", "contrast": f"{treat}-{base}",
                                        "metric": m, "n_tasks": n, "effect": round(s * est, 4),
                                        "ci_low": round(s * lo, 4), "ci_high": round(s * hi, 4),
                                        "p_sign_flip": round(p, 4)})
    for name, table in (("condition_summary.csv", summary), ("paired_effects.csv", effects)):
        with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(table[0]))
            w.writeheader()
            w.writerows(table)
        print(f"wrote results/{name} ({len(table)} rows)")

    print("\nPrimary compression, all tasks (headline contrasts):")
    for e in effects:
        if e["batch"] == "primary" and e["family"] == "compression" and e["subset"] == "all" \
                and e["metric"] in ("Q", "Z", "ZWF"):
            print(f"  {e['metric']:>4} {e['contrast']:<16} n={e['n_tasks']} {e['effect']:+.3f} "
                  f"[{e['ci_low']:+.3f}, {e['ci_high']:+.3f}] p={e['p_sign_flip']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
