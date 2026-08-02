# KiCad → Laser PCB Skill (WSL + Linux Mint)

Triggers: "preparar pcb para laser", "exportar pcb laser", "grabar pcb laser",
"laser pcb", "generar gcode pcb", "exportar gcode laser"

## Método: Raster scan (PNG)

El láser barre toda la placa línea por línea:
- **Negro** (pista/cobre) → láser **OFF** (conserva pintura → cobre intacto)
- **Blanco** (fondo)    → láser **ON**  (quema pintura → ácido come cobre)

→ Resultado idéntico a tu workflow viejo de LaserGRBL + Inkscape PNG

### Pipeline (2 comandos)

```bash
# 1. Exportar SVG + PNG raster
python3 ~/laser-pcb-skill/scripts/export_svg.py "C:\Users\...\pcb.kicad_pcb"

# 2. PNG → G-code raster
python3 ~/laser-pcb-skill/scripts/raster_to_gcode.py ~/laser-pcb-skill/output/pcb_raster.png

# 3. Enviar al láser (opcional)
python3 ~/laser-pcb-skill/scripts/send_gcode.py ~/laser-pcb-skill/output/pcb_raster.gcode
```

### Parámetros raster

| Parámetro | Default | Descripción |
|---|---|---|
| `--dpi` | 250 | Resolución (250 = 0.1mm/pixel) |
| `--feedrate` | 1500 | Velocidad mm/min |
| `--power` | S70 | Potencia láser (7% de 30W) |
| `--laser` | M4 | Comando láser ON |
| `--bidirectional` | — | Barrido bidireccional (más rápido) |

### Tiempo estimado

PCB de ~60×48mm a 250 DPI → ~40-50 min (similar a tu workflow viejo con LaserGRBL)
