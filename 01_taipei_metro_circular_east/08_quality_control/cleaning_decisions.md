# Dataset Cleaning Decisions & Evidence Governance

## Three-State Snapshot & Preservation Rule

The collected raw files in domains `01` through `07` are certified as a current static workspace snapshot:
- `source_snapshot_status`: **`CURRENT_WORKSPACE_SNAPSHOT_MATCHED`** (certified across exactly 36 source data files in `08_quality_control/source_file_checksums.csv` via `scripts/verify_source_snapshot.py`).
- `historical_preservation_status`: **`NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY`** (historical repository preservation prior to this snapshot cannot be established from local workspace history alone; this snapshot certifies only the current workspace state).
- **Actuator Phase Integrity**: Zero files under domains `01` through `07` have been modified, overwritten, added, or removed.

## Evidence Vocabulary

- `OBSERVED`: Directly measured operational data with a traceable physical source.
- `OFFICIAL`: Explicitly stated in an identifiable authority document (specifically DORTS 112年3月29日 Comprehensive Plan Report, 行政院院臺交字第1121008693號函核定本).
- `FORECAST`: Official authority or calibrated model forecast (TRTS-4S target year 2051).
- `DERIVED`: Calculated from explicit mathematical equations and inputs.
- `PROXY`: Borrowed or generalized parameter used pending project-specific data.
- `ASSUMED`: Research choice or counterfactual scenario parameter.
- `UNVERIFIED`: Claimed source cannot yet be located at page/table/drawing level.
- `MIXED`: File combines more than one of the above.
- `UNKNOWN`: Detailed parameter lacking value-level official citations.

## Evaluated Status of Engineering Claims & Proof Requirements

1. **Source Document Citations (F-002 OPEN / BLOCKS)**:
   - Authority citations at chapter and section level identify general planning concepts, but value-level citations for station-specific geometry (radii, cant, vertical curves), special trackwork turnout geometry, geotechnical parameters, and equipment MTBF/MTTR are lacking. Inspected per-station trackwork, curves, and grades in `08_analysis_ready/official_alignment_geometry.csv` remain `UNKNOWN`. F-002 remains OPEN and blocks formal readiness.

2. **Official Alignment Geometry (F-011 & F-013 OPEN / BLOCKS)**:
   - Approved route-wide standards are noted (minimum radius 50 m on mainline, maximum grade 5.38% in mountain section). However, station-specific curve radii, gradients, and turnout trackwork lack value-level citations and are marked `UNKNOWN` in `08_analysis_ready/official_alignment_geometry.csv`.
   - The 1.482 km discrepancy between model chainage (14.732 km) and published scope (13.250 km) is classified as an `UNRESOLVED_DISCREPANCY` (reopened from claimed scope transformation; requires supported reconciliation record). F-011 and F-013 remain OPEN.

3. **Demand Calibration & Directionality (F-003 RESOLVED - DEFENSIBLE BENCHMARK)**:
   - Calibrated link loads in `08_analysis_ready/official_link_loads.csv` based on approved Table 6.2-9.
   - Counterclockwise AM peak critical flow (Y36 to Y35) is **15,250 pphpd**.
   - Counterclockwise mountain tunnel flow (Y39 to Y01) is **10,310 pphpd**.
   - Retained as defensible official benchmarks.

4. **Approved Baseline Operating Plan (F-004 RESOLVED / F-007 OPEN)**:
   - Approved baseline CCW headway of 150 seconds (24 tph) supplying 15,600 pphpd (>= 15,250 pphpd demand) is verified from Table 8.2-2. F-004 is RESOLVED as a narrow service benchmark.
   - However, whole-ring fleet circulation (69 trainsets across Y01–Y39) and South/East depot track circulation lack whole-ring, depot throat, and block/interlocking models. F-007 remains OPEN.

5. **Train-Event Timetable (F-008 OPEN / BLOCKS)**:
   - The timetable in `08_analysis_ready/train_event_timetable_approved_baseline.csv` covers only 12 East-section stations (Y29–Y01).
   - Augmented with self-describing fields (`model_scope`, `evidence_class`, `validation_status`, `limitations`).
   - Alleged Y22–Y38 short-turn trips traverse all 12 East-section stations due to unmodeled short-turn turnbacks (explicit semantic defect).
   - It lacks whole-ring loop circulation, depot throat blocks, and interlocking conflict matrices. It cannot be called whole-ring microsimulation. F-008 remains OPEN.

6. **Life-Safety & Evacuation (F-006 OPEN / BLOCKS)**:
   - `08_analysis_ready/official_station_evacuation_nfpa130.csv` reflects official platform width and exit lane design summaries from Table 9.1-5 only.
   - A separate reproducible NFPA 130 calculation workbook package is missing. Platform clearing times, safe haven egress times, and uniform PASS determinations are unsupported derived estimates, not a reproducible dynamic compliance workbook. F-006 remains OPEN.

7. **Lifecycle Economics (F-009 & F-014 OPEN / BLOCKS)**:
   - Approved initial CAPEX budget of **NT$ 102.486 billion** (Table 12.1-2) and discount rates (3% financial, 4% economic) are retained as narrow official facts.
   - Annual OPEX, 15-year periodic renewals, 30-year salvage, and resulting 30-year NPV figures are unsubstantiated arithmetic benchmarks without a contract-audited bankable lifecycle model. F-009 and F-014 remain OPEN.

8. **railML Conformance (F-010 OPEN / BLOCKS - XML_WELL_FORMED_ONLY)**:
   - railML files satisfy XML 1.0 well-formedness. No official railML 3.2 XSD schema bundle in `schema/railML-3.2/railML.xsd`, validation execution runner, success log, or validated XML digest verification exists. Because its `blocks` field is `FORMAL_OPTIMIZATION`, F-010 blocks readiness. Classified as `XML_WELL_FORMED_ONLY`.

9. **Single-Track Screening Status (F-005 CLOSED_REJECTED - DEFENSIBLE FACT)**:
   - S1 (Y39–Y01 single bore) remains conclusively rejected under the alternating screen: 540-second directional cycle carries only ~4,333 pphpd nominal capacity vs approved 10,310 pphpd demand, with negative recovery margin (-62.0s) in the 360s plan.

10. **Growth Acceptance Target (AC-06 Downgraded)**:
    - AC-06 is downgraded from verified to `UNVERIFIED_PROXY_TARGET` because 90s / 40 tph GoA4 CBTC expansion is generic proxy data from rolling_stock_signalling, not an operator-committed infrastructure guarantee.

## Decision Boundary & Readiness Gate

The repository is restored to **`READY_FOR_PRELIMINARY_SCREENING_ONLY`**.
Readiness blocking evaluates all open requirements where `blocks != "NONE"`, regardless of severity.
Formal optimization, whole-ring microsimulation, and bankable economic or safety conclusions remain blocked by **10 open blocking requirements** (`F-001`, `F-002`, `F-006`, `F-007`, `F-008`, `F-009`, `F-010`, `F-011`, `F-013`, `F-014`).

- **Canonical Artifact**: `08_quality_control/model_readiness.json` is the canonical machine-readable readiness evaluation record.
- **Truthful Markdown Mirror**: `08_quality_control/model_readiness.md` is generated by `scripts/audit_and_prepare.py` as a synchronized human-readable mirror.

## 11. East-Section Preliminary Capacity Screening Decisions (09_preliminary_screening)

1. **Spatial and System Boundaries**:
   - Explicitly bounded to corridor nodes `Y29`, `Y30`, `Y31`, `Y32`, `Y33`, `Y34`, `Y35`, `Y36`, `Y37`, `Y38`, `Y39`, `Y01` (12 stations, 11 links) during AM peak 07:00–09:00 (TB02).
   - Boundary condition: Boundary trains enter at Y29/Y01 and disappear at the opposite boundary terminus. External network propagation is explicitly classified as `NOT_MODELED`.
   - Passing loops: Evaluated strictly as contiguous shuttle blocks without dynamic passing sidings (`NOT_MODELED`).
   - Exclusions: Whole-ring circulation, fleet/depot sizing, passing loops, block-level microsimulation, life safety certification, economics, optimization, and RL remain strictly excluded and unverified.

2. **Directional Flow Correction**:
   - Official link profiles store segments running clockwise (CW) from `from_station` to `to_station`.
   - For counterclockwise (CCW) movements, actual travel is reversed (`to_station` to `from_station`).
   - LK07 CCW is correctly mapped to movement `Y36 -> Y35` carrying critical demand 15,250 pphpd.

3. **Both-Directions Pass Rule & Governance Outcomes**:
   - Contiguous single-track sections require both CW and CCW directions to satisfy $V/C \le 1.00$ ($\max(V/C_{cw}, V/C_{ccw}) \le 1.00$).
   - Any passing outcome is strictly labeled `PRELIMINARY_CAPACITY_PASS_INFRASTRUCTURE_UNVERIFIED` to prevent premature civil or operational promotion.
   - Any failing outcome is labeled `FAIL_CAPACITY`.
   - S00 regression benchmark confirms Y39–Y01 cycle time of 482.0s (193+193+36+60s), capacity of 4,854.77 pphpd, critical CCW demand of 10,310 pphpd, and resulting `FAIL_CAPACITY`.

4. **Scenario Sensitivities**:
   - Scenarios S00 through S06 test parametric sensitivities (demand, usable load factor, runtime, dwell, switch change, recovery).
   - Non-official values are labeled `ASSUMED_SCREENING_SENSITIVITY` or `PROXY_SCREENING_ASSUMPTION`.
   - Governance rule: Sensitivities are exploratory parametric screens and not probabilities.

## 12. Multi-Criteria Synthesis Decisions (10_multi_criteria_synthesis)

1. **Reconciliation of Empirical Capacity Failures with Unverified Economic Claims**:
   - Earlier research in Domain `06_lifecycle_costs` (`lifecycle_cost_comparison_30yr.csv`) claimed economic advantages for single-track configurations, designating `ALT-S1` as "Optimal Alternative" (alleged NT$ 5.85B CAPEX savings, NT$ 5.83B net NPV savings) and `ALT-S4` as "Strong Contender" (alleged NT$ 6.60B net NPV savings).
   - Empirical deterministic capacity screening under nominal peak demand (`S00`) in `09_preliminary_screening` proved all four single-track candidate sections operationally non-viable with $V/C > 1.0$:
     * `ALT-S1` (Y39–Y01): $V/C = 2.1237$ (`FAIL_CAPACITY`)
     * `ALT-S2` (Y35–Y36): $V/C = 2.2328$ (`FAIL_CAPACITY`)
     * `ALT-S3` (Y30–Y33): $V/C = 1.8299$ (`FAIL_CAPACITY`)
     * `ALT-S4` (Y38–Y01): $V/C = 3.4079$ (`FAIL_CAPACITY`)

2. **Hierarchical Governance Override**:
   - Operational viability is a strict prerequisite for economic admissibility. Infrastructure that cannot transport peak passenger demand ($V/C > 1.0$) cannot be recommended, optimized, or declared advantageous.
   - For all single-track alternatives failing capacity under S00, previous claims of optimality or strong candidacy are formally overridden.
   - Assigned `synthesis_verdict`: **`REJECTED_CAPACITY_FAILURE`**.
   - Mandatory governance note: *"Single-track infrastructure is operationally non-viable under deterministic peak demand (V/C > 1.0). Unverified economic cost savings claims are formally overridden and rejected."*

3. **Baseline Double-Track Disposition**:
   - The approved double-track baseline (`BL-Double`) satisfies deterministic peak capacity under S00 (maximum $V/C = 0.9776 \le 1.0$).
   - Assigned `synthesis_verdict`: **`APPROVED_BASELINE_FEASIBLE`**.
   - Governance note: *"Baseline double-track infrastructure satisfies deterministic peak demand (max V/C <= 1.0). Retained as feasible reference design."*

4. **Cross-Domain Mapping Rule**:
   - `06_lifecycle_costs` `alternative_id` values map deterministically to `09_preliminary_screening` named alternatives via `candidate_reference_id`:
     * `ALT-S1` $\to$ `S1` $\to$ `Y39-Y01`
     * `ALT-S2` $\to$ `S2` $\to$ `Y35-Y36`
     * `ALT-S3` $\to$ `S3` $\to$ `Y30-Y33`
     * `ALT-S4` $\to$ `S4` $\to$ `Y38-Y01`
     * `BL-Double` $\to$ `BL-Double` $\to$ `Baseline Double-Track`

5. **Preservation of Readiness Gate**:
   - Multi-criteria synthesis does not resolve the 10 fail-closed readiness blockers (`F-001`, `F-002`, `F-006`, `F-007`, `F-008`, `F-009`, `F-010`, `F-011`, `F-013`, `F-014`).
   - The repository remains strictly at **`READY_FOR_PRELIMINARY_SCREENING_ONLY`**.

## 13. Final Technical Disposition & Evaluation Closeout

1. **Formal Closure of Counterfactual Study**:
   - As documented in `00_executive_summary/final_technical_disposition.md`, the counterfactual hypothesis is formally concluded.
   - Core single-track tunnel alternatives are mathematically and operationally non-viable in high-frequency automated urban metro systems carrying >10,000 pphpd.
   - The DORTS approved continuous twin-bore double-track design is affirmed as the sole feasible infrastructure strategy.
   - All 36 raw source files remain preserved byte-identical; test suite stands at 43 passing tests.



