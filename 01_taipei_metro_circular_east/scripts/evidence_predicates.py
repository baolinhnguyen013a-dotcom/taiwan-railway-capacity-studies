#!/usr/bin/env python3
"""Machine-readable evidence requirements and proof-oriented executable predicates.

Enforces independent, fail-closed verification:
- declared_status is tracked separately from evaluated_status.
- A declared RESOLVED CANNOT override a failed predicate.
- Any evaluated open requirement with blocks != "NONE" blocks formal readiness.
- Predicates require positive, verifiable evidence packages, not mere marker strings.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class EvidenceRequirement:
    finding_id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    declared_status: str  # RESOLVED, OPEN, CLOSED, CLOSED_REJECTED
    predicate_id: str
    blocks: str  # FORMAL_OPTIMIZATION, NONE
    title: str
    evidence: str
    predicate_fn: Callable[[Path], tuple[bool, str]]
    default_closed_status: str = "RESOLVED"


def pred_f001_catalog(base: Path) -> tuple[bool, str]:
    catalog_path = base / "08_quality_control" / "data_catalog.csv"
    if not catalog_path.is_file():
        return False, "08_quality_control/data_catalog.csv is missing."
    with catalog_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "08_quality_control/data_catalog.csv is empty."
    required_cols = {"file_path", "registry_id", "evidence_class", "permitted_model_use", "source_label", "issue_or_condition"}
    if not required_cols.issubset(rows[0].keys()):
        return False, f"data_catalog.csv missing required governance columns: {sorted(required_cols - set(rows[0].keys()))}."
    blocked = [r["file_path"] for r in rows if r.get("permitted_model_use") == "BLOCKED"]
    rejected = [r["file_path"] for r in rows if r.get("permitted_model_use") == "REJECTED_AS_WRITTEN"]
    if blocked or rejected:
        return False, f"Catalog retains {len(blocked)} BLOCKED and {len(rejected)} REJECTED_AS_WRITTEN source inputs."
    return True, "All source data files permitted for model use."


def pred_f002_traceability(base: Path) -> tuple[bool, str]:
    # Proof-oriented: requires positive value-level citations for station-specific geometry,
    # trackwork, crossovers, and vertical grades across all stations with valid drawing citations.
    geom_path = base / "08_analysis_ready" / "official_alignment_geometry.csv"
    citations_path = base / "08_quality_control" / "official_source_citations.csv"

    if not geom_path.is_file():
        return False, "official_alignment_geometry.csv missing."
    with geom_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "official_alignment_geometry.csv has no records."

    required_cols = {
        "station_code",
        "station_name_zh",
        "chainage_km",
        "min_curve_radius_m",
        "max_grade_permille",
        "crossover_pocket_track",
        "trackwork_evidence_status",
        "curve_grade_evidence_status",
        "source_citation",
    }
    if not required_cols.issubset(rows[0].keys()):
        return False, f"official_alignment_geometry.csv missing required columns: {sorted(required_cols - set(rows[0].keys()))}."

    unsupported_geometry = []
    for r in rows:
        code = r.get("station_code", "UNKNOWN")
        curve = r.get("min_curve_radius_m", "")
        grade = r.get("max_grade_permille", "")
        trackwork = r.get("crossover_pocket_track", "")
        cite = r.get("source_citation", "")
        trackwork_status = r.get("trackwork_evidence_status", "")
        curve_status = r.get("curve_grade_evidence_status", "")

        if curve in {"", "UNKNOWN"} or grade in {"", "UNKNOWN"} or trackwork in {"", "UNKNOWN"}:
            unsupported_geometry.append(f"{code} (detailed values UNKNOWN)")
        elif curve_status != "OFFICIAL_DRAWING_VERIFIED" or trackwork_status != "OFFICIAL_DRAWING_VERIFIED":
            unsupported_geometry.append(f"{code} (evidence status not OFFICIAL_DRAWING_VERIFIED)")
        elif not any(prefix in cite for prefix in ("DORTS-DWG-", "CF76-", "TCL-DWG-", "DWG-")):
            unsupported_geometry.append(f"{code} (missing valid drawing sheet citation)")

    if unsupported_geometry:
        return False, (
            f"Detailed station curve radii, vertical gradients, and crossover trackwork exceed value-level official support "
            f"({len(unsupported_geometry)} stations unsupported: {', '.join(unsupported_geometry[:4])}...)."
        )

    if not citations_path.is_file():
        return False, "official_source_citations.csv missing."
    with citations_path.open(encoding="utf-8", newline="") as handle:
        cit_rows = list(csv.DictReader(handle))
    drawing_citations = [
        r for r in cit_rows
        if r.get("chapter_section", "").startswith(("DWG", "Drawing", "CF76"))
        or any(tag in r.get("page_citation", "") for tag in ("DWG", "Drawing", "CF76"))
    ]
    if len(drawing_citations) < 12:
        return False, f"official_source_citations.csv lacks drawing-sheet citations for all 12 stations ({len(drawing_citations)} found)."

    return True, "Station-specific curve radii, vertical grades, and trackwork verified with drawing-level citations."


def pred_f003_demand(base: Path) -> tuple[bool, str]:
    loads_path = base / "08_analysis_ready" / "official_link_loads.csv"
    if not loads_path.is_file():
        return False, "official_link_loads.csv missing."
    with loads_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "official_link_loads.csv is empty."
    y35_y36 = next((r for r in rows if (r.get("from_station") == "Y35" and r.get("to_station") == "Y36") or (r.get("from_station") == "Y36" and r.get("to_station") == "Y35")), None)
    if not y35_y36 or float(y35_y36.get("flow_counterclockwise_to_jiannan_pphpd", 0)) != 15250.0:
        return False, "AM peak critical load Y36->Y35 does not match official 15,250 pphpd benchmark."
    y39_y01 = next((r for r in rows if (r.get("from_station") == "Y39" and r.get("to_station") == "Y01") or (r.get("from_station") == "Y01" and r.get("to_station") == "Y39")), None)
    if not y39_y01 or float(y39_y01.get("flow_counterclockwise_to_jiannan_pphpd", 0)) != 10310.0:
        return False, "Mountain tunnel load Y39->Y01 does not match official 10,310 pphpd benchmark."
    return True, "Official demand benchmarks verified against Table 6.2-9 (15,250 pphpd peak link flow and 10,310 pphpd mountain link)."


def pred_f004_service(base: Path) -> tuple[bool, str]:
    service_path = base / "08_analysis_ready" / "official_operational_service_baseline.csv"
    if not service_path.is_file():
        return False, "official_operational_service_baseline.csv missing."
    with service_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "official_operational_service_baseline.csv is empty."
    am_peak = next((r for r in rows if "AM Peak" in r.get("period_name", "")), None)
    if not am_peak or float(am_peak.get("headway_ccw_s", 0)) != 150.0:
        return False, "Baseline CCW peak headway does not match official 150s (24 tph) specification."
    if float(am_peak.get("nominal_cap_ccw_pphpd", 0)) < 15250.0:
        return False, "Baseline CCW capacity fails to cover peak demand."
    return True, "Official baseline service plan benchmark verified (150s headway supplying 15,600 pphpd)."


def pred_f005_s1_screen(base: Path) -> tuple[bool, str]:
    screen_path = base / "08_analysis_ready" / "single_track_screening.csv"
    if not screen_path.is_file():
        return False, "single_track_screening.csv missing."
    with screen_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "single_track_screening.csv is empty."
    collected = next((r for r in rows if r.get("plan_id") == "COLLECTED_S1_PLAN"), None)
    if not collected or collected.get("overall_status") != "FAIL":
        return False, "S1 collected plan must evaluate to FAIL under the alternating screen."
    return True, "S1 alternating screen conclusively fails recovery margin and demand capacity."


def pred_f006_evacuation(base: Path) -> tuple[bool, str]:
    # Proof-oriented: requires positive presence of a reproducible NFPA 130 calculation workbook
    # package containing verified pedestrian egress parameters, valid limits, and calculation source IDs.
    workbook_path = base / "08_analysis_ready" / "reproducible_nfpa130_evacuation_workbook.csv"
    evac_path = base / "08_analysis_ready" / "official_station_evacuation_nfpa130.csv"

    if not evac_path.is_file():
        return False, "official_station_evacuation_nfpa130.csv missing."
    with evac_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "official_station_evacuation_nfpa130.csv is empty."

    evac_cols = {"station_code", "station_name_zh", "platform_width_installed_m", "installed_exit_lanes", "evacuation_compliance_status"}
    if not evac_cols.issubset(rows[0].keys()):
        return False, f"official_station_evacuation_nfpa130.csv missing required columns: {sorted(evac_cols - set(rows[0].keys()))}."

    # Fail closed if separate reproducible calculation workbook package is missing
    if not workbook_path.is_file():
        return False, (
            "Missing reproducible NFPA 130 evacuation workbook evidence package; official data is a station "
            "width/lane design summary (Table 9.1-5) only. Derived egress times and PASS determinations are unsupported."
        )

    with workbook_path.open(encoding="utf-8", newline="") as handle:
        wb_rows = list(csv.DictReader(handle))
    if not wb_rows:
        return False, "Reproducible evacuation workbook is empty."

    required_wb_cols = {
        "station_code",
        "platform_occupant_load",
        "concourse_occupant_load",
        "stairs_flow_rate_persons_per_min",
        "doors_gates_flow_rate_persons_per_min",
        "calculated_platform_clearance_time_min",
        "nfpa130_platform_limit_min",
        "calculated_safe_haven_time_min",
        "nfpa130_safe_haven_limit_min",
        "evacuation_margin_sec",
        "calculation_source_id",
        "compliance_status",
    }
    if not required_wb_cols.issubset(wb_rows[0].keys()):
        return False, (
            f"Reproducible evacuation workbook missing required schema columns: {sorted(required_wb_cols - set(wb_rows[0].keys()))}."
        )

    # Station coverage check: all 12 East-section stations
    expected_stations = {"Y29", "Y30", "Y31", "Y32", "Y33", "Y34", "Y35", "Y36", "Y37", "Y38", "Y39", "Y01"}
    covered_stations = {r.get("station_code", "") for r in wb_rows}
    missing_stations = expected_stations - covered_stations
    if missing_stations:
        return False, f"Evacuation workbook missing coverage for stations: {sorted(missing_stations)}."

    for r in wb_rows:
        code = r.get("station_code", "")
        try:
            p_load = float(r.get("platform_occupant_load", 0))
            stairs_flow = float(r.get("stairs_flow_rate_persons_per_min", 0))
            doors_flow = float(r.get("doors_gates_flow_rate_persons_per_min", 0))
            p_time = float(r.get("calculated_platform_clearance_time_min", 0))
            p_limit = float(r.get("nfpa130_platform_limit_min", 0))
            sh_time = float(r.get("calculated_safe_haven_time_min", 0))
            sh_limit = float(r.get("nfpa130_safe_haven_limit_min", 0))
            status = r.get("compliance_status", "")
            source_id = r.get("calculation_source_id", "")
        except ValueError:
            return False, f"Evacuation workbook row for {code} contains invalid non-numeric fields."

        if p_load <= 0 or stairs_flow <= 0 or doors_flow <= 0 or p_time <= 0 or sh_time <= 0:
            return False, f"Evacuation workbook row for {code} contains non-positive flow rates or loads."

        if p_limit != 4.0 or sh_limit != 6.0:
            return False, f"Evacuation workbook row for {code} uses non-standard NFPA 130 limits (expected 4.0 min and 6.0 min)."

        if (p_time > p_limit or sh_time > sh_limit) and status == "PASS":
            return False, f"Evacuation workbook row for {code} incorrectly reports PASS despite exceeding limits."

        if not source_id or source_id in {"UNKNOWN", "NONE"} or not source_id.startswith("CALC-NFPA130-"):
            return False, f"Evacuation workbook row for {code} lacks verified calculation source reference ID."

    return True, "Reproducible NFPA 130 compliance workbook evidence package verified across all 12 stations."


def pred_f007_whole_ring(base: Path) -> tuple[bool, str]:
    # Proof-oriented: requires actual whole-ring station coverage (all 39 Circular Line stations),
    # fleet circulation continuity, and nonempty multi-depot track movement models.
    tt_path = base / "08_analysis_ready" / "train_event_timetable_approved_baseline.csv"
    depot_plan_path = base / "08_analysis_ready" / "whole_ring_depot_circulation_plan.csv"

    if not tt_path.is_file():
        return False, "train_event_timetable_approved_baseline.csv missing."
    with tt_path.open(encoding="utf-8", newline="") as handle:
        tt_rows = list(csv.DictReader(handle))
    if not tt_rows:
        return False, "train_event_timetable_approved_baseline.csv is empty."

    stations = set(r.get("station_code", "") for r in tt_rows)
    expected_full_ring = {f"Y{i:02d}" for i in range(1, 40)}
    missing_stations = expected_full_ring - stations
    if len(stations) < 39 or missing_stations:
        return False, (
            f"Event timetable covers only {len(stations)} stations (East-section Y29-Y01); "
            f"lacks whole-ring coverage ({len(missing_stations)} stations missing), fleet continuity, and depot throat models."
        )

    if not depot_plan_path.is_file():
        return False, "Missing whole-ring depot circulation and stabling track allocation artifact."

    with depot_plan_path.open(encoding="utf-8", newline="") as handle:
        depot_rows = list(csv.DictReader(handle))
    if not depot_rows:
        return False, "whole_ring_depot_circulation_plan.csv is empty."

    required_depot_cols = {
        "depot_id",
        "depot_name_zh",
        "stabling_track_id",
        "trainset_id",
        "pull_out_time_s",
        "pull_in_time_s",
        "service_trip_id",
        "lead_track_length_m",
        "interlocking_throat_route_id",
        "source_plan_ref",
    }
    if not required_depot_cols.issubset(depot_rows[0].keys()):
        return False, f"whole_ring_depot_circulation_plan.csv missing required schema columns: {sorted(required_depot_cols - set(depot_rows[0].keys()))}."

    depots = {r.get("depot_id", "") for r in depot_rows}
    if not ("DEPOT-SOUTH" in depots and ("DEPOT-NORTH" in depots or "DEPOT-EAST" in depots)):
        return False, "Depot circulation plan missing multi-depot coverage (requires both South and North/East depots)."

    active_trainsets = {r.get("trainset_id", "") for r in depot_rows if r.get("trainset_id")}
    if len(active_trainsets) < 30:
        return False, f"Depot circulation plan accounts for only {len(active_trainsets)} trainsets (requires >= 30 active trainsets for whole ring)."

    tt_trips = {r.get("train_id", "") for r in tt_rows if r.get("train_id")}
    depot_trips = {r.get("service_trip_id", "") for r in depot_rows if r.get("service_trip_id")}
    unmatched_trips = depot_trips - tt_trips
    if unmatched_trips:
        return False, f"Depot circulation plan references {len(unmatched_trips)} trip IDs not present in timetable."

    for r in depot_rows:
        try:
            p_out = float(r.get("pull_out_time_s", 0))
            p_in = float(r.get("pull_in_time_s", 0))
            lead = float(r.get("lead_track_length_m", 0))
        except ValueError:
            return False, "Depot circulation plan contains invalid non-numeric times or track lengths."
        if p_out < 0 or p_in < p_out or lead <= 0:
            return False, "Depot circulation plan contains inconsistent pull-out/pull-in chronology or non-positive lead track lengths."
        if not r.get("source_plan_ref", "").startswith("DORTS-DEPOT-"):
            return False, f"Depot plan row {r.get('trainset_id')} lacks official source reference starting with DORTS-DEPOT-."

    return True, "Full-ring station coverage and validated depot fleet circulation model verified."


def pred_f008_microsimulation(base: Path) -> tuple[bool, str]:
    # Proof-oriented: requires block signaling layout, interlocking route conflicts matrix,
    # valid timetable semantics, and timetable block occupancy assignments.
    tt_path = base / "08_analysis_ready" / "train_event_timetable_approved_baseline.csv"
    block_layout_path = base / "08_analysis_ready" / "block_signalling_topology.csv"
    interlocking_path = base / "08_analysis_ready" / "interlocking_route_conflicts.csv"
    crossovers_path = base / "01_alignment_topology" / "special_trackwork_crossovers.csv"

    if not tt_path.is_file():
        return False, "train_event_timetable_approved_baseline.csv missing."
    with tt_path.open(encoding="utf-8", newline="") as handle:
        tt_rows = list(csv.DictReader(handle))
    if not tt_rows:
        return False, "train_event_timetable_approved_baseline.csv is empty."

    # Timetable semantic check: short-turn Y22-Y38 trips must NOT traverse stations south of Y38 (Y39, Y01) or north (Y29)
    short_turns = [r for r in tt_rows if "SHORT_TURN" in r.get("service_type", "")]
    if short_turns:
        st_stations = set(r.get("station_code", "") for r in short_turns)
        illegal_stations = st_stations.intersection({"Y01", "Y29", "Y39"})
        if illegal_stations:
            return False, (
                f"Timetable semantic error: short-turn Y22-Y38 trips incorrectly traverse non-turnback stations "
                f"({', '.join(sorted(illegal_stations))}); lacks block-level signaling and interlocking models."
            )

    # Require physical block layout and interlocking conflict models
    if not block_layout_path.is_file() or not interlocking_path.is_file():
        return False, (
            "Missing block signaling topology and interlocking route conflict matrices; "
            "timetable is an indicative headway schedule and cannot be certified as microsimulation."
        )

    with block_layout_path.open(encoding="utf-8", newline="") as handle:
        block_rows = list(csv.DictReader(handle))
    if not block_rows:
        return False, "block_signalling_topology.csv is empty."

    required_block_cols = {
        "block_id",
        "track_id",
        "start_chainage_m",
        "end_chainage_m",
        "block_length_m",
        "design_speed_kmh",
        "safe_braking_distance_m",
        "signalling_block_type",
        "cbtc_overlap_length_m",
    }
    if not required_block_cols.issubset(block_rows[0].keys()):
        return False, f"block_signalling_topology.csv missing required schema columns: {sorted(required_block_cols - set(block_rows[0].keys()))}."

    if len(block_rows) < 20:
        return False, f"block_signalling_topology.csv has insufficient blocks ({len(block_rows)} blocks; requires >= 20)."

    for b in block_rows:
        try:
            s_ch = float(b.get("start_chainage_m", 0))
            e_ch = float(b.get("end_chainage_m", 0))
            b_len = float(b.get("block_length_m", 0))
            s_brk = float(b.get("safe_braking_distance_m", 0))
        except ValueError:
            return False, f"Block {b.get('block_id')} contains invalid non-numeric geometry."
        if e_ch <= s_ch or abs((e_ch - s_ch) - b_len) > 0.1:
            return False, f"Block {b.get('block_id')} has invalid chainage span (start={s_ch}, end={e_ch}, len={b_len})."
        if s_brk <= 0:
            return False, f"Block {b.get('block_id')} has non-positive safe braking distance."

    with interlocking_path.open(encoding="utf-8", newline="") as handle:
        int_rows = list(csv.DictReader(handle))
    if not int_rows:
        return False, "interlocking_route_conflicts.csv is empty."

    required_int_cols = {
        "interlocking_id",
        "route_id",
        "conflicting_route_id",
        "switch_crossover_id",
        "flank_protection_track_id",
        "route_locking_time_s",
        "conflict_type",
    }
    if not required_int_cols.issubset(int_rows[0].keys()):
        return False, f"interlocking_route_conflicts.csv missing required schema columns: {sorted(required_int_cols - set(int_rows[0].keys()))}."

    if len(int_rows) < 10:
        return False, f"interlocking_route_conflicts.csv has insufficient conflict definitions ({len(int_rows)} rows; requires >= 10)."

    if crossovers_path.is_file():
        with crossovers_path.open(encoding="utf-8", newline="") as handle:
            xo_rows = list(csv.DictReader(handle))
        valid_xos = {r.get("crossover_id", "") for r in xo_rows if r.get("crossover_id")}
        int_xos = {r.get("switch_crossover_id", "") for r in int_rows if r.get("switch_crossover_id")}
        unmatched_xos = int_xos - valid_xos
        if unmatched_xos:
            return False, f"Interlocking matrix references invalid crossover IDs: {sorted(unmatched_xos)}."

    valid_blocks = {r.get("block_id", "") for r in block_rows if r.get("block_id")}
    tt_blocks = {r.get("block_id", "") for r in tt_rows if r.get("block_id")}
    if not tt_blocks:
        return False, "Timetable events lack block_id assignments referencing block_signalling_topology.csv."
    unmatched_tt_blocks = tt_blocks - valid_blocks
    if unmatched_tt_blocks:
        return False, f"Timetable references block IDs not present in block topology: {sorted(unmatched_tt_blocks)[:3]}."

    return True, "Microscopic simulation verified with validated block signaling and interlocking models."


def pred_f009_lifecycle(base: Path) -> tuple[bool, str]:
    # Proof-oriented: requires complete nonempty validated lifecycle evidence package with
    # contract-traceable OPEX/renewal/salvage line items and complete 30-year cash flow model.
    audit_model_path = base / "08_analysis_ready" / "bankable_lifecycle_audit_model.csv"
    lcc_path = base / "08_analysis_ready" / "official_lifecycle_cost_baseline.csv"

    if not lcc_path.is_file():
        return False, "official_lifecycle_cost_baseline.csv missing."
    with lcc_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "official_lifecycle_cost_baseline.csv is empty."

    required_lcc_cols = {
        "cost_category",
        "cost_component",
        "capex_twd_bn",
        "annual_opex_twd_bn",
        "renewal_yr15_twd_bn",
        "salvage_yr30_twd_bn",
        "opex_renewal_evidence_tag",
        "lifecycle_npv_status",
    }
    if not required_lcc_cols.issubset(rows[0].keys()):
        return False, f"official_lifecycle_cost_baseline.csv missing required evidence columns: {sorted(required_lcc_cols - set(rows[0].keys()))}."

    for r in rows:
        tag = r.get("opex_renewal_evidence_tag", "")
        status = r.get("lifecycle_npv_status", "")
        if "UNSUBSTANTIATED" in tag or "NON_BANKABLE" in status or "PROXY" in tag or "ARITHMETIC_ONLY" in tag:
            return False, (
                "Annual OPEX, 15-year renewal, 30-year salvage, and 30-year NPV are unsubstantiated arithmetic benchmarks; "
                "lacks a contract-audited bankable lifecycle evidence package."
            )
        if tag != "CONTRACT_AUDITED" or status != "BANKABLE_AUDITED":
            return False, f"Lifecycle row {r.get('cost_component')} lacks verified BANKABLE_AUDITED and CONTRACT_AUDITED certification."

    if not audit_model_path.is_file():
        return False, "Missing contract-audited bankable lifecycle audit model artifact (bankable_lifecycle_audit_model.csv)."

    with audit_model_path.open(encoding="utf-8", newline="") as handle:
        audit_rows = list(csv.DictReader(handle))
    if not audit_rows:
        return False, "bankable_lifecycle_audit_model.csv is empty."

    required_audit_cols = {
        "year",
        "capex_annual_m_ntd",
        "opex_annual_m_ntd",
        "periodic_renewal_m_ntd",
        "salvage_value_m_ntd",
        "net_cash_flow_m_ntd",
        "discount_factor_financial_3pct",
        "discounted_cash_flow_3pct_m_ntd",
        "contract_audit_citation_id",
        "audit_firm_or_agency",
    }
    if not required_audit_cols.issubset(audit_rows[0].keys()):
        return False, f"bankable_lifecycle_audit_model.csv missing required schema columns: {sorted(required_audit_cols - set(audit_rows[0].keys()))}."

    years = {int(r.get("year", -1)) for r in audit_rows if r.get("year", "").isdigit()}
    expected_years = set(range(1, 31))
    if not expected_years.issubset(years):
        return False, f"bankable_lifecycle_audit_model.csv lacks complete 30-year schedule (missing years: {sorted(expected_years - years)[:5]}...)."

    total_npv = 0.0
    for r in audit_rows:
        y = int(r.get("year", 0))
        try:
            capex = float(r.get("capex_annual_m_ntd", 0))
            opex = float(r.get("opex_annual_m_ntd", 0))
            ren = float(r.get("periodic_renewal_m_ntd", 0))
            salv = float(r.get("salvage_value_m_ntd", 0))
            ncf = float(r.get("net_cash_flow_m_ntd", 0))
            df = float(r.get("discount_factor_financial_3pct", 0))
            dcf = float(r.get("discounted_cash_flow_3pct_m_ntd", 0))
            audit_id = r.get("contract_audit_citation_id", "")
            agency = r.get("audit_firm_or_agency", "")
        except ValueError:
            return False, f"Audit model row year {y} contains invalid non-numeric financial values."

        calc_ncf = capex + opex + ren - salv
        if abs(calc_ncf - ncf) > 1.0:
            return False, f"Audit model year {y} net cash flow arithmetic mismatch (calc={calc_ncf}, recorded={ncf})."

        expected_df = 1.0 / ((1.0 + 0.03) ** y) if y > 0 else 1.0
        if abs(expected_df - df) > 0.005:
            return False, f"Audit model year {y} discount factor mismatch (expected={expected_df:.4f}, recorded={df:.4f})."

        if abs(ncf * df - dcf) > 1.0:
            return False, f"Audit model year {y} discounted cash flow arithmetic mismatch."

        total_npv += dcf

        if not audit_id.startswith("AUDIT-") or not agency:
            return False, f"Audit model year {y} lacks contract audit reference ID or audit agency."

    return True, f"Bankable 30-year lifecycle cost model with contract line items verified (NPV: NT$ {total_npv:.2f}M)."


def pred_f010_railml(base: Path) -> tuple[bool, str]:
    # Proof-oriented: requires pinned official railML 3.2 schema manifest/digest,
    # imported dependency verification, recorded validator executable/version/command and exit status,
    # and authenticated XML digests.
    xsd_path = base / "schema" / "railML-3.2" / "railML.xsd"
    manifest_path = base / "schema" / "railML-3.2" / "schema_manifest.json"
    log_json = base / "08_quality_control" / "railml_xsd_validation.json"
    log_text = base / "08_quality_control" / "railml_xsd_validation.log"
    infra_xml = base / "01_alignment_topology" / "railml_infrastructure_east_section.xml"
    rolling_xml = base / "03_rolling_stock_signalling" / "railml_rollingstock_hitachi_emu.xml"

    if not xsd_path.is_file():
        return False, "Missing official railML 3.2 XSD schema bundle in schema/railML-3.2/railML.xsd."

    if not manifest_path.is_file():
        return False, "Missing official railML 3.2 schema manifest (schema/railML-3.2/schema_manifest.json)."

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Cannot parse railML schema manifest: {exc}"

    if manifest.get("railml_version") != "3.2":
        return False, f"Schema manifest version mismatch: {manifest.get('railml_version')} != 3.2."

    schema_files = manifest.get("schema_files", {})
    if not schema_files or "railML.xsd" not in schema_files:
        return False, "Schema manifest does not define required schema files and SHA-256 digests."

    schema_dir = base / "schema" / "railML-3.2"
    for filename, expected_digest in schema_files.items():
        file_path = schema_dir / filename
        if not file_path.is_file():
            return False, f"Missing imported railML schema dependency: {filename}."
        actual_digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_digest != expected_digest:
            return False, f"railML schema file {filename} digest mismatch (corrupted or forged XSD bundle)."

    if not log_json.is_file() and not log_text.is_file():
        return False, "Missing railML schema validation execution log/record in 08_quality_control/."

    if not infra_xml.is_file() or not rolling_xml.is_file():
        return False, "Source railML XML files missing."

    infra_hash = hashlib.sha256(infra_xml.read_bytes()).hexdigest()
    rolling_hash = hashlib.sha256(rolling_xml.read_bytes()).hexdigest()

    if log_json.is_file():
        try:
            val_rec = json.loads(log_json.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"Cannot parse railml_xsd_validation.json: {exc}"

        req_log_keys = {"validator_executable", "validator_version", "command_line", "exit_code", "validated_files"}
        if not req_log_keys.issubset(val_rec.keys()):
            return False, f"railml_xsd_validation.json missing execution audit keys: {sorted(req_log_keys - set(val_rec.keys()))}."

        if val_rec.get("exit_code") != 0:
            return False, f"railML validation recorded non-zero exit status: {val_rec.get('exit_code')}."

        val_files = val_rec.get("validated_files", {})
        infra_logged = val_files.get("01_alignment_topology/railml_infrastructure_east_section.xml")
        rolling_logged = val_files.get("03_rolling_stock_signalling/railml_rollingstock_hitachi_emu.xml")
        if infra_logged != infra_hash or rolling_logged != rolling_hash:
            return False, "railML validation record digests do not match current workspace XML digests."
    else:
        log_content = log_text.read_text(encoding="utf-8")
        if "VALIDATION SUCCESSFUL" not in log_content or "EXIT_CODE: 0" not in log_content:
            return False, "railML XSD validation log does not certify authentic successful execution with exit code 0."
        if infra_hash not in log_content or rolling_hash not in log_content:
            return False, "railML XSD validation log does not certify matching SHA-256 digests for current railML XML files."

    return True, "railML 3.2 formal XSD schema validation verified against official pinned bundle with authentic runner logs."


def pred_f011_scope_transformation(base: Path) -> tuple[bool, str]:
    # Proof-oriented: requires a supported reconciliation record artifact proving how
    # 13.250 km official scope transforms to 14.732 km model chainage with mathematical equation checks.
    recon_path = base / "08_analysis_ready" / "route_length_reconciliation.csv"
    cross_path = base / "08_quality_control" / "official_geometry_crosscheck.csv"

    if not cross_path.is_file():
        return False, "official_geometry_crosscheck.csv missing."
    with cross_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "official_geometry_crosscheck.csv is empty."

    req_cross_cols = {"item", "collected_or_model_value", "official_value", "difference", "status", "source_id"}
    if not req_cross_cols.issubset(rows[0].keys()):
        return False, f"official_geometry_crosscheck.csv missing required columns: {sorted(req_cross_cols - set(rows[0].keys()))}."

    length_row = next((r for r in rows if "published route length" in r.get("item", "").lower()), None)
    if not length_row:
        return False, "Published route length item not found in official_geometry_crosscheck.csv."

    if length_row.get("status") != "RECONCILED_WITH_OFFICIAL_DRAWING":
        return False, (
            "1.482 km route length discrepancy between model chainage (14.732 km) and published scope (13.250 km) is unresolved "
            f"(status: {length_row.get('status')})."
        )

    if not recon_path.is_file():
        return False, "Missing supported route length reconciliation record artifact (route_length_reconciliation.csv)."

    with recon_path.open(encoding="utf-8", newline="") as handle:
        recon_rows = list(csv.DictReader(handle))
    if not recon_rows:
        return False, "route_length_reconciliation.csv is empty."

    required_recon_cols = {
        "segment_id",
        "segment_description",
        "start_chainage_km",
        "end_chainage_km",
        "revenue_length_km",
        "depot_lead_track_length_km",
        "pocket_tail_track_length_km",
        "total_chainage_km",
        "official_drawing_sheet_no",
        "chainage_equation_citation",
    }
    if not required_recon_cols.issubset(recon_rows[0].keys()):
        return False, f"route_length_reconciliation.csv missing required schema columns: {sorted(required_recon_cols - set(recon_rows[0].keys()))}."

    total_revenue = 0.0
    total_model = 0.0
    total_delta = 0.0
    for r in recon_rows:
        try:
            rev = float(r.get("revenue_length_km", 0))
            depot_lead = float(r.get("depot_lead_track_length_km", 0))
            tail = float(r.get("pocket_tail_track_length_km", 0))
            tot = float(r.get("total_chainage_km", 0))
            dwg = r.get("official_drawing_sheet_no", "")
            cite = r.get("chainage_equation_citation", "")
        except ValueError:
            return False, f"Reconciliation row {r.get('segment_id')} contains invalid non-numeric chainage."

        if abs((rev + depot_lead + tail) - tot) > 0.001:
            return False, f"Reconciliation row {r.get('segment_id')} internal equation mismatch (rev+lead+tail != tot)."

        if not dwg.startswith(("DORTS-DWG-", "CF76-", "TCL-DWG-")) or not cite:
            return False, f"Reconciliation row {r.get('segment_id')} lacks drawing sheet citation starting with DORTS-DWG- or CF76-."

        total_revenue += rev
        total_model += tot
        total_delta += (depot_lead + tail)

    if abs(total_revenue - 13.250) > 0.005:
        return False, f"Reconciled revenue length sum ({total_revenue:.3f} km) does not match official scope (13.250 km)."

    if abs(total_model - 14.732) > 0.005:
        return False, f"Reconciled total chainage sum ({total_model:.3f} km) does not match model chainage (14.732 km)."

    if abs(total_delta - 1.482) > 0.005:
        return False, f"Reconciled non-revenue trackage delta ({total_delta:.3f} km) does not account for 1.482 km discrepancy."

    return True, "Chainage scope transformation mathematically reconciled via supported reconciliation record."


def pred_f012_cf763_start(base: Path) -> tuple[bool, str]:
    cross_path = base / "08_quality_control" / "official_geometry_crosscheck.csv"
    if not cross_path.is_file():
        return False, "official_geometry_crosscheck.csv missing."
    with cross_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    start_row = next((r for r in rows if "construction start" in r.get("item", "").lower()), None)
    if start_row and "2024-12-24" in start_row.get("official_value", ""):
        return True, "CF763 construction start date (2024-12-24) verified from official contract notice."
    return False, "CF763 construction start date unverified."


def pred_f013_alignment_geometry(base: Path) -> tuple[bool, str]:
    geom_path = base / "08_analysis_ready" / "official_alignment_geometry.csv"
    if not geom_path.is_file():
        return False, "official_alignment_geometry.csv missing."
    with geom_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "official_alignment_geometry.csv is empty."

    required_cols = {
        "station_code",
        "station_name_zh",
        "chainage_km",
        "min_curve_radius_m",
        "max_grade_permille",
        "crossover_pocket_track",
        "source_citation",
        "curve_grade_evidence_status",
        "trackwork_evidence_status",
    }
    if not required_cols.issubset(rows[0].keys()):
        return False, f"official_alignment_geometry.csv missing required columns: {sorted(required_cols - set(rows[0].keys()))}."

    valid_trackwork_types = {
        "NONE",
        "SINGLE_CROSSOVER",
        "SCISSORS_CROSSOVER",
        "DIAMOND_CROSSOVER",
        "POCKET_TRACK",
        "TRAILING_CROSSOVER",
        "FACING_CROSSOVER",
    }

    unknowns = []
    for r in rows:
        code = r.get("station_code", "UNKNOWN")
        curve_val = r.get("min_curve_radius_m", "")
        grade_val = r.get("max_grade_permille", "")
        trackwork_val = r.get("crossover_pocket_track", "")
        cite = r.get("source_citation", "")
        curve_status = r.get("curve_grade_evidence_status", "")
        track_status = r.get("trackwork_evidence_status", "")

        if curve_val in {"", "UNKNOWN"} or grade_val in {"", "UNKNOWN"} or trackwork_val in {"", "UNKNOWN"}:
            unknowns.append(f"{code} (detailed values UNKNOWN)")
            continue

        if curve_status != "OFFICIAL_DRAWING_VERIFIED" or track_status != "OFFICIAL_DRAWING_VERIFIED":
            unknowns.append(f"{code} (evidence status not OFFICIAL_DRAWING_VERIFIED)")
            continue

        try:
            r_m = float(curve_val)
            g_pm = float(grade_val)
        except ValueError:
            unknowns.append(f"{code} (non-numeric geometry values)")
            continue

        if r_m < 50.0 or r_m > 5000.0:
            unknowns.append(f"{code} (curve radius {r_m}m outside feasible 50-5000m range)")
            continue

        if g_pm < 0.0 or g_pm > 53.8:
            unknowns.append(f"{code} (vertical grade {g_pm} permille exceeds route maximum 53.8)")
            continue

        if trackwork_val not in valid_trackwork_types:
            unknowns.append(f"{code} (unrecognized trackwork type '{trackwork_val}')")
            continue

        if not any(prefix in cite for prefix in ("DORTS-DWG-", "CF76-", "TCL-DWG-", "DWG-")):
            unknowns.append(f"{code} (invalid drawing citation format)")
            continue

    if unknowns:
        has_unknown_marker = any("UNKNOWN" in u for u in unknowns)
        if has_unknown_marker:
            return False, f"Station-specific curve radii, vertical gradients, and trackwork lack drawing-level citations ({len(unknowns)} stations marked UNKNOWN)."
        return False, f"Station-specific curve radii, vertical gradients, and trackwork exceed value-level official support ({len(unknowns)} stations unsupported: {', '.join(unknowns[:3])}...)."

    return True, "Station-specific alignment geometry verified from official drawings."


def pred_f014_capex_rates(base: Path) -> tuple[bool, str]:
    lcc_path = base / "08_analysis_ready" / "official_lifecycle_cost_baseline.csv"
    if not lcc_path.is_file():
        return False, "official_lifecycle_cost_baseline.csv missing."
    with lcc_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False, "official_lifecycle_cost_baseline.csv is empty."

    required_cols = {"cost_category", "cost_component", "capex_twd_bn", "capex_evidence_tag", "rates_evidence_tag", "lifecycle_npv_status"}
    if not required_cols.issubset(rows[0].keys()):
        return False, f"official_lifecycle_cost_baseline.csv missing required evidence columns: {sorted(required_cols - set(rows[0].keys()))}."

    capex_rows = [r for r in rows if r.get("capex_evidence_tag") == "OFFICIAL_APPROVED_BUDGET"]
    if not capex_rows:
        return False, "Initial CAPEX budget (NT$ 102.486B) not verified from official Table 12.1-2."

    non_bankable = [
        r.get("cost_component", "")
        for r in rows
        if r.get("lifecycle_npv_status") != "BANKABLE_AUDITED"
    ]
    if non_bankable:
        return False, "Only initial CAPEX budget and appraisal discount rates are verified; 30-year lifecycle NPV is unsubstantiated and non-bankable."

    passed_f009, reason_f009 = pred_f009_lifecycle(base)
    if not passed_f009:
        return False, f"Full lifecycle economics cannot be verified: {reason_f009}"

    return True, "Full lifecycle economics verified with audited bankable cash flow model."



def get_all_requirements() -> list[EvidenceRequirement]:
    return [
        EvidenceRequirement(
            finding_id="F-001",
            severity="HIGH",
            declared_status="OPEN",
            predicate_id="PRED-CATALOG-NO-BLOCKED",
            blocks="FORMAL_OPTIMIZATION",
            title="Data catalog inventories all source files, but retains 4 BLOCKED and 2 REJECTED_AS_WRITTEN sources without traceable replacements.",
            evidence="08_quality_control/data_catalog.csv",
            predicate_fn=pred_f001_catalog,
        ),
        EvidenceRequirement(
            finding_id="F-002",
            severity="CRITICAL",
            declared_status="OPEN",
            predicate_id="PRED-TRACEABILITY-VALUE-LEVEL",
            blocks="FORMAL_OPTIMIZATION",
            title="Value-level engineering traceability across station-specific geometry, crossovers, and risk parameters.",
            evidence="08_quality_control/official_source_citations.csv; 08_quality_control/data_catalog.csv; 08_analysis_ready/official_alignment_geometry.csv",
            predicate_fn=pred_f002_traceability,
        ),
        EvidenceRequirement(
            finding_id="F-003",
            severity="HIGH",
            declared_status="RESOLVED",
            predicate_id="PRED-DEMAND-CALIBRATION",
            blocks="NONE",
            title="Demand calibrated against official Table 6.2-9 and Table 6.2-8 in 08_analysis_ready/official_link_loads.csv.",
            evidence="08_analysis_ready/official_link_loads.csv; 08_analysis_ready/official_station_demand_am_peak.csv",
            predicate_fn=pred_f003_demand,
        ),
        EvidenceRequirement(
            finding_id="F-004",
            severity="CRITICAL",
            declared_status="RESOLVED",
            predicate_id="PRED-SERVICE-BASELINE",
            blocks="NONE",
            title="Official baseline operational service benchmark established in 08_analysis_ready/official_operational_service_baseline.csv (150s CCW supplying 15,600 pphpd).",
            evidence="08_analysis_ready/official_operational_service_baseline.csv",
            predicate_fn=pred_f004_service,
        ),
        EvidenceRequirement(
            finding_id="F-005",
            severity="CRITICAL",
            declared_status="CLOSED_REJECTED",
            predicate_id="PRED-S1-SCREEN-REJECTION",
            blocks="NONE",
            title="S1 is rejected under alternating screen: 360-second plan has negative recovery margin (-62.0s), and screened patterns fail target 10,310 pphpd demand.",
            evidence="08_analysis_ready/single_track_screening.csv; 08_analysis_ready/official_plan_benchmarks.csv",
            predicate_fn=pred_f005_s1_screen,
            default_closed_status="CLOSED_REJECTED",
        ),
        EvidenceRequirement(
            finding_id="F-006",
            severity="CRITICAL",
            declared_status="OPEN",
            predicate_id="PRED-SAFETY-EVACUATION-WORKBOOK",
            blocks="FORMAL_OPTIMIZATION",
            title="Official width/lane design summary from Table 9.1-5, not a reproducible NFPA 130 compliance workbook; derived egress times and PASS determinations are unsupported.",
            evidence="08_analysis_ready/official_station_evacuation_nfpa130.csv",
            predicate_fn=pred_f006_evacuation,
        ),
        EvidenceRequirement(
            finding_id="F-007",
            severity="HIGH",
            declared_status="OPEN",
            predicate_id="PRED-WHOLE-RING-FLEET-CIRCULATION",
            blocks="FORMAL_OPTIMIZATION",
            title="Whole-ring operational concept, fleet circulation, and depot turnarounds lack whole-ring, depot track, block, and interlocking models.",
            evidence="08_analysis_ready/official_operational_service_baseline.csv; 08_analysis_ready/train_event_timetable_approved_baseline.csv",
            predicate_fn=pred_f007_whole_ring,
        ),
        EvidenceRequirement(
            finding_id="F-008",
            severity="HIGH",
            declared_status="OPEN",
            predicate_id="PRED-MICROSIMULATION-TIMETABLE",
            blocks="FORMAL_OPTIMIZATION",
            title="Event timetable covers only 12 East-section stations and short turns Y22-Y38 traverse all 12 stations; lacks whole-ring/depot/block/interlocking models and cannot be called whole-ring microsimulation.",
            evidence="08_analysis_ready/train_event_timetable_approved_baseline.csv",
            predicate_fn=pred_f008_microsimulation,
        ),
        EvidenceRequirement(
            finding_id="F-009",
            severity="HIGH",
            declared_status="OPEN",
            predicate_id="PRED-LIFECYCLE-BANKABLE-NPV",
            blocks="FORMAL_OPTIMIZATION",
            title="Lifecycle cost baseline: bankable 30-year NPV, OPEX, renewals, and salvage are unsubstantiated; arithmetic-only recomputation from unverified unit rates.",
            evidence="08_analysis_ready/official_lifecycle_cost_baseline.csv",
            predicate_fn=pred_f009_lifecycle,
        ),
        EvidenceRequirement(
            finding_id="F-010",
            severity="MEDIUM",
            declared_status="OPEN",
            predicate_id="PRED-RAILML-SCHEMA-XSD",
            blocks="FORMAL_OPTIMIZATION",
            title="railML files are XML well-formed only; no official railML 3.2 XSD schema bundle, validator run, or validation log exists.",
            evidence="08_quality_control/railml_validation_report.md",
            predicate_fn=pred_f010_railml,
        ),
        EvidenceRequirement(
            finding_id="F-011",
            severity="HIGH",
            declared_status="OPEN",
            predicate_id="PRED-CHAINAGE-SCOPE-TRANSFORMATION",
            blocks="FORMAL_OPTIMIZATION",
            title="Route length: 1.482 km discrepancy between model chainage (14.732 km) and published route length (13.250 km) is an unresolved scope discrepancy, not a proven transformation.",
            evidence="08_analysis_ready/official_alignment_geometry.csv; 08_quality_control/official_geometry_crosscheck.csv",
            predicate_fn=pred_f011_scope_transformation,
        ),
        EvidenceRequirement(
            finding_id="F-012",
            severity="MEDIUM",
            declared_status="CLOSED",
            predicate_id="PRED-CF763-CONSTRUCTION-START",
            blocks="NONE",
            title="CF763 construction start date (2024-12-24) verified from official contract notice.",
            evidence="https://www.dorts.gov.taipei/cp.aspx?n=F47E41B6C8884DC6&s=9523DB9FBC46B35B",
            predicate_fn=pred_f012_cf763_start,
            default_closed_status="CLOSED",
        ),
        EvidenceRequirement(
            finding_id="F-013",
            severity="CRITICAL",
            declared_status="OPEN",
            predicate_id="PRED-ALIGNMENT-GEOMETRY-STANDARDS",
            blocks="FORMAL_OPTIMIZATION",
            title="Station-specific curve radii, vertical gradients, and special trackwork exceed value-level official support; detailed station geometry is marked UNKNOWN.",
            evidence="08_analysis_ready/official_alignment_geometry.csv; 08_quality_control/official_geometry_crosscheck.csv",
            predicate_fn=pred_f013_alignment_geometry,
        ),
        EvidenceRequirement(
            finding_id="F-014",
            severity="HIGH",
            declared_status="OPEN",
            predicate_id="PRED-CAPEX-DISCOUNT-RATES",
            blocks="FORMAL_OPTIMIZATION",
            title="Approved CAPEX budget (NT$ 102.486B) and discount rates (3%/4%) verified as narrow facts, but full lifecycle economics remain unverified and non-bankable.",
            evidence="08_analysis_ready/official_lifecycle_cost_baseline.csv; 08_analysis_ready/official_plan_benchmarks.csv",
            predicate_fn=pred_f014_capex_rates,
        ),
    ]


def evaluate_requirements(base: Path) -> list[dict]:
    results = []
    for req in get_all_requirements():
        passed, reason = req.predicate_fn(base)
        # Fail-closed rule: A declared RESOLVED cannot override a failed predicate!
        if passed:
            eval_status = req.default_closed_status
            effective_blocks = "NONE"
        else:
            eval_status = "OPEN"
            effective_blocks = req.blocks

        results.append({
            "finding_id": req.finding_id,
            "severity": req.severity,
            "declared_status": req.declared_status,
            "evaluated_status": eval_status,
            "status": eval_status,  # Backwards compatibility alias
            "predicate_id": req.predicate_id,
            "blocks": effective_blocks,
            "finding": req.title,
            "evidence": req.evidence,
            "predicate_passed": passed,
            "predicate_reason": reason,
        })
    return results
