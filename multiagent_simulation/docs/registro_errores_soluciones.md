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
