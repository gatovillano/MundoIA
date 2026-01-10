#!/bin/bash

# Script de inicio rápido para MUNDO IA - Simulación Multiagente

echo "🌐 MUNDO IA - Simulación Multiagente"
echo "===================================="
echo ""

# Activar entorno virtual
if [ -d "venv" ]; then
    echo "✅ Activando entorno virtual..."
    source venv/bin/activate
else
    echo "❌ No se encontró el entorno virtual."
    echo "   Ejecuta: python3 -m venv venv"
    echo "   Luego: source venv/bin/activate"
    echo "   Y finalmente: pip install -r requirements.txt"
    exit 1
fi

# Verificar que las dependencias estén instaladas
echo "🔍 Verificando dependencias..."
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Instalando dependencias..."
    pip install -r requirements.txt
fi

echo ""
echo "🚀 Iniciando servidor en http://localhost:8000"
echo "   Presiona Ctrl+C para detener"
echo ""
echo "📊 Abre tu navegador en: http://localhost:8000"
echo ""

# Iniciar servidor
python3 api.py
