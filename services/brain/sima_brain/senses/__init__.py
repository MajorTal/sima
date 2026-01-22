"""
Senses package - Interoceptive and environmental awareness for Sima.

This package provides sensory data collection for The Brain's cognitive loop.
Senses are divided into:

Fast Senses (collected every tick):
- Heartbeat Rate: CPU utilization %
- Breathing Rate: Memory utilization %
- Thought Burden: Context tokens as % of window
- Tiredness: Hours since last sleep

Slow Senses (cached, refreshed on schedule):
- Weather: Amsterdam conditions (every 15 minutes)
"""

from .collector import SenseCollector
from .heartbeat import HeartbeatSense
from .breathing import BreathingSense
from .thought_burden import ThoughtBurdenSense
from .tiredness import TirednessSense
from .weather import WeatherSense

__all__ = [
    "SenseCollector",
    "HeartbeatSense",
    "BreathingSense",
    "ThoughtBurdenSense",
    "TirednessSense",
    "WeatherSense",
]
