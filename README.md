<<<<<<< HEAD
# Roachbot
Real-time 3D visualization tool for the RoachBotV2 six-legged robot. Built with PyQt5 and pyqtgraph OpenGL. Reads live encoder data from an ESP32 over USB serial and renders each leg's rotation as an animated 3D arc.
=======
# RoachBotV2 — 3D Encoder Visualizer

Real-time 3D visualization of the 6-legged RoachBot.
Each leg is driven by an **independent encoder** (not left/right pairs).

```
roachbot/
├── main.py                      ← run this
├── requirements.txt
├── arduino/
│   └── serial_6leg.ino          ← add to your ESP32 sketch
├── core/
│   ├── constants.py             ← encoder math, geometry, colours
│   ├── robot_state.py           ← 6-leg independent state
│   └── serial_protocol.py      ← parses all serial formats
├── serial_io/
│   ├── reader.py                ← QThread serial reader (non-blocking)
│   └── port_scanner.py         ← ESP32 port detection
├── visualizer_3d/
│   ├── gl_widget.py             ← pyqtgraph OpenGL 3D robot
│   └── geometry.py             ← cylinder/box/sphere mesh builders
└── ui/
    ├── main_window.py           ← QMainWindow, mode switching
    ├── sim_panel.py             ← per-leg spinboxes + CW/CCW toggles
    └── serial_panel.py         ← port selector, log, live readout
```

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## Modes

| Mode | How to use |
|------|-----------|
| **IDLE** | Auto-plays a 6-leg walking gait demo |
| **◈ SIM** | Per-leg spinbox controls (−468 → +468 counts), CW/CCW toggle per leg |
| **⬤ LIVE** | Select ESP32 COM port → CONNECT → reads real encoder data |

## Live Mode — Arduino Side

Add `arduino/serial_6leg.ino` to your sketch. It outputs:
```
ENC:FL=120,ML=80,RL=45,FR=100,MR=60,RR=30
```

The visualizer also parses your **current test format** out of the box:
```
[LEFT 0->180] Lseg=120/234  (92.3 deg)
```
So you can test LIVE mode immediately with your existing sketch.

## Encoder Math

From your `.ino`:
```
LEFT_COUNTS_180 = 234
DEG_PER_COUNT   = 180 / 234 ≈ 0.7692°/count
```

## 3D Controls

| Action | Mouse |
|--------|-------|
| Orbit  | Left-drag |
| Zoom   | Scroll wheel |
| Pan    | Right-drag |
>>>>>>> 4089a03 (initial commit)
