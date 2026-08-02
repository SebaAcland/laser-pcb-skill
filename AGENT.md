# AGENT.md — Research & Development Notes

## ✅ Validación: raster vs vector (PIC_DFplayer, 2026-08-01)

| Métrica | Raster (PNG viejo) | Vector (SVG nuevo) |
|---|---|---|
| Formato | PNG raster (Inkscape) | SVG vector (KiCad directo) |
| Líneas G-code | 67,515 | **4,679** (×14 menos) |
| Tiempo estimado | 49 min | **~5-8 min** |
| Coincidencia visual | — | **98.7%** |
| Inkscape necesario | Sí | **No** |

Diferencia del 1.3% = pads ensanchados manualmente en el PNG viejo. Para replicar: ajustar ancho de pads en reglas de diseño de KiCad.

## Hardware identificado ✅

### NEJE Master 2S Plus

| Dato | Valor | Fuente |
|---|---|---|
| **Firmware** | GRBL 1.1f (2018-07-15) | `$I` → `[VER:1.1f.20180715:]` |
| **Opciones GRBL** | VML (Variable spindle, Mist coolant, Limit switches) | `$I` → `[OPT:VML,35,254]` |
| **USB-Serial** | CH340 (VID:PID=1a86:7523) | Windows: `usbipd list` |
| **Puerto en WSL** | `/dev/ttyUSB0` | vía usbipd-win v5.3.0 |
| **Área X** | 255 mm | `$130=255.000` |
| **Área Y** | 420 mm | `$131=420.000` |
| **Steps/mm X** | 80 | `$100=80.000` |
| **Steps/mm Y** | 80 | `$101=80.000` |
| **Laser mode** | ACTIVADO | `$32=1` ✅ |
| **PWM range** | 0–1000 | `$30=1000`, `$31=0` |
| **Max rate X** | 10000 mm/min | `$110=10000.000` |
| **Max rate Y** | 10000 mm/min | `$111=10000.000` |
| **Homing** | Habilitado | `$22=1`, `$23=1` |
| **Step pulse** | 10 µs | `$0=10` |
| **Status report** | WPos only | `$10=1` |
| **Soft limits** | Desactivado | `$20=0` |
| **Hard limits** | Desactivado | `$21=0` |

### Pendiente confirmar

- [ ] Potencia del módulo láser (¿7W, 10W, 20W, 30W?)
- [ ] ¿Tiene botón de encendido en el módulo? (algunos NEJE requieren encender el módulo manualmente)
- [ ] ¿La placa controladora es NEJE original o compatible? (algunas usan Arduino Nano + shield)

## Configuración GRBL completa

```
$0=10      (step pulse)
$1=200     (step idle delay)
$2=0       (step invert)
$3=3       (dir invert: X+Y)
$4=0       (step enable invert)
$5=0       (limit pins invert)
$6=0       (probe pin invert)
$10=1      (status report: WPos)
$11=0.010  (junction deviation)
$12=0.002  (arc tolerance)
$13=0      (report inches: mm)
$20=0      (soft limits: off)
$21=0      (hard limits: off)
$22=1      (homing: enabled)
$23=1      (homing dir invert)
$24=100.0  (homing feed)
$25=4000.0 (homing seek)
$26=250    (homing debounce)
$27=1.0    (homing pull-off)
$30=1000   (max spindle speed = PWM max)
$31=0      (min spindle speed)
$32=1      (LASER MODE ✅)
$100=80    (X steps/mm)
$101=80    (Y steps/mm)
$102=80    (Z steps/mm)
$110=10000 (X max rate)
$111=10000 (Y max rate)
$112=4000  (Z max rate)
$120=300   (X accel)
$121=250   (Y accel)
$122=200   (Z accel)
$130=255   (X max travel)
$131=420   (Y max travel)
$132=200   (Z max travel)
```

## Conexión WSL ↔ Láser (comprobado ✅)

```
Windows 11: usbipd-win v5.3.0
  └─ usbipd bind --busid 1-1  (CH340, COM5)
  └─ usbipd attach --wsl --busid 1-1

WSL Debian 12:
  └─ apt install usbip hwdata usbutils
  └─ modprobe usbip_host vhci-hcd ch341
  └─ /dev/ttyUSB0  (chmod 666 o regla udev)
```

## Parámetros de grabado estimados para PCB

Basado en NEJE Master 2S Plus con módulo diode (pendiente confirmar wattage real):

| Parámetro | Pistas | Borde |
|---|---|---|
| **Potencia láser** | S100–S300 | S300–S500 |
| **Feedrate** | 1000–2000 mm/min | 500–1000 mm/min |
| **Pasadas** | 1–2 | 3–5 |
| **DPI SVG** | 96 | 96 |

> ⚠️ Estos valores son estimados. Hacer pruebas en una placa de descarte
> con distintos S y feedrate para encontrar el punto justo donde la
> pintura se quema limpiamente sin dañar el cobre.

## Alternativas evaluadas (ver sección anterior)

[... mantener el resto de la investigación de herramientas ...]

## TODO pendiente

### Fase 1: Confirmar hardware ✅
- [x] Identificar modelo: NEJE Master 2S Plus
- [x] CH340 USB-serial (1a86:7523)
- [x] GRBL 1.1f detectado
- [x] Configuración GRBL extraída (34 settings)
- [x] Área: 255×420mm
- [x] Laser mode: $32=1
- [x] Conexión WSL vía usbipd funcional
- [ ] Confirmar potencia del módulo láser (W)

### Fase 2: Test de grabado
- [ ] Preparar placa de prueba (pintar con aerosol negro)
- [ ] Generar SVG de prueba (pattern de líneas a distintas potencias)
- [ ] Convertir a G-code con svg2gcode
- [ ] Probar M3 SXXX en el láser (sin grabar, solo ver spot)
- [ ] Grabar placa de prueba con patrón de calibración
- [ ] Ajustar potencia/velocidad óptimos

### Fase 3: Software
- [ ] Instalar Rust + svg2gcode-cli
- [ ] Probar export_svg.py con kicad-cli
- [ ] Probar svg_to_gcode.py
- [ ] Test end-to-end con una PCB real

### Fase 4: Skill
- [ ] Ajustar laser_defaults.json con valores reales
- [ ] Integrar con opencode MCP
- [ ] Agregar flag --double-sided para doble faz
