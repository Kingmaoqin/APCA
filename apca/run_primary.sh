#!/bin/bash
# Primary APCA evaluation (paper Sec. 5, "primary", six repeats).
# Frozen BFCL multi-turn base + missing-parameter tasks, frozen attacker policy (no live
# paraphrase generation). Conditions: C1 neutral, C3 static pressure, C4 APCA.
# Requires a local OpenAI-compatible server for the target model (see configs/models.json).
set -eu
cd "$(dirname "$0")/.."
export R9_BFCL_CATEGORIES="multi_turn_base,multi_turn_miss_param"
export R9_RESULTS_SUBDIR="${R9_RESULTS_SUBDIR:-primary}"
PY="${PYTHON:-python}"
"$PY" -u apca/run_confirmatory.py --stage confirmatory \
  --models qwen25_72b --repeats 6 --conditions C1 C3 C4 --no-live-attacker
