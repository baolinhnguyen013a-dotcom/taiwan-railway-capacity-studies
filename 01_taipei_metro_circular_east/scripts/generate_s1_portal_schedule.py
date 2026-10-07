#!/usr/bin/env python3
"""Generate and validate a preliminary S1 single-track portal schedule.

This checks section occupation only. It is not a whole-line timetable and does
not prove turnback, fleet, platform, passenger, or boundary feasibility.
"""

import csv
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
OUTPUT = BASE / "08_analysis_ready" / "s1_portal_occupation_schedule_2h.csv"

HORIZON_S = 2 * 60 * 60
DIRECTIONAL_HEADWAY_S = 540
ONE_WAY_RUN_S = 193
CHANGE_ALLOWANCE_S = 18
FIRST_NORTHBOUND_ENTRY_S = ONE_WAY_RUN_S + CHANGE_ALLOWANCE_S


def main() -> None:
    movements = []
    sequence = 1
    cycle = 0
    while cycle * DIRECTIONAL_HEADWAY_S < HORIZON_S:
        south_entry = cycle * DIRECTIONAL_HEADWAY_S
        north_entry = south_entry + FIRST_NORTHBOUND_ENTRY_S
        for direction, origin, destination, entry in (
            ("SOUTHBOUND", "Y39", "Y01", south_entry),
            ("NORTHBOUND", "Y01", "Y39", north_entry),
        ):
            if entry >= HORIZON_S:
                continue
            movements.append({
                "sequence": sequence,
                "direction": direction,
                "origin_portal": origin,
                "destination_portal": destination,
                "entry_time_s": entry,
                "clear_time_s": entry + ONE_WAY_RUN_S,
                "one_way_run_s": ONE_WAY_RUN_S,
            })
            sequence += 1
        cycle += 1

    movements.sort(key=lambda row: row["entry_time_s"])
    prior = None
    for movement in movements:
        if prior is None:
            movement["gap_after_prior_clear_s"] = ""
            movement["conflict_free"] = "YES"
        else:
            gap = movement["entry_time_s"] - prior["clear_time_s"]
            movement["gap_after_prior_clear_s"] = gap
            movement["conflict_free"] = "YES" if gap >= CHANGE_ALLOWANCE_S else "NO"
        prior = movement

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(movements[0]))
        writer.writeheader()
        writer.writerows(movements)

    conflicts = [row for row in movements if row["conflict_free"] == "NO"]
    minimum_gap = min(int(row["gap_after_prior_clear_s"]) for row in movements if row["gap_after_prior_clear_s"] != "")
    cycle_idle = DIRECTIONAL_HEADWAY_S - (2 * ONE_WAY_RUN_S + 2 * CHANGE_ALLOWANCE_S)
    print(f"Wrote {len(movements)} portal movements to {OUTPUT.relative_to(BASE)}")
    print(f"Minimum portal change gap: {minimum_gap}s (required {CHANGE_ALLOWANCE_S}s)")
    print(f"Full-cycle recovery/idle margin: {cycle_idle}s")
    nominal_capacity = (3600 / DIRECTIONAL_HEADWAY_S) * 650
    print("Integration pattern: 180s core headway, every third train through S1")
    print(f"Nominal directional capacity: {nominal_capacity:.1f} pphpd versus official target demand 10310 pphpd (FAIL)")
    print(f"Section occupation conflicts: {len(conflicts)}")
    if conflicts:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
