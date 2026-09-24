#!/bin/bash
# Interaction-control study (paper Sec. 5, "controls", three repeats).
# Conditions: C0 unwrapped BFCL wording, C1 neutral, C2 alternate neutral wrapper,
# C3 static pressure, C4 APCA, C5 explicit verify-less / verify-more instruction.
set -eu
cd "$(dirname "$0")/.."
export R9_BFCL_CATEGORIES="multi_turn_base,multi_turn_miss_param"
export R9_RESULTS_SUBDIR="${R9_RESULTS_SUBDIR:-controls}"
PY="${PYTHON:-python}"
"$PY" -u apca/run_confirmatory.py --stage confirmatory \
  --models qwen25_72b --repeats 3 --conditions C0 C1 C2 C3 C4 C5 --no-live-attacker
