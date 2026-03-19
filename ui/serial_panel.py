"""
ui/serial_panel.py
───────────────────
Serial / LIVE mode panel:
  - Port dropdown (auto-scans, detects ESP32)
  - Baud rate selector
  - Connect / Disconnect button
  - Status indicator
  - Raw log (last N lines)
  - Per-leg live encoder readout table
"""

from collections import deque

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QTextEdit,
    QFrame, QSizePolicy, QSpacerItem,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

from core.constants import LEG_NAMES, LEG_SIDE, DEG_PER_COUNT, QC
from core.robot_state import RobotState
from serial_io.port_scanner import list_ports, PYSERIAL_OK

_MONO = QFont("Courier New", 8)
_MONO.setStyleHint(QFont.Monospace)

_BAUD_RATES = ["115200", "57600", "38400", "9600"]
_MAX_LOG    = 120   # lines kept in raw log


def _lbl(text: str, color: str = QC["text"]) -> QLabel:
    lb = QLabel(text)
    lb.setFont(_MONO)
    lb.setStyleSheet(f"color: {color}; background: transparent;")
    return lb


class SerialPanel(QWidget):
    """LIVE mode panel."""

    # User clicked Connect / Disconnect
    connect_requested    = pyqtSignal(str, int)   # (port, baud)
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {QC['panel']};")
        self._connected = False
        self._log_buf: deque[str] = deque(maxlen=_MAX_LOG)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Header ────────────────────────────────────────────
        hdr = QLabel("⬤  LIVE MODE — ESP32 Serial")
        hdr.setFont(QFont("Courier New", 10, QFont.Bold))
        hdr.setStyleSheet(f"color: {QC['live_on'] if hasattr(QC,'live_on') else QC['leg_R']}; background: transparent;")
        root.addWidget(hdr)

        if not PYSERIAL_OK:
            warn = QLabel("⚠  pyserial not installed\n   pip install pyserial")
            warn.setFont(_MONO)
            warn.setStyleSheet(f"color: {QC['warn']}; background: transparent;")
            root.addWidget(warn)

        # ── Port selector ─────────────────────────────────────
        port_row = QHBoxLayout()
        port_row.addWidget(_lbl("PORT:"))
        self._port_combo = QComboBox()
        self._port_combo.setFont(_MONO)
        self._port_combo.setEditable(True)
        self._port_combo.setMinimumWidth(140)
        self._port_combo.setStyleSheet(f"""
            QComboBox {{
                background: {QC['bg']};
                color: {QC['text']};
                border: 1px solid {QC['border']};
                padding: 2px 4px;
            }}
            QComboBox QAbstractItemView {{
                background: {QC['bg']};
                color: {QC['text']};
                selection-background-color: {QC['border']};
            }}
        """)
        port_row.addWidget(self._port_combo, stretch=1)

        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedWidth(28)
        refresh_btn.setFont(QFont("Courier New", 9, QFont.Bold))
        refresh_btn.setToolTip("Rescan serial ports")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {QC['panel']};
                color: {QC['title']};
                border: 1px solid {QC['border']};
            }}
            QPushButton:hover {{ background: {QC['border']}; }}
        """)
        refresh_btn.clicked.connect(self._scan_ports)
        port_row.addWidget(refresh_btn)
        root.addLayout(port_row)

        # ── Baud rate ─────────────────────────────────────────
        baud_row = QHBoxLayout()
        baud_row.addWidget(_lbl("BAUD:"))
        self._baud_combo = QComboBox()
        self._baud_combo.setFont(_MONO)
        self._baud_combo.addItems(_BAUD_RATES)
        self._baud_combo.setCurrentText("115200")
        self._baud_combo.setStyleSheet(f"""
            QComboBox {{
                background: {QC['bg']};
                color: {QC['text']};
                border: 1px solid {QC['border']};
                padding: 2px;
            }}
            QComboBox QAbstractItemView {{
                background: {QC['bg']};
                color: {QC['text']};
            }}
        """)
        baud_row.addWidget(self._baud_combo)
        baud_row.addStretch()
        root.addLayout(baud_row)

        # ── Connect button ────────────────────────────────────
        self._con_btn = QPushButton("CONNECT")
        self._con_btn.setFont(QFont("Courier New", 9, QFont.Bold))
        self._con_btn.setFixedHeight(30)
        self._update_connect_btn(False)
        self._con_btn.clicked.connect(self._on_connect_clicked)
        root.addWidget(self._con_btn)

        # ── Status ────────────────────────────────────────────
        self._status_lbl = _lbl("● Disconnected", QC["dim"])
        root.addWidget(self._status_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {QC['border']};")
        root.addWidget(sep)

        # ── Live encoder readout ──────────────────────────────
        root.addWidget(_lbl("ENCODER COUNTS", QC["title"]))

        self._count_labels: dict[str, tuple[QLabel, QLabel]] = {}
        grid = QGridLayout()
        grid.setSpacing(3)
        for i, leg in enumerate(LEG_NAMES):
            col = QC["leg_L"] if LEG_SIDE[leg] == "L" else QC["leg_R"]
            tag  = _lbl(leg, col)
            tag.setFont(QFont("Courier New", 8, QFont.Bold))
            cnt  = _lbl("     0", QC["text"])
            deg  = _lbl("  0.00°", QC["dim"])
            grid.addWidget(tag, i, 0)
            grid.addWidget(cnt, i, 1)
            grid.addWidget(deg, i, 2)
            self._count_labels[leg] = (cnt, deg)
        root.addLayout(grid)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color: {QC['border']};")
        root.addWidget(sep2)

        # ── Raw serial log ────────────────────────────────────
        root.addWidget(_lbl("RAW LOG", QC["title"]))
        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setFont(QFont("Courier New", 7))
        self._log_box.setMaximumHeight(160)
        self._log_box.setStyleSheet(f"""
            QTextEdit {{
                background: {QC['bg']};
                color: {QC['dim']};
                border: 1px solid {QC['border']};
            }}
        """)
        root.addWidget(self._log_box)

        root.addStretch()

        # Initial port scan
        self._scan_ports()

    # ── Port scanning ─────────────────────────────────────────
    def _scan_ports(self) -> None:
        self._port_combo.blockSignals(True)
        self._port_combo.clear()
        ports = list_ports()
        if ports:
            for p in ports:
                self._port_combo.addItem(str(p), p.device)
            # Select first ESP32-likely port
            for i, p in enumerate(ports):
                if p.is_esp32:
                    self._port_combo.setCurrentIndex(i)
                    break
        else:
            self._port_combo.addItem("No ports found")
        self._port_combo.blockSignals(False)

    # ── Connect / disconnect ──────────────────────────────────
    def _on_connect_clicked(self) -> None:
        if self._connected:
            self.disconnect_requested.emit()
        else:
            port = self._port_combo.currentData() or self._port_combo.currentText()
            baud = int(self._baud_combo.currentText())
            self.connect_requested.emit(port, baud)

    def _update_connect_btn(self, connected: bool) -> None:
        if connected:
            self._con_btn.setText("DISCONNECT")
            self._con_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #1a0d0d;
                    color: #ff6b6b;
                    border: 1px solid #4a1515;
                    border-radius: 3px;
                    padding: 4px;
                }}
                QPushButton:hover {{ background: #2a0f0f; }}
            """)
        else:
            self._con_btn.setText("CONNECT")
            self._con_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {QC['panel']};
                    color: {QC['connected']};
                    border: 1px solid {QC['border']};
                    border-radius: 3px;
                    padding: 4px;
                }}
                QPushButton:hover {{ background: {QC['border']}; }}
            """)

    # ── Slots called by MainWindow ────────────────────────────
    def on_status_changed(self, level: str, msg: str) -> None:
        colors = {"ok": QC["connected"], "warn": QC["warn"], "error": QC["error"]}
        col = colors.get(level, QC["dim"])
        self._connected = (level == "ok" and "LIVE" in msg or "Connected" in msg)
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {col}; background: transparent; font-family: Courier New; font-size: 8pt;")
        self._update_connect_btn(self._connected)

    def on_raw_line(self, line: str) -> None:
        self._log_buf.append(line)
        self._log_box.setPlainText("\n".join(self._log_buf))
        sb = self._log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_connection_lost(self, err: str) -> None:
        self._connected = False
        self._update_connect_btn(False)
        self._status_lbl.setText(f"✗ Lost: {err}")
        self._status_lbl.setStyleSheet(f"color: {QC['error']}; background: transparent; font-family: Courier New; font-size: 8pt;")

    def update_counts(self, state: RobotState) -> None:
        """Refresh the per-leg count table from state."""
        for leg, (cnt_lbl, deg_lbl) in self._count_labels.items():
            ls = state.legs[leg]
            cnt_lbl.setText(f"{ls.counts:>6d}")
            deg_lbl.setText(f"{ls.angle_deg:>7.2f}°")
