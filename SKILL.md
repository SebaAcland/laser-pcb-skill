# KiCad → Laser PCB Skill (WSL + Linux Mint)

Triggers: "preparar pcb para laser", "exportar pcb laser", "grabar pcb laser",
"laser pcb", "generar gcode pcb", "exportar gcode laser"

## ⚠ Importante: MCP en WSL

El MCP de KiCad corre del lado WINDOWS (backend SWIG). Al pasar paths
desde WSL (`/mnt/c/Users/...`) el MCP los traduce a `C:\mnt\c\Users\...`
que **NO existe** en el filesystem de Windows. Esto causa que herramientas
como `kicad_export_pcb_svg`, `kicad_open_project`, etc. fallen con errores
de "Board not found" o "Schematic load failed".

**Solución:** esta skill NO usa el MCP para exportar. Usa **kicad-cli.exe**
de la instalación de Windows directamente desde WSL, con paths en formato
Windows (`C:\Users\...`). El script `export_svg.py` maneja esto
automáticamente.

### ¿Cuándo usar el MCP y cuándo no?

| Herramienta | Usar en WSL? | Razón |
|---|---|---|
| `kicad_add_schematic_component` | ✅ Sí | Edita archivos en memoria, paths relativos |
| `kicad_list_schematic_components` | ✅ Sí | Solo lectura, no afecta paths |
| `kicad_batch_add_components` | ✅ Sí | Ídem |
| `kicad_run_erc` | ✅ Sí | Ídem |
| `kicad_export_pcb_svg` | ❌ No | Path absoluto mal traducido |
| `kicad_open_project` | ❌ No | Ídem |
| `export_svg.py` (esta skill) | ✅ Sí | Usa kicad-cli.exe con paths Windows |

---

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

**Desde WSL con KiCad en Windows (ruta Windows-style):**
```bash
python3 ~/laser-pcb-skill/scripts/export_svg.py "C:\Users\Usuario\Documents\...\mi_placa.kicad_pcb"
```

> ⚠ En WSL, pasar el path en formato Windows (`C:\...`). NO usar paths WSL
> (`/mnt/c/...`) porque kicad-cli.exe es un binario de Windows y no entiende
> el filesystem virtual de WSL. Para convertir un path WSL a Windows:
> - WSL: `/mnt/c/Users/Usuario/Desktop/mi_placa.kicad_pcb`
> - Win: `C:\Users\Usuario\Desktop\mi_placa.kicad_pcb`

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
