# 🌐 MUNDO IA - Simulación Multiagente

Sistema de simulación multiagente con visualización en tiempo real de interacciones sociales, formación de grupos y emergencia de comportamientos complejos.

## ✨ Características

### 🎯 Simulación
- **30 agentes autónomos** con personalidades únicas
- **Memoria basada en grafos** (NetworkX) para recordar interacciones
- **Sistema de necesidades**: alimento, seguridad, socialización
- **Formación dinámica de grupos** sociales
- **Cerebro avanzado** con LangGraph para agentes élite
- **Generación de diálogos** con LLM (LiteLLM)
- **Idioma emergente** con traductor personalizado

### 🎨 Visualización Frontend
- **Red interactiva de agentes** con D3.js
  - Nodos coloreados según nivel de recursos
  - Enlaces según tipo de relación (amigo/enemigo/conocido)
  - Drag & drop para reorganizar la red
  - Zoom y pan para explorar
  
- **Panel de detalles de agente**
  - Recursos y estado actual
  - Personalidad (extroversión, amabilidad, competitividad)
  - Necesidades (alimento, seguridad, social)
  - Relaciones sociales
  - Análisis de comportamiento

- **Gráficos en tiempo real** (Chart.js)
  - Evolución de amistades
  - Evolución de conflictos
  - Formación de grupos

- **Sistema de logs**
  - Logs categorizados (social, conflicto, estado, sistema)
  - Panel minimizable
  - Auto-scroll

- **Controles de simulación**
  - Pausar/Reanudar
  - Control de velocidad (0.5x, 1x, 2x, 4x)

## 🚀 Instalación

### 1. Crear entorno virtual
```bash
cd /home/gato/MundoIA/multiagent_simulation
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Edita el archivo `.env`:
```env
# Configuración de la simulación
NUM_AGENTES=30
PASOS_SIMULACION=100

# API Keys para LLM (opcional)
OPENROUTER_API_KEY=tu_api_key_aqui
MODEL_NAME=openrouter/google/gemini-2.0-flash-exp:free

# TTS (opcional)
TTS_URL=http://localhost:5050/v1/audio/speech
```

## 🎮 Uso

### Iniciar el servidor
```bash
source venv/bin/activate
python3 api.py
```

El servidor se iniciará en `http://localhost:8000`

### Abrir el dashboard
Abre tu navegador en: `http://localhost:8000`

### Interactuar con la visualización
- **Haz clic en un nodo** para ver detalles del agente
- **Arrastra nodos** para reorganizar la red
- **Usa la rueda del mouse** para hacer zoom
- **Haz clic en "Pausar"** para detener la simulación
- **Cambia la velocidad** con el botón de velocidad
- **Minimiza los logs** con el botón "−"

## 📊 Arquitectura

### Backend (Python)
```
api.py              → FastAPI + WebSockets
modelo.py           → Lógica de simulación multiagente
memoria.py          → Sistema de memoria basado en grafos
cerebro_langgraph.py → Razonamiento con LangGraph
cerebro_llm.py      → Generación de diálogos con LLM
traductor.py        → Idioma emergente
herramientas.py     → Herramientas para agentes
```

### Frontend (HTML/JS)
```
index.html          → Dashboard completo
├── D3.js          → Visualización de red
├── Chart.js       → Gráficos en tiempo real
└── WebSockets     → Comunicación en tiempo real
```

## 🎯 Tipos de Interacciones

### 🤝 Cooperación
- Agentes amables comparten recursos
- Fortalece lazos de amistad
- Aumenta la cohesión social

### ⚔️ Conflicto
- Agentes competitivos atacan
- Genera enemistades
- Afecta el rango social

### 💬 Socialización
- Charlas neutrales
- Reduce necesidad social
- Crea conocidos

## 🧬 Personalidad de Agentes

Cada agente tiene tres rasgos (0.0 - 1.0):
- **Extroversión**: Frecuencia de interacciones
- **Amabilidad**: Tendencia a cooperar
- **Competitividad**: Tendencia a competir

## 📈 Métricas Visualizadas

- **Agentes Activos**: Total de agentes en la simulación
- **Paso Actual**: Número de iteración actual
- **Grupos Formados**: Cantidad de grupos sociales
- **Interacciones**: Total de interacciones registradas
- **Evolución temporal**: Gráfico de amigos/enemigos/grupos

## 🎨 Diseño

El frontend usa un diseño **premium y moderno** con:
- Tema oscuro con glassmorphism
- Gradientes vibrantes
- Animaciones fluidas
- Tipografía moderna (Outfit + JetBrains Mono)
- Paleta de colores curada

## 🔧 Personalización

### Cambiar número de agentes
Edita `.env`:
```env
NUM_AGENTES=50
```

### Cambiar duración de simulación
Edita `.env`:
```env
PASOS_SIMULACION=200
```

### Usar tu propio LLM
Edita `.env` y configura tu API key:
```env
OPENROUTER_API_KEY=sk-or-v1-...
MODEL_NAME=openrouter/anthropic/claude-3.5-sonnet
```

## 🐛 Solución de Problemas

### El servidor no inicia
```bash
# Verifica que las dependencias estén instaladas
pip install -r requirements.txt

# Verifica que el puerto 8000 esté libre
lsof -i :8000
```

### Los logs no aparecen
- Verifica la consola del navegador (F12)
- Asegúrate de que WebSocket esté conectado (badge verde)

### La red no se visualiza
- Actualiza la página
- Verifica que D3.js se haya cargado correctamente

## 📝 Licencia

MIT License - Proyecto educativo de simulación multiagente

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Este proyecto es parte de MundoIA.

---

**Desarrollado con ❤️ usando FastAPI, D3.js, Chart.js y LangGraph**
