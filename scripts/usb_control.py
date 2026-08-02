#!/usr/bin/env python3
"""usb_control.py — Gestiona el USB del láser entre Windows y WSL via usbipd.

Usa usbipd-win desde WSL mediante interop de PowerShell (powershell.exe).

Acciones:
  attach     — Pasa el láser de Windows a WSL (carga módulos, permisos)
  detach     — Devuelve el láser a Windows (para usar LaserGRBL)
  status     — Muestra dónde está el láser ahora
  auto       — Si hay G-code generado → attach. Si no → pregunta.

Ejecutar SIN sudo (el script pide sudo cuando lo necesita).
"""

import os
import subprocess
import sys
import time

BUSID = "1-1"
USBIPD = r"C:\Program Files\usbipd-win\usbipd.exe"
PORT = "/dev/ttyUSB0"

RED = "\033[0;31m"; GREEN = "\033[0;32m"; YELLOW = "\033[1;33m"; NC = "\033[0m"
def ok(s): print(f"{GREEN}[✓]{NC} {s}")
def warn(s): print(f"{YELLOW}[!]{NC} {s}")
def err(s): print(f"{RED}[✗]{NC} {s}")


def pwsh(cmd: str) -> tuple[int, str]:
    """Ejecuta un comando en PowerShell de Windows."""
    full = f'& "{USBIPD}" {cmd}'
    result = subprocess.run(
        ["powershell.exe", "-Command", full],
        capture_output=True, text=True, timeout=10
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def has_sudo() -> bool:
    return os.geteuid() == 0


def sudo(cmd: str) -> bool:
    """Ejecuta comando con sudo. Pide contraseña al usuario."""
    try:
        subprocess.run(["sudo"] + cmd.split(), check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def load_modules():
    """Carga los módulos del kernel necesarios."""
    needed = ["ch341", "usbip_host", "vhci_hcd"]
    for mod in needed:
        if os.path.exists(f"/sys/module/{mod}"):
            continue
        confirm = input(f"\n  Módulo {mod} no cargado. ¿Usar sudo? [S/n] ")
        if confirm.lower() not in ('n', 'no'):
            sudo(f"modprobe {mod}")
    # Verificar
    for mod in needed:
        if not os.path.exists(f"/sys/module/{mod}"):
            warn(f"Módulo {mod} no cargado. Ejecutá: sudo modprobe {mod}")
            return False
    return True


def set_permissions():
    """Asegura permisos en el puerto serie."""
    if not os.path.exists(PORT):
        return True
    if os.access(PORT, os.R_OK | os.W_OK):
        return True
    confirm = input(f"\n  {PORT} sin permisos de escritura. ¿Usar sudo? [S/n] ")
    if confirm.lower() not in ('n', 'no'):
        return sudo(f"chmod 666 {PORT}")
    return False


def is_attached() -> bool:
    """Verifica si el dispositivo ya está en WSL."""
    # ¿Existe /dev/ttyUSB0?
    if os.path.exists(PORT):
        return True
    # Preguntar a Windows
    code, out = pwsh("list")
    if code == 0:
        for line in out.splitlines():
            if BUSID in line and "Attached" in line:
                return True
    return False


def is_wsl() -> bool:
    """Detecta si corremos en WSL."""
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except FileNotFoundError:
        return False


def cmd_attach():
    print(f"\n{'='*55}")
    print("  Pasar láser: Windows → WSL")
    print(f"{'='*55}")

    # 1. Verificar si ya está
    if is_attached():
        ok(f"El láser ya está en WSL ({PORT})")
        return

    # 2. Cargar módulos
    if not load_modules():
        err("No se pudieron cargar los módulos del kernel.")
        sys.exit(1)

    # 3. Attach via usbipd
    print(f"\n  Adjuntando dispositivo {BUSID} desde Windows...")
    code, out = pwsh(f"attach --wsl --busid {BUSID}")
    if code != 0:
        # Intentar bind primero
        code2, out2 = pwsh(f"bind --busid {BUSID}")
        time.sleep(1)
        code, out = pwsh(f"attach --wsl --busid {BUSID}")

    time.sleep(2)

    # 4. Verificar
    if os.path.exists(PORT):
        ok(f"Láser detectado en {PORT}")
        set_permissions()
        ok("Listo para usar desde WSL.")
    else:
        warn(f"No se detectó {PORT}. Esperando...")
        time.sleep(2)
        if os.path.exists(PORT):
            ok(f"Láser detectado en {PORT}")
            set_permissions()
        else:
            warn("Reintentá o verificá la conexión física.")


def cmd_detach():
    print(f"\n{'='*55}")
    print("  Devolver láser: WSL → Windows")
    print(f"{'='*55}")

    if not is_attached():
        ok("El láser ya está en Windows (no hay /dev/ttyUSB0 en WSL)")
        pwsh(f"list")
        return

    confirm = input("\n  ¿Devolver el láser a Windows? [S/n] ")
    if confirm.lower() in ('n', 'no'):
        print("  Cancelado.")
        return

    code, out = pwsh(f"detach --busid {BUSID}")
    if code == 0:
        ok("Láser devuelto a Windows. COM5 debería reaparecer.")
        ok("Abrí LaserGRBL y seleccioná COM5.")
    else:
        warn(f"Error al detach: {out}")
        print(f"  Intentá manualmente en PowerShell de Windows:")
        print(f'    usbipd detach --busid {BUSID}')

    # Verificar que ya no está
    time.sleep(1)
    if not os.path.exists(PORT):
        ok("Confirmado: láser liberado de WSL.")


def cmd_status():
    print(f"\n{'='*55}")
    print("  Estado del láser")
    print(f"{'='*55}")

    print(f"\n  Chip:   CH340 (1a86:7523)")
    print(f"  BUSID:  {BUSID}")
    print(f"  Máquina: NEJE Master 2S Plus — 30W, 255×420mm")

    # WSL side
    if os.path.exists(PORT):
        ok(f"WSL:    {PORT} presente")
        import serial
        try:
            ser = serial.Serial(PORT, 115200, timeout=0.5)
            time.sleep(1.5)
            ser.write(b"$I\r\n")
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting or 128).decode(errors="ignore")
            ser.close()
            for line in resp.splitlines():
                line = line.strip()
                if line and line != "ok":
                    ok(f"GRBL:   {line}")
        except Exception as e:
            warn(f"GRBL:   no responde ({e})")
    else:
        warn(f"WSL:    {PORT} NO presente → láser en Windows")

    # Windows side
    code, out = pwsh("list")
    if code == 0:
        in_wsl = False
        for line in out.splitlines():
            if BUSID in line:
                if "Attached" in line:
                    in_wsl = True
                    ok(f"Windows: compartido a WSL")
                else:
                    ok(f"Windows: COM5 disponible")
                break
    else:
        warn(f"Windows: usbipd no accesible")


def cmd_auto():
    """Modo automático: si hay output/ con G-code → attach, si no → pregunta."""
    skill_dir = os.path.expanduser("~/laser-pcb-skill/output")
    has_gcode = False
    if os.path.isdir(skill_dir):
        for f in os.listdir(skill_dir):
            if f.endswith(".gcode"):
                has_gcode = True
                break

    print(f"\n{'='*55}")
    print("  Auto-detección")
    print(f"{'='*55}")

    if has_gcode:
        print(f"\n  Hay G-code generado → asumo que querés attach.")
        cmd_attach()
    else:
        print(f"\n  No hay G-code generado. ¿Qué querés hacer?")
        if is_attached():
            print("  El láser está en WSL ahora.")
            print("  1) Seguir usando desde WSL")
            print("  2) Devolver a Windows (LaserGRBL)")
            choice = input("  > ")
            if choice == "2":
                cmd_detach()
        else:
            print("  El láser está en Windows (COM5).")
            print("  1) Pasar a WSL para usar la skill")
            print("  2) Seguir en Windows (LaserGRBL)")
            choice = input("  > ")
            if choice == "1":
                cmd_attach()


def main():
    if not is_wsl():
        print("Este script está pensado para correr EN WSL.")
        print("En Linux nativo, el láser aparece en /dev/ttyUSB0 directamente.")
        return

    action = sys.argv[1] if len(sys.argv) > 1 else "auto"

    if action == "attach":
        cmd_attach()
    elif action == "detach":
        cmd_detach()
    elif action == "status":
        cmd_status()
    elif action in ("auto", ""):
        cmd_auto()
    else:
        print(f"Uso: {sys.argv[0]} [attach|detach|status|auto]")
        print()
        print("  attach   Pasar láser de Windows a WSL")
        print("  detach   Devolver láser de Windows a WSL")
        print("  status   Ver dónde está el láser")
        print("  auto     Detectar y sugerir (default)")


if __name__ == "__main__":
    main()
