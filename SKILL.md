# KiCad → Laser PCB Skill (NEJE Master 2S Plus)

Triggers: "preparar pcb para laser", "exportar pcb laser", "grabar pcb laser",
"laser pcb", "generar gcode pcb", "exportar gcode laser"

## Sistema de Coordenadas

```
┌─────────────────────────────────────────┐
│                                         │
│  (0,420) ← Homing (fondo-izquierda)     │
│                                         │
│         Área: 255×420mm                 │
│                                         │
│  (0,0) ← Frente-izquierda               │
│                                         │
│  Y+ = atrás (alejándose)                │
│  Y- = adelante (hacia usuario)          │
│  X+ = derecha                           │
│  X- = izquierda                         │
└─────────────────────────────────────────┘
```

## Pipeline (3 comandos)

```bash
# 1. Exportar SVG + PNG raster
python3 ~/laser-pcb-skill/scripts/export_svg.py "C:\Users\...\pcb.kicad_pcb"

# 2. PNG → G-code raster (Y invertido por defecto)
python3 ~/laser-pcb-skill/scripts/raster_to_gcode.py \
  ~/laser-pcb-skill/output/pcb_raster.png

# 3. Posicionar láser y dibujar marco
python3 ~/laser-pcb-skill/scripts/position_laser.py --back

# 4. Enviar al láser (valida límites automáticamente)
python3 ~/laser-pcb-skill/scripts/send_gcode.py \
  ~/laser-pcb-skill/output/pcb_raster.gcode
```

## Configuración GRBL

```
$3=3     (ambos ejes invertidos - necesario para homing)
$22=1    (homing habilitado)
$23=1    (X homes negative, Y homes positive)
$25=2000 (homing seek speed - bajado de 4000)
$120=150 (X acceleration - bajado de 300)
$121=150 (Y acceleration - bajado de 250)
$30=1000 (PWM max)
$32=1    (laser mode)
$130=255 (X max travel)
$131=420 (Y max travel)
```

## Flujo de Trabajo Seguro

### Opción A: Placa al fondo (recomendado)

```bash
# 1. Homing + mover al fondo + marco
python3 position_laser.py --back

# 2. Poner placa dentro del marco

# 3. Enviar raster (ya tiene --flip-y por defecto)
python3 send_gcode.py output/pcb_raster.gcode
```

### Opción B: Placa al frente

```bash
# 1. Homing + mover al frente + marco
python3 position_laser.py --front

# 2. Poner placa dentro del marco

# 3. Enviar raster
python3 send_gcode.py output/pcb_raster.gcode
```

## Parámetros

| Flag | Default | Descripción |
|---|---|---|
| `--dpi=250` | 250 | Resolución (0.1mm/pixel) |
| `--feedrate=1500` | 1500 | Velocidad mm/min |
| `--power=S70` | S70 | Potencia (7% de 30W) |
| `--laser=M4` | M4 | Comando láser ON |
| `--bidirectional` | — | Barrido en ambas direcciones |
| `--no-flip-y` | — | NO invertir Y (solo si Y está correcta) |

## Validación de Límites

El `send_gcode.py` valida automáticamente:
- X: 0-255mm
- Y: 0-420mm

Si hay coordenadas fuera de rango, **no envía nada** y muestra error.

## Troubleshooting

### "Se disparó" durante homing

**Causa**: `$25=4000` es muy rápido (66mm/s)
**Solución**: `$25=2000` (ya aplicado)

### "Y está invertida"

**Causa**: La máquina tiene Y+ hacia atrás
**Solución**: `--flip-y` ya es default en `raster_to_gcode.py`

### "No se mueve"

**Causa**: GRBL en estado Alarm
**Solución**: `$X` para desbloquear

### "Homing no funciona"

**Causa**: `$3` incorrecto
**Solución**: `$3=3` (ambos ejes invertidos)

### "Coordenadas fuera de rango"

**Causa**: PCB muy grande o `--flip-y` no usado
**Solución**: Reducir DPI o usar `--flip-y`

## Scripts

| Script | Función |
|---|---|
| `export_svg.py` | KiCad → SVG + PNG raster |
| `raster_to_gcode.py` | PNG → G-code raster (Y invertido) |
| `position_laser.py` | Homing + posicionamiento + marco |
| `send_gcode.py` | Enviar G-code (valida límites) |
| `neje_check.py` | Diagnóstico completo |
| `usb_control.py` | Attach/detach USB desde WSL |

## Proceso Físico

1. Lijar placa de cobre
2. Pintar con aerosol negro mate (capa fina)
3. Alinear en el láser (usar `position_laser.py`)
4. Enviar `pcb_raster.gcode` (~20-40 min)
5. Grabar con cloruro férrico
6. Limpiar con CIF + agua
