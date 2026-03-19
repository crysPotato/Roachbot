"""
serial_io/reader.py
────────────────────
QThread that continuously reads lines from the ESP32 serial port.
Emits Qt signals (thread-safe) — never touches the UI directly.

Signal flow:
  SerialReader.data_received(dict)  → MainWindow updates RobotState
  SerialReader.status_changed(str, str)  → SerialPanel updates status label
  SerialReader.raw_line(str)        → SerialPanel log window
  SerialReader.connection_lost()    → UI handles reconnect/error
"""

import time
from PyQt5.QtCore import QThread, pyqtSignal

from core.serial_protocol import parse_line
from core.constants import SERIAL_BAUD, SERIAL_TIMEOUT

try:
    import serial
    PYSERIAL_OK = True
except ImportError:
    PYSERIAL_OK = False


class SerialReader(QThread):
    # {leg_name: count_value} — only contains legs present in the line
    data_received = pyqtSignal(dict)
    # (level, message)  level = "ok" | "warn" | "error"
    status_changed = pyqtSignal(str, str)
    # raw text line from ESP32
    raw_line = pyqtSignal(str)
    # emitted when port unexpectedly closes
    connection_lost = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._port:    str  = ""
        self._baud:    int  = SERIAL_BAUD
        self._running: bool = False
        self._ser             = None   # serial.Serial instance

    # ── Public API (call from main thread) ────────────────────
    def connect(self, port: str, baud: int = SERIAL_BAUD) -> None:
        """Start reading from port. Runs in calling thread briefly, then loop."""
        if not PYSERIAL_OK:
            self.status_changed.emit(
                "error",
                "pyserial not installed — run: pip install pyserial"
            )
            return

        self._port    = port
        self._baud    = baud
        self._running = True
        self.start()   # launches run() in background thread

    def disconnect(self) -> None:
        """Signal the thread to stop and wait for clean exit."""
        self._running = False
        self.wait(2000)   # wait up to 2 s
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None

    @property
    def is_connected(self) -> bool:
        return self._running and self._ser is not None and self._ser.is_open

    # ── QThread.run() — executes in background thread ─────────
    def run(self) -> None:
        if not PYSERIAL_OK:
            return

        # ── Open port ─────────────────────────────────────────
        try:
            self._ser = serial.Serial(
                self._port,
                self._baud,
                timeout=SERIAL_TIMEOUT,
            )
        except serial.SerialException as exc:
            self.status_changed.emit("error", f"Cannot open {self._port}: {exc}")
            self._running = False
            return

        # ESP32 resets on DTR toggle — wait for boot
        time.sleep(2.0)
        self._ser.reset_input_buffer()

        self.status_changed.emit(
            "ok",
            f"Connected  {self._port}  @  {self._baud} baud",
        )

        lines_rx  = 0
        parsed_ok = 0
        last_stat = time.monotonic()

        # ── Read loop ─────────────────────────────────────────
        while self._running:
            try:
                if not self._ser.is_open:
                    raise serial.SerialException("Port closed unexpectedly")

                raw = self._ser.readline()
                if not raw:
                    continue    # timeout — no data yet

                line = raw.decode("utf-8", errors="replace").strip()
                lines_rx += 1

                # Always emit raw for the log window
                self.raw_line.emit(line)

                # Try to parse encoder data
                data = parse_line(line)
                if data:
                    parsed_ok += 1
                    self.data_received.emit(data)

                # Periodic status update (every 2 s)
                now = time.monotonic()
                if now - last_stat >= 2.0:
                    self.status_changed.emit(
                        "ok",
                        f"LIVE  {self._port}  |  "
                        f"{lines_rx} lines  |  {parsed_ok} parsed"
                    )
                    last_stat = now

            except serial.SerialException as exc:
                err = str(exc)
                self.connection_lost.emit(err)
                self.status_changed.emit("error", f"Lost connection: {err}")
                self._running = False
                break
            except Exception as exc:
                self.status_changed.emit("warn", f"Read error: {exc}")
                time.sleep(0.1)

        # ── Cleanup ───────────────────────────────────────────
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except Exception:
                pass
