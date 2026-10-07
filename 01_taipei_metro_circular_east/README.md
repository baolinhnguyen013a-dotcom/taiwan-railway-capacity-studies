# Taipei Metro Circular Line East Section Counterfactual Optimization Study

> **Data maturity (updated 2026-10-06): preliminary screening only.**
> Authoritative engineering benchmarks from the DORTS Comprehensive Plan
> (112年3月核定本) establish narrow defensible facts: demand benchmarks (15,250 pphpd peak link load),
> baseline service capacity (150s headway supplying 15,600 pphpd), S1 alternating single-track rejection,
> approved construction CAPEX (NT$ 102.486B), and appraisal discount rates (3% financial, 4% economic).
> All 36 raw source inputs remain strictly preserved under a certified snapshot:
> `source_snapshot_status: CURRENT_WORKSPACE_SNAPSHOT_MATCHED` and
> `historical_preservation_status: NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY`
> (`08_quality_control/source_file_checksums.csv`).
> The independent, fail-closed readiness gate reports 10 open blocking requirements
> (`READY_FOR_PRELIMINARY_SCREENING_ONLY`). Formal optimization, whole-ring microsimulation,
> and bankable economic or safety conclusions remain blocked.

The East Section is not operational, but it is no longer merely a designed
line: the CF763 mountain-tunnel contract began construction on 24 December
2024. The study is therefore a counterfactual research exercise against the
approved twin-bore design, not a live design recommendation. Official status:
https://www.dorts.gov.taipei/cp.aspx?n=F47E41B6C8884DC6&s=9523DB9FBC46B35B

## Research Overview & Core Hypothesis
This repository contains a structured preliminary dataset for evaluating whether targeted sections of the **Taipei Metro Circular Line East Section (環狀線東環段 Y30–Y39 connecting Y29 to Y01)** could operate with a single bidirectional track while preserving acceptable capacity, safety, reliability, and expandability compared with an equally optimized double-track baseline.

The hypothesis is intentionally open: targeted single-track construction may
reduce civil cost, but it is admissible only if it satisfies fixed safety,
capacity, reliability, and growth requirements against an equally optimized
double-track comparator. The official approved plan reports 15,250 pphpd on
Y36-Y35 and 10,310 pphpd on Y39-Y01; those values replace the untraced 15,640
and 3,210 pphpd values in the collected screening narrative.

---

## Repository Structure & Data Domains

```
taipei_circular_east_counterfactual/
├── README.md                                    # This project blueprint & research specification
├── METADATA_REGISTRY.json                      # Master metadata registry (sources, dates, CRS, accuracy, licenses)
├── provenance.csv                              # Tabular provenance register for automated verification
├── 00_executive_summary/
│   ├── research_hypothesis_and_framework.md   # Counterfactual design space, optimization formulations, trade-off frontier
│   └── final_technical_disposition.md         # Final engineering conclusion, capacity failure review & disposition
├── 01_alignment_topology/                      # 7 preserved source files: stations, curves, grades, trackwork, geojson, railML
├── 02_tunnel_civil/                            # 5 preserved source files: bore specs, shafts/passages, strata, spatial constraints, IFC
├── 03_rolling_stock_signalling/                # 5 preserved source files: specs, tractive curves, CBTC, degraded rules, railML
├── 04_service_operations/                      # 5 preserved source files: timetables (baseline, S1, S3), dwells, maintenance
├── 05_demand_ridership/                        # 5 preserved source files: OD matrices (AM, PM, off-peak), link profiles, growth
├── 06_lifecycle_costs/                         # 4 preserved source files: unit costs, 30yr LCC, crossover capex, conversion penalties
├── 07_risk_safety_regulations/                 # 5 preserved source files: NFPA 130, ventilation, MTBF, delay distributions, hazards
├── 08_analysis_ready/                          # Verified benchmarks, S1 screening, and preliminary analysis datasets
├── 08_quality_control/                         # Data catalog, checksums, canonical model_readiness.json & mirror model_readiness.md
├── 09_preliminary_screening/                   # East-Section deterministic capacity screening engine inputs & outputs
│   ├── README.md                               # Screening engine specifications, formulations, and governance rules
│   ├── inputs/                                 # Boundary conditions, screening scenarios (S00-S06), named alternatives
│   └── outputs/                                # Link/section capacity screens, representative occupations, JSON summary
├── 10_multi_criteria_synthesis/                 # Multi-criteria synthesis & reconciliation engine outputs
│   ├── README.md                               # Synthesis methodology, mapping rules, and override governance
│   └── outputs/                                # Synthesis evaluation CSV and structured summary JSON
├── schema/                                     # Data dictionary, railML notes, IFC4.3 mapping guide
├── scripts/
│   ├── audit_and_prepare.py                    # Independent predicate-based analysis-ready layer generator
│   ├── evidence_predicates.py                  # Proof-oriented executable evidence requirement predicate definitions
│   ├── run_east_section_screening.py           # East-section deterministic preliminary capacity screening engine
│   ├── verify_east_section_screening.py        # Screening verifier (benchmarks, monotonicity, non-overlap, rerun)
│   ├── run_multi_criteria_synthesis.py         # Phase 10 multi-criteria synthesis generator
│   ├── verify_multi_criteria_synthesis.py      # Phase 10 multi-criteria synthesis verifier
│   ├── verify_pipeline_integrity.py            # Automated structural & physical plausibility checks (disclaims readiness)
│   ├── verify_source_snapshot.py               # SHA-256 snapshot verification for exactly 36 source data files
│   ├── verify_analysis_readiness.py            # Fail-closed gate evaluation (exits nonzero on open blocking requirements)
│   ├── generate_baseline_event_timetable.py    # Self-describing 12-station headway schedule generator
│   └── generate_s1_portal_schedule.py          # S1 portal section movement screening
└── tests/
    ├── test_analysis_readiness.py              # Test suite with adversarial cases (overrides, inconsistency, semantics, checksum drift)
    ├── test_east_section_screening.py          # Unit tests for preliminary capacity screening engine and boundaries
    └── test_multi_criteria_synthesis.py        # Unit tests for multi-criteria synthesis and override logic
```

---

## Verification Engine & Execution Commands

1. **Source Data File Snapshot Verification**:
   ```bash
   python3 scripts/verify_source_snapshot.py
   ```
   Certifies that exactly 36 source data files exist in `01` through `07` matching recorded SHA-256 digests in `08_quality_control/source_file_checksums.csv`. Reports `CURRENT_WORKSPACE_SNAPSHOT` and disclaims historical preservation prior to the snapshot (`NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY`).

2. **Structural Pipeline Integrity Verification**:
   ```bash
   python3 scripts/verify_pipeline_integrity.py
   ```
   Runs 48 automated checks confirming CSV formatting, non-empty records, GeoJSON RFC 7946 validity, railML well-formedness, kinematic stopping distances, and topological continuity. Explicitly disclaims analysis readiness.

3. **Analysis Readiness Gate Verification**:
   ```bash
   python3 scripts/verify_analysis_readiness.py
   ```
   Executes independent, fail-closed predicate evaluation against canonical `08_quality_control/model_readiness.json` (truthfully mirrored in `08_quality_control/model_readiness.md`). Reports `READY_FOR_PRELIMINARY_SCREENING_ONLY` and exits nonzero (code 1) due to 10 open blocking requirements (including medium F-010).

4. **Audit & Analysis-Ready Layer Generation**:
   ```bash
   python3 scripts/audit_and_prepare.py
   ```
   Re-indexes source files, populates traceable citations, evaluates predicates, and updates quality control and analysis-ready outputs without bypassing open findings. Cannot restore formal readiness.

5. **East-Section Preliminary Capacity Screening**:
   ```bash
   python3 scripts/run_east_section_screening.py
   ```
   Executes deterministic capacity screening across double-track baseline links and all 66 contiguous no-loop intervals under scenarios S00–S06. Outputs results to `09_preliminary_screening/outputs/`.

6. **Screening Engine Verification**:
   ```bash
   python3 scripts/verify_east_section_screening.py
   ```
   Verifies boundary set, baseline TB02 capacities, direction correction, Y39-Y01 regression failure, both-direction pass rules, parameter monotonicity, non-overlapping occupations, byte-identical rerun, and data catalog preservation.

7. **Test Suite Execution**:
   ```bash
   python3 -m unittest discover -s tests -v
   ```
   Executes unit tests covering adversarial cases: declared RESOLVED overrides, metadata inconsistency, timetable semantics, missing XSD schemas, label deletion resistance, source checksum drift, screening engine verification tests, and Phase 10 multi-criteria synthesis override tests.

8. **Multi-Criteria Synthesis Generation (Phase 10)**:
   ```bash
   python3 scripts/run_multi_criteria_synthesis.py
   ```
   Reconciles empirical single-track capacity failures (Phase 9) with unverified lifecycle cost claims (Phase 6), formally overriding 'Optimal Alternative' (ALT-S1) and 'Strong Contender' (ALT-S4) with `REJECTED_CAPACITY_FAILURE`. Outputs to `10_multi_criteria_synthesis/outputs/`.

9. **Multi-Criteria Synthesis Verification**:
   ```bash
   python3 scripts/verify_multi_criteria_synthesis.py
   ```
   Verifies cross-domain mapping, CSV schema, financial and capacity metrics, synthesis verdicts, governance note compliance, JSON summary, deterministic rerun reproducibility, and invariant preservation.

---

## Evaluated Status of Engineering Findings (10 Blockers)

- **F-001 (Data Catalog Completeness)**: `OPEN` (HIGH - BLOCKS). Data catalog inventories source files, but retains 4 BLOCKED and 2 REJECTED_AS_WRITTEN source inputs lacking traceable replacements.
- **F-002 (Engineering Traceability)**: `OPEN` (CRITICAL - BLOCKS). Chapter-level plan references exist, but value-level citations for station-specific geometry, crossovers, and risk parameters remain missing.
- **F-003 (Demand Calibration)**: `RESOLVED` (HIGH - DEFENSIBLE BENCHMARK). Calibrated against Table 6.2-9 (link loads) and Table 6.2-8 in `08_analysis_ready/official_link_loads.csv`. Peak CCW load Y36→Y35 is verified at 15,250 pphpd; mountain link Y39→Y01 at 10,310 pphpd.
- **F-004 (Baseline Service Timetable)**: `RESOLVED` (CRITICAL - DEFENSIBLE BENCHMARK). Baseline operating plan (`08_analysis_ready/official_operational_service_baseline.csv`) provides 150s (24 tph) CCW headway supplying 15,600 pphpd, covering the 15,250 pphpd demand.
- **F-005 (S1 Single-Track Screen)**: `CLOSED_REJECTED` (CRITICAL - DEFENSIBLE FACT). S1 alternating single bore is conclusively rejected due to negative recovery margin (-62.0s) and carrying only ~4,333 pphpd vs 10,310 pphpd required flow.
- **F-006 (NFPA 130 Station Safety)**: `OPEN` (CRITICAL - BLOCKS). Station evacuation table (`08_analysis_ready/official_station_evacuation_nfpa130.csv`) reflects Table 9.1-5 width/lane design summaries only; platform clearance times and PASS determinations are unsupported derived values lacking a reproducible calculation workbook package.
- **F-007 (Whole-Ring Fleet & Depots)**: `OPEN` (HIGH - BLOCKS). Timetable covers only 12 East-section stations; lacks whole-ring loop circulation (Y01–Y39), depot throat tracks, and network turnaround models.
- **F-008 (Microscopic Train Events)**: `OPEN` (HIGH - BLOCKS). Indicative 12-station timetable lacks block signals and interlocking conflict models; short turns Y22-Y38 traverse all 12 stations. Not whole-ring microsimulation.
- **F-009 & F-014 (Lifecycle Economics)**: `OPEN` (HIGH - BLOCKS). Approved CAPEX budget of NT$ 102.486 billion and discount rates (3% financial, 4% economic) are verified as narrow facts; annual OPEX, 15-year renewals, salvage, and 30-year NPV are unsubstantiated arithmetic benchmarks lacking an audited bankable model.
- **F-010 (railML Schema Conformance)**: `OPEN` (MEDIUM - BLOCKS). railML files satisfy XML 1.0 well-formedness only (`XML_WELL_FORMED_ONLY`); lacks official railML 3.2 XSD schema bundle, validator run, success log, and matching XML digests. Blocks formal readiness.
- **F-011 (Chainage Scope Transformation)**: `OPEN` (HIGH - BLOCKS). 1.482 km discrepancy between model chainage (14.732 km) and published route length (13.250 km) is an unresolved discrepancy lacking a supported reconciliation record artifact.
- **F-012 (CF763 Construction Start)**: `CLOSED` (MEDIUM - DEFENSIBLE FACT). CF763 mountain tunnel began construction on 2024-12-24, verified from official DORTS contract overview.
- **F-013 (Alignment Geometry & Standards)**: `OPEN` (CRITICAL - BLOCKS). Route standards (min R=50m, max grade 5.38%) are documented, but station-specific curve radii, gradients, and trackwork lack drawing-level citations and are marked `UNKNOWN`.

---

## Multi-Criteria Synthesis Findings (Phase 10)

Phase 10 reconciles empirical preliminary capacity screening results (`09_preliminary_screening`) with unverified lifecycle cost claims (`06_lifecycle_costs`):
- **Single-Track Alternatives Rejection**: All four single-track candidate sections (`ALT-S1`, `ALT-S2`, `ALT-S3`, `ALT-S4`) fail deterministic capacity screening under peak demand ($V/C > 1.0$) and are assigned `synthesis_verdict: REJECTED_CAPACITY_FAILURE`.
- **Formal Override of Economic Claims**: Previous claims of civil savings or lifecycle optimality from Domain 06—specifically `ALT-S1` ("Optimal Alternative: Saves NT$ 5.85B... Net NPV saving NT$ 5.83B") and `ALT-S4` ("Strong Contender... net lifecycle savings NT$ 6.60B")—are formally overridden and rejected as operationally non-viable.
- **Baseline Retained**: The approved double-track baseline (`BL-Double`) satisfies peak capacity requirements ($V/C = 0.9776 \le 1.0$) and is confirmed as `APPROVED_BASELINE_FEASIBLE`.
- **Readiness Invariant Preserved**: The repository remains strictly at `READY_FOR_PRELIMINARY_SCREENING_ONLY` with 10 open blocking requirements.
