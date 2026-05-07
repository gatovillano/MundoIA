# 🎯 PLAN DE REFACTORIZACIÓN MUNDOIA — Fases 1-4

**Estado actual**: Proyecto funcional pero con riesgos críticos de seguridad y mantenibilidad.
**Objetivo**: Convertir MundoIA en un sistema modular, seguro y escalable.

---

## 🔴 FASE 1 — SEGURIDAD (URGENTE) — 2-3 días

### T1.1: Parche RestrictedPython en `herramientas.py` ✅ **COMPLETADO**
- **Estado**: Hecho
- **Archivo**: `systems/herramientas.py:97-142`
- **Cambio**: Reemplazado `exec()` por `compile_restricted()` con `safe_builtins`
- **Testing**: Probar que `ejecutar_codigo_seguro()` sigue funcionando con código simple

### T1.2: Unificar sistemas de Skills
**Objetivo**: Eliminar duplicación entre `herramientas.py` y `skills_manager.py`

**Subtareas**:
1. **T1.2.1**: Modificar `Agente` para que use solo `SkillManager`
   - En `agent.py`: Reemplazar `self.herramientas = HerramientasAgente()` por `self.skill_manager = SkillManager()`
   - Actualizar todas las llamadas: `self.herramientas.web_search()` → `self.skill_manager.execute_skill("web_search", ...)`
   
2. **T1.2.2**: Migrar skills de `herramientas.py` a `SkillManager`
   - Mover: `obtener_clima`, `consultar_mercado`, `web_search`, `scrapear_url`, `ejecutar_codigo_seguro`, `crear_app`
   - Convertir a formato `Skill` con `experiencia_ganada` y `efecto_necesidades`
   
3. **T1.2.3**: Eliminar clase `HerramientasAgente` (o mantener como wrapper deprecated)
   - Marcar con `@deprecated` y redirigir a `SkillManager`

**Responsable**: KogniTerm + CodeAgent  
**Estimación**: 4-6 horas  
**Riesgo**: Bajo (cambios localizados)

### T1.3: Añadir locks a `MemoriaGrafica`
**Objetivo**: Evitar race conditions en operaciones concurrentes

**Cambios**:
```python
# systems/memoria.py
import threading

class MemoriaGrafica:
    def __init__(self):
        self.grafo = nx.Graph()
        self._lock = threading.RLock()  # ← NUEVO
    
    @synchronized  # Ya usa @synchronized, verificar que proteja todo
    def registrar_interaccion(self, ...):
        with self._lock:
            # ... código actual
```

**Responsable**: KogniTerm  
**Estimación**: 1 hora  
**Riesgo**: Bajo (solo añadir lock)

---

## 🟡 FASE 2 — ARQUITECTURA (ALTA PRIORIDAD) — 1 semana

### T2.1: Partir `modelo.py` (8706 líneas) en módulos
**Objetivo**: Reducir complejidad cognitiva, mejorar testabilidad

**Estructura nueva**:
```
core/
├── modelo.py                    # ↓ 500 líneas (solo clase Modelo)
├── db/
│   ├── __init__.py
│   ├── database.py              # Clase DB (52 queries)
│   ├── models.py                # Modelos SQLAlchemy (opcional)
│   └── migrations/              # Alembic migrations
├── simulation/
│   ├── __init__.py
│   ├── world.py                 # Lógica de turnos, eventos
│   ├── factions.py              # Sistema de facciones
│   ├── missions.py              # Sistema de misiones
│   └── economics.py             # Economía (precios, mercado)
├── persistence/
│   ├── __init__.py
│   ├── agent_serializer.py      # to_dict/from_dict
│   ├── state_persister.py       # Guardar/cargar estado mundo
│   └── checkpoint_manager.py    # Checkpoints automáticos
└── entities/
    ├── agent.py                 # Ya está aquí ✅
    └── world_tile.py            # WorldTile (mover de world_system.py)
```

**Pasos**:
1. **T2.1.1**: Crear estructura de directorios
2. **T2.1.2**: Extraer `DB` class a `core/db/database.py` (buscar todas las queries)
3. **T2.1.3**: Extraer lógica de simulación a `core/simulation/world.py`
4. **T2.1.4**: Extraer persistencia a `core/persistence/`
5. **T2.1.5**: Actualizar imports en todos los archivos
6. **T2.1.6**: Testing: ejecutar simulación 100 turnos, verificar sin errores

**Responsable**: CodeAgent (refactor grande) + KogniTerm (supervisión)  
**Estimación**: 2-3 días  
**Riesgo**: Alto (romper integración). Necesita tests de regresión.

### T2.2: Refactorizar `Agente.step()` (240 líneas)
**Objetivo**: Separar responsabilidades, mejorar legibilidad

**Descomposición**:
```python
def step(self):
    """Turno principal del agente."""
    if self.descanso <= 0:
        return self._forced_rest()
    
    self._update_metabolism()          # T1: metabolismo
    self._process_critical_needs()     # T2: necesidades críticas
    
    if hasattr(self, "tick_bdi"):
        self.tick_bdi()                # T3: ciclo BDI
    
    self._tick_heartbeat()             # T4: deriva personalidad
    self._tick_social_oasis()          # T5: acción social automática
    
    # Decidir y ejecutar acción
    action = self.decide_action()
    self.execute_action(action)

def _update_metabolism(self):
    """Degradación de necesidades por turno."""
    # ... código actual _actualizar_metabolismo()
    
def _process_critical_needs(self):
    """Maneja hambre/salud crítica."""
    # ... código actual _procesar_necesidades_criticas()
    
def _tick_heartbeat(self):
    """Actualiza ritmo interno y deriva de personalidad."""
    # ... código actual heartbeat
    
def _tick_social_oasis(self):
    """Acción social proactiva (post/like/comment)."""
    # ... código actual _ejecutar_accion_social_automática + social_force_action
```

**Responsable**: CodeAgent  
**Estimación**: 3-4 horas  
**Riesgo**: Bajo (lógica sin cambios, solo reestructura)

### T2.3: Extraer `WorldSystem` a `core/world_system.py` (ya está)
**Objetivo**: Mantener world system separado (ya lo está ✅)

**Tarea**: Verificar que `WorldSystem` no dependa de `modelo.py` directamente.
- Si hay dependencias, inyectar `modelo` como parámetro (no como atributo global)

**Responsable**: KogniTerm  
**Estimación**: 1 hora  
**Riesgo**: Bajo

---

## 🟢 FASE 3 — PERFORMANCE (MEDIA) — 3-4 días

### T3.1: Indexación asíncrona de ChromaDB
**Problema**: `MemoriaPersistente.guardar_episodica()` indexa en hilo principal → pausas

**Solución**:
```python
# systems/memoria_persistente.py
from concurrent.futures import ThreadPoolExecutor

class MemoriaPersistente:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._index_queue = []
    
    def guardar_episodica(self, ...):
        # Encolar indexación
        self._executor.submit(self._indexar_async, ...)
    
    def _indexar_async(self, ...):
        # Indexación en background
        self.chroma_collection.add(...)
```

**Responsable**: CodeAgent  
**Estimación**: 4-5 horas  
**Riesgo**: Medio (concurrencia, need testing)

### T3.2: Añadir índices SQL a tablas críticas
**Análisis**: Buscar queries más frecuentes con `EXPLAIN ANALYZE`

**Índices sugeridos**:
```sql
-- agentes
CREATE INDEX idx_agentes_user_id ON agentes(user_id);
CREATE INDEX idx_agentes_grupo ON agentes(grupo_id);
CREATE INDEX idx_agentes_posicion ON agentes USING GIST (point(x, y));  -- si usan PostGIS

-- logs
CREATE INDEX idx_logs_paso ON logs_simulacion(paso_actual);
CREATE INDEX idx_logs_timestamp ON logs_simulacion(timestamp);

-- chat
CREATE INDEX idx_chat_timestamp ON chat_mensajes(timestamp_utc);

-- misiones
CREATE INDEX idx_misiones_user ON misiones(user_id);
```

**Responsable**: KogniTerm (SQL)  
**Estimación**: 1 hora  
**Riesgo**: Bajo (índices no bloqueantes en PostgreSQL)

### T3.3: Optimizar `_spawn_en_posicion_valida`
**Problema**: Búsqueda O(n²) con muchos agentes

**Solución**:
```python
class WorldSystem:
    def __init__(self):
        self.occupancy_grid = {}  # {(x,y): agent_id}
    
    def ocupar_posicion(self, x, y, agent_id):
        self.occupancy_grid[(x,y)] = agent_id
    
    def desocupar_posicion(self, x, y):
        self.occupancy_grid.pop((x,y), None)
    
    def _spawn_en_posicion_valida(self, intentos=100):
        for _ in range(intentos):
            x = random.randint(0, self.size-1)
            y = random.randint(0, self.size-1)
            if (x,y) not in self.occupancy_grid:
                return x, y
        # Fallback: expansión radial
        return self._find_empty_cell_radial()
```

**Responsable**: CodeAgent  
**Estimación**: 2-3 horas  
**Riesgo**: Bajo

### T3.4: `FastNoise` determinista
**Problema**: No reproducible entre runs

**Solución**: Inyectar generador en `WorldSystem`:
```python
class WorldSystem:
    def __init__(self, size=20, seed=None):
        self.rng = random.Random(seed)  # ← ÚNICA fuente de aleatoriedad
        self.elev_noise = FastNoise(seed_elev, rng=self.rng)
        self.moist_noise = FastNoise(seed_moist, rng=self.rng)

class FastNoise:
    def __init__(self, seed=None, rng=None):
        self.rand = rng or random.Random(seed)
```

**Responsable**: CodeAgent  
**Estimación**: 1-2 horas  
**Riesgo**: Bajo

---

## 🔵 FASE 4 — CALIDAD & UX (BAJA) — 2-3 días

### T4.1: Mejorar búsqueda de memoria
**Objetivo**: Scoring híbrido configurable

**Implementar**:
```python
class MemoriaPersistente:
    def buscar(
        self,
        query: str,
        agent_id: str,
        weights: Dict[str, float] = None  # {"vector": 0.6, "recencia": 0.2, "importancia": 0.2}
    ):
        # ... lógica actual
        # combo_score = (w1*vector_score + w2*recencia_score + w3*importancia_score)
```

**Responsable**: CodeAgent  
**Estimación**: 3-4 horas  
**Riesgo**: Bajo

### T4.2: TTL automático para conversaciones
**Objetivo**: Limpiar conversaciones inactivas cada N turnos

**Implementar**:
```python
class GestorConversaciones:
    def tick(self, current_turn):
        if current_turn % 100 == 0:
            self.cerrar_inactivas(max_inactividad=50)
```

**Responsable**: CodeAgent  
**Estimación**: 1-2 horas  
**Riesgo**: Bajo

### T4.3: Fusionar social OASIS
**Objetivo**: Unificar `social_force_action` y `_ejecutar_accion_social_automática`

**Nueva estructura**:
```python
def _tick_social_oasis(self, turno):
    """Acción social proactiva unificada."""
    recsys = self.modelo.social_recsys
    if not recsys: return
    
    # Decidir: crear contenido o interactuar
    if self.necesidades_intelectuales.get("expresion", 0) > 6:
        self._crear_contenido_social(turno)
    else:
        self._interactuar_socialmente(turno)
```

**Responsable**: CodeAgent  
**Estimación**: 2-3 horas  
**Riesgo**: Medio (cambia comportamiento social)

### T4.4: Ajustar umbrales de leyendas
**Objetivo**: Más leyendas activas (más dinámica)

**Cambios en `cronicas.py:detectar_leyenda()`**:
```python
# ANTES
if resonancia < 0.7: return None
if num_respuestas < 3: return None
if num_menciones < 5: return None

# DESPUÉS
if resonancia < 0.5: return None        # ↓ 0.7 → 0.5
if num_respuestas < 2: return None      # ↓ 3 → 2
if num_menciones < 3: return None       # ↓ 5 → 3
```

**Responsable**: KogniTerm  
**Estimación**: 30 min  
**Riesgo**: Bajo

### T4.5: Contexto de crónicas personalizado
**Objetivo**: Filtrar crónicas por intereses/facción del agente

**Implementar**:
```python
def obtener_contexto_cronicas(self, agente_id, max_items=5):
    agente = self.modelo.get_agente(agente_id)
    intereses = agente.identidad.intereses if agente.identidad else []
    # Filtrar crónicas por tags que coincidan con intereses
    return [c for c in crónicas_recientes if any(tag in intereses for tag in c.tags)][:max_items]
```

**Responsable**: CodeAgent  
**Estimación**: 2 horas  
**Riesgo**: Bajo

---

## 📊 MÉTRICAS DE ÉXITO

### Seguridad
- [ ] `ejecutar_codigo_seguro` no permite `import os`, `open()`, `eval()`
- [ ] Tests de intrusión: código malicioso bloqueado
- [ ] Lock en `MemoriaGrafica` previene race conditions (test multithread)

### Mantenibilidad
- [ ] `modelo.py` reducido a < 600 líneas
- [ ] `Agente.step()` < 80 líneas
- [ ] Cobertura de tests > 60% (añadir tests unitarios)

### Performance
- [ ] Indexación ChromaDB no bloquea turno (< 50ms overhead)
- [ ] Queries DB con índices: < 10ms promedio
- [ ] Spawn de 100 agentes: < 2 segundos

### Calidad
- [ ] Búsqueda de memoria: relevancia > 80% (eval manual)
- [ ] Conversaciones inactivas se cierran automáticamente
- [ ] Leyendas activas: al menos 3 simultáneas en simulación de 500 turnos

---

## 🚀 ROADMAP DE EJECUCIÓN

### Semana 1 (Urgente)
- **Día 1-2**: FASE 1 completa (seguridad)
- **Día 3**: T2.1.1 — Preparar estructura de directorios
- **Día 4-5**: T2.1.2 — Extraer DB class

### Semana 2 (Arquitectura)
- **Día 1-2**: T2.1.3 — Extraer simulation world
- **Día 3**: T2.1.4 — Extraer persistence
- **Día 4-5**: T2.1.5 — Actualizar imports + testing básico

### Semana 3 (Refinamiento)
- **Día 1**: T2.2 — Refactorizar `Agente.step()`
- **Día 2**: T2.3 — Verificar `WorldSystem` independiente
- **Día 3-4**: T3.1 — Indexación asíncrona ChromaDB
- **Día 5**: T3.2 — Añadir índices SQL

### Semana 4 (Performance & Calidad)
- **Día 1**: T3.3 — Spawn optimizado
- **Día 2**: T3.4 — FastNoise determinista
- **Día 3-4**: T4.1-T4.3 — Mejoras UX
- **Día 5**: T4.4-T4.5 — Ajustes finales + testing integral

---

## 📝 NOTAS DE IMPLEMENTACIÓN

### Para CodeAgent (refactor grandes):
1. **Siempre hacer backup**: `git branch backup/{fecha}`
2. **Commit incremental**: cada subtarea completada
3. **Tests after each change**: ejecutar `python -m pytest` o simulación de prueba
4. **No romper API pública**: si algo se mueve, mantener imports compatibles (re-export)

### Para KogniTerm (supervisión):
1. **Code review** de cada cambio
2. **Actualizar llm_context.md** con decisiones
3. **Verificar integridad** después de cada fase
4. **Documentar** nuevas estructuras en `/docs/`

### Riesgos y contingencias:
| Riesgo | Mitigación |
|--------|------------|
| Romper simulación | Tener script `test_simulation.py` que ejecute 10 turnos sin errores |
| DB queries rotas | Loggear todas las queries, verificar con `EXPLAIN` |
| Skills rotos | Mantener compatibility layer en `SkillManager` por 1 semana |
| Concurrencia issues | Añadir logs detallados en locks, test con 10 hilos |

---

## 🎯 SIGUIENTE PASO INMEDIATO

**HOY**: Completar **FASE 1.2** (Unificar skills)
1. Añadir `SkillManager` a `Agente.__init__`
2. Migrar 6 skills de `herramientas.py` a `SkillManager`
3. Actualizar llamadas en `agent.py`
4. Probar que todo funciona

¿Quieres que proceda con **T1.2.1** (integrar SkillManager en Agente) ahora?
