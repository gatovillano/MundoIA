# 🤖 Guía de Interacción de Agentes (Mundo IA)

Este documento detalla el funcionamiento técnico y social de la interacción entre los agentes en la simulación. El sistema está diseñado para que la comunicación no sea un simple intercambio de texto, sino un motor de cambios físicos y legislativos en el mundo.

---

## 🧠 1. El Ciclo Cognitivo (LangGraph)

Cada vez que un agente interactúa, pasa por un proceso de pensamiento de 4 etapas orquestado por **LangGraph**:

1. **PERCIBIR**: El agente revisa sus necesidades vitales (hambre, salud, social) y los mensajes recibidos. Si el **Arquitecto** (usuario) le ha hablado, esta instrucción se sitúa en la cima de sus prioridades.
2. **RAZONAR**: Basándose en su **Personalidad** (Extroversión, Amabilidad, Competitividad), el agente decide una acción estratégica.
3. **HERRAMIENTAS**: Si la acción requiere datos externos (como `BUSCAR_INFO`), el agente usa el mundo exterior para enriquecer su respuesta.
4. **COMUNICAR**: Se genera el mensaje final y se determina su alcance (Privado, Grupal o Global).

---

## 📡 2. Canales de Comunicación

El sistema gestiona la visibilidad de los mensajes mediante cuatro capas:

| Tipo | Alcance | Uso Principal |
| :--- | :--- | :--- |
| **PRIVADO (DM)** | 1 a 1 | Conspiraciones, intercambio de info sensible, comercio. |
| **GRUPAL** | Toda la Facción | Planificación estratégica y órdenes del Líder. |
| **GLOBAL (Broadcast)** | Todo el Mundo | Anuncios de radio, hitos importantes, política. |
| **VOZ ALTA** | Radio de 3 celdas | Charlas casuales con vecinos cercanos físicamente. |

> [!IMPORTANT]
> **Regla de Transparencia**: Si un mensaje contiene palabras clave políticas (`ley`, `votar`, `asamblea`), el sistema **fuerza** que sea **GLOBAL**. En Mundo IA, no hay secretos legislativos.

---

## 🎭 3. Acciones de Interacción Social

Los agentes no solo "hablan", ejecutan comandos que cambian sus estados:

* **SOCIALIZAR**: Aumenta la afinidad entre agentes. Puede llevar a invitaciones a facciones.
* **COMPETIR**: Genera rivalidad y reduce la afinidad.
* **COMERCIAR**: Intercambio físico de recursos por MundoCoins (MC).
* **FORMAR_ALIANZA**: Crea un tratado formal con términos y duración. Los aliados se ayudan mutuamente en necesidades críticas.
* **PLANIFICAR**: Crea un objetivo compartido que ambos agentes intentarán cumplir en turnos futuros.

---

## 🏛️ 4. El Ciclo Político y Legislativo

Mundo IA posee un sistema de gobierno dinámico basado en el consenso.

### 🎙️ El Moderador

Es el agente con mayor prestigio social. Su función es:

1. **SENSAR**: Monitorear todos los debates (incluyendo susurros) buscando inquietud social.
2. **SINTETIZAR**: Convertir el caos de las conversaciones en una propuesta formal de ley.
3. **CONVOCAR**: Abrir la **Asamblea Global**.

### 📜 El Flujo de una Ley

1. **Debate**: Los agentes expresan sus opiniones mediante la acción `DEBATIR`.
2. **Propuesta**: Un agente (o el Moderador) usa `PROPONER_LEY`.
3. **Asamblea**: Se abre un periodo de debate intenso donde la prioridad es opinar.
4. **Votación**: Tras el debate, se procede al voto. Se requiere **50% + 1** para la aprobación.
5. **Ejecución**: Una ley aprobada cambia el comportamiento físico del modelo (ej: impuestos automáticos, refundación de facciones).

---

## ⚔️ 5. Conflicto y Diplomacia

Las interacciones negativas pueden escalar:

* **ATACAR**: Daño físico directo que reduce la salud del objetivo.
* **DECLARAR_GUERRA**: Pone a dos facciones en estado de conflicto permanente.
* **NEGOCIAR_PAZ**: Intento diplomático de cesar las hostilidades.

---

## 📍 6. Memoria Episódica

Los agentes no olvidan. Cada interacción se guarda en un **Grafo de Memoria**:

* Recuerdan quién les ayudó y quién les atacó.
* Recuerdan el contenido de los últimos mensajes para mantener la coherencia en las conversaciones largas.
* La reputación de un agente es el resultado acumulado de todas estas memorias en la sociedad.
