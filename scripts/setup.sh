#!/usr/bin/env bash
# setup.sh — Instalación one-shot para KiCad → Laser PCB
# Funciona en WSL (Ubuntu) y Linux Mint
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[✗]${NC} $*"; }
header(){ echo -e "\n${YELLOW}── $* ──${NC}"; }

# ─── Detectar entorno ───
if grep -qi microsoft /proc/version 2>/dev/null || grep -qi wsl /proc/version 2>/dev/null; then
    IS_WSL=true
    info "Entorno detectado: WSL"
else
    IS_WSL=false
    info "Entorno detectado: Linux nativo"
fi

# ─── Paquetes del sistema ───
header "Paquetes del sistema"
sudo apt update -qq
sudo apt install -y python3 python3-pip python3-venv usbutils udev curl

# kicad-cli (viene con KiCad; si no está, instalar)
if ! command -v kicad-cli &>/dev/null; then
    warn "kicad-cli no encontrado, instalando..."
    sudo apt install -y kicad-cli || warn "kicad-cli no disponible en este repo"
fi
info "kicad-cli: $(command -v kicad-cli || echo 'no encontrado')"

# ─── Rust + svg2gcode ───
header "Rust + svg2gcode"
if ! command -v cargo &>/dev/null; then
    info "Instalando Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi
if command -v svg2gcode-cli &>/dev/null; then
    info "svg2gcode-cli ya instalado"
else
    info "Instalando svg2gcode-cli..."
    cargo install svg2gcode-cli
fi

# ─── Python deps ───
header "Python dependencies"
pip install --quiet pyserial cairosvg 2>/dev/null || pip3 install --quiet pyserial cairosvg
info "Python deps OK"

# ─── bCNC (opcional) ───
header "bCNC (sender GRBL, opcional)"
if python3 -c "import bCNC" 2>/dev/null; then
    info "bCNC ya instalado"
else
    warn "bCNC no instalado. Instalar con: pip install bCNC"
fi

# ─── WSL: usbipd ───
if $IS_WSL; then
    header "WSL: herramientas USB/IP"
    sudo apt install -y linux-tools-generic linux-tools-$(uname -r) hwdata 2>/dev/null || true
    sudo update-alternatives --install /usr/local/bin/usbip usbip \
        /usr/lib/linux-tools/$(uname -r)/usbip 20 2>/dev/null || true

    header "WSL: reglas udev para CH340/CP2102/FT232"
    RULES=/etc/udev/rules.d/99-laser-pcb.rules
    if [ ! -f "$RULES" ]; then
        sudo tee "$RULES" > /dev/null <<'UDEV'
# CH340/CH341
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666"
# CP2102
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666"
# FT232
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666"
# ATmega16U2
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", MODE="0666"
UDEV
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        info "Reglas udev instaladas"
    else
        info "Reglas udev ya existen"
    fi

    echo ""
    warn "Falta instalar en WINDOWS (PowerShell Admin):"
    echo "    winget install usbipd"
    echo ""
    echo "  Para pasar el láser a WSL:"
    echo "    usbipd wsl list"
    echo "    usbipd wsl attach --busid <BUS_ID>"
fi

# ─── Verificar ───
header "Verificación"
python3 "${HOME}/laser-pcb-skill/scripts/env_check.py" || warn "env_check.py no disponible aún"

echo ""
info "Instalación completa. Reiniciá WSL si agregaste reglas udev."
echo "  Para testear: python3 ~/laser-pcb-skill/scripts/env_check.py"
