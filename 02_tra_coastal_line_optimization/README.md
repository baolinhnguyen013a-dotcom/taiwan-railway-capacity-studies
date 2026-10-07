# TRA Coastal Line exploratory bottleneck model

> **Status: unvalidated proof of concept. Not an official submission, engineering recommendation, safety case, timetable, or cost estimate.**

This directory contains a simplified software experiment concerning single-track river-bridge bottlenecks on the TRA Coastal Line. Published government material supports only limited background facts such as the overall planning scope, approval status, and aggregate project budget. Most bridge, signalling, timetable, reinforcement, cost, and operational inputs here are assumptions.

## What the model does

- calculates simplified bridge traversal and direction-reversal times;
- compares fixed dispatch rules in a toy event/kinematic environment;
- generates 123 synthetic train movements between 05:00 and 24:00;
- shifts bridge entry times forward to enforce mutual exclusion; and
- reports arithmetic scenario totals for inspection.

The zero-conflict counter is not evidence that the original schedule is conflict-free: the algorithm delays trains before checking conflicts. It does not propagate the adjusted schedule through a complete railway network.

## The legacy “RL” name

The names `RLAgentPolicy`, `CoastalBridgeRLDispatchEnv`, and `06_rl_dispatch_environment` are retained to avoid breaking the existing API and tests. `RLAgentPolicy` is not a trained reinforcement-learning model. It selects among fixed speed tiers using a hand-written scoring equation with static weights. Its `train()` method does not update those weights or populate its empty `q_table`.

## Cost scenario

Files under `05_cost_tradeoff_curves/` are scenario arithmetic, not sourced quantity-surveyor estimates. In particular, the NT$150 million reinforcement allowance per retained bridge has no supporting inspection or design package. The calculated NT$4.845 billion difference must not be called a verified saving.

## Run

```bash
python3 -m unittest discover -s tests -v
python3 scripts/run_bridge_bottleneck_simulation.py
python3 scripts/verify_coastal_model_integrity.py
```

The simulation writes `outputs/simulation_19h_summary.json`. Generated outputs are intentionally excluded from version control.

## Layout

- `01_corridor_topology/`: collected or assumed topology tables.
- `02_rolling_stock_signalling/`: assumed rolling-stock and signalling inputs.
- `03_timetable_baseline/`: synthetic service targets and runtimes.
- `04_bridge_bottleneck_model/`: simplified bridge arithmetic.
- `05_cost_tradeoff_curves/`: unvalidated cost scenario assumptions.
- `06_rl_dispatch_environment/`: legacy-named dispatch environment and fixed heuristics.
- `scripts/`: simulation and internal-consistency checks.
- `tests/`: software behavior tests.

Passing these tests does not validate real-world feasibility. See the repository-level [`LIMITATIONS.md`](../LIMITATIONS.md).
