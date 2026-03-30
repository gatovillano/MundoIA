from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph.checkpoint import SqliteSaver
    except ImportError:
        # Para versiones más nuevas de langgraph
        from langgraph.checkpoint.base import SqliteSaver
import random
from cerebro_llm import cerebro_llm
from herramientas import herramientas
from skills_manager import skill_manager

# Estado Cognitivo del Agente con mayor interactividad
class AgentState(TypedDict):
    agente_yo_id: str
    agente_otro_id: Optional[str]
    modelo_instance: Any
    
    # Campos de decisión
    pensamiento_actual: str
    accion_elegida: Dict
    info_externa: str
    mensaje_llm: str
    
    # Metadatos de interacción
    peticion_arquitecto: Optional[str]  # Petición que el agente le hace al usuario
    dilema_usuario: Optional[str]      # Un dilema que requiere intervención del usuario
    esta_poseido: bool                 # Si el usuario tiene el control total
    
    # Campos de salida
    mensaje_generado: str
    es_global: bool
    es_grupal: bool
    privado: bool
    destinatario_id: Optional[str]  # ID del agente destinatario si el mensaje es privado
    planes: List[Dict]
    
    # BDI persistence
    beliefs: List[str]
    desires: List[str]
    intentions: List[Dict]

def analizar_situacion(state: AgentState):
    """Nodo 1: Percibir entorno y verificar si hay intervención humana."""
    modelo = state['modelo_instance']
    agente_yo = modelo.get_agent_by_id(state['agente_yo_id'])
    
    if not agente_yo:
        return {"pensamiento_actual": "Inexistente"}

    # Verificar si el agente está poseído por el usuario
    poseido = getattr(modelo, 'agente_poseido_id', None) == agente_yo.unique_id
    
    # --- ENRIQUECER CONTEXTO ---
    contexto = f"Estado: Salud={agente_yo.necesidades['salud']:.1f}, Alimento={agente_yo.necesidades['alimento']:.1f}, Descanso={agente_yo.necesidades['descanso']:.1f}. "
    contexto += f"Dinero: {agente_yo.dinero:.1f} MC. Reputación: {agente_yo.reputacion:.2f}. "
    contexto += f"Ubicación: ({agente_yo.x}, {agente_yo.y}). "

    # --- VISIÓN GLOBAL: Lore y Facciones ---
    contexto += "\n=== REALIDAD NARRATIVA (LORE DEL ARQUITECTO) ===\n"
    lore = getattr(modelo, 'lore', 'Un mundo de posibilidades infinitas.')
    contexto += f"'{lore}'\n"

    contexto += "\n=== ESTADO GLOBAL DEL MUNDO ===\n"
    if modelo.civilizaciones:
        for civ in modelo.civilizaciones.values():
            num_miembros = sum(1 for a in modelo.agentes if a.grupo_id == civ.id)
            es_la_mia = " (TU FACCIÓN)" if civ.id == agente_yo.grupo_id else ""
            contexto += f"  Facción '{civ.nombre}' ({num_miembros} miembros){es_la_mia}. "
    else:
        contexto += "  Sin facciones fundadas aún. "

    # Leyes globales vigentes
    if modelo.leyes_globales:
        leyes_resumen = [f"'{l.get('titulo', l.get('texto', '?')[:20])}'" for l in modelo.leyes_globales[-2:]]
        contexto += f"\n  Leyes Globales: {', '.join(leyes_resumen)}. "
    else:
        contexto += "\n  Leyes Globales: Ninguna. "

    # Instituciones fundadas
    if modelo.instituciones:
        inst_resumen = [f"'{i.nombre}' ({i.tipo})" for i in list(modelo.instituciones.values())[-2:]]
        contexto += f"\n  Instituciones: {', '.join(inst_resumen)}. "
    else:
        contexto += "\n  Instituciones: Ninguna. "

    # Leyes locales de tu facción
    if agente_yo.grupo_id:
        leyes_locales = modelo.facciones_leyes.get(agente_yo.grupo_id, [])
        if leyes_locales:
            loc_resumen = [f"'{l.get('titulo', l.get('texto', '?')[:20])}'" for l in leyes_locales[-2:]]
            contexto += f"\n  Leyes de tu Facción: {', '.join(loc_resumen)}. "
        contexto += f"\n  Tu Rol en la facción: {agente_yo.rol}. "
    else:
        contexto += "\n  No perteneces a ninguna facción. ¡Considera unirte o fundar una! "
    contexto += "\n============================\n"

    # --- ENTORNO LOCAL: Agentes cercanos ---
    cercanos = [a for a in modelo.agentes if a.unique_id != agente_yo.unique_id and abs(a.x - agente_yo.x) <= 2 and abs(a.y - agente_yo.y) <= 2]
    if cercanos:
        nombres_cercanos = [f"{a.unique_id} (Facción: {a.grupo_id or 'Ninguna'}, Rol: {a.rol})" for a in cercanos]
        contexto += f"Agentes cercanos: {', '.join(nombres_cercanos)}. "

    # Info del terreno
    tile = modelo.mapa[agente_yo.x][agente_yo.y]
    contexto += f"Terreno actual: {tile.terrain_type}. "
    if tile.resource_node:
        contexto += f"Recursos aquí: {tile.resource_node['amount']} de {tile.resource_node['type']}. "

    # Detectar órdenes directas del usuario (Personal y Global)
    contexto_arquitecto = ""
    if hasattr(modelo, 'mensaje_global_arquitecto') and modelo.mensaje_global_arquitecto:
        contexto_arquitecto += f"📢 [MENSAJE DIVINO GLOBAL]: '{modelo.mensaje_global_arquitecto}'. "
    
    if hasattr(agente_yo, 'mensaje_arquitecto') and agente_yo.mensaje_arquitecto:
        contexto_arquitecto += f"✨ [ORDEN DIVINA PERSONAL]: '{agente_yo.mensaje_arquitecto['contenido']}'. "
    
    if contexto_arquitecto:
        contexto += f"\n=== INTERVENCIÓN DEL ARQUITECTO ===\n{contexto_arquitecto}\n====================================\n"

    # --- HISTORIAL DE CHAT CON EL ARQUITECTO (User) ---
    if modelo.db_active:
        historial_chat = modelo.db.get_chat_history(modelo.user_id, agente_yo.unique_id, limit=20)
        if historial_chat:
            contexto += "\n=== HISTORIAL DE CHAT PERSONAL CON EL ARQUITECTO ===\n"
            for msg in historial_chat:
                rol = "Arquitecto" if msg['role'] == "user" else "Tú"
                contexto += f"  {rol}: {msg['content']}\n"
            contexto += "===================================================\n"

    # --- HISTORIAL DE DIÁLOGOS Y ACCIONES CON OTROS AGENTES ---
    contexto += f"\n{agente_yo.memoria.obtener_contexto_mensajes()}\n"
    contexto += f"\n{agente_yo.memoria.obtener_contexto_acciones()}\n"

    # --- Contexto para el Historiador ---
    if agente_yo.rol == "Historiador":
        hitos = modelo.historia.obtener_resumen_hitos()
        if hitos != "No han ocurrido eventos notables recientemente.":
            contexto += f"\n¡CRÍTICO! ERES EL HISTORIADOR Y HAY HITOS PENDIENTES:\n{hitos}\nTU PRIORIDAD ABSOLUTA ES USAR 'ESCRIBIR_CRONICA' PARA NARRAR ESTO AHORA."
        else:
            contexto += f"\n[HISTORIADOR] No hay hitos nuevos que narrar. Sigue observando."

    # --- PRESIONES VITALES Y OPORTUNIDADES DINÁMICAS ---
    urgencias = []
    
    # Supervivencia
    if agente_yo.necesidades["alimento"] < 3.0:
        tiene_comida = agente_yo.inventario.get("comida", 0) > 0
        if tiene_comida:
            urgencias.append(f"🔴 HAMBRE CRÍTICA ({agente_yo.necesidades['alimento']:.1f}/10) — ¡COME ahora mismo! Tienes comida en el inventario.")
        else:
            urgencias.append(f"🔴 HAMBRE CRÍTICA ({agente_yo.necesidades['alimento']:.1f}/10) — RECOLECTA o COMERCIA comida ahora o morirás.")
    elif agente_yo.necesidades["alimento"] < 5.0:
        tiene_comida = agente_yo.inventario.get("comida", 0) > 0
        if tiene_comida:
            urgencias.append(f"🟡 HAMBRE MODERADA ({agente_yo.necesidades['alimento']:.1f}/10) — considera COMER pronto para恢复.")
        else:
            urgencias.append(f"🟡 HAMBRE MODERADA ({agente_yo.necesidades['alimento']:.1f}/10) — considera RECOLECTAR pronto.")
    
    if agente_yo.necesidades["salud"] < 3.0:
        tiene_med = agente_yo.inventario.get("medicina", 0) > 0
        if tiene_med:
            urgencias.append(f"🔴 SALUD CRÍTICA ({agente_yo.necesidades['salud']:.1f}/10) — CÚRATE AHORA, tienes medicina en el inventario.")
        else:
            urgencias.append(f"🔴 SALUD CRÍTICA ({agente_yo.necesidades['salud']:.1f}/10) — DESCANSAR o llegar a un Hospital urgentemente.")
    
    if agente_yo.necesidades["descanso"] < 2.0:
        urgencias.append(f"🟡 AGOTAMIENTO EXTREMO ({agente_yo.necesidades['descanso']:.1f}/10) — DESCANSA o tu efectividad caerá.")

    # Oportunidades económicas
    if agente_yo.dinero > 120 and not agente_yo.inversiones:
        urgencias.append(f"💰 CAPITAL OCIOSO: Tienes {agente_yo.dinero:.0f} MC sin invertir. Considera INVERTIR (retorno en 5 turnos).")
    
    if agente_yo.dinero < 15 and agente_yo.recursos > 50:
        urgencias.append(f"💸 POBREZA CON RECURSOS: Tienes {agente_yo.dinero:.0f} MC pero {agente_yo.recursos:.0f} recursos. COMERCIA para obtener dinero.")
    
    # Oportunidades de comercio con vecinos
    agentes_ricos_en_recursos = [a for a in modelo.agentes 
                                  if a.unique_id != agente_yo.unique_id 
                                  and a.recursos > 80 
                                  and agente_yo.dinero > 15
                                  and abs(a.x - agente_yo.x) <= 3 
                                  and abs(a.y - agente_yo.y) <= 3]
    if agentes_ricos_en_recursos:
        t = agentes_ricos_en_recursos[0]
        urgencias.append(f"🤝 OPORTUNIDAD COMERCIAL: {t.unique_id} está cerca con {t.recursos:.0f} recursos. Puedes COMERCIAR.")
    
    # Amenazas de enemigos cercanos
    enemigos_cercanos = []
    for a in modelo.agentes:
        if a.unique_id == agente_yo.unique_id:
            continue
        rel = agente_yo.memoria.obtener_tipo(a.unique_id) if hasattr(agente_yo.memoria, 'obtener_tipo') else "desconocido"
        if rel == "enemigo" and abs(a.x - agente_yo.x) <= 2 and abs(a.y - agente_yo.y) <= 2:
            enemigos_cercanos.append(a)
    
    if enemigos_cercanos and agente_yo.personalidad.get("hostilidad", 0) > 0.5:
        e = enemigos_cercanos[0]
        urgencias.append(f"⚔️ ENEMIGO A LA VISTA: {e.unique_id} (grupo: {e.grupo_id or 'ninguno'}) está a {abs(e.x-agente_yo.x)+abs(e.y-agente_yo.y)} casillas. Tu hostilidad es alta — ¿ATACAS?")
    elif enemigos_cercanos and agente_yo.personalidad.get("hostilidad", 0) <= 0.5:
        e = enemigos_cercanos[0]
        urgencias.append(f"⚠️ ENEMIGO CERCA: {e.unique_id} está próximo. Puedes NEGOCIAR_PAZ o evitarlo moviéndote.")

    # Logros disponibles
    xp_max_area = max(agente_yo.experiencia, key=agente_yo.experiencia.get) if agente_yo.experiencia else None
    if xp_max_area and agente_yo.experiencia.get(xp_max_area, 0) >= 8 and not agente_yo.profesion:
        urgencias.append(f"🎓 PUEDES PROFESIONALIZARTE: Tienes {agente_yo.experiencia[xp_max_area]} XP en {xp_max_area}. Ve a una Universidad para GRADUARTE.")
    
    # --- SUGERENCIAS BASADAS EN PERSONALIDAD ---
    curiosidad = agente_yo.personalidad.get("curiosidad", 0.5)
    amabilidad = agente_yo.personalidad.get("amabilidad", 0.5)
    hostilidad = agente_yo.personalidad.get("hostilidad", 0.5)
    
    # Solo sugerir crear habilidades si tiene curiosidad alta y está bien de salud/comida
    if not agente_yo.skills and curiosidad > 0.7 and agente_yo.necesidades["alimento"] > 7 and agente_yo.necesidades["salud"] > 7:
        urgencias.append("🧠 CURIOSIDAD INSACIABLE: Sientes que puedes mejorar tu entorno. Considera CREAR_HABILIDAD (Python) para automatizar una ventaja única.")
    
    # Incitar a la socialización si es amable
    if amabilidad > 0.7 and len(agente_yo.memoria.grafo.nodes) < 5:
        urgencias.append("🤝 PERSONA AFABLE: Te sientes solo. Socializa con alguien cercano o busca fundar/unirte a un grupo para prosperar.")
    
    # Incitar al conflicto si es hostil
    if hostilidad > 0.7 and not enemigos_cercanos:
        urgencias.append("⚔️ IMPULSO AGRESIVO: Sientes que este mundo es para los fuertes. Busca un rival cercano con recursos y somételo con ATACAR.")

    if urgencias:
        contexto += "\n=== ⚡ SITUACIÓN ACTUAL — PRESIONES Y OPORTUNIDADES ===\n"
        contexto += "\n".join(urgencias)
        contexto += "\n=======================================================\n"

    return {
        "esta_poseido": poseido,
        "info_externa": contexto
    }

def actuar(state: AgentState):
    """Nodo 2: Toma la decisión basada en Intenciones (BDI)."""
    modelo = state['modelo_instance']
    agente_yo = modelo.get_agent_by_id(state['agente_yo_id'])
    agente_otro = modelo.get_agent_by_id(state.get('agente_otro_id'))
    
    # 1. POSESIÓN (Sobreescribe todo)
    if state.get('esta_poseido'):
        return {
            "pensamiento_actual": "Mi voluntad ha sido suplantada por el Arquitecto. Él guía mis pasos ahora.",
            "accion_elegida": {"nombre": "POSESIÓN_DIVINA", "argumentos": {}},
            "mensaje_llm": "Mi cuerpo no me pertenece... el Arquitecto me controla."
        }

    # 2. EJECUCIÓN DE INTENCIÓN (Si ya existe un plan y no ha cambiado el estado de forma crítica)
    intenciones_restantes = getattr(agente_yo, 'intentions', [])
    if intenciones_restantes:
        # Verificar si hay que abortar (Emergencia)
        es_emergencia = (agente_yo.necesidades["salud"] < 3.0 or 
                         agente_yo.necesidades["alimento"] < 3.0 or
                         agente_yo.necesidades["descanso"] < 2.0)
        
        if not es_emergencia:
            proxima = intenciones_restantes.pop(0)
            agente_yo.intentions = intenciones_restantes # Guardar lista restante
            
            p_msg = f"Siguiendo plan: {proxima.get('meta', 'sin meta')}"
            return {
                "pensamiento_actual": p_msg,
                "accion_elegida": {"nombre": proxima['accion'], "argumentos": proxima.get('params', {})},
                "mensaje_llm": f"Estoy enfocado en mi objetivo: {proxima.get('meta', '...')}",
                "intentions": intenciones_restantes
            }
        else:
            modelo.log(f"⚡ [BDI] Agente {agente_yo.unique_id} aborta planes por emergencia vital.", categoria="sistema")
            agente_yo.intentions = []

    # 3. DELIBERACIÓN (Llamar a la IA para nuevos deseos e intenciones)
    decision = cerebro_llm.generar_pensamiento_y_accion(agente_yo, agente_otro, state['info_externa'])
    
    # Extraer BDI de la respuesta de la IA (configurado en el prompt de cerebro_llm)
    nuevas_intenciones = decision.get("intentions", [])
    
    # Si la IA devolvió intenciones, guardarlas (quitando el primer paso que se ejecuta ahora)
    if nuevas_intenciones and len(nuevas_intenciones) > 1:
        agente_yo.intentions = nuevas_intenciones[1:]
    else:
        agente_yo.intentions = []

    return {
        "pensamiento_actual": decision.get("pensamiento", "No pude pensar."),
        "accion_elegida": decision.get("accion", {"nombre": "HABLAR", "argumentos": {"mensaje": "..."}}),
        "mensaje_llm": decision.get("mensaje", ""),
        "es_global": decision.get("es_global", False),
        "es_grupal": decision.get("es_grupal", False),
        "privado": bool(decision.get("destinatario_id")),
        "destinatario_id": decision.get("destinatario_id"),
        "beliefs": decision.get("beliefs", []),
        "desires": decision.get("desires", []),
        "intentions": nuevas_intenciones
    }

def decidir_ruta(state: AgentState) -> str:
    """Nodo 3: Decide si usar herramientas o ir a comunicación."""
    if state.get('esta_poseido'):
        return "comunicar"
        
    accion_nombre = state['accion_elegida'].get('nombre', 'HABLAR')
    
    # Verificar si el nombre de la acción es una skill conocida
    modelo = state['modelo_instance']
    agente_yo = modelo.get_agent_by_id(state['agente_yo_id'])
    
    is_skill = (accion_nombre in skill_manager.base_skills or 
                (agente_yo and accion_nombre in agente_yo.skills))
    
    if is_skill:
        return "ejecutar_herramientas"
    return "comunicar"
    
def ejecutar_herramientas(state: AgentState):
    """Nodo 4: Ejecuta habilidades (base y aprendidas)."""
    modelo = state['modelo_instance']
    agente_yo = modelo.get_agent_by_id(state['agente_yo_id'])
    accion = state['accion_elegida']
    nombre_accion = accion.get("nombre")
    argumentos = accion.get("argumentos", {})
    
    # Usar skill_manager para ejecutar
    resultado = skill_manager.ejecutar_skill(
        nombre_accion, 
        argumentos, 
        agente_id=agente_yo.unique_id, 
        agent_skills=agente_yo.skills
    )
    
    # Manejar el caso especial de crear_habilidad
    if nombre_accion == "CREAR_HABILIDAD" and isinstance(resultado, dict) and resultado.get("status") == "success":
        new_skill_data = resultado.get("new_skill")
        agente_yo.skills[new_skill_data["name"]] = new_skill_data
        mensaje_res = f"Habilidad '{new_skill_data['name']}' creada con éxito. ¡Ahora puedo usarla!"
        modelo.log(f"🧠 [EVOLUCIÓN] Agente {agente_yo.unique_id} ha desarrollado la habilidad: {new_skill_data['name']}", categoria="sistema")
        # Notificar al frontend inmediatamente
        modelo.notificar_cambio_estado()
        return {"info_externa": mensaje_res}

    return {"info_externa": str(resultado)}

def comunicar(state: AgentState):
    """Nodo 5: Genera el output final y gestiona la interactividad con el usuario."""
    modelo = state['modelo_instance']
    agente_yo = modelo.get_agent_by_id(state['agente_yo_id'])
    accion = state['accion_elegida']
    mensaje_llm = state.get('mensaje_llm', '')
    peticion = state.get('peticion_arquitecto')
    dilema = state.get('dilema_usuario')

    # Si hay una petición al usuario, la registramos en el log para que el usuario la vea
    if peticion:
        modelo.log(f"🙏 [PETICIÓN] Agente {agente_yo.unique_id}: '{peticion}'", categoria="sistema")
    
    if dilema:
        modelo.log(f"🤔 [DILEMA] Agente {agente_yo.unique_id} enfrenta un dilema: '{dilema}'", categoria="consenso")

    mensaje_final = mensaje_llm if mensaje_llm else f"Realizando {accion.get('nombre')}..."
    
    # Respetar la decisión explícita del LLM sobre el alcance del mensaje.
    # Solo forzar global si el LLM lo indica. No forzar por ser Líder o por mencionar "ley".
    es_global = state.get('es_global', False)
    es_grupal = state.get('es_grupal', False)
    # Si hay destinatario específico del LLM, el mensaje es privado
    privado = state.get('privado', False)

    return {
        "mensaje_generado": mensaje_final,
        "es_global": es_global,
        "es_grupal": es_grupal,
        "privado": privado,
        "destinatario_id": state.get('destinatario_id')
    }

# Construcción del Grafo Cognitivo Mejorado
workflow = StateGraph(AgentState)

workflow.add_node("analizar", analizar_situacion)
workflow.add_node("actuar", actuar)
workflow.add_node("ejecutar_herramientas", ejecutar_herramientas)
workflow.add_node("comunicar", comunicar)

workflow.set_entry_point("analizar")
workflow.add_edge("analizar", "actuar")
workflow.add_conditional_edges("actuar", decidir_ruta, {
    "comunicar": "comunicar",
    "ejecutar_herramientas": "ejecutar_herramientas"
})
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
            "beliefs": getattr(agente, 'beliefs_list', []),
            "desires": getattr(agente, 'desires', []),
            "intentions": getattr(agente, 'intentions', [])
        }
        
        config = {"configurable": {"thread_id": f"agent_{agente.unique_id}"}}
        final_state = cerebro_cognitivo.invoke(initial_state, config)
        
        accion = final_state.get('accion_elegida', {})
        nombre_accion = accion.get('nombre', 'HABLAR')
        argumentos = accion.get('argumentos', {})
        
        # Formato para el motor de simulación
        decision_str = f"{nombre_accion}:" + ":".join(map(str, argumentos.values())) if argumentos else nombre_accion

        agente.beliefs_list = final_state.get('beliefs', [])
        agente.desires = final_state.get('desires', [])
        agente.intentions = final_state.get('intentions', [])

        return (
            decision_str,
            final_state.get('mensaje_generado', ""),
            final_state.get('pensamiento_actual', ""),
            final_state.get('privado', False),
            final_state.get('es_grupal', False),
            final_state.get('es_global', False),
            final_state.get('planes', []),
            accion, # Retornar el diccionario original de la acción
            final_state.get('destinatario_id')  # ID del destinatario si el mensaje es privado
        )
