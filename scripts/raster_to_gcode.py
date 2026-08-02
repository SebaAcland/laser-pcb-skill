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
                        direction: str = "unidirectional",
                        flip_y: bool = True) -> Path:
    """Convierte PNG a G-code raster. Retorna path del archivo generado.
    
    flip_y: niega el eje Y en el G-code (default True para NEJE con Y invertida).
    """
    img = Image.open(png_path).convert("L")
    w, h = img.size

    pixel_mm = 25.4 / dpi
    board_w = w * pixel_mm
    board_h = h * pixel_mm

    # Validación de límites
    if board_w > 255 or board_h > 420:
        print(f"⚠ ADVERTENCIA: PCB {board_w:.1f}×{board_h:.1f}mm excede área 255×420mm")
        print(f"   Reducir DPI o recortar imagen")
        sys.exit(1)

    def machine_y(y: float) -> float:
        """Convierte coordenada Y del PNG a coordenada Y de la máquina.
        
        Con G92 X0 Y0 fijado en el fondo (machine Y=420 después del homing):
        - PNG Y=0 (arriba) → G-code Y=-(board_h) → máquina Y=420-board_h ✓
        - PNG Y=board_h (abajo) → G-code Y=0 → máquina Y=420 ✓
        
        Y negativo = hacia adelante (FRONT), dentro de límites.
        """
        if flip_y:
            return y - board_h  # negativo, va de -board_h a 0
        else:
            return y

    print(f"PNG: {w}×{h}px @ {dpi} DPI = {board_w:.1f}×{board_h:.1f}mm")
    if flip_y:
        print(f"Y invertido (negado) para máquina con Y+ = atrás")
    print(f"Filas: {h}, Pasos por fila: {w}")
    print(f"Tiempo est: {h * board_w / feedrate * 60:.0f}s (~{h * board_w / feedrate:.1f} min)")

    gcode_path = OUTPUT_DIR / "pcb_raster.gcode"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(gcode_path, "w") as f:
        f.write("G21 ; mm\n")
        f.write("G90 ; absolute\n")
        f.write("G0 X0 Y0\n")
        f.write("M5\n\n")

        for row in range(h):
            pixels = [img.getpixel((x, row)) for x in range(w)]

            y_machine = machine_y(row * pixel_mm)

            if direction == "bidirectional" and row % 2 == 1:
                # Barrido de derecha a izquierda
                f.write("M5\n")
                f.write(f"G0 X{board_w:.4f} Y{y_machine:.4f}\n")
                scan_pixels = list(reversed(pixels))
                x_start = board_w
                x_delta = -pixel_mm
            else:
                # Barrido de izquierda a derecha
                f.write("M5\n")
                f.write(f"G0 X0 Y{y_machine:.4f}\n")
                scan_pixels = pixels
                x_start = 0.0
                x_delta = pixel_mm

            laser_state = None

            for i, pixel in enumerate(scan_pixels):
                is_dark = pixel < 128
                new_state = not is_dark

                if new_state != laser_state:
                    if laser_state is not None:
                        x_pos = x_start + i * x_delta
                        f.write(f"G1 X{x_pos:.4f} F{feedrate}\n")
                    if new_state:
                        f.write(f"{laser_on} {power}\n")
                    else:
                        f.write("M5\n")
                    laser_state = new_state

            if laser_state:
                end_x = 0.0 if (direction == "bidirectional" and row % 2 == 1) else board_w
                f.write(f"G1 X{end_x:.4f} F{feedrate}\n")
            f.write("M5\n")

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
    flip_y = True  # Default True para NEJE

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
        elif arg == "--no-flip-y":
            flip_y = False

    result = png_to_raster_gcode(png_path, dpi, feedrate, power, laser_on, direction, flip_y)
    print(f"\n✓ Listo: {result}")


if __name__ == "__main__":
    main()
