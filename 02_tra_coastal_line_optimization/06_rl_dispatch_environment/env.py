#!/usr/bin/env python3
"""
Exploratory dispatch environment for the TRA Coastal Line.
Models dynamic speed advisories and bottleneck slotting across single-track river bridges:
- Daan River Bridge (大安溪橋): K51.2 - K52.3 (1100m)
- Dajia River Bridge (大甲溪橋): K61.8 - K63.0 (1250m)
Double-track approaches: Rinan (K49.8) to Dajia (K54.9), Taichung Port (K65.3) to Qingshui (K69.5).

Implements simplified modeled constraints (not a safety certification):
- Mutual exclusion over modeled single-track bridge resources.
- Direction reversal clearance: 15.0s safety buffer + 8.0s switch throw + 10.0s route release = 33.0s.
- Discrete speed advisory tiers: Cruise (115 or v_max), Glide (90), Hold (60), Stop (0).
- Bottleneck priority: Express (1) > Commuter (2) > Freight (3).
"""

from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import List, Dict, Optional, Tuple, Any, Union
import math
import numpy as np

from .traffic_generator import (
    TrafficGenerator, TrainSpec, TrainClass, TrainDirection,
    ROLLING_STOCK_SPECS, CORRIDOR_NORTH_BOUND_KM, CORRIDOR_SOUTH_BOUND_KM,
    CORRIDOR_LENGTH_KM
)


class SpeedAdvisory(IntEnum):
    CRUISE = 0   # Cruise at maximum permissible speed (115 km/h or v_max)
    GLIDE = 1    # Glide / coasting advisory (90 km/h)
    HOLD = 2     # Hold speed advisory (60 km/h)
    STOP = 3     # Stop advisory / deceleration to standstill (0 km/h)


class SignalAspect(IntEnum):
    RED = 0      # Danger / Stop before signal block
    YELLOW = 1   # Caution / Prepare to reduce speed or bridge clearing soon
    GREEN = 2    # Clear / Proceed at authorized speed


class BridgeReservationState(IntEnum):
    CLEAR = 0
    OCCUPIED_NB = 1
    OCCUPIED_SB = 2


@dataclass
class BridgeBottleneck:
    bridge_id: str
    name_zh: str
    name_en: str
    k_start: float                       # Chainage start (km)
    k_end: float                         # Chainage end (km)
    length_m: float                      # Length in meters
    approach_north_km: float             # Double-track approach boundary (North, e.g. K49.8)
    approach_south_km: float             # Double-track approach boundary (South, e.g. K54.9)
    state: BridgeReservationState = BridgeReservationState.CLEAR
    current_occupant_id: Optional[str] = None
    occupant_direction: Optional[TrainDirection] = None
    lock_expiry_sec: float = 0.0         # Timestamp when bridge clears and reversal lock ends
    last_exit_sec: float = 0.0           # Timestamp when rear axle cleared bridge
    reversal_lock_active: bool = False   # True during the 33.0s switch & release buffer
    total_traversals: int = 0
    flying_meets_count: int = 0


@dataclass
class TrainLiveState:
    spec: TrainSpec
    is_active: bool = False
    is_finished: bool = False
    current_km: float = 0.0
    speed_kmh: float = 0.0
    target_advisory_kmh: float = 0.0
    advisory_action: SpeedAdvisory = SpeedAdvisory.CRUISE
    signal_aspect_ahead: SignalAspect = SignalAspect.GREEN
    distance_to_signal_m: float = 9999.0
    unplanned_stops: int = 0
    is_stopped: bool = False
    stop_start_time_sec: float = 0.0
    total_stop_duration_sec: float = 0.0
    energy_dissipated_mj: float = 0.0    # Mechanical kinetic energy lost in braking (MJ)
    traction_energy_mj: float = 0.0      # Energy consumed for acceleration (MJ)
    delay_sec: float = 0.0
    entry_time_actual: Optional[float] = None
    exit_time_actual: Optional[float] = None
    inside_bridge_id: Optional[str] = None
    min_speed_in_bottleneck: float = 999.0
    flying_meets_achieved: int = 0
    dwell_remaining_sec: float = 0.0
    has_dwelled: bool = False


class CoastalBridgeRLDisptachEnv:
    """
    Simulation Environment for TRA Coastal Line Bottleneck Dispatching.
    Implements OpenAI Gym / Gymnasium compatible API: reset() and step().
    """

    def __init__(
        self,
        traffic_generator: Optional[TrafficGenerator] = None,
        dt_seconds: float = 1.0,
        max_simulation_seconds: float = 1800.0,
        switch_throw_sec: float = 8.0,
        interlock_release_sec: float = 10.0,
        safety_buffer_sec: float = 15.0,
        reward_weights: Optional[Dict[str, float]] = None
    ):
        self.dt = dt_seconds
        self.max_sim_sec = max_simulation_seconds
        self.traffic_gen = traffic_generator or TrafficGenerator()

        # Interlocking & Safety Buffers
        self.switch_throw_sec = switch_throw_sec
        self.interlock_release_sec = interlock_release_sec
        self.safety_buffer_sec = safety_buffer_sec
        self.total_reversal_overhead_sec = switch_throw_sec + interlock_release_sec + safety_buffer_sec  # 33.0s

        # Reward weights
        self.weights = {
            "delay_penalty": 0.05,        # Per second of late delay
            "stop_penalty": 30.0,         # Per unplanned stop event
            "energy_loss_penalty": 0.02,  # Per MJ dissipated in braking
            "flying_meet_bonus": 60.0,    # Per bottleneck crossed without stopping
            "punctuality_bonus": 40.0     # Bonus for on-time exit
        }
        if reward_weights:
            self.weights.update(reward_weights)

        # Bottlenecks: Daan River Bridge and Dajia River Bridge
        self.bridges: Dict[str, BridgeBottleneck] = {
            "BRG_DAAN": BridgeBottleneck(
                bridge_id="BRG_DAAN",
                name_zh="大安溪橋",
                name_en="Daan River Bridge",
                k_start=51.2,
                k_end=52.3,
                length_m=1100.0,
                approach_north_km=49.8,  # Rinan approach
                approach_south_km=54.9   # Dajia approach
            ),
            "BRG_DAJIA": BridgeBottleneck(
                bridge_id="BRG_DAJIA",
                name_zh="大甲溪橋",
                name_en="Dajia River Bridge",
                k_start=61.8,
                k_end=63.0,
                length_m=1250.0,
                approach_north_km=59.3,  # Taichung Port approach
                approach_south_km=69.5   # Qingshui approach
            )
        }

        self.sim_time = 0.0
        self.step_count = 0
        self.trains: List[TrainLiveState] = []
        self.num_trains = 0
        self.episode_history: List[Dict[str, Any]] = []

    def reset(
        self,
        seed: Optional[int] = None,
        train_specs: Optional[List[TrainSpec]] = None,
        stochastic: bool = False
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Resets the environment for a new simulation episode."""
        self.sim_time = 0.0
        self.step_count = 0
        self.episode_history = []

        # Reset bridges
        for bridge in self.bridges.values():
            bridge.state = BridgeReservationState.CLEAR
            bridge.current_occupant_id = None
            bridge.occupant_direction = None
            bridge.lock_expiry_sec = 0.0
            bridge.last_exit_sec = 0.0
            bridge.reversal_lock_active = False
            bridge.total_traversals = 0
            bridge.flying_meets_count = 0

        # Load trains
        if train_specs is not None:
            specs = train_specs
        elif stochastic:
            specs = self.traffic_gen.generate_stochastic_traffic(seed=seed)
        else:
            specs = self.traffic_gen.generate_deterministic_traffic()

        self.trains = []
        for sp in specs:
            starts_active = (sp.actual_entry_sec <= 0.0)
            t_state = TrainLiveState(
                spec=sp,
                is_active=starts_active,
                is_finished=False,
                current_km=sp.entry_position_km,
                speed_kmh=min(60.0, sp.max_speed_kmh) if starts_active else 0.0,
                target_advisory_kmh=sp.max_speed_kmh,
                advisory_action=SpeedAdvisory.CRUISE,
                signal_aspect_ahead=SignalAspect.GREEN,
                distance_to_signal_m=9999.0,
                unplanned_stops=0,
                is_stopped=False,
                energy_dissipated_mj=0.0,
                traction_energy_mj=0.0,
                delay_sec=0.0,
                entry_time_actual=0.0 if starts_active else None,
                min_speed_in_bottleneck=999.0,
                flying_meets_achieved=0,
                dwell_remaining_sec=sp.planned_dwell_sec,
                has_dwelled=(sp.planned_dwell_km is None or sp.planned_dwell_sec <= 0.0)
            )
            self.trains.append(t_state)

        self.num_trains = len(self.trains)
        obs = self._get_observation()
        info = self._get_info()
        return obs, info

    def _get_target_speed_for_advisory(self, action: SpeedAdvisory, max_speed: float) -> float:
        """Maps discrete advisory action to physical speed target in km/h."""
        if action == SpeedAdvisory.CRUISE:
            return max_speed
        elif action == SpeedAdvisory.GLIDE:
            return min(max_speed, 90.0)
        elif action == SpeedAdvisory.HOLD:
            return min(max_speed, 60.0)
        elif action == SpeedAdvisory.STOP:
            return 0.0
        return max_speed

    def _find_next_bridge_ahead(self, train: TrainLiveState) -> Tuple[Optional[BridgeBottleneck], float, float]:
        """
        Finds the next single-track bridge the train will encounter along its direction.
        Returns (bridge, entrance_km, distance_to_entrance_km).
        """
        candidate_bridges = list(self.bridges.values())
        if train.spec.direction == TrainDirection.SOUTHBOUND:
            # Moving from North to South (increasing km)
            # Bridges ahead have k_start >= current_km - 0.05
            ahead = []
            for b in candidate_bridges:
                if train.current_km <= b.k_end + (train.spec.length_m / 1000.0):
                    dist_to_entry = (b.k_start - train.current_km) * 1000.0
                    ahead.append((b, b.k_start, dist_to_entry))
            if not ahead:
                return None, 0.0, 99999.0
            ahead.sort(key=lambda item: item[1])
            return ahead[0]
        else:
            # Moving from South to North (decreasing km)
            # Bridges ahead have k_end <= current_km + 0.05
            ahead = []
            for b in candidate_bridges:
                if train.current_km >= b.k_start - (train.spec.length_m / 1000.0):
                    dist_to_entry = (train.current_km - b.k_end) * 1000.0
                    ahead.append((b, b.k_end, dist_to_entry))
            if not ahead:
                return None, 0.0, 99999.0
            ahead.sort(key=lambda item: -item[1])
            return ahead[0]

    def _update_bridge_interlocking(self):
        """
        Updates bridge reservation, mutual exclusion, route release, and reversal locks.
        Enforces:
        1. Opposing trains CANNOT occupy the bridge at the same time.
        2. A vacated bridge cannot be entered by opposing train until
           route release (10s) + switch throw (8s) + safety buffer (15s) = 33s.
        3. Turnout entrance priority: Express (1) > Commuter (2) > Freight (3).
        """
        for bridge in self.bridges.values():
            # Check if current occupant has completely cleared the bridge
            if bridge.current_occupant_id is not None:
                occ_train = next((t for t in self.trains if t.spec.train_id == bridge.current_occupant_id), None)
                cleared = False
                if occ_train is None or occ_train.is_finished:
                    cleared = True
                else:
                    train_len_km = occ_train.spec.length_m / 1000.0
                    if occ_train.spec.direction == TrainDirection.SOUTHBOUND:
                        # SB locomotive entered at k_start; rear clears when locomotive passes k_end + length
                        if occ_train.current_km >= (bridge.k_end + train_len_km):
                            cleared = True
                    else:
                        # NB locomotive entered at k_end; rear clears when locomotive passes k_start - length
                        if occ_train.current_km <= (bridge.k_start - train_len_km):
                            cleared = True

                if cleared:
                    # Bridge is now vacated physically
                    bridge.last_exit_sec = self.sim_time
                    bridge.lock_expiry_sec = self.sim_time + self.total_reversal_overhead_sec
                    bridge.reversal_lock_active = True
                    bridge.state = BridgeReservationState.CLEAR
                    bridge.current_occupant_id = None
                    # Note: occupant_direction is preserved to remember last direction for reversal checks

            # Reversal lock expiry check
            if bridge.reversal_lock_active and self.sim_time >= bridge.lock_expiry_sec:
                bridge.reversal_lock_active = False
                bridge.occupant_direction = None

            # If bridge is clear and not in reversal lock, evaluate incoming requests by priority
            if bridge.state == BridgeReservationState.CLEAR and not bridge.reversal_lock_active:
                competing_trains = []
                for t in self.trains:
                    if not t.is_active or t.is_finished:
                        continue
                    b_ahead, entry_km, dist_m = self._find_next_bridge_ahead(t)
                    if b_ahead == bridge and dist_m <= 3000.0:  # Within 3km approach zone
                        competing_trains.append((t, dist_m))

                if competing_trains:
                    # Sort by priority: Express (1) > Commuter (2) > Freight (3), then distance
                    competing_trains.sort(key=lambda item: (item[0].spec.priority, item[1]))
                    best_train, _ = competing_trains[0]
                    # Reserve for the highest-priority train
                    bridge.current_occupant_id = best_train.spec.train_id
                    bridge.occupant_direction = best_train.spec.direction
                    bridge.state = (
                        BridgeReservationState.OCCUPIED_SB
                        if best_train.spec.direction == TrainDirection.SOUTHBOUND
                        else BridgeReservationState.OCCUPIED_NB
                    )

    def _determine_signal_aspect(self, train: TrainLiveState) -> Tuple[SignalAspect, float]:
        """
        Evaluates the signal aspect and distance to the stop boundary for an approaching train.
        Aspects:
        - GREEN: Route is cleared and reserved for this train.
        - YELLOW: Approaching single-track bottleneck; same-direction train ahead.
        - RED: Stop! Bridge is occupied by opposing train, in reversal lock, or reserved for another train.
        """
        bridge, entry_km, dist_m = self._find_next_bridge_ahead(train)
        if bridge is None:
            return SignalAspect.GREEN, 9999.0

        # If train has legitimately entered and is currently inside the single-track section
        if train.inside_bridge_id == bridge.bridge_id:
            return SignalAspect.GREEN, 0.0

        # Is the bridge reserved specifically for this train?
        if bridge.current_occupant_id == train.spec.train_id:
            return SignalAspect.GREEN, dist_m

        # Is the bridge in 33.0s reversal lock?
        if bridge.reversal_lock_active:
            return SignalAspect.RED, dist_m

        # Is the bridge currently occupied?
        if bridge.state != BridgeReservationState.CLEAR:
            same_direction = (bridge.occupant_direction == train.spec.direction)
            if same_direction:
                return SignalAspect.YELLOW, dist_m
            else:
                return SignalAspect.RED, dist_m

        # Bridge is clear and ready to reserve
        return SignalAspect.GREEN, dist_m

    def step(
        self,
        actions: Union[List[int], np.ndarray, Dict[str, int]]
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Executes one simulation step (dt seconds).
        Updates traffic entry, kinematics, signaling, collisions prevention, and rewards.
        """
        self.sim_time += self.dt
        self.step_count += 1

        step_reward = 0.0
        step_stops = 0
        step_energy_loss_mj = 0.0
        flying_meets_this_step = 0

        # Normalize actions input
        action_dict: Dict[str, SpeedAdvisory] = {}
        if isinstance(actions, dict):
            for tid, a in actions.items():
                action_dict[str(tid)] = SpeedAdvisory(int(a))
        elif isinstance(actions, (list, tuple, np.ndarray)):
            for i, t in enumerate(self.trains):
                act_val = int(actions[i]) if i < len(actions) else int(SpeedAdvisory.CRUISE)
                action_dict[t.spec.train_id] = SpeedAdvisory(act_val)

        # 1. Update bridge interlocking & locks
        self._update_bridge_interlocking()

        # 2. Process each train
        for train in self.trains:
            # A. Check train entry into corridor
            if not train.is_active and not train.is_finished:
                if self.sim_time >= train.spec.actual_entry_sec:
                    train.is_active = True
                    train.entry_time_actual = self.sim_time
                    train.current_km = train.spec.entry_position_km
                    train.speed_kmh = min(40.0, train.spec.max_speed_kmh)  # Entering speed

            if not train.is_active or train.is_finished:
                continue

            # B. Evaluate signaling and speed limits
            aspect, dist_to_sig_m = self._determine_signal_aspect(train)
            train.signal_aspect_ahead = aspect
            train.distance_to_signal_m = dist_to_sig_m

            # C. Determine advisory command and physical speed cap
            v_curr_kmh = train.speed_kmh
            advisory = action_dict.get(train.spec.train_id, SpeedAdvisory.CRUISE)
            train.advisory_action = advisory
            advisory_target_kmh = self._get_target_speed_for_advisory(advisory, train.spec.max_speed_kmh)

            # Enforce ATP Safe Braking Profile if Signal is RED
            effective_target_kmh = advisory_target_kmh
            if aspect == SignalAspect.RED:
                # ATP Braking Curve: v_safe = sqrt(2 * d * dist)
                # Safety margin of 20 meters before signal
                effective_dist_m = max(0.0, dist_to_sig_m - 20.0)
                decel_mps2 = train.spec.nominal_decel_mps2
                safe_speed_mps = math.sqrt(2.0 * decel_mps2 * effective_dist_m)
                safe_speed_kmh = safe_speed_mps * 3.6
                effective_target_kmh = min(effective_target_kmh, safe_speed_kmh)
                if dist_to_sig_m <= 15.0:
                    effective_target_kmh = 0.0
            elif aspect == SignalAspect.YELLOW:
                # Caution aspect: speed capped at 60 km/h or glide
                effective_target_kmh = min(effective_target_kmh, 60.0)

            # Station Dwell Kinematics
            is_dwelling_now = False
            if train.spec.planned_dwell_km is not None and not train.has_dwelled:
                dist_to_station_m = abs(train.spec.planned_dwell_km - train.current_km) * 1000.0

                # Verify train is approaching or at station
                if ((train.spec.direction == TrainDirection.SOUTHBOUND and train.current_km <= train.spec.planned_dwell_km + 0.05) or
                    (train.spec.direction == TrainDirection.NORTHBOUND and train.current_km >= train.spec.planned_dwell_km - 0.05)):

                    if dist_to_station_m <= 30.0 or (v_curr_kmh < 15.0 and dist_to_station_m <= 80.0):
                        effective_target_kmh = 0.0
                        if v_curr_kmh < 0.5 or dist_to_station_m <= 5.0:
                            is_dwelling_now = True
                            train.dwell_remaining_sec -= self.dt
                            if train.dwell_remaining_sec <= 0:
                                train.has_dwelled = True
                        else:
                            is_dwelling_now = True
                    else:
                        # ATP Braking Curve to station platform
                        decel_mps2 = train.spec.nominal_decel_mps2
                        safe_speed_mps = math.sqrt(2.0 * decel_mps2 * max(0.0, dist_to_station_m - 10.0))
                        effective_target_kmh = min(effective_target_kmh, safe_speed_mps * 3.6)

            train.target_advisory_kmh = effective_target_kmh

            # D. Kinematic Update
            v_curr_kmh = train.speed_kmh
            v_targ_kmh = train.target_advisory_kmh

            if v_curr_kmh < v_targ_kmh:
                # Accelerate
                a_mps2 = train.spec.nominal_accel_mps2
                dv_kmh = a_mps2 * self.dt * 3.6
                v_next_kmh = min(v_targ_kmh, v_curr_kmh + dv_kmh)
                # Traction energy proxy
                dv_mps = (v_next_kmh - v_curr_kmh) / 3.6
                if dv_mps > 0:
                    mass_kg = train.spec.mass_tonnes * 1000.0
                    e_step_j = 0.5 * mass_kg * (((v_next_kmh / 3.6) ** 2) - ((v_curr_kmh / 3.6) ** 2))
                    train.traction_energy_mj += max(0.0, e_step_j / 1e6)
            elif v_curr_kmh > v_targ_kmh:
                # Decelerate / Braking
                d_mps2 = train.spec.nominal_decel_mps2
                dv_kmh = d_mps2 * self.dt * 3.6
                v_next_kmh = max(v_targ_kmh, v_curr_kmh - dv_kmh)
                # Kinetic energy dissipated in mechanical braking
                mass_kg = train.spec.mass_tonnes * 1000.0
                e_loss_j = 0.5 * mass_kg * (((v_curr_kmh / 3.6) ** 2) - ((v_next_kmh / 3.6) ** 2))
                train.energy_dissipated_mj += max(0.0, e_loss_j / 1e6)
                step_energy_loss_mj += max(0.0, e_loss_j / 1e6)
            else:
                v_next_kmh = v_curr_kmh

            # E. Unplanned Dead Stop Detection
            if v_next_kmh < 0.1:
                v_next_kmh = 0.0
                if not train.is_stopped:
                    train.is_stopped = True
                    if not is_dwelling_now:
                        train.unplanned_stops += 1
                        train.stop_start_time_sec = self.sim_time
                        step_stops += 1
                train.total_stop_duration_sec += self.dt
            else:
                if train.is_stopped:
                    train.is_stopped = False

            # F. Position advancement & Signal Boundary Enforcement
            v_avg_mps = (v_curr_kmh + v_next_kmh) / (2.0 * 3.6)
            dist_moved_km = (v_avg_mps * self.dt) / 1000.0

            # Station platform stopping enforcement
            if train.spec.planned_dwell_km is not None and not train.has_dwelled:
                if train.spec.direction == TrainDirection.SOUTHBOUND:
                    if train.current_km <= train.spec.planned_dwell_km:
                        if train.current_km + dist_moved_km >= train.spec.planned_dwell_km:
                            dist_moved_km = max(0.0, train.spec.planned_dwell_km - train.current_km)
                            v_next_kmh = 0.0
                            is_dwelling_now = True
                else:
                    if train.current_km >= train.spec.planned_dwell_km:
                        if train.current_km - dist_moved_km <= train.spec.planned_dwell_km:
                            dist_moved_km = max(0.0, train.current_km - train.spec.planned_dwell_km)
                            v_next_kmh = 0.0
                            is_dwelling_now = True

                if abs(train.current_km - train.spec.planned_dwell_km) <= 0.02 and not train.has_dwelled:
                    dist_moved_km = 0.0
                    v_next_kmh = 0.0
                    is_dwelling_now = True

            # Enforce hard stop boundary if facing a RED entrance signal
            bridge_ahead, entry_km, dist_m = self._find_next_bridge_ahead(train)
            if bridge_ahead is not None and train.inside_bridge_id != bridge_ahead.bridge_id:
                if train.signal_aspect_ahead == SignalAspect.RED:
                    if train.spec.direction == TrainDirection.SOUTHBOUND:
                        if train.current_km < bridge_ahead.k_start:
                            stop_line = bridge_ahead.k_start - 0.005  # 5m safety margin
                            if train.current_km + dist_moved_km >= stop_line:
                                dist_moved_km = max(0.0, stop_line - train.current_km)
                                v_next_kmh = 0.0
                                if not train.is_stopped:
                                    train.is_stopped = True
                                    if not is_dwelling_now:
                                        train.unplanned_stops += 1
                                        train.stop_start_time_sec = self.sim_time
                                        step_stops += 1
                    else:
                        if train.current_km > bridge_ahead.k_end:
                            stop_line = bridge_ahead.k_end + 0.005  # 5m safety margin
                            if train.current_km - dist_moved_km <= stop_line:
                                dist_moved_km = max(0.0, train.current_km - stop_line)
                                v_next_kmh = 0.0
                                if not train.is_stopped:
                                    train.is_stopped = True
                                    if not is_dwelling_now:
                                        train.unplanned_stops += 1
                                        train.stop_start_time_sec = self.sim_time
                                        step_stops += 1

            if train.spec.direction == TrainDirection.SOUTHBOUND:
                train.current_km += dist_moved_km
            else:
                train.current_km -= dist_moved_km

            train.speed_kmh = v_next_kmh

            # G. Check Bridge Traversal & Flying Meets
            train_len_km = train.spec.length_m / 1000.0
            for b in self.bridges.values():
                # Is train inside bridge?
                inside = False
                if train.spec.direction == TrainDirection.SOUTHBOUND:
                    if (train.current_km >= b.k_start) and (train.current_km - train_len_km <= b.k_end):
                        inside = True
                else:
                    if (train.current_km <= b.k_end) and (train.current_km + train_len_km >= b.k_start):
                        inside = True

                if inside:
                    train.inside_bridge_id = b.bridge_id
                    train.min_speed_in_bottleneck = min(train.min_speed_in_bottleneck, train.speed_kmh)
                else:
                    if train.inside_bridge_id == b.bridge_id:
                        # Train just exited this bridge
                        train.inside_bridge_id = None
                        b.total_traversals += 1
                        # Did it achieve a flying meet? (Cruised/glided without dead stop)
                        if train.min_speed_in_bottleneck >= 30.0:
                            train.flying_meets_achieved += 1
                            b.flying_meets_count += 1
                            flying_meets_this_step += 1
                        train.min_speed_in_bottleneck = 999.0

            # H. Schedule delay tracking
            # Nominal progress calculation
            corridor_span_km = abs(train.spec.target_exit_km - train.spec.entry_position_km)
            progress_fraction = abs(train.current_km - train.spec.entry_position_km) / max(0.1, corridor_span_km)
            progress_fraction = min(1.0, max(0.0, progress_fraction))
            nominal_elapsed_at_curr_km = train.spec.nominal_run_time_sec * progress_fraction
            scheduled_epoch = train.spec.scheduled_entry_sec + nominal_elapsed_at_curr_km
            train.delay_sec = max(0.0, self.sim_time - scheduled_epoch)

            # I. Check Corridor Exit
            has_exited = False
            if train.spec.direction == TrainDirection.SOUTHBOUND:
                if train.current_km >= train.spec.target_exit_km:
                    has_exited = True
            else:
                if train.current_km <= train.spec.target_exit_km:
                    has_exited = True

            if has_exited:
                train.is_active = False
                train.is_finished = True
                train.exit_time_actual = self.sim_time
                train.speed_kmh = 0.0

        # 3. Calculate Step Rewards
        total_delay_this_step = sum(t.delay_sec for t in self.trains if t.is_active)
        r_delay = - (self.weights["delay_penalty"] * total_delay_this_step * (self.dt / 60.0))
        r_stop = - (self.weights["stop_penalty"] * step_stops)
        r_energy = - (self.weights["energy_loss_penalty"] * step_energy_loss_mj)
        r_flying = (self.weights["flying_meet_bonus"] * flying_meets_this_step)

        step_reward = r_delay + r_stop + r_energy + r_flying

        # 4. Episode Termination
        all_finished = all(t.is_finished for t in self.trains)
        time_limit_exceeded = (self.sim_time >= self.max_sim_sec)

        terminated = all_finished
        truncated = time_limit_exceeded and not all_finished

        obs = self._get_observation()
        info = self._get_info()
        return obs, step_reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """
        Constructs a normalized flat observation vector containing:
        - For each train: [is_active, position_norm, speed_norm, delay_norm, signal_aspect, dist_to_sig_norm]
        - For each bridge: [state, time_to_clear_norm, occupant_priority]
        """
        obs_elements = []
        for t in self.trains:
            obs_elements.extend([
                1.0 if t.is_active else 0.0,
                (t.current_km - CORRIDOR_NORTH_BOUND_KM) / CORRIDOR_LENGTH_KM,
                t.speed_kmh / 115.0,
                min(1.0, t.delay_sec / 600.0),
                float(t.signal_aspect_ahead) / 2.0,
                min(1.0, t.distance_to_signal_m / 3000.0)
            ])

        for b in self.bridges.values():
            time_to_clear = max(0.0, b.lock_expiry_sec - self.sim_time) if b.reversal_lock_active else 0.0
            obs_elements.extend([
                float(b.state) / 2.0,
                min(1.0, time_to_clear / 60.0),
                1.0 if b.reversal_lock_active else 0.0
            ])

        return np.array(obs_elements, dtype=np.float32)

    def _get_info(self) -> Dict[str, Any]:
        """Returns structured diagnostic and performance metrics."""
        delays = [t.delay_sec for t in self.trains]
        total_stops = sum(t.unplanned_stops for t in self.trains)
        total_energy_dissipated = sum(t.energy_dissipated_mj for t in self.trains)
        total_flying_meets = sum(t.flying_meets_achieved for t in self.trains)

        train_summaries = {}
        for t in self.trains:
            train_summaries[t.spec.train_id] = {
                "train_number": t.spec.train_number,
                "train_class": t.spec.train_class.value,
                "direction": t.spec.direction.value,
                "priority": t.spec.priority,
                "current_km": round(t.current_km, 3),
                "speed_kmh": round(t.speed_kmh, 1),
                "unplanned_stops": t.unplanned_stops,
                "energy_dissipated_mj": round(t.energy_dissipated_mj, 2),
                "traction_energy_mj": round(t.traction_energy_mj, 2),
                "delay_sec": round(t.delay_sec, 1),
                "flying_meets": t.flying_meets_achieved,
                "is_finished": t.is_finished
            }

        return {
            "sim_time": round(self.sim_time, 1),
            "step_count": self.step_count,
            "all_trains_finished": all(t.is_finished for t in self.trains),
            "total_unplanned_stops": total_stops,
            "total_energy_dissipated_mj": round(total_energy_dissipated, 2),
            "total_flying_meets": total_flying_meets,
            "avg_delay_sec": round(float(np.mean(delays)), 2) if delays else 0.0,
            "max_delay_sec": round(float(np.max(delays)), 2) if delays else 0.0,
            "trains": train_summaries,
            "bridges": {
                b.bridge_id: {
                    "state": b.state.name,
                    "reversal_lock_active": b.reversal_lock_active,
                    "occupant": b.current_occupant_id,
                    "total_traversals": b.total_traversals,
                    "flying_meets": b.flying_meets_count
                }
                for b in self.bridges.values()
            }
        }


# Alias for flexible spelling
CoastalBridgeRLDispatchEnv = CoastalBridgeRLDisptachEnv
