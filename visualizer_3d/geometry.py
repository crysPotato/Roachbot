"""
visualizer_3d/geometry.py
──────────────────────────
3D mesh generators for pyqtgraph.opengl.

Leg model
─────────
Each leg is an arc-shaped tube (torus segment) — like a curved roach limb.
The arc lives in the YZ plane at the shoulder's X position and rotates
as a rigid body around the X-axis (the shoulder axle going into the box wall).

Arc path (local frame, shoulder = origin):
  p(t) = [0,  R·sin(t),  R·(cos(t) − 1)]   t ∈ [0, arc_span]

  t = 0          → shoulder  (0, 0, 0)
  t = arc_span   → tip       (0, R·sin(span), R·(cos(span)−1))

At rest (encoder = 0°) the arc curls outward (+Y) and downward (−Z),
which looks like the roach leg hanging naturally to the side and down.
Encoder angle rotates the whole arc around X:
  0°  → hanging down/outward
  90° → swept forward
  180°→ pointing up/outward
  270°→ swept backward
Full 360° with no clamping.
"""

import numpy as np

try:
    from pyqtgraph.opengl import MeshData
    _HAS_PG = True
except ImportError:
    MeshData = None
    _HAS_PG = False


def _make_meshdata(verts, faces):
    if not _HAS_PG:
        raise ImportError("pyqtgraph not installed — pip install pyqtgraph PyOpenGL")
    return MeshData(
        vertexes=np.asarray(verts, dtype=np.float32),
        faces=np.asarray(faces,    dtype=np.int32),
    )


# ─── Rotation matrices ────────────────────────────────────────────────────────

def Rx(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]], dtype=float)

def Ry(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]], dtype=float)

def Rz(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c,-s,0],[s,c,0],[0,0,1]], dtype=float)


# ─── Arc tube ─────────────────────────────────────────────────────────────────

def arc_leg_mesh(
    shoulder,
    encoder_angle_deg: float,
    arc_radius:  float = 2.4,   # curvature radius of the limb arc
    arc_span_deg: float = 135,  # how much the arc subtends (leg length feel)
    tube_r:      float = 0.18,  # cross-section radius of the tube
    n_arc:       int   = 24,    # segments along arc path
    n_tube:      int   = 10,    # segments around tube cross-section
):
    """
    Build an arc-tube mesh for one leg at the given encoder angle.
    Returns pyqtgraph MeshData.
    """
    shoulder = np.asarray(shoulder, dtype=float)
    span     = np.radians(arc_span_deg)
    ts       = np.linspace(0.0, span, n_arc)

    # ── Arc path in local frame (shoulder at origin, in YZ plane) ──────────
    path = np.column_stack([
        np.zeros(n_arc),
        arc_radius * np.sin(ts),
        arc_radius * (np.cos(ts) - 1.0),
    ])

    # ── Tangent vectors (normalised derivative) ──────────────────────────────
    tangents = np.column_stack([
        np.zeros(n_arc),
        arc_radius * np.cos(ts),
        -arc_radius * np.sin(ts),
    ])
    norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1.0, norms)
    tangents /= norms

    # ── Tube cross-section at each path point ────────────────────────────────
    # Because the path lies in the YZ plane, X is always a valid normal.
    x_hat = np.array([1.0, 0.0, 0.0])
    tube_angles = np.linspace(0, 2 * np.pi, n_tube, endpoint=False)

    verts_local = []
    for p, t in zip(path, tangents):
        # Binormal = tangent × X (gives a vector in the YZ plane perp to t)
        binormal = np.cross(t, x_hat)
        bn = np.linalg.norm(binormal)
        binormal = binormal / bn if bn > 1e-8 else np.array([0.0, 0.0, 1.0])
        # Normal for tube ring: X and binormal span the cross-section plane
        for a in tube_angles:
            v = p + tube_r * (np.cos(a) * x_hat + np.sin(a) * binormal)
            verts_local.append(v)

    verts_local = np.array(verts_local, dtype=float)

    # ── Rotate entire arc by encoder angle around shoulder (X-axis) ──────────
    R     = Rx(np.radians(encoder_angle_deg))
    verts = (R @ verts_local.T).T + shoulder

    # ── Quad strip faces ─────────────────────────────────────────────────────
    faces = []
    for i in range(n_arc - 1):
        for j in range(n_tube):
            a = i       * n_tube + j
            b = i       * n_tube + (j + 1) % n_tube
            c = (i + 1) * n_tube + (j + 1) % n_tube
            d = (i + 1) * n_tube + j
            faces.extend([[a, b, c], [a, c, d]])

    return _make_meshdata(verts, faces)


def arc_leg_tip(shoulder, encoder_angle_deg: float,
                arc_radius: float = 2.4, arc_span_deg: float = 135) -> np.ndarray:
    """Return the world-space position of the leg tip (foot end of the arc)."""
    shoulder = np.asarray(shoulder, dtype=float)
    span     = np.radians(arc_span_deg)
    tip_local = np.array([
        0.0,
        arc_radius * np.sin(span),
        arc_radius * (np.cos(span) - 1.0),
    ])
    return shoulder + Rx(np.radians(encoder_angle_deg)) @ tip_local


# ─── Utility meshes ───────────────────────────────────────────────────────────

def cylinder_mesh(p1, p2, radius: float = 0.20, n_sides: int = 14):
    """Capped cylinder from p1 to p2 (used for axle decorations)."""
    p1, p2 = np.asarray(p1, dtype=float), np.asarray(p2, dtype=float)
    axis   = p2 - p1
    length = np.linalg.norm(axis)
    if length < 1e-8:
        return box_mesh(p1, np.ones(3) * 0.01)
    angles = np.linspace(0, 2 * np.pi, n_sides, endpoint=False)
    circle = np.column_stack([np.cos(angles) * radius,
                               np.sin(angles) * radius,
                               np.zeros(n_sides)])
    z_hat  = np.array([0, 0, 1], dtype=float)
    a_hat  = axis / length
    cross  = np.cross(z_hat, a_hat)
    cn     = np.linalg.norm(cross)
    if cn < 1e-8:
        R = np.eye(3) if np.dot(z_hat, a_hat) > 0 else np.diag([1, -1, -1])
    else:
        cd = np.dot(z_hat, a_hat)
        K  = np.array([[0,-cross[2],cross[1]],[cross[2],0,-cross[0]],[-cross[1],cross[0],0]]) / cn
        R  = np.eye(3) + cn * K + (1 - cd) * K @ K
    ring1  = (R @ circle.T).T + p1
    ring2  = (R @ circle.T).T + p2
    verts  = np.vstack([ring1, ring2, [p1], [p2]])
    n      = n_sides
    faces  = []
    for i in range(n):
        j = (i + 1) % n
        faces += [[i, j, n+i],[j, n+j, n+i],[2*n, i, j],[2*n+1, n+j, n+i]]
    return _make_meshdata(verts, faces)


def box_mesh(center, size):
    cx, cy, cz = np.asarray(center, dtype=float)
    sx, sy, sz = np.asarray(size,   dtype=float) / 2.0
    verts = np.array([
        [cx-sx,cy-sy,cz-sz],[cx+sx,cy-sy,cz-sz],
        [cx+sx,cy+sy,cz-sz],[cx-sx,cy+sy,cz-sz],
        [cx-sx,cy-sy,cz+sz],[cx+sx,cy-sy,cz+sz],
        [cx+sx,cy+sy,cz+sz],[cx-sx,cy+sy,cz+sz],
    ], dtype=np.float32)
    faces = np.array([
        [0,1,2],[0,2,3],[4,5,6],[4,6,7],
        [0,1,5],[0,5,4],[2,3,7],[2,7,6],
        [0,3,7],[0,7,4],[1,2,6],[1,6,5],
    ], dtype=np.int32)
    return _make_meshdata(verts, faces)


def sphere_mesh(center, radius: float, n: int = 10):
    center = np.asarray(center, dtype=float)
    nc     = 2 * n
    verts  = []
    for i in range(n + 1):
        lat = np.pi * i / n - np.pi / 2
        for j in range(nc):
            lon = 2 * np.pi * j / nc
            verts.append([
                center[0] + radius * np.cos(lat) * np.cos(lon),
                center[1] + radius * np.cos(lat) * np.sin(lon),
                center[2] + radius * np.sin(lat),
            ])
    faces = []
    for i in range(n):
        for j in range(nc):
            a = i*nc+j; b = i*nc+(j+1)%nc
            c = (i+1)*nc+(j+1)%nc; d = (i+1)*nc+j
            faces.extend([[a,b,c],[a,c,d]])
    return _make_meshdata(verts, faces)
