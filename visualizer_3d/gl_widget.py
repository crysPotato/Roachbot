"""
visualizer_3d/gl_widget.py
───────────────────────────
3D OpenGL view of the RoachBotV2.

Per-leg GL items (3 each):
  [0]  arc mesh      — curved limb  (updated every frame)
  [1]  shoulder ball — fixed pivot  (built once)
  [2]  foot ball     — arc tip      (updated every frame)

No text labels on the limbs — readout lives in the status footer only.
"""

import numpy as np
import pyqtgraph.opengl as gl

from core.constants import (
    BODY_W, BODY_H, BODY_L,
    LEG_NAMES, LEG_SIDE, LEG_Y_OFFSETS, LEG_X_OFFSET,
    STUMP_LEN, C,
)
from core.robot_state import RobotState
from visualizer_3d.geometry import (
    arc_leg_mesh, arc_leg_tip,
    cylinder_mesh, box_mesh, sphere_mesh,
)

_LEG_ROW = {"FL": 0, "ML": 1, "RL": 2, "FR": 0, "MR": 1, "RR": 2}

# Smaller, tighter arc
_ARC_R    = 1.5    # was 2.4 — shorter radius = smaller limbs
_ARC_SPAN = 110    # was 135 — slightly less sweep arc


def _shoulder_pos(leg: str) -> np.ndarray:
    side = LEG_SIDE[leg]
    row  = _LEG_ROW[leg]
    x    = -LEG_X_OFFSET if side == "L" else LEG_X_OFFSET
    y    = LEG_Y_OFFSETS[row]
    return np.array([x, y, 0.0], dtype=float)


class RobotGLWidget(gl.GLViewWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        bg = C["bg"]
        self.setBackgroundColor((int(bg[0]*255), int(bg[1]*255),
                                  int(bg[2]*255), int(bg[3]*255)))
        self.setCameraPosition(distance=22, elevation=20, azimuth=-40)

        self._leg_items: dict[str, list] = {}
        self._build_static_scene()
        self._build_all_legs()

    # ── Static scene ──────────────────────────────────────────────────────────
    def _build_static_scene(self):
        grid = gl.GLGridItem()
        grid.setSize(40, 40)
        grid.setSpacing(2, 2)
        grid.translate(0, 0, -BODY_H / 2 - _ARC_R - 1.0)
        r, g, b, a = C["grid"]
        grid.setColor((r, g, b, a))
        self.addItem(grid)

        # Box body
        self.addItem(gl.GLMeshItem(
            meshdata=box_mesh(np.zeros(3), np.array([BODY_W, BODY_L, BODY_H])),
            smooth=False, color=C["body"],
            drawEdges=True, edgeColor=C["body_edge"],
        ))

        # Front marker dot
        self.addItem(gl.GLMeshItem(
            meshdata=sphere_mesh(np.array([0, BODY_L/2 + 0.5, 0]), 0.28, n=8),
            smooth=True, color=C["body_edge"],
        ))

        # Shoulder axle discs
        for y in LEG_Y_OFFSETS:
            for sx in [-LEG_X_OFFSET, LEG_X_OFFSET]:
                p1 = np.array([sx - 0.05, y, 0.0])
                p2 = np.array([sx + 0.05, y, 0.0])
                self.addItem(gl.GLMeshItem(
                    meshdata=cylinder_mesh(p1, p2, radius=0.26, n_sides=16),
                    smooth=True, color=C["joint"],
                ))

        ax = gl.GLAxisItem()
        ax.setSize(1.5, 1.5, 1.5)
        self.addItem(ax)

    # ── Legs ──────────────────────────────────────────────────────────────────
    def _build_all_legs(self):
        for leg in LEG_NAMES:
            items = self._make_leg_items(leg, 0.0)
            self._leg_items[leg] = items
            for it in items:
                self.addItem(it)

    def _make_leg_items(self, leg: str, angle_deg: float) -> list:
        side     = LEG_SIDE[leg]
        shoulder = _shoulder_pos(leg)
        foot     = arc_leg_tip(shoulder, angle_deg, _ARC_R, _ARC_SPAN)

        arc_col  = C["leg_L"]  if side == "L" else C["leg_R"]
        foot_col = C["foot_L"] if side == "L" else C["foot_R"]

        return [
            gl.GLMeshItem(                                       # [0] arc
                meshdata=arc_leg_mesh(shoulder, angle_deg,
                                      arc_radius=_ARC_R,
                                      arc_span_deg=_ARC_SPAN),
                smooth=True, color=arc_col,
            ),
            gl.GLMeshItem(                                       # [1] shoulder
                meshdata=sphere_mesh(shoulder, 0.26, n=8),
                smooth=True, color=C["joint"],
            ),
            gl.GLMeshItem(                                       # [2] foot
                meshdata=sphere_mesh(foot, 0.20, n=8),
                smooth=True, color=foot_col,
            ),
        ]

    def _update_leg(self, leg: str, angle_deg: float):
        shoulder = _shoulder_pos(leg)
        foot     = arc_leg_tip(shoulder, angle_deg, _ARC_R, _ARC_SPAN)
        items    = self._leg_items[leg]
        items[0].setMeshData(
            meshdata=arc_leg_mesh(shoulder, angle_deg, _ARC_R, _ARC_SPAN))
        items[2].setMeshData(
            meshdata=sphere_mesh(foot, 0.20, n=8))

    # ── Public update ─────────────────────────────────────────────────────────
    def update_state(self, state: RobotState):
        for leg, (counts, angle_deg, is_cw) in state.snapshot().items():
            self._update_leg(leg, angle_deg)
        self.update()
