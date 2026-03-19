"""
core/constants.py
─────────────────
All hardware constants derived from RoachBotV2.ino.
6-leg configuration — each leg has an independent encoder.
"""

# ─── Encoder math (from .ino: LEFT_COUNTS_180 = 234) ────────────────────────
COUNTS_PER_180: int   = 234
DEG_PER_COUNT:  float = 180.0 / COUNTS_PER_180   # 0.76923...°/count
MAX_COUNT:      int   = 468                        # 360° equivalent

# ─── Leg identifiers ─────────────────────────────────────────────────────────
LEG_NAMES: list[str] = ["FL", "ML", "RL", "FR", "MR", "RR"]
LEFT_LEGS:  list[str] = ["FL", "ML", "RL"]
RIGHT_LEGS: list[str] = ["FR", "MR", "RR"]
LEG_SIDE: dict[str, str] = {
    "FL": "L", "ML": "L", "RL": "L",
    "FR": "R", "MR": "R", "RR": "R",
}

# ─── Serial protocol ─────────────────────────────────────────────────────────
SERIAL_BAUD:    int   = 115_200
SERIAL_TIMEOUT: float = 0.05

# ─── PWM / PID  (from .ino) ──────────────────────────────────────────────────
MAX_PWM:      int   = 180
MIN_PWM:      int   = 100
POSITION_TOL: int   = 4
KP:           float = 0.55

# ─── 3-D robot geometry  (world units) ───────────────────────────────────────
BODY_W: float = 4.0   # left-right width
BODY_L: float = 7.0   # front-back length
BODY_H: float = 1.4   # height

# Shoulder attachment positions on the side walls
# Y positions for the three leg rows (front, mid, rear)
LEG_Y_OFFSETS: list[float] = [+2.6, 0.0, -2.6]
LEG_X_OFFSET:  float = BODY_W / 2   # x = ±BODY_W/2 (on the side wall)

# Single stump length (shoulder → foot tip)
# Arc leg geometry (see visualizer_3d/geometry.py)
ARC_RADIUS:   float = 2.4   # curvature radius of the limb
ARC_SPAN_DEG: float = 135   # degrees the arc subtends
STUMP_LEN:    float = 2.4   # kept for gl_widget grid offset compat

# ─── Colour palette — (R, G, B, A) floats 0–1 for pyqtgraph GL ──────────────
C = {
    "bg":         (0.05, 0.07, 0.06, 1.0),
    "grid":       (0.10, 0.22, 0.12, 1.0),
    "body":       (0.08, 0.17, 0.10, 1.0),
    "body_edge":  (0.18, 1.00, 0.42, 1.0),
    "leg_L":      (0.00, 0.90, 1.00, 1.0),   # cyan  — left stumps
    "leg_R":      (1.00, 0.43, 0.22, 1.0),   # orange — right stumps
    "foot_L":     (0.00, 1.00, 0.80, 1.0),   # bright cyan tip
    "foot_R":     (1.00, 0.70, 0.10, 1.0),   # bright orange tip
    "joint":      (0.85, 0.90, 0.85, 1.0),   # light grey shoulder pivot
    "foot":       (0.22, 1.00, 0.42, 1.0),
}

# ─── Qt stylesheet hex versions ───────────────────────────────────────────────
QC = {
    "bg":        "#0d120e",
    "panel":     "#0e1a10",
    "border":    "#1e4228",
    "title":     "#3aff6c",
    "text":      "#cfffda",
    "dim":       "#4a7a50",
    "leg_L":     "#00e5ff",
    "leg_R":     "#ff6e3a",
    "cw":        "#00e5ff",
    "ccw":       "#ff6e3a",
    "connected": "#3aff6c",
    "error":     "#ff4a4a",
    "warn":      "#ffb830",
}
