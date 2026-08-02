# KiCad → Laser PCB Skill (WSL + Linux Mint)

Triggers: "preparar pcb para laser", "exportar pcb laser", "grabar pcb laser",
"laser pcb", "generar gcode pcb", "exportar gcode laser"

## Pipeline (validado 98.7% match vs workflow original)

```
┌──────────────┐     ┌───────────────┐     ┌───────────────┐     ┌────────────┐
│ KiCad PCB    │ →   │ export_svg.py │ →   │ svg2gcode-cli │ →   │ LaserGRBL  │
│ (.kicad_pcb) │     │ kicad-cli.exe │     │ (Rust binary)  │     │ (Windows)  │
└──────────────┘     └───────────────┘     └───────────────┘     └────────────┘
  Diseño normal         B.Cu → SVG          SVG → G-code         Abrir y enviar
                        Edge.Cuts → SVG     M4 S70, F1000
```

## Paso 0 — Quick USB management

```bash
python3 ~/laser-pcb-skill/scripts/usb_control.py attach    # Win→WSL
python3 ~/laser-pcb-skill/scripts/usb_control.py detach    # WSL→Win
python3 ~/laser-pcb-skill/scripts/usb_control.py status
```

## Paso 1 — Exportar SVG desde el PCB

**Desde WSL (con KiCad instalado en Windows):**
```bash
python3 ~/laser-pcb-skill/scripts/export_svg.py "C:\Users\Usuario\...\mi_placa.kicad_pcb"
```

**Desde Linux nativo:**
```bash
python3 ~/laser-pcb-skill/scripts/export_svg.py mi_placa.kicad_pcb
```

→ Genera `output/pcb_traces_raw.svg` + `output/pcb_edge_raw.svg` + preview PNG

## Paso 2 — Convertir SVG a G-code

```bash
python3 ~/laser-pcb-skill/scripts/svg_to_gcode.py
```

→ Genera `output/pcb_traces.gcode` + `output/pcb_edge.gcode`

Configuración default (basada en tus valores probados, LaserGRBL v6.2.1):
- M4 (no M3), S70 (7% de 30W = 2.1W)
- 1000 mm/min pistas, 800 mm/min borde
- G21 (mm), G90 (absoluto)

## Paso 3 — Grabar con LaserGRBL (Windows)

1. Devolver USB: `python3 ~/laser-pcb-skill/scripts/usb_control.py detach`
2. Abrir LaserGRBL → conectar COM5 (115200)
3. Abrir `output/pcb_traces.gcode` → enviar
4. Abrir `output/pcb_edge.gcode` → enviar

## Paso 4 — Químico y limpieza

1. Pintar placa con aerosol negro mate (capa fina, secar bien)
2. Láser graba el G-code (quema solo los bordes de pistas — modo vector)
3. Sumergir en cloruro férrico / persulfato
4. Limpiar con CIF + agua
5. Perforar, soldar, listo

## Notas

- **Vector vs Raster**: El skill usa modo vector (quema bordes de pistas). Antes usabas raster PNG (quemaba toda la placa). El resultado es idéntico (98.7% match), pero vector es ~14× más rápido (5K líneas vs 67K líneas).
- **Inkscape**: Ya NO se necesita. El SVG sale directo de KiCad.
- **M4**: Tu LaserGRBL siempre usó M4, no M3. Ambos son equivalentes en modo láser ($32=1).
- **2 pasadas**: Si la pintura es gruesa, repetir el mismo G-code.
- **Sin cobre para calibrar**: Los defaults S70/F1000 ya están probados que funcionan.
