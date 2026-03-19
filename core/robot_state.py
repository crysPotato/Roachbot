"""
core/robot_state.py
────────────────────
Shared state for all 6 legs.

Direction convention (matches ESP32 sign of encoder counts):
  positive counts → CW  rotation
  negative counts → CCW rotation

No separate direction field — sign of counts IS the direction.
"""

from dataclasses import dataclass, field
from core.constants import LEG_NAMES, DEG_PER_COUNT

import math


@dataclass
class LegState:
    name: str
    counts: int = 0   # signed: + = CW, - = CCW

    @property
    def angle_deg(self) -> float:
        """Effective position 0–360°. Negative counts wrap correctly."""
        return (self.counts * DEG_PER_COUNT) % 360.0

    @property
    def angle_rad(self) -> float:
        return math.radians(self.angle_deg)

    @property
    def is_cw(self) -> bool:
        return self.counts >= 0

    @property
    def direction_label(self) -> str:
        return "CW ↻" if self.is_cw else "CCW ↺"


@dataclass
class RobotState:
    legs: dict = field(
        default_factory=lambda: {n: LegState(name=n) for n in LEG_NAMES}
    )
    mode: str = "idle"   # "idle" | "simulation" | "live"

    def set_counts(self, leg: str, counts: int) -> None:
        if leg in self.legs:
            self.legs[leg].counts = int(counts)

    def set_all_counts(self, data: dict) -> None:
        for leg, c in data.items():
            self.set_counts(leg, c)

    def negate_counts(self, leg: str) -> None:
        """Flip CW↔CCW by negating counts."""
        if leg in self.legs:
            self.legs[leg].counts = -self.legs[leg].counts

    def reset_leg(self, leg: str) -> None:
        if leg in self.legs:
            self.legs[leg].counts = 0

    def reset_all(self) -> None:
        for leg in self.legs:
            self.reset_leg(leg)

    def snapshot(self) -> dict:
        """Thread-safe copy: {leg: (counts, angle_deg, is_cw)}"""
        return {
            n: (ls.counts, ls.angle_deg, ls.is_cw)
            for n, ls in self.legs.items()
        }
