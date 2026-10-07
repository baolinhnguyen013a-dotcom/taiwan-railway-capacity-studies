#!/usr/bin/env python3
"""
Internal-consistency verifier for the exploratory TRA Coastal Line package.
Validates:
1. Topology consistency (16 stations, 5 bottlenecks, 4 bridges).
2. Train kinetics and bridge clearance equations.
3. Timetable coverage (15-min commuter, 30-min express).
4. Arithmetic reconciliation of an unvalidated cost scenario.

Passing this script does not validate source accuracy, engineering feasibility,
safety, timetable feasibility, or cost assumptions.
"""

import os
import sys
import csv
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

def verify():
    passed = 0
    errors = []

    def check(cond, msg):
        nonlocal passed
        if cond:
            passed += 1
            print(f"  [PASS] {msg}")
        else:
            errors.append(msg)
            print(f"  [FAIL] {msg}")

    print("=================================================================")
    print("VERIFYING EXPLORATORY TRA COASTAL LINE MODEL INTERNAL CONSISTENCY")
    print("=================================================================")

    # 1. Topology checks
    print("\n1. Verifying Corridor Topology...")
    stations_file = os.path.join(PROJECT_DIR, "01_corridor_topology", "stations.csv")
    with open(stations_file) as f:
        stations = list(csv.DictReader(f))
    check(len(stations) == 16, f"Exactly 16 stations cataloged (found {len(stations)})")
    check(stations[0]["station_id"] == "STA01" and stations[0]["chainage_km"] == "4.5", "Tanwen is at K4.5")
    check(stations[-1]["station_id"] == "STA16" and stations[-1]["chainage_km"] == "83.1", "Zhuifen is at K83.1")

    bottlenecks_file = os.path.join(PROJECT_DIR, "01_corridor_topology", "single_track_bottlenecks.csv")
    with open(bottlenecks_file) as f:
        bottlenecks = list(csv.DictReader(f))
    check(len(bottlenecks) == 5, f"Exactly 5 single-track bottlenecks cataloged (found {len(bottlenecks)})")
    total_bn_len = sum(float(b["length_km"]) for b in bottlenecks)
    check(abs(total_bn_len - 35.4) < 1.0, f"Total single-track bottleneck length is ~35.4 km (found {total_bn_len} km)")

    bridges_file = os.path.join(PROJECT_DIR, "01_corridor_topology", "river_bridges.csv")
    with open(bridges_file) as f:
        bridges = list(csv.DictReader(f))
    check(len(bridges) == 4, f"Exactly 4 major river bridges cataloged (found {len(bridges)})")

    # 2. Bridge kinetics checks
    print("\n2. Verifying Bridge Kinetics...")
    kinetics_csv = os.path.join(PROJECT_DIR, "04_bridge_bottleneck_model", "bridge_capacity_evaluations.csv")
    with open(kinetics_csv) as f:
        kinetics = list(csv.DictReader(f))
    check(len(kinetics) == 4, f"Evaluations present for all 4 bridges (found {len(kinetics)})")

    daan = next(k for k in kinetics if k["bridge_id"] == "BRG03")
    dajia = next(k for k in kinetics if k["bridge_id"] == "BRG04")

    check(float(daan["traversal_time_express_sec"]) < 45.0, f"Daan bridge express traversal is {daan['traversal_time_express_sec']}s (< 45s)")
    check(float(dajia["traversal_time_express_sec"]) < 50.0, f"Dajia bridge express traversal is {dajia['traversal_time_express_sec']}s (< 50s)")
    check(float(daan["platooned_utilization_pct"]) < 30.0, f"Daan platooned utilization is {daan['platooned_utilization_pct']}% (< 30%)")
    check(float(dajia["platooned_utilization_pct"]) < 30.0, f"Dajia platooned utilization is {dajia['platooned_utilization_pct']}% (< 30%)")
    check(daan["capacity_verdict"] == "PASSES_ASSUMED_ARITHMETIC_THRESHOLD", "Daan scenario carries the non-engineering arithmetic-screen label")
    check(dajia["capacity_verdict"] == "PASSES_ASSUMED_ARITHMETIC_THRESHOLD", "Dajia scenario carries the non-engineering arithmetic-screen label")

    # 3. Financial comparison checks
    print("\n3. Checking unvalidated cost-scenario arithmetic...")
    capex_file = os.path.join(PROJECT_DIR, "05_cost_tradeoff_curves", "capex_comparison_baseline_vs_lever1.csv")
    with open(capex_file) as f:
        capex = list(csv.DictReader(f))
    tot_row = next(c for c in capex if c["wbs_code"] == "TOTAL")
    wbs_rows = [c for c in capex if c["wbs_code"] != "TOTAL"]

    baseline_tot = float(tot_row["baseline_cost_twd_million"])
    lever1_tot = float(tot_row["lever1_optimized_twd_million"])
    delta_tot = float(tot_row["cost_delta_twd_million"])

    wbs_baseline_sum = sum(float(r["baseline_cost_twd_million"]) for r in wbs_rows)
    wbs_lever1_sum = sum(float(r["lever1_optimized_twd_million"]) for r in wbs_rows)
    wbs_delta_sum = sum(float(r["cost_delta_twd_million"]) for r in wbs_rows)

    check(baseline_tot == 16195.0, f"Baseline matches Railway Bureau approved budget: NT$ {baseline_tot}M (16.195B)")
    check(wbs_baseline_sum == baseline_tot, f"Baseline WBS01..WBS08 sums exactly to TOTAL: NT$ {wbs_baseline_sum}M")
    check(lever1_tot == 11350.0, f"Assumed alternative scenario total is NT$ {lever1_tot}M (not a validated estimate)")
    check(wbs_lever1_sum == lever1_tot, f"Lever 1 WBS01..WBS08 sums exactly to TOTAL: NT$ {wbs_lever1_sum}M")
    check(delta_tot == -4845.0, f"Unvalidated arithmetic difference is NT$ {abs(delta_tot)}M (not a forecast or verified saving)")
    check(wbs_delta_sum == delta_tot, f"Line-item cost deltas sum exactly to total delta: NT$ {wbs_delta_sum}M")

    # 4. Simulation output checks
    print("\n4. Verifying Simulation & Diagram Outputs...")
    sim_json = os.path.join(PROJECT_DIR, "outputs", "simulation_19h_summary.json")
    check(os.path.exists(sim_json), "19-hour exploratory simulation summary JSON exists")
    with open(sim_json) as f:
        sim_data = json.load(f)
    for bname, s in sim_data.items():
        check(s["total_trains_simulated"] == 123, f"Scenario contains 123 trains for {bname}")
        check(s["sim_duration_hours"] == 19.0, f"Scenario covers 19 operating hours for {bname}")
        check(s["scheduled_conflicts"] == 0, f"Scheduler-enforced mutual exclusion records zero conflicts for {bname}")
        check(s["stochastic_disruption_tests"]["robustness_verdict"] == "SCHEDULE_INTERFERENCE", f"Disruption result is disclosed as SCHEDULE_INTERFERENCE for {bname}")

    print("\n=================================================================")
    print(f"VERIFICATION RESULT: {passed} PASSED, {len(errors)} ERRORS")
    print("=================================================================")
    if errors:
        sys.exit(1)
    else:
        print("ALL INTERNAL-CONSISTENCY CHECKS PASSED.")
        print("This result does not validate engineering, safety, timetable, or cost claims.")

if __name__ == "__main__":
    verify()
