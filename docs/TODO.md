# TODO - MundoIA (Simulación Multiagente)
**Prioridad:** Media - Proyecto de investigación
**Fecha:** 2026-03-18

---

## 🎯 Estado General
Simulación multiagente con dashboard interactivo funcional. Agentes con personalidades, recursos, relaciones sociales, formación de grupos, visualización con Three.js/cytoscape. Necesita mejoras en métricas, persistencia y documentation.

---

## 📌 Fase 1: Evaluación Actual

### 1.1 Probar Funcionamiento
- [ ] Levantar servidor: `python api.py` (¿o hay docker-compose?)
- [ ] Abrir dashboard: http://localhost:puerto
- [ ] Verificar:
  - [ ] Red de agentes se visualiza correctamente
  - [ ] Nodos se mueven/colapsan apropiadamente
  - [ ] Logs aparecen en tiempo real
  - [ ] Controles (pausa, velocidad) funcionan
  - [ ] Click en nodo abre panel de detalles
  - [ ] Métricas (stats, gráficos) se actualizan

### 1.2 Revisar Código
- [ ] Leer `docs/Cambios.md` - últimas modificaciones
- [ ] Leer `docs/mejoras_grupos_misiones_puntaje.md` - mejoras planificadas
- [ ] Revisar `modelo.py` - lógica de agentes y simulación
- [ ] Revisar `api.py` - endpoints WebSocket y REST
- [ ] Revisar `frontend/` - estructura del código frontend

---

## 📌 Fase 2: Mejoras Identificadas (de `mejoras_grupos_misiones_puntaje.md`)

**Objetivo:** Implementar mejoras planificadas (misiones, puntuación, grupos).

- [ ] **Sistema de Misiones:**
  - [ ] Definir tipos de misiones (ej: recolectar recursos, formar alianzas, conquistar)
  - [ ] Asignar misiones a agentes o grupos
  - [ ] tracking de progreso de misión
  - [ ] Recompensas (recursos, relaciones)
  - [ ] UI para mostrar misiones activas

- [ ] **Puntuación y Ranking:**
  - [ ] Calcular puntuación por agente (ej: recursos × influencia social)
  - [ ] Ranking global de agentes
  - [ ] Mostrar en dashboard (tabla o leaderboard)
  - [ ] Histórico de puntuaciones a lo largo del tiempo

- [ ] **Mejoras de Grupos:**
  - [ ] Jerarquías dentro de grupos (líder, miembros)
  - [ ] Roles (explorador, guardián, recolector)
  - [ ] Comportamiento cooperativo dentro del grupo
  - [ ] Conflictos internos (opcional)

- [ ] **Puntaje Social:**
  - [ ] Calcular "poder social" de cada agente (centralidad, conexiones)
  - [ ] Mostrar en panel de detalles

---

## 📌 Fase 3: Persistencia y Exportación

- [ ] **Guardar estado de simulación:**
  - [ ] Poder pausar y guardar (JSON: todos los agentes, relaciones, recursos, grupos)
  - [ ] Cargar estado guardado (continuar simulación desde punto)
  - [ ] Versionado de estados (v1, v2...)

- [ ] **Exportar datos:**
  - [ ] Exportar logs a CSV/JSON (para análisis en pandas/R)
  - [ ] Exportar gráfico de red en formato GraphML/JSON (para Gephi/Neo4j)
  - [ ] Exportar time series de métricas (amistades, grupos, recursos)

- [ ] **Reproducibilidad:**
  - [ ] Semilla aleatoria configurable (para experiments)
  - [ ] Guardar semilla con el estado

---

## 📌 Fase 4: Métricas Avanzadas

- [ ] **Métricas Sociales:**
  - [ ] Coeficiente de聚类 (¿qué tan agrupados están?)
  - [ ] Gini de recursos (desigualdad)
  - [ ] Centralidad de nodos (betweenness, closeness)
  - [ ] Modularidad (calidad de grupos)

- [ ] **Métricas de Comportamiento:**
  - [ ] Tasa de cooperación vs conflicto
  - [ ] Tiempo promedio para formar grupo
  - [ ] Supervivencia de agentes a lo largo del tiempo
  - [ ] Migración entre grupos

- [ ] **Gráficos:**
  - [ ] Histograma de recursos por grupo
  - [ ] Evolución de cada necesidad (alimento, seguridad, social) en heatmap
  - [ ] Red de interacciones (quién interactúa con quién)

---

## 📌 Fase 5: Mejoras de Performance

- [ ] **Optimización de simulación:**
  - [ ] Usar numpy arrays en lugar de listas Python para cálculos masivos
  - [ ] Paralelizar cálculos de interacciones (multiprocessing)
  - [ ] Límite de FPS en visualización (no recalcular cada frame si no hay cambios)

- [ ] **Escalabilidad:**
  - [ ] Probar con 100 agentes → ¿performance aceptable?
  - [ ] Probar con 500 agentes
  - [ ] Probar con 1000 agentes
  - [ ] Si se ralentiza: implementar spatial hashing para colisiones/influencia

- [ ] **WebSocket:**
  - [ ] Enviar solo datos cambiados (diffs) en lugar de estado completo
  - [ ] Comprimir datos (binary format: MessagePack?)

---

## 📌 Fase 6: Configurabilidad

- [ ] **Archivo de configuración YAML/JSON:**
  ```yaml
  agents:
    count: 50
    initial_resources: 100
    personality_ranges:
      extroversion: [0, 100]
      agreeableness: [0, 100]
      competitiveness: [0, 100]
  simulation:
    step_interval_ms: 100
    max_steps: 0  # 0 = infinite
  groups:
    min_size: 2
    cohesion_threshold: 0.7
  resources:
    types: [food, safety, social]
    decay_rate: 0.01
  ```

- [ ] CLI arguments para `api.py`:
  - `--config config.yaml`
  - `--agents 100`
  - `--speed 2x`
  - `--headless` (sin UI, solo logs)

- [ ] UI para configurar parámetros en caliente (sliders, inputs)

---

## 📌 Fase 7: Tipos de Agentes y Especialización

- [ ] **Diferentes roles:**
  - [ ] Explorador (busca recursos, mapea territories)
  - [ ] recolector (obtiene recursos)
  - [ ] Guerrero (defiende, ataca)
  - [ ] diplomático (negocia alianzas)
  - [ ] Líder (atrae seguidores, decide por grupo)

- [ ] **Habilidades:**
  - [ ] Cada agente tiene skills levels (búsqueda, combate, persuasión)
  - [ ] Las habilidades mejoran con la práctica
  - [ ] Las habilidades afectan resultados de acciones

---

## 📌 Fase 8: Interacciones más Complejas

- [ ] **Comercio:**
  - [ ] Agentes pueden intercambiar recursos
  - [ ] Precios dinámicos (oferta/demanda)
  - [ ] Mercado centralizado o P2P

- [ ] **Comunicación:**
  - [ ] Mensajes entre agentes (chat simulado)
  - [ ] Propagación de información (chismes)
  - [ ] Mentiras/desinformación

- [ ] **Objetivos:**
  - [ ] Agentes pueden tener metas personales
  - [ ] Pueden formar planes colaborativos
  - [ ] Poder usar herramientas simbólicas (ej: "map" del territorio)

---

## 📌 Fase 9: Documentación

- [ ] **README.md** actualizado:
  - Descripción clara del proyecto
  - Instrucciones para levantar (`python api.py` o `docker-compose up`)
  - Variables de entorno necesarias (si hay)
  - Ejemplo de uso
  - Links a documentación

- [ ] **docs/architecture.md**:
  - Diagrama de componentes
  - Flujo de datos (frontend → API → simulación)
  - Estructura de clases (Agent, Group, Resource)

- [ ] **docs/configuration.md**:
  - Todos los parámetros configurables
  - Ejemplo de `config.yaml` completo
  - Efecto de cada parámetro en la simulación

- [ ] **docs/development.md**:
  - Cómo añadir nuevo tipo de agente
  - Cómo añadir nueva acción
  - Cómo modificar visualización

- [ ] **Jupyter Notebook** para análisis de resultados:
  - Cargar datos exportados
  - Graficar métricas
  - Comparar diferentes configuraciones

---

## 📌 Fase 10: Tests Automatizados

- [ ] Tests unitarios del `modelo.py`:
  - [ ] Inicialización de agentes
  - [ ] Cálculo de necesidades
  - [ ] Formación de grupos
  - [ ] Resolución de conflictos

- [ ] Tests de la API:
  - [ ] Conexión WebSocket
  - [ ] Endpoint de configuración
  - [ ] Endpoint de estado

- [ ] Tests de frontend (con Jest/React Testing Library):
  - [ ] Componentes renderizan correctamente
  - [ ] Simulación de clicks en nodos
  - [ ] Actualización de stats

---

## 📊 Métricas de Éxito

- [ ] Simulación estable a 60 FPS con 100 agentes
- [ ] Dashboard responsivo (<200ms de latencia WebSocket)
- [ ] Código cubierto por tests > 70%
- [ ] Documentación completa (README + 3 doc files)
- [ ] Configuración reproducible (config.yaml funcional)

---

## 🐛 Problemas Conocidos

- [ ] Si la red es muy densa, performance cae → implementar spatial partitioning
- [ ] Si muchos agentes en grupos grandes, visualización se satura → colapsar grupos?
- [ ] WebSocket se desconecta en simulaciones largas → heartbeat/reconnect

---

## 🔄 Próximos Pasos Inmediatos

1. [ ] Probar simulación actual (¿es divertida/educativa?)
2. [ ] Identificar 1-2 mejoras de `mejoras_grupos_misiones_puntaje.md` para implementar YA
3. [ ] Añadir exportación de datos (aunque sea CSV simple)
4. [ ] Escribir tests básicos de modelo
5. [ ] Hacer benchmarks de performance (agent count vs FPS)

---

**Notas:**
- Este es un proyecto de investigación/experimento → la iteración rápida es clave
- Probar diferentes parámetros y observar resultados
- Considerar publicar resultados (paper, blog post)

---

**Próxima revisión:** 2026-03-25

**Completadas:**
- [ ]
