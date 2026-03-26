#!/bin/bash

# Este script prepara la versión de Android desde el frontend

FRONTEND_DIR="$(pwd)/frontend"
ANDROID_DIR="$(pwd)/android_app"

echo "🚀 Preparando la versión de Android..."

# 1. Construir el Frontend
echo "📦 1/3: Compilando el código visual (Frontend)..."
cd "$FRONTEND_DIR" || exit
npm run build

# 2. Verificar que el build existe
if [ ! -d "out" ]; then
    echo "❌ Error: No se encontraron los archivos generados en 'frontend/out'."
    exit 1
fi

# 3. Limpiar y Copiar archivos al contenedor de Android
echo "🚚 2/3: Pasando los archivos a la carpeta 'android_app'..."
rm -rf "$ANDROID_DIR/www/"*
mkdir -p "$ANDROID_DIR/www"
cp -r "$FRONTEND_DIR/out/"* "$ANDROID_DIR/www/"

# 4. Sincronizar Capacitor
echo "🔄 3/3: Sincronizando el contenedor nativo de Android..."
cd "$ANDROID_DIR" || exit
npx cap sync android

echo "✅ ¡Listo! Todo está sincronizado."
echo "Puedes abrir el proyecto en Android Studio con:"
echo "   cd android_app && npx cap open android"
