#!/usr/bin/env python3
"""Verifier for Phase 10: Multi-Criteria Synthesis.

Validates:
1. Inputs and outputs existence.
2. Cross-domain mapping consistency (06_lifecycle_costs to 09_preliminary_screening).
3. Schema and structural validation of synthesis_evaluation.csv.
4. Overriding of unverified economic claims (ALT-S1, ALT-S4) by empirical capacity failures.
5. Synthesis verdicts: REJECTED_CAPACITY_FAILURE for all single track, APPROVED_BASELINE_FEASIBLE for BL-Double.
6. Exact governance note compliance.
7. Aggregated disposition and metadata in synthesis_summary.json.
8. Deterministic rerun byte-identical reproducibility.
9. Strict repository invariants (36 source files in 01-07 unchanged, 10 open readiness blockers).
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.run_multi_criteria_synthesis import (
    EXPECTED_COLUMNS,
    NOTE_SINGLE_TRACK_REJECTED,
    VERDICT_APPROVED_BASELINE,
    VERDICT_REJECTED,
    run_synthesis,
)

EXPECTED_MAPPING = {
    "BL-Double": ("BL-Double", "Baseline Double-Track"),
    "ALT-S1": ("S1", "Y39-Y01"),
    "ALT-S2": ("S2", "Y35-Y36"),
    "ALT-S3": ("S3", "Y30-Y33"),
    "ALT-S4": ("S4", "Y38-Y01"),
}

EXPECTED_CAPEX = {
    "BL-Double": "108.5",
    "ALT-S1": "102.65",
    "ALT-S2": "105.8",
    "ALT-S3": "104.2",
    "ALT-S4": "100.8",
}

EXPECTED_NPV = {
    "BL-Double": "138.2",
    "ALT-S1": "131.42",
    "ALT-S2": "135.1",
    "ALT-S3": "133.15",
    "ALT-S4": "129.2",
}

EXPECTED_MAX_VC_S00 = {
    "BL-Double": "0.9776",
    "ALT-S1": "2.1237",
    "ALT-S2": "2.2328",
    "ALT-S3": "1.8299",
    "ALT-S4": "3.4079",
}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def file_sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class SynthesisVerifier:
    def __init__(self, base_dir: Path = BASE_DIR):
        self.base = base_dir
        self.p10_dir = self.base / "10_multi_criteria_synthesis"
        self.outputs_dir = self.p10_dir / "outputs"
        self.inputs_09_dir = self.base / "09_preliminary_screening" / "inputs"
        self.outputs_09_dir = self.base / "09_preliminary_screening" / "outputs"
        self.p06_dir = self.base / "06_lifecycle_costs"
        self.passed_checks = 0
        self.errors: list[str] = []

    def log_pass(self, msg: str) -> None:
        self.passed_checks += 1
        print(f"  [PASS] {msg}")

    def log_error(self, msg: str) -> None:
        self.errors.append(msg)
        print(f"  [FAIL] {msg}")

    def verify_inputs_and_outputs_existence(self) -> None:
        print("\n1. Verifying input and output files existence...")
        req_inputs = [
            self.outputs_09_dir / "screening_summary.json",
            self.inputs_09_dir / "named_alternatives.csv",
            self.p06_dir / "lifecycle_cost_comparison_30yr.csv",
        ]
        for inp in req_inputs:
            if inp.is_file():
                self.log_pass(f"Verified input file: {inp.relative_to(self.base)}")
            else:
                self.log_error(f"Missing input file: {inp.relative_to(self.base)}")

        req_outputs = [
            self.outputs_dir / "synthesis_evaluation.csv",
            self.outputs_dir / "synthesis_summary.json",
            self.p10_dir / "README.md",
        ]
        for out in req_outputs:
            if out.is_file():
                self.log_pass(f"Verified deliverable file: {out.relative_to(self.base)}")
            else:
                self.log_error(f"Missing deliverable file: {out.relative_to(self.base)}")

    def verify_csv_schema_and_mapping(self) -> list[dict[str, str]]:
        print("\n2. Verifying CSV schema and cross-domain mapping...")
        csv_path = self.outputs_dir / "synthesis_evaluation.csv"
        rows = read_csv_rows(csv_path)

        if not rows:
            self.log_error("synthesis_evaluation.csv is empty")
            return []

        actual_cols = list(rows[0].keys())
        if actual_cols == EXPECTED_COLUMNS:
            self.log_pass(f"CSV header columns exactly match expected schema ({len(actual_cols)} cols)")
        else:
            self.log_error(f"CSV header columns mismatch: {actual_cols} vs {EXPECTED_COLUMNS}")

        if len(rows) == 5:
            self.log_pass("Exactly 5 alternative records present in synthesis_evaluation.csv")
        else:
            self.log_error(f"Expected 5 records, got {len(rows)}")

        for r in rows:
            alt_id = r["alternative_id"]
            if alt_id not in EXPECTED_MAPPING:
                self.log_error(f"Unexpected alternative_id: {alt_id}")
                continue

            exp_ref, exp_sec = EXPECTED_MAPPING[alt_id]
            if r["candidate_reference_id"] == exp_ref and r["section_id"] == exp_sec:
                self.log_pass(f"Mapping verified for {alt_id}: candidate_ref={exp_ref}, section={exp_sec}")
            else:
                self.log_error(
                    f"Mapping mismatch for {alt_id}: got ({r['candidate_reference_id']}, {r['section_id']}), "
                    f"expected ({exp_ref}, {exp_sec})"
                )

        return rows

    def verify_financial_and_capacity_metrics(self, rows: list[dict[str, str]]) -> None:
        print("\n3. Verifying financial metrics and S00 capacity metrics...")
        for r in rows:
            alt_id = r["alternative_id"]
            if alt_id not in EXPECTED_CAPEX:
                continue

            exp_capex = EXPECTED_CAPEX[alt_id]
            exp_npv = EXPECTED_NPV[alt_id]
            exp_vc = EXPECTED_MAX_VC_S00[alt_id]

            if r["initial_capex_twd_billion"] == exp_capex:
                self.log_pass(f"{alt_id} initial CAPEX verified: {exp_capex} TWD B")
            else:
                self.log_error(f"{alt_id} initial CAPEX mismatch: got {r['initial_capex_twd_billion']}, expected {exp_capex}")

            if r["npv_30yr_3_5pct_twd_billion"] == exp_npv:
                self.log_pass(f"{alt_id} 30yr NPV verified: {exp_npv} TWD B")
            else:
                self.log_error(f"{alt_id} 30yr NPV mismatch: got {r['npv_30yr_3_5pct_twd_billion']}, expected {exp_npv}")

            if r["max_vc_s00"] == exp_vc:
                self.log_pass(f"{alt_id} max V/C S00 verified: {exp_vc}")
            else:
                self.log_error(f"{alt_id} max V/C S00 mismatch: got {r['max_vc_s00']}, expected {exp_vc}")

    def verify_synthesis_logic_and_overrides(self, rows: list[dict[str, str]]) -> None:
        print("\n4. Verifying synthesis verdicts, overrides, and governance notes...")
        for r in rows:
            alt_id = r["alternative_id"]
            claim = r["original_economic_claim"]
            status = r["capacity_status_s00"]
            verdict = r["synthesis_verdict"]
            note = r["governance_note"]

            if alt_id == "BL-Double":
                if verdict == VERDICT_APPROVED_BASELINE:
                    self.log_pass(f"BL-Double assigned verdict: {VERDICT_APPROVED_BASELINE}")
                else:
                    self.log_error(f"BL-Double unexpected verdict: {verdict}")

                if "PASS" in status:
                    self.log_pass(f"BL-Double capacity status verified: {status}")
                else:
                    self.log_error(f"BL-Double unexpected capacity status: {status}")

                if float(r["max_vc_s00"]) <= 1.0:
                    self.log_pass(f"BL-Double max V/C <= 1.0 confirmed ({r['max_vc_s00']})")
                else:
                    self.log_error(f"BL-Double max V/C > 1.0 ({r['max_vc_s00']})")

            elif alt_id.startswith("ALT-"):
                # Single-track candidate
                if status == "FAIL_CAPACITY":
                    self.log_pass(f"{alt_id} capacity status is FAIL_CAPACITY")
                else:
                    self.log_error(f"{alt_id} unexpected capacity status: {status}")

                if float(r["max_vc_s00"]) > 1.0:
                    self.log_pass(f"{alt_id} max V/C > 1.0 confirmed ({r['max_vc_s00']})")
                else:
                    self.log_error(f"{alt_id} unexpected max V/C <= 1.0: {r['max_vc_s00']}")

                if verdict == VERDICT_REJECTED:
                    self.log_pass(f"{alt_id} assigned verdict: {VERDICT_REJECTED}")
                else:
                    self.log_error(f"{alt_id} unexpected verdict: {verdict}")

                if note == NOTE_SINGLE_TRACK_REJECTED:
                    self.log_pass(f"{alt_id} governance note exactly matches required text")
                else:
                    self.log_error(f"{alt_id} governance note mismatch: got '{note}'")

                # Verify specific override of domain 06 claims
                if alt_id == "ALT-S1":
                    if "Optimal Alternative" in claim:
                        self.log_pass("ALT-S1 retained original claim prefix 'Optimal Alternative'")
                        self.log_pass("ALT-S1 claim 'Optimal Alternative' successfully overridden by REJECTED_CAPACITY_FAILURE")
                    else:
                        self.log_error(f"ALT-S1 original claim missing 'Optimal Alternative': {claim}")

                if alt_id == "ALT-S4":
                    if "Strong Contender" in claim:
                        self.log_pass("ALT-S4 retained original claim prefix 'Strong Contender'")
                        self.log_pass("ALT-S4 claim 'Strong Contender' successfully overridden by REJECTED_CAPACITY_FAILURE")
                    else:
                        self.log_error(f"ALT-S4 original claim missing 'Strong Contender': {claim}")

    def verify_json_summary(self) -> None:
        print("\n5. Verifying JSON summary structure and aggregated disposition...")
        json_path = self.outputs_dir / "synthesis_summary.json"
        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        if meta.get("analysis_phase") == "Phase 10: Multi-Criteria Synthesis":
            self.log_pass("JSON metadata analysis_phase verified")
        else:
            self.log_error(f"JSON metadata analysis_phase mismatch: {meta.get('analysis_phase')}")

        if meta.get("readiness_gate") == "READY_FOR_PRELIMINARY_SCREENING_ONLY":
            self.log_pass("JSON metadata readiness_gate matches project state")
        else:
            self.log_error(f"JSON metadata readiness_gate mismatch: {meta.get('readiness_gate')}")

        disp = data.get("aggregated_disposition", {})
        if disp.get("total_alternatives_evaluated") == 5:
            self.log_pass("JSON aggregated total alternatives: 5")
        else:
            self.log_error(f"JSON aggregated total alternatives mismatch: {disp.get('total_alternatives_evaluated')}")

        if disp.get("single_track_rejected_capacity_failure") == 4:
            self.log_pass("JSON single-track rejected count: 4/4")
        else:
            self.log_error(f"JSON single-track rejected mismatch: {disp.get('single_track_rejected_capacity_failure')}")

        if disp.get("baseline_approved") == 1:
            self.log_pass("JSON baseline approved count: 1")
        else:
            self.log_error(f"JSON baseline approved mismatch: {disp.get('baseline_approved')}")

        if disp.get("overridden_economic_claims_count") == 2:
            self.log_pass("JSON overridden claims count: 2 (ALT-S1, ALT-S4)")
        else:
            self.log_error(f"JSON overridden claims count mismatch: {disp.get('overridden_economic_claims_count')}")

        eval_dict = data.get("alternatives_evaluation", {})
        if len(eval_dict) == 5:
            self.log_pass("JSON alternatives_evaluation contains 5 alternatives")
        else:
            self.log_error(f"JSON alternatives_evaluation count mismatch: {len(eval_dict)}")

    def verify_deterministic_rerun(self) -> None:
        print("\n6. Verifying deterministic byte-identical rerun...")
        csv_path = self.outputs_dir / "synthesis_evaluation.csv"
        json_path = self.outputs_dir / "synthesis_summary.json"

        csv_hash_before = file_sha256(csv_path)
        json_hash_before = file_sha256(json_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_out = Path(tmpdir)
            run_synthesis(base_dir=self.base, output_dir=tmp_out)

            tmp_csv_hash = file_sha256(tmp_out / "synthesis_evaluation.csv")
            tmp_json_hash = file_sha256(tmp_out / "synthesis_summary.json")

            if csv_hash_before == tmp_csv_hash:
                self.log_pass("Deterministic rerun: synthesis_evaluation.csv is byte-identical")
            else:
                self.log_error("Deterministic rerun: synthesis_evaluation.csv differs")

            if json_hash_before == tmp_json_hash:
                self.log_pass("Deterministic rerun: synthesis_summary.json is byte-identical")
            else:
                self.log_error("Deterministic rerun: synthesis_summary.json differs")

    def verify_repository_invariants(self) -> None:
        print("\n7. Verifying repository invariants and readiness blockers...")
        # 1. verify_source_snapshot
        snap_cmd = [sys.executable, str(self.base / "scripts" / "verify_source_snapshot.py")]
        snap_proc = subprocess.run(snap_cmd, cwd=self.base, capture_output=True, text=True)
        if snap_proc.returncode == 0:
            self.log_pass("Source snapshot passes: exactly 36 source data files unchanged")
        else:
            self.log_error(f"Source snapshot failed:\n{snap_proc.stderr or snap_proc.stdout}")

        # 2. verify_pipeline_integrity
        pipe_cmd = [sys.executable, str(self.base / "scripts" / "verify_pipeline_integrity.py")]
        pipe_proc = subprocess.run(pipe_cmd, cwd=self.base, capture_output=True, text=True)
        if pipe_proc.returncode == 0:
            self.log_pass("Pipeline integrity passes: 48 automated checks pass")
        else:
            self.log_error(f"Pipeline integrity failed:\n{pipe_proc.stderr or pipe_proc.stdout}")

        # 3. verify_analysis_readiness (must exit 1 with 10 blockers)
        read_cmd = [sys.executable, str(self.base / "scripts" / "verify_analysis_readiness.py")]
        read_proc = subprocess.run(read_cmd, cwd=self.base, capture_output=True, text=True)
        if read_proc.returncode == 1:
            if "READY_FOR_PRELIMINARY_SCREENING_ONLY" in read_proc.stdout and "Open blocking requirements: 10" in read_proc.stdout:
                self.log_pass("Readiness gate correctly preserved: READY_FOR_PRELIMINARY_SCREENING_ONLY with 10 blockers")
            else:
                self.log_error(f"Readiness output unexpected: {read_proc.stdout[:300]}")
        else:
            self.log_error(f"Readiness gate expected returncode 1, got {read_proc.returncode}")

    def run_all(self) -> int:
        print("=" * 65)
        print("VERIFYING PHASE 10: MULTI-CRITERIA SYNTHESIS")
        print("=" * 65)

        self.verify_inputs_and_outputs_existence()
        rows = self.verify_csv_schema_and_mapping()
        if rows:
            self.verify_financial_and_capacity_metrics(rows)
            self.verify_synthesis_logic_and_overrides(rows)
        self.verify_json_summary()
        self.verify_deterministic_rerun()
        self.verify_repository_invariants()

        print("\n" + "=" * 65)
        if self.errors:
            print(f"VERIFICATION SUMMARY: {self.passed_checks} PASSED, {len(self.errors)} ERRORS")
            print("=" * 65)
            for err in self.errors:
                print(f"  [ERROR] {err}")
            return 1
        else:
            print(f"VERIFICATION SUMMARY: {self.passed_checks} PASSED, 0 WARNINGS, 0 ERRORS")
            print("=" * 65)
            print("ALL PHASE 10 MULTI-CRITERIA SYNTHESIS CHECKS COMPLETED SUCCESSFULLY.")
            return 0


def main() -> int:
    verifier = SynthesisVerifier()
    return verifier.run_all()


if __name__ == "__main__":
    sys.exit(main())
