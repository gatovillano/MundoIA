## 14-01-26 Capacidad de Construcción para Agentes

Se ha implementado la capacidad para que los agentes construyan infraestructuras (Hospitales, Comedores, Centros de Ocio) que afectan positivamente sus necesidades y las de su facción.

- **Punto 1**: Modificación de `modelo.py` para incluir el sistema de infraestructuras y efectos pasivos por turno.
- **Punto 2**: Actualización de `cerebro_langgraph.py` para que los agentes tomen decisiones de construcción basadas en necesidades y recursos.
- **Punto 3**: Ajuste de `api.py` para transmitir los datos de infraestructura al frontend.
- **Punto 4**: Reorganización del constructor de `ModeloRelacional` para mejorar la estabilidad y evitar errores de inicialización.
- **Punto 5**: Creación de script de prueba `test_construccion.py` para validación técnica.

---

## 14-01-26 Implementación de Territorios y Civilizaciones

Se ha introducido un sistema de territorios y civilizaciones donde cada usuario gestiona una facción. Los agentes ahora tienen ubicación espacial y pueden expandir la influencia de su civilización.

- **Punto 1**: Implementación de la clase `Civilizacion` y un mapa de rejilla 20x20 en `modelo.py`.
- **Punto 2**: Actualización de los agentes con coordenadas `x`, `y` y la acción `MOVER` para exploración territorial.
- **Punto 3**: Creación de tablas `usuarios` y `civilizaciones` en PostgreSQL para persistencia multi-usuario.
- **Punto 4**: Desarrollo de endpoints de autenticación (`/auth/register`, `/auth/login`) y creación de civilizaciones en `api.py`.
- **Punto 5**: Actualización del frontend con `SimulationView` (mapa de territorios) y `AuthModal` para el onboarding de usuarios.
- **Punto 6**: Integración de conciencia espacial en el cerebro de los agentes (`cerebro_langgraph.py`).

---

## 14-01-26 Expansión del Mundo: Mapa Dinámico y Clima

Se ha implementado un sistema de mapa dinámico basado en tiles, un ciclo de clima variable y mejoras en la construcción y recolección.

- **Punto 1**: Implementación de clases `Tile`, `TerrainType` y `WeatherType` en `modelo.py`.
- **Punto 2**: Generación procedural de mapa con diferentes terrenos y recursos.
- **Punto 3**: Sistema de clima dinámico que afecta el movimiento de los agentes.
- **Punto 4**: Actualización de la lógica de agentes para interactuar con el terreno (bloqueo por agua) y construir en tiles específicos.
- **Punto 5**: Nuevo componente frontend `WorldMap` para visualizar el terreno, edificios y clima.
- **Punto 6**: Integración de datos de mapa y clima en la API WebSocket.
