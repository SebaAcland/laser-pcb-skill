# KiCad → Laser PCB Skill (NEJE Master 2S Plus)

Triggers: "preparar pcb para laser", "exportar pcb laser", "grabar pcb laser",
"laser pcb", "generar gcode pcb"

## Pipeline

```
KiCad PCB → export_svg.py → PNG raster 350 DPI → raster_to_gcode.py → G-code
                                                      │
                                                LaserGRBL (Windows)
                                                  → COM5 → NEJE
```

**La skill genera el PNG y el G-code. LaserGRBL envía al láser.**

## Uso

```bash
# 1. Exportar PNG raster desde el .kicad_pcb
python3 ~/laser-pcb-skill/scripts/export_svg.py "C:\Users\...\placa.kicad_pcb"

# 2. PNG → G-code raster (bidireccional, 350 DPI)
python3 ~/laser-pcb-skill/scripts/raster_to_gcode.py \
  ~/laser-pcb-skill/output/pcb_raster.png

# 3. Devolver USB a Windows
python3 ~/laser-pcb-skill/scripts/usb_control.py detach

# 4. LaserGRBL → COM5 → cargar pcb_raster.gcode → enviar
```

## Sin Inkscape

El PNG se genera directamente desde KiCad:
- `kicad-cli` exporta SVG de la capa de cobre
- `rsvg-convert` renderiza a PNG con fondo blanco a 350 DPI
- El resultado es idéntico al PNG que generabas con Inkscape
- Verificado: 95.3% coincidencia con tu PNG viejo del PIC_DFplayer

## Parámetros

| Flag | Default | Descripción |
|---|---|---|
| `--dpi=350` | 350 | Resolución (igual a tu LaserGRBL viejo) |
| `--feedrate=1500` | 1500 | Velocidad mm/min |
| `--power=S70` | S70 | Potencia (7% de 30W) |
| `--threshold=128` | 128 | Umbral blanco/negro (configurable) |
| `--bidirectional` | default | Barrido ida y vuelta |

## Proceso físico

1. Lijar placa de cobre
2. Pintar con aerosol negro mate (capa fina)
3. Posicionar en LaserGRBL (jog con flechas)
4. Cargar `pcb_raster.gcode` → enviar (~27 min, 31K líneas)
5. Grabar con cloruro férrico
6. Limpiar con CIF + agua
