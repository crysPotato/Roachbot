"""
ui/main_window.py
──────────────────
QMainWindow — root of the application.

Layout:
┌─────────────────────────────────────┬──────────────────────┐
│  [IDLE]  [◈ SIM]  [⬤ LIVE]  ...    │  mode bar            │
├─────────────────────────────────────┼──────────────────────┤
│                                     │  SimPanel            │
│   3-D  GLWidget                     │  or SerialPanel      │
│                                     │  (stacked)           │
├─────────────────────────────────────┴──────────────────────┤
│  LEG STATUS BAR — always visible, all 6 legs               │
└────────────────────────────────────────────────────────────┘

Direction convention (from ESP32 encoder sign):
  positive counts → CW
  negative counts → CCW
"""

import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont

from core.constants import QC, LEG_NAMES, LEG_SIDE, DEG_PER_COUNT
from core.robot_state import RobotState

from visualizer_3d.gl_widget import RobotGLWidget
from ui.sim_panel    import SimPanel
from ui.serial_panel import SerialPanel
from serial_io.reader import SerialReader

_IDX_SIM  = 0
_IDX_LIVE = 1

_MONO  = QFont("Courier New", 8)
_MONOB = QFont("Courier New", 8, QFont.Bold)


def _lbl(text, color=QC["text"], bold=False):
    w = QLabel(text)
    w.setFont(_MONOB if bold else _MONO)
    w.setStyleSheet(f"color:{color};background:transparent;")
    return w


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RoachBotV2 — 3D Encoder Monitor")
        self.resize(1300, 780)
        self.setStyleSheet(f"QMainWindow,QWidget{{background:{QC['bg']};}}")

        self._state  = RobotState()
        self._reader = SerialReader()
        self._mode   = "idle"
        self._idle_t = 0

        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        root_lay.addWidget(self._build_top_bar())

        # ── Content row ───────────────────────────────────────
        content = QWidget()
        c_lay   = QHBoxLayout(content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)

        self._gl = RobotGLWidget()
        self._gl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        c_lay.addWidget(self._gl, stretch=7)

        self._right = QStackedWidget()
        self._right.setFixedWidth(330)
        self._right.setStyleSheet(
            f"background:{QC['panel']};border-left:1px solid {QC['border']};")
        self._sim_panel    = SimPanel()
        self._serial_panel = SerialPanel()
        self._right.addWidget(self._sim_panel)
        self._right.addWidget(self._serial_panel)
        c_lay.addWidget(self._right)
        root_lay.addWidget(content)

        # ── Always-visible leg status footer ──────────────────
        root_lay.addWidget(self._build_status_bar())

        # ── Wire signals ──────────────────────────────────────
        self._sim_panel.leg_counts_changed.connect(self._on_sim_counts_changed)
        self._serial_panel.connect_requested.connect(self._on_connect_requested)
        self._serial_panel.disconnect_requested.connect(self._on_disconnect_requested)
        self._reader.data_received.connect(self._on_serial_data)
        self._reader.status_changed.connect(self._serial_panel.on_status_changed)
        self._reader.raw_line.connect(self._serial_panel.on_raw_line)
        self._reader.connection_lost.connect(self._serial_panel.on_connection_lost)
        self._reader.connection_lost.connect(lambda _: self._force_idle())

        # ── Timer ─────────────────────────────────────────────
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)   # 25 fps

        self._set_mode("idle")

    # ── Top bar ───────────────────────────────────────────────
    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(
            f"background:{QC['panel']};border-bottom:1px solid {QC['border']};")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 4, 12, 4)
        lay.setSpacing(8)

        title = QLabel("◈  ROACHBOT V2  —  3D ENCODER MONITOR")
        title.setFont(QFont("Courier New", 11, QFont.Bold))
        title.setStyleSheet(f"color:{QC['title']};background:transparent;")
        lay.addWidget(title)
        lay.addStretch()

        self._mode_btns: dict[str, QPushButton] = {}
        for mode, label in [("idle","IDLE"),("simulation","◈ SIM"),("live","⬤ LIVE")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Courier New", 9, QFont.Bold))
            btn.setFixedSize(92, 32)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, m=mode: self._set_mode(m))
            self._mode_btns[mode] = btn
            lay.addWidget(btn)
        self._refresh_mode_btns()
        return bar

    # ── Leg status footer — always visible ────────────────────
    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(
            f"background:{QC['panel']};border-top:1px solid {QC['border']};")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(0)

        hdr = _lbl("LEGS: ", QC["dim"])
        hdr.setFixedWidth(42)
        lay.addWidget(hdr)

        self._status_cells: dict[str, QLabel] = {}
        for i, leg in enumerate(LEG_NAMES):
            col = QC["leg_L"] if LEG_SIDE[leg] == "L" else QC["leg_R"]

            cell = QWidget()
            cell.setStyleSheet(
                f"background:{QC['bg']};border:1px solid {QC['border']};border-radius:3px;")
            cell_lay = QVBoxLayout(cell)
            cell_lay.setContentsMargins(6, 2, 6, 2)
            cell_lay.setSpacing(0)

            name_lbl = _lbl(leg, col, bold=True)
            name_lbl.setAlignment(Qt.AlignCenter)
            cell_lay.addWidget(name_lbl)

            val_lbl = QLabel("0 cts | 0.0° | CW")
            val_lbl.setFont(_MONO)
            val_lbl.setStyleSheet(f"color:{col};background:transparent;")
            val_lbl.setAlignment(Qt.AlignCenter)
            cell_lay.addWidget(val_lbl)

            self._status_cells[leg] = val_lbl
            lay.addWidget(cell, stretch=1)
            if i < len(LEG_NAMES) - 1:
                lay.addSpacing(3)

        return bar

    def _refresh_status_bar(self):
        for leg, ls in self._state.legs.items():
            cell = self._status_cells.get(leg)
            if cell:
                dir_str = "CW ↻" if ls.is_cw else "CCW ↺"
                cell.setText(f"{ls.counts:+d} | {ls.angle_deg:.1f}° | {dir_str}")

    # ── Mode switching ────────────────────────────────────────
    def _set_mode(self, mode: str):
        if mode == self._mode:
            return
        if self._mode == "live" and self._reader.is_connected:
            self._reader.disconnect()
        self._mode = mode
        self._state.mode = mode
        if mode == "simulation":
            self._right.setCurrentIndex(_IDX_SIM)
            self._sim_panel.sync_from_state(self._state)
        elif mode == "live":
            self._right.setCurrentIndex(_IDX_LIVE)
        self._refresh_mode_btns()

    def _refresh_mode_btns(self):
        active_style = f"""QPushButton{{
            background:{QC['panel']};color:{QC['title']};
            border:1px solid {QC['title']};border-radius:3px;}}"""
        idle_style = f"""QPushButton{{
            background:{QC['panel']};color:{QC['dim']};
            border:1px solid {QC['border']};border-radius:3px;}}
            QPushButton:hover{{border-color:{QC['dim']};color:{QC['text']};}}"""
        for m, btn in self._mode_btns.items():
            btn.setChecked(m == self._mode)
            btn.setStyleSheet(active_style if m == self._mode else idle_style)

    def _force_idle(self):
        self._mode = "idle"
        self._state.mode = "idle"
        self._refresh_mode_btns()

    # ── Animation tick ────────────────────────────────────────
    def _tick(self):
        if self._mode == "idle":
            self._run_idle_demo()
        self._gl.update_state(self._state)
        self._refresh_status_bar()
        if self._mode == "live":
            self._serial_panel.update_counts(self._state)

    def _run_idle_demo(self):
        """
        Tripod gait demo — legs phase-shifted so opposite legs move together.
        Alternates positive (CW) and negative (CCW) counts per step so the
        direction indicator is exercised too.
        """
        t = self._idle_t * 0.038
        # FL, MR, RR move together; FR, ML, RL move together (classic tripod)
        phases = {
            "FL":  0.0,  "MR":  0.0,  "RR":  0.0,
            "FR": 3.14,  "ML": 3.14,  "RL": 3.14,
        }
        for leg, phi in phases.items():
            # Oscillate 0 → +234 (CW half) — counts always positive in idle
            counts = int(117 * (1 - np.cos(t + phi)))
            self._state.set_counts(leg, counts)
        self._idle_t += 1

    # ── Sim callbacks ─────────────────────────────────────────
    @pyqtSlot(str, int)
    def _on_sim_counts_changed(self, leg: str, counts: int):
        self._state.set_counts(leg, counts)

    # ── Live / serial callbacks ───────────────────────────────
    @pyqtSlot(str, int)
    def _on_connect_requested(self, port: str, baud: int):
        self._set_mode("live")
        self._reader.connect(port, baud)

    @pyqtSlot()
    def _on_disconnect_requested(self):
        self._reader.disconnect()
        self._state.reset_all()

    @pyqtSlot(dict)
    def _on_serial_data(self, data: dict):
        """
        Serial data: positive counts = CW, negative = CCW.
        We trust the sign from the ESP32 directly.
        """
        self._state.set_all_counts(data)

    def closeEvent(self, event):
        self._timer.stop()
        self._reader.disconnect()
        event.accept()
