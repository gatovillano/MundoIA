#!/bin/bash

# Script de preparación para MundoIA Android
# Autor: Antigravity AI

set -e

# Colores para salida
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ROOT_DIR=$(pwd)
FRONTEND_DIR="$ROOT_DIR/frontend"
ANDROID_DIR="$ROOT_DIR/android_app"

echo -e "${BLUE}🚀 Iniciando preparación completa de MundoIA para Android...${NC}"

# 1. Verificar node_modules en Frontend
echo -e "${BLUE}📦 1/4: Verificando dependencias del Frontend...${NC}"
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    npm install
fi

# 2. Construir el Frontend
echo -e "${BLUE}🔨 2/4: Generando build estático (npm run build)...${NC}"
npm run build

if [ ! -d "out" ]; then
    echo -e "${RED}❌ Error: No se encontró la carpeta 'frontend/out' después del build.${NC}"
    exit 1
fi

# 3. Preparar carpeta www en android_app
echo -e "${BLUE}🚚 3/4: Sincronizando archivos con el contenedor Android...${NC}"
if [ ! -d "$ANDROID_DIR" ]; then
    echo -e "${RED}❌ Error: No se encontró la carpeta 'android_app'.${NC}"
    exit 1
fi

rm -rf "$ANDROID_DIR/www/"*
mkdir -p "$ANDROID_DIR/www"
cp -r "out/"* "$ANDROID_DIR/www/"

# 4. Sincronizar Capacitor
echo -e "${BLUE}🔄 4/4: Sincronizando Capacitor Android...${NC}"
cd "$ANDROID_DIR"

# Instalar dependencias si faltan
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing android app dependencies...${NC}"
    npm install
fi

npx cap sync android

echo -e "${GREEN}✅ ¡Sincronización Completada con Éxito!${NC}"
echo -e "${BLUE}--------------------------------------------------${NC}"
echo -e "Para probar en tu dispositivo:"
echo -e " 1. Asegúrate de que el servidor backend esté corriendo en tu PC."
echo -e " 2. Abre el proyecto en Android Studio:"
echo -e "    ${GREEN}cd android_app && npx cap open android${NC}"
echo -e " 3. Usa el botón de configuración (engranaje) en la app"
echo -e "    para poner la IP de tu PC."
echo -e "${BLUE}--------------------------------------------------${NC}"
