#!/usr/bin/env bash
# setup.sh — Crea el entorno virtual e instala las dependencias de ACAB-Configurator
# Uso:  bash setup.sh [ruta_venv]
# Por defecto el entorno se crea en $HOME/acab-venv

set -euo pipefail

VENV_PATH="${1:-$HOME/acab-venv}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "=== ACAB-Configurator — Configuración del entorno (Linux) ==="
echo "  Directorio del proyecto : $PROJECT_DIR"
echo "  Entorno virtual         : $VENV_PATH"
echo ""

# ── 1. Verificar Python 3 ────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 no encontrado. Instálalo con tu gestor de paquetes:"
    echo "  sudo apt install python3 python3-venv   # Debian/Ubuntu"
    echo "  sudo dnf install python3                # Fedora/RHEL"
    exit 1
fi
echo "[1/3] Python detectado: $(python3 --version)"

# ── 2. Crear entorno virtual ─────────────────────────────────────────────────
if [ -f "$VENV_PATH/bin/python" ]; then
    echo "[2/3] El entorno virtual ya existe en '$VENV_PATH', se omite la creación."
else
    echo "[2/3] Creando entorno virtual en '$VENV_PATH'..."
    python3 -m venv "$VENV_PATH"
fi

# ── 3. Instalar dependencias ─────────────────────────────────────────────────
echo "[3/3] Instalando dependencias desde requirements.txt..."
"$VENV_PATH/bin/pip" install --upgrade pip --quiet
"$VENV_PATH/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# ── Resumen ──────────────────────────────────────────────────────────────────
echo ""
echo "=== Entorno listo. Para arrancar la aplicación: ==="
echo "  '$VENV_PATH/bin/python' '$PROJECT_DIR/app.py'"
echo ""
