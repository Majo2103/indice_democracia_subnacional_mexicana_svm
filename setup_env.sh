#!/bin/bash
# setup_env.sh
# Crea el virtual environment e instala dependencias desde requirements.txt
# Uso: bash setup_env.sh

set -e

echo "============================================"
echo "  Setup: Tesis Electoral — Entorno Python"
echo "============================================"

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 no encontrado. Instálalo desde https://python.org"
    exit 1
fi
echo "✓ $(python3 --version) encontrado"

# Verificar que requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "✗ No se encontró requirements.txt en esta carpeta."
    exit 1
fi
echo "✓ requirements.txt encontrado"

# Crear el virtual environment
if [ -d "venv" ]; then
    echo "⚠  La carpeta ./venv ya existe. Saltando creación."
else
    echo ""
    echo "[1] Creando virtual environment en ./venv ..."
    python3 -m venv venv
    echo "✓ Virtual environment creado"
fi

# Activar
echo ""
echo "[2] Activando entorno ..."
source venv/bin/activate

# Actualizar pip
echo ""
echo "[3] Actualizando pip ..."
pip install --upgrade pip --quiet

# Instalar desde requirements.txt
echo ""
echo "[4] Instalando dependencias desde requirements.txt ..."
pip install -r requirements.txt --quiet
echo "✓ Dependencias instaladas"

# Registrar kernel en Jupyter
echo ""
echo "[5] Registrando kernel en Jupyter ..."
python -m ipykernel install --user --name tesis_electoral --display-name "Tesis Electoral"
echo "✓ Kernel registrado como 'Tesis Electoral'"

echo ""
echo "============================================"
echo "  ¡Listo! Para activar el entorno:"
echo "    source venv/bin/activate"
echo ""
echo "  Para abrir Jupyter:"
echo "    jupyter notebook"
echo ""
echo "  Para desactivar:"
echo "    deactivate"
echo ""
echo "  Si agregas un paquete nuevo, actualiza"
echo "  requirements.txt con:"
echo "    pip freeze > requirements.txt"
echo "============================================"
