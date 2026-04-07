# Memoria Contextual del Proyecto


## 🎨 Actualizaciones Frontend WebSocket - Campos BDI/MundoVivo

**Fecha:** Sesión actual
**Archivos modificados:** `index.html`

### Cambios realizados:

1. **`handleInitialState()`** - Extendido para incluir nuevos campos:
   - `tratados`, `reputacion`, `profesion`, `experiencia`
   - `beliefs`, `desires`, `intentions` (BDI)
   - `identidad`, `memoria_persistente_data`, `alma_estado`
   - `heartbeat_config`, `cronicas_publicadas`

2. **`updateAgentState()`** - Sincronización incremental añadida para todos los campos nuevos BDI/MundoVivo

3. **`showAgentDetail()`** - Nuevas secciones de UI renderizadas:
   - 🧠 **Creencias (Beliefs)**: Muestra key-value con porcentajes
   - 🎯 **Deseos (Desires)**: Muestra objetivos con valores numéricos
   - ⚡ **Intenciones (Intentions)**: Lista de acciones planificadas
   - 🪪 **Identidad**: Nombre, arquetipo, valores
   - ✨ **Estado del Alma**: Métricas emocionales/espirituales
   - 📜 **Crónicas Publicadas**: Últimas 5 crónicas con scroll

### Estado: ✅ Completado - Listo para pruebas de integración

## ✅ Payload BDI sincronizado Backend ↔ Frontend

**Fecha:** 2025-01-09
**Archivos modificados:** `api.py` (líneas ~398-407)
**Campos añadidos al WebSocket:**
- `creencias`: SistemaCreencias.to_dict() → {proposicion: {probabilidad, fuerza, fuente, ultimo_update}}
- `deseos`: SistemaDeseos.to_dict() → {deseos: {...}, pesos: {...}}
- `intenciones`: SistemaIntenciones.to_dict() → {plan_actual: {...}, historial_planes: [...]}
- `identidad`: MundoVivo (opcional)
- `alma_estado`: MundoVivo (opcional)
- `cronicas_publicadas`: Lista de crónicas publicadas

**Validado:** Estructura Python coincide con TypeScript `agent.d.ts` y renderizado en `AgentSidebar.tsx`
