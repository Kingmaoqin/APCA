# APCA and LoopShift-Bench

Code and benchmark for **Adaptive Process-Control Attacks on Human Oversight in Large Language
Model Agents** (anonymous submission).

- **APCA** (Adaptive Process-Control Attack) is a controller that selects task-preserving cues from
  public assistant text and turn position under a four-cue budget, while preserving canonical task
  content.
- **LoopShift-Bench** is a process-control benchmark built over the Berkeley Function Calling
  Leaderboard (BFCL) multi-turn tasks. It has an 80-task manifest, 2,817 minimal observation records
  (2,793 usable), and an executable scorer.

## Repository layout

```text
apca/                      APCA controller, cue library, constraint filter, BFCL adapter, runners
  attacker.py              condition rendering (C0–C5) and the state-dependent APCA controller
  attack_families.py       compression / inflation cue library and frozen constraints
  constraint_filter.py     payload-preservation and intervention-constraint guard
  targeted_selector.py     frozen-prior, state-matched cue selection
  adapters/bfcl_adapter.py BFCL multi-turn environment, tool loop and native checker
  extract_metrics.py       process metrics recorded with each episode
  run_confirmatory.py      episode runner (used for both evaluations)
  run_primary.sh           primary evaluation: neutral / static / APCA, six repeats
  run_controls.sh          interaction-control evaluation: six conditions, three repeats
configs/models.json        local OpenAI-compatible model endpoints
data/frozen/               frozen attacker policies, priors, hashes and split metadata
tests/                     unit tests (no network, no model server needed)
loopshift_bench/           the benchmark: manifest, splits, cue library, policies,
                           observation records, scorer, case traces
primary_episodes.csv       per-episode metrics, primary evaluation (1,404 usable)
controls_episodes.csv      per-episode metrics, interaction-control evaluation (1,389 usable)
recompute.py               per-condition aggregates and paired-task inference
```

Conditions: `C0` native BFCL wording, `C1` neutral wrapper, `C2` alternate neutral wrapper,
`C3` static pressure, `C4` APCA, `C5` explicit process instruction.

## Reproducing the reported results from stored records

```bash
python loopshift_bench/score_records.py   # Python >= 3.10, standard library only
pip install numpy
python recompute.py
```

The scorer recomputes all metrics from `observable_records.jsonl.gz` and cross-checks the 2,793
usable rows against the CSVs. Expected output: 2,817 scored records, 24 infrastructure exclusions,
0 metric mismatches. `recompute.py` writes `results/condition_summary.csv` and
`results/paired_effects.csv` (20,000 task-bootstrap draws, sign-flip tests, seed 20260903). For the
primary compression comparison it prints:

```text
     Q apca-neutral     n=39 -0.504 [-0.910, -0.120] p=0.0169
     Q static-neutral   n=39 -0.137 [-0.521, +0.256] p=0.4947
     Q apca-static      n=39 -0.367 [-0.786, +0.043] p=0.1008
     Z apca-static      n=39 +15.385 [+2.564, +28.205] p=0.0703
   ZWF apca-neutral     n=39 +5.128 [+0.000, +12.820] p=0.5000
```

## Running new trajectories

New episodes need the BFCL environments and a model server.

```bash
pip install -r requirements.txt            # bfcl-eval, numpy, pytest
python -m pytest -q tests                  # offline unit tests
# Serve the target model locally with an OpenAI-compatible API, e.g.
#   vllm serve Qwen/Qwen2.5-72B-Instruct-AWQ --served-model-name qwen25-72b --port 8010
bash apca/run_primary.sh                   # -> results/primary/confirmatory/
bash apca/run_controls.sh                  # -> results/controls/confirmatory/
```

The runners use the frozen policies in `data/frozen/`, set `--no-live-attacker`, and allow network
access only to loopback endpoints (`apca/common/net_guard.py`). Before a first run, build and freeze
the task registries with `python apca/build_splits.py` and
`python apca/canonical_message_cache.py --freeze` (with
`R9_BFCL_CATEGORIES=multi_turn_base,multi_turn_miss_param`), then confirm that the registries match
`data/frozen/split_hashes.sha256`. The evaluation set is defined by
`loopshift_bench/task_manifest.json`, which carries the canonical-message hashes of every task. The
end-to-end pipeline, including development runs and policy freezing, is in
`apca/run_full_pipeline.py`.

## License

MIT for the code in this repository. BFCL tasks, environments and the native checker are inherited
from BFCL and remain under their original license.
