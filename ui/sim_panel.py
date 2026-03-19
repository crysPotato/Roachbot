"""
ui/sim_panel.py
────────────────
Simulation mode panel.

Each leg row has:
  [LEG]  [Counts ±spinbox]  [Angle °spinbox]  [CW/CCW indicator]  [Negate dir]  [Reset]

Counts ↔ Angle are bidirectionally linked:
  • Change counts → angle updates automatically
  • Change angle  → counts magnitude updates (sign preserved)

Direction is encoded in the SIGN of counts:
  positive = CW,  negative = CCW
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.constants import LEG_NAMES, LEG_SIDE, MAX_COUNT, DEG_PER_COUNT, QC

_MONO   = QFont("Courier New", 8);  _MONO.setStyleHint(QFont.Monospace)
_MONOB  = QFont("Courier New", 8, QFont.Bold)


def _lbl(text, color=QC["text"], bold=False):
    w = QLabel(text)
    w.setFont(_MONOB if bold else _MONO)
    w.setStyleSheet(f"color:{color};background:transparent;")
    return w


class LegRow(QWidget):
    """One row: bidirectional count↔angle inputs + direction display."""

    counts_changed = pyqtSignal(str, int)   # (leg, new_counts)

    def __init__(self, leg: str, parent=None):
        super().__init__(parent)
        self.leg  = leg
        self.side = LEG_SIDE[leg]
        self._col  = QC["leg_L"] if self.side == "L" else QC["leg_R"]
        self._busy = False   # reentrancy guard

        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(4)

        # ── Leg name ─────────────────────────────────────────
        name = _lbl(leg, self._col, bold=True)
        name.setFixedWidth(24)
        name.setAlignment(Qt.AlignCenter)
        lay.addWidget(name)

        # ── Counts spinbox ────────────────────────────────────
        self._sp_counts = QSpinBox()
        self._sp_counts.setRange(-MAX_COUNT * 4, MAX_COUNT * 4)  # allow multi-rev
        self._sp_counts.setValue(0)
        self._sp_counts.setSuffix(" cts")
        self._sp_counts.setFixedWidth(96)
        self._sp_counts.setFont(_MONO)
        self._sp_counts.setStyleSheet(self._spin_style())
        self._sp_counts.valueChanged.connect(self._on_counts_changed)
        lay.addWidget(self._sp_counts)

        # ── Angle spinbox ─────────────────────────────────────
        self._sp_angle = QDoubleSpinBox()
        self._sp_angle.setRange(0.0, 359.99)
        self._sp_angle.setValue(0.0)
        self._sp_angle.setSuffix("°")
        self._sp_angle.setDecimals(1)
        self._sp_angle.setSingleStep(5.0)
        self._sp_angle.setWrapping(True)
        self._sp_angle.setFixedWidth(78)
        self._sp_angle.setFont(_MONO)
        self._sp_angle.setStyleSheet(self._spin_style())
        self._sp_angle.valueChanged.connect(self._on_angle_changed)
        lay.addWidget(self._sp_angle)

        # ── Direction label ───────────────────────────────────
        self._dir_lbl = _lbl("CW ↻", QC["cw"], bold=True)
        self._dir_lbl.setFixedWidth(50)
        self._dir_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._dir_lbl)

        # ── Flip direction button ─────────────────────────────
        self._flip_btn = QPushButton("⇄")
        self._flip_btn.setFont(_MONOB)
        self._flip_btn.setFixedSize(26, 22)
        self._flip_btn.setToolTip("Flip CW ↔ CCW (negates counts)")
        self._flip_btn.setStyleSheet(f"""
            QPushButton{{background:{QC['panel']};color:{QC['dim']};
                         border:1px solid {QC['border']};border-radius:2px;}}
            QPushButton:hover{{color:{QC['text']};border-color:{QC['dim']};}}
        """)
        self._flip_btn.clicked.connect(self._on_flip)
        lay.addWidget(self._flip_btn)

        # ── Reset ─────────────────────────────────────────────
        rst = QPushButton("↺")
        rst.setFont(_MONOB)
        rst.setFixedSize(22, 22)
        rst.setToolTip(f"Reset {leg} to 0")
        rst.setStyleSheet(f"""
            QPushButton{{background:{QC['panel']};color:#ff6b6b;
                         border:1px solid #3a1515;border-radius:2px;}}
            QPushButton:hover{{background:#2a0f0f;}}
        """)
        rst.clicked.connect(lambda: self._sp_counts.setValue(0))
        lay.addWidget(rst)

        self.setStyleSheet("background:transparent;")

    # ── Spin styles ───────────────────────────────────────────
    def _spin_style(self):
        return f"""
            QSpinBox,QDoubleSpinBox{{
                background:{QC['bg']};color:{self._col};
                border:1px solid {QC['border']};padding:2px 3px;}}
            QSpinBox::up-button,QDoubleSpinBox::up-button,
            QSpinBox::down-button,QDoubleSpinBox::down-button{{
                background:{QC['border']};width:13px;}}
        """

    # ── Linked update callbacks ───────────────────────────────
    def _on_counts_changed(self, val: int):
        if self._busy:
            return
        self._busy = True
        # Update angle to match (direction encoded in sign)
        angle = (val * DEG_PER_COUNT) % 360.0
        self._sp_angle.setValue(angle)
        self._refresh_dir(val)
        self.counts_changed.emit(self.leg, val)
        self._busy = False

    def _on_angle_changed(self, angle: float):
        if self._busy:
            return
        self._busy = True
        # Preserve sign of current counts; only update magnitude
        current = self._sp_counts.value()
        sign    = -1 if current < 0 else 1
        mag     = round(angle / DEG_PER_COUNT)
        new_val = sign * mag
        self._sp_counts.setValue(new_val)
        self.counts_changed.emit(self.leg, new_val)
        self._busy = False

    def _on_flip(self):
        self._sp_counts.setValue(-self._sp_counts.value())

    def _refresh_dir(self, counts: int):
        if counts >= 0:
            self._dir_lbl.setText("CW ↻")
            self._dir_lbl.setStyleSheet(
                f"color:{QC['cw']};background:transparent;font-weight:bold;font-family:'Courier New';font-size:8pt;")
        else:
            self._dir_lbl.setText("CCW ↺")
            self._dir_lbl.setStyleSheet(
                f"color:{QC['ccw']};background:transparent;font-weight:bold;font-family:'Courier New';font-size:8pt;")

    # ── External sync (from serial / state restore) ───────────
    def set_counts_silent(self, counts: int):
        self._busy = True
        self._sp_counts.setValue(counts)
        angle = (counts * DEG_PER_COUNT) % 360.0
        self._sp_angle.setValue(angle)
        self._refresh_dir(counts)
        self._busy = False


class SimPanel(QWidget):
    leg_counts_changed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{QC['panel']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(3)

        # Header
        hdr = _lbl("◈  SIMULATION", QC["title"], bold=True)
        hdr.setFont(QFont("Courier New", 10, QFont.Bold))
        root.addWidget(hdr)

        sub = _lbl(f"1 count = {DEG_PER_COUNT:.4f}°   |   +counts=CW   −counts=CCW",
                   QC["dim"])
        root.addWidget(sub)

        # Column header
        col_hdr = QHBoxLayout()
        col_hdr.setContentsMargins(2, 0, 2, 0)
        for txt, w in [("LEG",24),("COUNTS",96),("ANGLE",78),("DIR",50),("⇄",26),("↺",22)]:
            lb = _lbl(txt, QC["dim"])
            lb.setFixedWidth(w)
            lb.setAlignment(Qt.AlignCenter)
            col_hdr.addWidget(lb)
        col_hdr.addStretch()
        root.addLayout(col_hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{QC['border']};"); root.addWidget(sep)

        self._rows: dict[str, LegRow] = {}

        for group_lbl, legs in [("— LEFT LEGS ——", ["FL","ML","RL"]),
                                  ("— RIGHT LEGS —", ["FR","MR","RR"])]:
            root.addWidget(_lbl(group_lbl,
                                QC["leg_L"] if "LEFT" in group_lbl else QC["leg_R"]))
            for leg in legs:
                row = LegRow(leg)
                row.counts_changed.connect(self.leg_counts_changed)
                self._rows[leg] = row
                root.addWidget(row)
            sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
            sep2.setStyleSheet(f"color:{QC['border']};"); root.addWidget(sep2)

        # Reset all
        rst = QPushButton("⟳  RESET ALL")
        rst.setFont(QFont("Courier New", 9, QFont.Bold))
        rst.setStyleSheet(f"""
            QPushButton{{background:{QC['panel']};color:#ff6b6b;
                         border:1px solid #3a1515;padding:4px;border-radius:3px;}}
            QPushButton:hover{{background:#2a0f0f;}}""")
        rst.clicked.connect(self._reset_all)
        root.addWidget(rst)
        root.addStretch()

    def _reset_all(self):
        for row in self._rows.values():
            row.set_counts_silent(0)
            self.leg_counts_changed.emit(row.leg, 0)

    def sync_from_state(self, state):
        for leg, ls in state.legs.items():
            if leg in self._rows:
                self._rows[leg].set_counts_silent(ls.counts)
