#!/usr/bin/env python3
"""Fail closed when unresolved evidence predicates block formal optimization.

Independent, executable readiness verification:
- Evaluates proof-oriented machine-readable predicates directly from data files.
- Ensures declared_status cannot override a failed predicate.
- Any open evaluated requirement with blocks != "NONE" blocks formal readiness (regardless of severity).
- Verifies model_readiness.json consistency and snapshot certification metadata.
- Fails closed (exit code 1) when any blocking requirement is open.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
QC = BASE / "08_quality_control"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evidence_predicates import evaluate_requirements


def check_readiness(base_dir: Path | None = None) -> tuple[int, dict]:
    if base_dir is None:
        base_dir = BASE
    qc_dir = base_dir / "08_quality_control"

    required_files = [
        qc_dir / "data_catalog.csv",
        qc_dir / "source_manifest.csv",
        qc_dir / "acceptance_criteria.csv",
        qc_dir / "validation_findings.csv",
        qc_dir / "model_readiness.json",
        qc_dir / "source_file_checksums.csv",
    ]
    missing = [str(p.relative_to(base_dir)) for p in required_files if not p.exists()]
    if missing:
        print("READINESS: FAIL (MISSING_FILES)")
        for p in missing:
            print(f"  Missing required QC artifact: {p}")
        return 2, {"status": "FAIL_MISSING_FILES", "missing": missing}

    # 1. Independent evaluation of all requirements
    eval_results = evaluate_requirements(base_dir)

    # 2. Check for declared RESOLVED overriding failed predicate
    for row in eval_results:
        if row["declared_status"] == "RESOLVED" and not row["predicate_passed"]:
            print(f"  [OVERRIDE-REJECTED] {row['finding_id']}: Declared RESOLVED cannot override failed predicate {row['predicate_id']} ({row['predicate_reason']})")

    # 3. Read recorded model_readiness.json and check consistency
    readiness_json = json.loads((qc_dir / "model_readiness.json").read_text(encoding="utf-8"))
    recorded_status = readiness_json.get("overall_status")
    recorded_blocking = set(readiness_json.get("blocking_findings", []))
    snapshot_status = readiness_json.get("source_snapshot_status")
    historical_status = readiness_json.get("historical_preservation_status")

    # 4. Compute evaluated blocking findings (any open requirement where blocks != NONE)
    eval_blocking = [
        r for r in eval_results
        if r["evaluated_status"] not in {"RESOLVED", "CLOSED", "CLOSED_REJECTED"}
        and r["blocks"] != "NONE"
    ]
    eval_blocking_ids = set(r["finding_id"] for r in eval_blocking)

    computed_status = "READY_FOR_FORMAL_OPTIMIZATION_AND_SIMULATION" if not eval_blocking else "READY_FOR_PRELIMINARY_SCREENING_ONLY"

    # Consistency checks
    consistency_errors = []
    if recorded_status == "READY_FOR_FORMAL_OPTIMIZATION_AND_SIMULATION" and eval_blocking:
        consistency_errors.append(
            f"model_readiness.json claims READY_FOR_FORMAL_OPTIMIZATION_AND_SIMULATION while {len(eval_blocking)} requirements are open."
        )
    if recorded_status != computed_status:
        consistency_errors.append(
            f"Recorded status '{recorded_status}' does not match computed evaluated status '{computed_status}'."
        )
    if recorded_blocking != eval_blocking_ids:
        consistency_errors.append(
            f"Recorded blocking findings {sorted(recorded_blocking)} do not match evaluated blocking findings {sorted(eval_blocking_ids)}."
        )
    if snapshot_status != "CURRENT_WORKSPACE_SNAPSHOT_MATCHED":
        consistency_errors.append(
            f"model_readiness.json source_snapshot_status must be 'CURRENT_WORKSPACE_SNAPSHOT_MATCHED', found '{snapshot_status}'."
        )
    if historical_status != "NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY":
        consistency_errors.append(
            f"model_readiness.json historical_preservation_status must be 'NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY', found '{historical_status}'."
        )

    if consistency_errors:
        print("READINESS: FAIL (INCONSISTENT_READINESS_METADATA)")
        for err in consistency_errors:
            print(f"  [INCONSISTENCY] {err}")
        return 3, {"status": "INCONSISTENT_METADATA", "errors": consistency_errors}

    print(f"READINESS: {computed_status}")
    print(f"Open blocking requirements: {len(eval_blocking)}")
    for row in eval_blocking:
        print(f"  {row['finding_id']} [{row['severity']}] {row['finding']}")
        print(f"    -> Blocked by predicate: {row['predicate_id']} ({row['predicate_reason']})")

    if eval_blocking:
        print("Formal optimization and economic/safety conclusions remain blocked.")
        return 1, {
            "status": computed_status,
            "blocking_count": len(eval_blocking),
            "blocking_findings": sorted([r["finding_id"] for r in eval_blocking]),
        }

    print("Formal optimization readiness gate passed.")
    return 0, {"status": computed_status, "blocking_count": 0}


def main() -> int:
    exit_code, _ = check_readiness(BASE)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
