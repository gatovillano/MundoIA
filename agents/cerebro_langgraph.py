from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from datetime import datetime

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph.checkpoint import SqliteSaver
    except ImportError:
        # Para versiones más nuevas de langgraph
        from langgraph.checkpoint.base import SqliteSaver
import random
from agents.cerebro_llm import cerebro_llm
from core.skills_manager import skill_manager
from systems.conversaciones import gestor_conversaciones


# Estado Cognitivo del Agente con mayor interactividad
class AgentState(TypedDict):
    agente_yo_id: str
    agente_otro_id: Optional[str]
    modelo_instance: Any

    # Campos de decisión
    pensamiento_actual: str
    accion_elegida: Dict
    info_externa: str
    mensaje_generado: str

    # Metadatos de interacción
    peticion_arquitecto: Optional[str]  # Petición que el agente le hace al usuario
    dilema_usuario: Optional[str]  # Un dilema que requiere intervención del usuario
    esta_poseido: bool  # Si el usuario tiene el control total

    # Campos de salida
    mensaje_generado: str
    es_global: bool
    es_grupal: bool
    privado: bool
    destinatario_id: Optional[
        str
    ]  # ID del agente destinatario si el mensaje es privado
    planes: List[Dict]

    # BDI objects (referencing the objects in the Agente instance)
    beliefs: Any
    desires: Any
    intentions: Any


def analizar_situacion(state: AgentState):
    """Nodo 1: Percibir entorno y verificar si hay intervención humana."""
    modelo = state["modelo_instance"]
    agente_yo = modelo.get_agent_by_id(state["agente_yo_id"])

    if not agente_yo:
        return {"pensamiento_actual": "Inexistente"}

    # Verificar si el agente está poseído por el usuario
    poseido = getattr(modelo, "agente_poseido_id", None) == agente_yo.unique_id

    # --- ENRIQUECER CONTEXTO ---
    contexto = f"Estado: Salud={agente_yo.necesidades['salud']:.1f}, Alimento={agente_yo.necesidades['alimento']:.1f}, Descanso={agente_yo.necesidades['descanso']:.1f}. "
    contexto += (
        f"Dinero: {agente_yo.dinero:.1f} MC. Reputación: {agente_yo.reputacion:.2f}. "
    )
    contexto += f"Ubicación: ({agente_yo.x}, {agente_yo.y}). "

    # --- CACHÉ DE CONTEXTO ESTÁTICO ---
    # Separamos lo que cambia cada turno de lo que es estructuralmente estable.
    if not hasattr(agente_yo, "_contexto_estatico_cache") or agente_yo._contexto_estatico_cache is None:
        cache = "\n=== REALIDAD NARRATIVA (LORE DEL ARQUITECTO) ===\n"
        lore = getattr(modelo, "lore", "Un mundo de posibilidades infinitas.")
        cache += f"'{lore}'\n"

        cache += "\n=== GUÍA DE PROGRESO ===\n"
        cache += "- CONSTRUIR: Granja (Ali=++), Hospital (Sal=++), C. Descanso (Des=++), Universidad (XP=++), Mina (Mat=++), C. Comunitario (Social=++).\n"
        cache += "- REFLEXIONAR: Evoluciona tu ALMA, aumenta CONCIENCIA y genera revelaciones profundas.\n"
        cache += "========================\n"
        agente_yo._contexto_estatico_cache = cache

    contexto += agente_yo._contexto_estatico_cache

    # --- ESTADO GLOBAL DEL MUNDO (Sigue siendo dinámico por las facciones y leyes) ---
    contexto += "\n=== ESTADO GLOBAL DEL MUNDO ===\n"
    if modelo.civilizaciones:
        for civ in modelo.civilizaciones.values():
            num_miembros = sum(1 for a in modelo.agentes if a.grupo_id == civ.id)
            es_la_mia = " (TU FACCIÓN)" if civ.id == agente_yo.grupo_id else ""
            contexto += (
                f"  Facción '{civ.nombre}' ({num_miembros} miembros){es_la_mia}. "
            )
    else:
        contexto += "  Sin facciones fundadas aún. "

    # Leyes globales vigentes
    if modelo.leyes_globales:
        leyes_resumen = [
            f"'{l.get('titulo', l.get('texto', '?')[:20])}'"
            for l in modelo.leyes_globales[-2:]
        ]
        contexto += f"\n  Leyes Globales: {', '.join(leyes_resumen)}. "
    else:
        contexto += "\n  Leyes Globales: Ninguna. "

    # Instituciones fundadas
    if modelo.instituciones:
        inst_resumen = [
            f"'{i.nombre}' ({i.tipo})" for i in list(modelo.instituciones.values())[-2:]
        ]
        contexto += f"\n  Instituciones: {', '.join(inst_resumen)}. "
    else:
        contexto += "\n  Instituciones: Ninguna. "

    # Leyes locales de tu facción
    if agente_yo.grupo_id:
        leyes_locales = modelo.facciones_leyes.get(agente_yo.grupo_id, [])
        if leyes_locales:
            loc_resumen = [
                f"'{l.get('titulo', l.get('texto', '?')[:20])}'"
                for l in leyes_locales[-2:]
            ]
            contexto += f"\n  Leyes de tu Facción: {', '.join(loc_resumen)}. "
        contexto += f"\n  Tu Rol en la facción: {agente_yo.rol}. "
    else:
        contexto += "\n  No perteneces a ninguna facción. Puedes elegir prosperar solo o buscar aliados. "

    # Simpatías con otras facciones
    simpatias = getattr(agente_yo, "simpatizante_de", [])
    if simpatias:
        nombres_simpatias = []
        for gid in simpatias:
            civ = modelo.civilizaciones.get(gid)
            nombres_simpatias.append(civ.nombre if civ else gid)
        contexto += f"\n  Eres SIMPATIZANTE de: {', '.join(nombres_simpatias)} → puedes entrar en su territorio libremente. "

    contexto += "\n============================\n"



    # --- GUÍA DE CONSTRUCCIÓN Y EVOLUCIÓN ---
    contexto += "\n=== GUÍA DE PROGRESO ===\n"
    contexto += "- CONSTRUIR: Granja (Ali=++), Hospital (Sal=++), C. Descanso (Des=++), Universidad (XP=++), Mina (Mat=++), C. Comunitario (Social=++).\n"
    contexto += "- REFLEXIONAR: Evoluciona tu ALMA, aumenta CONCIENCIA y genera revelaciones profundas.\n"
    contexto += "========================\n"

    # --- ENTORNO LOCAL: Agentes cercanos ---
    cercanos = [
        a
        for a in modelo.agentes
        if a.unique_id != agente_yo.unique_id
        and abs(a.x - agente_yo.x) <= 2
        and abs(a.y - agente_yo.y) <= 2
    ]
    if cercanos:
        nombres_cercanos = [
            f"{a.identidad.nombre or a.unique_id} (Facción: {a.grupo_id or 'Ninguna'}, Rol: {a.rol})"
            for a in cercanos
        ]
        contexto += f"Agentes cercanos: {', '.join(nombres_cercanos)}. "

    # Info del terreno
    tile = modelo.mapa[agente_yo.x][agente_yo.y]
    contexto += f"Terreno actual: {tile.terrain_type}. "
    if tile.buildings:
        tipos_edif = [b.get("tipo", "Desconocido") for b in tile.buildings]
        contexto += f"EDIFICIOS AQUÍ: {', '.join(tipos_edif)}. "
    if tile.resource_node:
        contexto += f"RECURSOS EN ESTA CASILLA: {tile.resource_node['amount']} de {tile.resource_node['type']}. "

    # Detectar órdenes directas del usuario (Personal y Global)
    contexto_arquitecto = ""
    if (
        hasattr(modelo, "mensaje_global_arquitecto")
        and modelo.mensaje_global_arquitecto
    ):
        contexto_arquitecto += (
            f"📢 [MENSAJE DIVINO GLOBAL]: '{modelo.mensaje_global_arquitecto}'. "
        )

    if hasattr(agente_yo, "mensaje_arquitecto") and agente_yo.mensaje_arquitecto:
        contexto_arquitecto += f"✨ [ORDEN DIVINA PERSONAL]: '{agente_yo.mensaje_arquitecto['contenido']}'. "

    if contexto_arquitecto:
        contexto += f"\n=== INTERVENCIÓN DEL ARQUITECTO ===\n{contexto_arquitecto}\n====================================\n"

    # --- HISTORIAL DE CHAT CON EL ARQUITECTO (User) ---
    if modelo.db_active:
        historial_chat = modelo.db.get_chat_history(
            modelo.user_id, agente_yo.unique_id, limit=20
        )
        if historial_chat:
            contexto += "\n=== HISTORIAL DE CHAT PERSONAL CON EL ARQUITECTO ===\n"
            for msg in historial_chat:
                rol = "Arquitecto" if msg["role"] == "user" else "Tú"
                contexto += f"  {rol}: {msg['content']}\n"
            contexto += "===================================================\n"

    # --- HISTORIAL DE MENSAJES RECIENTES (Percepción de diálogos cercanos) ---
    historial_mensajes = agente_yo.memoria.obtener_contexto_mensajes()
    if historial_mensajes and historial_mensajes != "No hay diálogos previos recientes.":
        contexto += f"\n=== {historial_mensajes} ===\n"

    # --- ÚLTIMO MENSAJE DIRECTO RECIBIDO ---
    if hasattr(agente_yo, "ultimo_mensaje_recibido") and agente_yo.ultimo_mensaje_recibido:
        msg_rec = agente_yo.ultimo_mensaje_recibido
        contexto += "\n=== 📬 ÚLTIMO MENSAJE RECIBIDO (DIRECTO O CERCANO) ===\n"
        contexto += f"De: Agente {msg_rec['emisor']} | Tipo: {msg_rec.get('tipo', 'DIRECTO')}\n"
        contexto += f"Contenido: \"{msg_rec['contenido']}\"\n"
        contexto += "REACCIÓN SUGERIDA: Si te hablan directamente, es de buena educación responder. Usa SUSURRAR para una respuesta privada o el campo 'mensaje' para hablar en voz alta.\n"
        contexto += "======================================================\n"

    # --- CONVERSACIONES ACTIVAS (Contexto profundo) ---
    conversaciones_activas = agente_yo.memoria.obtener_conversaciones_activas()
    if conversaciones_activas:
        contexto += "\n=== CONVERSACIONES ACTIVAS ===\n"
        for otro_id in conversaciones_activas[:2]:
            hist = agente_yo.memoria.obtener_contexto_conversacion_activa(otro_id, max_mensajes=8)
            if hist:
                contexto += hist
                conv = gestor_conversaciones.obtener_conversacion_activa(agente_yo.unique_id, otro_id)
                if conv and conv.profundidad < 0.3:
                    contexto += f"\n[SUGERENCIA] Esta conversación es superficial. Haz preguntas más profundas.\n"
        contexto += "================================\n"

    # --- TEMAS DE INTERÉS RECIENTES ---
    # (Se pueden obtener de experiencias clave recientes)
    if agente_yo.alma and agente_yo.alma.epifanias:
        epifania_reciente = agente_yo.alma.epifanias[-1]
        contexto += f"\n=== REFLEXIÓN PERSONAL RECIENTE ===\n"
        contexto += f"Has tenido una epifanía: '{epifania_reciente.descripcion}'\n"
        contexto += f"Lección: {epifania_reciente.leccion or 'Aún procesando.'}\n"
        contexto += "Considera compartir esta reflexión en tus conversaciones.\n"
        contexto += "==============================\n"

    # --- OASIS: Feed y Notificaciones de interacciones propias ---
    if hasattr(agente_yo, "actualizar_contexto_social_oasis"):
        try:
            agente_yo.actualizar_contexto_social_oasis()
        except Exception:
            pass

    recent_posts = getattr(agente_yo, "contexto_social_reciente", [])
    if recent_posts:
        contexto += "\n=== RED SOCIAL OASIS: PUBLICACIONES RELEVANTES ===\n"
        for p in recent_posts[:5]:
            contexto += f"- {p['autor']} publicó: \"{p['texto']}\" (ID: {p['id']}, ❤️ {p.get('likes', 0)}, 💬 {p.get('comentarios', 0)})\n"
        contexto += "==================================================\n"

    notifications = getattr(agente_yo, "notificaciones_sociales", [])
    if notifications:
        contexto += "\n=== NOTIFICACIONES: INTERACCIONES EN TUS POSTS ===\n"
        for n in notifications[-10:]:
            if n['tipo'] == 'like':
                contexto += f"- A {n['autor_interaccion']} le gustó tu post: \"{n['contenido_post']}\"\n"
            elif n['tipo'] == 'comentario':
                contexto += f"- {n['autor_interaccion']} comentó en tu post (\"{n['contenido_post']}\"): \"{n['contenido_interaccion']}\"\n"
        contexto += "\nESTRATEGIA RECOMENDADA: Si alguien comenta en tus posts, responde (COMMENT) para ganar capital social y fortalecer lazos.\n"
        contexto += "==============================================\n"

    # --- PRESIONES VITALES Y OPORTUNIDADES DINÁMICAS ---
    urgencias = []

    # Supervivencia
    if agente_yo.necesidades["alimento"] < 3.0:
        tiene_comida = agente_yo.inventario.get("comida", 0) > 0
        if tiene_comida:
            urgencias.append(
                f"🔴 HAMBRE CRÍTICA ({agente_yo.necesidades['alimento']:.1f}/10) — ¡COME ahora mismo! Tienes comida en el inventario."
            )
        else:
            urgencias.append(
                f"🔴 HAMBRE CRÍTICA ({agente_yo.necesidades['alimento']:.1f}/10) — RECOLECTA o COMERCIA comida ahora o morirás."
            )
    elif agente_yo.necesidades["alimento"] < 5.0:
        tiene_comida = agente_yo.inventario.get("comida", 0) > 0
        if tiene_comida:
            urgencias.append(
                f"🟡 HAMBRE MODERADA ({agente_yo.necesidades['alimento']:.1f}/10) — considera COMER pronto para恢复."
            )
        else:
            urgencias.append(
                f"🟡 HAMBRE MODERADA ({agente_yo.necesidades['alimento']:.1f}/10) — considera RECOLECTAR pronto."
            )

    if agente_yo.necesidades["salud"] < 3.0:
        tiene_med = agente_yo.inventario.get("medicina", 0) > 0
        if tiene_med:
            urgencias.append(
                f"🔴 SALUD CRÍTICA ({agente_yo.necesidades['salud']:.1f}/10) — CÚRATE AHORA, tienes medicina en el inventario."
            )
        else:
            urgencias.append(
                f"🔴 SALUD CRÍTICA ({agente_yo.necesidades['salud']:.1f}/10) — DESCANSAR o llegar a un Hospital urgentemente."
            )

    if agente_yo.necesidades["descanso"] < 2.0:
        urgencias.append(
            f"🟡 AGOTAMIENTO EXTREMO ({agente_yo.necesidades['descanso']:.1f}/10) — DESCANSA o tu efectividad caerá."
        )

    # Oportunidades económicas
    if agente_yo.dinero > 120 and not agente_yo.inversiones:
        urgencias.append(
            f"💰 CAPITAL OCIOSO: Tienes {agente_yo.dinero:.0f} MC sin invertir. Considera INVERTIR (retorno en 5 turnos)."
        )

    if agente_yo.dinero < 10 and agente_yo.recursos > 70:
        urgencias.append(
            f"💸 POBREZA CON RECURSOS: Tienes {agente_yo.dinero:.0f} MC pero {agente_yo.recursos:.0f} recursos. Considera COMERCIAR para obtener liquidez si lo necesitas."
        )

    # Oportunidades de comercio con vecinos (solo sugerir si realmente necesitas recursos)
    if agente_yo.recursos < 30 and agente_yo.dinero > 30:
        agentes_ricos_en_recursos = [
            a for a in modelo.agentes
            if a.unique_id != agente_yo.unique_id and a.recursos > 50 and abs(a.x - agente_yo.x) <= 3 and abs(a.y - agente_yo.y) <= 3
        ]
        if agentes_ricos_en_recursos:
            t = agentes_ricos_en_recursos[0]
            urgencias.append(
                f"🤝 NECESITAS MATERIALES: {t.identidad.nombre or t.unique_id} está cerca con suficientes recursos. Puedes COMERCIAR con él."
            )

    # Amenazas de enemigos cercanos
    enemigos_cercanos = []
    for a in modelo.agentes:
        if a.unique_id == agente_yo.unique_id:
            continue
        rel = (
            agente_yo.memoria.obtener_tipo(a.unique_id)
            if hasattr(agente_yo.memoria, "obtener_tipo")
            else "desconocido"
        )
        if (
            rel == "enemigo"
            and abs(a.x - agente_yo.x) <= 2
            and abs(a.y - agente_yo.y) <= 2
        ):
            enemigos_cercanos.append(a)

    if enemigos_cercanos and agente_yo.personalidad.get("hostilidad", 0) > 0.5:
        e = enemigos_cercanos[0]
        urgencias.append(
            f"⚔️ ENEMIGO A LA VISTA: {e.identidad.nombre or e.unique_id} (grupo: {e.grupo_id or 'ninguno'}) está a {abs(e.x - agente_yo.x) + abs(e.y - agente_yo.y)} casillas. Tu hostilidad es alta — ¿ATACAS?"
        )
    elif enemigos_cercanos and agente_yo.personalidad.get("hostilidad", 0) <= 0.5:
        e = enemigos_cercanos[0]
        urgencias.append(
            f"⚠️ ENEMIGO CERCA: {e.identidad.nombre or e.unique_id} está próximo. Puedes NEGOCIAR_PAZ o evitarlo moviéndote."
        )

    # Logros disponibles
    xp_max_area = (
        max(agente_yo.experiencia, key=agente_yo.experiencia.get)
        if agente_yo.experiencia
        else None
    )
    if (
        xp_max_area
        and agente_yo.experiencia.get(xp_max_area, 0) >= 8
        and not agente_yo.profesion
    ):
        urgencias.append(
            f"🎓 PUEDES PROFESIONALIZARTE: Tienes {agente_yo.experiencia[xp_max_area]} XP en {xp_max_area}. Ve a una Universidad para GRADUARTE."
        )

    # --- SUGERENCIAS BASADAS EN PERSONALIDAD ---
    curiosidad = agente_yo.personalidad.get("curiosidad", 0.5)
    amabilidad = agente_yo.personalidad.get("amabilidad", 0.5)
    hostilidad = agente_yo.personalidad.get("hostilidad", 0.5)

    # Solo sugerir crear habilidades/apps si tiene curiosidad media/alta y está estable
    if (
        curiosidad > 0.5
        and agente_yo.necesidades["alimento"] > 5
        and agente_yo.necesidades["salud"] > 5
    ):
        if not agente_yo.skills:
            urgencias.append(
                "🧠 POTENCIAL EVOLUTIVO: Sientes que tu mente puede ir más allá. Considera CREAR_HABILIDAD (Python) para desarrollar una capacidad única."
            )
        
        if not agente_yo.apps:
            urgencias.append(
                "💻 INGENIO TÉCNICO: Tienes ideas que podrían convertirse en herramientas. Considera CREAR_APP para programar una solución persistente."
            )
        elif len(agente_yo.apps) < 3:
             urgencias.append(
                "🚀 AMBICIÓN TECNOLÓGICA: Tus creaciones actuales son solo el principio. Considera CREAR_APP para expandir tu arsenal de software."
            )

    # Incitar a la socialización si es amable
    if amabilidad > 0.7 and len(agente_yo.memoria.grafo.nodes) < 5:
        urgencias.append(
            "🤝 PERSONA AFABLE: Te sientes solo. Socializa con alguien cercano o busca fundar/unirte a un grupo para prosperar."
        )

    # Sugerir EXPLORAR si tiene curiosidad y está estable
    if (
        curiosidad > 0.6
        and agente_yo.necesidades["alimento"] > 6
        and not enemigos_cercanos
    ):
        urgencias.append(
            "🔭 AFÁN EXPLORADOR: El horizonte te llama. Considera EXPLORAR nuevas tierras para ganar experiencia y descubrir tesoros."
        )

    # Sugerir INVESTIGAR si tiene mucha experiencia en algo pero no es profesional
    if (
        xp_max_area
        and agente_yo.experiencia.get(xp_max_area, 0) > 4
        and not agente_yo.profesion
    ):
        urgencias.append(
            f"🧪 VOCACIÓN POR {xp_max_area.upper()}: Te estás volviendo experto. Considera INVESTIGAR sobre {xp_max_area} o ir a una Universidad para ESTUDIAR."
        )

    # No hay sugerencias de camino vital (VOLUNTAD PURA)
    # El agente decide su destino basándose únicamente en su Alma y BDI.
    pass

    # Incitar al conflicto si es hostil
    if hostilidad > 0.7 and not enemigos_cercanos:
        urgencias.append(
            "⚔️ IMPULSO AGRESIVO: Sientes que este mundo es para los fuertes. Busca un rival cercano con recursos y somételo con ATACAR."
        )

    if urgencias:
        contexto += "\n=== ⚡ SITUACIÓN ACTUAL — PRESIONES Y OPORTUNIDADES ===\n"
        contexto += "\n".join(urgencias)
        contexto += "\n=======================================================\n"

    return {"esta_poseido": poseido, "info_externa": contexto}


def actuar(state: AgentState):
    """Nodo 2: Toma la decisión basada en Intenciones (BDI)."""
    modelo = state["modelo_instance"]
    agente_yo = modelo.get_agent_by_id(state["agente_yo_id"])
    agente_otro = modelo.get_agent_by_id(state.get("agente_otro_id"))

    # 1. POSESIÓN (Sobreescribe todo)
    if state.get("esta_poseido"):
        return {
            "pensamiento_actual": "Mi voluntad ha sido suplantada por el Arquitecto. Él guía mis pasos ahora.",
            "accion_elegida": {"nombre": "POSESIÓN_DIVINA", "argumentos": {}},
            "mensaje_llm": "Mi cuerpo no me pertenece... el Arquitecto me controla.",
        }

    # 2. EJECUCIÓN DE INTENCIÓN (Si ya existe un plan BDI válido)
    plan_bdi = agente_yo.intenciones.plan_actual
    if plan_bdi and plan_bdi.es_valido():
        # Verificar si hay que abortar (Emergencia crítica)
        es_emergencia = (
            agente_yo.necesidades["salud"] < 3.0
            or agente_yo.necesidades["alimento"] < 3.0
            or agente_yo.necesidades["descanso"] < 2.0
        )

        if not es_emergencia:
            accion_dict = agente_yo.tick_bdi()  # Ejecuta un paso del plan BDI
            if accion_dict:
                p_msg = f"Siguiendo plan BDI: {plan_bdi.meta} (Paso {plan_bdi.tiempo_actual}/{len(plan_bdi.acciones)})"
                return {
                    "pensamiento_actual": p_msg,
                    "accion_elegida": accion_dict,
                    "mensaje_llm": f"Estoy enfocado en mi objetivo: {plan_bdi.meta}",
                    "intentions": plan_bdi.acciones,
                }
        else:
            modelo.log(
                f"⚡ [BDI] Agente {agente_yo.unique_id} aborta planes BDI por emergencia vital.",
                categoria="sistema",
            )
            agente_yo.intenciones.plan_actual = None

    # 3. DELIBERACIÓN (Llamar a la IA para nuevos deseos e intenciones si no hay plan o es emergencia)
    stream_started = {"value": False}

    def _emit_llm_stream(chunk: str, done: bool = False):
        cb = getattr(modelo, "realtime_event_callback", None)
        if not cb:
            return
        payload = {
            "agent_id": agente_yo.unique_id,
            "agent_name": agente_yo.identidad.nombre if agente_yo.identidad else agente_yo.unique_id,
            "step": modelo.paso_actual,
            "chunk": chunk or "",
            "reset": not stream_started["value"],
            "done": bool(done),
        }
        stream_started["value"] = True
        try:
            # Usar helper del modelo para respetar posible ritmo lento
            if hasattr(modelo, "_emit_realtime_event"):
                modelo._emit_realtime_event("llm_stream", payload)
            else:
                cb("llm_stream", payload)
        except Exception:
            pass

    decision = cerebro_llm.generar_pensamiento_y_accion(
        agente_yo,
        agente_otro,
        state["info_externa"],
        stream_callback=_emit_llm_stream,
    )

    # Extraer BDI de la respuesta de la IA
    nuevas_creencias = decision.get("beliefs", [])
    nuevos_deseos = decision.get("desires", [])
    nuevas_intenciones = decision.get("intentions", [])

    # Actualizar Sistema de Creencias del agente con lo que el LLM "cree"
    for b in nuevas_creencias:
        agente_yo.creencias.actualizar_creencia(b, 0.8, 1.0, modelo.paso_actual)

    # Si la IA devolvió intenciones, crear un PlanBDI
    if nuevas_intenciones:
        from agents.bdi_components import PlanBDI, AccionBDI, TipoAccion

        acciones_plan = []
        for i, intencion in enumerate(nuevas_intenciones):
            try:
                tipo_act = TipoAccion(intencion.get("accion", "HABLAR").upper())
            except ValueError:
                tipo_act = TipoAccion.HABLAR

            acciones_plan.append(
                AccionBDI(
                    tipo=tipo_act,
                    objetivo=intencion.get("objetivo"),
                    parametros=intencion.get("params", {}),
                    meta=intencion.get("meta", decision.get("pensamiento", "")),
                )
            )

        nuevo_plan = PlanBDI(
            acciones=acciones_plan,
            meta=nuevas_intenciones[0].get("meta", "Plan sugerido por LLM"),
            prioridad=0.7,
        )
        agente_yo.intenciones.plan_actual = nuevo_plan

        # Ejecutar la primera acción ahora mismo
        accion_dict = agente_yo.tick_bdi()
    else:
        # Fallback si no hay intenciones, usar la acción inmediata de la IA
        accion_dict = decision.get(
            "accion", {"nombre": "HABLAR", "argumentos": {"mensaje": "..."}}
        )

    # Extraer destinatario si es una acción de SUSURRAR
    dest_id = decision.get("destinatario_id")
    if not dest_id and accion_dict and (accion_dict.get("nombre") == "SUSURRAR" or accion_dict.get("tipo") == "susurrar"):
        dest_id = accion_dict.get("argumentos", {}).get("target_id")

    return {
        "pensamiento_actual": decision.get("pensamiento", "No pude pensar."),
        "accion_elegida": accion_dict,
        "mensaje_generado": decision.get("mensaje", ""),
        "es_global": decision.get("es_global", False),
        "es_grupal": decision.get("es_grupal", False),
        "privado": bool(dest_id),
        "destinatario_id": dest_id,
        "beliefs": nuevas_creencias,
        "desires": nuevos_deseos,
        "intentions": nuevas_intenciones,
    }


def decidir_ruta(state: AgentState) -> str:
    """Nodo 3: Decide si usar herramientas o ir a comunicación."""
    if state.get("esta_poseido"):
        return "comunicar"

    accion_nombre = (
        state["accion_elegida"].get("nombre", "HABLAR").lower()
    )  # Normalizar a minúsculas

    # Verificar si el nombre de la acción es una skill conocida
    modelo = state["modelo_instance"]
    agente_yo = modelo.get_agent_by_id(state["agente_yo_id"])

    is_skill = accion_nombre in skill_manager.base_skills or (
        agente_yo and accion_nombre in agente_yo.skills
    )

    if is_skill:
        return "ejecutar_herramientas"
    return "comunicar"

    accion_nombre = state["accion_elegida"].get("nombre", "HABLAR")

    # Verificar si el nombre de la acción es una skill conocida
    modelo = state["modelo_instance"]
    agente_yo = modelo.get_agent_by_id(state["agente_yo_id"])

    is_skill = accion_nombre in skill_manager.base_skills or (
        agente_yo and accion_nombre in agente_yo.skills
    )

    if is_skill:
        return "ejecutar_herramientas"
    return "comunicar"


def ejecutar_herramientas(state: AgentState):
    """Nodo 4: Ejecuta habilidades (base y aprendidas)."""
    from agents.alma import ExperienciaClave

    modelo = state["modelo_instance"]
    agente_yo = modelo.get_agent_by_id(state["agente_yo_id"])
    accion = state["accion_elegida"]
    nombre_accion = accion.get("nombre", "").lower()  # Normalizar a minúsculas
    argumentos = accion.get("argumentos", {})

    # === CASO ESPECIAL: REFLEXIONAR ===
    if nombre_accion == "reflexionar":
        tema = argumentos.get("tema", "la vida y mi propósito")
        profundidad = argumentos.get("profundidad", "media")
        intensidad = {"superficial": 0.3, "media": 0.5, "profunda": 0.8}.get(profundidad, 0.5)

        # Generar reflexión y conclusión con LLM
        reflexion_texto, conclusion = cerebro_llm.generar_reflexion_conclusion(agente_yo, tema, profundidad)

        exp = ExperienciaClave(
            descripcion=reflexion_texto,
            turno=modelo.paso_actual,
            intensidad=intensidad,
            tipo="epifania",
            leccion=conclusion,
            emociones_asociadas=["reflexivo", "claro"],
        )
        agente_yo.alma.evolucionar(exp)

        # Guardar también en lista de reflexiones del Alma
        try:
            if not hasattr(agente_yo.alma, "reflexiones"):
                agente_yo.alma.reflexiones = []
            reflex_exp = ExperienciaClave(
                descripcion=reflexion_texto,
                turno=modelo.paso_actual,
                intensidad=intensidad,
                tipo="reflexion",
                leccion=conclusion,
                emociones_asociadas=["reflexivo"],
            )
            agente_yo.alma.reflexiones.append(reflex_exp)
        except Exception as e:
            print(f"⚠️ No se pudo guardar reflexión en lista: {e}")

        # Registrar en memoria conversacional si hay conversación activa
        if state.get("agente_otro_id"):
            agente_yo.memoria.agregar_mensaje_a_conversacion(
                state["agente_otro_id"],
                f"[REFLEXIÓN] {reflexion_texto}",
                modelo.paso_actual,
                tipo="reflexion",
                metadata={"tema": tema, "profundidad": profundidad, "conclusion": conclusion},
            )

        mensaje_res = f"Mi reflexión sobre '{tema}' me llevó a: {conclusion}"
        modelo.log(
            f"🧠 [REFLEXIÓN] Agente {agente_yo.unique_id} reflexiona sobre '{tema}' (intensidad: {intensidad}). Conclusión: {conclusion}",
            categoria="sistema",
        )
        modelo.notificar_cambio_estado()
        return {"info_externa": mensaje_res}

    # === ACCIÓN: COMMENT (COMENTAR EN OASIS) ===
    if nombre_accion == "comment":
        post_id = argumentos.get("post_id", "")
        contenido = argumentos.get("contenido", "")
        if not contenido:
            resultado = "Error: COMMENT requiere 'contenido'."
        else:
            modelo = state.get("modelo_instance")
            if hasattr(agente_yo, "social_comment") and agente_yo.social_comment(post_id, contenido):
                resultado = f"Comentario añadido en Oasis: {contenido[:50]}..."
                if hasattr(agente_yo, "memoria") and agente_yo.memoria:
                    agente_yo.memoria.agregar_mensaje_a_conversacion(
                        state.get("agente_otro_id", "OASIS"),
                        f"[COMENTARIO] {contenido}",
                        modelo.paso_actual,
                        tipo="social_comment",
                        metadata={"post_id": post_id},
                    )
            else:
                resultado = "Error: No se pudo registrar el comentario en Oasis."
        return {"info_externa": resultado}


    # === ALIAS: WEB_SEARCH -> web_search ===
    if nombre_accion == "web_search":
        nombre_accion = "web_search"
    
    if nombre_accion == "ejecutar_codigo":
        nombre_accion = "ejecutar_codigo"
        
    if nombre_accion == "crear_app":
        nombre_accion = "crear_app"

    # === USAR SKILL_MANAGER PARA EL RESTO ===
    resultado_skill = skill_manager.ejecutar_skill(
        nombre_accion,
        argumentos,
        agente_id=agente_yo.unique_id,
        agent_skills=agente_yo.skills,
    )

    # Procesar el resultado de la skill
    if isinstance(resultado_skill, dict):
        # Manejar errores
        if resultado_skill.get("error"):
            return {"info_externa": resultado_skill["error"]}

        # Si fue una búsqueda web y hay conversación activa, registrar en el historial conversacional
        if nombre_accion == "web_search" and state.get("agente_otro_id"):
            query = argumentos.get("query", "")
            resultado_str = str(resultado_skill.get("resultado", ""))[:200]
            agente_yo.memoria.agregar_mensaje_a_conversacion(
                state["agente_otro_id"],
                f"[INVESTIGACIÓN WEB sobre '{query}'] {resultado_str}...",
                modelo.paso_actual,
                tipo="busqueda_info",
                metadata={"query": query},
            )

        # Aplicar experiencia ganada
        experiencia_ganada = resultado_skill.get("experiencia_ganada", {})
        for categoria, puntos in experiencia_ganada.items():
            if categoria in agente_yo.experiencia:
                agente_yo.experiencia[categoria] = min(
                    100, agente_yo.experiencia[categoria] + puntos
                )

        # Aplicar efectos en necesidades
        efecto_necesidades = resultado_skill.get("efecto_necesidades", {})
        for necesidad, cambio in efecto_necesidades.items():
            if necesidad in agente_yo.necesidades:
                agente_yo.necesidades[necesidad] = max(
                    0, min(10, agente_yo.necesidades[necesidad] + cambio)
                )

        # Loguear si hubo efectos significativos
        if experiencia_ganada:
            exp_msg = ", ".join(
                [f"+{v:.1f} {k}" for k, v in experiencia_ganada.items()]
            )
            modelo.log(
                f"📊 [EXP] Agente {agente_yo.unique_id}: {exp_msg}", categoria="sistema"
            )

        if efecto_necesidades:
            nec_msg = ", ".join(
                [f"{k}: {v:+.1f}" for k, v in efecto_necesidades.items()]
            )
            modelo.log(
                f"💫 [NECESIDADES] Agente {agente_yo.unique_id}: {nec_msg}",
                categoria="sistema",
            )

        resultado = resultado_skill.get("resultado", "")

        # Manejar el caso especial de crear_habilidad
        if nombre_accion == "crear_habilidad":
            if isinstance(resultado, dict) and resultado.get("status") == "success":
                new_skill_data = resultado.get("new_skill")
                agente_yo.skills[new_skill_data["name"]] = new_skill_data
                
                # RECOMPENSA: Prestigio e Intelecto
                agente_yo.reputacion = min(1.0, agente_yo.reputacion + 0.05)
                if hasattr(agente_yo, "necesidades_intelectuales"):
                    agente_yo.necesidades_intelectuales["curiosidad"] = min(10.0, agente_yo.necesidades_intelectuales["curiosidad"] + 2.0)
                    agente_yo.necesidades_intelectuales["aprendizaje"] = min(10.0, agente_yo.necesidades_intelectuales["aprendizaje"] + 2.0)
                
                mensaje_res = f"Habilidad '{new_skill_data['name']}' creada con éxito. Mi reputación aumenta."
                modelo.log(
                    f"🧠 [EVOLUCIÓN] Agente {agente_yo.unique_id} ha desarrollado la habilidad: {new_skill_data['name']}",
                    categoria="sistema",
                )
                modelo.notificar_cambio_estado()
                return {"info_externa": mensaje_res}

        # Manejar el caso especial de crear_app
        if nombre_accion == "crear_app":
            if isinstance(resultado, dict) and resultado.get("status") == "success":
                app_data = resultado.get("app")
                agente_yo.apps[app_data["name"]] = app_data
                
                # RECOMPENSA: Capital Social y Trascendencia
                if hasattr(agente_yo, "capital_social"):
                    agente_yo.capital_social = min(100.0, agente_yo.capital_social + 5.0)
                agente_yo.reputacion = min(1.0, agente_yo.reputacion + 0.08)
                if hasattr(agente_yo, "necesidades_intelectuales"):
                    agente_yo.necesidades_intelectuales["expresion"] = min(10.0, agente_yo.necesidades_intelectuales["expresion"] + 3.0)
                
                mensaje_res = f"Aplicación '{app_data['name']}' creada y guardada. Me siento más poderoso y reconocido."
                modelo.log(
                    f"💻 [APP CREATED] Agente {agente_yo.unique_id} ha creado una nueva App: {app_data['name']}",
                    categoria="sistema",
                )
                modelo.notificar_cambio_estado()
                return {"info_externa": mensaje_res}

        return {"info_externa": str(resultado)}
    else:
        return {"info_externa": str(resultado_skill)}


def comunicar(state: AgentState):
    """Nodo 5: Genera el output final y gestiona la interactividad con el usuario."""
    modelo = state["modelo_instance"]
    agente_yo = modelo.get_agent_by_id(state["agente_yo_id"])
    accion = state["accion_elegida"]
    mensaje_llm = state.get("mensaje_generado", "")
    peticion = state.get("peticion_arquitecto")
    dilema = state.get("dilema_usuario")
    destinatario_id = state.get("destinatario_id")

    # Si hay una petición al usuario, la registramos en el log para que el usuario la vea
    if peticion:
        modelo.log(
            f"🙏 [PETICIÓN] Agente {agente_yo.unique_id}: '{peticion}'",
            categoria="sistema",
        )

    if dilema:
        modelo.log(
            f"🤔 [DILEMA] Agente {agente_yo.unique_id} enfrenta un dilema: '{dilema}'",
            categoria="consenso",
        )

    mensaje_final = (
        mensaje_llm if mensaje_llm else f"Realizando {accion.get('nombre')}..."
    )

    # === GESTIÓN DE CONVERSACIONES ===
    if destinatario_id:
        # Iniciar conversación si no existe una activa
        conversaciones_activas = agente_yo.memoria.obtener_conversaciones_activas()
        if destinatario_id not in conversaciones_activas:
            agente_yo.memoria.iniciar_conversacion_con(destinatario_id)
            modelo.log(
                f"💬 [CONVERSACIÓN] Agente {agente_yo.unique_id} inicia conversación con {destinatario_id}",
                categoria="social",
            )
        # Registrar el mensaje en la memoria conversacional
        agente_yo.memoria.agregar_mensaje_a_conversacion(
            destinatario_id,
            mensaje_final,
            modelo.paso_actual,
            tipo="normal",
            metadata={"accion": accion.get("nombre")},
        )

    # Respetar la decisión explícita del LLM sobre el alcance del mensaje.
    # Solo forzar global si el LLM lo indica. No forzar por ser Líder o por mencionar "ley".
    es_global = state.get("es_global", False)
    es_grupal = state.get("es_grupal", False)
    # Si hay destinatario específico del LLM, el mensaje es privado
    privado = bool(destinatario_id)

    return {
        "mensaje_generado": mensaje_final,
        "es_global": es_global,
        "es_grupal": es_grupal,
        "privado": privado,
        "destinatario_id": destinatario_id,
    }


# Construcción del Grafo Cognitivo Mejorado
workflow = StateGraph(AgentState)

workflow.add_node("analizar", analizar_situacion)
workflow.add_node("actuar", actuar)
workflow.add_node("ejecutar_herramientas", ejecutar_herramientas)
workflow.add_node("comunicar", comunicar)

workflow.set_entry_point("analizar")
workflow.add_edge("analizar", "actuar")
workflow.add_conditional_edges(
    "actuar",
    decidir_ruta,
    {"comunicar": "comunicar", "ejecutar_herramientas": "ejecutar_herramientas"},
)
workflow.add_edge("ejecutar_herramientas", "comunicar")
workflow.add_edge("comunicar", END)

cerebro_cognitivo = workflow.compile()


class CerebroAvanzado:
    def __init__(self, agent_id):
        self.agent_id = agent_id

    def pensar(self, agente, objetivo_id=None):
        initial_state = {
            "agente_yo_id": agente.unique_id,
            "agente_otro_id": objetivo_id,
            "modelo_instance": agente.modelo,
            "pensamiento_actual": "",
            "accion_elegida": {},
            "info_externa": "",
            "mensaje_generado": "",
            "mensaje_llm": "",
            "esta_poseido": False,
            "peticion_arquitecto": None,
            "dilema_usuario": None,
            "es_global": False,
            "es_grupal": False,
            "privado": False,
            "destinatario_id": None,
            "planes": [],
            "beliefs": agente.creencias,
            "desires": agente.deseos,
            "intentions": agente.intenciones,
        }

        config = {"configurable": {"thread_id": f"agent_{agente.unique_id}"}}
        final_state = cerebro_cognitivo.invoke(initial_state, config)

        # --- CAPTURAR PENSAMIENTO PARA STREAM DE CONCIENCIA ---
        pensamiento_actual = final_state.get("pensamiento_actual", "")
        if not hasattr(agente, 'pensamientos_recientes'):
            agente.pensamientos_recientes = []
        agente.pensamientos_recientes.append({
            'turno': agente.modelo.paso_actual,
            'pensamiento': pensamiento_actual,
            'timestamp': datetime.now().isoformat()
        })
        # Limitar a los últimos 100 pensamientos
        agente.pensamientos_recientes = agente.pensamientos_recientes[-100:]

        accion = final_state.get("accion_elegida", {})
        nombre_accion = accion.get("nombre", "HABLAR")
        argumentos = accion.get("argumentos", {})

        # Formato para el motor de simulación
        decision_str = (
            f"{nombre_accion}:" + ":".join(map(str, argumentos.values()))
            if argumentos
            else nombre_accion
        )

        # NOTA: No sobrescribir los objetos BDI (creencias, deseos, intenciones) con lo que devuelve el state.
        # El state contiene listas crudas del LLM, pero los agentes necesitan objetos completos
        # (SistemaCreencias, SistemaDeseos, SistemaIntenciones).
        # Los BDI ya se actualizan correctamente dentro de actuar():
        #   - creencias: actuar() llama a agente_yo.creencias.actualizar_creencia()
        #   - intenciones: actuar() asigna agente_yo.intenciones.plan_actual = nuevo_plan

        return (
            decision_str,
            final_state.get("mensaje_generado", ""),
            final_state.get("pensamiento_actual", ""),
            final_state.get("privado", False),
            final_state.get("es_grupal", False),
            final_state.get("es_global", False),
            final_state.get("planes", []),
            accion,  # Retornar el diccionario original de la acción
            final_state.get(
                "destinatario_id"
            ),  # ID del destinatario si el mensaje es privado
        )
