# Taiwan Railway Capacity Studies

This repository contains two independent, exploratory railway-capacity studies released for methodological review and reproducibility. It is not an official government publication, engineering design, safety case, cost estimate, procurement recommendation, or operational timetable.

## Projects

### Taipei Metro Circular Line East Section

[`01_taipei_metro_circular_east/`](01_taipei_metro_circular_east/README.md) is a counterfactual preliminary screening study. Its fail-closed audit reports `READY_FOR_PRELIMINARY_SCREENING_ONLY` with ten open blockers. The approved twin-bore project is already under construction; this repository does not propose a construction change.

### TRA Coastal Line

[`02_tra_coastal_line_optimization/`](02_tra_coastal_line_optimization/README.md) is a simplified proof-of-concept model. Inputs concerning bridge condition, signalling, timetable, costs, and construction are partly assumed and have not been independently validated. The legacy identifiers `RLAgentPolicy` and `06_rl_dispatch_environment` are retained for compatibility, but the implemented policy is a fixed-weight analytical heuristic—not reinforcement learning.

## Important limitations

Read [`LIMITATIONS.md`](LIMITATIONS.md) before interpreting any result. In particular:

- passing tests establishes software behavior and arithmetic consistency only;
- the Taipei analysis is not ready for formal optimization, safety certification, or bankable economics;
- the Coastal model simulates 123 trains over a 19-hour operating window, not 124 trains over 24 hours;
- the Coastal scheduler shifts entry times to maintain mutual exclusion, so zero recorded conflicts does not establish timetable feasibility;
- Coastal cost figures are unvalidated scenario assumptions, not expected project savings; and
- neither project has been reviewed or endorsed by MOTC, the Railway Bureau, TRA Corporation, Taipei DORTS, or another public authority.

## Reproduce the checks

Python 3.10 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

cd 01_taipei_metro_circular_east
python3 -m unittest discover -s tests -v
python3 scripts/verify_pipeline_integrity.py
# Expected to exit 1 while formal-readiness blockers remain:
python3 scripts/verify_analysis_readiness.py

cd ../02_tra_coastal_line_optimization
python3 -m unittest discover -s tests -v
python3 scripts/run_bridge_bottleneck_simulation.py
python3 scripts/verify_coastal_model_integrity.py
```

GitHub Actions runs the same core test and verification sequence on every push and pull request.

## Repository policy

- Do not describe model outputs as official, certified, validated, construction-ready, or safety-approved.
- Do not use this repository for live railway operations or safety-critical decisions.
- Generated Coastal outputs are intentionally not committed; regenerate them locally from the scripts.
- Original software and documentation are available under the [`MIT License`](LICENSE). Third-party and government-derived materials remain subject to their original terms; see [`NOTICE.md`](NOTICE.md).
