## 14-01-26 Capacidad de Construcción para Agentes

Se ha implementado la capacidad para que los agentes construyan infraestructuras (Hospitales, Comedores, Centros de Ocio) que afectan positivamente sus necesidades y las de su facción.

- **Punto 1**: Modificación de `modelo.py` para incluir el sistema de infraestructuras y efectos pasivos por turno.
- **Punto 2**: Actualización de `cerebro_langgraph.py` para que los agentes tomen decisiones de construcción basadas en necesidades y recursos.
- **Punto 3**: Ajuste de `api.py` para transmitir los datos de infraestructura al frontend.
- **Punto 4**: Reorganización del constructor de `ModeloRelacional` para mejorar la estabilidad y evitar errores de inicialización.
- **Punto 5**: Creación de script de prueba `test_construccion.py` para validación técnica.
