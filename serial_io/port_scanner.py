"""
serial_io/port_scanner.py
──────────────────────────
Lists available serial ports and tries to identify ESP32/Arduino devices.
"""

from dataclasses import dataclass
from typing import Optional

try:
    import serial.tools.list_ports
    PYSERIAL_OK = True
except ImportError:
    PYSERIAL_OK = False


# USB vendor/product IDs for common ESP32 USB-UART chips
_ESP32_VID_PIDS = {
    (0x10C4, 0xEA60),  # Silicon Labs CP2102/CP2104
    (0x1A86, 0x7523),  # CH340/CH341 (common on cheap boards)
    (0x0403, 0x6001),  # FTDI FT232RL
    (0x239A, 0x80AB),  # Espressif native USB (ESP32-S2/S3)
    (0x303A, 0x1001),  # Espressif USB JTAG/CDC
}


@dataclass
class PortInfo:
    device:      str
    description: str
    is_esp32:    bool = False

    def __str__(self) -> str:
        tag = " [ESP32?]" if self.is_esp32 else ""
        return f"{self.device}{tag} — {self.description}"


def list_ports() -> list[PortInfo]:
    """Return all available serial ports, ESP32-like ones sorted first."""
    if not PYSERIAL_OK:
        return []

    ports = []
    for p in serial.tools.list_ports.comports():
        vid = getattr(p, "vid", None)
        pid = getattr(p, "pid", None)
        is_esp = (vid, pid) in _ESP32_VID_PIDS if (vid and pid) else False
        # Also flag by description string
        desc = p.description or ""
        if not is_esp:
            for kw in ("CP210", "CH340", "FTDI", "ESP", "Arduino"):
                if kw.lower() in desc.lower():
                    is_esp = True
                    break
        ports.append(PortInfo(device=p.device, description=desc, is_esp32=is_esp))

    # ESP32-likely ports first
    ports.sort(key=lambda x: (not x.is_esp32, x.device))
    return ports


def best_guess_port() -> Optional[str]:
    """Return the most likely ESP32 port, or None."""
    for p in list_ports():
        if p.is_esp32:
            return p.device
    all_p = list_ports()
    return all_p[0].device if all_p else None
