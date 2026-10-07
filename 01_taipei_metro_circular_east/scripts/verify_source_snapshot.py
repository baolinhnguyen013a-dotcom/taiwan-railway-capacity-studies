#!/usr/bin/env python3
"""Verify source data file SHA-256 snapshot for domains 01 through 07.

Checks for file addition, removal, or digest drift against
08_quality_control/source_file_checksums.csv.
Reports exactly 36 files and the non-retrospective preservation disclaimer.
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
QC = BASE / "08_quality_control"
CHECKSUM_FILE = QC / "source_file_checksums.csv"
SOURCE_DOMAINS = (
    "01_alignment_topology",
    "02_tunnel_civil",
    "03_rolling_stock_signalling",
    "04_service_operations",
    "05_demand_ridership",
    "06_lifecycle_costs",
    "07_risk_safety_regulations",
)


def get_current_source_files(base_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for domain in sorted(SOURCE_DOMAINS):
        domain_dir = base_dir / domain
        if not domain_dir.is_dir():
            continue
        for p in sorted(domain_dir.iterdir()):
            if p.is_file() and not p.name.startswith("."):
                rel = f"{domain}/{p.name}"
                with p.open("rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
                files[rel] = digest
    return files


def load_recorded_snapshot(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing checksum snapshot: {path}")
    recorded: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            recorded[row["file_path"]] = row["sha256"]
    return recorded


def verify_snapshot(base_dir: Path | None = None) -> tuple[bool, int, list[str]]:
    if base_dir is None:
        base_dir = BASE
    checksum_path = base_dir / "08_quality_control" / "source_file_checksums.csv"
    current_files = get_current_source_files(base_dir)
    recorded_files = load_recorded_snapshot(checksum_path)

    errors: list[str] = []

    if len(current_files) != 36:
        errors.append(f"Expected exactly 36 source data files across domains 01-07, found {len(current_files)}.")

    if len(recorded_files) != 36:
        errors.append(f"Recorded snapshot contains {len(recorded_files)} files, expected exactly 36.")

    missing_in_current = set(recorded_files.keys()) - set(current_files.keys())
    for f in sorted(missing_in_current):
        errors.append(f"Source file removed or missing: {f}")

    unexpected_in_current = set(current_files.keys()) - set(recorded_files.keys())
    for f in sorted(unexpected_in_current):
        errors.append(f"Unexpected source file added: {f}")

    for f in sorted(set(current_files.keys()) & set(recorded_files.keys())):
        if current_files[f] != recorded_files[f]:
            errors.append(f"Digest drift detected in {f}: expected {recorded_files[f]}, got {current_files[f]}")

    success = len(errors) == 0
    return success, len(current_files), errors


def main() -> int:
    try:
        success, count, errors = verify_snapshot(BASE)
    except Exception as exc:
        print(f"[FAIL] Checksum verification aborted: {exc}")
        return 1

    if not success:
        print(f"[FAIL] Source snapshot verification failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"Snapshot verified: exactly {count} source data files match recorded SHA-256 digests.")
    print("Label: CURRENT_WORKSPACE_SNAPSHOT")
    print("Preservation Disclaimer: Historical file preservation prior to this snapshot is")
    print("NOT_VERIFIABLE_FROM_AVAILABLE_HISTORY; this snapshot certifies only the current workspace state.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
