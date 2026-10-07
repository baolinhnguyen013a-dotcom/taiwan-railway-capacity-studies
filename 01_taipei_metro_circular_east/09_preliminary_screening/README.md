# 09_preliminary_screening: East-Section Preliminary Capacity Screening Engine

## 1. Engine Scope and System Boundaries

This module implements a deterministic, fail-closed preliminary capacity screening engine for the **Taipei Circular Line East Section**.

### Spatial and Temporal Bounds
- **Corridor Nodes**: Exactly 12 stations in topological order:
  `Y29` (Jiannan Rd), `Y30`, `Y31`, `Y32`, `Y33`, `Y34`, `Y35`, `Y36`, `Y37`, `Y38`, `Y39`, `Y01` (Taipei Zoo).
- **Corridor Links**: Exactly 11 contiguous track segments (`LK01` through `LK11`).
- **Temporal Analysis Window**: Morning Peak 07:00–09:00 (Time Band `TB02` from `official_operational_service_baseline.csv`).
- **Boundary Condition**: Boundary trains enter at `Y29` or `Y01` and disappear at the opposite boundary station upon clearing the East Section.
- **External Network Propagation**: `NOT_MODELED`. Interaction with Northern, Southern, or Western Sections is outside the preliminary screening gate.
- **Passing Loops**: `NOT_MODELED`. All single-track candidate sections are evaluated as contiguous shuttle blocks without dynamic passing loops.

### Strict Non-Goals & Scope Exclusions
Per project analysis readiness governance (`READY_FOR_PRELIMINARY_SCREENING_ONLY` with 10 open blockers):
- **Whole-ring circulation**: Excluded (`NOT_MODELED`).
- **Depot throat, storage tracks, and fleet sizing**: Excluded (`NOT_MODELED`).
- **Passing loops / dynamic sidings**: Excluded (`NOT_MODELED`).
- **Block-level signalling microsimulation**: Excluded (`NOT_MODELED`).
- **Life safety & egress certification (NFPA 130)**: Excluded (`NOT_MODELED`).
- **Lifecycle economics / bankable NPV / CAPEX optimization**: Excluded (`NOT_MODELED`).
- **Reinforcement learning / mathematical dispatch optimization**: Excluded (`NOT_MODELED`).

---

## 2. Methodology & Mathematical Formulations

### A. Double-Track Benchmark Capacity
For each link and direction under Time Band `TB02` baseline parameters:
- **Headway**:
  - CCW Headway $h_{ccw} = 150\,\text{s}$ ($\text{TPH}_{ccw} = 3600 / 150 = 24.0$).
  - CW Headway $h_{cw} = 198\,\text{s}$ ($\text{TPH}_{cw} = 3600 / 198 = 18.1818\dots$).
- **Nominal Capacity**:
  $$\text{Nominal Capacity} = \text{TPH} \times 650\,\text{pax}$$
  - CCW: $24.0 \times 650 = 15,600.00\,\text{pphpd}$.
  - CW: $18.1818\dots \times 650 \approx 11,818.18\,\text{pphpd}$.
- **Effective Capacity**:
  $$\text{Capacity}_{\text{effective}} = \text{Nominal Capacity} \times \text{usable\_load\_factor}$$
- **Screened Demand**:
  $$\text{Demand}_{\text{screened}} = \text{Demand}_{\text{official}} \times \text{demand\_multiplier}$$
- **Volume-to-Capacity Ratio ($V/C$)**:
  $$V/C = \frac{\text{Demand}_{\text{screened}}}{\text{Capacity}_{\text{effective}}}$$

#### Direction Correction Rule
Official link tables store links from station $i$ to station $i+1$ in the clockwise (CW, toward Zoo) direction.
- **Clockwise (CW) movement**: runs $\text{from\_station} \to \text{to\_station}$ using $\text{flow\_clockwise\_to\_zoo\_pphpd}$.
- **Counterclockwise (CCW) movement**: runs $\text{to\_station} \to \text{from\_station}$ using $\text{flow\_counterclockwise\_to\_jiannan\_pphpd}$.
- Specifically for **LK07**: CCW movement is actual $\text{Y36} \to \text{Y35}$ carrying $15,250\,\text{pphpd}$.

#### Rating Tiers
- $V/C \le 0.85$: `COMFORTABLE` ($\to$ `PRELIMINARY_CAPACITY_PASS_INFRASTRUCTURE_UNVERIFIED`)
- $0.85 < V/C \le 1.00$: `TIGHT` ($\to$ `PRELIMINARY_CAPACITY_PASS_INFRASTRUCTURE_UNVERIFIED`)
- $V/C > 1.00$: `FAIL` ($\to$ `FAIL_CAPACITY`)

---

### B. Contiguous No-Loop Section Capacity (All 66 Intervals)
For any contiguous station pair $(i, j)$ with $i < j$, spanning $k = j - i$ links:
- **Intermediate Station Count**:
  $$\text{intermediate\_count} = k - 1$$
- **Per-Direction Traversing Time**:
  $$t_{cw} = \left(\sum \text{run\_time}\right) \times \text{runtime\_multiplier} + \text{intermediate\_count} \times \text{dwell\_s}$$
  $$t_{ccw} = \left(\sum \text{run\_time}\right) \times \text{runtime\_multiplier} + \text{intermediate\_count} \times \text{dwell\_s}$$
  *(Note: Symmetric runtime between directions is explicitly classified as a `PROXY_SCREENING_ASSUMPTION`)*.
- **Block Cycle Time**:
  $$\text{cycle} = t_{cw} + t_{ccw} + 2 \times \text{change\_s} + \text{recovery\_s}$$
  *(2 boundary changes: one at each terminus for turnout locking/proving/route clear)*.
- **Single-Track Throughput**:
  $$\text{TPH} = \frac{3600}{\text{cycle}}$$
- **Effective Directional Capacity**:
  $$\text{Capacity} = \text{TPH} \times 650 \times \text{usable\_load\_factor}$$
- **Directional Demand**:
  $$\text{Demand}_{cw} = \max_{\text{links}} (\text{flow}_{cw}) \times \text{demand\_multiplier}$$
  $$\text{Demand}_{ccw} = \max_{\text{links}} (\text{flow}_{ccw}) \times \text{demand\_multiplier}$$
- **Both-Directions Pass Rule**:
  $$\max(V/C_{cw}, V/C_{ccw}) \le 1.00$$
  Both directions must pass simultaneously for the section to achieve `PRELIMINARY_CAPACITY_PASS_INFRASTRUCTURE_UNVERIFIED`. If either direction exceeds $1.00$, status is `FAIL_CAPACITY`.

---

### C. Regression Benchmark Verification
For candidate section **Y39–Y01** (Mountain Tunnel Section, S1) under baseline scenario **S00**:
- Links spanned: `LK11` ($\text{run\_time} = 193.0\,\text{s}$).
- Intermediate stations: $0$.
- Parameters: $\text{runtime\_multiplier}=1.0$, $\text{dwell}=0\,\text{s}$, $\text{change}=18\,\text{s}$, $\text{recovery}=60\,\text{s}$, $\text{demand\_multiplier}=1.0$, $\text{usable\_load}=1.0$.
- Cycle:
  $$\text{cycle} = 193 + 193 + 2 \times 18 + 60 = 482.0\,\text{s}$$
- Effective Capacity:
  $$\text{Capacity} = \frac{3600}{482} \times 650 \times 1.0 = 4,854.77\,\text{pphpd}$$
- Critical Demand:
  $$\text{CCW Demand} = 10,310\,\text{pphpd}$$
- Volume-to-Capacity Ratio:
  $$V/C_{ccw} = \frac{10310}{4854.7718} \approx 2.1237 > 1.00$$
- Result: **`FAIL_CAPACITY`** (Regression matches exact expected figure).

---

## 3. Screening Scenarios & Governance Labeling

All scenario multipliers and parameters explore operational sensitivities. **Sensitivities are exploratory parametric screenings and not probabilities or forecasts.**

| Scenario | Demand Multiplier | Usable Load Factor | Runtime Multiplier | Dwell (s) | Change (s) | Recovery (s) | Governance Classification | Interpretation Note |
|---|---|---|---|---|---|---|---|---|
| **S00** | 1.0 | 1.0 | 1.0 | 0 | 18 | 60 | `PROXY_SCREENING_ASSUMPTION` | Nominal unconstrained pure-run baseline |
| **S01** | 1.0 | 0.9 | 1.0 | 30 | 18 | 60 | `ASSUMED_SCREENING_SENSITIVITY` | Standard 30s intermediate dwell, 90% load |
| **S02** | 1.1 | 0.9 | 1.0 | 30 | 18 | 60 | `ASSUMED_SCREENING_SENSITIVITY` | +10% peak demand surge sensitivity |
| **S03** | 1.0 | 0.9 | 1.1 | 45 | 30 | 120 | `ASSUMED_SCREENING_SENSITIVITY` | Operational stress (+10% run, 45s dwell, 120s rec) |
| **S04** | 1.2 | 0.8 | 1.1 | 45 | 30 | 120 | `ASSUMED_SCREENING_SENSITIVITY` | Compound severe stress (+20% demand, 80% load) |
| **S05** | 0.9 | 1.0 | 0.9 | 0 | 0 | 0 | `ASSUMED_SCREENING_SENSITIVITY` | Pure technical speed run (zero buffers) |
| **S06** | 1.0 | 0.7 | 1.0 | 30 | 18 | 60 | `ASSUMED_SCREENING_SENSITIVITY` | High comfort / degraded vehicle capacity (70% load) |

---

## 4. Directory Layout

```
09_preliminary_screening/
├── README.md
├── inputs/
│   ├── boundary_conditions.csv
│   ├── named_alternatives.csv
│   └── screening_scenarios.csv
└── outputs/
    ├── link_capacity_screen.csv
    ├── representative_section_occupations.csv
    ├── screening_summary.json
    └── section_capacity_screen.csv
```

---

## 5. Execution and Verification Commands

1. **Run Preliminary Screening Engine**:
   ```bash
   python3 scripts/run_east_section_screening.py
   ```
2. **Run Dedicated Screening Verifier**:
   ```bash
   python3 scripts/verify_east_section_screening.py
   ```
3. **Run Unit Tests**:
   ```bash
   python3 -m unittest tests/test_east_section_screening.py
   ```
4. **Run Full Pipeline Verification**:
   ```bash
   python3 scripts/verify_pipeline_integrity.py
   python3 scripts/verify_source_snapshot.py
   python3 scripts/audit_and_prepare.py
   python3 scripts/verify_analysis_readiness.py
   ```
