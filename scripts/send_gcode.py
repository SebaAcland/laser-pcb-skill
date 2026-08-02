#!/usr/bin/env python3
"""send_gcode.py — Envía archivos G-code al láser via GRBL.

Flow control GRBL estándar: envía línea, espera "ok", siguiente línea.
Robusto y simple.

Uso:
    python3 send_gcode.py archivo.gcode
    python3 send_gcode.py archivo.gcode --dry-run
"""

import serial
import sys
import time
import re
from pathlib import Path

DEFAULT_PORT = "/dev/ttyUSB0"
BAUD = 115200
GRBL_BUFFER = 128


def validate_gcode(gcode_path: Path) -> bool:
    """Valida que el rango de coordenadas no exceda los límites."""
    with open(gcode_path) as f:
        lines = f.readlines()

    x_vals, y_vals = [], []
    for line in lines:
        x_match = re.search(r'X(-?\d+\.?\d*)', line)
        y_match = re.search(r'Y(-?\d+\.?\d*)', line)
        if x_match: x_vals.append(float(x_match.group(1)))
        if y_match: y_vals.append(float(y_match.group(1)))

    if x_vals:
        x_range = max(x_vals) - min(x_vals)
        if x_range > 255:
            print(f"⚠ X rango {x_range:.1f}mm excede 255mm")
            return False
    if y_vals:
        y_range = max(y_vals) - min(y_vals)
        if y_range > 420:
            print(f"⚠ Y rango {y_range:.1f}mm excede 420mm")
            return False
    print(f"✓ Validado: X={min(x_vals):.1f}~{max(x_vals):.1f}  Y={min(y_vals):.1f}~{max(y_vals):.1f}")
    return True


def read_response(ser) -> str:
    """Lee respuesta de GRBL hasta que no haya más datos."""
    resp = ""
    for _ in range(10):
        if ser.in_waiting:
            resp += ser.read(ser.in_waiting).decode(errors="ignore")
            time.sleep(0.01)
        else:
            break
    return resp.strip()


def send_line(ser, line: str) -> str:
    """Envía una línea G-code y espera respuesta."""
    ser.write(f"{line}\r\n".encode())
    time.sleep(0.02)
    for _ in range(50):  # max 5 segundos esperando respuesta
        resp = read_response(ser)
        if resp:
            return resp
        time.sleep(0.1)
    return ""


def send_file(gcode_path: Path, port: str = DEFAULT_PORT, dry_run: bool = False):
    """Envía un archivo G-code a GRBL línea por línea con flow control."""
    if not gcode_path.exists():
        print(f"ERROR: {gcode_path} no existe")
        return

    if not validate_gcode(gcode_path):
        print("❌ G-code fuera de límites")
        return

    with open(gcode_path) as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith(";")]
    total = len(lines)
    print(f"Archivo: {gcode_path.name} ({total} líneas)")

    if dry_run:
        print("[DRY RUN] OK")
        return

    ser = serial.Serial(port, BAUD, timeout=0.05)
    time.sleep(2)
    ser.reset_input_buffer()

    # Unlock y preparar
    ser.write(b"$X\r\n"); time.sleep(0.3); ser.reset_input_buffer()
    ser.write(b"$20=0\r\n"); time.sleep(0.2); ser.reset_input_buffer()

    # Verificar GRBL
    ser.write(b"$I\r\n"); time.sleep(0.3)
    ver = read_response(ser)
    if not any(kw in ver.lower() for kw in ("grbl", "ver:", "[ver")):
        print(f"ERROR: No GRBL. Respuesta: {ver[:60]}")
        ser.close()
        return
    print(f"GRBL: {ver.splitlines()[0][:50]}")
    ser.reset_input_buffer()

    # Enviar línea por línea
    sent = 0
    errors = 0
    start = time.time()

    print(f"\nEnviando {total} líneas...\n")

    for i, line in enumerate(lines):
        resp = send_line(ser, line)

        if "ok" in resp:
            sent += 1
        elif "error" in resp.lower():
            errors += 1
            print(f"  ⚠ Línea {i+1}: {resp[:60]}  → {line[:50]}")

        # Progreso cada 200 líneas
        if sent > 0 and sent % 500 == 0:
            elapsed = time.time() - start
            rate = sent / elapsed
            eta = (total - sent) / rate / 60 if rate > 0 else 0
            print(f"  {sent}/{total} ({100*sent/total:.0f}%) — {rate:.0f} l/s — ETA {eta:.0f}min")

        # Pequeña pausa para no saturar CPU
        time.sleep(0.001)

    elapsed = time.time() - start

    # Esperar que termine el buffer físico
    print("  Esperando buffer...")
    for _ in range(60):
        ser.write(b"?\r\n")
        time.sleep(0.2)
        resp = read_response(ser)
        if "Idle" in resp:
            break
        time.sleep(0.2)

    ser.write(b"M5\r\n")
    ser.close()

    print(f"\n{'='*50}")
    print(f"  Líneas: {sent}/{total} — Errores: {errors}")
    print(f"  Tiempo: {elapsed/60:.1f} min")
    print(f"{'='*50}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    gcode_path = Path(sys.argv[1])
    port = DEFAULT_PORT
    dry_run = False

    for arg in sys.argv[2:]:
        if arg.startswith("--port="):
            port = arg.split("=", 1)[1]
        elif arg == "--dry-run":
            dry_run = True

    send_file(gcode_path, port, dry_run)


if __name__ == "__main__":
    main()
