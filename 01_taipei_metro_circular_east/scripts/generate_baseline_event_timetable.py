#!/usr/bin/env python3
"""Generate an indicative East-section headway schedule (12 stations only).

NOTE: This is NOT a whole-ring microsimulation. It covers only 12 East-section stations
(Y29-Y01) and lacks whole-ring circulation (Y02-Y28), depot track layouts, block signals,
and interlocking conflict models. Y22-Y38 short-turns in this collected schedule traverse
all 12 East-section stations due to unmodeled short-turn turnbacks (explicit semantic defect).
"""

from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUTPUT_CSV = BASE / "08_analysis_ready" / "train_event_timetable_approved_baseline.csv"

# Approved interstation link parameters from Table 7.3-8
# Station code sequence from North (Y29) to South (Y01)
STATION_SEQUENCE = ["Y29", "Y30", "Y31", "Y32", "Y33", "Y34", "Y35", "Y36", "Y37", "Y38", "Y39", "Y01"]

RUN_TIMES_NORTH_TO_SOUTH = {
    ("Y29", "Y30"): 89,
    ("Y30", "Y31"): 92,
    ("Y31", "Y32"): 72,
    ("Y32", "Y33"): 87,
    ("Y33", "Y34"): 94,
    ("Y34", "Y35"): 88,
    ("Y35", "Y36"): 123,
    ("Y36", "Y37"): 85,
    ("Y37", "Y38"): 128,
    ("Y38", "Y39"): 92,
    ("Y39", "Y01"): 193,
}

# Dwell times: 45s at major transfer/junction stations, 30s at local intermediate stations
STATION_DWELLS = {
    "Y29": 45,
    "Y30": 30,
    "Y31": 30,
    "Y32": 30,
    "Y33": 45,
    "Y34": 30,
    "Y35": 45,
    "Y36": 45,
    "Y37": 45,
    "Y38": 45,
    "Y39": 30,
    "Y01": 45,
}

PEAK_START_S = 7 * 3600  # 07:00:00 (25200 s)
PEAK_END_S = 9 * 3600    # 09:00:00 (32400 s)

# Approved Headways from Table 8.2-2
CCW_HEADWAY_S = 150  # 2.5 min (24 tph) Counterclockwise (往劍南路 / Northbound)
CW_HEADWAY_S = 198   # 3.3 min (18.18 tph) Clockwise (往動物園 / Southbound)


def format_time(seconds: int) -> str:
    td = timedelta(seconds=int(seconds))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def build_events() -> list[dict]:
    events = []
    event_id = 1

    # 1. COUNTERCLOCKWISE SERVICES (South to North: Y01 -> Y29)
    # 24 tph: 16 full-pattern trains + 8 short-turn trains on 12-station section
    trip_num = 1
    t_start = PEAK_START_S
    while t_start <= PEAK_END_S:
        is_short_turn = (trip_num % 3 == 0)
        # Truthful labels: EAST_SECTION_INDICATIVE_PATTERN vs defective SHORT_TURN_Y22_Y38 traversing 12 stations
        service_type = "SHORT_TURN_Y22_Y38" if is_short_turn else "EAST_SECTION_INDICATIVE_PATTERN"
        trip_id = f"TR-CCW-{trip_num:03d}"
        train_id = f"EMU-CCW-{(trip_num % 35) + 1:02d}"
        depot = "UNVERIFIED_DEPOT_ALLOCATION_EAST" if is_short_turn else "UNVERIFIED_DEPOT_ALLOCATION_SOUTH"

        current_time = t_start
        stations_for_trip = list(reversed(STATION_SEQUENCE))  # Y01 down to Y29

        for i, st in enumerate(stations_for_trip):
            dwell = STATION_DWELLS[st]
            arr_s = current_time
            dep_s = arr_s + dwell
            platform_id = f"{st}-T2"  # Track 2: Counterclockwise
            route_id = f"R-{st}-CCW"

            next_st = stations_for_trip[i + 1] if i + 1 < len(stations_for_trip) else None
            run_to_next = 0
            if next_st:
                run_to_next = RUN_TIMES_NORTH_TO_SOUTH.get((next_st, st), 90)

            events.append({
                "event_id": event_id,
                "trip_id": trip_id,
                "train_id": train_id,
                "direction": "COUNTERCLOCKWISE",
                "service_type": service_type,
                "station_code": st,
                "scheduled_arrival_s": arr_s,
                "scheduled_arrival_hhmmss": format_time(arr_s),
                "dwell_s": dwell,
                "scheduled_departure_s": dep_s,
                "scheduled_departure_hhmmss": format_time(dep_s),
                "run_time_to_next_s": run_to_next,
                "platform_id": platform_id,
                "route_id": route_id,
                "assigned_depot": depot,
                "model_scope": "EAST_SECTION_12_STATIONS_ONLY",
                "evidence_class": "INDICATIVE_HEADWAY_SCHEDULE",
                "validation_status": "UNVALIDATED_LACKS_BLOCK_INTERLOCKING_WHOLE_RING",
                "limitations": "Covers only 12 East stations (Y29-Y01); lacks whole-ring loop, depot throat tracks, block signals, and interlocking models; short-turn Y22-Y38 incorrectly traverses all 12 stations.",
            })
            event_id += 1
            current_time = dep_s + run_to_next

        t_start += CCW_HEADWAY_S
        trip_num += 1

    # 2. CLOCKWISE SERVICES (North to South: Y29 -> Y01)
    # 18 tph service: every 198 seconds
    trip_num = 1
    t_start = PEAK_START_S
    while t_start <= PEAK_END_S:
        trip_id = f"TR-CW-{trip_num:03d}"
        train_id = f"EMU-CW-{(trip_num % 28) + 1:02d}"
        service_type = "EAST_SECTION_INDICATIVE_PATTERN"
        depot = "UNVERIFIED_DEPOT_ALLOCATION_SOUTH"

        current_time = t_start
        for i, st in enumerate(STATION_SEQUENCE):
            dwell = STATION_DWELLS[st]
            arr_s = current_time
            dep_s = arr_s + dwell
            platform_id = f"{st}-T1"  # Track 1: Clockwise
            route_id = f"R-{st}-CW"

            next_st = STATION_SEQUENCE[i + 1] if i + 1 < len(STATION_SEQUENCE) else None
            run_to_next = 0
            if next_st:
                run_to_next = RUN_TIMES_NORTH_TO_SOUTH.get((st, next_st), 90)

            events.append({
                "event_id": event_id,
                "trip_id": trip_id,
                "train_id": train_id,
                "direction": "CLOCKWISE",
                "service_type": service_type,
                "station_code": st,
                "scheduled_arrival_s": arr_s,
                "scheduled_arrival_hhmmss": format_time(arr_s),
                "dwell_s": dwell,
                "scheduled_departure_s": dep_s,
                "scheduled_departure_hhmmss": format_time(dep_s),
                "run_time_to_next_s": run_to_next,
                "platform_id": platform_id,
                "route_id": route_id,
                "assigned_depot": depot,
                "model_scope": "EAST_SECTION_12_STATIONS_ONLY",
                "evidence_class": "INDICATIVE_HEADWAY_SCHEDULE",
                "validation_status": "UNVALIDATED_LACKS_BLOCK_INTERLOCKING_WHOLE_RING",
                "limitations": "Covers only 12 East stations (Y29-Y01); lacks whole-ring loop, depot throat tracks, block signals, and interlocking models.",
            })
            event_id += 1
            current_time = dep_s + run_to_next

        t_start += CW_HEADWAY_S
        trip_num += 1

    return events


def main() -> None:
    events = build_events()
    events.sort(key=lambda r: (r["scheduled_arrival_s"], r["event_id"]))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(events[0].keys()))
        writer.writeheader()
        writer.writerows(events)

    print(f"Generated {len(events)} train events across 12 East-section stations (indicative headway schedule).")
    ccw_trips = len(set(e["trip_id"] for e in events if e["direction"] == "COUNTERCLOCKWISE"))
    cw_trips = len(set(e["trip_id"] for e in events if e["direction"] == "CLOCKWISE"))
    print(f"Counterclockwise trips: {ccw_trips} (target 24 tph * 2h = 48 trips)")
    print(f"Clockwise trips: {cw_trips} (target 18.18 tph * 2h = ~36 trips)")
    print("NOTE: Covers only 12 stations; lacks whole-ring loop, depot throats, and interlocking models.")
    print(f"File saved to: {OUTPUT_CSV.relative_to(BASE)}")


if __name__ == "__main__":
    main()
