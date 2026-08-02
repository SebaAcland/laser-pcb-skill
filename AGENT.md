# AGENT.md — NEJE Master 2S Plus + PCB Laser

## Hardware ✅

| Dato | Valor |
|---|---|
| **Modelo** | NEJE Master 2S Plus |
| **Firmware** | GRBL 1.1f (2018-07-15) |
| **Láser** | 30W óptico diode |
| **Área** | 255mm × 420mm |
| **USB** | CH340 (1a86:7523) → /dev/ttyUSB0 vía usbipd |
| **Laser mode** | $32=1 (M4 PWM, S0-S1000) |
| **Homing** | $3=3, $23=1 → back-left (0,420) |
| **Finales de carrera** | Fondo (Y=420) e izquierda (X=0) |

## Sistema de Coordenadas (según NEJE oficial + diagrama del usuario)

```
       (0,420) ← Homing y límites de carrera
          ●
    ┌─────┴────────────────────┐
    │                          │
    │     NEJE 2S Plus         │
    │     255 × 420 mm         │
    │                          │
    │                          │
    │                          │  X →
    │                          │  (eje corto, 255mm)
    │                          │
    └──────────────────────────┘
    (0,0)          Y ↓        vos (YO)
  Front-Left    (eje largo,
                  420mm,
                hacia adelante)

• Fuente: GRBL_Homing.pdf (documento oficial NEJE)
• Homing ($H): va a (0,420) = Rear Left
• (0,0) = Front Left (cerca del usuario)
• X = eje CORTO (255mm) → derecha (X+)
• Y = eje LARGO (420mm) 
  - Y+ = hacia ATRÁS (alejándose del usuario, de 0→420)
  - Y- = hacia ADELANTE (hacia el usuario, de 420→0)
• Switches de final de carrera: en Rear Left (fondo-izquierda)

Importante para el G-code:
• Con G92 X0 Y0 fijado en el fondo (después de $H):
  - G-code Y=0 = máquina Y=420 (Rear, en los switches)
  - G-code Y=-48 = máquina Y=372 (48mm hacia adelante, dentro de límites)
  - El raster SIEMPRE usa Y negativo (hacia adelante) desde el fondo
"""

## GRBL Config

```
$3=3    (X+Y invert)  $130=255  $131=420
$30=1000 (PWM max)    $32=1     (laser mode)
$100=80  $101=80      (steps/mm)
$22=1    $23=1        (homing)
$25=2000              (homing speed - bajado de 4000)
$120=150 $121=150     (acceleration - bajados)
$20=0                 (soft limits off para enviar)
```

## WSL → Láser

```
usbipd-win 5.3.0 en Windows:
  usbipd bind --busid 1-1        (persistente)
  usbipd attach --wsl --busid 1-1 (cada vez que abrís WSL)

En WSL:
  modprobe ch341 usbip_host vhci-hcd
  /dev/ttyUSB0 (chmod 666)
```

## Pipeline Validado

```
KiCad → kicad-cli.exe (Windows) → SVG
  → rsvg-convert --background-color white → PNG 250 DPI
  → raster_to_gcode.py --flip-y (default) → G-code raster
  → send_gcode.py (valida límites) → /dev/ttyUSB0 → NEJE
```

Probado: PIC_DFplayer 60×48mm → PNG 591×473px → 22,648 líneas G-code → ~19 min

## LECCIONES APRENDIDAS

### Homing
- `$3=3` es **OBLIGATORIO** (ambos ejes invertidos)
- `$3=1` rompe el homing (Y no encuentra el tope)
- Homing siempre va a (0,420) = fondo-izquierda
- **NUNCA** hacer `$H` después de `G92` (pierde el origen manual)
- `$25=4000` es muy rápido → causa "disparo" → usar `$25=2000`

### Dirección Y
- Y+ va **ATRÁS** (alejándose del usuario)
- Y- va **ADELANTE** (hacia el usuario)
- El raster **DEBE** usar `--flip-y` (ahora es default)
- Sin `--flip-y`, el láser barre en dirección incorrecta

### Raster vs Vector
- **Raster SÍ** para etching químico (barre toda la placa)
- **Vector NO** para etching (solo traza bordes, ácido no alcanza)
- Raster: 22K líneas, 19 min
- Vector: 4K líneas, 5 min (pero no funciona para PCB)

### PNG Export
- SVG de KiCad tiene fondo transparente
- `rsvg-convert` necesita `--background-color white`
- Sin fondo blanco, todo el PNG es oscuro → no quema nada

### Láser
- M4 S70 = 7% de 30W = 2.1W (correcto para pintura negra)
- M3 y M4 son equivalentes en modo láser ($32=1)
- Nunca enviar M3/M4 sin verificar posición primero

### Seguridad
- `send_gcode.py` valida límites (0-255 X, 0-420 Y)
- Si hay coordenadas fuera de rango, **no envía nada**
- Siempre hacer marco de referencia antes de grabar
- Usar potencia baja (S15) para el marco

## Config LaserGRBL Vieja (Referencia)

Extraído de LaserGRBL.Settings.bin v6.2.1:
- PowerMax: 70/1000 (7%), M4
- Speed: 1000 mm/min
- Unidirectional: ON
- Jog Speed: 7694 mm/min
- Jog Step: 1mm
- 0 errores en múltiples trabajos de PCB
