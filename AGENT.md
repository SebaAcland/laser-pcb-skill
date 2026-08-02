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
| **Origin** | Front Left en NEJE/LightBurn, Back Left en GRBL directo |

## GRBL Config

```
$3=3  (X+Y invert)  $130=255  $131=420
$30=1000 (PWM max)  $32=1   (laser mode)
$100=80  $101=80    (steps/mm)
$22=1   $23=1       (homing)
$20=0               (soft limits off para enviar)
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

## Pipeline validado

```
KiCad → kicad-cli.exe (Windows) → SVG
  → rsvg-convert → PNG 250 DPI
  → raster_to_gcode.py → G-code (barre toda la placa)
  → send_gcode.py → /dev/ttyUSB0 → NEJE
```

Probado: PIC_DFplayer 60×48mm → PNG 591×473px → 4,014 líneas G-code → ~19 min

## Config LaserGRBL vieja (referencia)

Extraído de LaserGRBL.Settings.bin v6.2.1:
- PowerMax: 70/1000 (7%), M4
- Speed: 1000 mm/min
- Unidirectional ON
- 0 errores en múltiples trabajos de PCB

## Lecciones aprendidas

- **Raster sí, vector no** para etching químico. El vector solo traza bordes y el ácido no alcanza.
- **Sin homing**: usar $X (unlock) + G92/G10 para cero de trabajo. Evitar $H.
- **$3=3** es el valor correcto. Cambiarlo a 1 rompe el homing y causa ruido/rebote.
- **Y-down de SVG** vs **Y-up de GRBL**: rsvg-convert resuelve esto automáticamente en el PNG.
