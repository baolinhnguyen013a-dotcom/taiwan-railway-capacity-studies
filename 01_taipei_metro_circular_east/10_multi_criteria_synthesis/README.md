# 10_multi_criteria_synthesis: Multi-Criteria Synthesis and Governance Reconciliation Engine

## 1. Scope, Context, and Governance Framework

Phase 10 provides the **Multi-Criteria Synthesis** module for the Taipei Circular Line East Section counterfactual infrastructure optimization study.

### Context and Problem Statement
Earlier research in Domain `06_lifecycle_costs` (`lifecycle_cost_comparison_30yr.csv`) hypothesized economic advantages for single-track configurations, labelling:
- **ALT-S1** (Y39–Y01 single bore) as *"Optimal Alternative"* with an alleged initial CAPEX saving of NT$ 5.85B and 30-year net NPV saving of NT$ 5.83B.
- **ALT-S4** (Y38–Y01 with passing loop) as *"Strong Contender"* with an alleged net lifecycle saving of NT$ 6.60B.

However, the empirical, deterministic capacity screening conducted in `09_preliminary_screening` established that single-track shuttle blocks under peak passenger demand fail basic capacity constraints:
- ALT-S1 (Y39–Y01) suffers a block cycle of 482.0s, supplying only 4,854.77 pphpd against an AM peak demand of 10,310 pphpd ($V/C = 2.1237 > 1.0$).
- ALT-S4 (Y38–Y01) has a cycle time of 666.2s, supplying only 3,512.46 pphpd against demand ($V/C = 3.4079 > 1.0$).
- ALT-S2 (Y35–Y36) yields $V/C = 2.2328 > 1.0$.
- ALT-S3 (Y30–Y33) yields $V/C = 1.8299 > 1.0$.

### Fail-Closed Synthesis Rule
Under project readiness governance (`READY_FOR_PRELIMINARY_SCREENING_ONLY` with 10 open blockers):
1. **Capacity Feasibility is a Non-Negotiable Prerequisite**: Infrastructure configurations that fail deterministic peak capacity ($V/C > 1.0$) under nominal operating conditions (scenario `S00`) cannot be declared optimal, strong contenders, or admissible.
2. **Override of Unverified Economic Claims**: Any previous claims of civil or lifecycle cost savings from Domain 06 for single-track candidates that fail capacity are formally overridden and rejected.
3. **Synthesis Verdict**:
   - For all single-track alternatives failing capacity under S00: `REJECTED_CAPACITY_FAILURE`.
   - Governance note: *"Single-track infrastructure is operationally non-viable under deterministic peak demand (V/C > 1.0). Unverified economic cost savings claims are formally overridden and rejected."*
   - For the approved double-track baseline (`BL-Double`): `APPROVED_BASELINE_FEASIBLE`.

---

## 2. Cross-Domain Mapping

The synthesis reconciles alternatives defined in `06_lifecycle_costs` with named screening sections in `09_preliminary_screening`:

| Alternative ID (`06`) | Candidate Ref ID | Section ID (`09`) | Section Name | Spanned Links | Original Economic Claim (`06`) |
|---|---|---|---|---|---|
| **BL-Double** | `BL-Double` | `Baseline Double-Track` | Entire East Section (Y29–Y01) | LK01–LK11 (Full Double Track) | Reference Case: Unconstrained headway (90s–180s), full degraded redundancy, approved DORTS layout |
| **ALT-S1** | `S1` | `Y39-Y01` | Mountain Tunnel Section | LK11 | Optimal Alternative: Saves NT$ 5.85B initial CAPEX... Net NPV saving NT$ 5.83B |
| **ALT-S2** | `S2` | `Y35-Y36` | Keelung River Undercrossing | LK07 | Severely Inadmissible: Saves NT$ 2.7B CAPEX, but chokes 15,640 pphpd demand corridor (+NT$ 25.3B economic loss) |
| **ALT-S3** | `S3` | `Y30-Y33` | Ruiguang Road Core Corridor | LK02;LK03;LK04 | Economically Inadmissible: Saves NT$ 4.3B street-level excavation; creates 270s bottleneck (+NT$ 14.6B delay penalty) |
| **ALT-S4** | `S4` | `Y38-Y01` | Southern Tail Extended Section | LK10;LK11 | Strong Contender: Extends single track north to Xiangshan... net lifecycle savings NT$ 6.60B |

---

## 3. Synthesis Evaluation Results

The multi-criteria synthesis evaluation is output to `outputs/synthesis_evaluation.csv`:

| Alternative ID | Candidate Ref ID | Section ID | CAPEX (NT$ B) | 30yr NPV (NT$ B) | Capacity Status (S00) | Max V/C (S00) | Synthesis Verdict | Governance Note |
|---|---|---|---|---|---|---|---|---|
| **BL-Double** | `BL-Double` | `Baseline Double-Track` | 108.50 | 138.20 | `PRELIMINARY_CAPACITY_PASS_INFRASTRUCTURE_UNVERIFIED` | 0.9776 | **`APPROVED_BASELINE_FEASIBLE`** | Baseline double-track infrastructure satisfies deterministic peak demand (max V/C <= 1.0). Retained as feasible reference design. |
| **ALT-S1** | `S1` | `Y39-Y01` | 102.65 | 131.42 | `FAIL_CAPACITY` | 2.1237 | **`REJECTED_CAPACITY_FAILURE`** | Single-track infrastructure is operationally non-viable under deterministic peak demand (V/C > 1.0). Unverified economic cost savings claims are formally overridden and rejected. |
| **ALT-S2** | `S2` | `Y35-Y36` | 105.80 | 135.10 | `FAIL_CAPACITY` | 2.2328 | **`REJECTED_CAPACITY_FAILURE`** | Single-track infrastructure is operationally non-viable under deterministic peak demand (V/C > 1.0). Unverified economic cost savings claims are formally overridden and rejected. |
| **ALT-S3** | `S3` | `Y30-Y33` | 104.20 | 133.15 | `FAIL_CAPACITY` | 1.8299 | **`REJECTED_CAPACITY_FAILURE`** | Single-track infrastructure is operationally non-viable under deterministic peak demand (V/C > 1.0). Unverified economic cost savings claims are formally overridden and rejected. |
| **ALT-S4** | `S4` | `Y38-Y01` | 100.80 | 129.20 | `FAIL_CAPACITY` | 3.4079 | **`REJECTED_CAPACITY_FAILURE`** | Single-track infrastructure is operationally non-viable under deterministic peak demand (V/C > 1.0). Unverified economic cost savings claims are formally overridden and rejected. |

### Summary Disposition
- **Total Alternatives Evaluated**: 5
- **Single-Track Alternatives Evaluated**: 4
- **Single-Track Rejected (Capacity Failure)**: 4 (100%)
- **Single-Track Approved**: 0
- **Domain 06 Economic Claims Overridden**: 2 (`ALT-S1` "Optimal Alternative", `ALT-S4` "Strong Contender")
- **Baseline Disposition**: `BL-Double` retained as sole feasible design (`APPROVED_BASELINE_FEASIBLE`).

---

## 4. Directory Layout

```
10_multi_criteria_synthesis/
├── README.md                                 # Synthesis governance, mapping, and results documentation
└── outputs/
    ├── synthesis_evaluation.csv              # Joined multi-criteria evaluation table
    └── synthesis_summary.json                # Structured summary metadata and aggregated disposition
```

---

## 5. Execution and Verification Commands

1. **Run Multi-Criteria Synthesis Engine**:
   ```bash
   python3 scripts/run_multi_criteria_synthesis.py
   ```
2. **Run Dedicated Synthesis Verifier**:
   ```bash
   python3 scripts/verify_multi_criteria_synthesis.py
   ```
3. **Run Unit Tests**:
   ```bash
   python3 -m unittest discover -s tests -v
   ```
4. **Run Full Pipeline and Gate Verification**:
   ```bash
   python3 scripts/verify_source_snapshot.py
   python3 scripts/verify_pipeline_integrity.py
   python3 scripts/verify_analysis_readiness.py
   ```
