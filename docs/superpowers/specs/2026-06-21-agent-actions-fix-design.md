# Especificación de Diseño: Corrección de Acciones de Agentes y Sistema de Votaciones/Red Social

Fecha: 2026-06-21
Estado: Propuesto

## 1. Contexto y Problema

Durante las simulaciones autónomas, los agentes se limitan principalmente a moverse y votar, ignorando otras capacidades del motor social como la recolección, el comercio, la construcción de infraestructura, la fundación de facciones, o el uso/unión a instituciones. Este comportamiento anómalo se debe a una combinación de bugs en el cerebro cognitivo y en el router de acciones físicas:

1. **Bypass del Sistema BDI Heurístico:** Cuando el LLM falla (por ejemplo, al alcanzar límites de cuota) o no devuelve intenciones a largo plazo, el nodo `actuar` en `cerebro_langgraph.py` no realiza deliberación heurística BDI. En su lugar, ejecuta una única acción de fallback seleccionada al azar.
2. **AttributeError en `unirse_institucion`:** El router de acciones en `agent.py` y `agent_body.py` intenta acceder a `self.instituciones` en lugar de `self.modelo.instituciones`, lo que hace que unirse a cualquier institución falle inmediatamente con una excepción.
3. **Acciones no Normalizadas:** La acción `"INVITAR"` no se normaliza a `"invitar_grupo"`, provocando que el motor de simulación la clasifique como acción desconocida y la reemplace con un fallback de movimiento.
4. **Acción `VOTAR` sin sentido en fallbacks:** Los fallbacks procedimentales eligen la acción `VOTAR` al azar, desperdiciando el turno del agente si no hay asambleas activas.
5. **Mapeos Faltantes en `SocialRecSys`:** La clase encargada de la red social en `modelo.py` carece de métodos clave como `.comentar()`, `.get_siguiendo()`, `.get_seguidores()` y `.get_interacciones_usuario()`. Esto hace que las acciones sociales obligatorias fallen.
6. **Error de Tipo en PostgreSQL:** Al escribir la columna `timestamp` en `posts_sociales`, Postgres rechaza los enteros/floats de Python y requiere `TIMESTAMP`, y la posterior lectura carga objetos `datetime` que rompen la serialización JSON del estado.

## 2. Solución Propuesta

### 2.1. Fallback Heurístico BDI en LangGraph

Modificar la lógica de deliberación en el nodo `actuar` de `agents/cerebro_langgraph.py` para que, si `nuevas_intenciones` está vacío, el agente genere un plan BDI heurístico completo a partir de sus necesidades y deseos (usando el entorno percibido) en lugar de limitarse a una acción aislada.

### 2.2. Correcciones en el Router de Acciones Físicas

*   Reemplazar las referencias a `self.instituciones` por `self.modelo.instituciones` en `unirse_institucion` tanto en `agent.py` como en `agent_body.py`.
*   Agregar `"invitar"` a la lista de normalizaciones en `ejecutar_accion_final()` en ambos archivos:
    ```python
    if tipo in ["invitar_a_grupo", "invitar_al_grupo", "invitar_agente", "invitar"]:
        tipo = "invitar_grupo"
    ```

### 2.3. Filtrado de Voto en Fallback

Modificar `_generar_fallback_contextual` en `agents/cerebro_llm.py` para verificar si el agente tiene alguna votación activa pendiente antes de añadir la acción `"VOTAR"` a la lista de acciones posibles.

### 2.4. Implementación en `SocialRecSys` y Conversión de Tiempos

*   Implementar métodos en `SocialRecSys`:
    *   `comentar(self, post_id, autor_id, contenido)`
    *   `get_siguiendo(self, follower_id)`
    *   `get_seguidores(self, followed_id)`
    *   `get_interacciones_usuario(self, user_id)`
*   Usar `TO_TIMESTAMP(%s)` en la query de inserción de `posts_sociales` para PostgreSQL.
*   Convertir `timestamp` a float en `_cargar_posts_desde_db` llamando a `.timestamp()` si el campo devuelto es un objeto de tipo `datetime`.

## 3. Plan de Pruebas

1.  Ejecutar el script de prueba `scripts/reproduce_voting_loop.py` y validar que:
    *   No haya errores de PostgreSQL al insertar posts.
    *   No haya excepciones de `AttributeError` referentes a `SocialRecSys` o `.instituciones`.
    *   Los agentes realicen recolección y se unan o funden facciones/instituciones.
