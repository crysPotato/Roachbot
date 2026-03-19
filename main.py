"""
main.py
────────
RoachBotV2 — 3D Encoder Visualizer
Entry point.

Usage:
    pip install -r requirements.txt
    python main.py
"""

import sys
import os

# Ensure project root is on path regardless of cwd
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.main_window import MainWindow


def main() -> None:
    # High-DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("RoachBotV2 Visualizer")
    app.setFont(QFont("Courier New", 9))

    win = MainWindow()
    win.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
