#!/usr/bin/env python3
"""position_laser.py — Posiciona el láser de forma segura para grabar PCBs.

Uso:
    python3 position_laser.py                    # homing + pregunta
    python3 position_laser.py --back             # placa al fondo
    python3 position_laser.py --front            # placa al frente
    python3 position_laser.py --x 50 --y 100     # posición manual
    python3 position_laser.py --frame            # solo dibujar marco
"""

import serial
import sys
import time
from pathlib import Path

PORT = "/dev/ttyUSB0"
BAUD = 115200


def unlock(ser):
    """Desbloquea GRBL."""
    ser.write(b"$X\r\n")
    time.sleep(0.2)
    ser.reset_input_buffer()


def check_status(ser):
    """Retorna el status actual."""
    ser.write(b"?\r\n")
    time.sleep(0.2)
    return ser.read(ser.in_waiting or 128).decode(errors="ignore").strip()


def home(ser):
    """Homing."""
    print("► Homing...")
    ser.write(b"$H\r\n")
    for _ in range(60):
        ser.write(b"?\r\n")
        time.sleep(0.2)
        if ser.in_waiting:
            buf = ser.read(ser.in_waiting).decode(errors="ignore")
            if "Idle" in buf:
                print("  ✓ Homing OK")
                return True
            if "Alarm" in buf:
                print("  ✗ ALARM")
                return False
        time.sleep(0.1)
    return False


def move_to(ser, x: float, y: float, feedrate: int = 2000):
    """Mueve a posición absoluta."""
    print(f"► Moviendo a X={x} Y={y}...")
    ser.write(f"G90 G0 X{x} Y{y} F{feedrate}\r\n".encode())
    time.sleep(3)
    ser.write(b"?\r\n")
    time.sleep(0.2)
    pos = ser.read(ser.in_waiting).decode(errors="ignore").strip()
    print(f"  Pos: {pos[:70]}")


def set_zero(ser):
    """Fija G92 X0 Y0 en posición actual."""
    ser.write(b"G92 X0 Y0\r\n")
    time.sleep(0.1)
    print("  ✓ Cero de trabajo fijado")


def draw_frame(ser, w: float = 60, h: float = 48, power: int = 15):
    """Dibuja un marco de referencia. Y va negativo (hacia adelante).
    
    Después de G92 en el fondo (machine Y=420):
    - G1 Y-h = hacia adelante (Y-), dentro de límites
    - G1 Y+h = vuelve al origen, seguro
    """
    print(f"► Marco {w}×{h}mm (M4 S{power})...")
    ser.write(b"M5\r\n")
    time.sleep(0.1)
    ser.write(f"M4 S{power}\r\n".encode())
    time.sleep(0.2)
    ser.write(f"G1 X{w} F800\r\n".encode())   # X+, seguro (max 255)
    time.sleep(2)
    ser.write(f"G1 Y-{h} F800\r\n".encode())  # Y-, hacia adelante (seguro)
    time.sleep(2)
    ser.write(f"G1 X0 F800\r\n".encode())     # vuelve X
    time.sleep(2)
    ser.write(f"G1 Y{h} F800\r\n".encode())   # vuelve Y al origen
    time.sleep(2)
    ser.write(b"M5\r\n")
    print("  ✓ Marco dibujado")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    position = "back"
    x_pos = 0
    y_pos = 50
    frame_only = False

    for arg in sys.argv[1:]:
        if arg == "--back":
            position = "back"
        elif arg == "--front":
            position = "front"
        elif arg == "--frame":
            frame_only = True
        elif arg.startswith("--x="):
            x_pos = float(arg.split("=", 1)[1])
        elif arg.startswith("--y="):
            y_pos = float(arg.split("=", 1)[1])

    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    time.sleep(2)
    ser.reset_input_buffer()

    # Homing
    unlock(ser)
    if not home(ser):
        ser.close()
        sys.exit(1)

    # Desactivar soft limits
    ser.write(b"$20=0\r\n")
    time.sleep(0.1)
    ser.reset_input_buffer()

    if frame_only:
        # Solo dibujar marco en posición actual
        set_zero(ser)
        draw_frame(ser)
    elif position == "back":
        # Placa al fondo (láser ya está ahí después de homing)
        set_zero(ser)
        draw_frame(ser)
        print("\n🎯 Placa al FONDO. Marco dibujado.")
        print("   Poné la placa DENTRO del marco")
    elif position == "front":
        # Placa al frente
        move_to(ser, 0, 50)
        set_zero(ser)
        draw_frame(ser)
        print("\n🎯 Placa al FRENTE. Marco dibujado.")
        print("   Poné la placa DENTRO del marco")
    else:
        # Posición manual
        move_to(ser, x_pos, y_pos)
        set_zero(ser)
        draw_frame(ser)
        print(f"\n🎯 Placa en ({x_pos},{y_pos}). Marco dibujado.")

    ser.close()


if __name__ == "__main__":
    main()
