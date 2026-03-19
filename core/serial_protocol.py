"""
core/serial_protocol.py
────────────────────────
Parses every serial line the ESP32 can send.

Supported formats
─────────────────
1. 6-leg canonical (from arduino/serial_6leg.ino):
       ENC:FL=120,ML=80,RL=45,FR=100,MR=60,RR=30

2. Legacy LEFT-ONLY test output (original .ino):
       [LEFT 0->180] Lseg=120/234  (92.3 deg)
   → mapped to leg "FL" only (left front = first left leg in test)

3. Raw pair (simple addition you can drop into any sketch):
       L:120 R:80
   → maps L→FL,ML,RL all same; R→FR,MR,RR all same (legacy compat)

4. Individual leg line (verbose debug):
       LEG:FL counts=120 deg=92.31

Returns
───────
dict[str, int] | None   — {leg_name: count_value} or None if unrecognised
"""

import re
from typing import Optional

from core.constants import LEG_NAMES

# ─── Pattern 1: ENC:FL=120,ML=80,... ─────────────────────────────────────────
_PAT_CANONICAL = re.compile(
    r"ENC:"
    r"FL=(-?\d+),ML=(-?\d+),RL=(-?\d+),"
    r"FR=(-?\d+),MR=(-?\d+),RR=(-?\d+)"
)

# ─── Pattern 2: Lseg=120/234 (legacy test) ───────────────────────────────────
_PAT_LSEG = re.compile(r"Lseg=(-?\d+)/\d+")
_PAT_RSEG = re.compile(r"Rseg=(-?\d+)/\d+")

# ─── Pattern 3: L:120 R:80 ───────────────────────────────────────────────────
_PAT_LR = re.compile(r"L:(-?\d+)\s+R:(-?\d+)")

# ─── Pattern 4: LEG:FL counts=120 ────────────────────────────────────────────
_PAT_SINGLE = re.compile(
    r"LEG:([A-Z]{2})\s+counts=(-?\d+)"
)


def parse_line(line: str) -> Optional[dict[str, int]]:
    """
    Parse one Arduino serial line.
    Returns dict mapping leg names → encoder counts, or None.
    """
    line = line.strip()
    if not line:
        return None

    # ── 1. Canonical 6-leg ────────────────────────────────────
    m = _PAT_CANONICAL.match(line)
    if m:
        vals = [int(x) for x in m.groups()]
        return dict(zip(LEG_NAMES, vals))

    # ── 2. Legacy Lseg / Rseg ────────────────────────────────
    ml = _PAT_LSEG.search(line)
    mr = _PAT_RSEG.search(line)
    if ml or mr:
        result: dict[str, int] = {}
        if ml:
            c = int(ml.group(1))
            result.update({"FL": c, "ML": c, "RL": c})
        if mr:
            c = int(mr.group(1))
            result.update({"FR": c, "MR": c, "RR": c})
        return result if result else None

    # ── 3. L:x R:y ───────────────────────────────────────────
    m = _PAT_LR.search(line)
    if m:
        lc, rc = int(m.group(1)), int(m.group(2))
        return {
            "FL": lc, "ML": lc, "RL": lc,
            "FR": rc, "MR": rc, "RR": rc,
        }

    # ── 4. Single leg ────────────────────────────────────────
    m = _PAT_SINGLE.search(line)
    if m:
        leg, cnt = m.group(1), int(m.group(2))
        if leg in LEG_NAMES:
            return {leg: cnt}

    return None
