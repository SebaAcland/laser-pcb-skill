#!/usr/bin/env python3
"""detect_laser.py — Detecta y muestra info del grabador láser conectado.

Prueba puertos ttyUSB/ttyACM, consulta GRBL $$ y $I.
"""

import glob
import sys

try:
    import serial
except ImportError:
    print("ERROR: pyserial no instalado. pip install pyserial")
    sys.exit(1)


BAUD_RATES = [115200, 250000, 9600]
GRBL_COMMANDS = [
    ("$I", "Versión de firmware"),
    ("$$", "Configuración completa"),
    ("$G", "Estado actual"),
]


def probe_grbl(port: str) -> dict | None:
    """Prueba un puerto a diferentes baud rates buscando respuesta GRBL."""
    for baud in BAUD_RATES:
        try:
            ser = serial.Serial(port, baud, timeout=1.5)
            ser.reset_input_buffer()
            ser.write(b"\r\n\r\n")
            import time
            time.sleep(0.5)
            ser.write(b"$I\r\n")
            time.sleep(0.3)
            response = ser.read(ser.in_waiting or 512).decode(errors="ignore")
            ser.close()
            if "Grbl" in response or "grbl" in response.lower():
                ser2 = serial.Serial(port, baud, timeout=1)
                return {"port": port, "baud": baud, "response": response.strip()}
        except (serial.SerialException, OSError) as e:
            continue
    return None


def query_grbl(port: str, baud: int, cmd: str) -> str:
    """Envía un comando a GRBL y devuelve la respuesta."""
    try:
        ser = serial.Serial(port, baud, timeout=1.5)
        ser.write(b"\r\n")
        import time
        time.sleep(0.2)
        ser.reset_input_buffer()
        ser.write(f"{cmd}\r\n".encode())
        time.sleep(0.5)
        resp = ser.read(ser.in_waiting or 2048).decode(errors="ignore")
        ser.close()
        return resp.strip()
    except Exception as e:
        return f"Error: {e}"


def main():
    devices = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")

    if not devices:
        print("No se encontraron puertos USB serie.")
        print("¿Conectaste el láser? ¿Ejecutaste usbipd wsl attach?")
        sys.exit(1)

    print(f"Puertos encontrados: {', '.join(devices)}\n")

    for dev in devices:
        result = probe_grbl(dev)
        if result:
            print(f"GRBL detectado en {result['port']} @ {result['baud']} baud")
            print("-" * 50)
            for cmd, desc in GRBL_COMMANDS:
                print(f"\n[{desc}]")
                resp = query_grbl(result["port"], result["baud"], cmd)
                print(resp)
            print("-" * 50)
            return

    print("No se detectó GRBL en ningún puerto. Verificá:")
    print("  1. ¿El láser está prendido y conectado por USB?")
    print("  2. En WSL: ¿ejecutaste 'usbipd wsl attach'?")
    print("  3. ¿El firmware de la placa es GRBL? (no Marlin ni otro)")


if __name__ == "__main__":
    main()
