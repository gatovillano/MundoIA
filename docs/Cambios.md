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

## 23-01-26 Estabilización de Atributos y Dependencias Frontend

Corrección de errores de ejecución que impedían el inicio correcto de la simulación y el renderizado de efectos visuales.

- **Atributos de Modelo**: Corregido `AttributeError` en `ModeloRelacional` al asegurar la inicialización del atributo `civilizaciones` en el preámbulo de la clase. Esto previene fallos al cargar estados persistentes desde PostgreSQL.
- **Dependencias de Animación**: Resuelto error de "Module not found" para `canvas-confetti` en el frontend. Se forzó la instalación de la dependencia y sus tipos para asegurar que las celebraciones de misiones funcionen correctamente en el entorno de ejecución.
- **Robustez de Carga**: Verificada la consistencia de los diccionarios de estado globales durante el arranque para evitar excepciones en el broadcast de websockets.
