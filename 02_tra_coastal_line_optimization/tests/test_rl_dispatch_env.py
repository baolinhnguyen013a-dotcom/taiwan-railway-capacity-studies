#!/usr/bin/env python3
"""
Unit tests for TRA Coastal Line RL Dispatch Environment and Policies.
Validates:
1. Physical mutual exclusion & collision prevention over single-track bridges.
2. Kinematic updates and discrete speed advisory actions (Cruise, Glide, Hold, Stop).
3. Reward formulation (penalties for delays, stops, energy losses, flying meet bonus).
4. Real-world Coastal Line train specs (280, 288, 2512, 2518, 7501).
5. Robust execution of FCFS, Rule-Based Green-Wave, and RL policies without exceptions.
"""

import os
import sys
import unittest
import importlib
import numpy as np

# Ensure 06_rl_dispatch_environment package can be imported
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

pkg = importlib.import_module("06_rl_dispatch_environment")
CoastalBridgeRLDisptachEnv = pkg.CoastalBridgeRLDisptachEnv
CoastalBridgeRLDispatchEnv = pkg.CoastalBridgeRLDispatchEnv
SpeedAdvisory = pkg.SpeedAdvisory
SignalAspect = pkg.SignalAspect
BridgeReservationState = pkg.BridgeReservationState
TrafficGenerator = pkg.TrafficGenerator
TrainDirection = pkg.TrainDirection
TrainClass = pkg.TrainClass
FCFSPolicy = pkg.FCFSPolicy
RuleBasedGreenWavePolicy = pkg.RuleBasedGreenWavePolicy
RLAgentPolicy = pkg.RLAgentPolicy


class TestCoastalBridgeRLEnvironment(unittest.TestCase):

    def setUp(self):
        self.generator = TrafficGenerator()
        self.env = CoastalBridgeRLDisptachEnv(
            traffic_generator=self.generator,
            dt_seconds=1.0,
            max_simulation_seconds=1200.0
        )

    def test_alias_equivalence(self):
        """Verify both spellings (CoastalBridgeRLDisptachEnv and CoastalBridgeRLDispatchEnv) exist and match."""
        self.assertIs(CoastalBridgeRLDisptachEnv, CoastalBridgeRLDispatchEnv)

    def test_traffic_generation_train_ids(self):
        """Verify real-world train IDs and specs match TRA Coastal Line specifications."""
        trains = self.generator.generate_deterministic_traffic()
        train_map = {t.train_id: t for t in trains}

        # Check all 5 required trains
        expected_ids = {"280", "288", "2512", "2518", "7501"}
        self.assertEqual(set(train_map.keys()), expected_ids)

        # 280: Express NB (EMU3000)
        self.assertEqual(train_map["280"].train_class, TrainClass.EXPRESS)
        self.assertEqual(train_map["280"].direction, TrainDirection.NORTHBOUND)
        self.assertEqual(train_map["280"].length_m, 244.0)
        self.assertEqual(train_map["280"].max_speed_kmh, 115.0)
        self.assertEqual(train_map["280"].priority, 1)

        # 288: Express SB (EMU3000)
        self.assertEqual(train_map["288"].train_class, TrainClass.EXPRESS)
        self.assertEqual(train_map["288"].direction, TrainDirection.SOUTHBOUND)
        self.assertEqual(train_map["288"].priority, 1)

        # 2512: Commuter NB (EMU900)
        self.assertEqual(train_map["2512"].train_class, TrainClass.COMMUTER)
        self.assertEqual(train_map["2512"].direction, TrainDirection.NORTHBOUND)
        self.assertEqual(train_map["2512"].length_m, 203.0)
        self.assertEqual(train_map["2512"].priority, 2)

        # 2518: Commuter SB (EMU900)
        self.assertEqual(train_map["2518"].train_class, TrainClass.COMMUTER)
        self.assertEqual(train_map["2518"].direction, TrainDirection.SOUTHBOUND)
        self.assertEqual(train_map["2518"].priority, 2)

        # 7501: Freight SB
        self.assertEqual(train_map["7501"].train_class, TrainClass.FREIGHT)
        self.assertEqual(train_map["7501"].direction, TrainDirection.SOUTHBOUND)
        self.assertEqual(train_map["7501"].length_m, 350.0)
        self.assertEqual(train_map["7501"].max_speed_kmh, 75.0)
        self.assertEqual(train_map["7501"].priority, 3)

    def test_stochastic_traffic_generation(self):
        """Verify stochastic traffic applies reasonable perturbation delays."""
        trains = self.generator.generate_stochastic_traffic(seed=42)
        self.assertEqual(len(trains), 5)
        # Verify delay values are non-negative
        for t in trains:
            self.assertGreaterEqual(t.delay_sec, 0.0)
            self.assertGreaterEqual(t.actual_entry_sec, t.scheduled_entry_sec)

    def test_kinematic_updates_acceleration(self):
        """Verify trains accelerate smoothly according to nominal acceleration specs."""
        obs, info = self.env.reset()
        t288 = next(t for t in self.env.trains if t.spec.train_id == "288")
        
        # Step environment with CRUISE advisory
        init_speed = t288.speed_kmh
        obs, reward, term, trunc, info = self.env.step({t288.spec.train_id: SpeedAdvisory.CRUISE})
        
        # Speed should increase by a * dt * 3.6
        expected_dv = t288.spec.nominal_accel_mps2 * self.env.dt * 3.6
        self.assertAlmostEqual(t288.speed_kmh - init_speed, expected_dv, places=2)

    def test_speed_advisory_tiers(self):
        """Verify discrete speed advisory mapping (Glide 90 km/h, Hold 60 km/h, Stop 0 km/h)."""
        target_cruise = self.env._get_target_speed_for_advisory(SpeedAdvisory.CRUISE, 115.0)
        target_glide = self.env._get_target_speed_for_advisory(SpeedAdvisory.GLIDE, 115.0)
        target_hold = self.env._get_target_speed_for_advisory(SpeedAdvisory.HOLD, 115.0)
        target_stop = self.env._get_target_speed_for_advisory(SpeedAdvisory.STOP, 115.0)

        self.assertEqual(target_cruise, 115.0)
        self.assertEqual(target_glide, 90.0)
        self.assertEqual(target_hold, 60.0)
        self.assertEqual(target_stop, 0.0)

    def test_mutual_exclusion_collision_prevention(self):
        """
        Critical safety test:
        Verify that two opposing trains approaching a single-track bridge cannot both enter.
        The entrance signal must stay RED for the un-cleared train, stopping it before entry.
        """
        obs, info = self.env.reset()
        daan_bridge = self.env.bridges["BRG_DAAN"]

        # Run simulation until Train 288 (SB) occupies Daan River Bridge
        found_in_bridge = False
        for step in range(200):
            obs, reward, term, trunc, info = self.env.step([int(SpeedAdvisory.CRUISE)] * len(self.env.trains))
            # Check if any bridge has multiple occupants of opposing directions
            nb_inside = [t for t in self.env.trains if t.inside_bridge_id == "BRG_DAAN" and t.spec.direction == TrainDirection.NORTHBOUND]
            sb_inside = [t for t in self.env.trains if t.inside_bridge_id == "BRG_DAAN" and t.spec.direction == TrainDirection.SOUTHBOUND]

            # Mutual exclusion: opposing directions NEVER simultaneously inside
            self.assertFalse(len(nb_inside) > 0 and len(sb_inside) > 0, "COLLISION HAZARD: Opposing trains in bridge simultaneously!")

    def test_reversal_safety_buffer_timing(self):
        """Verify 33.0s total reversal buffer (15s buffer + 8s switch + 10s route release)."""
        self.assertEqual(self.env.total_reversal_overhead_sec, 33.0)
        self.assertEqual(self.env.switch_throw_sec, 8.0)
        self.assertEqual(self.env.interlock_release_sec, 10.0)
        self.assertEqual(self.env.safety_buffer_sec, 15.0)

    def test_reward_penalties(self):
        """Verify reward structure applies penalties for stops and energy dissipation."""
        obs, info = self.env.reset()
        t288 = next(t for t in self.env.trains if t.spec.train_id == "288")
        
        # Accelerate train first
        for _ in range(10):
            self.env.step({t288.spec.train_id: SpeedAdvisory.CRUISE})
        
        self.assertGreater(t288.speed_kmh, 10.0)

        # Now force full emergency stop
        obs, reward, term, trunc, info = self.env.step({t288.spec.train_id: SpeedAdvisory.STOP})
        
        # When train is forced to brake, reward should be negative due to energy loss
        self.assertLess(reward, 0.0)

    def test_fcfs_policy_executes_without_errors(self):
        """Verify FCFSPolicy executes full episode cleanly."""
        obs, info = self.env.reset()
        policy = FCFSPolicy()
        total_reward = 0.0

        for _ in range(400):
            actions = policy.act(self.env, obs)
            obs, reward, terminated, truncated, info = self.env.step(actions)
            total_reward += reward
            if terminated or truncated:
                break

        self.assertIsInstance(total_reward, float)
        self.assertIn("trains", info)
        self.assertIn("bridges", info)

    def test_rule_based_policy_executes_without_errors(self):
        """Verify RuleBasedGreenWavePolicy executes full episode cleanly."""
        obs, info = self.env.reset()
        policy = RuleBasedGreenWavePolicy()
        total_reward = 0.0

        for _ in range(400):
            actions = policy.act(self.env, obs)
            obs, reward, terminated, truncated, info = self.env.step(actions)
            total_reward += reward
            if terminated or truncated:
                break

        self.assertIsInstance(total_reward, float)

    def test_rl_agent_policy_executes_without_errors(self):
        """Verify RLAgentPolicy executes full episode cleanly."""
        obs, info = self.env.reset()
        policy = RLAgentPolicy()
        total_reward = 0.0

        for _ in range(400):
            actions = policy.act(self.env, obs)
            obs, reward, terminated, truncated, info = self.env.step(actions)
            total_reward += reward
            if terminated or truncated:
                break

        self.assertIsInstance(total_reward, float)

    def test_kinematic_updates_deceleration(self):
        """Verify deceleration adheres to nominal deceleration specs."""
        obs, info = self.env.reset()
        t288 = next(t for t in self.env.trains if t.spec.train_id == "288")
        
        # Accelerate to reasonable speed
        for _ in range(15):
            self.env.step({t288.spec.train_id: SpeedAdvisory.CRUISE})
            
        speed_before = t288.speed_kmh
        # Now command HOLD (60 km/h) or deceleration
        self.env.step({t288.spec.train_id: SpeedAdvisory.HOLD})
        speed_after = t288.speed_kmh
        
        expected_decel = t288.spec.nominal_decel_mps2 * self.env.dt * 3.6
        self.assertAlmostEqual(speed_before - speed_after, expected_decel, places=2)

    def test_priority_bottleneck_assignment(self):
        """Verify higher priority Express (1) gets preference over Commuter (2) or Freight (3)."""
        trains = self.generator.generate_deterministic_traffic()
        t_express = next(t for t in trains if t.train_class == TrainClass.EXPRESS)
        t_commuter = next(t for t in trains if t.train_class == TrainClass.COMMUTER)
        t_freight = next(t for t in trains if t.train_class == TrainClass.FREIGHT)
        
        self.assertLess(t_express.priority, t_commuter.priority)
        self.assertLess(t_commuter.priority, t_freight.priority)

    def test_greenwave_avoids_stops_compared_to_fcfs(self):
        """Verify Rule-Based Green-Wave and RL policies avoid unplanned stops compared to uncoordinated FCFS."""
        env = CoastalBridgeRLDisptachEnv(max_simulation_seconds=1600.0)
        
        # 1. Evaluate FCFS
        obs, info = env.reset()
        fcfs = FCFSPolicy()
        for _ in range(1600):
            obs, r, term, trunc, info_fcfs = env.step(fcfs.act(env, obs))
            if term or trunc:
                break
                
        # 2. Evaluate RuleBased
        obs, info = env.reset()
        rule = RuleBasedGreenWavePolicy()
        for _ in range(1600):
            obs, r, term, trunc, info_rule = env.step(rule.act(env, obs))
            if term or trunc:
                break
                
        # 3. Evaluate RL Agent
        obs, info = env.reset()
        rl = RLAgentPolicy()
        for _ in range(1600):
            obs, r, term, trunc, info_rl = env.step(rl.act(env, obs))
            if term or trunc:
                break
                
        # FCFS incurs unplanned stops, while Green-Wave achieves 0 stops and superior flying meets
        self.assertGreater(info_fcfs["total_unplanned_stops"], 0)
        self.assertEqual(info_rule["total_unplanned_stops"], 0)
        self.assertEqual(info_rl["total_unplanned_stops"], 0)
        self.assertGreaterEqual(info_rl["total_flying_meets"], info_fcfs["total_flying_meets"])


if __name__ == "__main__":
    unittest.main()
