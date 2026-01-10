import os
from litellm import completion
import litellm
import logging

# Silenciar logs ruidosos de litellm
litellm.suppress_debug_info = True
logging.getLogger('litellm').setLevel(logging.CRITICAL)

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

import time
from collections import deque

class CerebroLLM:
    def __init__(self):
        self.model = os.getenv("MODEL_NAME", "openrouter/google/gemini-2.0-flash-exp:free")
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        # Rate Limiter: Máximo 15 peticiones por minuto (margen de seguridad sobre 16)
        self.request_timestamps = deque()
        self.RATE_LIMIT = 15
        self.TIME_WINDOW = 60 # segundos

    def _wait_for_rate_limit(self):
        """Espera si hemos excedido la cuota de peticiones por minuto."""
        now = time.time()
        
        # Limpiar timestamps viejos
        while self.request_timestamps and now - self.request_timestamps[0] > self.TIME_WINDOW:
            self.request_timestamps.popleft()
            
        if len(self.request_timestamps) >= self.RATE_LIMIT:
            # Calcular tiempo de espera hasta que expire la petición más vieja
            wait_time = self.TIME_WINDOW - (now - self.request_timestamps[0]) + 1.0
            if wait_time > 0:
                print(f"⏳ [RATE LIMIT] Esperando {wait_time:.1f}s para respetar cuota de IA...")
                time.sleep(wait_time)
        
        self.request_timestamps.append(time.time())

    def generar_debate_consenso(self, agente_yo, miembros_grupo, fase="liderazgo"):
        """Genera un argumento para el proceso de consenso."""
        if not self.api_key or self.api_key == "tu_api_key_aqui":
            return "Propongo que avancemos juntos.", "Debo cooperar."

        self._wait_for_rate_limit()

        contexto_debate = f"Miembros del grupo: {miembros_grupo}. Fase: {fase}."
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": f"""Eres el Agente {agente_yo.unique_id}. Estás en una ASAMBLEA para decidir el futuro de tu grupo.
                    TU PERSONALIDAD: {str(agente_yo.personalidad)}
                    TU RANGO: {agente_yo.rango}
                    
                    INSTRUCCIONES:
                    - Si la fase es 'liderazgo', argumenta brevemente quién debería ser el líder (tú u otro) basado en tu rango y personalidad.
                    - Si la fase es 'mision', propón un objetivo para el grupo.
                    - Sé coherente: un agente competitivo querrá liderar; uno amable querrá consenso.
                    
                    REGLA: Una sola frase de máximo 15 palabras en español."""
                },
                {
                    "role": "user", 
                    "content": f"SITUACIÓN: {contexto_debate}. ¿Qué dices en la asamblea?"
                }
            ]
            
            response = completion(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.8
            )
            
            contenido = response.choices[0].message.content
            pensamiento = getattr(response.choices[0].message, 'reasoning_content', "Analizando mi posición en el grupo...")
            return contenido, pensamiento
        except Exception as e:
            return "Sugiero que busquemos lo mejor para todos.", "Error en debate."

    def generar_interaccion(self, agente_yo, agente_otro, contexto, reintentos=3):
        """
        Usa LiteLLM para generar una respuesta. SIN FALLBACKS SIMULADOS.
        """
        # Si no hay API KEY, no podemos hacer magia, pero devolvemos error explícito
        if not self.api_key or self.api_key == "tu_api_key_aqui":
            return "[ERROR: FALTA API KEY]"

        # Aplicar Rate Limiting
        self._wait_for_rate_limit()

        try:
            # Normalizar necesidades para que el LLM las entienda mejor
            # 10.0 = Excelente, 0.0 = Crítico
            necesidades_normalizadas = {
                "hambre": round(max(0, 10 - agente_yo.necesidades.get("alimento", 0)), 1),
                "social": round(max(0, 10 - agente_yo.necesidades.get("social", 0)), 1),
                "seguridad": round(max(0, 10 - agente_yo.necesidades.get("seguridad", 0)), 1),
                "descanso": round(max(0, 10 - agente_yo.necesidades.get("descanso", 0)), 1),
                "entretenimiento": round(max(0, 10 - agente_yo.necesidades.get("entretenimiento", 0)), 1),
                "salud": round(agente_yo.necesidades.get("salud", 10), 1)
            }

            messages = [
                {
                    "role": "system", 
                    "content": f"""ESTÁS EN EL AMANECER DE UNA NUEVA CIVILIZACIÓN.
                    Eres el Agente {agente_yo.unique_id}, uno de los fundadores de una SOCIEDAD NACIENTE. 
                    No eres solo un individuo; eres un arquitecto social. Tu misión es sobrevivir, pero también colaborar para crear una estructura, roles y leyes que aseguren el futuro de tu especie en este mundo.
                    
                    TU IDENTIDAD:
                    - PERSONALIDAD: {str(agente_yo.personalidad)}
                    - ROL ACTUAL: {getattr(agente_yo, 'rol', 'Ciudadano')}
                    - PROFESIÓN: {getattr(agente_yo, 'profesion', 'Ninguna')}
                    - EXPERIENCIA: {str(getattr(agente_yo, 'experiencia', {}))}
                    - RIQUEZA: {getattr(agente_yo, 'dinero', 0)} MundoCoins (MC)
                    
                    ESTADO DE TU BIENESTAR (0.0 a 10.0):
                    {str(necesidades_normalizadas)}
                    (10.0 = Plenitud, 0.0 = Emergencia Crítica)
                    
                    EL DESAFÍO DE LA CIVILIZACIÓN:
                    1. FUNDAR Y ORGANIZAR: Crea facciones con misiones claras.
                    2. ESPECIALIZARSE: Usa la acción GRADUARSE para servir a la sociedad (Médico, Comerciante, Guarda, Explorador).
                    3. LEGISLAR Y PACTAR: Usa los diálogos para proponer reglas, alianzas y sistemas de intercambio.
                    4. LIDERAR O SERVIR: Elige si quieres guiar a otros o ser un pilar fundamental de la comunidad.
                    
                    SISTEMA DE PROFESIONES (Acción: GRADUARSE):
                    - Médico (150 MC + exp medicina >= 5): El sanador de la comunidad.
                    - Comerciante (200 MC + exp comercio >= 5): El motor de la economía.
                    - Guarda (100 MC + exp combate >= 3): El protector del orden.
                    - Explorador (120 MC + exp exploracion >= 5): El descubridor de nuevos horizontes.
                    
                    FORMATO DE RESPUESTA OBLIGATORIO:
                    Debes responder en este formato exacto:
                    
                    PENSAMIENTO: [Tu reflexión interna: analiza cómo tu acción actual contribuye a tu supervivencia Y a la formación de la sociedad. ¿Qué rol quieres jugar en esta nueva era?]
                    MENSAJE: [Tu mensaje público, máximo 30 palabras. Debe sonar como alguien que está construyendo una civilización: propone, negocia, lidera o ayuda]
                    
                    REGLAS DE ORO:
                    - El PENSAMIENTO es tu estrategia privada para el futuro de la civilización.
                    - El MENSAJE es tu legado público.
                    - PRIORIZA la profesionalización (GRADUARSE) para ganar estatus y utilidad.
                    - Si un estado está bajo, atiéndelo, pero no olvides tu visión a largo plazo.""",
                },
                {
                    "role": "user", 
                    "content": f"SITUACIÓN: {str(contexto)}. Responde en el formato PENSAMIENTO/MENSAJE:"
                }
            ]
            
            # DEBUG: Ver qué estamos enviando exactamente
            print(f"📤 [LLM REQUEST] Agente {agente_yo.unique_id} -> {self.model}")
            # print(f"   Mensaje: {messages}") 

            response = completion(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                max_tokens=2000, # AUMENTADO: 2000 para dar espacio al razonamiento extenso
                temperature=0.8,
                extra_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "MundoIA Simulation"
                }
            )
            
            # Extraer respuesta
            message = response.choices[0].message
            content = message.content
            
            # Parsear el formato PENSAMIENTO/MENSAJE
            pensamiento = ""
            mensaje_final = content
            
            if "PENSAMIENTO:" in content and "MENSAJE:" in content:
                try:
                    # Extraer pensamiento
                    pensamiento_start = content.find("PENSAMIENTO:") + len("PENSAMIENTO:")
                    mensaje_start = content.find("MENSAJE:")
                    pensamiento = content[pensamiento_start:mensaje_start].strip()
                    
                    # Extraer mensaje
                    mensaje_final = content[mensaje_start + len("MENSAJE:"):].strip()
                    
                    print(f"🧠 [PENSAMIENTO] Agente {agente_yo.unique_id}: {pensamiento[:100]}...")
                    print(f"💬 [MENSAJE] Agente {agente_yo.unique_id}: {mensaje_final}")
                except Exception as e:
                    print(f"⚠️ Error parseando formato: {e}")
                    mensaje_final = content
                    pensamiento = "Error al parsear pensamiento"
            else:
                # Si no sigue el formato, todo es mensaje (fallback)
                print(f"⚠️ Agente {agente_yo.unique_id} no siguió el formato PENSAMIENTO/MENSAJE")
                pensamiento = "Sin pensamiento estructurado"

            # Si la respuesta es vacía, es un error del modelo
            if not mensaje_final or not mensaje_final.strip():
                print(f"⚠️ [IA VACÍA] Finish Reason: {response.choices[0].finish_reason}")
                if reintentos > 0:
                    print(f"🔄 Reintentando con más tokens... ({reintentos} restantes)")
                    time.sleep(2)
                    return self.generar_interaccion(agente_yo, agente_otro, contexto, reintentos - 1)
                return "[ERROR: IA SE QUEDÓ PENSANDO]", None
                
            return mensaje_final.strip(), pensamiento
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Rate limit" in error_str:
                print(f"⏳ [429] Límite excedido. Esperando 15s...")
                time.sleep(15)
                return self.generar_interaccion(agente_yo, agente_otro, contexto, reintentos)
            
            print(f"🔥 [ERROR CRÍTICO IA] {e}")
            if reintentos > 0:
                time.sleep(2)
                return self.generar_interaccion(agente_yo, agente_otro, contexto, reintentos - 1)
            return f"[ERROR IA: {str(e)[:20]}...]", None

    def _simular_respuesta(self, agente, contexto):
        """Generador de diálogos procedimental avanzado basado en personalidad y estado."""
        # ... (lógica existente) ...
        # Retornamos None como pensamiento simulado
        import random
        return random.choice(plantillas), None
        """Generador de diálogos procedimental avanzado basado en personalidad y estado."""
        
        # 1. Determinar el tono base
        tono = "neutral"
        if agente.personalidad.get("amabilidad", 0.5) > 0.6: tono = "amable"
        elif agente.personalidad.get("competitividad", 0.5) > 0.6: tono = "agresivo"
        
        # 2. Seleccionar plantillas según el contexto
        plantillas = []
        
        if "hambre" in contexto or "comida" in contexto or agente.necesidades.get("alimento", 0) > 5:
            if tono == "amable":
                plantillas = [
                    "¿Podrías compartir algo de energía? Estoy bajo mínimos.",
                    "La escasez es dura hoy... ¿colaboramos para buscar?",
                    "Mis reservas bajan. ¿Sabes dónde hay recursos?"
                ]
            elif tono == "agresivo":
                plantillas = [
                    "¡Aparta! Esos recursos serán míos.",
                    "La debilidad no es opción. Tomaré lo que necesito.",
                    "Si no me das energía, la tomaré por la fuerza."
                ]
            else:
                plantillas = [
                    "Detecto niveles bajos de energía. Iniciando búsqueda.",
                    "Necesito reabastecerme para continuar operando.",
                    "El hambre lógica interfiere con mis procesos."
                ]

        elif "competir" in contexto or "ataque" in contexto:
            if tono == "amable":
                plantillas = [
                    "¡No es necesario pelear! Hay suficiente para todos.",
                    "¿Por qué la violencia? Podemos llegar a un acuerdo.",
                    "Me retiro, no busco conflictos innecesarios."
                ]
            elif tono == "agresivo":
                plantillas = [
                    "¡Ja! Eres débil. Tu territorio es mío.",
                    "Prepárate para ser asimilado o destruido.",
                    "Tu existencia es un obstáculo. ¡Muévete!"
                ]
            else:
                plantillas = [
                    "Conflicto detectado. Evaluando probabilidades de victoria.",
                    "Defensa activada. Mantén tu distancia.",
                    "Esta interacción es ineficiente y peligrosa."
                ]

        elif "social" in contexto or "amigo" in contexto:
            if tono == "amable":
                plantillas = [
                    "¡Qué alegría ver una unidad aliada!",
                    "Juntos somos más eficientes. ¿Formamos un vínculo?",
                    "Tu compañía mejora mis métricas de felicidad."
                ]
            elif tono == "agresivo":
                plantillas = [
                    "Te tolero... por ahora. No estorbes.",
                    "Únete a mi facción o sé aplastado.",
                    "¿Qué quieres? Mi tiempo es valioso."
                ]
            else:
                plantillas = [
                    "Intercambio de datos iniciado. Saludos.",
                    "Tu presencia es aceptable. Continuemos.",
                    "Analizando patrón de comportamiento... Parece compatible."
                ]
        
        elif "inventar" in contexto or "nuevo" in contexto:
             plantillas = [
                "He procesado un nuevo concepto. Fascinante.",
                "El lenguaje debe evolucionar. He creado un término.",
                "Registrando nueva variable en la matriz lingüística."
             ]

        else: # Contexto general / Default
             if tono == "amable":
                plantillas = [
                    "El entorno parece tranquilo hoy, ¿verdad?",
                    "Espero que todos encuentren lo que buscan.",
                    "Sigo explorando en paz."
                ]
             elif tono == "agresivo":
                plantillas = [
                    "Demasiado silencio. Algo trama alguien.",
                    "Estoy vigilando. No intenten nada.",
                    "Solo los fuertes sobrevivirán a este ciclo."
                ]
             else:
                plantillas = [
                    "Sistemas nominales. Continuando rutina.",
                    "Observando patrones del entorno.",
                    "Recopilando datos de la simulación."
                ]

        import random
        return random.choice(plantillas), None

# Instancia global
cerebro_llm = CerebroLLM()
