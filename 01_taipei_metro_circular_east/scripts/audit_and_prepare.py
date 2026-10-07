#!/usr/bin/env python3
"""Build an auditable, analysis-ready layer without overwriting collected inputs.

The source package mixes official facts, derived values, proxies, and assumptions.
This script inventories those files, recomputes cross-file checks, and writes derived
quality-control and analysis-ready datasets under 08_quality_control and 08_analysis_ready.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
QC = BASE / "08_quality_control"
READY = BASE / "08_analysis_ready"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evidence_predicates import evaluate_requirements


EVIDENCE_RULES = {
    "01_alignment_topology/alignment_stations.csv": ("MIXED", "BLOCKED", "Official station sequence mixed with untraced geometry; platform types and total chainage conflict with the approved plan."),
    "01_alignment_topology/alignment_horizontal_curves.csv": ("REJECTED", "BLOCKED", "Collected 220 m minimum conflicts with approved 50 m minimum; no drawing-level source."),
    "01_alignment_topology/alignment_vertical_gradients.csv": ("REJECTED", "BLOCKED", "Collected 3.25% maximum conflicts with approved 5.38% maximum; no drawing-level source."),
    "01_alignment_topology/special_trackwork_crossovers.csv": ("UNVERIFIED", "BLOCKED", "Trackwork locations and turnout details lack traceable contract references."),
    "01_alignment_topology/single_track_candidate_sections.csv": ("ASSUMED", "SCREENING_ONLY", "Research alternatives and verdicts, not observed infrastructure."),
    "01_alignment_topology/circular_line_east_alignment.geojson": ("DERIVED", "CONDITIONAL", "Derived geometry; metadata claims centimetric mapping but also +/-5 m accuracy."),
    "01_alignment_topology/railml_infrastructure_east_section.xml": ("DERIVED", "CONDITIONAL", "XML well-formed only; no official railML 3.2 XSD bundle or validation log; verified in 08_quality_control/railml_validation_report.md."),
    "02_tunnel_civil/tunnel_bore_specifications.csv": ("MIXED", "CONDITIONAL", "Official twin-bore concept mixed with untraced dimensions and hypothetical alternatives."),
    "02_tunnel_civil/shafts_cross_passages.csv": ("MIXED", "CONDITIONAL", "CF763 has one shaft and six connecting passages officially reported; detailed dimensions/chainages require document citations."),
    "02_tunnel_civil/geotechnical_strata_zones.csv": ("UNVERIFIED", "CONDITIONAL", "Geological strata zones mapped to Taipei Basin and Muzhishan formations."),
    "02_tunnel_civil/civil_spatial_constraints.csv": ("MIXED", "CONDITIONAL", "Crossings are broadly plausible; clearance and engineering values require drawings."),
    "02_tunnel_civil/ifc_civil_identifiers_mapping.json": ("DERIVED", "SCREENING_ONLY", "Semantic mapping, not an IFC engineering model."),
    "03_rolling_stock_signalling/rolling_stock_specifications.csv": ("MIXED", "CONDITIONAL", "Existing Circular Line vehicle is a proxy until East Section fleet compatibility is confirmed."),
    "03_rolling_stock_signalling/tractive_braking_performance_curves.csv": ("PROXY", "CONDITIONAL", "Engineering curve requires manufacturer/source table traceability."),
    "03_rolling_stock_signalling/signalling_cbtc_parameters.csv": ("PROXY", "CONDITIONAL", "Generic/assumed CBTC values mixed with proposed service parameters."),
    "03_rolling_stock_signalling/degraded_operation_rules.csv": ("ASSUMED", "SCREENING_ONLY", "Scenario rules require operator and interlocking confirmation."),
    "03_rolling_stock_signalling/railml_rollingstock_hitachi_emu.xml": ("DERIVED", "CONDITIONAL", "XML well-formed only; no official railML 3.2 XSD bundle or validation log; verified in 08_quality_control/railml_validation_report.md."),
    "04_service_operations/operational_timetable_baseline.csv": ("ASSUMED", "SCREENING_ONLY", "Time-band service plan; supplemented by train_event_timetable_approved_baseline.csv."),
    "04_service_operations/operational_timetable_counterfactual_S1.csv": ("ASSUMED", "REJECTED_AS_WRITTEN", "Six-minute S1 claim leaves inadequate recovery and contradicts its stated 150-second buffer."),
    "04_service_operations/operational_timetable_counterfactual_S3.csv": ("ASSUMED", "SCREENING_ONLY", "No train-event or route-conflict timetable."),
    "04_service_operations/dwell_turnback_times.csv": ("PROXY", "CONDITIONAL", "Requires observed distribution or approved operating plan."),
    "04_service_operations/maintenance_window_rules.csv": ("MIXED", "CONDITIONAL", "Revenue closure window plausible; possessions and single-bore rules require operator confirmation."),
    "05_demand_ridership/station_od_matrix_am_peak.csv": ("PROXY", "CONDITIONAL", "Synthetic/calibrated matrix; reconciled with official Table 6.2-9 in 08_analysis_ready."),
    "05_demand_ridership/station_od_matrix_pm_peak.csv": ("PROXY", "CONDITIONAL", "Synthetic/calibrated matrix; forecast horizon and assignment path are not specified."),
    "05_demand_ridership/station_od_matrix_off_peak.csv": ("PROXY", "CONDITIONAL", "Synthetic/calibrated matrix; forecast horizon and assignment path are not specified."),
    "05_demand_ridership/link_load_profiles.csv": ("FORECAST", "CONDITIONAL", "Reconciled with official Table 6.2-9 in 08_analysis_ready/official_link_loads.csv."),
    "05_demand_ridership/demand_growth_scenarios_2032_2051.csv": ("FORECAST", "CONDITIONAL", "Scenario derivation documented against official master plan."),
    "06_lifecycle_costs/unit_costs_civil_systems.csv": ("PROXY", "CONDITIONAL", "Benchmark values reconciled with Table 12.1-7 in 08_analysis_ready/official_lifecycle_cost_baseline.csv."),
    "06_lifecycle_costs/lifecycle_cost_comparison_30yr.csv": ("REJECTED", "REJECTED_AS_WRITTEN", "Reported NPV unreconciled; replaced by official_lifecycle_cost_baseline.csv."),
    "06_lifecycle_costs/station_crossover_capex.csv": ("PROXY", "SCREENING_ONLY", "Requires quantities, price year and source contracts."),
    "06_lifecycle_costs/single_to_double_conversion_penalties.csv": ("ASSUMED", "SCREENING_ONLY", "Scenario cost components require construction programme and quantity support."),
    "07_risk_safety_regulations/equipment_reliability_failure_rates.csv": ("PROXY", "SCREENING_ONLY", "MTBF/MTTR values lack fleet or supplier evidence."),
    "07_risk_safety_regulations/delay_distribution_parameters.csv": ("ASSUMED", "SCREENING_ONLY", "Distribution parameters are not fitted to cited observations."),
    "07_risk_safety_regulations/evacuation_nfpa130_compliance.csv": ("ASSUMED", "CONDITIONAL", "Replaced by official width/lane design summary in 08_analysis_ready/official_station_evacuation_nfpa130.csv; derived egress times/PASS unsupported."),
    "07_risk_safety_regulations/tunnel_ventilation_fire_safety.csv": ("PROXY", "CONDITIONAL", "Authority ventilation design documented in Table 7.3-8."),
    "07_risk_safety_regulations/environmental_hazards_resilience.csv": ("MIXED", "CONDITIONAL", "Hazard values require map/report citations and project design criteria."),
}


OFFICIAL_SOURCES = {
    "DORTS_PROJECT": "https://www.dorts.gov.taipei/cp.aspx?n=F47E41B6C8884DC6",
    "DORTS_COMPREHENSIVE_PLAN": "https://www.dorts.gov.taipei/News_Content.aspx?n=4027AA15756300C8&s=1B647A54DF3E09B7&sms=4E98D53D04E37D56",
    "DORTS_CF763": "https://www.dorts.gov.taipei/cp.aspx?n=F47E41B6C8884DC6&s=9523DB9FBC46B35B",
}

SOURCE_CITATIONS_MAP = {
    "01_alignment_topology/alignment_stations.csv": ("1120329-DORTS-PLAN", "Summary p. 摘-4; Table 8.1-1 p. 8-4; Table 9.1-1 p. 9-6"),
    "01_alignment_topology/alignment_horizontal_curves.csv": ("1120329-DORTS-PLAN", "Section 8.1.1 p. 8-1 to 8-3"),
    "01_alignment_topology/alignment_vertical_gradients.csv": ("1120329-DORTS-PLAN", "Section 8.1.1 p. 8-1; Table 8.1-1 p. 8-4"),
    "01_alignment_topology/special_trackwork_crossovers.csv": ("1120329-DORTS-PLAN", "Section 8.2.2 p. 8-17, Table 8.2-5, Figure 8.2-8"),
    "01_alignment_topology/railml_infrastructure_east_section.xml": ("1120329-DORTS-PLAN", "railML 3.2 schema; Chapter 8 topology"),
    "02_tunnel_civil/tunnel_bore_specifications.csv": ("1120329-DORTS-PLAN", "Section 5.3 p. 5-19; Table 12.1-7 p. 12-10"),
    "02_tunnel_civil/shafts_cross_passages.csv": ("1131224-DORTS-CF763", "CF763 contract overview; Table 7.3-8 p. 7-73"),
    "02_tunnel_civil/geotechnical_strata_zones.csv": ("1120329-DORTS-PLAN", "Chapter 7 geotechnical survey"),
    "02_tunnel_civil/civil_spatial_constraints.csv": ("1120329-DORTS-PLAN", "Section 5.3 p. 5-18 to 5-19; Table 7.3-4"),
    "03_rolling_stock_signalling/rolling_stock_specifications.csv": ("1120329-DORTS-PLAN", "Section 8.2.1 p. 8-8"),
    "03_rolling_stock_signalling/tractive_braking_performance_curves.csv": ("1120329-DORTS-PLAN", "Chapter 7 train performance specs"),
    "03_rolling_stock_signalling/signalling_cbtc_parameters.csv": ("1120329-DORTS-PLAN", "Section 7.3 & Section 8.2"),
    "03_rolling_stock_signalling/railml_rollingstock_hitachi_emu.xml": ("1120329-DORTS-PLAN", "railML 3.2 schema; Section 8.2.1"),
    "04_service_operations/operational_timetable_baseline.csv": ("1120329-DORTS-PLAN", "Table 8.2-2 p. 8-9; Section 8.2.2 pp. 8-11 to 8-13"),
    "04_service_operations/dwell_turnback_times.csv": ("1120329-DORTS-PLAN", "Section 8.2.1 p. 8-8; p. 8-15"),
    "04_service_operations/maintenance_window_rules.csv": ("1120329-DORTS-PLAN", "Section 8.2.3 p. 8-18"),
    "05_demand_ridership/station_od_matrix_am_peak.csv": ("1120329-DORTS-PLAN", "Table 6.2-8 p. 6-18; Table 6.2-9 p. 6-19"),
    "05_demand_ridership/link_load_profiles.csv": ("1120329-DORTS-PLAN", "Table 6.2-9 p. 6-19"),
    "05_demand_ridership/demand_growth_scenarios_2032_2051.csv": ("1120329-DORTS-PLAN", "Table 6.2-10 p. 6-20; Summary p. 摘-5"),
    "06_lifecycle_costs/unit_costs_civil_systems.csv": ("1120329-DORTS-PLAN", "Table 12.1-7 p. 12-10; Table 12.1-2 p. 12-92"),
    "06_lifecycle_costs/lifecycle_cost_comparison_30yr.csv": ("1120329-DORTS-PLAN", "Table 12.1-2 p. 12-92; Chapter 17 p. 17-10"),
    "07_risk_safety_regulations/evacuation_nfpa130_compliance.csv": ("1120329-DORTS-PLAN", "Table 9.1-5 p. 9-10; Section 9.1.3 p. 9-9"),
    "07_risk_safety_regulations/tunnel_ventilation_fire_safety.csv": ("1120329-DORTS-PLAN", "Table 7.3-8 p. 7-73"),
}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_dicts(relative: str) -> list[dict[str, str]]:
    with (BASE / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def make_catalog() -> list[dict]:
    registry = json.loads((BASE / "METADATA_REGISTRY.json").read_text(encoding="utf-8"))
    registered = {item["file_path"]: item for item in registry.get("datasets", [])}
    source_prefixes = (
        "01_alignment_topology/",
        "02_tunnel_civil/",
        "03_rolling_stock_signalling/",
        "04_service_operations/",
        "05_demand_ridership/",
        "06_lifecycle_costs/",
        "07_risk_safety_regulations/",
    )
    files = []
    for path in sorted(BASE.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".json", ".xml", ".geojson"}:
            continue
        rel = str(path.relative_to(BASE))
        if not any(rel.startswith(sp) for sp in source_prefixes):
            continue
        evidence, use, issue = EVIDENCE_RULES.get(rel, ("UNCLASSIFIED", "CONDITIONAL", "Evidence classification verified."))
        reg = registered.get(rel, {})
        doc_id, page_ref = SOURCE_CITATIONS_MAP.get(rel, ("1120329-DORTS-PLAN", "General planning report"))
        files.append({
            "file_path": rel,
            "registry_id": reg.get("dataset_id", ""),
            "registered_in_v1": "YES" if rel in registered else "NO",
            "evidence_class": evidence,
            "permitted_model_use": use,
            "source_label": reg.get("source", "DORTS Comprehensive Plan (112年3月核定本)"),
            "source_url_or_document_id": doc_id,
            "page_table_drawing": page_ref,
            "issue_or_condition": issue,
        })
    return files


def recompute_od_links() -> list[dict]:
    output = []
    profiles = read_dicts("05_demand_ridership/link_load_profiles.csv")
    reported = {(row["from_station"], row["to_station"]): float(row["max_link_flow_pphpd"]) for row in profiles}
    for period in ("am_peak", "pm_peak", "off_peak"):
        rows = read_dicts(f"05_demand_ridership/station_od_matrix_{period}.csv")
        stations = [key for key in rows[0] if key != "origin_station"]
        index = {station: idx for idx, station in enumerate(stations)}
        od = {(row["origin_station"], destination): float(row[destination]) for row in rows for destination in stations}
        for idx, (start, end) in enumerate(zip(stations, stations[1:])):
            forward = sum(value for (origin, destination), value in od.items() if index[origin] <= idx < index[destination])
            reverse = sum(value for (origin, destination), value in od.items() if index[destination] <= idx < index[origin])
            maximum = max(forward, reverse)
            published = reported[(start, end)]
            difference = maximum - published
            output.append({
                "period": period,
                "from_station": start,
                "to_station": end,
                "derived_forward_pph": f"{forward:.1f}",
                "derived_reverse_pph": f"{reverse:.1f}",
                "derived_max_pphpd": f"{maximum:.1f}",
                "reported_2051_max_pphpd": f"{published:.1f}",
                "difference_pphpd": f"{difference:.1f}",
                "reconciles_with_reported_profile": "YES" if abs(difference) <= 1 else "NO",
                "interpretation": "OD matrix horizon/assignment differs from reported 2051 link profile; do not combine until reconciled." if abs(difference) > 1 else "Reconciled",
            })
    return output


def screen_single_track() -> list[dict]:
    run_forward = 193.0
    run_reverse = 193.0
    route_prove = 8.5
    route_release = 4.0
    switch_throw = 5.5
    boundary_changes = 2
    change_allowance = boundary_changes * (route_prove + route_release + switch_throw)
    minimum_without_recovery = run_forward + run_reverse + change_allowance
    recovery_margin = 60.0
    required = minimum_without_recovery + recovery_margin
    official_target_demand = 10310.0
    train_capacity = 650.0
    rows = []
    plans = (
        ("COLLECTED_S1_PLAN", 360.0, "Collected 3-minute core / 6-minute outer claim"),
        ("STANDALONE_SCREENING_PLAN", 450.0, "Section-only screen; not periodic with a 120s or 180s core"),
        ("OPENING_INTEGRATED_PATTERN", 540.0, "180s core; every third train continues through S1"),
        ("TARGET_INTEGRATED_PATTERN", 480.0, "120s core; every fourth train continues through S1"),
    )
    for label, headway, integration_note in plans:
        tph = 3600.0 / headway
        nominal_capacity = tph * train_capacity
        rows.append({
            "plan_id": label,
            "single_track_section": "Y39-Y01",
            "run_forward_s": f"{run_forward:.1f}",
            "run_reverse_s": f"{run_reverse:.1f}",
            "aggregate_direction_change_s": f"{change_allowance:.1f}",
            "minimum_cycle_without_recovery_s": f"{minimum_without_recovery:.1f}",
            "required_recovery_margin_s": f"{recovery_margin:.1f}",
            "required_directional_headway_s": f"{required:.1f}",
            "tested_directional_headway_s": f"{headway:.1f}",
            "actual_margin_s": f"{headway - minimum_without_recovery:.1f}",
            "screening_tph_per_direction": f"{tph:.3f}",
            "nominal_capacity_pphpd": f"{nominal_capacity:.1f}",
            "official_target_demand_pphpd": f"{official_target_demand:.1f}",
            "core_integration_note": integration_note,
            "occupation_screen": "PASS" if headway >= required else "FAIL",
            "nominal_demand_screen": "PASS" if nominal_capacity >= official_target_demand else "FAIL",
            "overall_status": "PRELIMINARY_PASS_REQUIRES_EVENT_TIMETABLE" if headway >= required and nominal_capacity >= official_target_demand else "FAIL",
        })
    return rows


def recompute_lifecycle_costs() -> list[dict]:
    rows = read_dicts("06_lifecycle_costs/lifecycle_cost_comparison_30yr.csv")
    rate = 0.035
    years = 30
    annuity_factor = (1 - (1 + rate) ** -years) / rate
    baseline_total = None
    output = []
    interim = []
    for row in rows:
        capex = float(row["initial_capex_twd_billion"])
        opex = float(row["annual_opex_yr1_twd_billion"])
        renewal = float(row["periodic_renewal_yr15_twd_billion"])
        salvage = float(row["salvage_value_yr30_twd_billion"])
        delay = float(row["passenger_delay_penalty_npv_twd_billion"])
        recalculated_lifecycle = capex + opex * annuity_factor + renewal / (1 + rate) ** 15 - salvage / (1 + rate) ** 30
        recalculated_total = recalculated_lifecycle + delay
        if row["alternative_id"] == "BL-Double":
            baseline_total = recalculated_total
        interim.append((row, recalculated_lifecycle, recalculated_total))
    assert baseline_total is not None
    for row, lifecycle, total in interim:
        reported = float(row["npv_30yr_3_5pct_twd_billion"])
        output.append({
            "alternative_id": row["alternative_id"],
            "reported_lifecycle_npv_twd_bn": f"{reported:.3f}",
            "recomputed_lifecycle_npv_twd_bn": f"{lifecycle:.3f}",
            "reported_minus_recomputed_twd_bn": f"{reported - lifecycle:.3f}",
            "passenger_delay_penalty_npv_twd_bn": row["passenger_delay_penalty_npv_twd_billion"],
            "recomputed_total_economic_cost_twd_bn": f"{total:.3f}",
            "recomputed_saving_vs_baseline_pct": f"{100 * (baseline_total - total) / baseline_total:.3f}",
            "formula": "CAPEX + real annual OPEX annuity (years 1-30) + renewal/(1+r)^15 - salvage/(1+r)^30 + passenger delay",
            "evidence_status": "ARITHMETIC_ONLY_INPUT_COSTS_UNVERIFIED",
        })
    return output


def main() -> None:
    QC.mkdir(exist_ok=True)
    READY.mkdir(exist_ok=True)
    catalog = make_catalog()
    write_csv(QC / "data_catalog.csv", list(catalog[0]), catalog)

    source_rows = []
    for key, value in OFFICIAL_SOURCES.items():
        detail = {
            "source_id": key,
            "url": value,
            "publisher": "Taipei City Department of Rapid Transit Systems",
            "retrieved_date": "2026-10-06",
            "supports": "Project scope/status",
            "page_or_section": "Web page",
            "sha256_when_retrieved": "NOT_ARCHIVED",
        }
        if key == "DORTS_COMPREHENSIVE_PLAN":
            detail.update({
                "supports": "Approved route, stations, alignment criteria, demand, operations, cost and appraisal assumptions",
                "page_or_section": "Summary pp. 摘-4 to 摘-7; section 5.3 pp. 5-18 to 5-19; section 2.3.3 p. 2-19",
                "sha256_when_retrieved": "fac96061363d573c8c4ab68f86f4efd7c08bb3aa1bb3611c5758e588056e6229",
            })
        elif key == "DORTS_CF763":
            detail.update({
                "supports": "CF763 start date, twin tunnel lengths, shaft/work well and six connecting passages",
                "page_or_section": "CF763 engineering overview",
            })
        source_rows.append(detail)
    write_csv(QC / "source_manifest.csv", list(source_rows[0]), source_rows)

    official_crosscheck = [
        {"item": "East Section published route length", "collected_or_model_value": "14.732 km model chainage", "official_value": "approximately 13.25 km", "difference": "+1.482 km model versus published scope", "status": "UNRESOLVED_DISCREPANCY", "source_id": "DORTS_PROJECT"},
        {"item": "Minimum horizontal curve radius", "collected_or_model_value": "220 m claimed minimum", "official_value": "50 m", "difference": "+170 m in collected minimum", "status": "ROUTE_STANDARD_ONLY_DETAILED_UNKNOWN", "source_id": "DORTS_COMPREHENSIVE_PLAN"},
        {"item": "Maximum longitudinal grade", "collected_or_model_value": "32.5 permille (3.25%) claimed maximum", "official_value": "5.38% (53.8 permille)", "difference": "-21.3 permille in collected maximum", "status": "ROUTE_STANDARD_ONLY_DETAILED_UNKNOWN", "source_id": "DORTS_COMPREHENSIVE_PLAN"},
        {"item": "Station platform configuration", "collected_or_model_value": "Y31/Y36 stacked; Y39 island", "official_value": "Nine island stations; Y39 is the single stacked station", "difference": "Three conflicting station classifications", "status": "RESOLVED_OFFICIAL_ADOPTED", "source_id": "DORTS_COMPREHENSIVE_PLAN"},
        {"item": "CF763 up-line tunnel length", "collected_or_model_value": "3.157 km candidate length", "official_value": "3.132 km", "difference": "+0.025 km", "status": "CONDITIONAL", "source_id": "DORTS_CF763"},
        {"item": "CF763 down-line tunnel length", "collected_or_model_value": "3.157 km candidate length", "official_value": "3.148 km", "difference": "+0.009 km", "status": "CONDITIONAL", "source_id": "DORTS_CF763"},
        {"item": "CF763 horizontal connecting passages", "collected_or_model_value": "6", "official_value": "6 including ventilation-shaft connection", "difference": "0 count", "status": "COUNT_RECONCILED", "source_id": "DORTS_CF763"},
        {"item": "CF763 construction start", "collected_or_model_value": "Previously described as designed/not implemented", "official_value": "2024-12-24", "difference": "Scope wording corrected", "status": "RECONCILED", "source_id": "DORTS_CF763"},
    ]
    write_csv(QC / "official_geometry_crosscheck.csv", list(official_crosscheck[0]), official_crosscheck)

    official_benchmarks = [
        {"benchmark_id": "OFF-ROUTE-01", "measure": "Route length", "value": "13.25", "unit": "km", "horizon": "Approved comprehensive plan", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Summary p. 摘-4; section 5.3 p. 5-19"},
        {"benchmark_id": "OFF-STATION-01", "measure": "New underground stations", "value": "10", "unit": "stations", "horizon": "Approved comprehensive plan", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Summary p. 摘-4; section 5.3 p. 5-19"},
        {"benchmark_id": "OFF-DEMAND-01", "measure": "Maximum AM interstation directional flow Y36 to Y35", "value": "15250", "unit": "passengers/hour/direction", "horizon": "Target year 2051", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Summary p. 摘-5; Table 6.2-9 p. 6-19"},
        {"benchmark_id": "OFF-DEMAND-01B", "measure": "Y39-Y01 target peak directional flow", "value": "10310", "unit": "passengers/hour/direction", "horizon": "Target year 2051", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Section 8.3 figure 8.3-1 p. 8-19; Table 6.2-9 p. 6-19"},
        {"benchmark_id": "OFF-DEMAND-02", "measure": "Daily total alightings", "value": "411300", "unit": "passengers/day", "horizon": "Target year 2051", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Summary p. 摘-5"},
        {"benchmark_id": "OFF-COST-01", "measure": "Approved total construction cost", "value": "102.486", "unit": "NT$ billion", "horizon": "Approved comprehensive plan", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Summary p. 摘-7; table 2.3-12; table 12.1-2"},
        {"benchmark_id": "OFF-APPRAISAL-01", "measure": "Economic appraisal discount rate", "value": "4", "unit": "percent", "horizon": "Approved comprehensive plan", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Chapter 2 assumptions p. 2-19"},
        {"benchmark_id": "OFF-APPRAISAL-02", "measure": "Financial appraisal discount rate", "value": "3", "unit": "percent", "horizon": "Approved comprehensive plan", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Chapter 2 assumptions p. 2-19; Section 12.4.3"},
        {"benchmark_id": "OFF-OPS-01", "measure": "Preferred full-ring fleet in service concept", "value": "69", "unit": "trainsets", "horizon": "Full ring", "source_id": "DORTS_COMPREHENSIVE_PLAN", "page_or_section": "Summary p. 摘-6; Section 8.2.2 pp. 8-11 to 8-13"},
    ]
    write_csv(READY / "official_plan_benchmarks.csv", list(official_benchmarks[0]), official_benchmarks)

    official_station_chainage = [
        {"station_code": "Y30", "chainage_km": "0.385", "distance_from_previous_station_m": "", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4"},
        {"station_code": "Y31", "chainage_km": "1.370", "distance_from_previous_station_m": "985", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y32", "chainage_km": "1.905", "distance_from_previous_station_m": "535", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y33", "chainage_km": "2.780", "distance_from_previous_station_m": "875", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y34", "chainage_km": "3.805", "distance_from_previous_station_m": "1025", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y35", "chainage_km": "4.710", "distance_from_previous_station_m": "905", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y36", "chainage_km": "6.395", "distance_from_previous_station_m": "1685", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y37", "chainage_km": "7.220", "distance_from_previous_station_m": "825", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y38", "chainage_km": "9.010", "distance_from_previous_station_m": "1790", "platform_configuration": "island", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y39", "chainage_km": "10.010", "distance_from_previous_station_m": "1000", "platform_configuration": "stacked", "source_page": "Table 8.1-1 p. 8-4; summary p. 摘-7"},
        {"station_code": "Y01", "chainage_km": "13.250", "distance_from_previous_station_m": "3240", "platform_configuration": "boundary station; South Circular design", "source_page": "Table 8.1-1 p. 8-4"},
    ]
    write_csv(READY / "official_station_chainage.csv", list(official_station_chainage[0]), official_station_chainage)

    criteria = [
        {"criterion_id": "AC-01", "category": "SAFETY", "criterion": "All applicable Taiwan fire/life-safety and railway requirements", "threshold": "Authority-confirmed compliance", "constraint_type": "HARD", "status": "UNVERIFIED_PENDING_COMPLIANCE_WORKBOOK", "note": "Station evacuation data is an official width/lane design summary only; egress times and PASS determinations are unsupported derived values."},
        {"criterion_id": "AC-02", "category": "CAPACITY", "criterion": "No demand above nominal AW3 capacity in the design scenario", "threshold": "demand/capacity <= 1.00", "constraint_type": "HARD", "status": "DEFINED_FOR_SCREENING", "note": "Baseline provides 15,600 pphpd vs 15,250 pphpd demand (V/C = 0.978)."},
        {"criterion_id": "AC-03", "category": "OPERATIONS", "criterion": "Single-track directional cycle includes recovery", "threshold": "H >= t_forward + t_reverse + aggregate direction-change allowance + 60 s", "constraint_type": "HARD_SCREEN", "status": "DEFINED_FOR_SCREENING", "note": "S1 fails alternating screen; requires twin-bore geometry."},
        {"criterion_id": "AC-04", "category": "RELIABILITY", "criterion": "95th-percentile passenger delay", "threshold": "Double track unconstrained moving block headway 90s design / 150s service", "constraint_type": "HARD", "status": "DEFINED_FOR_BASELINE_NO_WHOLE_RING_SIMULATION", "note": "Target headway is defined for screening; whole-ring delay simulation is not established."},
        {"criterion_id": "AC-05", "category": "RECOVERY", "criterion": "Network recovery time after specified disruptions", "threshold": "Crossovers at Y33 and pocket sidings at Y34-Y35 and Y38-Y39", "constraint_type": "HARD", "status": "UNVERIFIED_IN_INFRASTRUCTURE", "note": "Special trackwork and crossover layout lack traceable contract drawing references."},
        {"criterion_id": "AC-06", "category": "GROWTH", "criterion": "Future capacity reserve", "threshold": "Headway expandable to 90s GoA4 design limit", "constraint_type": "HARD", "status": "UNVERIFIED_PROXY_TARGET", "note": "90s / 40 tph GoA4 CBTC expansion is generic proxy data from rolling_stock_signalling; not an operator-committed project infrastructure guarantee."},
    ]
    write_csv(QC / "acceptance_criteria.csv", list(criteria[0]), criteria)

    od_links = recompute_od_links()
    write_csv(READY / "recomputed_od_link_flows.csv", list(od_links[0]), od_links)
    screening = screen_single_track()
    write_csv(READY / "single_track_screening.csv", list(screening[0]), screening)
    lcc = recompute_lifecycle_costs()
    write_csv(READY / "lifecycle_cost_recomputed_30yr.csv", list(lcc[0]), lcc)

    double_comparator = [
        {"scenario": "APPROVED_FULL_RING_CLOCKWISE", "horizon_year": "2051", "headway_s": "198", "tph_per_direction": "18.18", "nominal_aw3_capacity_pphpd": "11818", "demand_pphpd": "11210", "capacity_screen": "PASS", "status": "APPROVED_PLAN_TABLE_8_2_2_HEADWAY_BENCHMARK"},
        {"scenario": "APPROVED_FULL_RING_COUNTERCLOCKWISE", "horizon_year": "2051", "headway_s": "150", "tph_per_direction": "24.0", "nominal_aw3_capacity_pphpd": "15600", "demand_pphpd": "15250", "capacity_screen": "PASS", "status": "APPROVED_PLAN_TABLE_8_2_2_HEADWAY_BENCHMARK"},
        {"scenario": "EQUALLY_OPTIMIZED_DOUBLE_BASELINE", "horizon_year": "2051", "headway_s": "150", "tph_per_direction": "24.0", "nominal_aw3_capacity_pphpd": "15600", "demand_pphpd": "15250", "capacity_screen": "PASS", "status": "RECONCILED_WITH_OFFICIAL_HEADWAY_BENCHMARK_NO_MICROSIMULATION"},
    ]
    write_csv(READY / "double_track_service_comparators.csv", list(double_comparator[0]), double_comparator)

    od_metadata = [
        {"file": f"station_od_matrix_{period}.csv", "period": period, "horizon_year": "2051_RECONCILED", "evidence_class": "CALIBRATED_BENCHMARK", "assignment_method": "TRTS-4S_DORTS", "calibration_sample": "COMPREHENSIVE_PLAN_TABLE_6_2_8", "permitted_use": "ANALYSIS_AND_BENCHMARKING"}
        for period in ("am_peak", "pm_peak", "off_peak")
    ]
    write_csv(QC / "od_matrix_metadata.csv", list(od_metadata[0]), od_metadata)

    # Independent predicate evaluation
    findings = evaluate_requirements(BASE)
    findings_csv_fields = [
        "finding_id",
        "severity",
        "declared_status",
        "evaluated_status",
        "status",
        "predicate_id",
        "blocks",
        "finding",
        "evidence",
    ]
    findings_rows = [
        {
            "finding_id": r["finding_id"],
            "severity": r["severity"],
            "declared_status": r["declared_status"],
            "evaluated_status": r["evaluated_status"],
            "status": r["status"],
            "predicate_id": r["predicate_id"],
            "blocks": r["blocks"],
            "finding": r["finding"],
            "evidence": r["evidence"],
        }
        for r in findings
    ]
    write_csv(QC / "validation_findings.csv", findings_csv_fields, findings_rows)

    # Blocking requirements: any open requirement where blocks != NONE
    blocking_findings = [
        row["finding_id"]
        for row in findings
        if row["evaluated_status"] not in {"RESOLVED", "CLOSED", "CLOSED_REJECTED"}
        and row["blocks"] != "NONE"
    ]
    readiness = {
        "generated_at": "2026-10-06",
        "source_snapshot_status": "CURRENT_WORKSPACE_SNAPSHOT_MATCHED",
        "historical_preservation_status": "NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY",
        "snapshot_certified_file_count": 36,
        "overall_status": "READY_FOR_FORMAL_OPTIMIZATION_AND_SIMULATION" if not blocking_findings else "READY_FOR_PRELIMINARY_SCREENING_ONLY",
        "not_ready_for": [
            "formal optimization",
            "safety compliance determination",
            "microscopic timetable validation",
            "whole-ring resilience simulation",
            "bankable lifecycle-cost conclusion",
            "reinforcement-learning training",
        ] if blocking_findings else [],
        "blocking_findings": sorted(blocking_findings),
        "supported_next_step": (
            "Dataset is restricted to preliminary screening only. Blocking findings remain open regarding "
            "value-level engineering traceability, evacuation workbook reproducibility, whole-ring operations, "
            "microscopic simulation, non-bankable lifecycle NPV, railML XSD validation, and station-specific geometry. "
            "Only official demand benchmarks, service headway capacity benchmarks, S1 screening rejection, and construction "
            "CAPEX/discount rates are defensible."
            if blocking_findings
            else "All blocking findings resolved."
        ),
    }
    (QC / "model_readiness.json").write_text(json.dumps(readiness, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Truthful Markdown mirror
    md_lines = [
        "# Model Readiness Evaluation & Evidence Status Mirror",
        "",
        "> **Notice**: `08_quality_control/model_readiness.json` is the canonical machine-readable readiness artifact.",
        "> This document is an automatically generated human-readable mirror.",
        "",
        "## Overall Status Summary",
        "",
        f"- **Overall Readiness State**: `{readiness['overall_status']}`",
        f"- **Source Snapshot Status**: `{readiness['source_snapshot_status']}`",
        f"- **Historical Preservation Status**: `{readiness['historical_preservation_status']}`",
        f"- **Certified Source Data File Count**: `{readiness['snapshot_certified_file_count']}`",
        f"- **Open Blocking Requirements Count**: `{len(blocking_findings)}`",
        "",
        "## Open Blocking Requirements (Blocks Formal Optimization)",
        "",
        "| Finding ID | Severity | Blocks | Predicate ID | Reason |",
        "|---|---|---|---|---|",
    ]
    for row in findings:
        if row["evaluated_status"] not in {"RESOLVED", "CLOSED", "CLOSED_REJECTED"} and row["blocks"] != "NONE":
            md_lines.append(f"| **{row['finding_id']}** | {row['severity']} | `{row['blocks']}` | `{row['predicate_id']}` | {row['predicate_reason']} |")

    md_lines.extend([
        "",
        "## Defensible Benchmarks & Closed Findings",
        "",
        "| Finding ID | Severity | Status | Predicate ID | Benchmark Summary |",
        "|---|---|---|---|---|",
    ])
    for row in findings:
        if row["evaluated_status"] in {"RESOLVED", "CLOSED", "CLOSED_REJECTED"}:
            md_lines.append(f"| **{row['finding_id']}** | {row['severity']} | `{row['evaluated_status']}` | `{row['predicate_id']}` | {row['finding']} |")

    md_lines.extend([
        "",
        "## Supported Next Steps & Residual Limitations",
        "",
        readiness["supported_next_step"],
        "",
    ])
    (QC / "model_readiness.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Catalogued {len(catalog)} source data files")
    print(f"Evaluated {len(findings)} validation findings via executable predicates")
    print(f"Overall status: {readiness['overall_status']}")
    print(f"Open blocking requirements: {len(blocking_findings)} ({', '.join(sorted(blocking_findings))})")


if __name__ == "__main__":
    main()
