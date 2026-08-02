#!/usr/bin/env python3
"""env_check.py — Detecta el entorno de ejecución y herramientas disponibles.

Muestra: WSL vs bare-metal, kicad-cli, svg2gcode, bCNC, puertos USB.
"""

import os
import shutil
import subprocess
import sys


def is_wsl():
    """Detecta si corremos dentro de WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except FileNotFoundError:
        return "WSL_DISTRO_NAME" in os.environ or "WSL_INTEROP" in os.environ


def has_tool(name):
    """Verifica si una herramienta está en PATH."""
    return shutil.which(name) is not None


def check_kicad_cli():
    print("\n── KiCad CLI ──")
    if has_tool("kicad-cli"):
        result = subprocess.run(["kicad-cli", "version"], capture_output=True, text=True)
        print(f"  ✅ kicad-cli ({result.stdout.strip()})")
    else:
        print("  ❌ kicad-cli no encontrado")
        print("     Instalar: sudo apt install kicad-cli")


def check_svg2gcode():
    print("\n── svg2gcode ──")
    if has_tool("svg2gcode-cli"):
        result = subprocess.run(["svg2gcode-cli", "--version"], capture_output=True, text=True)
        print(f"  ✅ svg2gcode-cli ({result.stdout.strip()})")
    else:
        print("  ❌ svg2gcode-cli no encontrado")
        if has_tool("cargo"):
            print("     Instalar: cargo install svg2gcode-cli")
        else:
            print("     Instalar Rust primero: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
            print("     Luego: cargo install svg2gcode-cli")


def check_bcnc():
    print("\n── bCNC ──")
    try:
        result = subprocess.run([sys.executable, "-c", "import bCNC; print(bCNC.__file__)"],
                                capture_output=True, text=True)
        print(f"  ✅ bCNC instalado")
    except subprocess.CalledProcessError:
        print("  ⚠ bCNC no instalado (opcional, para enviar G-code)")
        print("     Instalar: pip install bCNC")


def check_usb():
    print("\n── Puertos USB ──")
    globs = ["/dev/ttyUSB*", "/dev/ttyACM*"]
    found = False
    for g in globs:
        import glob as gl
        for p in gl.glob(g):
            print(f"  🔌 {p}")
            found = True
    if not found:
        print("  ⚠ No se detectaron puertos serie USB")
        print("     Si estás en WSL, en PowerShell de Windows ejecutá:")
        print("       usbipd wsl list")
        print("       usbipd wsl attach --busid <BUS_ID>")


def check_grbl():
    print("\n── GRBL (láser) ──")
    import glob as gl
    devices = gl.glob("/dev/ttyUSB*") + gl.glob("/dev/ttyACM*")
    if not devices:
        print("  ⚠ No se encontró puerto para consultar GRBL")
        return

    dev = devices[0]
    print(f"  Probando {dev} a 115200 baud...")
    try:
        import serial
        ser = serial.Serial(dev, 115200, timeout=1)
        ser.write(b"\r\n\r\n")
        ser.write(b"$I\r\n")
        response = ser.read_until(b"ok").decode(errors="ignore").strip()
        ser.close()
        if response:
            print(f"  ✅ GRBL responde: {response}")
        else:
            print(f"  ⚠ Sin respuesta de GRBL en {dev}")
    except ImportError:
        print("  ⚠ pyserial no instalado. Instalar: pip install pyserial")
    except Exception as e:
        print(f"  ⚠ Error al conectar: {e}")


def main():
    print("=" * 60)
    print("  KiCad → Laser PCB — Verificación de entorno")
    print("=" * 60)

    env = "WSL" if is_wsl() else "Linux nativo"
    print(f"\n  Sistema: {env} ({os.uname().sysname} {os.uname().release})")

    check_kicad_cli()
    check_svg2gcode()
    check_bcnc()
    check_usb()
    check_grbl()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
