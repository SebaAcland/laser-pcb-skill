#!/usr/bin/env python3
"""export_svg.py — Exporta capas de un .kicad_pcb a SVG.

Soporta WSL (kicad-cli de Windows) y Linux nativo.

Uso:
    python3 export_svg.py <board.kicad_pcb> [output_dir]
    python3 export_svg.py <board.kicad_pcb> --no-edge  (solo pistas, sin borde)

Ejemplo WSL:
    python3 export_svg.py "C:\\Users\\...\\mi_placa.kicad_pcb"
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path.home() / "laser-pcb-skill"
OUTPUT_DIR = SKILL_DIR / "output"

# Nombres de archivos de salida
TRACES_SVG = "pcb_traces_raw.svg"
EDGE_SVG = "pcb_edge_raw.svg"


def is_wsl() -> bool:
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except FileNotFoundError:
        return "WSL_DISTRO_NAME" in os.environ


def wsl_to_win(path: str) -> str:
    """Convierte path WSL (/mnt/c/...) a path Windows (C:\\...)."""
    p = Path(path).resolve()
    parts = p.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "mnt":
        drive = parts[2].upper()
        rest = "\\".join(parts[3:])
        return f"{drive}:\\{rest}"
    return str(p)


def find_kicad_cli() -> dict:
    """Busca kicad-cli. Devuelve {'exe': ruta-ejecutable, 'type': 'win'|'linux'}."""
    # 1. kicad-cli nativo de Linux
    if shutil.which("kicad-cli"):
        try:
            subprocess.run(["kicad-cli", "version"], capture_output=True, check=True)
            return {"exe": "kicad-cli", "type": "linux"}
        except Exception:
            pass

    # 2. kicad-cli de Windows (vía WSL interop)
    win_paths = [
        r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
    ]
    for wpath in win_paths:
        wsl_exe = wpath.replace("C:\\", "/mnt/c/").replace("\\", "/")
        if os.path.exists(wsl_exe):
            try:
                subprocess.run([wsl_exe, "version"], capture_output=True, check=True)
                return {"exe": wsl_exe, "type": "win", "win_path": wpath}
            except Exception:
                pass

    return None


def export_layer(kicad: dict, board_path: str, layers: str, output: str) -> bool:
    """Exporta una capa a SVG."""
    exe = kicad["exe"]
    kicad_type = kicad["type"]

    if kicad_type == "win":
        board = wsl_to_win(board_path) if not board_path.startswith("C:") else board_path
        # El output DEBE estar en filesystem Windows. Usar Desktop como temp.
        temp_out = r"C:\Users\Usuario\Desktop\test mcp kicad\_temp_export.svg"
        out = temp_out
    else:
        board = board_path
        out = output

    cmd = [exe, "pcb", "export", "svg",
           "--layers", layers,
           "--page-size-mode", "2",
           "--exclude-drawing-sheet",
           "-o", out, board]

    print(f"  Exportando {layers} ...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        return False

    # Copiar de Windows temp al destino WSL
    if kicad_type == "win":
        wsl_temp = temp_out.replace("C:\\", "/mnt/c/").replace("\\", "/")
        if os.path.exists(wsl_temp):
            os.makedirs(os.path.dirname(output), exist_ok=True)
            with open(wsl_temp, "rb") as src, open(output, "wb") as dst:
                dst.write(src.read())
            os.remove(wsl_temp)
        else:
            # Probar path alternativo
            alt = temp_out.replace("C:\\", "C:\\mnt\\c\\")
            wsl_alt = alt.replace("C:\\mnt\\c\\", "/mnt/c/").replace("\\", "/")
            if os.path.exists(wsl_alt):
                os.makedirs(os.path.dirname(output), exist_ok=True)
                with open(wsl_alt, "rb") as src, open(output, "wb") as dst:
                    dst.write(src.read())
                return True
            print(f"  WARN: temp no encontrado en {wsl_temp}")
            return False

    if os.path.exists(output):
        size = os.path.getsize(output)
        print(f"  OK: {Path(output).name} ({size:,} bytes)")
        return True
    return False


def generate_preview(out_dir: Path):
    """Genera PNG del SVG de pistas para modo raster."""
    traces = out_dir / TRACES_SVG
    if not traces.exists():
        return

    # 1. PNG preview
    try:
        import cairosvg
        png_path = out_dir / "pcb_preview.png"
        cairosvg.svg2png(url=str(traces), write_to=str(png_path))
        print(f"\n  Preview PNG: {png_path.stat().st_size:,} bytes")
    except ImportError:
        print("\n  (pip install cairosvg para preview)")

    # 2. PNG raster (alta resolución para modo raster, fondo blanco)
    rsvg = shutil.which("rsvg-convert")
    raster_out = out_dir / "pcb_raster.png"
    if rsvg:
        subprocess.run(
            [rsvg, "-f", "png", "-d", "350", "-p", "350",
             "--background-color", "white",
             "-o", str(raster_out), str(traces)],
            capture_output=True, check=True
        )
        print(f"  Raster PNG: {raster_out.stat().st_size:,} bytes @ 350 DPI")
    else:
        print("  (apt install librsvg2-bin para raster PNG)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    board_path = sys.argv[1]
    out_dir = OUTPUT_DIR
    include_edge = True

    for arg in sys.argv[2:]:
        if arg == "--no-edge":
            include_edge = False
        elif not arg.startswith("--"):
            out_dir = Path(arg)

    out_dir.mkdir(parents=True, exist_ok=True)

    # Encontrar kicad-cli
    kicad = find_kicad_cli()
    if not kicad:
        print("ERROR: kicad-cli no encontrado.")
        print("  En Linux:      sudo apt install kicad-cli")
        print("  En WSL (Win):  instalar KiCad 9.x o 10.x en C:\\Program Files\\KiCad\\")
        sys.exit(1)

    env = "WSL → kicad-cli Windows" if kicad["type"] == "win" else "Linux nativo"
    print(f"kicad-cli: {kicad['exe']}")
    print(f"Entorno:   {env}")
    print(f"Board:     {board_path}")
    print(f"Output:    {out_dir}/\n")

    traces_out = str(out_dir / TRACES_SVG)
    edge_out = str(out_dir / EDGE_SVG)

    success = export_layer(kicad, board_path, "B.Cu", traces_out)
    if include_edge:
        export_layer(kicad, board_path, "Edge.Cuts", edge_out)

    if success:
        generate_preview(out_dir)
        print(f"\n✓ Listo. Archivos en {out_dir}/")
        for f in sorted(out_dir.glob("pcb_*")):
            print(f"  {f.name}")
    else:
        print("\n✗ Falló la exportación.")
        sys.exit(1)


if __name__ == "__main__":
    main()
