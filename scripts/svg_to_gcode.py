#!/usr/bin/env python3
"""svg_to_gcode.py — Convierte SVG de KiCad a G-code para láser usando svg2gcode.

Uso: python3 svg_to_gcode.py <input_dir> [--settings config/laser_defaults.json]

Genera:
  - output/pcb_traces.gcode
  - output/pcb_edge.gcode
"""

import json
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path.home() / "laser-pcb-skill" / "output"
CONFIG_DIR = Path.home() / "laser-pcb-skill" / "config"

DEFAULTS = {
    "traces": {
        "dpi": 96,
        "feedrate": 1000,
        "on": "M4 S70",
        "off": "M5",
        "tolerance": 0.01,
        "begin": "G21 ; mm",
        "end": "M5\nG0 X0 Y0",
    },
    "edge": {
        "dpi": 96,
        "feedrate": 800,
        "on": "M4 S100",
        "off": "M5",
        "tolerance": 0.01,
        "begin": "G21 ; mm",
        "end": "M5\nG0 X0 Y0",
    },
}


def find_svg2gcode():
    """Busca svg2gcode en PATH (binario de svg2gcode-cli crate)."""
    for name in ("svg2gcode", "svg2gcode-cli"):
        try:
            subprocess.run([name, "--version"], capture_output=True, check=True)
            return name
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    print("ERROR: svg2gcode no encontrado.")
    print("  Instalar: cargo install svg2gcode-cli")
    print("  O bajar binario: https://github.com/sameer/svg2gcode/releases")
    sys.exit(1)


def load_settings(settings_path: Path):
    """Carga settings JSON o usa defaults."""
    if settings_path and settings_path.exists():
        with open(settings_path) as f:
            return json.load(f)
    return DEFAULTS


def convert_svg_to_gcode(svg_path: Path, gcode_path: Path, settings: dict, binary: str):
    """Ejecuta svg2gcode para convertir SVG a G-code."""
    cmd = [binary, str(svg_path)]
    for key, value in settings.items():
        if key in ("on", "off", "begin", "end"):
            cmd.extend([f"--{key}", value])
        elif key == "dpi":
            cmd.extend(["--dpi", str(value)])
        elif key == "feedrate":
            cmd.extend(["--feedrate", str(value)])
        elif key == "tolerance":
            cmd.extend(["--tolerance", str(value)])
    cmd.extend(["-o", str(gcode_path)])

    print(f"  {svg_path.name} → {gcode_path.name} ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        return False
    print(f"  OK: {gcode_path.stat().st_size:,} bytes")
    return True


def main():
    svg2gcode = find_svg2gcode()

    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_DIR
    if not input_dir.exists():
        print(f"ERROR: {input_dir} no existe")
        sys.exit(1)

    settings_path = None
    for arg in sys.argv[2:]:
        if arg.startswith("--settings="):
            settings_path = Path(arg.split("=", 1)[1])

    settings = load_settings(settings_path)

    convert_svg_to_gcode(
        input_dir / "pcb_traces_raw.svg",
        input_dir / "pcb_traces.gcode",
        settings["traces"],
        svg2gcode,
    )
    convert_svg_to_gcode(
        input_dir / "pcb_edge_raw.svg",
        input_dir / "pcb_edge.gcode",
        settings["edge"],
        svg2gcode,
    )

    print(f"\nListo. G-code generado en {input_dir}/")
    print(f"  pcb_traces.gcode — grabado de pistas")
    print(f"  pcb_edge.gcode   — corte del contorno")


if __name__ == "__main__":
    main()
