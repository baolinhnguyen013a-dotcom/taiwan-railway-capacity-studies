#!/usr/bin/env python3
"""
Dispatch policies for the TRA Coastal Line exploratory environment.
Implements:
1. FCFSPolicy: Baseline 1 - Uncoordinated First-Come-First-Served dispatch.
   Trains cruise at maximum speed, ignoring upcoming bottleneck occupation,
   incurring hard stops at red signals.
2. RuleBasedGreenWavePolicy: Baseline 2 - Heuristic dynamic speed advisory.
   Preemptively steps down speed (Glide 90 km/h or Hold 60 km/h) based on
   distance and estimated clearance time to achieve smooth flying meets.
3. RLAgentPolicy: legacy-named fixed-weight analytical heuristic.
   It scores speed advisory tiers using static, hand-selected weights. It
   does not learn from data or update policy parameters.
"""

from typing import Dict, List, Optional, Any, Tuple
import math
import numpy as np

from .env import (
    CoastalBridgeRLDisptachEnv, SpeedAdvisory, SignalAspect,
    BridgeReservationState, TrainLiveState, BridgeBottleneck
)
from .traffic_generator import TrainDirection, TrainClass


class FCFSPolicy:
    """
    Baseline 1: Uncoordinated First-Come-First-Served Policy.
    Every train commands Cruise (v_max) at all times, without lookahead
    coordination or speed regulation.
    Trains run at maximum speed directly to the bridge entrance signal,
    incurring dead stops if the bridge is occupied or in reversal lock.
    """

    def __init__(self, name: str = "FCFS_Baseline"):
        self.name = name

    def act(self, env: CoastalBridgeRLDisptachEnv, obs: Optional[np.ndarray] = None) -> Dict[str, int]:
        actions: Dict[str, int] = {}
        for train in env.trains:
            # Always command full cruise speed
            actions[train.spec.train_id] = int(SpeedAdvisory.CRUISE)
        return actions


class RuleBasedGreenWavePolicy:
    """
    Baseline 2: Heuristic Rule-Based Green-Wave Policy.
    Calculates estimated clearance time for the next bottleneck bridge.
    When a conflict is pending, steps down approaching train speeds
    (Glide 90 km/h or Hold 60 km/h) to create a flying meet and prevent
    unplanned stops at the red signal.
    """

    def __init__(self, name: str = "RuleBased_GreenWave"):
        self.name = name

    def _estimate_bridge_clear_time(
        self,
        env: CoastalBridgeRLDisptachEnv,
        bridge: BridgeBottleneck,
        train: TrainLiveState
    ) -> float:
        """Estimates seconds until the bridge is fully cleared and unlocked for this train."""
        now = env.sim_time

        # If already reserved for this train, clearance time is 0
        if bridge.current_occupant_id == train.spec.train_id:
            return 0.0

        t_wait = 0.0
        # If in reversal lock, wait until lock expires
        if bridge.reversal_lock_active:
            t_wait = max(0.0, bridge.lock_expiry_sec - now)

        # If occupied by another train
        if bridge.current_occupant_id is not None:
            occ = next((tr for tr in env.trains if tr.spec.train_id == bridge.current_occupant_id), None)
            if occ and not occ.is_finished:
                v_mps = max(10.0, occ.speed_kmh / 3.6)
                train_len = occ.spec.length_m
                if occ.spec.direction == TrainDirection.SOUTHBOUND:
                    rem_dist_m = max(0.0, ((bridge.k_end + train_len / 1000.0) - occ.current_km) * 1000.0)
                else:
                    rem_dist_m = max(0.0, (occ.current_km - (bridge.k_start - train_len / 1000.0)) * 1000.0)

                t_traversal_rem = rem_dist_m / v_mps
                # If opposing train, must wait for reversal buffer (33s)
                if occ.spec.direction != train.spec.direction:
                    t_wait = max(t_wait, t_traversal_rem + env.total_reversal_overhead_sec)
                else:
                    # Same direction headway
                    t_wait = max(t_wait, t_traversal_rem + 15.0)

        # Also inspect approaching opposing trains with higher priority or earlier arrival
        _, _, my_dist_m = env._find_next_bridge_ahead(train)
        for opp in env.trains:
            if not opp.is_active or opp.is_finished or opp.spec.train_id == train.spec.train_id:
                continue
            if opp.spec.direction != train.spec.direction:
                b_opp, _, opp_dist_m = env._find_next_bridge_ahead(opp)
                if b_opp == bridge and 0.0 <= opp_dist_m <= 4000.0:
                    if (opp.spec.priority < train.spec.priority) or (
                        opp.spec.priority == train.spec.priority and opp_dist_m < my_dist_m
                    ):
                        opp_v_mps = max(15.0, opp.speed_kmh / 3.6)
                        opp_eta = opp_dist_m / opp_v_mps
                        opp_trav = (bridge.length_m + opp.spec.length_m) / opp_v_mps
                        t_opp_clear = opp_eta + opp_trav + env.total_reversal_overhead_sec
                        t_wait = max(t_wait, t_opp_clear)

        return t_wait

    def act(self, env: CoastalBridgeRLDisptachEnv, obs: Optional[np.ndarray] = None) -> Dict[str, int]:
        actions: Dict[str, int] = {}
        for train in env.trains:
            if not train.is_active or train.is_finished:
                actions[train.spec.train_id] = int(SpeedAdvisory.CRUISE)
                continue

            bridge, entry_km, dist_m = env._find_next_bridge_ahead(train)
            if bridge is None or dist_m <= 0.0 or dist_m > 4500.0:
                # Far away or already through
                actions[train.spec.train_id] = int(SpeedAdvisory.CRUISE)
                continue

            t_clear_sec = self._estimate_bridge_clear_time(env, bridge, train)
            if t_clear_sec <= 3.0:
                # Bridge clear or clearing immediately: Full speed ahead
                actions[train.spec.train_id] = int(SpeedAdvisory.CRUISE)
                continue

            # Required speed to arrive in t_clear_sec seconds: v = d / t
            target_v_mps = dist_m / t_clear_sec
            target_v_kmh = target_v_mps * 3.6

            # Select discrete speed advisory tier
            if target_v_kmh >= 95.0:
                actions[train.spec.train_id] = int(SpeedAdvisory.CRUISE)
            elif target_v_kmh >= 65.0:
                actions[train.spec.train_id] = int(SpeedAdvisory.GLIDE)  # 90 km/h
            elif target_v_kmh >= 20.0:
                actions[train.spec.train_id] = int(SpeedAdvisory.HOLD)   # 60 km/h
            else:
                # Coast with HOLD as long as distance to stop boundary allows safe approach
                if dist_m > 60.0:
                    actions[train.spec.train_id] = int(SpeedAdvisory.HOLD)
                else:
                    actions[train.spec.train_id] = int(SpeedAdvisory.STOP)

        return actions


class RLAgentPolicy:
    """
    Legacy-named fixed-weight dynamic speed advisory heuristic.

    Evaluates a hand-written multi-objective score:
      Q(s, a) = - w_delay * DelayCost(s, a)
                - w_stop * StopProbabilityCost(s, a)
                - w_energy * KineticDissipation(s, a)
                + w_flying * FlyingMeetUtility(s, a)

    The weights below are static assumptions. ``q_table`` is retained only for
    API compatibility and is never populated. ``train`` runs evaluation
    episodes but performs no parameter or Q-value update.
    """

    def __init__(self, name: str = "RL_Agent_Optimized"):
        self.name = name
        # Static, hand-selected scoring weights (not learned parameters)
        self.w_delay = 0.08
        self.w_stop = 45.0
        self.w_energy = 0.03
        self.w_flying = 70.0
        self.q_table: Dict[Tuple, np.ndarray] = {}
        self.lr = 0.10
        self.gamma = 0.95
        self.epsilon = 0.05

    def _state_discretization(
        self,
        dist_m: float,
        speed_kmh: float,
        t_clear_sec: float,
        priority: int
    ) -> Tuple[int, int, int, int]:
        """Discretizes continuous state features into compact bins for Q-evaluation."""
        # Distance bin: 0: <300m, 1: 300-1200m, 2: 1200-2500m, 3: >2500m
        if dist_m < 300.0:
            d_bin = 0
        elif dist_m < 1200.0:
            d_bin = 1
        elif dist_m < 2500.0:
            d_bin = 2
        else:
            d_bin = 3

        # Speed bin: 0: <20 km/h, 1: 20-65 km/h, 2: 65-95 km/h, 3: >=95 km/h
        if speed_kmh < 20.0:
            v_bin = 0
        elif speed_kmh < 65.0:
            v_bin = 1
        elif speed_kmh < 95.0:
            v_bin = 2
        else:
            v_bin = 3

        # Clearance time bin: 0: <=5s, 1: 5-25s, 2: 25-60s, 3: >60s
        if t_clear_sec <= 5.0:
            t_bin = 0
        elif t_clear_sec <= 25.0:
            t_bin = 1
        elif t_clear_sec <= 60.0:
            t_bin = 2
        else:
            t_bin = 3

        p_bin = min(3, priority)
        return (d_bin, v_bin, t_bin, p_bin)

    def _evaluate_action_value(
        self,
        action: SpeedAdvisory,
        dist_m: float,
        current_speed_kmh: float,
        max_speed_kmh: float,
        t_clear_sec: float,
        priority: int,
        mass_tonnes: float
    ) -> float:
        """
        Analytic action score based on a hand-written reward surrogate:
        Balances kinetic dissipation, stop risk, schedule delay, and flying meet reward.
        """
        # Target speed for this action
        if action == SpeedAdvisory.CRUISE:
            target_v_kmh = max_speed_kmh
        elif action == SpeedAdvisory.GLIDE:
            target_v_kmh = min(max_speed_kmh, 90.0)
        elif action == SpeedAdvisory.HOLD:
            target_v_kmh = min(max_speed_kmh, 60.0)
        else:
            target_v_kmh = 0.0

        target_v_mps = max(0.1, target_v_kmh / 3.6)
        eta_to_bridge = dist_m / target_v_mps

        # Stop probability risk: high if train arrives before bridge is clear
        early_arrival_sec = t_clear_sec - eta_to_bridge
        if early_arrival_sec > 5.0 and dist_m < 1500.0:
            # Train will hit red signal and be forced to stop dead
            stop_risk = 1.0
        elif early_arrival_sec > 0.0:
            stop_risk = 0.5
        else:
            stop_risk = 0.0

        # Energy dissipation penalty
        delta_v = max(0.0, current_speed_kmh - target_v_kmh) / 3.6
        energy_loss_mj = 0.5 * (mass_tonnes * 1000.0) * (delta_v ** 2) / 1e6

        # Additional loss if stopping dead
        if stop_risk > 0.0:
            full_stop_loss_mj = 0.5 * (mass_tonnes * 1000.0) * ((target_v_kmh / 3.6) ** 2) / 1e6
            energy_loss_mj += full_stop_loss_mj * stop_risk

        # Delay impact (travel time difference from free-flow cruise)
        t_free_flow = dist_m / (max_speed_kmh / 3.6)
        delay_cost = max(0.0, eta_to_bridge - t_free_flow)
        if priority == 1:
            delay_cost *= 1.5  # Higher weight on Express delays

        # Flying meet bonus: achieved if passing bridge smoothly without stop
        flying_bonus = self.w_flying if (stop_risk < 0.2 and dist_m < 3000.0 and target_v_kmh >= 40.0) else 0.0

        q_val = - (self.w_delay * delay_cost) \
                - (self.w_stop * stop_risk) \
                - (self.w_energy * energy_loss_mj) \
                + flying_bonus

        return q_val

    def act(self, env: CoastalBridgeRLDisptachEnv, obs: Optional[np.ndarray] = None) -> Dict[str, int]:
        actions: Dict[str, int] = {}
        rule_helper = RuleBasedGreenWavePolicy()

        for train in env.trains:
            if not train.is_active or train.is_finished:
                actions[train.spec.train_id] = int(SpeedAdvisory.CRUISE)
                continue

            bridge, entry_km, dist_m = env._find_next_bridge_ahead(train)
            if bridge is None or dist_m <= 0.0 or dist_m > 4000.0:
                actions[train.spec.train_id] = int(SpeedAdvisory.CRUISE)
                continue

            t_clear_sec = rule_helper._estimate_bridge_clear_time(env, bridge, train)
            state_key = self._state_discretization(dist_m, train.speed_kmh, t_clear_sec, train.spec.priority)

            # Evaluate Q-values across all 4 candidate discrete actions
            q_values = []
            for act_candidate in [SpeedAdvisory.CRUISE, SpeedAdvisory.GLIDE, SpeedAdvisory.HOLD, SpeedAdvisory.STOP]:
                q = self._evaluate_action_value(
                    action=act_candidate,
                    dist_m=dist_m,
                    current_speed_kmh=train.speed_kmh,
                    max_speed_kmh=train.spec.max_speed_kmh,
                    t_clear_sec=t_clear_sec,
                    priority=train.spec.priority,
                    mass_tonnes=train.spec.mass_tonnes
                )
                q_values.append(q)

            best_action_idx = int(np.argmax(q_values))
            actions[train.spec.train_id] = best_action_idx

        return actions

    def train(self, env: CoastalBridgeRLDisptachEnv, episodes: int = 50) -> Dict[str, Any]:
        """
        Run repeated evaluation episodes without learning.

        This compatibility method does not update weights, q_table, or any
        other policy parameter. The returned rewards are descriptive only.
        """
        rewards_history = []
        for ep in range(episodes):
            obs, info = env.reset(stochastic=(ep % 2 == 1), seed=100 + ep)
            terminated = False
            truncated = False
            ep_reward = 0.0

            while not (terminated or truncated):
                action_dict = self.act(env, obs)
                obs, reward, terminated, truncated, info = env.step(action_dict)
                ep_reward += reward

            rewards_history.append(ep_reward)

        return {
            "episodes_trained": episodes,
            "final_episode_reward": round(rewards_history[-1], 2),
            "mean_reward": round(float(np.mean(rewards_history)), 2)
        }
