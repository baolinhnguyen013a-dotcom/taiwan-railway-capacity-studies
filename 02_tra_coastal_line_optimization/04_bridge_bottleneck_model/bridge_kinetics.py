#!/usr/bin/env python3
"""
Bridge Bottleneck Kinetics & Capacity Model for TRA Coastal Line.
Computes traversal time, clearance cycles, platooning headways, and capacity utilization.
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

@dataclass
class Bridge:
    bridge_id: str
    name_zh: str
    name_en: str
    length_m: float
    max_speed_kmh: float

@dataclass
class Train:
    train_id: str
    name_zh: str
    train_class: str
    length_m: float
    speed_kmh: float

class BridgeKineticsEngine:
    def __init__(
        self,
        switch_throw_sec: float = 8.0,
        interlock_release_sec: float = 10.0,
        safety_buffer_sec: float = 15.0,
        atp_block_headway_sec: float = 90.0
    ):
        self.switch_throw_sec = switch_throw_sec
        self.interlock_release_sec = interlock_release_sec
        self.safety_buffer_sec = safety_buffer_sec
        self.atp_block_headway_sec = atp_block_headway_sec

    def traversal_time_sec(self, bridge: Bridge, train: Train) -> float:
        """Physical traversal time from locomotive entering bridge to rear axle clearing abutment."""
        speed_mps = min(bridge.max_speed_kmh, train.speed_kmh) / 3.6
        total_distance = bridge.length_m + train.length_m
        return total_distance / speed_mps

    def direction_reversal_cycle_sec(self, bridge: Bridge, train: Train) -> float:
        """Minimum time required from train entry to opposing train being cleared for entry."""
        t_trav = self.traversal_time_sec(bridge, train)
        t_overhead = self.switch_throw_sec + self.interlock_release_sec + self.safety_buffer_sec
        return t_trav + t_overhead

    def platooned_two_train_slot_sec(self, bridge: Bridge, lead_train: Train, trail_train: Train) -> float:
        """
        Time occupied by two consecutive trains running in the same direction,
        followed by a direction reversal.
        """
        # Lead train traverses and clears first block
        # Trail train follows at ATP block separation
        # Bridge is cleared when trail train exits
        trail_trav = self.traversal_time_sec(bridge, trail_train)
        total_platoon_time = self.atp_block_headway_sec + trail_trav + self.switch_throw_sec + self.interlock_release_sec + self.safety_buffer_sec
        return total_platoon_time

    def evaluate_30min_clockface_window(
        self,
        bridge: Bridge,
        express_train: Train,
        commuter_train: Train
    ) -> Dict[str, float]:
        """
        Evaluates a standard 30-minute clockface service window containing:
        - 1 Northbound Express + 2 Northbound Commuters (3 NB trains)
        - 1 Southbound Express + 2 Southbound Commuters (3 SB trains)
        Total: 6 trains in 30 minutes (1,800 seconds).
        """
        # Mode 1: Strict One-by-One Alternating (NB1 -> SB1 -> NB2 -> SB2 -> NB3 -> SB3)
        # Requires 6 full direction reversal cycles
        cycle_exp = self.direction_reversal_cycle_sec(bridge, express_train)
        cycle_comm = self.direction_reversal_cycle_sec(bridge, commuter_train)
        total_alternating_occ_sec = 2 * cycle_exp + 4 * cycle_comm
        alt_utilization_pct = (total_alternating_occ_sec / 1800.0) * 100.0

        # Mode 2: Platooned Dispatch (Convoy: [NB Exp + NB Comm] -> [SB Exp + SB Comm] -> [NB Comm] -> [SB Comm])
        # Grouping 2 same-direction trains cuts reversals from 6 down to 4
        platoon_nb = self.platooned_two_train_slot_sec(bridge, express_train, commuter_train)
        platoon_sb = self.platooned_two_train_slot_sec(bridge, express_train, commuter_train)
        single_nb = self.direction_reversal_cycle_sec(bridge, commuter_train)
        single_sb = self.direction_reversal_cycle_sec(bridge, commuter_train)
        total_platooned_occ_sec = platoon_nb + platoon_sb + single_nb + single_sb
        plat_utilization_pct = (total_platooned_occ_sec / 1800.0) * 100.0

        # Free buffer remaining in 30 minutes
        free_buffer_sec = 1800.0 - total_platooned_occ_sec

        return {
            "bridge_id": bridge.bridge_id,
            "bridge_name": bridge.name_zh,
            "bridge_length_m": bridge.length_m,
            "traversal_time_express_sec": round(self.traversal_time_sec(bridge, express_train), 1),
            "traversal_time_commuter_sec": round(self.traversal_time_sec(bridge, commuter_train), 1),
            "reversal_cycle_express_sec": round(cycle_exp, 1),
            "reversal_cycle_commuter_sec": round(cycle_comm, 1),
            "alternating_occupied_sec_per_30min": round(total_alternating_occ_sec, 1),
            "alternating_utilization_pct": round(alt_utilization_pct, 2),
            "platooned_occupied_sec_per_30min": round(total_platooned_occ_sec, 1),
            "platooned_utilization_pct": round(plat_utilization_pct, 2),
            "platooned_free_buffer_sec": round(free_buffer_sec, 1),
            "capacity_verdict": "PASSES_ASSUMED_ARITHMETIC_THRESHOLD" if plat_utilization_pct <= 45.0 else "EXCEEDS_ASSUMED_ARITHMETIC_THRESHOLD"
        }

if __name__ == "__main__":
    bridges = [
        Bridge("BRG01", "中港溪橋", "Zhonggang River Bridge", 450.0, 115.0),
        Bridge("BRG02", "後龍溪橋", "Houlong River Bridge", 700.0, 115.0),
        Bridge("BRG03", "大安溪橋", "Daan River Bridge", 1100.0, 115.0),
        Bridge("BRG04", "大甲溪橋", "Dajia River Bridge", 1250.0, 115.0)
    ]
    exp = Train("EMU3000", "新自強號", "Express", 244.0, 115.0)
    comm = Train("EMU900", "區間車", "Commuter", 203.0, 105.0)

    engine = BridgeKineticsEngine()
    import csv
    results = [engine.evaluate_30min_clockface_window(b, exp, comm) for b in bridges]

    out_path = Path(__file__).resolve().with_name("bridge_capacity_evaluations.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print("=== BRIDGE CAPACITY EVALUATION SUMMARY ===")
    for r in results:
        print(f"{r['bridge_name']} ({r['bridge_length_m']}m): Traversals={r['traversal_time_express_sec']}s Exp / {r['traversal_time_commuter_sec']}s Comm | Platooned Util={r['platooned_utilization_pct']}% | Free Buffer={r['platooned_free_buffer_sec']}s ({r['capacity_verdict']})")
