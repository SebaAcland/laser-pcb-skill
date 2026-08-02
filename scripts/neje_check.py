#!/usr/bin/env python3
"""neje_check.py — Diagnóstico completo de la NEJE Master 2S Plus.

Uso:
    python3 neje_check.py
"""

import serial
import sys
import time
from pathlib import Path

PORT = "/dev/ttyUSB0"
BAUD = 115200


def check_connection():
    """Verifica conexión USB."""
    if not Path(PORT).exists():
        print(f"❌ {PORT} no existe")
        print("   Conectar USB o hacer attach con usbipd")
        return False
    print(f"✓ {PORT} presente")
    return True


def check_grbl(ser):
    """Verifica versión GRBL."""
    ser.write(b"$I\r\n")
    time.sleep(0.3)
    resp = ser.read(ser.in_waiting or 128).decode(errors="ignore").strip()
    if "Grbl" in resp or "VER:" in resp:
        print(f"✓ GRBL: {resp.splitlines()[0][:60]}")
        return True
    else:
        print(f"❌ No se detectó GRBL: {resp[:60]}")
        return False


def check_config(ser):
    """Muestra configuración GRBL."""
    print("\n► Configuración GRBL:")
    for setting in ["$3", "$22", "$23", "$25", "$30", "$32", "$120", "$121", "$130", "$131"]:
        ser.write(f"{setting}\r\n".encode())
        time.sleep(0.15)
        resp = ser.read(ser.in_waiting).decode(errors="ignore").strip()
        # Filtrar solo la línea del setting
        for line in resp.splitlines():
            if line.startswith("$"):
                print(f"  {line}")
                break


def check_position(ser):
    """Muestra posición actual."""
    ser.write(b"?\r\n")
    time.sleep(0.2)
    pos = ser.read(ser.in_waiting).decode(errors="ignore").strip()
    print(f"\n► Posición: {pos[:80]}")


def check_limits(ser):
    """Verifica límites de trabajo."""
    print("\n► Límites de trabajo:")
    print(f"  X: 0-255mm")
    print(f"  Y: 0-420mm")
    print(f"  Área: 255×420mm")


def main():
    print("=" * 60)
    print("  Diagnóstico NEJE Master 2S Plus")
    print("=" * 60)

    if not check_connection():
        sys.exit(1)

    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    time.sleep(2)
    ser.reset_input_buffer()

    if not check_grbl(ser):
        ser.close()
        sys.exit(1)

    check_config(ser)
    check_position(ser)
    check_limits(ser)

    print("\n" + "=" * 60)
    print("  Sistema de Coordenadas")
    print("=" * 60)
    print("  Homing: (0,420) = fondo-izquierda")
    print("  Y+ = atrás (alejándose)")
    print("  Y- = adelante (hacia usuario)")
    print("  X+ = derecha")
    print("  X- = izquierda")
    print("=" * 60)

    ser.close()


if __name__ == "__main__":
    main()
