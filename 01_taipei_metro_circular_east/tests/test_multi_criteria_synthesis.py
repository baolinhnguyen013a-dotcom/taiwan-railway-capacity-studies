#!/usr/bin/env python3
"""Unit tests for Phase 10: Multi-Criteria Synthesis."""

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

from scripts.run_multi_criteria_synthesis import (
    EXPECTED_COLUMNS,
    NOTE_BASELINE_FEASIBLE,
    NOTE_SINGLE_TRACK_REJECTED,
    STATUS_FAIL,
    STATUS_PASS_BASELINE,
    VERDICT_APPROVED_BASELINE,
    VERDICT_REJECTED,
    evaluate_synthesis,
    load_lifecycle_costs,
    load_named_alternatives,
    load_screening_summary,
    run_synthesis,
)


def file_sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestMultiCriteriaSynthesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = BASE_DIR
        cls.p10_dir = cls.base_dir / "10_multi_criteria_synthesis"
        cls.outputs_dir = cls.p10_dir / "outputs"
        cls.inputs_09 = cls.base_dir / "09_preliminary_screening" / "inputs"
        cls.outputs_09 = cls.base_dir / "09_preliminary_screening" / "outputs"
        cls.inputs_06 = cls.base_dir / "06_lifecycle_costs"

        cls.screening_summary = load_screening_summary(cls.outputs_09 / "screening_summary.json")
        cls.named_alts_by_ref = load_named_alternatives(cls.inputs_09 / "named_alternatives.csv")
        cls.lifecycle_rows = load_lifecycle_costs(cls.inputs_06 / "lifecycle_cost_comparison_30yr.csv")

    def test_inputs_existence_and_parsing(self):
        """Test that all three Phase 10 required input files exist and parse with correct counts."""
        self.assertEqual(len(self.lifecycle_rows), 5)
        self.assertEqual(len(self.named_alts_by_ref), 4)
        self.assertIn("named_alternatives_evaluation", self.screening_summary)

        # Confirm named alternatives in screening summary match named_alts_by_ref
        named_eval = self.screening_summary["named_alternatives_evaluation"]
        for ref_id, alt_row in self.named_alts_by_ref.items():
            sec_id = alt_row["alternative_id"]
            self.assertIn(sec_id, named_eval)
            self.assertIn("S00", named_eval[sec_id])

    def test_cross_domain_mapping(self):
        """Test cross-domain mapping between 06_lifecycle_costs and 09_preliminary_screening."""
        eval_rows, summary = evaluate_synthesis(
            self.lifecycle_rows, self.named_alts_by_ref, self.screening_summary
        )
        self.assertEqual(len(eval_rows), 5)

        mapping = {r["alternative_id"]: (r["candidate_reference_id"], r["section_id"]) for r in eval_rows}
        self.assertEqual(mapping["BL-Double"], ("BL-Double", "Baseline Double-Track"))
        self.assertEqual(mapping["ALT-S1"], ("S1", "Y39-Y01"))
        self.assertEqual(mapping["ALT-S2"], ("S2", "Y35-Y36"))
        self.assertEqual(mapping["ALT-S3"], ("S3", "Y30-Y33"))
        self.assertEqual(mapping["ALT-S4"], ("S4", "Y38-Y01"))

    def test_empirical_capacity_failure_overrides_economic_claims(self):
        """Test that empirical capacity failures under S00 override 'Optimal Alternative' and 'Strong Contender' claims."""
        eval_rows, summary = evaluate_synthesis(
            self.lifecycle_rows, self.named_alts_by_ref, self.screening_summary
        )

        by_id = {r["alternative_id"]: r for r in eval_rows}

        # ALT-S1 originally claimed "Optimal Alternative: Saves NT$ 5.85B..."
        s1 = by_id["ALT-S1"]
        self.assertIn("Optimal Alternative", s1["original_economic_claim"])
        self.assertEqual(s1["capacity_status_s00"], STATUS_FAIL)
        self.assertEqual(s1["max_vc_s00"], "2.1237")
        self.assertGreater(float(s1["max_vc_s00"]), 1.0)
        self.assertEqual(s1["synthesis_verdict"], VERDICT_REJECTED)
        self.assertEqual(s1["governance_note"], NOTE_SINGLE_TRACK_REJECTED)

        # ALT-S4 originally claimed "Strong Contender: Extends single track..."
        s4 = by_id["ALT-S4"]
        self.assertIn("Strong Contender", s4["original_economic_claim"])
        self.assertEqual(s4["capacity_status_s00"], STATUS_FAIL)
        self.assertEqual(s4["max_vc_s00"], "3.4079")
        self.assertGreater(float(s4["max_vc_s00"]), 1.0)
        self.assertEqual(s4["synthesis_verdict"], VERDICT_REJECTED)
        self.assertEqual(s4["governance_note"], NOTE_SINGLE_TRACK_REJECTED)

        # ALT-S2 and ALT-S3
        for alt_id in ("ALT-S2", "ALT-S3"):
            row = by_id[alt_id]
            self.assertEqual(row["capacity_status_s00"], STATUS_FAIL)
            self.assertGreater(float(row["max_vc_s00"]), 1.0)
            self.assertEqual(row["synthesis_verdict"], VERDICT_REJECTED)
            self.assertEqual(row["governance_note"], NOTE_SINGLE_TRACK_REJECTED)

        # Check summary aggregated disposition tracks exactly 2 overridden claims
        disp = summary["aggregated_disposition"]
        self.assertEqual(disp["overridden_economic_claims_count"], 2)
        overridden_ids = [c["alternative_id"] for c in disp["overridden_economic_claims"]]
        self.assertEqual(overridden_ids, ["ALT-S1", "ALT-S4"])

    def test_baseline_double_track_feasibility(self):
        """Test that BL-Double baseline is verified feasible and approved."""
        eval_rows, summary = evaluate_synthesis(
            self.lifecycle_rows, self.named_alts_by_ref, self.screening_summary
        )
        by_id = {r["alternative_id"]: r for r in eval_rows}
        bl = by_id["BL-Double"]

        self.assertEqual(bl["synthesis_verdict"], VERDICT_APPROVED_BASELINE)
        self.assertEqual(bl["capacity_status_s00"], STATUS_PASS_BASELINE)
        self.assertEqual(bl["max_vc_s00"], "0.9776")
        self.assertLessEqual(float(bl["max_vc_s00"]), 1.0)
        self.assertEqual(bl["governance_note"], NOTE_BASELINE_FEASIBLE)

    def test_csv_and_json_deliverables_schema_and_values(self):
        """Test synthesis_evaluation.csv and synthesis_summary.json structure and values."""
        csv_path = self.outputs_dir / "synthesis_evaluation.csv"
        self.assertTrue(csv_path.is_file())

        with csv_path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 5)
        self.assertEqual(list(rows[0].keys()), EXPECTED_COLUMNS)

        json_path = self.outputs_dir / "synthesis_summary.json"
        self.assertTrue(json_path.is_file())

        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        disp = data["aggregated_disposition"]
        self.assertEqual(disp["total_alternatives_evaluated"], 5)
        self.assertEqual(disp["single_track_candidates_evaluated"], 4)
        self.assertEqual(disp["single_track_rejected_capacity_failure"], 4)
        self.assertEqual(disp["single_track_approved"], 0)
        self.assertEqual(disp["baseline_approved"], 1)

    def test_deterministic_rerun_and_temporary_outputs_no_mutations(self):
        """Test that running synthesis in a temporary directory produces byte-identical outputs."""
        csv_path = self.outputs_dir / "synthesis_evaluation.csv"
        json_path = self.outputs_dir / "synthesis_summary.json"

        csv_hash = file_sha256(csv_path)
        json_hash = file_sha256(json_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_out = Path(tmpdir)
            run_synthesis(base_dir=self.base_dir, output_dir=tmp_out)

            self.assertEqual(file_sha256(tmp_out / "synthesis_evaluation.csv"), csv_hash)
            self.assertEqual(file_sha256(tmp_out / "synthesis_summary.json"), json_hash)

    def test_error_handling_missing_and_malformed_inputs(self):
        """Test error handling when inputs are missing or malformed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Test missing file raises FileNotFoundError
            with self.assertRaises(FileNotFoundError):
                load_screening_summary(tmp_path / "nonexistent.json")

            with self.assertRaises(FileNotFoundError):
                load_named_alternatives(tmp_path / "nonexistent.csv")

            with self.assertRaises(FileNotFoundError):
                load_lifecycle_costs(tmp_path / "nonexistent.csv")

            # Test malformed lifecycle costs missing required column
            bad_lcc = tmp_path / "bad_lcc.csv"
            bad_lcc.write_text("alternative_id,initial_capex_twd_billion\nALT-S1,102.65\n")
            with self.assertRaises(ValueError):
                load_lifecycle_costs(bad_lcc)

    def test_strict_invariants_source_snapshot_and_screening_untouched(self):
        """Test that 36 source files in 01-07 and all 09 screening files remain strictly intact."""
        # Check source snapshot
        snap_cmd = [sys.executable, str(self.base_dir / "scripts" / "verify_source_snapshot.py")]
        proc = subprocess.run(snap_cmd, cwd=self.base_dir, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("exactly 36 source data files match", proc.stdout)

        # Check screening verifier
        screen_cmd = [sys.executable, str(self.base_dir / "scripts" / "verify_east_section_screening.py")]
        proc = subprocess.run(screen_cmd, cwd=self.base_dir, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)

    def test_readiness_blockers_strictly_preserved(self):
        """Test that readiness gate remains READY_FOR_PRELIMINARY_SCREENING_ONLY with exactly 10 open blockers."""
        cmd = [sys.executable, str(self.base_dir / "scripts" / "verify_analysis_readiness.py")]
        proc = subprocess.run(cmd, cwd=self.base_dir, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("READY_FOR_PRELIMINARY_SCREENING_ONLY", proc.stdout)
        self.assertIn("Open blocking requirements: 10", proc.stdout)
        for blocker in ("F-001", "F-002", "F-006", "F-007", "F-008", "F-009", "F-010", "F-011", "F-013", "F-014"):
            self.assertIn(blocker, proc.stdout)


if __name__ == "__main__":
    unittest.main()
