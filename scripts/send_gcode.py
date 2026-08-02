#!/usr/bin/env python3
"""send_gcode.py — Envía archivos G-code al láser via GRBL por puerto serie.

Uso:
    python3 send_gcode.py archivo.gcode                     # enviar
    python3 send_gcode.py archivo.gcode --port /dev/ttyUSB0 # puerto custom
    python3 send_gcode.py archivo.gcode --dry-run           # simular
    python3 send_gcode.py archivo.gcode --wait-homing       # esperar $H antes
"""

import serial
import sys
import time
import re
from pathlib import Path

DEFAULT_PORT = "/dev/ttyUSB0"
BAUD = 115200
MAX_X = 255
MAX_Y = 420


def validate_gcode(gcode_path: Path) -> bool:
    """Valida que todas las coordenadas estén dentro de los límites."""
    with open(gcode_path) as f:
        lines = f.readlines()

    violations = []
    for i, line in enumerate(lines, 1):
        x_match = re.search(r'X(-?\d+\.?\d*)', line)
        y_match = re.search(r'Y(-?\d+\.?\d*)', line)

        if x_match:
            x = float(x_match.group(1))
            if x < 0 or x > MAX_X:
                violations.append(f"Línea {i}: X={x} fuera de rango [0,{MAX_X}]")

        if y_match:
            y = float(y_match.group(1))
            if y < 0 or y > MAX_Y:
                violations.append(f"Línea {i}: Y={y} fuera de rango [0,{MAX_Y}]")

    if violations:
        print(f"⚠ {len(violations)} violaciones de límites:")
        for v in violations[:10]:
            print(f"  {v}")
        if len(violations) > 10:
            print(f"  ... y {len(violations)-10} más")
        return False

    return True


def send_file(gcode_path: Path, port: str = DEFAULT_PORT, dry_run: bool = False,
              wait_homing: bool = False) -> bool:
    """Envía un archivo G-code a GRBL línea por línea."""
    if not gcode_path.exists():
        print(f"ERROR: {gcode_path} no existe")
        return False

    # Validar límites antes de enviar
    if not validate_gcode(gcode_path):
        print("\n❌ G-code fuera de límites. No enviado.")
        print("   Usar --flip-y en raster_to_gcode.py o revisar posición de placa")
        return False

    with open(gcode_path) as f:
        lines = []
        for l in f:
            l = l.strip()
            if l and not l.startswith(";"):
                lines.append(l)
    total = len(lines)
    print(f"Archivo: {gcode_path.name} ({total} líneas)\n")

    if dry_run:
        print("[DRY RUN] Simulando envío...")
        for i, line in enumerate(lines[:5]):
            print(f"  [{i+1}/{total}] {line[:70]}")
        print(f"  ... ({total - 5} líneas más)")
        print(f"\n[DRY RUN] OK")
        return True

    if not Path(port).exists():
        print(f"ERROR: Puerto {port} no existe.")
        return False

    ser = serial.Serial(port, BAUD, timeout=0.1)
    time.sleep(2)
    ser.reset_input_buffer()

    # Unlock
    ser.write(b"$X\r\n")
    time.sleep(0.2)
    ser.reset_input_buffer()

    # Verificar estado GRBL
    ser.write(b"?\r\n")
    time.sleep(0.2)
    status = ser.read(ser.in_waiting or 128).decode(errors="ignore")
    ser.reset_input_buffer()
    soft_limits_disabled = False

    if "Alarm" in status:
        print("⚠  GRBL en ALARM. Desbloqueando ($X)...")
        ser.write(b"$X\r\n")
        time.sleep(0.3)
        ser.reset_input_buffer()
        print("   Soft limits → OFF temporal")
        ser.write(b"$20=0\r\n")
        time.sleep(0.2)
        ser.reset_input_buffer()
        soft_limits_disabled = True

    # Verificar GRBL version
    ser.write(b"$I\r\n")
    time.sleep(0.4)
    resp = ser.read(ser.in_waiting or 256).decode(errors="ignore")
    if not any(kw in resp.lower() for kw in ("grbl", "ver:", "[ver")):
        print(f"ERROR: No se detectó GRBL. Respuesta: {resp[:80]}")
        ser.close()
        return False
    ver = resp.strip().split("\r\n")[0] if resp.strip() else "?"
    print(f"GRBL: {ver}")
    ser.reset_input_buffer()

    # Homing opcional
    if wait_homing:
        print("Homing...")
        ser.write(b"$H\r\n")
        for _ in range(120):
            ser.write(b"?\r\n")
            time.sleep(0.1)
            if ser.in_waiting:
                if b"Idle" in ser.read(ser.in_waiting):
                    break
            time.sleep(0.05)
        ser.reset_input_buffer()

    # Enviar con flow control GRBL estándar
    sent = 0
    errors = 0
    pending = 0
    start = time.time()
    last_ok = time.time()
    idx = 0

    print(f"\nEnviando {total} líneas...")

    while idx < total or pending > 0:
        # Leer respuestas
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode(errors="ignore")
            for rl in data.splitlines():
                rl = rl.strip()
                if rl == "ok":
                    pending -= 1
                    sent += 1
                    last_ok = time.time()
                elif "error" in rl.lower():
                    errors += 1
                    pending -= 1
        else:
            time.sleep(0.005)

        # Enviar más líneas
        while pending < 40 and idx < total:
            ser.write(f"{lines[idx]}\r\n".encode())
            pending += 1
            idx += 1

        # Progreso
        if sent > 0 and sent % 200 == 0:
            elapsed = time.time() - start
            rate = sent / elapsed if elapsed > 0 else 0
            print(f"  {sent}/{total} ({100*sent/total:.0f}%) — {rate:.0f} l/s")

        # Total timeout: 15 segundos sin respuestas cuando ya terminamos de enviar
        if idx >= total and pending > 0 and time.time() - last_ok > 15:
            print(f"  ⚠ Timeout final. {pending} líneas pendientes.")
            break

    elapsed = time.time() - start

    # Esperar Idle
    for _ in range(30):
        ser.write(b"?\r\n")
        time.sleep(0.15)
        if ser.in_waiting:
            if b"Idle" in ser.read(ser.in_waiting):
                break
        time.sleep(0.05)

    ser.close()

    # Restaurar soft limits
    if soft_limits_disabled:
        time.sleep(0.5)
        ser2 = serial.Serial(port, BAUD, timeout=0.3)
        time.sleep(1)
        ser2.write(b"$20=1\r\n")
        time.sleep(0.2)
        ser2.close()
        print("   Soft limits → ON")

    print(f"\n{'='*50}")
    print(f"  Líneas: {sent}/{total} — Errores: {errors}")
    print(f"  Tiempo: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"{'='*50}")
    return errors == 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    gcode_path = Path(sys.argv[1])
    port = DEFAULT_PORT
    dry_run = False
    wait_homing = False

    for arg in sys.argv[2:]:
        if arg.startswith("--port="):
            port = arg.split("=", 1)[1]
        elif arg == "--dry-run":
            dry_run = True
        elif arg == "--wait-homing":
            wait_homing = True

    ok = send_file(gcode_path, port, dry_run, wait_homing)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
