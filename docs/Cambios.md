## 15-04-26 Implementación de Modo "Control de Agentes" (Turno Manual con LLM)

- **Fecha y hora**: 2026-04-15.
- **Descripción de la tarea**: Crear un modo de control donde el usuario dicta hasta 3 acciones para un agente, las cuales se ejecutan en su turno con narrativa generada por LLM.
- **Desafíos encontrados**:
    - El modo "posesión" anterior ejecutaba acciones inmediatamente y sin contexto narrativo.
    - Los agentes necesitaban una forma de integrar mandatos externos en su personalidad y alma.
    - El ciclo de turno de la simulación debía permitir múltiples acciones físicas si provenían de un plan de usuario.
- **Soluciones implementadas**:
    - **Backend**: Se añadió `acciones_control_usuario` a la clase `Agente` y el endpoint `SET_CONTROL_ACTIONS` en la API.
    - **Cerebro**: Nuevo método `generar_pensamiento_para_accion_forzada` en `CerebroLLM` que obliga al agente a justificar narrativamente las órdenes del Arquitecto.
    - **Simulación**: Modificación de `_procesar_turno_agente` en `ModeloRelacional` para interceptar y ejecutar secuencialmente planes de usuario antes del pensamiento autónomo.
    - **Frontend**: Nuevo componente `ControlAgentePanel.tsx` que categoriza absolutamente todas las acciones y habilidades (Vital, Social, Eco, Saber, Leyes, Dev, Move, War).
    - **Interfaz**: Integración en `AgentSidebar.tsx` con transiciones animadas entre vista de información y vista de control.
- **Resultados**:
    - El usuario puede orquestar turnos complejos para cualquier agente sin romper la coherencia narrativa del mundo.
    - Los agentes reaccionan ante las órdenes del usuario expresando pensamientos y mensajes fieles a su alma.
    - Se proporciona acceso total a todas las mecánicas del juego (skills, construcciones, leyes, social) desde un panel unificado.

## 15-04-26 Social LLM Ratio en 1.0 (posts sociales siempre con IA)

- **Fecha y hora**: 2026-04-15.
- **Descripción de la tarea**: Forzar que todos los posts sociales de agentes sean generados por el LLM, usando la personalidad y contexto completo del agente.
- **Desafíos encontrados**:
    - El sistema anterior usaba posts rápidos (plantillas fijas) en ~65% de los casos, lo que generaba mensajes repetidos y poco realistas.
    - Para simulación social realista, se requiere que cada post refleje la identidad y estado del agente.
- **Soluciones implementadas**:
    - Se cambió el valor por defecto de `social_llm_ratio` a 1.0 en `ModeloRelacional`.
    - Ahora todos los posts sociales automáticos usan el LLM salvo que se indique lo contrario por variable de entorno.
- **Resultados**:
    - Los mensajes sociales de los agentes son únicos, ricos y coherentes con su personalidad y contexto.
    - Se elimina la repetición de plantillas y se mejora la calidad de la simulación social.

## 15-04-26 Compatibilidad de Streaming con Ollama Cloud

- **Fecha y hora**: 2026-04-15.
- **Descripción de la tarea**: Corregir cuelgues largos durante streaming LLM con Ollama Cloud y mantener entrega en tiempo real al frontend.
- **Desafíos encontrados**:
    - LiteLLM arrojaba `Unable to parse ollama chunk` ante chunks válidos de Ollama Cloud con formato no esperado por su parser.
    - Cuando fallaba el streaming, el flujo podía quedarse esperando demasiado tiempo antes de devolver control.
    - Ollama Cloud puede operar por `/api/generate` aunque el código asumía prioritariamente `/api/chat`.
- **Soluciones implementadas**:
    - Se añadió `timeout` explícito configurable (`MUNDOIA_LLM_TIMEOUT_SECONDS`, default `90`) a las llamadas LLM.
    - Para modelos `ollama/*` en base URL de Ollama Cloud, se añadió stream directo por HTTP en `cerebro_llm`.
    - Se implementó fallback automático de endpoint: primero `/api/chat`, y si falla, `/api/generate`.
    - Se robusteció el parseo de líneas stream (`data: ...`, `[DONE]`, `message.content` y `response`).
- **Resultados**:
    - Se evita el bloqueo prolongado por incompatibilidad de parser.
    - El frontend puede volver a recibir chunks en vivo con mayor estabilidad en Ollama Cloud.
    - Ante fallos de endpoint o chunks atípicos, el sistema degrada de forma controlada en lugar de quedar colgado.

## 14-04-26 Corrección NODE_ENV no estándar en Frontend

- **Fecha y hora**: 2026-04-14.
- **Descripción de la tarea**: Eliminar advertencia de Next.js: "non-standard NODE_ENV value in your environment".
- **Desafíos encontrados**:
    - El `Dockerfile.frontend` (etapa runner) fija `ENV NODE_ENV production`.
    - `docker-compose.yml` inicia el contenedor frontend con `npm run dev`, pero hereda `NODE_ENV=production` de la imagen.
    - La combinación genera una inconsistencia: modo dev + NODE_ENV de producción.
    - Next.js 16 emite el warning al detectar esta inconsistencia.
- **Soluciones implementadas**:
    - Se agregó `NODE_ENV=development` al bloque `environment:` del servicio `mundoia-frontend` en `docker-compose.yml`. Esto overridea el valor del Dockerfile cuando se levanta para desarrollo.
- **Resultados**:
    - El warning desaparece al volver a hacer `docker compose up`.
    - El Dockerfile original queda intacto para builds de producción donde `NODE_ENV=production` sí es correcto.

## 14-04-26 Pipeline de Streaming en Tiempo Real (LLM -> Acción -> Social)

- **Fecha y hora**: 2026-04-14.
- **Descripción de la tarea**: Se implementó un flujo incremental para que el frontend reciba eventos en vivo durante el turno del agente: texto del LLM por streaming, inicio/fin de acción y publicación social inmediata.
- **Desafíos encontrados**:
    - El flujo original enviaba estado mayormente al final del paso de simulación.
    - `generar_pensamiento_y_accion` era request/response tradicional (sin stream de tokens).
    - No existían eventos WS estructurados para acción/social en tiempo real.
- **Soluciones implementadas**:
    - `ModeloRelacional` ahora expone `realtime_event_callback` para emitir eventos de bajo nivel en vivo.
    - `SessionManager.create_simulation` conecta ese callback al WebSocket usando `enqueue_message`.
    - En `CerebroLLM.generar_pensamiento_y_accion` se añadió soporte de stream (`MUNDOIA_LLM_STREAM=1` por defecto) con callback por chunk y fallback automático a modo no-stream si el proveedor no soporta streaming.
    - En `cerebro_langgraph.actuar` se inyecta el callback y se emiten eventos `llm_stream` con `reset/done`.
    - En el turno del agente (`_procesar_turno_agente`) se emiten `action_event` (`start`/`done`) alrededor de la ejecución física.
    - En `_ejecutar_accion_social_automatica` se emite `social_event` al crear post.
    - En frontend (`useGameStore`) se añadieron handlers para `llm_stream`, `action_event` y `social_event`.
- **Resultados**:
    - El usuario puede ver texto del LLM “escribiéndose” en vivo.
    - La acción del agente se refleja inmediatamente al iniciar/finalizar.
    - La publicación social aparece en tiempo real, sin esperar al cierre completo del paso.

## 14-04-26 Sincronización Inmediata de Construcciones en Frontend

- **Fecha y hora**: 2026-04-14.
- **Descripción de la tarea**: Se corrigió la visibilidad de construcciones para que, cuando un agente ejecute la acción `CONSTRUIR`, el edificio aparezca inmediatamente en el mapa del frontend sin esperar ciclos largos de sincronización.
- **Desafíos encontrados**: Aunque `construir_edificio` sí añadía el edificio en `tile.buildings`, el canal de WebSocket enviaba con frecuencia deltas sin mapa (`stats_delta`), por lo que la UI no recibía el cambio estructural del terreno en ese momento.
- **Soluciones implementadas**:
    - En `ModeloRelacional` se agregó la bandera `self._map_dirty` para marcar cambios estructurales del mapa.
    - En `construir_edificio`, al crear un edificio exitosamente, se marca `self._map_dirty = True`.
    - En el router de acciones del agente se acepta también `constrir` como alias de `construir` para tolerar el typo frecuente del LLM y no perder construcciones.
    - En `SessionManager.broadcast_state` (`api/api.py`) se detecta `map_dirty` y se fuerza `include_map=True` para enviar estado completo con el mapa actualizado.
    - Tras el envío exitoso, se limpia la bandera (`_map_dirty = False`) para evitar payloads grandes innecesarios en ciclos siguientes.
- **Resultados**: El frontend recibe el mapa actualizado justo después de una construcción y renderiza la nueva estructura en tiempo real.

## 11-04-26 Nombres Propios en Panel de Chat
- 2026-04-11: Se sustituyeron los IDs técnicos de los agentes (ej: `ag_456a0`) por sus nombres propios en la interfaz del chat. Ahora los agentes aparecen con sus identidades reales en la lista, encabezado y mensajes, mejorando la inmersión.
- Se actualizó el endpoint `/chat/{user_id}/agents` para incluir el campo `nombre`.
- Se refactorizó `ChatPanel.tsx` para consumir el nuevo campo.

## 11-04-26 Corrección de 404 y Doble Barra en Panel de Chat
- 2026-04-11: Se resolvió el error `404 Not Found` recurrente en el endpoint `/chat/{user_id}/agents`. La causa era una concatenación incorrecta de URLs que generaba una doble barra (`//chat/...`).
- 2026-04-11: Se refactorizó `web/frontend/src/utils/apiConfig.ts` para que `getHttpUrl("")` no devuelva una barra al final si el path está vacío, haciendo la construcción de URLs más robusta.
- 2026-04-11: Se actualizaron todas las llamadas `fetch` en `ChatPanel.tsx` para usar la utilidad centralizada de red de forma correcta, restaurando la carga de agentes y la persistencia del historial de chat desde PostgreSQL.

## 11-04-26 Hotfix de Emergencia: IndentationError en Modelo
- 2026-04-11: Se corrigió un error de indentación crítico en `core/modelo.py` (línea 5346) que impedía el arranque del backend. El error "unindent does not match any outer indentation level" fue resuelto eliminando un espacio extra en la validación de expansión del mapa.

## 11-04-26 Restauración de Orquestación y Reparación Estructural de Agentes
- 2026-04-11: Se agregó protección de fallback `or []` contra TypeError en `cargar_estado` (core/modelo.py) al recuperar agentes de la DB, evitando que la carga de la partida falle estrepitosamente si no hay agentes guardados o la DB devuelve None.
- 2026-04-11: Se integró la llamada incondicional a `self.cargar_estado()` en la inicialización de `ModeloRelacional` a fin de recuperar la persistencia de las partidas (mapa y agentes) de los usuarios tras el reinicio del servidor.
- 2026-04-11: Se eliminó un duplicado fantasma del método `_bdi_ejecutar_plan` en la clase Agente que generaba un conflicto de firmas en los argumentos (`TypeError`) y colapsaba el fallback cognitivo BDI.
- 2026-04-11: Se restauró la lógica de generación compleja (`OASIS-STYLE`) dentro de `spawn_agent()` en `ModeloRelacional`, reparando el `AttributeError` proveniente del ausente `_generar_nombre_agente()`.
- 2026-04-11: Se inicializó `self.lock` con `threading.Lock()` en el constructor de `ModeloRelacional` para evitar el `AttributeError` al intentar registrar logs concurrentes.
- 2026-04-11: Se eliminaron métodos estresados y duplicados en `ModeloRelacional` que interferían con la ejecución (`TypeError: log()`). Se corrigió además la instanciación incondicional de `system_prompt` en `cerebro_llm.py` que provocaba un `UnboundLocalError`.
- 2026-04-11: **Estabilización de Comunicación (Hotfix)**: Se reparó el flujo de logs añadiendo `agente_id` al callback de `ModeloRelacional` y a `user_log_callback` en la API. Esto restaura las burbujas de diálogo y el TTS en el frontend al permitir asociar los mensajes con agentes específicos.
- 2026-04-11: **Corrección de Estado LangGraph (Hotfix)**: Se sincronizaron las llaves de estado `mensaje_llm` y `mensaje_generado` en `cerebro_langgraph.py`, eliminando el bug que provocaba el envío de mensajes vacíos al frontend.
- 2026-04-11: **Persistencia Estructural**: Se implementó una serialización manual profunda del mapa y la historia mundial en `ModeloRelacional.guardar_estado`, resolviendo fallos silenciosos al intentar persistir objetos complejos no serializables en PostgreSQL.

Se realizó una cirugía estructural crítica en el núcleo del modelo para resolver una corrupción masiva de código que impedía la interacción de los agentes.

- **`core/modelo.py` (Cirugía Estructural)**: 
    - Se extrajeron más de 1500 líneas de código que estaban incorrectamente anidadas dentro de la clase `Agente` y se reubicaron en la clase `ModeloRelacional`.
    - Se restauró el método `step()` y el bucle principal de simulación.
    - Se implementó `Agente.ejecutar_accion_final`, un router maestro que conecta las decisiones cognitivas (Pensar) con acciones físicas (Recolección, Movimiento, Construcción, Social).
    - Se reparó la lógica de `_procesar_turno_agente` implementando el ciclo: Metabolismo -> Pensamiento -> Acción -> Comunicación -> Actividad Social.
- **`core/modelo.py` (Limpieza)**: Se eliminaron métodos esqueleto redundantes y se reparó la clase `Institucion.from_dict` que había quedado truncada.
- **Verificación**: Estructura de clases validada. Se confirmó que el sistema funciona correctamente dentro del entorno de contenedores Docker.

---

## 11-04-26 Evolución Dinámica del Alma y Sincronización de Identidad

Implementación de un sistema de crecimiento espiritual y corrección de incoherencias en la visualización de nombres.

- **`agents/alma.py` (Evolución Dinámica)**: El **Nivel de Conciencia** y la **Capacidad de Reflexión** ahora crecen con cualquier experiencia, no solo epifanías.
- **`core/modelo.py` (Sincronización)**: Sincronización bidireccional de nombres entre Identidad y Alma. Hablar/pensar ahora impulsa la evolución.
- **`web/frontend/src/components/AgentSidebar.tsx` (UI)**: Consistencia total de nombres en la pestaña de Alma.

---

## 11-04-26 Integración de Identidades Procedimentales y Mejora de Legibilidad
1: 
2: Implementación de identidades ricas para los agentes y optimización de la interfaz visual para reflejar nombres propios.
3: 
4: - **`web/frontend/src/types/agent.d.ts` (Restauración de Tipos)**: Se restauró la interfaz `Agent` a su estado completo tras una regresión accidental, recuperando campos de `alma`, `intenciones`, `deseos`, `creencias` y `skills`. Se integró la nueva interfaz `Identidad`.
5: - **`web/frontend/src/components/AgentSidebar.tsx` (Personalización Visual)**: El sidebar ahora muestra el **Nombre Real** (ej: *Aelius the Explorer*) y su **Emoji** único en lugar del ID técnico (`ag_123`). Se añadió el título honorífico y la biografía procedimental.
6: - **`web/frontend/src/components/WorldViewport.tsx` (Etiquetas en Mapa)**: Las etiquetas flotantes bajo los agentes en el mapa ahora muestran sus nombres reales, acortados inteligentemente para legibilidad, eliminando la etiqueta genérica "AGENTE".
7: - **`core/world_system.py` (Abundancia Biológica)**: Se incrementó drásticamente la frecuencia de aparición de alimento en biomas de pasto (del 15% al 40%) y de bancos de pesca en el agua (del 25% al 45%) para mejorar la supervivencia inicial.
- **`web/frontend/src/components/WorldViewport.tsx` (Sync de Iconos)**: Se solucionó el problema de las "cajas de regalo" (🎁) mediante un mapeo bilingüe de recursos. El sistema ahora reconoce `comida`, `madera`, `hierro`, `oro` y `pescado` con sus iconos temáticos correspondientes (🍎, 🪵, ⚙️, 💰, 🐟).
- **`core/modelo.py` (Spawn de Identidades)**: Se sincronizó la creación de agentes para que generen automáticamente una `Identidad` (Nombre, Emoji, Título) vinculada a su `Alma` al nacer.
8: 
9: ---
10: 
11: ## 11-04-26 Generación de Mapas Realistas y Fix de Spawn en Modo Dios


Implementación de un motor de generación de terreno avanzado y resolución de errores críticos de inicialización.

- **`core/world_system.py` (Biomas por Ruido Fractal)**: Se sustituyó la generación puramente aleatoria por un sistema de **Ruido de Valor (Fractal Noise)**.
    - El mundo ahora cuenta con **cordilleras coherentes, lagos profundos, desiertos y bosques densos**.
    - La expansión del mundo (`expandir`) ahora es **seamless**, manteniendo la coherencia geográfica al generar nuevos sectores.
    - Los recursos se distribuyen ahora de forma lógica según el bioma (ej: minerales en montañas, madera en bosques).
- **`core/modelo.py` (Spawn Aleatorio)**: Se cambió la distribución secuencial (en fila) por una **distribución aleatoria** en todo el mapa. Ahora los agentes nacen en coordenadas `(x, y)` impredecibles.
    - **Nombres Dinámicos**: Se mejoró la generación de IDs Únicos (UUIDs cortos) para acompañar a los nombres complejos generados por el sistema de Identidad, garantizando una población diversa desde el inicio.
    - Sincronización automática de nombres entre el sistema de Alma y la Identidad pública.

---

## 11-04-26 Corrección de Crashes en Backend: TerrainType, Callbacks y Atributos

Se han corregido tres errores críticos que impedían el inicio de la simulación o la creación de mapas.

- **`core/world_system.py` (TerrainType.STATS)**: El diccionario `STATS` se ha movido fuera de la clase `TerrainType` (Enum) para evitar que sea tratado como un miembro del Enum, permitiendo el uso de sus métodos nativos como `.get()`.
- **`api/api.py` (user_log_callback)**: Se corrigió un `TypeError` al hacer opcionales los parámetros `subtitulos` y `tts_text` en el callback de logs, eliminando la discrepancia con las llamadas del motor central.
- **`core/modelo.py` (Atributos ModeloRelacional)**: Se rescataron múltiples atributos críticos (`weather`, `sistema_misiones`, `historia`, `db`, etc.) que estaban inicializados en un bloque de código inalcanzable (unreachable code) dentro de `ModeloRelacional`. Se han movido correctamente al método `__init__`.
- **Verificación**: Se validaron las tres correcciones mediante scripts de prueba independientes, asegurando que el mundo se genera, los logs fluyen y el estado inicial del modelo es consistente.

---

## 10-04-26 Centralización de Infraestructura de Red (Portabilidad Total)

Se ha eliminado la dependencia de URLs hardcodeadas en todo el frontend para permitir la portabilidad total entre entornos locales y de producción.

- **`apiConfig.ts`**: Nueva utilidad centralizada que gestiona la construcción dinámica de URLs (HTTP y WebSocket) basándose en `NEXT_PUBLIC_API_HOST`.
- **Portabilidad**: El sistema ahora detecta automáticamente si el usuario ha configurado un host personalizado en `localStorage` o usa el configurado en `.env`.
- **Refactorización de Componentes**: `ConfigPanel`, `ArchitectPanel`, `SocialPanel`, `ChatPanel`, `AgentSidebar`, `GamePage` y `AuthPage` han sido actualizados para consumir la configuración centralizada.
- **Estabilización de UI**: Se restauró `ConfigPanel.tsx` a su versión premium estable y se solucionaron errores de importación de módulos.

---

## 10-04-26 Corrección de Compatibilidad: litellm y aiohttp

Resuelto el error crítico de arranque del backend debido a una incompatibilidad entre `litellm` y versiones antiguas de `aiohttp`.

- **Actualización de Dependencias**: Se incrementó la versión de `aiohttp` a `>=3.10.0` en `requirements.txt`.
- **Causa**: `litellm` requiere el atributo `ConnectionTimeoutError` en `aiohttp`, el cual solo está disponible a partir de la versión 3.10.

---

## 10-04-26 Unificación TUI: Experiencia Gemela Premium

Se integró un motor de interfaz compartido para eliminar la disparidad entre los clientes de terminal local y remoto.

- **`shared_widgets.py`**: Nuevo núcleo de UI que gestiona el Mapa Braille High-Res, el HUD de estadísticas y el Panel de Arquitecto.
- **TUI Local (`local_tui.py`)**: Actualizada a "Premium Edition". Incluye controles divinos directos sobre el objeto en memoria.
- **TUI Remota (`remote_tui.py`)**: Actualizada a "Premium Edition". Incluye el mismo set de herramientas divinas, sincronizadas con la API mediante WebSockets y HTTP.
- **Modo Arquitecto**: Paridad total de botones (Clima, Génesis, Economía, Eventos) en todas las interfaces de terminal.

---

## 10-04-26 Refactor: CLI del Arquitecto con Poderes Totales

## 10-04-26 Corrección Arquitectural: Agentes Controlados por el Arquitecto

## 16-04-26 Enforce per-turn: Mensaje, Acción, Acción Social

- **Fecha y hora**: 2026-04-16.
- **Descripción de la tarea**: Forzar que cada turno de agente ejecute exactamente: 1 mensaje (público/privado/grupal), 1 acción física, 1 acción en la red social. Esto gamifica el turno y obliga a decisiones alineadas con objetivos personales del agente.
- **Cambios implementados**:
  - Modificado `core/modelo.py`: `_procesar_turno_agente` ahora normaliza y fuerza los tres pasos. Si el LLM no proporciona un mensaje o acción, se generan fallbacks basados en necesidades (COMER/RECOLECTAR/EXPLORAR/SOCIALIZAR).
  - Usado `agente.social_force_action(step)` cuando existe; en su defecto cae en `_ejecutar_accion_social_automatica` para compatibilidad.
  - Se respetan los callbacks `realtime_event_callback` y logging para trazabilidad de eventos (action_event, social_event).
- **Desafíos encontrados**:
  - Duplicidad de definiciones de `Agente` en `core/entities/agent.py` y `core/modelo.py`, que obliga a confirmar cuál clase se instancia en tiempo de ejecución.
  - Necesidad de diseñar fallbacks que no rompan la coherencia narrativa ni introduzcan acciones imposibles.
- **Soluciones aplicadas**:
  - Implementación no intrusiva en `ModeloRelacional` (ruta usada por la simulación), dejando compatibilidad hacia atrás.
  - Fallbacks basados en `agente._evaluar_tipo_accion_necesidades()` para mantener prioridad en supervivencia, social o exploración.
- **Resultados**:
  - Cada turno ejecuta obligatoriamente: un mensaje público/privado/grupal, una acción en el mundo y una acción social. Esto incrementa diversidad (recolección, construir, fundar grupos, crear instituciones) y reduce el sesgo comunicativo de solo "hablar".
- **Siguientes pasos**:
  - Revisar si `core/entities/agent.py` también necesita la misma wiring (aplicar cambios si se detecta uso concurrente).
  - Añadir tests unitarios/integración que verifiquen por agente y por turno la invariant 1 mensaje/1 acción/1 social.
  - Ajustar `agents/bdi_components.py` para favorecer acciones no-comunicativas cuando la utilidad de supervivencia/recursos sea alta.





Se resolvió la confusión entre el modo CLI (auto-generación de agentes) y el modo API web (el usuario los crea desde el frontend).

- **Problema**: Al conectarse por WebSocket, el servidor creaba 30 agentes automáticamente via `NUM_AGENTES`, contradiciendo la mecánica de que el Arquitecto (usuario) construye su mundo desde el frontend.
- **Fix `api.py` (WebSocket)**: La primera conexión ahora llama `create_simulation(start_empty=True)` — mundo vacío al conectar.
- **Fix `SessionManager.create_simulation()`**: Eliminado `os.getenv("NUM_AGENTES")`. La API siempre pasa `num_agentes=0`; los agentes los crea el usuario vía `SPAWN_AGENT`.
- **`.env`**: `NUM_AGENTES` y `PASOS_SIMULACION` quedan comentados — solo aplican al modo CLI (`python core/modelo.py`).

---

## 10-04-26 Recreación del Archivo de Entorno (.env)

Recreación del archivo `.env` eliminado, con todas las variables detectadas en el código fuente.

- **Base de datos**: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS` — apuntando al contenedor `mundoia-db`.
- **LLM**: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_API_BASE`, `LLM_MODEL` y `LLM_PROVIDER` para el motor de agentes.
- **Herramientas**: `TAVILY_API_KEY` para búsqueda web de los agentes.
- **Embeddings**: `CHROMA_PERSIST_DIR` y `EMBEDDING_MODEL` para el servicio de embeddings.
- **Simulación**: `NUM_AGENTES` (30) y `PASOS_SIMULACION` (100).
- **TTS**: `TTS_URL` para el servicio de Text-To-Speech.

---

## 17-01-26 Completar Sistema de Autenticación

Implementación final del flujo de registro e inicio de sesión que estaba incompleto.

- **Redirección Frontend**: Configurada la página `/auth` para redirigir a `/game` tras un login exitoso.
- **Protección de Rutas**: Implementada la lógica para redirigir usuarios autenticados desde `/auth` a `/game` y proteger `/game` de accesos no autorizados.
- **UX Landing Page**: Actualizada la página de inicio para reconocer sesiones activas y ofrecer un botón de "Continuar".
- **Verificación Backend**: Validada la funcionalidad de los endpoints de registro y login mediante script de prueba.

---

## 18-01-26 Restauración de UI y Visor de Diálogos

Corrección de errores críticos en el frontend y restauración de funcionalidades perdidas.

- **Corrección ArchitectPanel**: Solucionado error de TypeScript al hacer opcional la propiedad `isOpen` e implementar animaciones de entrada/salida.
- **Restauración HUD**: Reimplementados los controles de interfaz perdidos (Selector de Vistas, Barra de Estado, Controles de Juego y Botones de Paneles).
- **Visor de Diálogos**: Añadido panel inferior para visualizar logs y diálogos del sistema en tiempo real.
- **Manejo de Logs**: Solucionado error `TypeError` en el mapeo de logs, permitiendo renderizar objetos de log complejos y timestamps reales además de texto plano.

---

## 18-01-26 Mejoras en UI y Lógica de Leyes

Mejoras en la interfaz de usuario y corrección de la lógica de toma de decisiones de los agentes.

- **UI Refinada**: Implementado menú desplegable (Dropdown) para el selector de vistas para limpiar la interfaz.
- **Visor de Logs**: Reposicionado el panel de logs a la esquina inferior izquierda, aumentado su altura para mejor legibilidad y añadido estilos distintivos para mensajes de "PENSAMIENTO".
- **Lógica Agentes**: Actualizado `cerebro_langgraph.py` para que los agentes generen propuestas de ley con el formato correcto (`PROPONER_LEY:alcance:texto`) y temas variados, incluyendo intentos de Liderazgo.
- **Backend Modelo**: Actualizado `modelo.py` para parsear correctamente las acciones de ley directamente desde la cadena de decisión del agente, solucionando el problema de propuestas vacías o mal formadas.

---

## 18-01-26 Ajustes Visuales y Panel de Diplomacia

Refinamientos visuales solicitados por el usuario y expansión de funcionalidades del panel de información.

- **Controles 3D**: Reposicionados a la esquina inferior derecha para evitar conflictos con el nuevo visor de logs.
- **Estilo de Logs**: Implementado código de colores semántico para los mensajes (Amarillo: Eventos, Rosa: Política, Cian: Sistema) y encapsulamiento visual distintivo para los Pensamientos de los agentes.
- **Panel de Facciones**: Añadida nueva pestaña "Diplomacia" que visualiza las alianzas activas entre agentes y su estado.
- **Overlay de Instrucciones**: Ajustado el orden de renderizado para asegurar que las instrucciones se muestren siempre por encima de la interfaz de juego.
- **Modelo 3D Refactorizado**: Transformación visual completa del modo 3D al estilo "Juego de Estrategia" (Civilization), incluyendo terreno low-poly con bordes definidos, montañas con picos múltiples, bosques densos de pinos y agentes representados como "peones" (meeples) estilizados.

---

## 18-01-26 Refinamiento de Burbujas de Diálogo 2D

Transformación de los mensajes flotantes de los agentes en el tablero 2D para mejorar la legibilidad y estética.

- **Párrafos Multilínea**: Implementado sistema de envuelto automático de texto (`text wrap`) que divide los mensajes largos en párrafos, evitando que se extiendan horizontalmente fuera de la vista.
- **Ajuste de Altura Dinámico**: El fondo de la burbuja ahora calcula y adapta su altura automáticamente según la cantidad de líneas de texto generadas.
- **Estética RPG Mejorada**: Añadido puntero Direccional hacia el agente, efecto de resplandor (`glow`) y bordes estilizados para un look más premium y funcional.
- **Optimización de Animación**: Refinado el fade-in y el movimiento ascendente al aparecer para una experiencia visual más fluida.

---

## 18-01-26 Integración de Gamificación y Misiones Globales

Transformación de la simulación en una experiencia gamificada con objetivos claros y mecánicas de progreso.

- **Sistema de Misiones**: Definida clase `Mision` en el backend para gestionar objetivos globales (construcción, recursos) con recompensas y seguimiento de progreso.
- **Inteligencia de Agentes**: Integradas las misiones activas en el contexto cognitivo (`cerebro_langgraph.py`) y añadida heurística para priorizar la construcción de edificios requeridos si hay recursos suficientes.
- **Interfaz de Misiones**: Implementado nuevo componente `MissionsPanel` en el frontend para visualizar misiones activas, progreso y recompensas, accesible desde la barra superior.
- **Gestión de Estado Frontend**: Actualizado `useGameStore` para sincronizar las misiones mediante WebSocket y gestionar su visibilidad.

---

## 20-01-26 Evolución de Reinos, Misiones y Recompensas

Implementación masiva para dar soberanía a los agentes en sus grupos y gamificar la experiencia del usuario con recompensas visuales.

- **Nombramiento Dinámico de Facciones**: Los agentes ahora proponen y fundan grupos con nombres creativos propios (ej: "Orden del Amanecer") mediante el LLM, eliminando la lista preestablecida.
- **Motor de Misiones Mejorado**: Creado `sistema_misiones.py` con 10 misiones predefinidas de dificultad variable, objetivos medibles y sistema de desbloqueo progresivo.
- **Sistema de Puntaje de Usuario**: Implementado contador de puntos de prestigio para el usuario Arquitecto, visible en el HUD principal.
- **Celebraciones Premium**: Añadido componente `MissionCelebration.tsx` con animaciones de Framer Motion e integración de `canvas-confetti` (vía importación dinámica) para festejar el cumplimiento de objetivos.
- **Optimización de UX**: Implementado auto-scroll inteligente en el panel de logs y corregidos errores de sincronización en la API para reflejar el estado de las misiones en tiempo real.
- **Build & Robustez**: Solucionado error de construcción relacionado con módulos externos mediante el cambio a carga dinámica de scripts en el lado del cliente.

---

## 21-01-26 Unificación de Comunicación y Crónica de la Sociedad

Consolidación de la narrativa del mundo y mejora de la cohesión visual en todas las dimensiones de la simulación.

- **Crónica de la Sociedad**: Implementado sistema de historia con la clase `LibretaHistoria`. Se asigna automáticamente un "Historiador" entre los agentes para narrar hitos (fundaciones, leyes, misiones) con un tono épico generado por IA.
- **Ranking de Arquitectos**: Añadido panel de ranking global en la página de inicio, permitiendo ver los puntajes de los mejores usuarios en tiempo real.
- **Diálogos 3D Unificados**: Rediseñadas las burbujas de mensajes en la vista de esfera 3D para replicar el estilo de terminal RPG del 2D (bordes neón, fondo oscuro, mono-font).
- **Diálogos en Red Social**: Integrado el sistema de burbujas en el grafo de relaciones, permitiendo ver lo que dicen los agentes mientras interactúan en el mapa de conexiones dinámico de D3.
- **Estabilidad de Build**: Corregido error crítico de `canvas-confetti` en Next.js mediante el uso de importaciones dinámicas asíncronas dentro del ciclo de vida de React, asegurando un despliegue estable.

---

## 21-01-26 Refinamiento de HUD y Ergonomía Visual

Optimización de la disposición de elementos en pantalla para evitar superposiciones y mejorar el acceso a la información ambiental.

- **Separación de Paneles**: Reubicado el panel de misiones a una posición inferior (`top-[440px]`) para evitar colisiones con el botón de control mental "Mind" y asegurar que ambos elementos tengan espacio visual dedicado.
- **HUD Meteorológico Global**: Extraído el widget de clima que se encontraba oculto tras el selector de vista de mapa. Ahora se renderiza como un visor flotante en el centro superior de la pantalla, visible y consistente en todos los modos de vista (2D, 3D y Grafo).
- **Z-Index Unificado**: Ajustada la jerarquía de renderizado para asegurar que los paneles interactivos se mantengan correctamente por encima de los fondos, mejorando la respuesta táctil y visual del Arquitecto.

---

## 21-01-26 Radio Global y Visibilidad de Construcciones

Expansión de las capacidades de comunicación de los agentes y mejora en la representación visual de la infraestructura.

- **Sistema de Radio Global**: Implementada la nueva acción `ANUNCIAR:mensaje` en la lógica cognitiva de los agentes. Esto les permite enviar transmisiones de radio a todos los habitantes del mundo sin necesidad de asambleas o leyes, facilitando la coordinación espontánea.

- **Visibilidad de Construcciones 2D**: Mejorada la representación de edificios en el mapa D3. Se han añadido círculos de fondo con bordes de neón que heredan el color de la facción propietaria y se han actualizado los iconos a color blanco con efectos de resplandor para asegurar su visibilidad sobre terrenos oscuros.
- **Corrección de Renderizado 3D**: Solucionado un error crítico en el visor esférico donde las construcciones no se mostraban debido a una discrepancia en los nombres de las propiedades y el formato de las cadenas (Title Case vs lowercase).
- **Consistencia de Datos**: Asegurada la propagación de la información de infraestructura desde el backend (`Tile.buildings`) hasta el socket de la API, permitiendo un reflejo inmediato de las obras en todos los tableros.

---

## 10-04-26 Reestructuración Arquitectónica y Modularización de MundoIA

Saneamiento integral del repositorio para transformar una estructura plana y desordenada en una arquitectura modular de grado empresarial.

- **Migración a la Raíz**: Elevación de todo el núcleo operativo desde `multiagent_simulation` a la raíz del repositorio `MundoIA`.
- **Arquitectura Modular**: Organización de archivos en directorios lógicos:
    - `api/`: Comunicación y servicios de red.
    - `agents/`: Sistemas cognitivos, BDI y consciencia.
    - `core/`: Motor de simulación y validación de reglas de mundo.
    - `systems/`: Subvínculos de crónicas, misiones, memoria y herramientas.
    - `data/`: Persistencia física (SQL, ChromaDB y archivos de historia).
    - `mobile/` & `web/`: Interfaces de usuario multiplataforma.
- **Refactorización de Dependencias**: Actualización masiva de importaciones en Python para soportar la ejecución modular (`api.api`, `core.modelo`, etc.).
- **Actualización de Infraestructura**: Reconfiguración de `Dockerfile.backend`, `docker-compose.yml` y scripts de inicio (`start.sh`) para reflejar los nuevos senderos de ejecución.
- **Pathing Adaptativo**: Corregida la lógica de búsqueda de esquemas SQL en el backend y ajustado el `sys.path` de las herramientas CLI para garantizar funcionamiento autónomo desde cualquier nivel jerárquico.

---

## 23-01-26 Estabilización de Atributos y Dependencias Frontend

Corrección de errores de ejecución que impedían el inicio correcto de la simulación y el renderizado de efectos visuales.

- **Atributos de Modelo**: Corregido `AttributeError` en `ModeloRelacional` al asegurar la inicialización del atributo `civilizaciones` en el preámbulo de la clase. Esto previene fallos al cargar estados persistentes desde PostgreSQL.
- **Dependencias de Animación**: Resuelto error de "Module not found" para `canvas-confetti` en el frontend. Se forzó la instalación de la dependencia y sus tipos para asegurar que las celebraciones de misiones funcionen correctamente en el entorno de ejecución.
- **Robustez de Carga**: Verificada la consistencia de los diccionarios de estado globales durante el arranque para evitar excepciones en el broadcast de websockets.
\n---\n\n## 11-04-26 Corrección de Flujo de Comunicación Frontend-Backend\n\nResolución de fallo de diseño donde los mensajes autónomos de los agentes no se visualizaban en el frontend.\n\n- **Estandarización de Backend ( y )**: Se extrajo el ID del agente explícitamente en los metadatos de los websockets y se forzó la inclusión del identificador entre corchetes al inicio del mensaje para hacer más robusto el parseo.\n- **Actualización Frontend ()**: Se optimizó la lectura de mensajes del websocket para priorizar la clave `agent_id` proporcionada por el backend en lugar de depender exclusivamente de Regex, evitando que etiquetas como `[CHAT]` interrumpieran la renderización de los globos de diálogo.

---

## 11-04-26 Uso de Nombre Propio por Agentes

- **Identidad en el LLM**: Se ajustó el contexto en `cerebro_langgraph.py` y `cerebro_llm.py` para que los agentes utilicen y perciban el nombre propio (`identidad.nombre`) de sí mismos y de otros agentes en lugar del identificador técnico (`unique_id`) durante sus interacciones, reflexiones y decisiones.

---

## 16-04-26 Multipartida por usuario: menú inicio, QuickPlay y persistencia

- **Fecha y hora**: 2026-04-16.
- **Descripción de la tarea**: Implementada la experiencia de multipartida por usuario: pantalla inicial (/start) con opciones Cargar / Iniciar nueva / Partida Rápida; generación rápida de partidas con agentes aleatorios (QuickPlay) y persistencia ligada a la cuenta.
- **Cambios implementados**:
  - Backend: añadidos endpoints en `api/api.py`: POST `/games/quickplay`, POST `/games/save`, GET `/games/list/{user_id}`, POST `/games/load`, GET `/ranking`. Se reutiliza `ModeloRelacional.spawn_agent`, `guardar_estado` y `cargar_estado`.
  - Frontend: nueva ruta `web/frontend/src/app/start/page.tsx`, redirección desde `/auth` a `/start`, y botón "Guardar partida" en `web/frontend/src/app/game/page.tsx` que llama a `/games/save`.
  - Persistencia: `DatabaseManager.get_world_state`, `save_score` y `get_ranking` reutilizados para listar y rankear partidas por mejor puntaje.
- **Observaciones**: Autorización y validación de `user_id` deben revisarse; es recomendable limitar frecuencia/tamaño de guardados para evitar escrituras masivas.
- **Siguientes pasos**: Añadir modal de carga detallada, pruebas de integración (guardar/cargar/quickplay), y protección de endpoints (tokens/sesiones).
