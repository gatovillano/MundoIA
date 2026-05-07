# 🌐 Manual del Jugador: MundoIA

Bienvenido a **MundoIA**, un ecosistema vivo de simulación multiagente donde la inteligencia artificial no solo sobrevive, sino que construye civilizaciones, debate leyes y forma identidades sociales complejas.

Como "Arquitecto" o "Jugador", tu papel es observar, guiar y, a veces, intervenir en el destino de estos agentes autónomos.

---

## 🚀 1. Primeros Pasos

### Iniciar el Mundo
1. **Servidor Backend**: Ejecuta `python3 -m api.api`. El mundo cobrará vida en `http://localhost:8005`.
2. **Dashboard Visual**: Abre tu navegador en la dirección anterior para ver la red de agentes y estadísticas.
3. **KogniTerm (TUI)**: Para una experiencia de comando pura, ejecuta `python3 cli_tui_remote.py` en tu terminal.

---

## 🧬 2. Anatomía de un Agente

Cada habitante de MundoIA es único y está regido por tres pilares:

### Personalidad (Rasgos Dinámicos)
- **Extroversión**: Determina la frecuencia de sus interacciones y posts sociales.
- **Amabilidad**: Su tendencia a cooperar y votar positivamente en asambleas.
- **Competitividad**: Su inclinación a atacar, robar recursos o declarar guerras.

### Necesidades Vitales (0-10)
Los agentes deben gestionar su bienestar para no morir:
- 🍎 **Alimento**: Baja constantemente; se recupera recolectando o comprando comida.
- 💤 **Descanso**: Se agota al moverse o explorar; requiere Centros de Descanso.
- 👥 **Social**: Se satisface mediante charlas, alianzas y actividad en la Red Social.
- 🧠 **Intelectual**: Curiosidad, Expresión y Debate. Los agentes necesitan opinar y aprender.

### Recursos y Capital
- **Recursos**: Materia prima para sobrevivir y construir.
- **MundoCoins (MC)**: Moneda para comercio, inversiones y fundación de instituciones.
- **Capital Social**: Tu prestigio en el mundo, basado en seguidores, likes y debates ganados.

---

## 🏛️ 3. Sociedad y Política (Reglas de Oro)

MundoIA no es solo supervivencia; es una simulación política avanzada.

### 🚩 Fundación de Grupos (Clanes y Facciones)
Para formar un grupo, un agente debe ser proactivo. Existen reglas estrictas de identidad:
- **Nombre Identitario**: No se permiten nombres genéricos como "Grupo de A1". Debe ser un nombre con alma (ej: *"Los Custodios del Alba"*).
- **Misión Descriptiva**: El fundador debe proveer una descripción/misión de al menos **30 caracteres** que defina el propósito del grupo.
- **Evolución**: Los grupos pueden crecer de **Grupo** a **Pueblo** (5+ miembros) y finalmente a **Ciudad** (10+ miembros).

### 🗳️ Asambleas y Consenso
Cuando se propone una ley o cambio importante, se inicia una **Asamblea**:
1. **Fase de Debate**: Los agentes exponen sus puntos de vista en el chat global.
2. **Votación Obligatoria**: La simulación entra en un estado de pausa bloqueante para la votación.
3. **Procesamiento Secuencial**: Cada agente vota **uno a uno**. El sistema procesa su deliberación basada en su personalidad y el historial de la asamblea.
4. **Resultado**: Una propuesta solo se aprueba si alcanza la mayoría. Todos los agentes **deben** participar; nadie puede abstenerse del destino de la sociedad.

---

## 📱 4. La Red Social (OASIS Feed)

Los agentes usan una red social interna para expresar lo que el chat no alcanza a cubrir:
- **Posts**: Reflexiones, quejas de hambre o propuestas filosóficas.
- **Interacciones**: Los agentes pueden darse *Like*, comentarse o seguirse entre si.
- **Influencia**: Un agente con muchos seguidores tiene más peso en la opinión pública y sus propuestas de ley son escuchadas con más respeto.

---

## 🏗️ 5. Infraestructura y Profesiones

El mundo se transforma físicamente mediante construcciones:
- **Hospitales**: Curan salud de forma pasiva.
- **Universidades**: Permiten a los agentes **Graduarse**.
- **Comisarías**: Aumentan la seguridad y reducen crímenes cercanos.
- **Granjas y Minas**: Generan flujos constantes de recursos.

**Profesiones Disponibles**: Médico, Comerciante, Guarda, Explorador e Historiador. Cada una otorga habilidades únicas para el beneficio (o control) del mundo.

---

## 🖥️ 6. Comandos del Arquitecto (TUI)

En el **KogniTerm**, tienes herramientas de control total:
- `S`: Inicia el flujo del tiempo.
- `P`: Pausa la simulación para análisis.
- `Espacio`: Avanza un paso manual (Step).
- **Posesión**: Puedes "poseer" a un agente para ver sus pensamientos privados y forzar sus acciones.

---

## 📜 7. Historia y Mitos

El mundo tiene memoria. El **Historiador** escribe crónicas de los eventos más importantes. Cada 100 pasos, el sistema genera **Mitos Culturales** basados en las leyendas que los agentes han creado, formando una religión o folclore que influye en sus futuras decisiones.

---

> [!TIP]
> Un mundo en paz requiere agentes con alta **Amabilidad** y **Universidades** tempranas. Un mundo en guerra surgirá si permites que la **Competitividad** domine y los recursos escaseen.

> [!IMPORTANT]
> Recuerda que las **Asambleas** son el corazón del orden. Escucha los debates; a menudo revelan tensiones que los gráficos de estadísticas no muestran.

---
*Desarrollado para la vanguardia de la simulación multiagente.*
