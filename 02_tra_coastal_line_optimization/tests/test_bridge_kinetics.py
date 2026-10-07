#!/usr/bin/env python3
"""
Unit tests for TRA Coastal Line bridge bottleneck kinetics and capacity model.
"""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, "04_bridge_bottleneck_model"))

from bridge_kinetics import Bridge, Train, BridgeKineticsEngine

class TestBridgeKinetics(unittest.TestCase):
    def setUp(self):
        self.engine = BridgeKineticsEngine()
        self.daan_bridge = Bridge("BRG03", "大安溪橋", "Daan River Bridge", 1100.0, 115.0)
        self.dajia_bridge = Bridge("BRG04", "大甲溪橋", "Dajia River Bridge", 1250.0, 115.0)
        self.emu3000 = Train("EMU3000", "新自強號", "Express", 244.0, 115.0)
        self.emu900 = Train("EMU900", "區間車", "Commuter", 203.0, 105.0)

    def test_traversal_time_kinetics(self):
        """Test physical traversal time matches (L_bridge + L_train) / speed."""
        t_daan = self.engine.traversal_time_sec(self.daan_bridge, self.emu3000)
        expected_time = (1100.0 + 244.0) / (115.0 / 3.6)
        self.assertAlmostEqual(t_daan, expected_time, places=2)
        # Should take ~42 seconds
        self.assertTrue(40.0 < t_daan < 45.0)

    def test_dajia_bridge_traversal(self):
        """Test 1250m Dajia bridge traversal for 10-car commuter train."""
        t_dajia = self.engine.traversal_time_sec(self.dajia_bridge, self.emu900)
        expected_time = (1250.0 + 203.0) / (105.0 / 3.6)
        self.assertAlmostEqual(t_dajia, expected_time, places=2)
        self.assertTrue(48.0 < t_dajia < 52.0)

    def test_direction_reversal_overhead(self):
        """Test reversal cycle includes switch throw and vital interlocking release."""
        cycle = self.engine.direction_reversal_cycle_sec(self.daan_bridge, self.emu3000)
        t_trav = self.engine.traversal_time_sec(self.daan_bridge, self.emu3000)
        overhead = cycle - t_trav
        self.assertEqual(overhead, 8.0 + 10.0 + 15.0) # 33.0 seconds

    def test_platooned_buffer_consistency(self):
        """Test platooned slot includes safety buffer matching reversal overhead."""
        slot_time = self.engine.platooned_two_train_slot_sec(self.daan_bridge, self.emu3000, self.emu900)
        trail_trav = self.engine.traversal_time_sec(self.daan_bridge, self.emu900)
        overhead = slot_time - self.engine.atp_block_headway_sec - trail_trav
        expected_overhead = self.engine.switch_throw_sec + self.engine.interlock_release_sec + self.engine.safety_buffer_sec
        self.assertAlmostEqual(overhead, expected_overhead, places=5) # 33.0 seconds

    def test_clockface_capacity_headroom(self):
        """Test that platooned utilization under 30-min window is strictly under 35%."""
        res_daan = self.engine.evaluate_30min_clockface_window(self.daan_bridge, self.emu3000, self.emu900)
        res_dajia = self.engine.evaluate_30min_clockface_window(self.dajia_bridge, self.emu3000, self.emu900)

        self.assertLess(res_daan["platooned_utilization_pct"], 30.0)
        self.assertLess(res_dajia["platooned_utilization_pct"], 30.0)
        self.assertEqual(res_daan["capacity_verdict"], "PASSES_ASSUMED_ARITHMETIC_THRESHOLD")
        self.assertEqual(res_dajia["capacity_verdict"], "PASSES_ASSUMED_ARITHMETIC_THRESHOLD")

    def test_free_buffer_magnitude(self):
        """Test that free buffer exceeds 20 minutes out of every 30-minute clockface cycle."""
        res_dajia = self.engine.evaluate_30min_clockface_window(self.dajia_bridge, self.emu3000, self.emu900)
        # Free buffer should be over 1,200 seconds (20 mins)
        self.assertGreater(res_dajia["platooned_free_buffer_sec"], 1200.0)

if __name__ == "__main__":
    unittest.main()
