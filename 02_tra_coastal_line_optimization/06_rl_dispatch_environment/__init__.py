"""
TRA Coastal Line exploratory bottleneck dispatch environment.

Provides simplified dynamic speed advisory, train kinematics, bridge mutual
exclusion, and fixed heuristic policies. Legacy ``RL`` identifiers are retained
for compatibility; no trained reinforcement-learning policy is implemented.
"""

from .env import (
    CoastalBridgeRLDisptachEnv,
    CoastalBridgeRLDispatchEnv,
    SpeedAdvisory,
    SignalAspect,
    BridgeReservationState,
    BridgeBottleneck,
    TrainLiveState,
)

from .traffic_generator import (
    TrafficGenerator,
    TrainSpec,
    TrainClass,
    TrainDirection,
    ROLLING_STOCK_SPECS,
    CORRIDOR_NORTH_BOUND_KM,
    CORRIDOR_SOUTH_BOUND_KM,
    CORRIDOR_LENGTH_KM,
)

from .policies import (
    FCFSPolicy,
    RuleBasedGreenWavePolicy,
    RLAgentPolicy,
)

__all__ = [
    "CoastalBridgeRLDisptachEnv",
    "CoastalBridgeRLDispatchEnv",
    "SpeedAdvisory",
    "SignalAspect",
    "BridgeReservationState",
    "BridgeBottleneck",
    "TrainLiveState",
    "TrafficGenerator",
    "TrainSpec",
    "TrainClass",
    "TrainDirection",
    "ROLLING_STOCK_SPECS",
    "CORRIDOR_NORTH_BOUND_KM",
    "CORRIDOR_SOUTH_BOUND_KM",
    "CORRIDOR_LENGTH_KM",
    "FCFSPolicy",
    "RuleBasedGreenWavePolicy",
    "RLAgentPolicy",
]
