# Registro de Errores y Soluciones

## 14-01-26 NameError: name 'modelo' is not defined en api.py

**Descripción**: El servidor fallaba al iniciar si ocurría un error durante `ModeloRelacional.cargar_estado()`. Esto se debía a que el método `log()` del modelo intentaba llamar al callback `log_to_ws` en `api.py`, el cual intentaba acceder a la variable global `modelo` antes de que esta terminara de ser inicializada y asignada.

**Solución**: Se modificó `log_to_ws` en `api.py` para acceder a la variable global `modelo` de forma segura utilizando `globals().get('modelo')`. Si el modelo aún no está definido, se asume un paso de simulación 0.

**Archivo afectado**: `api.py`

---

## 14-01-26 ValueError: too many values to unpack (expected 16) en modelo.py

**Descripción**: Al intentar cargar el estado desde PostgreSQL, el sistema fallaba con un error de desempaquetado. Esto ocurrió porque la consulta `SELECT * FROM agentes` devolvía 17 columnas (tras añadir `civilizacion_id` y el `timestamp` automático), pero el código solo esperaba 16.

**Solución**: Se actualizó el método `cargar_estado` en `ModeloRelacional` para desempaquetar las 17 columnas y asignar correctamente el `civilizacion_id` a los agentes cargados.

**Archivo afectado**: `modelo.py`

---

## 14-01-26 Fallo en Frontend por Ejecución de Código (Inyección HTML)

**Descripción**: El frontend (especialmente `index.html`) fallaba o se rompía visualmente cuando los agentes ejecutaban código cuyo resultado contenía etiquetas HTML (ej: `</div>`, `<script>`). Al no escapar estos caracteres en el log, el navegador los interpretaba como parte de la estructura de la página, rompiendo el diseño o ejecutando scripts.

**Solución**:

1. Se implementó una función `escapeHTML` en `index.html` para limpiar todos los mensajes antes de insertarlos en el DOM.
2. Se truncaron los resultados de ejecución de código a 1000 caracteres en `herramientas.py` para evitar saturación.
3. Se mejoró la delimitación de los resultados de código en `cerebro_langgraph.py`.

**Archivos afectados**: `index.html`, `herramientas.py`, `cerebro_langgraph.py`

---

## 17-01-26 UnboundLocalError: cannot access local variable 'accion' where it is not associated with a value en cerebro_langgraph.py

**Descripción**: En la función `razonar_accion`, si un agente recibía un mensaje del "Arquitecto" que no contenía una palabra clave de acción reconocida (como "RECOLECTAR", "SOCIALIZAR", etc.), la variable `accion` no se inicializaba dentro de ese bloque de código. Esto provocaba un `UnboundLocalError` cuando el código intentaba acceder a `accion` para evaluarla.

**Solución**: Se añadió una línea para inicializar `accion` como una cadena vacía (`accion = ""`) al principio del bloque que maneja los mensajes del "Arquitecto". Esto asegura que `accion` siempre tenga un valor asignado antes de ser utilizada, evitando el error.

**Archivo afectado**: `cerebro_langgraph.py`

---

## 21-01-26 Runtime QuotaExceededError en Frontend

**Descripción**: El sistema fallaba al intentar guardar el estado completo de la simulación en el `localStorage` del navegador. Dado que el objeto de estado (especialmente los logs y el mapa) crece rápidamente, se superaba el límite de 5MB permitido por el navegador, bloqueando la ejecución.

**Solución**: Se modificó la lógica de persistencia en `useGameStore.ts`. Ahora, mediante un filtro en `setItem`, solo se guardan los datos esenciales de la sesión (autenticación) y se añadió un bloque `try-catch` para evitar una ruptura total si el almacenamiento vuelve a saturarse.

**Archivo afectado**: `frontend/src/store/useGameStore.ts`

---

## 21-01-26 Error 400 - Provider returned error: Prompt too large (Tokens)

**Descripción**: Los agentes dejaban de responder cuando el contexto acumulado (leyes, propuestas, lore) superaba el límite de tokens del modelo (Mistral/Google en OpenRouter). El prompt llegó a exceder los 268k tokens debido al crecimiento descontrolado de las listas de leyes facilitadas al LLM.

**Solución**: Se implementó una "dieta de contexto" en `cerebro_llm.py` y `cerebro_langgraph.py`, limitando el lore a 1000 caracteres y las listas de leyes/propuestas a los 5 elementos más recientes.

**Archivos afectados**: `cerebro_llm.py`, `cerebro_langgraph.py`

---

## 21-01-26 AttributeError: 'ModeloRelacional' object has no attribute 'actualizar_economia'

**Descripción**: Tras la consolidación de los métodos `step()` en `ModeloRelacional`, se invocó una función de actualización económica que no había sido definida como método independiente, provocando el fallo del hilo de simulación.

**Solución**: Se creó el método `actualizar_economia` en `ModeloRelacional`, aislando la lógica bursátil y monetaria para su correcta ejecución en cada turno.

**Archivo afectado**: `modelo.py`
---

## 21-01-26 Error de WebGL en WorldViewport3D y Falso Negativo

**Descripción**: El componente `WorldViewport3D` fallaba si WebGL no estaba disponible. Una primera solución con detección manual (`useEffect`) resultó ser demasiado estricta, mostrando el mensaje "WebGL Not Supported" a usuarios que sí tenían soporte, pero que fallaban la detección.

**Solución**: Se reemplazó la detección manual por un `ErrorBoundary` de React. Se creó un componente `ErrorBoundary.tsx` que envuelve la escena 3D. Si el componente `<Canvas>` falla al renderizar (por ejemplo, por un error de contexto WebGL), el `ErrorBoundary` lo captura y muestra un mensaje de error amigable, sin bloquear la aplicación para los usuarios con configuraciones válidas.

**Archivos afectados**: `frontend/src/components/WorldViewport3D.tsx`, `frontend/src/components/ErrorBoundary.tsx`
