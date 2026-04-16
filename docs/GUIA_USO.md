# 🎯 Guía de Uso - MUNDO IA Dashboard

## 🖥️ Interfaz Principal

El dashboard está dividido en 4 secciones principales:

### 1. 🕸️ Red de Agentes (Izquierda, Grande)

La visualización principal muestra todos los agentes como nodos conectados.

**Colores de los nodos:**

- 🟢 Verde: Agente con muchos recursos (>80)
- 🟡 Amarillo: Recursos moderados (50-80)
- 🟠 Naranja: Recursos bajos (30-50)
- 🔴 Rojo: Recursos críticos (<30)

**Tipos de enlaces:**

- Verde: Relación de amistad
- Rojo: Relación de enemistad
- Gris: Conocidos

**Interacciones:**

- **Clic en nodo**: Abre panel de detalles
- **Arrastrar nodo**: Reorganiza la red
- **Rueda del mouse**: Zoom in/out
- **Arrastrar fondo**: Pan (mover vista)

### 2. 📊 Panel de Estadísticas (Derecha, Arriba)

Muestra métricas en tiempo real:

- **Agentes Activos**: Total de agentes en la simulación
- **Paso Actual**: Iteración actual de la simulación
- **Grupos Formados**: Cantidad de grupos sociales establecidos
- **Interacciones**: Total de interacciones registradas

### 3. 📈 Gráficos (Derecha, Abajo)

Visualización temporal de:

- Línea verde: Evolución de amistades
- Línea roja: Evolución de enemistades
- Línea morada: Formación de grupos

### 4. 📝 Panel de Logs (Abajo, Izquierda)

Muestra eventos en tiempo real:

**Categorías de logs:**

- 🔵 Azul: Interacciones sociales
- 🔴 Rojo: Conflictos y ataques
- 🟢 Verde: Cambios de estado
- 🟡 Amarillo: Eventos del sistema

**Controles:**

- Botón `−`: Minimizar panel
- Auto-scroll: Sigue automáticamente los nuevos logs

## 🎮 Controles de Simulación

### ⏸️ Pausar/Reanudar

- Detiene temporalmente la simulación
- Los datos actuales se mantienen
- Útil para analizar un momento específico

### ⚡ Control de Velocidad

Cicla entre diferentes velocidades:

- 0.5x: Más lento (mejor para análisis detallado)
- 1x: Velocidad normal
- 2x: Doble velocidad
- 4x: Cuádruple velocidad

## 👤 Panel de Detalles de Agente

Al hacer clic en un nodo, se abre un panel lateral con:

### 🤖 Información Básica

- ID del agente
- Recursos actuales
- Grupo al que pertenece
- Rango social

### 🧬 Personalidad

Tres rasgos visualizados con barras:

- **Extroversión**: Qué tan sociable es
- **Amabilidad**: Tendencia a cooperar
- **Competitividad**: Tendencia a competir

### 💭 Necesidades

Niveles actuales (0-10):

- 🍎 **Alimento**: Necesidad de recursos
- 🛡️ **Seguridad**: Necesidad de protección
- 👥 **Social**: Necesidad de interacción

### 📊 Relaciones

Conteo de:

- 🟢 Amigos
- 🔴 Enemigos
- ⚪ Conocidos

### 💬 Análisis

Descripción generada del comportamiento del agente basada en sus características.

## 🎨 Características Visuales

### Animaciones

- **Entrada de logs**: Deslizamiento suave desde la izquierda
- **Nodos seleccionados**: Efecto de brillo pulsante
- **Hover en nodos**: Aumento de tamaño y brillo
- **Transiciones**: Todas las interacciones son fluidas

### Efectos

- **Glassmorphism**: Paneles con efecto de vidrio esmerilado
- **Gradientes**: Colores vibrantes en títulos y valores
- **Sombras**: Profundidad visual en elementos interactivos

## 🔍 Casos de Uso

### Análisis de Formación de Grupos

1. Observa el gráfico de grupos (línea morada)
2. Identifica picos de formación
3. Examina la red para ver qué agentes se agruparon
4. Haz clic en agentes del mismo grupo para ver sus características

### Seguimiento de Conflictos

1. Observa logs rojos (conflictos)
2. Identifica agentes involucrados
3. Examina sus personalidades (alta competitividad)
4. Observa cómo evolucionan sus relaciones

### Estudio de Cooperación

1. Busca logs azules de cooperación
2. Identifica agentes amables (alta amabilidad)
3. Observa cómo forman redes de amistad
4. Analiza el impacto en sus recursos

## 🚀 Tips y Trucos

### Mejor Visualización

- Usa zoom para ver detalles de áreas específicas
- Arrastra nodos para separar grupos densos
- Minimiza logs si obstruyen la vista

### Análisis Efectivo

- Pausa la simulación en momentos clave
- Compara personalidades de agentes exitosos
- Observa patrones en la formación de grupos

### Performance

- Reduce la velocidad si hay lag
- Cierra otros tabs del navegador
- Usa Chrome o Firefox para mejor rendimiento

## 🐛 Solución de Problemas Comunes

### La red no se actualiza

- Verifica que el badge diga "CONECTADO"
- Recarga la página (F5)
- Verifica la consola del navegador (F12)

### Los nodos están muy juntos

- Arrastra nodos manualmente para separarlos
- Haz zoom out para ver toda la red
- Espera unos segundos para que la simulación se estabilice

### Los logs van muy rápido

- Minimiza el panel de logs
- Reduce la velocidad de simulación
- Pausa para leer con calma

### El panel de detalles no se abre

- Asegúrate de hacer clic directamente en el círculo del nodo
- Verifica que el agente tenga datos cargados
- Recarga la página si persiste

## 📱 Compatibilidad

### Navegadores Soportados

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### Resoluciones Recomendadas

- Óptimo: 1920x1080 o superior
- Mínimo: 1280x720
- Responsive: Se adapta a tablets

## 🎓 Conceptos Avanzados

### Emergencia de Comportamientos

Observa cómo comportamientos complejos emergen de reglas simples:

- Formación espontánea de jerarquías
- Alianzas temporales
- Ciclos de conflicto y paz

### Memoria Basada en Grafos

Cada agente mantiene su propio grafo mental:

- Recuerda interacciones pasadas
- Ajusta comportamiento según historial
- Forma preferencias sociales

### LangGraph para Razonamiento

Agentes élite (0 y 1) usan LangGraph:

- Análisis de situación
- Toma de decisiones estratégicas
- Planificación a futuro

## 📚 Recursos Adicionales

- **Código fuente**: Inspecciona `index.html` para ver la implementación
- **Backend**: Revisa `api.py` y `modelo.py` para la lógica
- **Documentación**: Lee `README.md` para más detalles

---

**¿Necesitas ayuda?** Abre un issue en el repositorio o consulta la documentación completa.
