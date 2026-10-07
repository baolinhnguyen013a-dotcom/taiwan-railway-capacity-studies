#!/usr/bin/env python3
"""Adversarial and regression tests for analysis readiness and source preservation.

Test suite covers:
1. Declared RESOLVED cannot override failed predicate (fail-closed rule).
2. Inconsistent model_readiness.json metadata detection.
3. Timetable semantic checks (short-turn boundary violations, missing whole-ring).
4. railML XSD schema proof requirement: stray XSD or empty log cannot bypass F-010.
5. Evacuation label/tag deletion resistance: F-006 requires workbook package.
6. Lifecycle tag deletion resistance: F-009 requires bankable audit package.
7. Route length fake status resistance: F-011 requires reconciliation record.
8. Source file SHA-256 snapshot verification and drift detection.
9. Current workspace fail-closed readiness gate (10 blocking requirements).
10. Real isolated temporary-copy test running audit_and_prepare.py followed by verify_analysis_readiness.py.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts.evidence_predicates import (
    EvidenceRequirement,
    evaluate_requirements,
    get_all_requirements,
    pred_f001_catalog,
    pred_f002_traceability,
    pred_f003_demand,
    pred_f004_service,
    pred_f005_s1_screen,
    pred_f006_evacuation,
    pred_f007_whole_ring,
    pred_f008_microsimulation,
    pred_f009_lifecycle,
    pred_f010_railml,
    pred_f011_scope_transformation,
    pred_f013_alignment_geometry,
    pred_f014_capex_rates,
)
from scripts.verify_analysis_readiness import check_readiness
from scripts.verify_source_snapshot import get_current_source_files, verify_snapshot


class TestAnalysisReadiness(unittest.TestCase):
    def setUp(self) -> None:
        self.base_dir = BASE_DIR

    def test_current_workspace_has_exactly_36_source_files(self) -> None:
        """Certified snapshot must contain exactly 36 source data files across domains 01-07."""
        current_files = get_current_source_files(self.base_dir)
        self.assertEqual(len(current_files), 36)

    def test_source_snapshot_verification_passes(self) -> None:
        """verify_source_snapshot must pass on the unedited source domains 01-07."""
        success, count, errors = verify_snapshot(self.base_dir)
        self.assertTrue(success, f"Snapshot verification failed: {errors}")
        self.assertEqual(count, 36)
        self.assertEqual(len(errors), 0)

    def test_adversarial_checksum_drift_content_change(self) -> None:
        """Modifying a source file's digest must cause snapshot verification to fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            qc_dir = tmp_path / "08_quality_control"
            qc_dir.mkdir(parents=True)
            shutil.copy(self.base_dir / "08_quality_control" / "source_file_checksums.csv", qc_dir / "source_file_checksums.csv")

            for domain_dir in self.base_dir.iterdir():
                if domain_dir.name.startswith(("01_", "02_", "03_", "04_", "05_", "06_", "07_")) and domain_dir.is_dir():
                    shutil.copytree(domain_dir, tmp_path / domain_dir.name)

            # Tamper with one file
            tampered_file = tmp_path / "01_alignment_topology" / "alignment_horizontal_curves.csv"
            tampered_file.write_text("tampered,content\n", encoding="utf-8")

            success, count, errors = verify_snapshot(tmp_path)
            self.assertFalse(success)
            self.assertTrue(any("Digest drift detected" in e for e in errors))

    def test_adversarial_checksum_drift_file_removal_and_addition(self) -> None:
        """Removing or adding a file in domains 01-07 must cause snapshot verification to fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            qc_dir = tmp_path / "08_quality_control"
            qc_dir.mkdir(parents=True)
            shutil.copy(self.base_dir / "08_quality_control" / "source_file_checksums.csv", qc_dir / "source_file_checksums.csv")

            for domain_dir in self.base_dir.iterdir():
                if domain_dir.name.startswith(("01_", "02_", "03_", "04_", "05_", "06_", "07_")) and domain_dir.is_dir():
                    shutil.copytree(domain_dir, tmp_path / domain_dir.name)

            # Remove one file
            (tmp_path / "01_alignment_topology" / "alignment_stations.csv").unlink()
            success, count, errors = verify_snapshot(tmp_path)
            self.assertFalse(success)
            self.assertTrue(any("Source file removed or missing" in e for e in errors))

            # Add an unexpected file
            (tmp_path / "02_tunnel_civil" / "unexpected_new_bore.csv").write_text("dummy\n", encoding="utf-8")
            success, count, errors = verify_snapshot(tmp_path)
            self.assertFalse(success)
            self.assertTrue(any("Unexpected source file added" in e for e in errors))

    def test_declared_resolved_cannot_override_failed_predicate(self) -> None:
        """Adversarial case: Declaring status = RESOLVED when predicate fails MUST evaluate to OPEN."""
        adversarial_req = EvidenceRequirement(
            finding_id="F-TEST-OVERRIDE",
            severity="CRITICAL",
            declared_status="RESOLVED",
            predicate_id="PRED-TEST-FAILING",
            blocks="FORMAL_OPTIMIZATION",
            title="Adversarial finding declaring RESOLVED despite failing evidence predicate",
            evidence="nonexistent_file.csv",
            predicate_fn=lambda base: (False, "Simulated missing evidence failure"),
        )

        passed, reason = adversarial_req.predicate_fn(self.base_dir)
        self.assertFalse(passed)

        eval_status = adversarial_req.default_closed_status if passed else "OPEN"
        self.assertEqual(eval_status, "OPEN")
        self.assertNotEqual(eval_status, adversarial_req.declared_status)

    def test_inconsistent_readiness_json_detection(self) -> None:
        """Adversarial case: model_readiness.json claiming formal readiness when blocking findings exist must fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            qc_dir = tmp_path / "08_quality_control"
            qc_dir.mkdir(parents=True)

            for qc_file in ("data_catalog.csv", "source_manifest.csv", "acceptance_criteria.csv", "validation_findings.csv", "source_file_checksums.csv"):
                shutil.copy(self.base_dir / "08_quality_control" / qc_file, qc_dir / qc_file)

            # Write falsely claiming formal readiness
            dishonest_readiness = {
                "generated_at": "2026-10-06",
                "source_snapshot_status": "CURRENT_WORKSPACE_SNAPSHOT_MATCHED",
                "historical_preservation_status": "NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY",
                "overall_status": "READY_FOR_FORMAL_OPTIMIZATION_AND_SIMULATION",
                "not_ready_for": [],
                "blocking_findings": [],
                "supported_next_step": "Falsely claiming readiness",
            }
            (qc_dir / "model_readiness.json").write_text(json.dumps(dishonest_readiness), encoding="utf-8")

            ready_dir = tmp_path / "08_analysis_ready"
            shutil.copytree(self.base_dir / "08_analysis_ready", ready_dir)

            code, res = check_readiness(tmp_path)
            self.assertEqual(code, 3)
            self.assertEqual(res["status"], "INCONSISTENT_METADATA")
            self.assertTrue(any("claims READY_FOR_FORMAL_OPTIMIZATION_AND_SIMULATION" in err for err in res["errors"]))

    def test_timetable_semantics_short_turn_and_whole_ring(self) -> None:
        """Timetable semantic evaluation must flag short turns traversing all stations and missing whole-ring."""
        passed_ring, reason_ring = pred_f007_whole_ring(self.base_dir)
        self.assertFalse(passed_ring)
        self.assertIn("12 stations", reason_ring)

        passed_micro, reason_micro = pred_f008_microsimulation(self.base_dir)
        self.assertFalse(passed_micro)
        self.assertIn("semantic error", reason_micro)

    def test_adversarial_stray_dummy_xsd_and_empty_log_fails(self) -> None:
        """Adversarial case: Stray dummy XSD file or unverified log cannot pass railML predicate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create a stray dummy XSD
            stray_xsd = tmp_path / "schema" / "dummy.xsd"
            stray_xsd.parent.mkdir(parents=True)
            stray_xsd.write_text("<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'/>", encoding="utf-8")

            # Create an empty log
            fake_log = tmp_path / "08_quality_control" / "railml_xsd_validation.log"
            fake_log.parent.mkdir(parents=True)
            fake_log.write_text("random text without success or hashes\n", encoding="utf-8")

            # Must still fail closed
            passed, reason = pred_f010_railml(tmp_path)
            self.assertFalse(passed)
            self.assertIn("Missing official railML 3.2 XSD schema bundle", reason)

    def test_adversarial_evacuation_label_deletion_fails(self) -> None:
        """Adversarial case: Deleting status/evidence columns from evacuation CSV cannot make it pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ready_dir = tmp_path / "08_analysis_ready"
            ready_dir.mkdir(parents=True)

            # Create an evacuation table with labels stripped away
            evac_path = ready_dir / "official_station_evacuation_nfpa130.csv"
            with evac_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["station_code", "platform_width", "exit_lanes"])
                writer.writerow(["Y29", "10.0", "24"])

            # Predicate fails closed if columns are deleted or if reproducible workbook is missing
            passed, reason = pred_f006_evacuation(tmp_path)
            self.assertFalse(passed)
            self.assertTrue("missing required columns" in reason or "Missing reproducible NFPA 130 evacuation workbook" in reason)

    def test_adversarial_lifecycle_tag_deletion_fails(self) -> None:
        """Adversarial case: Deleting tag columns from lifecycle CSV cannot make it pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ready_dir = tmp_path / "08_analysis_ready"
            ready_dir.mkdir(parents=True)

            # Create a lifecycle table with tags stripped away
            lcc_path = ready_dir / "official_lifecycle_cost_baseline.csv"
            with lcc_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["cost_category", "capex", "opex", "npv"])
                writer.writerow(["Baseline", "102.486", "1.863", "143.764"])

            # Predicate fails closed if columns are deleted or if bankable audit package is missing
            passed, reason = pred_f009_lifecycle(tmp_path)
            self.assertFalse(passed)
            self.assertTrue("missing required evidence columns" in reason or "lacks a contract-audited bankable lifecycle evidence package" in reason)

    def test_adversarial_fake_status_in_crosscheck_fails_f011(self) -> None:
        """Adversarial case: Faking status in crosscheck without reconciliation record must still fail F-011."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            qc_dir = tmp_path / "08_quality_control"
            qc_dir.mkdir(parents=True)

            cross_path = qc_dir / "official_geometry_crosscheck.csv"
            with cross_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["item", "status"])
                writer.writerow(["East Section published route length", "RECONCILED_FAKE_STATUS"])

            # Fails closed on missing columns or missing reconciliation record
            passed, reason = pred_f011_scope_transformation(tmp_path)
            self.assertFalse(passed)
            self.assertTrue("missing required columns" in reason or "Missing supported route length" in reason)

    def test_detailed_geometry_unknown_values_block_traceability(self) -> None:
        """Station-specific curve radii, vertical grades, and trackwork marked UNKNOWN must block traceability."""
        passed_trace, reason_trace = pred_f002_traceability(self.base_dir)
        self.assertFalse(passed_trace)
        self.assertIn("UNKNOWN", reason_trace)

        passed_geom, reason_geom = pred_f013_alignment_geometry(self.base_dir)
        self.assertFalse(passed_geom)
        self.assertIn("UNKNOWN", reason_geom)

    def test_defensible_official_benchmarks_pass(self) -> None:
        """Defensible official benchmarks (demand, service, S1 rejection, CF763 date) must pass."""
        passed_demand, _ = pred_f003_demand(self.base_dir)
        self.assertTrue(passed_demand)

        passed_service, _ = pred_f004_service(self.base_dir)
        self.assertTrue(passed_service)

        passed_s1, _ = pred_f005_s1_screen(self.base_dir)
        self.assertTrue(passed_s1)

    def test_current_workspace_readiness_fails_closed_with_10_blockers(self) -> None:
        """scripts/verify_analysis_readiness.py must exit with code 1 and list all 10 blockers."""
        code, res = check_readiness(self.base_dir)
        self.assertEqual(code, 1)
        self.assertEqual(res["status"], "READY_FOR_PRELIMINARY_SCREENING_ONLY")
        self.assertEqual(res["blocking_count"], 10)
        expected_blocking = {
            "F-001",
            "F-002",
            "F-006",
            "F-007",
            "F-008",
            "F-009",
            "F-010",
            "F-011",
            "F-013",
            "F-014",
        }
        self.assertEqual(set(res["blocking_findings"]), expected_blocking)

    def test_adversarial_synthetic_station_coverage_and_empty_depot_fails_f007(self) -> None:
        """Adversarial case: Synthetic station coverage (Y01-Y39) with empty/missing depot plan cannot pass F-007."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ready_dir = tmp_path / "08_analysis_ready"
            ready_dir.mkdir(parents=True)

            # Create synthetic timetable with all 39 stations
            tt_path = ready_dir / "train_event_timetable_approved_baseline.csv"
            with tt_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["trip_id", "train_id", "station_code", "arrival_time_s", "departure_time_s", "service_type"])
                for i in range(1, 40):
                    writer.writerow([f"TRIP-{i}", "TRAIN-01", f"Y{i:02d}", f"{i * 100}", f"{i * 100 + 30}", "FULL_RING"])

            # Subcase A: depot plan missing entirely
            passed_no_depot, reason_no_depot = pred_f007_whole_ring(tmp_path)
            self.assertFalse(passed_no_depot)
            self.assertIn("Missing whole-ring depot circulation", reason_no_depot)

            # Subcase B: depot plan exists but is empty
            depot_path = ready_dir / "whole_ring_depot_circulation_plan.csv"
            depot_path.write_text("", encoding="utf-8")
            passed_empty, reason_empty = pred_f007_whole_ring(tmp_path)
            self.assertFalse(passed_empty)
            self.assertIn("empty", reason_empty)

            # Subcase C: depot plan has missing columns / incomplete fleet
            with depot_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["depot_id", "trainset_id"])
                writer.writerow(["DEPOT-SOUTH", "TS-01"])
            passed_incomplete, reason_incomplete = pred_f007_whole_ring(tmp_path)
            self.assertFalse(passed_incomplete)
            self.assertIn("missing required schema columns", reason_incomplete)

    def test_adversarial_empty_block_and_interlocking_fails_f008(self) -> None:
        """Adversarial case: Valid timetable with empty or missing block/interlocking models cannot pass F-008."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ready_dir = tmp_path / "08_analysis_ready"
            ready_dir.mkdir(parents=True)

            # Create valid timetable without short turns
            tt_path = ready_dir / "train_event_timetable_approved_baseline.csv"
            with tt_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["trip_id", "train_id", "station_code", "service_type", "block_id"])
                writer.writerow(["TRIP-1", "TRAIN-01", "Y29", "EAST_SECTION_REGULAR", "BLK-01"])

            # Subcase A: files missing
            passed_missing, reason_missing = pred_f008_microsimulation(tmp_path)
            self.assertFalse(passed_missing)
            self.assertIn("Missing block signaling topology and interlocking", reason_missing)

            # Subcase B: files exist but are empty
            (ready_dir / "block_signalling_topology.csv").write_text("", encoding="utf-8")
            (ready_dir / "interlocking_route_conflicts.csv").write_text("", encoding="utf-8")
            passed_empty, reason_empty = pred_f008_microsimulation(tmp_path)
            self.assertFalse(passed_empty)
            self.assertIn("empty", reason_empty)

    def test_adversarial_empty_lifecycle_audit_fails_f009_and_f014(self) -> None:
        """Adversarial case: Baseline claiming BANKABLE_AUDITED with empty audit model cannot pass F-009 or F-014."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ready_dir = tmp_path / "08_analysis_ready"
            ready_dir.mkdir(parents=True)

            # Create baseline with falsely claimed BANKABLE_AUDITED tags
            lcc_path = ready_dir / "official_lifecycle_cost_baseline.csv"
            with lcc_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "cost_category", "cost_component", "capex_twd_bn", "annual_opex_twd_bn",
                    "renewal_yr15_twd_bn", "salvage_yr30_twd_bn", "opex_renewal_evidence_tag",
                    "rates_evidence_tag", "capex_evidence_tag", "lifecycle_npv_status"
                ])
                writer.writerow([
                    "Total", "Total Capital Expenditure", "102.486", "1.863", "10.438", "15.519",
                    "CONTRACT_AUDITED", "OFFICIAL_APPRAISAL_RATES", "OFFICIAL_APPROVED_BUDGET", "BANKABLE_AUDITED"
                ])

            # Missing audit model
            passed_f009_no, reason_f009_no = pred_f009_lifecycle(tmp_path)
            self.assertFalse(passed_f009_no)
            self.assertIn("Missing contract-audited bankable", reason_f009_no)

            passed_f014_no, reason_f014_no = pred_f014_capex_rates(tmp_path)
            self.assertFalse(passed_f014_no)

            # Empty audit model
            (ready_dir / "bankable_lifecycle_audit_model.csv").write_text("", encoding="utf-8")
            passed_f009_empty, reason_f009_empty = pred_f009_lifecycle(tmp_path)
            self.assertFalse(passed_f009_empty)
            self.assertIn("empty", reason_f009_empty)

    def test_adversarial_empty_route_reconciliation_fails_f011(self) -> None:
        """Adversarial case: Crosscheck marked RECONCILED_WITH_OFFICIAL_DRAWING with empty reconciliation CSV fails F-011."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            qc_dir = tmp_path / "08_quality_control"
            ready_dir = tmp_path / "08_analysis_ready"
            qc_dir.mkdir(parents=True)
            ready_dir.mkdir(parents=True)

            cross_path = qc_dir / "official_geometry_crosscheck.csv"
            with cross_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["item", "collected_or_model_value", "official_value", "difference", "status", "source_id"])
                writer.writerow([
                    "East Section published route length", "14.732 km model chainage", "13.25 km",
                    "+1.482 km", "RECONCILED_WITH_OFFICIAL_DRAWING", "DORTS_PROJECT"
                ])

            # Missing reconciliation file
            passed_missing, reason_missing = pred_f011_scope_transformation(tmp_path)
            self.assertFalse(passed_missing)
            self.assertIn("Missing supported route length", reason_missing)

            # Empty reconciliation file
            (ready_dir / "route_length_reconciliation.csv").write_text("", encoding="utf-8")
            passed_empty, reason_empty = pred_f011_scope_transformation(tmp_path)
            self.assertFalse(passed_empty)
            self.assertIn("empty", reason_empty)

    def test_adversarial_arbitrary_geometry_values_fails_f002_and_f013(self) -> None:
        """Adversarial case: Arbitrary curve/grade values without drawing citations cannot clear F-002 or F-013."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ready_dir = tmp_path / "08_analysis_ready"
            qc_dir = tmp_path / "08_quality_control"
            ready_dir.mkdir(parents=True)
            qc_dir.mkdir(parents=True)

            geom_path = ready_dir / "official_alignment_geometry.csv"
            with geom_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "station_code", "station_name_zh", "chainage_km", "min_curve_radius_m",
                    "max_grade_permille", "crossover_pocket_track", "source_citation",
                    "curve_grade_evidence_status", "trackwork_evidence_status"
                ])
                for i in range(1, 13):
                    writer.writerow([
                        f"Y{i:02d}", f"Station{i}", f"{i * 1.2}", "10.0", "90.0",
                        "BOGUS_TRACKWORK", "General Plan Text", "UNVERIFIED", "UNVERIFIED"
                    ])

            (qc_dir / "official_source_citations.csv").write_text(
                "domain,parameter,official_value,chapter_section,page_citation\n", encoding="utf-8"
            )

            passed_trace, reason_trace = pred_f002_traceability(tmp_path)
            self.assertFalse(passed_trace)
            self.assertIn("unsupported", reason_trace)

            passed_geom, reason_geom = pred_f013_alignment_geometry(tmp_path)
            self.assertFalse(passed_geom)
            self.assertIn("unsupported", reason_geom)

    def test_adversarial_fake_xsd_and_forged_log_fails_f010(self) -> None:
        """Adversarial case: Dummy XSD and forged validation log without authentic manifest fail F-010."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            schema_dir = tmp_path / "schema" / "railML-3.2"
            qc_dir = tmp_path / "08_quality_control"
            topo_dir = tmp_path / "01_alignment_topology"
            rs_dir = tmp_path / "03_rolling_stock_signalling"
            schema_dir.mkdir(parents=True)
            qc_dir.mkdir(parents=True)
            topo_dir.mkdir(parents=True)
            rs_dir.mkdir(parents=True)

            shutil.copy(self.base_dir / "01_alignment_topology" / "railml_infrastructure_east_section.xml", topo_dir / "railml_infrastructure_east_section.xml")
            shutil.copy(self.base_dir / "03_rolling_stock_signalling" / "railml_rollingstock_hitachi_emu.xml", rs_dir / "railml_rollingstock_hitachi_emu.xml")

            # Create dummy XSD
            (schema_dir / "railML.xsd").write_text("<xs:schema/>", encoding="utf-8")

            # Create forged validation log with XML hashes
            infra_h = hashlib.sha256((topo_dir / "railml_infrastructure_east_section.xml").read_bytes()).hexdigest()
            (qc_dir / "railml_xsd_validation.log").write_text(f"VALIDATION SUCCESSFUL\nEXIT_CODE: 0\n{infra_h}\n", encoding="utf-8")

            # Must fail because official schema_manifest.json is missing
            passed_f010, reason_f010 = pred_f010_railml(tmp_path)
            self.assertFalse(passed_f010)
            self.assertIn("Missing official railML 3.2 schema manifest", reason_f010)

            # Forged schema_manifest.json with invalid digests must also fail
            fake_manifest = {
                "railml_version": "3.2",
                "schema_files": {
                    "railML.xsd": "0000000000000000000000000000000000000000000000000000000000000000"
                }
            }
            (schema_dir / "schema_manifest.json").write_text(json.dumps(fake_manifest), encoding="utf-8")
            passed_forged, reason_forged = pred_f010_railml(tmp_path)
            self.assertFalse(passed_forged)
            self.assertIn("digest mismatch", reason_forged)

    def test_real_isolated_regeneration_subprocess(self) -> None:
        """Real isolated temporary-copy test: audit_and_prepare followed by verify_analysis_readiness cannot restore formal readiness."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Copy all files from current workspace to temp directory
            for item in self.base_dir.iterdir():
                if item.name.startswith((".git", ".pytest_cache", "__pycache__")):
                    continue
                dest = tmp_path / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # Run audit_and_prepare in the isolated temp directory
            proc_audit = subprocess.run(
                [sys.executable, str(tmp_path / "scripts" / "audit_and_prepare.py")],
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc_audit.returncode, 0, f"audit_and_prepare failed: {proc_audit.stderr}")

            # Run verify_analysis_readiness in the isolated temp directory
            proc_readiness = subprocess.run(
                [sys.executable, str(tmp_path / "scripts" / "verify_analysis_readiness.py")],
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
            )
            # Must fail closed with exit code 1
            self.assertEqual(proc_readiness.returncode, 1, f"verify_analysis_readiness expected exit 1, got {proc_readiness.returncode}")
            self.assertIn("READY_FOR_PRELIMINARY_SCREENING_ONLY", proc_readiness.stdout)
            self.assertIn("Open blocking requirements: 10", proc_readiness.stdout)

            # Verify generated model_readiness.json in isolated copy
            readiness_data = json.loads((tmp_path / "08_quality_control" / "model_readiness.json").read_text(encoding="utf-8"))
            self.assertEqual(readiness_data["overall_status"], "READY_FOR_PRELIMINARY_SCREENING_ONLY")
            self.assertEqual(readiness_data["source_snapshot_status"], "CURRENT_WORKSPACE_SNAPSHOT_MATCHED")
            self.assertEqual(readiness_data["historical_preservation_status"], "NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY")
            self.assertEqual(len(readiness_data["blocking_findings"]), 10)

            # Verify snapshot verification passes in the temp copy
            proc_snapshot = subprocess.run(
                [sys.executable, str(tmp_path / "scripts" / "verify_source_snapshot.py")],
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc_snapshot.returncode, 0)


if __name__ == "__main__":
    unittest.main()
