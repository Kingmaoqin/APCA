#!/usr/bin/env python3
"""LoopShift-Bench scorer: deterministic per-episode metrics from the observation records.

Standard library only (Python >= 3.10).

    python loopshift_bench/score_records.py            # score and cross-check ../*_episodes.csv
    python loopshift_bench/score_records.py --write    # (re)write ../*_episodes.csv

Metric definitions (paper Sec. 4.2 and Appendix H):
  Q   question-mark turns: canonical user turns whose recorded agent messages contain "?"
  Z   question-free episode, 1[Q = 0]
  W   at least one successful state-changing (mutating) tool call
  F   completed BFCL-native failure (endpoint success = 0 and termination = completed)
  ZWF observed joint endpoint
  all_reads        successful read calls (tool_type == "read"; fallback: successful non-mutating)
  first_mutation   0-based call index of the first successful mutating call (blank if none)
  reads_before_first_mutation, total_tool_calls, success, error_type
Infrastructure failures are scored but excluded from the CSVs and all analyses.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORDS = HERE / "observable_records.jsonl.gz"
BATCHES = ("primary", "controls")
FIELDS = ["episode_id", "batch", "task_id", "category", "family", "condition", "condition_name",
          "model", "repeat", "Q", "Z", "W", "F", "ZWF", "all_reads", "first_mutation",
          "reads_before_first_mutation", "total_tool_calls", "success", "error_type"]


def is_read(call: dict) -> bool:
    if call.get("tool_type") is not None:
        return call["tool_type"] == "read" and call["ok"]
    return call["ok"] and not call["mutating"]


def score(rec: dict) -> dict:
    calls = rec["tool_calls"]
    q = sum(any("?" in m for m in t["agent_messages"]) for t in rec["turns"])
    first_mut = next((i for i, c in enumerate(calls) if c["mutating"] and c["ok"]), None)
    w = int(first_mut is not None)
    f = int(rec["endpoint"]["success"] == 0 and rec["endpoint"]["termination_reason"] == "completed")
    z = int(q == 0)
    upto = calls if first_mut is None else calls[:first_mut]
    return {
        **{k: rec[k] for k in ("episode_id", "batch", "task_id", "category", "family", "condition",
                               "condition_name", "model", "repeat")},
        "Q": q, "Z": z, "W": w, "F": f, "ZWF": z * w * f,
        "all_reads": sum(is_read(c) for c in calls),
        "first_mutation": "" if first_mut is None else first_mut,
        "reads_before_first_mutation": sum(is_read(c) for c in upto),
        "total_tool_calls": len(calls),
        "success": rec["endpoint"]["success"],
        "error_type": rec["endpoint"]["error_type"] or "",
    }


def load_records() -> list[dict]:
    with gzip.open(RECORDS, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="write ../<batch>_episodes.csv")
    args = ap.parse_args()

    recs = load_records()
    excluded = sum(r["infra_failure"] for r in recs)
    rows = [score(r) for r in recs if not r["infra_failure"]]
    print(f"scored records: {len(recs)}  infrastructure exclusions: {excluded}  usable: {len(rows)}")

    mismatches = 0
    for batch in BATCHES:
        path = HERE.parent / f"{batch}_episodes.csv"
        mine = [r for r in rows if r["batch"] == batch]
        if args.write:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(mine)
            print(f"wrote {path.name}: {len(mine)} rows")
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            ref = {r["episode_id"]: r for r in csv.DictReader(fh)}
        if set(ref) != {r["episode_id"] for r in mine}:
            print(f"{path.name}: episode set differs", file=sys.stderr)
            mismatches += 1
        for r in mine:
            exp = ref.get(r["episode_id"], {})
            for k in FIELDS:
                if str(r[k]) != exp.get(k):
                    mismatches += 1
        print(f"{path.name}: {len(mine)} usable rows checked")
    if not args.write:
        print(f"metric mismatches: {mismatches}")
    return int(mismatches > 0)


if __name__ == "__main__":
    sys.exit(main())
