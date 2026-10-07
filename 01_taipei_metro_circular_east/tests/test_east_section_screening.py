#!/usr/bin/env python3
"""Unit tests for the East-Section Preliminary Capacity Screening Engine."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.run_east_section_screening import (
    EAST_SECTION_NODES,
    NOMINAL_CAR_CAPACITY_PAX,
    STATUS_FAIL,
    STATUS_PASS,
    classify_vc,
    evaluate_contiguous_sections,
    evaluate_double_track_links,
    generate_representative_occupations,
    load_and_validate_boundary_conditions,
    load_and_validate_link_loads,
    load_and_validate_named_alternatives,
    load_and_validate_scenarios,
    load_tb02_service,
    run_screening,
)
from scripts.verify_east_section_screening import ScreeningVerifier


def file_sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestEastSectionScreening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = BASE_DIR
        cls.inputs_dir = cls.base_dir / "09_preliminary_screening" / "inputs"
        cls.outputs_dir = cls.base_dir / "09_preliminary_screening" / "outputs"
        cls.analysis_ready = cls.base_dir / "08_analysis_ready"

        # Load reference inputs
        cls.links = load_and_validate_link_loads(cls.analysis_ready / "official_link_loads.csv")
        cls.tb02 = load_tb02_service(cls.analysis_ready / "official_operational_service_baseline.csv")
        cls.scenarios = load_and_validate_scenarios(cls.inputs_dir / "screening_scenarios.csv")
        cls.named_alts = load_and_validate_named_alternatives(cls.inputs_dir / "named_alternatives.csv")
        cls.boundary = load_and_validate_boundary_conditions(cls.inputs_dir / "boundary_conditions.csv")

    def test_exact_boundary_set(self):
        """Test corridor nodes are exactly Y29..Y01 (12 nodes, 11 links) and external propagation is NOT_MODELED."""
        expected_nodes = ("Y29", "Y30", "Y31", "Y32", "Y33", "Y34", "Y35", "Y36", "Y37", "Y38", "Y39", "Y01")
        self.assertEqual(EAST_SECTION_NODES, expected_nodes)
        self.assertEqual(len(self.links), 11)

        # Verify boundary conditions file specifies these nodes and NOT_MODELED propagation
        nodes_in_file = tuple(n.strip() for n in self.boundary["CORRIDOR_NODES"].split(","))
        self.assertEqual(nodes_in_file, expected_nodes)
        self.assertEqual(self.boundary["EXTERNAL_PROPAGATION"], "NOT_MODELED")
        self.assertEqual(self.boundary["PASSING_LOOPS"], "NOT_MODELED")
        self.assertEqual(self.boundary["CORRIDOR_BOUNDARIES"], "Y29,Y01")

    def test_baseline_capacity_values_tb02(self):
        """Test baseline capacity: 15600 CCW and ~11818.18 CW."""
        # CCW: headway 150s -> tph = 24.0 -> capacity = 24 * 650 = 15600.0
        self.assertEqual(self.tb02["headway_ccw_s"], 150.0)
        tph_ccw = 3600.0 / self.tb02["headway_ccw_s"]
        self.assertEqual(tph_ccw, 24.0)
        cap_ccw = tph_ccw * NOMINAL_CAR_CAPACITY_PAX
        self.assertEqual(cap_ccw, 15600.0)

        # CW: headway 198s -> tph = 18.1818... -> capacity = ~11818.18
        self.assertEqual(self.tb02["headway_cw_s"], 198.0)
        tph_cw = 3600.0 / self.tb02["headway_cw_s"]
        self.assertAlmostEqual(tph_cw, 18.181818, places=4)
        cap_cw = tph_cw * NOMINAL_CAR_CAPACITY_PAX
        self.assertAlmostEqual(cap_cw, 11818.1818, places=2)

    def test_direction_correction_lk07(self):
        """Test direction correction: stored links run CW; LK07 CCW is actual Y36->Y35 at 15250 pphpd."""
        eval_rows = evaluate_double_track_links(self.links, self.scenarios, self.tb02)
        s00_lk07_ccw = next(
            r for r in eval_rows
            if r["scenario_id"] == "S00" and r["link_id"] == "LK07" and r["direction"] == "CCW"
        )
        self.assertEqual(s00_lk07_ccw["movement_from"], "Y36")
        self.assertEqual(s00_lk07_ccw["movement_to"], "Y35")
        self.assertEqual(float(s00_lk07_ccw["official_flow_pphpd"]), 15250.0)
        self.assertEqual(float(s00_lk07_ccw["screened_demand_pphpd"]), 15250.0)
        self.assertEqual(s00_lk07_ccw["vc_band"], "TIGHT")
        self.assertEqual(s00_lk07_ccw["screening_status"], STATUS_PASS)

        s00_lk07_cw = next(
            r for r in eval_rows
            if r["scenario_id"] == "S00" and r["link_id"] == "LK07" and r["direction"] == "CW"
        )
        self.assertEqual(s00_lk07_cw["movement_from"], "Y35")
        self.assertEqual(s00_lk07_cw["movement_to"], "Y36")
        self.assertEqual(float(s00_lk07_cw["official_flow_pphpd"]), 5640.0)
        self.assertEqual(s00_lk07_cw["vc_band"], "COMFORTABLE")
        self.assertEqual(s00_lk07_cw["screening_status"], STATUS_PASS)

    def test_regression_benchmark_y39_y01_s00(self):
        """Test regression: Y39-Y01 S00 cycle=193+193+36+60=482s, capacity 4854.77 pphpd, demand 10310, FAIL_CAPACITY."""
        eval_rows = evaluate_contiguous_sections(self.links, self.scenarios, self.named_alts)
        y39_s00 = next(
            r for r in eval_rows
            if r["scenario_id"] == "S00" and r["section_id"] == "Y39-Y01"
        )
        self.assertEqual(float(y39_s00["t_cw_s"]), 193.0)
        self.assertEqual(float(y39_s00["t_ccw_s"]), 193.0)
        self.assertEqual(float(y39_s00["boundary_change_total_s"]), 36.0)
        self.assertEqual(float(y39_s00["recovery_s"]), 60.0)
        self.assertEqual(float(y39_s00["cycle_s"]), 482.0)
        self.assertEqual(float(y39_s00["effective_capacity_pphpd"]), 4854.77)
        self.assertEqual(float(y39_s00["ccw_screened_demand_pphpd"]), 10310.0)
        self.assertEqual(y39_s00["screening_status"], STATUS_FAIL)
        self.assertEqual(y39_s00["vc_band"], "FAIL")

    def test_both_directions_pass_rule(self):
        """Test both directions must pass rule: if either CW or CCW > 1.0, status must be FAIL_CAPACITY."""
        # 1. Test helper classify_vc
        self.assertEqual(classify_vc(0.50), ("COMFORTABLE", STATUS_PASS))
        self.assertEqual(classify_vc(0.85), ("COMFORTABLE", STATUS_PASS))
        self.assertEqual(classify_vc(0.86), ("TIGHT", STATUS_PASS))
        self.assertEqual(classify_vc(1.00), ("TIGHT", STATUS_PASS))
        self.assertEqual(classify_vc(1.01), ("FAIL", STATUS_FAIL))

        # 2. Check in evaluated section rows
        eval_rows = evaluate_contiguous_sections(self.links, self.scenarios, self.named_alts)
        for r in eval_rows:
            vc_cw = float(r["vc_cw"])
            vc_ccw = float(r["vc_ccw"])
            max_vc = float(r["max_vc"])
            self.assertEqual(max_vc, max(vc_cw, vc_ccw))
            if vc_cw <= 1.0 and vc_ccw <= 1.0:
                self.assertEqual(r["screening_status"], STATUS_PASS)
            else:
                self.assertEqual(r["screening_status"], STATUS_FAIL)

        # 3. Test synthetic case where CW passes but CCW fails
        synthetic_links = [dict(lk) for lk in self.links]
        synthetic_links[0]["flow_clockwise_to_zoo_pphpd"] = 1000.0   # low demand (passes)
        synthetic_links[0]["flow_counterclockwise_to_jiannan_pphpd"] = 25000.0  # high demand (fails)
        res = evaluate_contiguous_sections(synthetic_links, [self.scenarios[0]], {})
        first_sec = res[0]
        self.assertLessEqual(float(first_sec["vc_cw"]), 1.0)
        self.assertGreater(float(first_sec["vc_ccw"]), 1.0)
        self.assertEqual(first_sec["screening_status"], STATUS_FAIL)

    def test_all_66_contiguous_intervals_evaluated(self):
        """Test all 66 contiguous single-track intervals and 4 named alternatives are evaluated."""
        eval_rows = evaluate_contiguous_sections(self.links, self.scenarios, self.named_alts)
        s00_rows = [r for r in eval_rows if r["scenario_id"] == "S00"]
        self.assertEqual(len(s00_rows), 66)

        sections = {r["section_id"] for r in s00_rows}
        self.assertEqual(len(sections), 66)

        # Check the 4 named alternatives
        for alt_id in ("Y39-Y01", "Y35-Y36", "Y30-Y33", "Y38-Y01"):
            self.assertIn(alt_id, sections)
            alt_row = next(r for r in s00_rows if r["section_id"] == alt_id)
            self.assertEqual(alt_row["is_named_alternative"], "YES")
            self.assertEqual(alt_row["passing_loops_modeled"], "NOT_MODELED")

    def test_monotonicity(self):
        """Test monotonicity across demand, load factor, runtime, dwell, change, and recovery."""
        eval_rows = evaluate_contiguous_sections(self.links, self.scenarios, self.named_alts)
        by_sec_sc = {(r["section_id"], r["scenario_id"]): r for r in eval_rows}
        all_sections = {r["section_id"] for r in eval_rows}

        for sec in all_sections:
            # 1. Demand monotonicity: S01 (dm=1.0) vs S02 (dm=1.1)
            vc_s01 = float(by_sec_sc[(sec, "S01")]["max_vc"])
            vc_s02 = float(by_sec_sc[(sec, "S02")]["max_vc"])
            self.assertGreaterEqual(vc_s02, vc_s01 - 1e-7)

            # 2. Usable load factor monotonicity: S01 (load=0.9) vs S06 (load=0.7)
            cap_s01 = float(by_sec_sc[(sec, "S01")]["effective_capacity_pphpd"])
            cap_s06 = float(by_sec_sc[(sec, "S06")]["effective_capacity_pphpd"])
            self.assertLessEqual(cap_s06, cap_s01 + 1e-7)

            # 3. Dwell/runtime/switch/recovery cycle monotonicity: S00 (baseline) vs S03 (stressed)
            cyc_s00 = float(by_sec_sc[(sec, "S00")]["cycle_s"])
            cyc_s03 = float(by_sec_sc[(sec, "S03")]["cycle_s"])
            self.assertGreaterEqual(cyc_s03, cyc_s00)

    def test_nonoverlapping_representative_occupations(self):
        """Test that representative section occupations are strictly non-overlapping."""
        occupations = generate_representative_occupations(self.links, self.named_alts, self.scenarios)
        self.assertGreater(len(occupations), 0)

        sections = sorted(list({r["section_id"] for r in occupations}))
        self.assertEqual(set(sections), {"Y39-Y01", "Y35-Y36", "Y30-Y33", "Y38-Y01"})

        for sec in sections:
            sec_rows = [r for r in occupations if r["section_id"] == sec]
            sec_rows.sort(key=lambda r: float(r["entry_sec_am_peak"]))
            for i in range(len(sec_rows) - 1):
                exit_k = float(sec_rows[i]["exit_sec_am_peak"])
                entry_k1 = float(sec_rows[i + 1]["entry_sec_am_peak"])
                # Must be strictly non-overlapping
                self.assertGreaterEqual(
                    entry_k1, exit_k,
                    f"Overlap detected in section {sec} between trip {sec_rows[i]['trip_id']} and {sec_rows[i+1]['trip_id']}"
                )

    def test_infrastructure_unverified_positive_outcomes(self):
        """Test positive screening outcomes always carry PRELIMINARY_CAPACITY_PASS_INFRASTRUCTURE_UNVERIFIED."""
        eval_sections = evaluate_contiguous_sections(self.links, self.scenarios, self.named_alts)
        eval_links = evaluate_double_track_links(self.links, self.scenarios, self.tb02)

        for r in eval_sections:
            if float(r["max_vc"]) <= 1.0:
                self.assertEqual(r["screening_status"], STATUS_PASS)
            else:
                self.assertEqual(r["screening_status"], STATUS_FAIL)

        for r in eval_links:
            if float(r["vc_ratio"]) <= 1.0:
                self.assertEqual(r["screening_status"], STATUS_PASS)
            else:
                self.assertEqual(r["screening_status"], STATUS_FAIL)

    def test_source_catalog_exactly_36_and_domains_01_07(self):
        """Test data catalog contains strictly 36 source data files from 01_ through 07_."""
        catalog_path = self.base_dir / "08_quality_control" / "data_catalog.csv"
        with catalog_path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 36)
        expected_domains = {
            "01_alignment_topology", "02_tunnel_civil", "03_rolling_stock_signalling",
            "04_service_operations", "05_demand_ridership", "06_lifecycle_costs",
            "07_risk_safety_regulations"
        }
        for r in rows:
            domain = r["file_path"].split("/")[0]
            self.assertIn(domain, expected_domains)
            self.assertFalse(r["file_path"].startswith("09_preliminary_screening"))

    def test_readiness_blockers_unchanged(self):
        """Test that preliminary analysis readiness remains READY_FOR_PRELIMINARY_SCREENING_ONLY with 10 open blockers."""
        cmd = [sys.executable, str(self.base_dir / "scripts" / "verify_analysis_readiness.py")]
        proc = subprocess.run(cmd, cwd=self.base_dir, capture_output=True, text=True)
        # Expected exit code 1 because 10 blockers remain open
        self.assertEqual(proc.returncode, 1)
        self.assertIn("READY_FOR_PRELIMINARY_SCREENING_ONLY", proc.stdout)
        self.assertIn("Open blocking requirements: 10", proc.stdout)
        for f_id in ("F-001", "F-002", "F-006", "F-007", "F-008", "F-009", "F-010", "F-011", "F-013", "F-014"):
            self.assertIn(f_id, proc.stdout)

    def test_deterministic_rerun_and_temporary_outputs_no_mutations(self):
        """Test that runner can write to temporary directory without mutating repo and outputs are byte-identical."""
        output_files = [
            "link_capacity_screen.csv",
            "section_capacity_screen.csv",
            "representative_section_occupations.csv",
            "screening_summary.json",
        ]
        repo_digests = {fn: file_sha256(self.outputs_dir / fn) for fn in output_files}

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_out = Path(tmpdir)
            run_screening(base_dir=self.base_dir, output_dir=tmp_out)

            tmp_digests = {fn: file_sha256(tmp_out / fn) for fn in output_files}
            for fn in output_files:
                self.assertEqual(
                    repo_digests[fn], tmp_digests[fn],
                    f"Rerun output differs for {fn}"
                )

    def test_hard_fail_malformed_inputs(self):
        """Test hard fail on malformed, out-of-bound, or missing input files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            bad_scenarios = tmp_path / "bad_scenarios.csv"
            # Write invalid negative dwell
            bad_scenarios.write_text(
                "scenario_id,demand_multiplier,usable_load_factor,runtime_multiplier,dwell_s,change_s,recovery_s\n"
                "S99,1.0,1.0,1.0,-10.0,18.0,60.0\n"
            )
            with self.assertRaises(ValueError):
                load_and_validate_scenarios(bad_scenarios)

            # Write out of bound usable_load_factor (> 1.5)
            bad_scenarios.write_text(
                "scenario_id,demand_multiplier,usable_load_factor,runtime_multiplier,dwell_s,change_s,recovery_s\n"
                "S99,1.0,2.5,1.0,30.0,18.0,60.0\n"
            )
            with self.assertRaises(ValueError):
                load_and_validate_scenarios(bad_scenarios)

            # Write invalid boundary nodes
            bad_bc = tmp_path / "bad_bc.csv"
            bad_bc.write_text(
                "parameter_id,parameter_name,parameter_value\n"
                "CORRIDOR_NODES,East Section Corridor Stations,\"Y29,Y30,BAD_NODE\"\n"
                "CORRIDOR_BOUNDARIES,Corridor Boundary Ingress/Egress,\"Y29,Y01\"\n"
                "TIME_WINDOW,Analysis Operational Window,07:00-09:00\n"
                "HEADWAY_CCW_S,Baseline Headway CCW,150\n"
                "HEADWAY_CW_S,Baseline Headway CW,198\n"
                "NOMINAL_TRAIN_CAPACITY_PAX,Train Nominal Capacity,650\n"
                "DIRECTION_CORRECTION_RULE,Link Directional Mapping,STORED_CW_REVERSE_CCW\n"
                "EXTERNAL_PROPAGATION,External Network Propagation,NOT_MODELED\n"
                "PASSING_LOOPS,Intermediate Passing Siding Loops,NOT_MODELED\n"
            )
            with self.assertRaises(ValueError):
                load_and_validate_boundary_conditions(bad_bc)


if __name__ == "__main__":
    unittest.main()
