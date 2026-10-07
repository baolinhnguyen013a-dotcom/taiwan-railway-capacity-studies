# Model Readiness Evaluation & Evidence Status Mirror

> **Notice**: `08_quality_control/model_readiness.json` is the canonical machine-readable readiness artifact.
> This document is an automatically generated human-readable mirror.

## Overall Status Summary

- **Overall Readiness State**: `READY_FOR_PRELIMINARY_SCREENING_ONLY`
- **Source Snapshot Status**: `CURRENT_WORKSPACE_SNAPSHOT_MATCHED`
- **Historical Preservation Status**: `NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY`
- **Certified Source Data File Count**: `36`
- **Open Blocking Requirements Count**: `10`

## Open Blocking Requirements (Blocks Formal Optimization)

| Finding ID | Severity | Blocks | Predicate ID | Reason |
|---|---|---|---|---|
| **F-001** | HIGH | `FORMAL_OPTIMIZATION` | `PRED-CATALOG-NO-BLOCKED` | Catalog retains 4 BLOCKED and 2 REJECTED_AS_WRITTEN source inputs. |
| **F-002** | CRITICAL | `FORMAL_OPTIMIZATION` | `PRED-TRACEABILITY-VALUE-LEVEL` | Detailed station curve radii, vertical gradients, and crossover trackwork exceed value-level official support (12 stations unsupported: Y29 (detailed values UNKNOWN), Y30 (detailed values UNKNOWN), Y31 (detailed values UNKNOWN), Y32 (detailed values UNKNOWN)...). |
| **F-006** | CRITICAL | `FORMAL_OPTIMIZATION` | `PRED-SAFETY-EVACUATION-WORKBOOK` | Missing reproducible NFPA 130 evacuation workbook evidence package; official data is a station width/lane design summary (Table 9.1-5) only. Derived egress times and PASS determinations are unsupported. |
| **F-007** | HIGH | `FORMAL_OPTIMIZATION` | `PRED-WHOLE-RING-FLEET-CIRCULATION` | Event timetable covers only 12 stations (East-section Y29-Y01); lacks whole-ring coverage (27 stations missing), fleet continuity, and depot throat models. |
| **F-008** | HIGH | `FORMAL_OPTIMIZATION` | `PRED-MICROSIMULATION-TIMETABLE` | Timetable semantic error: short-turn Y22-Y38 trips incorrectly traverse non-turnback stations (Y01, Y29, Y39); lacks block-level signaling and interlocking models. |
| **F-009** | HIGH | `FORMAL_OPTIMIZATION` | `PRED-LIFECYCLE-BANKABLE-NPV` | Annual OPEX, 15-year renewal, 30-year salvage, and 30-year NPV are unsubstantiated arithmetic benchmarks; lacks a contract-audited bankable lifecycle evidence package. |
| **F-010** | MEDIUM | `FORMAL_OPTIMIZATION` | `PRED-RAILML-SCHEMA-XSD` | Missing official railML 3.2 XSD schema bundle in schema/railML-3.2/railML.xsd. |
| **F-011** | HIGH | `FORMAL_OPTIMIZATION` | `PRED-CHAINAGE-SCOPE-TRANSFORMATION` | 1.482 km route length discrepancy between model chainage (14.732 km) and published scope (13.250 km) is unresolved (status: UNRESOLVED_DISCREPANCY). |
| **F-013** | CRITICAL | `FORMAL_OPTIMIZATION` | `PRED-ALIGNMENT-GEOMETRY-STANDARDS` | Station-specific curve radii, vertical gradients, and trackwork lack drawing-level citations (12 stations marked UNKNOWN). |
| **F-014** | HIGH | `FORMAL_OPTIMIZATION` | `PRED-CAPEX-DISCOUNT-RATES` | Only initial CAPEX budget and appraisal discount rates are verified; 30-year lifecycle NPV is unsubstantiated and non-bankable. |

## Defensible Benchmarks & Closed Findings

| Finding ID | Severity | Status | Predicate ID | Benchmark Summary |
|---|---|---|---|---|
| **F-003** | HIGH | `RESOLVED` | `PRED-DEMAND-CALIBRATION` | Demand calibrated against official Table 6.2-9 and Table 6.2-8 in 08_analysis_ready/official_link_loads.csv. |
| **F-004** | CRITICAL | `RESOLVED` | `PRED-SERVICE-BASELINE` | Official baseline operational service benchmark established in 08_analysis_ready/official_operational_service_baseline.csv (150s CCW supplying 15,600 pphpd). |
| **F-005** | CRITICAL | `CLOSED_REJECTED` | `PRED-S1-SCREEN-REJECTION` | S1 is rejected under alternating screen: 360-second plan has negative recovery margin (-62.0s), and screened patterns fail target 10,310 pphpd demand. |
| **F-012** | MEDIUM | `CLOSED` | `PRED-CF763-CONSTRUCTION-START` | CF763 construction start date (2024-12-24) verified from official contract notice. |

## Supported Next Steps & Residual Limitations

Dataset is restricted to preliminary screening only. Blocking findings remain open regarding value-level engineering traceability, evacuation workbook reproducibility, whole-ring operations, microscopic simulation, non-bankable lifecycle NPV, railML XSD validation, and station-specific geometry. Only official demand benchmarks, service headway capacity benchmarks, S1 screening rejection, and construction CAPEX/discount rates are defensible.

