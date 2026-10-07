#!/usr/bin/env python3
"""
Nineteen-hour deterministic and disruption scenario for two river bridges.

This toy scheduler shifts entry times to enforce modeled mutual exclusion. A
zero conflict count therefore describes the scheduling rule, not an independently
feasible timetable or a safety result.
"""

import os
import sys
import json
import csv
import random
from typing import List, Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

class BridgeSimulation:
    def __init__(self, bridge_name: str, bridge_length_m: float, max_speed_kmh: float = 115.0):
        self.bridge_name = bridge_name
        self.bridge_length_m = bridge_length_m
        self.max_speed_kmh = max_speed_kmh
        self.switch_time_sec = 8.0
        self.interlock_time_sec = 10.0
        self.safety_buffer_sec = 15.0
        self.atp_headway_sec = 90.0

    def traversal_time(self, train_len_m: float, speed_kmh: float) -> float:
        v = min(self.max_speed_kmh, speed_kmh) / 3.6
        return (self.bridge_length_m + train_len_m) / v

    def run_operating_window_schedule(self, seed: int = 42) -> Dict:
        random.seed(seed)
        # Operating window: 05:00 to 24:00 (19 hours = 1140 minutes = 68,400 seconds)
        # Base second: 05:00:00 = 18000s
        start_sec = 5 * 3600
        end_sec = 24 * 3600

        trains = []
        train_id_counter = 1

        # Generate schedule across 19 operating hours
        for hour in range(5, 24):
            # Express: at :10 (NB) and :40 (SB)
            trains.append({
                "train_id": f"EXP_NB_{train_id_counter:03d}",
                "train_class": "EMU3000",
                "direction": "NB",
                "scheduled_entry_sec": hour * 3600 + 10 * 60,
                "length_m": 244.0,
                "speed_kmh": 115.0
            })
            train_id_counter += 1
            trains.append({
                "train_id": f"EXP_SB_{train_id_counter:03d}",
                "train_class": "EMU3000",
                "direction": "SB",
                "scheduled_entry_sec": hour * 3600 + 40 * 60,
                "length_m": 244.0,
                "speed_kmh": 115.0
            })
            train_id_counter += 1

            # Commuters: at :00 (NB), :15 (SB), :30 (NB), :45 (SB)
            for minute, direction in [(0, "NB"), (15, "SB"), (30, "NB"), (45, "SB")]:
                trains.append({
                    "train_id": f"COMM_{direction}_{train_id_counter:03d}",
                    "train_class": "EMU900",
                    "direction": direction,
                    "scheduled_entry_sec": hour * 3600 + minute * 60,
                    "length_m": 203.0,
                    "speed_kmh": 105.0
                })
                train_id_counter += 1

            # Freight: 1 per hour off-peak at :25 (alternating)
            if hour in [9, 10, 11, 13, 14, 15, 21, 22, 23]:
                frt_dir = "NB" if hour % 2 == 1 else "SB"
                trains.append({
                    "train_id": f"FRT_{frt_dir}_{train_id_counter:03d}",
                    "train_class": "FREIGHT_E",
                    "direction": frt_dir,
                    "scheduled_entry_sec": hour * 3600 + 25 * 60,
                    "length_m": 350.0,
                    "speed_kmh": 75.0
                })
                train_id_counter += 1

        # Sort all trains by scheduled entry time
        trains.sort(key=lambda t: t["scheduled_entry_sec"])

        # Simulate bridge occupations
        total_bridge_occupied_sec = 0.0
        conflicts = 0
        last_exit_sec = 0.0
        last_direction = None

        events = []
        for t in trains:
            t_trav = self.traversal_time(t["length_m"], t["speed_kmh"])
            sched_entry = t["scheduled_entry_sec"]

            # Headway calculation
            if last_direction is None or last_direction == t["direction"]:
                # Same direction platoon: requires ATP separation
                earliest_entry = max(sched_entry, last_exit_sec - t_trav + self.atp_headway_sec)
            else:
                # Opposite direction reversal: requires full clearance + interlock + buffer
                earliest_entry = max(sched_entry, last_exit_sec + self.switch_time_sec + self.interlock_time_sec + self.safety_buffer_sec)

            actual_entry = earliest_entry
            actual_exit = actual_entry + t_trav
            occ_duration = actual_exit - actual_entry

            # This check is expected to remain zero because actual_entry was
            # shifted above. It must not be interpreted as timetable validation.
            if actual_entry < last_exit_sec and last_direction != t["direction"]:
                conflicts += 1

            delay_sec = actual_entry - sched_entry

            events.append({
                "train_id": t["train_id"],
                "train_class": t["train_class"],
                "direction": t["direction"],
                "scheduled_entry_sec": sched_entry,
                "actual_entry_sec": round(actual_entry, 1),
                "actual_exit_sec": round(actual_exit, 1),
                "bridge_occupation_sec": round(occ_duration, 1),
                "schedule_shift_sec": round(delay_sec, 1)
            })

            total_bridge_occupied_sec += occ_duration
            last_exit_sec = actual_exit
            last_direction = t["direction"]

        total_sim_window_sec = end_sec - start_sec
        utilization_pct = (total_bridge_occupied_sec / total_sim_window_sec) * 100.0

        # Disruption test: inject stochastic delays (20% of trains delayed by 1-5 mins)
        disrupted_conflicts = 0
        max_knock_on_delay_sec = 0.0

        disrupted_trains = [dict(t) for t in trains]
        for t in disrupted_trains:
            if random.random() < 0.20:
                primary_delay = random.uniform(60.0, 300.0) # 1 to 5 min primary delay
                t["scheduled_entry_sec"] += primary_delay

        disrupted_trains.sort(key=lambda t: t["scheduled_entry_sec"])
        last_exit_d = 0.0
        last_dir_d = None
        for t in disrupted_trains:
            t_trav = self.traversal_time(t["length_m"], t["speed_kmh"])
            sched = t["scheduled_entry_sec"]
            if last_dir_d is None or last_dir_d == t["direction"]:
                e_entry = max(sched, last_exit_d - t_trav + self.atp_headway_sec)
            else:
                e_entry = max(sched, last_exit_d + self.switch_time_sec + self.interlock_time_sec + self.safety_buffer_sec)
            shift = e_entry - sched
            if shift > max_knock_on_delay_sec:
                max_knock_on_delay_sec = shift
            last_exit_d = e_entry + t_trav
            last_dir_d = t["direction"]

        return {
            "bridge_name": self.bridge_name,
            "bridge_length_m": self.bridge_length_m,
            "total_trains_simulated": len(trains),
            "sim_duration_hours": 19.0,
            "total_occupied_sec": round(total_bridge_occupied_sec, 1),
            "total_free_buffer_sec": round(total_sim_window_sec - total_bridge_occupied_sec, 1),
            "bridge_utilization_pct": round(utilization_pct, 2),
            "scheduled_conflicts": conflicts,
            "stochastic_disruption_tests": {
                "trains_perturbed_pct": 20.0,
                "primary_delay_range_sec": "60s - 300s (1m - 5m)",
                "max_knock_on_delay_sec": round(max_knock_on_delay_sec, 1),
                "robustness_verdict": "ROBUST_ABSORPTION" if max_knock_on_delay_sec < 90.0 else "SCHEDULE_INTERFERENCE"
            },
            "events_sample": events[:15]
        }

def main():
    print("=== RUNNING 19-HOUR EXPLORATORY BRIDGE SCHEDULING SCENARIO ===")
    bridges = [
        ("大安溪橋 (Daan River Bridge)", 1100.0),
        ("大甲溪橋 (Dajia River Bridge)", 1250.0)
    ]

    summary = {}
    for name, length in bridges:
        sim = BridgeSimulation(name, length)
        res = sim.run_operating_window_schedule()
        summary[name] = res
        print(f"\n{name} ({length}m):")
        print(f"  Total trains dispatched: {res['total_trains_simulated']} trains across 19 hours")
        print(f"  Bridge utilization: {res['bridge_utilization_pct']}% (Occupied: {res['total_occupied_sec']/3600:.2f}h / Buffer: {res['total_free_buffer_sec']/3600:.2f}h)")
        print(f"  Schedule conflicts: {res['scheduled_conflicts']}")
        print(f"  Disruption stress test: Max secondary delay = {res['stochastic_disruption_tests']['max_knock_on_delay_sec']}s ({res['stochastic_disruption_tests']['robustness_verdict']})")

    out_file = os.path.join(OUTPUT_DIR, "simulation_19h_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSaved simulation summary to: {out_file}")

if __name__ == "__main__":
    main()
