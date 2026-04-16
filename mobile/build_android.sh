#!/bin/bash

# Configuration
FRONTEND_DIR="/home/gato/Proyectos/MundoIA/multiagent_simulation/frontend"
ANDROID_DIR="/home/gato/Proyectos/MundoIA/multiagent_simulation/android_app"

echo "🚀 Building MundoIA for Android..."

# 1. Build Frontend
echo "📦 Building Frontend (Static Export)..."
cd "$FRONTEND_DIR" || exit
npm run build

# 2. Check if build succeeded
if [ ! -d "out" ]; then
    echo "❌ Error: Frontend build failed (out/ directory not found)."
    exit 1
fi

# 3. Transfer Build to Android project
echo "🚚 Syncing build with Android project..."
rm -rf "$ANDROID_DIR/www"
mkdir -p "$ANDROID_DIR/www"
cp -r "out/"* "$ANDROID_DIR/www/"

# 4. Sync Capacitor
echo "🔄 Synchronizing Capacitor..."
cd "$ANDROID_DIR" || exit
npx cap sync android

echo "✅ Ready! You can now open the project in Android Studio:"
echo "   cd $ANDROID_DIR && npx cap open android"
