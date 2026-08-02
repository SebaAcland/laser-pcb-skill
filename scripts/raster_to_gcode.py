#!/usr/bin/env python3
"""raster_to_gcode.py — Convierte PNG a G-code de escaneo raster para láser.

El PNG debe tener:
  - NEGRO (pixel oscuro) = pista/cobre a CONSERVAR → láser OFF
  - BLANCO (pixel claro) = fondo a ELIMINAR      → láser ON (quema pintura)

Uso:
    python3 raster_to_gcode.py pcb.png
    python3 raster_to_gcode.py pcb.png --dpi 250 --feedrate 1500 --power S70

Genera:
    output/pcb_raster.gcode
"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow no instalado. sudo apt install python3-pil")
    sys.exit(1)

SKILL_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = SKILL_DIR / "output"


def png_to_raster_gcode(png_path: Path, dpi: int = 250, feedrate: int = 1500,
                        power: str = "S70", laser_on: str = "M4",
                        direction: str = "unidirectional") -> Path:
    """Convierte PNG a G-code raster. Retorna path del archivo generado."""
    img = Image.open(png_path).convert("L")  # grayscale
    w, h = img.size

    pixel_mm = 25.4 / dpi
    board_w = w * pixel_mm
    board_h = h * pixel_mm

    print(f"PNG: {w}×{h}px @ {dpi} DPI = {board_w:.1f}×{board_h:.1f}mm")
    print(f"Filas: {h}, Pasos por fila: {w}")
    print(f"Tiempo est: {h * board_w / feedrate * 60:.0f}s (~{h * board_w / feedrate:.1f} min)")

    gcode_path = OUTPUT_DIR / "pcb_raster.gcode"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(gcode_path, "w") as f:
        f.write("G21 ; mm\n")
        f.write("G90 ; absolute\n")
        f.write("G0 X0 Y0\n")
        f.write("M5\n\n")

        last_x = 0.0
        current_y = h * pixel_mm  # empezar desde arriba (Y max)

        for row in range(h):
            # Leer fila de píxeles
            pixels = [img.getpixel((x, row)) for x in range(w)]

            # Moverse al inicio de la fila
            if direction == "unidirectional":
                f.write(f"M5\n")
                f.write(f"G0 X0 Y{current_y:.4f}\n")
                scan_pixels = pixels
                x_start = 0.0
                x_delta = pixel_mm
            else:
                # Bidireccional: alternar dirección
                if row % 2 == 0:
                    f.write(f"M5\n")
                    f.write(f"G0 X0 Y{current_y:.4f}\n")
                    scan_pixels = pixels
                    x_start = 0.0
                    x_delta = pixel_mm
                else:
                    f.write(f"M5\n")
                    f.write(f"G0 X{board_w:.4f} Y{current_y:.4f}\n")
                    scan_pixels = reversed(pixels)
                    x_start = board_w
                    x_delta = -pixel_mm

            last_x = x_start
            laser_state = None  # None, True, False

            for i, pixel in enumerate(scan_pixels):
                is_dark = pixel < 128  # threshold: <128 = pista (negro)
                new_state = not is_dark  # no es oscuro → quemar

                if new_state != laser_state:
                    if laser_state is not None:
                        # Terminar segmento actual
                        x_pos = x_start + i * x_delta
                        f.write(f"G1 X{x_pos:.4f} F{feedrate}\n")
                    # Cambiar estado láser
                    if new_state:
                        f.write(f"{laser_on} {power}\n")
                    else:
                        f.write("M5\n")
                    laser_state = new_state

            # Terminar última línea de la fila
            if laser_state:
                f.write(f"G1 X{board_w if direction != 'bidirectional' or row % 2 == 0 else 0:.4f} F{feedrate}\n")
                f.write("M5\n")

            # Siguiente fila
            if direction == "unidirectional":
                current_y -= pixel_mm
            else:
                current_y -= pixel_mm

            if row % 50 == 0 and row > 0:
                print(f"  Fila {row}/{h} ({100*row/h:.0f}%)")

        f.write("M5\n")
        f.write("G0 X0 Y0\n")

    size = gcode_path.stat().st_size
    print(f"  G-code: {size:,} bytes")
    return gcode_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    png_path = Path(sys.argv[1])
    dpi = 250
    feedrate = 1500
    power = "S70"
    laser_on = "M4"
    direction = "unidirectional"

    for arg in sys.argv[2:]:
        if arg.startswith("--dpi="):
            dpi = int(arg.split("=", 1)[1])
        elif arg.startswith("--feedrate="):
            feedrate = int(arg.split("=", 1)[1])
        elif arg.startswith("--power="):
            power = arg.split("=", 1)[1]
        elif arg.startswith("--laser="):
            laser_on = arg.split("=", 1)[1]
        elif arg == "--bidirectional":
            direction = "bidirectional"

    result = png_to_raster_gcode(png_path, dpi, feedrate, power, laser_on, direction)
    print(f"\n✓ Listo: {result}")


if __name__ == "__main__":
    main()
