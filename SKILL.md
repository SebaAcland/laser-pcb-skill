# KiCad → Laser PCB Skill

Triggers: "preparar pcb para laser", "exportar pcb laser", "grabar pcb laser",
"laser pcb", "generar gcode pcb", "exportar gcode laser"

## Pipeline

```
KiCad PCB → kicad-cli → SVG → rsvg-convert → PNG raster (250 DPI)
                                                │
                                                ▼
                                     raster_to_gcode.py
                                                │
                                                ▼
                                          G-code raster
                                          (barre toda la placa)
                                                │
                                                ▼
                                     send_gcode.py → /dev/ttyUSB0 → NEJE
```

**Método**: Raster scan — el láser barre línea por línea.
- **Negro** (pista/cobre) → láser OFF (conserva pintura)
- **Blanco** (fondo)    → láser ON  (quema pintura → ácido come cobre)

Resultado idéntico a LaserGRBL + PNG raster, sin Inkscape.

## Uso

```bash
# 1. Exportar SVG + PNG raster desde el .kicad_pcb
python3 ~/laser-pcb-skill/scripts/export_svg.py "C:\Users\...\placa.kicad_pcb"

# 2. PNG → G-code raster
python3 ~/laser-pcb-skill/scripts/raster_to_gcode.py \
  ~/laser-pcb-skill/output/pcb_raster.png

# 3. Enviar al láser
python3 ~/laser-pcb-skill/scripts/send_gcode.py \
  ~/laser-pcb-skill/output/pcb_raster.gcode
```

### Parámetros

| Flag | Default | Descripción |
|---|---|---|
| `--dpi=250` | 250 | Resolución (0.1mm/pixel) |
| `--feedrate=1500` | 1500 | Velocidad mm/min |
| `--power=S70` | S70 | Potencia (7% de 30W) |
| `--bidirectional` | — | Barrido en ambas direcciones |

### Proceso físico

1. Lijar placa de cobre
2. Pintar con aerosol negro mate (capa fina)
3. Alinear en el láser (usar `send_gcode.py pcb_edge.gcode` con baja potencia)
4. Enviar `pcb_raster.gcode` (~20-40 min)
5. Grabar con cloruro férrico
6. Limpiar con CIF + agua
