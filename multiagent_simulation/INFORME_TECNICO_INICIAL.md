# 📊 Informe Técnico Inicial: Sistema de Simulación Multiagente (MundoIA)

## 1. Resumen Ejecutivo
El proyecto **MundoIA** es una simulación social avanzada basada en agentes autónomos impulsados por Inteligencia Artificial (LLMs). Los agentes interactúan en un mundo virtual con recursos, necesidades y dinámicas sociales complejas, utilizando un modelo cognitivo **BDI (Belief-Desire-Intention)** para tomar decisiones, planificar y evolucionar.

## 2. Arquitectura del Sistema
El sistema se organiza en varios módulos clave que definen el ciclo de vida y comportamiento de los agentes:

- **`modelo.py`**: Motor central de la simulación. Gestiona el mapa, el tiempo, las facciones y el ciclo de actualización de los agentes.
- **`cerebro_langgraph.py`**: Implementación del flujo de decisión del agente usando LangGraph. Define los nodos de análisis, actuación, ejecución de herramientas y comunicación.
- **`cerebro_llm.py`**: Interfaz con los Modelos de Lenguaje (LLMs). Gestiona la generación de respuestas, fallback contextuales y rate limiting.
- **`bdi_components.py`**: Estructuras de datos para el modelo BDI (Creencias, Deseos, Intenciones).
- **`memoria.py`**: Sistema de memoria gráfica (NetworkX) para representar relaciones sociales y conocimiento del entorno.
- **`alma.py`**: Sistema de evolución interna del agente (experiencias, epifanías, crecimiento personal).
- **`identity_system.py`**: Generación y gestión de identidades únicas (nombres, arquetipos, especies).
- **`skills_manager.py`**: Gestor de habilidades, permitiendo a los agentes ejecutar código Python de forma segura.

## 3. Modelo Cognitivo BDI
Cada agente posee una arquitectura cognitiva inspirada en el modelo BDI:
- **Creencias (Beliefs):** Representan lo que el agente sabe sobre el mundo (ej. "A1 es hostil", "Hay comida al norte"). Se actualizan mediante observación y testimonios.
- **Deseos (Desires):** Objetivos motivacionales con intensidad dinámica (Supervivencia, Estatus, Recursos, Armonía, Conocimiento, etc.).
- **Intenciones (Intentions):** Planes de acción concretos que el agente se compromete a ejecutar para satisfacer sus deseos.

## 4. Sistema de Identidad y Personalidad
- **Identidad Dinámica:** Los agentes no son entidades genéricas. Tienen nombres, emojis, especies y "vibes" generados proceduralmente basados en arquetipos (Explorador, Guerrero, Sabio, etc.).
- **Personalidad:** Rasgos como Amabilidad, Hostilidad, Curiosidad y Competitividad influyen en las decisiones y el tono de las interacciones.

## 5. Ejecución de Habilidades (Skills)
- **Entorno Seguro:** Las habilidades se ejecutan en un sandbox usando `RestrictedPython` para evitar código malicioso.
- **Creación de Skills:** Los agentes pueden aprender o crear nuevas habilidades (`crear_habilidad`), expandiendo su repertorio de acciones.
- **Habilidades Base:** Incluyen `web_search`, `comerciar`, `cultivar`, `reflexionar`, entre otras.

## 6. Interacción y Comunicación
- **Conversaciones Persistentes:** Sistema de historial de mensajes que permite diálogos profundos y coherentes a lo largo del tiempo.
- **Asambleas y Votaciones:** Mecanismos para la formación de grupos y toma de decisiones colectivas.
- **Intervención del Arquitecto:** El usuario puede intervenir directamente en la simulación mediante mensajes globales o posesión de agentes.

## 7. Estado Actual y Próximos Pasos
- **Estado:** ✅ **Código Completo y Estructurado.** El sistema cuenta con todos los módulos necesarios para una simulación funcional.
- **Pendiente:**
  - 🚀 Ejecutar la primera simulación de prueba.
  - 🧪 Implementar tests unitarios para los componentes BDI.
  - 📈 Optimizar el consumo de tokens del LLM.
  - 🎨 Integrar una interfaz visual para monitoreo en tiempo real.

---
*Generado por el Agente de Sistemas (BashAgent) - KogniTerm*