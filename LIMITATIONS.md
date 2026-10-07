# Limitations and evidence boundary

## Applies to both studies

Automated checks validate selected file structures, deterministic calculations, and program behavior. They do not validate the accuracy, completeness, ownership, or fitness of source data, nor do they establish engineering feasibility, regulatory compliance, operational safety, or economic value.

The studies are independent. Evidence or test results from one study do not validate the other.

## Taipei Metro study

The readiness gate reports `READY_FOR_PRELIMINARY_SCREENING_ONLY` and intentionally exits with status 1. Ten requirements remain open, including value-level geometry provenance, a reproducible NFPA 130 evacuation workbook, whole-ring fleet and depot modeling, block/interlocking modeling, bankable lifecycle economics, official railML schema validation, route-length reconciliation, and drawing-level station geometry.

The model chainage is 14.732 km while the published route length is 13.250 km. The 1.482 km difference is unresolved. Positive capacity-screening results must not be interpreted as infrastructure, safety, or construction approval.

## TRA Coastal Line study

This is an exploratory software model with synthetic or unverified assumptions.

- `RLAgentPolicy` evaluates actions using fixed weights. Its `train()` method runs episodes but does not update weights, a Q-table, or another learned parameter. It is therefore a hand-tuned heuristic.
- The bridge routine generates 123 trains between 05:00 and 24:00, a 19-hour operating window.
- Bridge entry is shifted forward to the next permitted slot. The resulting zero-conflict count is a consequence of this scheduling rule and does not prove corridor-wide feasibility.
- The disruption output reports `SCHEDULE_INTERFERENCE` when secondary delay exceeds 90 seconds.
- Cost tables contain scenario assumptions. The assumed NT$150 million reinforcement cost per retained bridge lacks geotechnical, structural, hydraulic, seismic, and scour validation. The computed NT$4.845 billion difference is not a forecast or verified saving.
- Simplified kinematics omit substantial network, rolling-stock, signalling, maintenance, passenger-flow, recovery, and human-operational constraints.

The Coastal model must not be used to recommend retaining, replacing, reinforcing, or operating any bridge.

## Data and rights

Official facts should be checked against the cited primary source before reuse. Some tables combine published facts with modeled or assumed values. This package makes no representation that third-party data or imagery may be redistributed under an open-data license.
