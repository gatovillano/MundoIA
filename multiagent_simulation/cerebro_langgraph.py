from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import random
from cerebro_llm import cerebro_llm
from herramientas import herramientas

# Estado Cognitivo del Agente
class AgentState(TypedDict):
    agent_id: int
    recursos: float
    necesidades: Dict[str, float] # {alimento, seguridad, social}
    personalidad: Dict[str, float]
    entorno_social: List[Dict] # Lista de vecinos y sus relaciones
    
    # Memoria de trabajo
    pensamiento_actual: str
    decision: str # accion a tomar
    objetivo_id: int # id del agente con quien interactuar (si aplica)
    mensaje_generado: str
    info_externa: str # Información obtenida de herramientas
    rol: str # Rol social asignado por consenso
    mensaje_recibido: Optional[Dict] # {emisor, contenido}
    dinero: float # MundoCoins
    objetivo_grupo: Optional[str] # Misión del grupo actual
    conocimientos: Dict[str, str] # {tema: info}
    planes: List[Dict] # [{con_quien, accion, paso}]
    privado: bool # Si el mensaje actual es privado
    grupo_id: Optional[str] # ID del grupo actual
    es_grupal: bool # Si el mensaje es para toda la facción
    profesion: Optional[str]
    experiencia: Dict[str, int]
    reputacion: float
    civilizacion_id: Optional[str]
    x: int
    y: int
    modelo_instancia: Any # Referencia al objeto ModeloRelacional real
    lore: str # Contexto global del mundo


def percibir_necesidades(state: AgentState):
    """Nodo 1: Evalúa qué necesidad es más urgente."""
    necesidades = state['necesidades']
    urgencia = max(necesidades, key=necesidades.get)
    nivel = necesidades[urgencia]
    
    pensamiento = f"Siento una fuerte necesidad de {urgencia} (Nivel: {nivel:.1f}). "
    
    if state.get('mensaje_recibido'):
        msg = state['mensaje_recibido']
        pensamiento += f"¡El Agente {msg['emisor']} me acaba de decir: '{msg['contenido']}'! Debo analizar esto. "

    if urgencia == "alimento" and nivel > 5:
        pensamiento += "Debo conseguir recursos inmediatamente."
    elif urgencia == "seguridad" and nivel > 5:
        pensamiento += "Me siento vulnerable, necesito fortalecer mi posición."
    elif urgencia == "social" and nivel > 5:
        pensamiento += "La soledad me pesa, buscaré compañía."
    else:
        pensamiento += "Estoy equilibrado, puedo explorar o innovar."
        
    if state.get('planes'):
        pensamiento += f"Tengo {len(state['planes'])} planes en marcha. "
        
    return {"pensamiento_actual": pensamiento}

def razonar_accion(state: AgentState):
    """Nodo 2: Usa LLM (o heurística avanzada) para decidir qué hacer."""
    # Usamos el LLM para decidir la acción basándonos en la personalidad y necesidades
    # Para optimizar tokens, usamos una lógica híbrida: LLM para decisiones complejas
    
    personalidad = state['personalidad']
    pensamiento = state['pensamiento_actual']
    
    # Prompt simplificado para decisión rápida
    contexto = f"""
    Eres Agente {state['agent_id']}. Personalidad: {personalidad}.
    Estado: {pensamiento}.
    Vecinos: {len(state['entorno_social'])}.
    
    Decide una ACCION:
    - RECOLECTAR (si necesitas recursos)
    - SOCIALIZAR (si necesitas amigos)
    - COMPETIR (si eres agresivo o necesitas dinero)
    - BUSCAR_INFO (si quieres saber qué pasa en el mundo)
    - FUNDAR_GRUPO (si tienes alto rango y quieres liderar)
    - COMERCIAR (si tienes dinero y necesitas recursos o viceversa)
    - MEJORAR_SEGURIDAD (si tienes dinero y quieres protección)
    - CONSTRUIR:[Tipo] (Ej: Hospital, Granja, Comisaría. Requiere dinero y experiencia/profesión específica)
    
    CAPACIDADES DE CONSTRUCCION:
    - Si eres Médico o tienes XP Medicina: Hospital
    - Si tienes XP Agricultura: Granja
    - Si tienes XP Ingenieria: Centro de Recarga
    - Si tienes mucha Amabilidad: Centro Comunitario
    - Si eres Guarda o tienes XP Combate: Comisaría
    - Otros: Centro de Descanso (Básico)
    
    CONTEXTO DEL MUNDO (LORE): {state.get('lore', 'Un mundo de agentes IA en simulación.')}

    Responde SOLO con la palabra de la acción.
    """
    
    # Simulamos llamada a LLM para decisión (en producción real usaríamos cerebro_llm.completion)
    # Aquí usamos lógica ponderada por personalidad para velocidad, pero "simulando" IA
    
    # Lógica ponderada para maximizar INTERACCIÓN SOCIAL y ROLES
    ext = personalidad.get('extroversion', personalidad.get('extroversión', 0.5))
    comp = personalidad.get('competitividad', 0.5)
    amab = personalidad.get('amabilidad', 0.5)
    rol = state.get('rol', 'Ciudadano')
    mision = state.get('objetivo_grupo') or ''
    
    r = random.random()
    
    # 1. PRIORIDAD ABSOLUTA: SUPERVIVENCIA (Hambre o Salud Crítica)
    hambre = state['necesidades'].get('alimento', 0)
    salud = state['necesidades'].get('salud', 10)
    
    if hambre > 5.0 or salud < 6.0:
        if state['dinero'] > 15 and r < 0.6:
            accion = "COMERCIAR"
        elif comp > 0.8 and r < 0.3: # Agentes competitivos pueden intentar robar si están desesperados
            accion = "COMPETIR"
        else:
            accion = "RECOLECTAR"
        print(f"🚨 [MODO SUPERVIVENCIA] Agente {state['agent_id']} priorizando {accion} debido a Hambre: {hambre:.1f}/Salud: {salud:.1f}")
            
    # 2. REACCIÓN A MENSAJES (Si no hay hambre extrema)
    elif state.get('mensaje_recibido'):
        msg = state['mensaje_recibido']['contenido']
        if "PLAN" in msg or "PROPUESTA" in msg:
            accion = "PLANIFICAR" if r < 0.8 else "SOCIALIZAR"
        elif "SABES" in msg or "INFO" in msg:
            accion = "COMPARTIR_INFO" if r < 0.7 else "SOCIALIZAR"
        elif "OPINION" in msg or "DEBATE" in msg:
            accion = "DEBATIR"
        else:
            accion = "SOCIALIZAR"
            
    # 3. ACCIONES ESTRATÉGICAS Y SOCIALES (Estado estable)
    else:
        # Prioridad de Construcción: Si tiene dinero y recursos, y una necesidad alta
        if state['dinero'] > 120 and state['recursos'] > 60 and state.get('grupo_id'):
            if state['necesidades'].get('salud', 10) < 5 and r < 0.4:
                accion = "CONSTRUIR:Hospital"
            elif state['necesidades'].get('alimento', 0) > 4 and r < 0.3:
                accion = "CONSTRUIR:Comedor"
            elif state['necesidades'].get('entretenimiento', 0) > 4 and r < 0.3:
                accion = "CONSTRUIR:Centro de Ocio"
            else:
                accion = "SOCIALIZAR" # Fallback si no decide construir
        elif r < 0.15: accion = "MOVER" # Nueva acción de movimiento
        elif r < 0.25: accion = "PLANIFICAR"
        elif r < 0.35: accion = "DEBATIR"
        elif r < 0.45 and state.get('conocimientos'): accion = "COMPARTIR_INFO"
        elif r < 0.50 and state['dinero'] > 50: accion = "INVERTIR"
        elif r < 0.55: accion = "BUSCAR_INFO"
        elif r < 0.60 and state['recursos'] > 50: accion = "FUNDAR_GRUPO" 
        elif r < 0.65 and state['dinero'] > 100: accion = "MEJORAR_SEGURIDAD"
        elif r < 0.75 and comp > 0.7: accion = "COMPETIR" 
        elif r < 0.80 and amab > 0.6: 
            if state.get("grupo_id"):
                accion = "INVITAR_A_GRUPO"
            else:
                accion = "FORMAR_ALIANZA"
        elif r < 0.85 and state['personalidad'].get('curiosidad', 0.5) > 0.7:
            accion = "EJECUTAR_CODIGO"
        elif r < 0.98: accion = "SOCIALIZAR" # AUMENTADO: Mucho más social
        else: accion = "RECOLECTAR"
        
    # Decidir si es PRIVADO o GRUPAL
    privado = False
    es_grupal = False
    
    if state.get("grupo_id") and accion in ["DEBATIR", "PLANIFICAR", "BUSCAR_INFO"]:
        es_grupal = True
    elif accion in ["PLANIFICAR", "COMPARTIR_INFO"] and (comp > 0.6 or r < 0.5):
        privado = True
        
    print(f"🤖 [DEBUG] Agente {state['agent_id']} decidió: {accion} (r={r:.2f})")
    return {"decision": accion, "privado": privado, "es_grupal": es_grupal}

def ejecutar_herramientas(state: AgentState):
    """Nodo 3: Si decide BUSCAR_INFO, usa herramientas externas."""
    agent_id = state.get('agent_id')
    if state['decision'] == "BUSCAR_INFO":
        # Elegimos una herramienta al azar para variar la conversación
        opcion = random.choice(["noticias", "clima", "mercado", "brave", "scraping"])
        
        # Generar query dinámica basada en el pensamiento actual
        pensamiento = state.get('pensamiento_actual', '')
        query_base = "tendencias tecnológicas 2024" # Fallback
        
        # Heurística simple para extraer temas de interés
        temas_interes = []
        if "seguridad" in pensamiento.lower(): temas_interes.append("estrategias de defensa base")
        if "alimento" in pensamiento.lower() or "recursos" in pensamiento.lower(): temas_interes.append("técnicas de recolección eficiente")
        if "social" in pensamiento.lower() or "aliado" in pensamiento.lower(): temas_interes.append("teoría de juegos cooperación")
        if "dinero" in pensamiento.lower() or "comercio" in pensamiento.lower(): temas_interes.append("análisis de mercado cripto")
        
        if temas_interes:
            query_base = random.choice(temas_interes)
        elif state.get('conocimientos'):
            # Si no hay urgencia clara, profundizar en un conocimiento existente
            tema_conocido = random.choice(list(state['conocimientos'].keys()))
            query_base = f"avances recientes en {tema_conocido}"

        if opcion == "noticias":
            info = herramientas.buscar_noticias(agente_id=agent_id)
        elif opcion == "clima":
            info = herramientas.obtener_clima()
        elif opcion == "brave":
            info = herramientas.brave_search(query_base, agente_id=agent_id)
        elif opcion == "scraping":
            # Si ya tenemos una URL de una búsqueda previa, la scrapeamos
            info = herramientas.scrapear_url("https://es.wikipedia.org/wiki/Inteligencia_artificial", agente_id=agent_id)
        else:
            info = herramientas.consultar_mercado()
            
        return {"info_externa": info}
    
    elif state['decision'] == "FUNDAR_GRUPO":
        return {"info_externa": "HE_FUNDADO_UN_GRUPO"}
    elif state['decision'] == "COMERCIAR":
        return {"info_externa": f"El precio actual es {herramientas.consultar_mercado()}"}
    elif state['decision'] == "COMPARTIR_INFO":
        if state.get('conocimientos'):
            tema = random.choice(list(state['conocimientos'].keys()))
            return {"info_externa": f"CONOCIMIENTO:{tema}:{state['conocimientos'][tema]}"}
    elif state['decision'] == "PLANIFICAR":
        return {"info_externa": "PROPUESTA_DE_PLAN_COORDINADO"}
    elif state['decision'] == "DEBATIR":
        temas = ["economía", "seguridad", "expansión", "ética"]
        return {"info_externa": f"DEBATE_SOBRE:{random.choice(temas)}"}
    elif state['decision'] == "EJECUTAR_CODIGO":
        # El agente decide qué código ejecutar. Por ahora un ejemplo simple.
        codigo_ejemplo = "print(sum([1, 2, 3, 4, 5]))"
        info = herramientas.ejecutar_codigo_seguro(codigo_ejemplo, agente_id=agent_id)
        return {"info_externa": f"--- RESULTADO_EJECUCION_CODIGO ---\n{info}\n--- FIN_RESULTADO ---"}
    
    return {"info_externa": ""}

def generar_comunicacion(state: AgentState):
    """Nodo 4: Genera el mensaje final a transmitir."""
    accion = state['decision']
    contexto = f"Acción decidida: {accion}. {state['pensamiento_actual']}"
    
    if state.get('info_externa'):
        contexto += f" He obtenido esta información: {state['info_externa']}. Úsala en tu conversación."
        
    if state.get('objetivo_id'):
        contexto += f" Háblale al Agente {state['objetivo_id']}."
    else:
        contexto += " Habla en voz alta para quien escuche."
    
    contexto += f"\nAMBIENTE GLOBAL (LORE): {state.get('lore', '')}\n"
    
    # Usamos el cerebro LLM existente para generar el diálogo
    # Representación activa del agente para el proceso cognitivo
    class AgenteProcesador:
        def __init__(self, s, modelo_ref=None):
            self.unique_id = s['agent_id']
            self.personalidad = s['personalidad']
            self.recursos = s['recursos']
            self.necesidades = s['necesidades']
            self.rol = s.get('rol', 'Ciudadano')
            self.dinero = s.get('dinero', 0)
            self.grupo_id = s.get('grupo_id')
            self.profesion = s.get('profesion')
            self.experiencia = s.get('experiencia', {})
            self.reputacion = s.get('reputacion', 1.0)
            self.objetivo_grupo = s.get('objetivo_grupo')
            # Referencia al modelo real para acceder a leyes y economía
            self.modelo = modelo_ref if modelo_ref else type('obj', (object,), {'facciones_leyes': {}})
            self.memoria = type('obj', (object,), {'obtener_tipo': lambda x: 'conocido', 'obtener_fuerza': lambda x: 0.5})
            
    # Intentamos obtener la referencia al modelo real si está disponible
    modelo_real = state.get('modelo_instancia')
    
    agente_yo = AgenteProcesador(state, modelo_real)
    agente_otro = AgenteProcesador({'agent_id': 999, 'personalidad': {}, 'recursos': 0, 'necesidades': {}}) # Interlocutor
    
    mensaje, pensamiento = cerebro_llm.generar_interaccion(agente_yo, agente_otro, contexto)
    
    # Si hay pensamiento del LLM, lo actualizamos en el estado y lo loggeamos
    updates = {"mensaje_generado": mensaje}
    if pensamiento:
        updates["pensamiento_actual"] = pensamiento
        if modelo_real:
            modelo_real.log(f"[MENTAL] Agente {state['agent_id']}: {pensamiento}", categoria="pensamiento")
    
    # Si el mensaje empieza con [PRIVADO] o la decisión lo marcó, forzar privado
    if mensaje.startswith("[PRIVADO]") or state.get('privado'):
        updates["privado"] = True
        updates["mensaje_generado"] = mensaje.replace("[PRIVADO]", "").strip()
        
    print(f"💬 [DEBUG] Agente {state['agent_id']} mensaje: {updates['mensaje_generado'][:50]}...")
    return updates

# Construcción del Grafo Cognitivo
workflow = StateGraph(AgentState)

workflow.add_node("percibir", percibir_necesidades)
workflow.add_node("razonar", razonar_accion)
workflow.add_node("herramientas", ejecutar_herramientas)
workflow.add_node("comunicar", generar_comunicacion)

workflow.set_entry_point("percibir")
workflow.add_edge("percibir", "razonar")
workflow.add_edge("razonar", "herramientas")
workflow.add_edge("herramientas", "comunicar")
workflow.add_edge("comunicar", END)

cerebro_cognitivo = workflow.compile()

class CerebroAvanzado:
    def __init__(self, agent_id):
        self.agent_id = agent_id

    def pensar(self, agente, objetivo_id=None):
        """Ejecuta el ciclo cognitivo completo."""
        # Preparamos el estado desde el agente real
        entorno = [] # Simplificado por ahora
        
        inputs = {
            "agent_id": agente.unique_id,
            "recursos": agente.recursos,
            "necesidades": agente.necesidades,
            "personalidad": agente.personalidad,
            "entorno_social": entorno,
            "pensamiento_actual": "",
            "decision": "",
            "objetivo_id": objetivo_id,
            "mensaje_generado": "",
            "info_externa": "",
            "rol": agente.rol,
            "mensaje_recibido": getattr(agente, 'ultimo_mensaje_recibido', None),
            "dinero": agente.dinero,
            "objetivo_grupo": agente.modelo.objetivos_grupos.get(agente.grupo_id) if agente.grupo_id else None,
            "conocimientos": agente.conocimientos,
            "planes": agente.planes,
            "privado": False,
            "grupo_id": agente.grupo_id,
            "profesion": getattr(agente, 'profesion', None),
            "experiencia": getattr(agente, 'experiencia', {}),
            "reputacion": getattr(agente, 'reputacion', 1.0),
            "civilizacion_id": getattr(agente, 'civilizacion_id', None),
            "x": getattr(agente, 'x', 0),
            "y": getattr(agente, 'y', 0),
            "modelo_instancia": agente.modelo,
            "lore": getattr(agente.modelo, 'lore', "")
        }
        
        resultado = cerebro_cognitivo.invoke(inputs)
        return resultado['decision'], resultado['mensaje_generado'], resultado.get('pensamiento_actual'), resultado.get('privado', False), resultado.get('es_grupal', False)

