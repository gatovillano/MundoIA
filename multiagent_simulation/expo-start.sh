#!/bin/bash

# Script para iniciar el entorno de desarrollo Expo para MundoIA
# Autor: Antigravity AI

set -e

# Colores para salida
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ROOT_DIR=$(pwd)
EXPO_DIR="$ROOT_DIR/android_app/android_expo"
FRONTEND_PORT=3005

echo -e "${BLUE}🚀 Iniciando MundoIA Mobile Native (Expo)...${NC}"

# 1. Información del Backend
echo -e "${BLUE}🔍 Nota: La App Nativa se conecta directamente al Backend (puerto 8005).${NC}"
echo -e "${BLUE}Asegúrate de que tu servidor Python esté corriendo.${NC}"

# 2. Iniciar Expo
echo -e "${BLUE}📱 Iniciando servidor Expo...${NC}"
cd "$EXPO_DIR"

# Instalar dependencias si faltan
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Instalando dependencias de Expo...${NC}"
    npm install
fi

echo -e "${GREEN}--------------------------------------------------${NC}"
echo -e "Instrucciones:"
echo -e " 1. Escanea el código QR con la app ${BLUE}Expo Go${NC} en tu teléfono."
echo -e " 2. Asegúrate de que tu PC y tu teléfono estén en la ${BLUE}misma red Wi-Fi${NC}."
echo -e " 3. El WebView se conectará automáticamente a tu IP local."
echo -e "${GREEN}--------------------------------------------------${NC}"

npx expo start --clear
