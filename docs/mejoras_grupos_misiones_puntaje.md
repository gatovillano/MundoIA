# Mejoras al Sistema de Grupos, Misiones y Puntaje

## Fecha: 20-01-2026

## Solicitud del Usuario

Mejorar tres sistemas principales:

1. **Sistema de Grupos**: Los agentes deben nombrar sus propias facciones
2. **Sistema de Misiones**: Misiones preestablecidas con objetivos medibles
3. **Sistema de Puntaje**: Puntos por completar misiones (preparación multiusuario)

## Solución Propuesta

### 1. Sistema de Misiones Mejorado ✅

- **Archivo**: `sistema_misiones.py`
- **Características**:
  - 10 misiones preestablecidas de diferentes dificultades
  - Objetivos medibles automáticamente
  - Sistema de progresión (desbloqueo de misiones)
  - Recompensas en puntos
  - Verificación automática de completado

**Misiones Implementadas**:

1. Primeros Pasos (100 pts) - Construir primer edificio
2. Ciudad Saludable (500 pts) - 3 Hospitales
3. Granero Mundial (500 pts) - 5 Granjas
4. Metrópolis (750 pts) - 50 agentes
5. Naciones Unidas (1000 pts) - 5 facciones
6. Prosperidad (1500 pts) - 10,000 MundoCoins
7. Democracia (1200 pts) - 10 leyes aprobadas
8. Diálogo Global (800 pts) - 5 asambleas completadas
9. Imperio (3000 pts) - 100 agentes
10. Utopía (5000 pts) - 30 edificios totales

### 2. Sistema de Puntaje de Usuario ✅

- **Características**:
  - Puntos acumulativos por misión completada
  - Ranking de usuarios
  - Preparado para multiusuario
  - Persistencia en el estado del juego

### 3. Sistema de Grupos Mejorado 🔄

**Cambios Pendientes**:

- Los agentes deben poder nombrar sus facciones al crearlas
- Usar LLM para generar nombres creativos basados en:
  - Personalidad del líder
  - Objetivo del grupo
  - Contexto del mundo

### 4. Componente de Animación 🔄

**Pendiente**: Crear componente React para celebrar misiones completadas

- Animación de confeti
- Notificación con puntos ganados
- Sonido de celebración

## Estado Actual

- ✅ Sistema de misiones creado
- 🔄 Integración con modelo.py
- 🔄 Mejora de nombres de grupos
- 🔄 Componente de animación frontend
- 🔄 Actualización de API para enviar eventos de misiones

## Próximos Pasos

1. Integrar `SistemaMisiones` en `modelo.py`
2. Modificar creación de grupos para que agentes los nombren
3. Crear componente `MissionCompleteAnimation.tsx`
4. Actualizar API para enviar eventos de misiones completadas
5. Probar y registrar cambios en `docs/Cambios.md`
