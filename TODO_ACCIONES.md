# TODO - MundoIA (Acciones Prioritarias)
**Basado en revisión técnica del 2026-03-18**
**Prioridad:** Media-Alta (proyecto de ocio en uso activo)

---

## 🎯 RESUMEN DE ESTADO

- ✅ **Funcional**: Juego funciona, visualización working
- ✅ **Gamificación**: Misiones, puntajes, ranking implementados
- ⚠️ **Performance**: WebSocket flood, sin delta updates
- ⚠️ **Escalabilidad**: Falta índices DB, memória límite
- ⚠️ **Calidad**: Tests casi inexistentes
- ⚠️ **Mantenibilidad**: modelo.py muy grande (6600 líneas)

---

## 🔥 BLOQUEO CRÍTICO (IMPRESCINDIBLE)

### WS-1: Implementar Delta Updates en WebSocket
**Problema:** `on_state_change()` envía estado completo en cada cambio → satura ancho de banda.
**Solución:** Enviar solo deltas (qué agente cambió, qué atributos cambiaron).

**Tareas:**
- [ ] Leer `api.py` línea ~150-200 donde está `on_state_change` y `broadcast_state`
- [ ] Modificar `broadcast_state` para enviar `{type: "agent_update", agent_id: "...", changes: {...}}` en lugar de estado completo
- [ ] Modificar frontend (`useGameStore`) para mergear cambios en el estado local
- [ ] Probar con 50 agentes: medir trafico WebSocket antes/después
- [ ] Verificar que la UI se actualiza correctamente con deltas

**Impacto:** Reduce 90% del trafico WebSocket → mejora performance drásticamente.

---

## ⚡ ALTA PRIORIDAD (esta semana)

### DB-1: Añadir Índices a PostgreSQL
**Problema:** Sin índices, queries se lentifican con datos.
**Solución:** Ejecutar ALTER TABLE para crear índices.

**Tareas:**
- [ ] Abrir `schema.sql` y añadir al final:
```sql
CREATE INDEX idx_agentes_user_id ON agentes(user_id);
CREATE INDEX idx_logs_user_turn ON logs_simulacion(user_id, turno);
CREATE INDEX idx_estado_user ON estado_mundo(user_id);
CREATE INDEX idx_misiones_user ON misiones(user_id);
CREATE INDEX idx_civilizaciones_user ON civilizaciones(user_id);
```
- [ ] Recrear DB desde schema (o aplicar índices a DB existente):
  ```bash
  docker-compose exec mundoia-db psql -U architect -d mundoia -f /app/schema.sql
  ```
- [ ] Verificar índices creados: `\d agentes` en psql
- [ ] Probar carga inicial de partida con 30 agentes → debe ser más rápido

### PERF-1: Limitar Memoria de Agentes
**Problema:** `MemoriaGrafica` guarda mensajes/acciones sin límite → OOM en simulaciones largas.
**Solución:** Limitar a últimos N mensajes (ej: 100) por agente.

**Tareas:**
- [ ] Leer `memoria.py` → clase `MemoriaGrafica`
- [ ] Añadir parámetro `max_mensajes=100` en `__init__`
- [ ] En `añadir_mensaje()` y `añadir_accion()`, truncar lista si supera max
- [ ] Probar simulación de 1000 turnos → memoria debe estabilizarse
- [ ] Verificar que el historial de diálogos sigue siendo útil (últimos 100)

### PERF-2: Timeout en LLM Calls
**Problema:** Si LLM se cuelga, turno se atasca.
**Solución:** Añadir timeout 30s en llamadas `cerebro_langgraph.py`.

**Tareas:**
- [ ] En `cerebro_langgraph.py`, donde se hace `llm.ainvoke()`, envolver en `asyncio.wait_for(..., timeout=30)`
- [ ] Si timeout, lanzar excepción y caer a `cerebro_llm` simple
- [ ] Loggear advertencia cuando timeoutea
- [ ] Probar simulando LLM lento (cambiar a modelo muy lento) → ver si recupera

### TEST-1: Tests Unitarios para SistemaMisiones
**Problema:** Cobertura ~0% → misiones podrían romperse sin detectar.
**Solución:** Tests automatizados para verificación de misiones.

**Tareas:**
- [ ] Crear `tests/test_sistema_misiones.py`
- [ ] Test: `Mision.verificar_completada()` para cada tipo:
  - [ ] construir (1 hospital)
  - [ ] población (50 agentes)
  - [ ] facciones (5 facciones)
  - [ ] economía (10000 dinero)
  - [ ] leyes (10 leyes)
  - [ ] asambleas (5 asambleas)
- [ ] Mockear `modelo` con datos mínimos
- [ ] Ejecutar: `pytest tests/test_sistema_misiones.py -v`
- [ ] Integrar en CI (GitHub Actions)

---

## 📊 MEDIA PRIORIDAD (siguiente bloque)

### REFACTOR-1: Separar modelo.py en Módulos
**Problema:** `modelo.py` tiene 6600 líneas → difícil mantener y testear.
**Solución:** Refactorizar en paquete modular.

**Estructura propuesta:**
```
modelo/
├── __init__.py          # Exportar ModeloRelacional
├── agent.py             # Clase Agent
├── civilization.py      # Clase Civilizacion/Faccion
├── world.py             # Clase Tile, Mapa, Terreno
├──missions.py          # SistemaMisiones (mover de sistema_misiones.py)
├── history.py           # LibretaHistoria
├── economy.py           # Recursos, comercio
├── relationships.py     # Relaciones entre agentes
└── database.py          # DatabaseManager (separar del actual)
```

**Tareas:**
- [ ] Crear directorio `modelo/` y mover clases
- [ ] Actualizar todos los imports en `api.py`, `cerebro_*.py`, etc.
- [ ] Ejecutar tests (ver que nada se rompa)
- [ ] Commit: "Refactor: split modelo.py into modules"

### FEAT-1: Misiones Dinámicas
**Problema:** Solo 10 misiones predefinidas → se acaban.
**Solución:** Generar misiones según estado actual del mundo.

**Tareas:**
- [ ] En `sistema_misiones.py`, añadir método `generar_mision_dinamica(modelo)`:
  - [ ] Si hay pocos edificios → misión "construir X de tipo Y"
  - [ ] Si hay desigualdad → misión "reducir Gini"
  - [ ] Si hay conflictos → misión "lograr paz entre factions A y B"
- [ ] Añadir 5 misiones dinámicas al catálogo (se generan on-demand)
- [ ] Actualizar `desbloquear_nuevas_misiones` para incluir dinámicas
- [ ] Documentar tipos de misiones dinámicas

### FEAT-2: Recompensas Materiales
**Problema:** Misiones solo dan puntos → falta incentive económico.
**Solución:** Al completar misión, otorgar recursos/dinero a facción/agentes.

**Tareas:**
- [ ] Modificar `Mision` para incluir `recompensa_recursos: Dict[str, int]` (ej: {"dinero": 500, "recursos": 100})
- [ ] En `verificar_completada()` y `otorgar_puntos()`, también otorgar recursos a:
  - [ ] Todos los miembros de la facción del usuario
  - [ ] O solo al usuario? (decidir)
- [ ] Mostrar notificación de recompensas materiales en frontend
- [ ] Añadir log: "Misión completada! Ganaste 500 MC"

### FEAT-3: Exportar Datos a CSV
**Problema:** No se pueden analizar datos externamente.
**Solución:** Añadir endpoint `/export` o botón en UI.

**Tareas:**
- [ ] Backend: crear `GET /export/csv?user_id=X` que devuelva:
  - [ ] `agents.csv` (todos los agentes del usuario)
  - [ ] `misiones.csv` ( historial de misiones completadas)
  - [ ] `economy_timeline.csv` (dinero total por turno)
  - [ ] Todo en ZIP
- [ ] Frontend: en MissionsPanel, añadir botón "Exportar Datos"
- [ ] Al hacer clic, descargar ZIP con CSVs
- [ ] Probar export y abrir en Excel/Google Sheets

### FEAT-4: Mejorar Reconexión WebSocket
**Problema:** Si se pierde conexión, frontend se desincroniza.
**Solución:** Auto-reconnect + full sync con versionado.

**Tareas:**
- [ ] En `useGameStore`, cada mensaje WS incluye `state_version` (int incremental)
- [ ] Cliente guarda `last_version`
- [ ] Al reconectar, enviar `last_version` al servidor
- [ ] Servidor, si `current_version > last_version + 1`, enviar full state
- [ ] Implementar exponential backoff en reconnect (1s, 2s, 4s, 8s...)
- [ ] Probar: matar WebSocket y verificar que se recupera

---

## 🧪 CALIDAD ( Tests y CI )

### TEST-2: Tests de Integración API
**Objetivo:** Asegurar que endpoints funcionan.

**Tareas:**
- [ ] `tests/test_api.py`:
  - [ ] `test_login_creates_user()`
  - [ ] `test_websocket_connection()`
  - [ ] `test_create_simulation()`
  - [ ] `test_send_architect_message()`
  - [ ] `test_clear_database()`
- [ ] Usar `httpx.AsyncClient` para WebSocket tests
- [ ] Mockear DB o usar test database separada

### CI-1: GitHub Actions
**Objetivo:** Automatizar tests y lint en cada push.

**Tareas:**
- [ ] Crear `.github/workflows/ci.yml`
- [ ] Jobs:
  - [ ] `test-backend`: pytest + coverage
  - [ ] `lint-backend`: ruff/flake8
  - [ ] `test-frontend`: npm test (si hay)
  - [ ] `lint-frontend`: eslint
- [ ] Badge en README: "CI passing"

### TEST-3: Tests de Frontend
**Objetivo:** Componentes críticos funcionan.

**Tareas:**
- [ ] Instalar Jest + React Testing Library
- [ ] Tests:
  - [ ] `GamePage` redirects to /auth when not authenticated
  - [ ] `MissionsPanel` displays active missions
  - [ ] `useGameStore` login/logout works
  - [ ] `WorldViewport` renders without crash
- [ ] Coverage > 60%

---

## 🔧 MEJORAS UX/UI (baja prioridad pero útiles)

### UI-1: Configuración de Gráficos
**Problema:** No se puede ajustar calidad para hardware débil.
**Solución:** Slider en ConfigPanel: [Baja, Media, Alta] calidad.

**Tareas:**
- [ ] En `ConfigPanel.tsx`, añadir selector de calidad
- [ ] Pasar calidad a `WorldViewport3D` (ajustar antialiasing, sombras, partículas)
- [ ] Pasar calidad a `WorldViewport` 2D (resolución de canvas)
- [ ] Guardar preferencia en localStorage

### UI-2: Panel de Logs Mejorado
**Problema:** Logs pueden saturar la pantalla.
**Solución:** Limitar visualizados + filtros.

**Tareas:**
- [ ] En `GamePage`, limitar `logs` en store a últimos 100 (o 500)
- [ ] Añadir botón "Limpiar Logs"
- [ ] Añadir filtro por categoría (Sistema, Evento, Pensamiento, Error)
- [ ] Añadir search en logs (texto)

### UI-3: Tooltips Mejorados
**Problema:** Información de agentes puede ser escasa.
**Solución:** Tooltip con más datos al hover en nodo 2D/3D.

**Tareas:**
- [ ] En `WorldViewport` y `WorldViewport3D`, al hover nodo:
  - [ ] Mostrar: ID, facción, recursos, dinero, personalidad (barras), necesidades
  - [ ] Mostrar último mensaje/acción
- [ ] Estilo: panel con glassmorphism

---

## 📦 INFRAESTRUCTURA

### INFRA-1: Backup Automático de PostgreSQL
**Problema:** Si se borra contenedor DB, se pierde todo.
**Solución:** Backup diario a volumen externo o S3.

**Tareas:**
- [ ] Crear script `backup_db.sh`:
  ```bash
  #!/bin/bash
  docker-compose exec mundoia-db pg_dump -U architect mundoia > backups/mundoia_$(date +%Y%m%d_%H%M%S).sql
  compress backup
  # eliminar backups > 30 días
  find backups -name "*.sql.gz" -mtime +30 -delete
  ```
- [ ] Añadir cron en host: `0 2 * * * /path/to/backup_db.sh`
- [ ] Probar restore desde backup

### MON-1: Healthcheck Endpoint
**Problema:** No hay healthcheck para monitoreo.
**Solución:** Añadir `GET /health` en FastAPI.

**Tareas:**
- [ ] En `api.py`, añadir:
  ```python
  @app.get("/health")
  async def health():
      db_ok = db.connect() if db else False
      return {"status": "healthy" if db_ok else "unhealthy", "timestamp": datetime.utcnow()}
  ```
- [ ] Dockerfile: HEALTHCHECK usando curl a /health
- [ ] Probar: `curl http://localhost:8005/health`

---

## 🐛 BUGS CONOCIDOS (investigar y corregir)

### BUG-1: WebSocket Flood (ver WS-1 arriba, es prioridad)
### BUG-2: Memoria sin límite (ver PERF-1)
### BUG-3: LLM timeout (ver PERF-2)
### BUG-4: Reconección WS (ver FEAT-4)

** Bugs adicionales a investigar:**

- [ ] **Error en logs**: Revisar `logs/` y consola backend → buscar stack traces
- [ ] **Falta de IDs en misiones**: ver `sistema_misiones.py` → `Mision.id` ¿siempre generado?
- [ ] **Race condition**: `SessionManager` accede a `self.simulations` desde múltiples hilos → lock necesario?
- [ ] **Facciones con nombres vacíos**: Si LLM falla, `civ.nombre` puede ser None → frontend crash

---

## 📈 MÉTRICAS Y MONITOREO

### METRIC-1: Dashboard de Métricas
**Objetivo:** Tener visibilidad de performance.

**Tareas:**
- [ ] Backend: exponer `/metrics` (si usas Prometheus) o `/stats`
  - [ ] Activos usuarios conectados
  - [ ] Latencia promedio WS
  - [ ] Tiempo de turno promedio
  - [ ] LLM calls per minute
  - [ ] DB query time
- [ ] Frontend: mostrar FPS y latency en esquina (debug mode)
- [ ] Loggear métricas a archivo CSV para análisis posterior

### METRIC-2: Alertas
**Objetivo:** Saber cuando algo falla.

**Tareas:**
- [ ] Si error rate > 5% en 5 minutos → enviar email/Telegram (usar webhook de OpenClaw?)
- [ ] Si DB connection falla → alerta
- [ ] Si WebSocket disconnect masivo → alerta

---

## 📚 DOCUMENTACIÓN

### DOC-1: API Documentation
**Problema:** No hay OpenAPI/Swagger.
**Solución:** FastAPI genera automáticamente.

**Tareas:**
- [ ] Revisar que todos los endpoints tengan docstrings
- [ ] Ejecutar: `uvicorn api:app --reload --host 0.0.0.0 --port 8000`
- [ ] Visitar: http://localhost:8005/docs (debería mostrar autodoc)
- [ ] Si no aparece, añadir `from fastapi.openapi.docs import get_swagger_ui_html`
- [ ] Exportar spec: `/openapi.json` → guardar en `docs/openapi.json`

### DOC-2: Developer Guide
**Objetivo:** Facilitar contribuciones externas.

**Tareas:**
- [ ] Crear `CONTRIBUTING.md`:
  - Cómo levantar entorno (docker-compose up)
  - Cómo ejecutar tests
  - Convenciones de código (black, isort, ruff)
  - Cómo añadir nueva misión
  - Cómo modificar agentes
- [ ] Actualizar README.md con:
  - Stack tecnológico
  - Instrucciones de desarrollo
  - Link a docs/Cambios.md
  - Link a REVISION_COMPLETA_FINAL.md

---

## 🎯 PRIORIZACIÓN SUGERIDA (Orden de Ejecución)

### Esta semana (18-25 Marzo):
1. **WS-1** Delta Updates (crítico performance)
2. **DB-1** Índices PostgreSQL (crítico escalabilidad)
3. **PERF-1** Límite memoria agentes (evitar OOM)
4. **PERF-2** Timeout LLM calls (estabilidad)
5. **TEST-1** Tests unitarios misiones (calidad)

### Próximas 2 semanas:
6. **FEAT-1** Misiones dinámicas
7. **FEAT-2** Recompensas materiales
8. **FEAT-3** Exportar datos CSV
9. **FEAT-4** Reconexión WebSocket mejorada
10. **CI-1** GitHub Actions

### Mes siguiente:
11. **REFACTOR-1** Separar modelo.py
12. **TEST-2** Tests integración API
13. **TEST-3** Tests frontend
14. **UI-1** Configuración gráficos
15. **DOC-1** API docs + Developer Guide
16. **INFRA-1** Backup automático DB
17. **MON-1** Healthcheck endpoint

---

## 📝 SEGUIMIENTO

**Cómo usar este TODO:**

1. Cada tarea tiene un código único (WS-1, DB-1, etc.)
2. Cuando completes una tarea, marca `[x]` y añade comentario:
   ```markdown
   - [x] WS-1: Implementar delta updates
     > Implementado, envió tráfico reducido 92%. Probado con 50 agentes, funciona.
   ```
3. Actualiza `docs/Cambios.md` con los cambios importantes
4. Si encuentras bugs durante el desarrollo, añádelos a la sección "Bugs conocidos"

**Actualizar este archivo** cada vez que completes una tarea o cambies prioridades.

---

## 🎯 CRITERIO DE ÉXITO (para decidir si paramos de mejorar)

- ✅ WebSocket bandwidth < 10KB/s con 50 agentes
- ✅ Tiempo de carga inicial < 3s
- ✅ Simulación corre a >10 turnos/segundo
- ✅ 0 errores críticos en logs por 1 semana
- ✅ Cobertura de tests > 70%

Si cumples esto, puedes considerar el proyecto "estable" y añadir features nuevas con más confianza.

---

**Total de tareas identificadas:** 50+  
**Tareas críticas (hacer ya):** 5  
**Estado inicial:** 0% completado

---

**¡A por ello!** 🚀
