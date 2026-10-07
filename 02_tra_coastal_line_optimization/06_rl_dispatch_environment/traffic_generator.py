#!/usr/bin/env python3
"""
Synthetic traffic generator for the TRA Coastal Line exploratory environment.
Generates deterministic timetable baselines and stochastic perturbed arrivals
for real-world Coastal Line services:
- Express: Tze-Chiang 280 (Northbound) & 288 (Southbound) [EMU3000]
- Commuter: Local 2512 (Northbound) & 2518 (Southbound) [EMU900]
- Freight: Taichung Port 7501 (Southbound) [Freight]
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import copy
import random
import numpy as np


class TrainClass(str, Enum):
    EXPRESS = "Express"
    COMMUTER = "Commuter"
    FREIGHT = "Freight"


class TrainDirection(str, Enum):
    NORTHBOUND = "NB"
    SOUTHBOUND = "SB"


@dataclass
class TrainSpec:
    train_id: str                      # Unique identifier, e.g., "280", "288"
    train_number: str                  # Official train number string, e.g., "280次"
    train_type: str                    # "EMU3000", "EMU900", "FREIGHT_7501"
    train_class: TrainClass            # Express, Commuter, Freight
    direction: TrainDirection          # NB or SB
    priority: int                      # 1: Express, 2: Commuter, 3: Freight
    length_m: float                    # Consist length (m)
    max_speed_kmh: float               # Maximum operating speed (km/h)
    nominal_accel_mps2: float          # Nominal acceleration (m/s^2)
    nominal_decel_mps2: float          # Nominal service deceleration (m/s^2)
    emergency_decel_mps2: float        # Emergency deceleration (m/s^2)
    mass_tonnes: float                 # Consist total mass (tonnes)
    scheduled_entry_sec: float         # Scheduled entry time into corridor (sec)
    entry_position_km: float           # Entry chainage (km)
    target_exit_km: float              # Exit chainage (km)
    nominal_run_time_sec: float        # Free-flow uninterrupted travel time (sec)
    actual_entry_sec: float = 0.0      # Actual entry time after delays
    delay_sec: float = 0.0             # Upstream perturbation delay (sec)
    planned_dwell_km: Optional[float] = None
    planned_dwell_sec: float = 0.0


# Specification database matching Phase 1 & 2 models
ROLLING_STOCK_SPECS = {
    "EMU3000": {
        "length_m": 244.0,
        "max_speed_kmh": 115.0,
        "nominal_accel_mps2": 0.60,
        "nominal_decel_mps2": 0.80,
        "emergency_decel_mps2": 1.20,
        "mass_tonnes": 540.0,
        "train_class": TrainClass.EXPRESS,
        "priority": 1
    },
    "EMU900": {
        "length_m": 203.0,
        "max_speed_kmh": 115.0,
        "nominal_accel_mps2": 0.80,
        "nominal_decel_mps2": 1.00,
        "emergency_decel_mps2": 1.20,
        "mass_tonnes": 450.0,
        "train_class": TrainClass.COMMUTER,
        "priority": 2
    },
    "FREIGHT_7501": {
        "length_m": 350.0,
        "max_speed_kmh": 75.0,
        "nominal_accel_mps2": 0.25,
        "nominal_decel_mps2": 0.40,
        "emergency_decel_mps2": 0.80,
        "mass_tonnes": 1200.0,
        "train_class": TrainClass.FREIGHT,
        "priority": 3
    }
}

# Corridor geometry limits
CORRIDOR_NORTH_BOUND_KM = 48.0   # North of Rinan (K49.8)
CORRIDOR_SOUTH_BOUND_KM = 72.0   # South of Qingshui (K69.5)
CORRIDOR_LENGTH_KM = CORRIDOR_SOUTH_BOUND_KM - CORRIDOR_NORTH_BOUND_KM  # 24.0 km


def compute_free_flow_runtime(distance_km: float, max_speed_kmh: float, accel_mps2: float, decel_mps2: float) -> float:
    """Computes kinematic theoretical minimum runtime accounting for acceleration & braking."""
    v_max_mps = max_speed_kmh / 3.6
    dist_m = distance_km * 1000.0
    t_acc = v_max_mps / accel_mps2
    d_acc = 0.5 * accel_mps2 * (t_acc ** 2)
    t_dec = v_max_mps / decel_mps2
    d_dec = 0.5 * decel_mps2 * (t_dec ** 2)
    
    if d_acc + d_dec < dist_m:
        d_cruise = dist_m - (d_acc + d_dec)
        t_cruise = d_cruise / v_max_mps
        return t_acc + t_cruise + t_dec
    else:
        # Triangular speed profile if distance is too short
        v_peak = np.sqrt(2 * dist_m * (accel_mps2 * decel_mps2) / (accel_mps2 + decel_mps2))
        return (v_peak / accel_mps2) + (v_peak / decel_mps2)


class TrafficGenerator:
    """
    Generates train traffic schedules for the TRA Coastal Line bottleneck corridor.
    Includes the 5 core benchmark trains:
      - 280: Tze-Chiang Express (NB, EMU3000)
      - 288: Tze-Chiang Express (SB, EMU3000)
      - 2512: Local Commuter (NB, EMU900)
      - 2518: Local Commuter (SB, EMU900)
      - 7501: Port Freight (SB, FREIGHT_7501)
    """

    def __init__(
        self,
        corridor_north_km: float = CORRIDOR_NORTH_BOUND_KM,
        corridor_south_km: float = CORRIDOR_SOUTH_BOUND_KM
    ):
        self.corridor_north_km = corridor_north_km
        self.corridor_south_km = corridor_south_km
        self.corridor_len_km = corridor_south_km - corridor_north_km

    def _build_train_spec(
        self,
        train_id: str,
        train_number: str,
        type_key: str,
        direction: TrainDirection,
        scheduled_entry_sec: float,
        start_km: Optional[float] = None,
        target_km: Optional[float] = None,
        planned_dwell_km: Optional[float] = None,
        planned_dwell_sec: float = 0.0
    ) -> TrainSpec:
        spec = ROLLING_STOCK_SPECS[type_key]
        if direction == TrainDirection.SOUTHBOUND:
            entry_km = self.corridor_north_km if start_km is None else start_km
            exit_km = self.corridor_south_km if target_km is None else target_km
        else:
            entry_km = self.corridor_south_km if start_km is None else start_km
            exit_km = self.corridor_north_km if target_km is None else target_km

        dist_km = abs(exit_km - entry_km)
        nominal_runtime = compute_free_flow_runtime(
            dist_km,
            spec["max_speed_kmh"],
            spec["nominal_accel_mps2"],
            spec["nominal_decel_mps2"]
        )

        return TrainSpec(
            train_id=train_id,
            train_number=train_number,
            train_type=type_key,
            train_class=spec["train_class"],
            direction=direction,
            priority=spec["priority"],
            length_m=spec["length_m"],
            max_speed_kmh=spec["max_speed_kmh"],
            nominal_accel_mps2=spec["nominal_accel_mps2"],
            nominal_decel_mps2=spec["nominal_decel_mps2"],
            emergency_decel_mps2=spec["emergency_decel_mps2"],
            mass_tonnes=spec["mass_tonnes"],
            scheduled_entry_sec=scheduled_entry_sec,
            entry_position_km=entry_km,
            target_exit_km=exit_km,
            nominal_run_time_sec=nominal_runtime,
            actual_entry_sec=scheduled_entry_sec,
            delay_sec=0.0,
            planned_dwell_km=planned_dwell_km,
            planned_dwell_sec=planned_dwell_sec
        )

    def generate_deterministic_traffic(
        self,
        station_dwells: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> List[TrainSpec]:
        """
        Builds the baseline deterministic timetable schedule.
        Timings are planned such that opposing trains approach the single-track
        bottleneck bridges (Daan K51.2-52.3 and Dajia K61.8-63.0) with tightly
        scheduled meet-pass arrival windows, exercising the dispatch coordination logic.
        station_dwells: Optional map of train_id -> (dwell_km, dwell_sec).
        """
        def _get_dwell(tid: str) -> Tuple[Optional[float], float]:
            if station_dwells and tid in station_dwells:
                return station_dwells[tid]
            return None, 0.0

        d288_km, d288_sec = _get_dwell("288")
        d280_km, d280_sec = _get_dwell("280")
        d2518_km, d2518_sec = _get_dwell("2518")
        d2512_km, d2512_sec = _get_dwell("2512")
        d7501_km, d7501_sec = _get_dwell("7501")

        trains = [
            # 1. Express 288 (SB): Departs K48.0 at t=0s. Approaching Daan bridge around t~100s.
            self._build_train_spec(
                train_id="288",
                train_number="新自強號 288次",
                type_key="EMU3000",
                direction=TrainDirection.SOUTHBOUND,
                scheduled_entry_sec=0.0,
                planned_dwell_km=d288_km,
                planned_dwell_sec=d288_sec
            ),
            # 2. Express 280 (NB): Departs K72.0 at t=140s. Approaching Dajia bridge around t~422s.
            self._build_train_spec(
                train_id="280",
                train_number="新自強號 280次",
                type_key="EMU3000",
                direction=TrainDirection.NORTHBOUND,
                scheduled_entry_sec=140.0,
                planned_dwell_km=d280_km,
                planned_dwell_sec=d280_sec
            ),
            # 3. Commuter 2518 (SB): Departs K48.0 at t=180s. Follows Express 288 Southbound.
            self._build_train_spec(
                train_id="2518",
                train_number="區間快 2518次",
                type_key="EMU900",
                direction=TrainDirection.SOUTHBOUND,
                scheduled_entry_sec=180.0,
                planned_dwell_km=d2518_km,
                planned_dwell_sec=d2518_sec
            ),
            # 4. Commuter 2512 (NB): Departs K72.0 at t=260s. Approaching Dajia bridge behind 280.
            self._build_train_spec(
                train_id="2512",
                train_number="區間快 2512次",
                type_key="EMU900",
                direction=TrainDirection.NORTHBOUND,
                scheduled_entry_sec=260.0,
                planned_dwell_km=d2512_km,
                planned_dwell_sec=d2512_sec
            ),
            # 5. Freight 7501 (SB): Enters at Taichung Port area / K54.9 or K48.0 at t=210s.
            # Using K48.0 to give full corridor evaluation, speed 75 km/h.
            self._build_train_spec(
                train_id="7501",
                train_number="貨物列車 7501次",
                type_key="FREIGHT_7501",
                direction=TrainDirection.SOUTHBOUND,
                scheduled_entry_sec=210.0,
                planned_dwell_km=d7501_km,
                planned_dwell_sec=d7501_sec
            ),
        ]
        return trains

    def generate_stochastic_traffic(
        self,
        mean_delay_sec: float = 120.0,
        std_delay_sec: float = 60.0,
        delay_prob: float = 0.60,
        seed: Optional[int] = None,
        station_dwells: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> List[TrainSpec]:
        """
        Injects upstream network delays into train arrival times.
        Delays are drawn from a positive truncated normal distribution.
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        trains = self.generate_deterministic_traffic(station_dwells=station_dwells)

        for t in trains:
            if random.random() < delay_prob:
                # Truncated normal: mean ~120s, std ~60s, min 10s, max 600s
                delay = float(np.clip(np.random.normal(mean_delay_sec, std_delay_sec), 10.0, 600.0))
                t.delay_sec = round(delay, 1)
                t.actual_entry_sec = round(t.scheduled_entry_sec + t.delay_sec, 1)
            else:
                t.delay_sec = 0.0
                t.actual_entry_sec = t.scheduled_entry_sec

        # Sort trains in chronological order of actual arrival
        trains.sort(key=lambda tr: tr.actual_entry_sec)
        return trains
