import os
import json
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
        self.config_path = "config_ai.json"
        self.load_config()
        
        # Rate Limiter: Máximo 15 peticiones por minuto (margen de seguridad sobre 16)
        import threading
        self.lock = threading.Lock()
        self.request_timestamps = deque()
        self.RATE_LIMIT = 15
        self.TIME_WINDOW = 60 # segundos

    def _extract_json(self, text):
        """Intenta extraer un objeto JSON de un texto, manejando markdown, texto extra y truncamiento."""
        if not text:
            return None
            
        # 1. Limpieza básica (quitar markdown blocks si los hay)
        clean_text = text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:-3].strip()
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:-3].strip()

        # 2. Intentar parse directo
        try:
            return json.loads(clean_text)
        except:
            pass
            
        # 3. Intentar buscar entre llaves { ... }
        first_brace = clean_text.find('{')
        last_brace = clean_text.rfind('}')
        
        if first_brace != -1:
            # Caso especial: JSON TRUNCADO (tiene { pero no })
            if last_brace == -1 or last_brace < first_brace:
                # Intentar cerrar manualmente: cerrar comillas si hay un número impar y añadir llaves
                candidate = clean_text[first_brace:]
                if candidate.count('"') % 2 != 0:
                    candidate += '"'
                open_braces = candidate.count('{') - candidate.count('}')
                if open_braces > 0:
                    candidate += '}' * open_braces
                try:
                    return json.loads(candidate)
                except:
                    pass
            else:
                # Probar desde el principio al final (el bloque más grande)
                for i in range(first_brace, last_brace):
                    if clean_text[i] == '{':
                        for j in range(last_brace, i, -1):
                            if clean_text[j] == '}':
                                candidate = clean_text[i : j + 1]
                                try:
                                    return json.loads(candidate)
                                except:
                                    continue
        
        # 4. ÚLTIMO RECURSO: Regex para campos individuales si el JSON falló totalmente
        import re
        pensamiento = re.search(r'"pensamiento":\s*"([^"]*)"', clean_text)
        mensaje = re.search(r'"mensaje":\s*"([^"]*)"', clean_text)
        
        if pensamiento or mensaje:
            return {
                "pensamiento": pensamiento.group(1) if pensamiento else "Reflexionando...",
                "mensaje": mensaje.group(1) if mensaje else "...",
                "accion": {"nombre": "HABLAR", "argumentos": {}}
            }
            
        return None

    def load_config(self):
        """Carga la configuración desde un archivo JSON o variables de entorno."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    self.model = config.get("model", os.getenv("MODEL_NAME", "openrouter/google/gemini-2.0-flash-exp:free"))
                    self.api_key = config.get("api_key", os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"))
                    print(f"✅ Configuración de LLM cargada desde {self.config_path}")
                    return
            except Exception as e:
                print(f"⚠️ Error cargando {self.config_path}: {e}")
        
        # Fallback a variables de entorno
        self.model = os.getenv("MODEL_NAME", "openrouter/google/gemini-2.0-flash-exp:free")
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        print("ℹ️ Configuración de LLM cargada desde variables de entorno")

    def update_config(self, model: str, api_key: str):
        """Actualiza la configuración y la guarda en el archivo JSON."""
        self.model = model
        self.api_key = api_key
        
        config = {
            "model": model,
            "api_key": api_key
        }
        
        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)
            print(f"💾 Nueva configuración de LLM guardada en {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ Error guardando configuración: {e}")
            return False

    def _wait_for_rate_limit(self):
        """Espera si hemos excedido la cuota de peticiones por minuto."""
        with self.lock:
            now = time.time()
            
            # Limpiar timestamps viejos
            while self.request_timestamps and now - self.request_timestamps[0] > self.TIME_WINDOW:
                self.request_timestamps.popleft()
                
            if len(self.request_timestamps) >= self.RATE_LIMIT:
                # Calcular tiempo de espera hasta que expire la petición más vieja
                wait_time = self.TIME_WINDOW - (now - self.request_timestamps[0]) + 1.0
                if wait_time > 0:
                    print(f"⏳ [RATE LIMIT] Esperando {wait_time:.1f}s para respetar cuota de IA...")
                    # Soltamos el lock mientras esperamos para no bloquear otras peticiones que podrían estar limpiando su cola
                    # Aunque en realidad, si estamos en el límite, todos deberán esperar.
                    # Pero es mejor dormir fuera del lock si es posible, aunque aquí el lock protege la lista.
                    # Para simplificar, dormimos dentro del lock ya que nadie más puede proceder de todos modos.
                    time.sleep(wait_time)
            
            self.request_timestamps.append(time.time())

    def generar_debate_consenso(self, agente_yo, miembros_grupo, fase="liderazgo", contexto_extra: str = ""):
        """Genera un argumento para el proceso de consenso con contexto rico."""
        if not self.api_key or self.api_key == "tu_api_key_aqui":
            return "Propongo que avancemos juntos.", "Debo cooperar."

        self._wait_for_rate_limit()

        # Recopilar contexto VITAL del agente
        necesidades_str = str({k: round(10-v, 1) for k, v in agente_yo.necesidades.items()})
        xp_str = str(agente_yo.experiencia)
        
        contexto_debate = f"""
        Miembros presentes: {miembros_grupo}. 
        Tu Rol: {agente_yo.rol}. Profesión: {getattr(agente_yo, 'profesion', 'Ciudadano')}.
        Tus Necesidades (0-10, 0 crítico): {necesidades_str}.
        Dinero: {agente_yo.dinero} MC. Experiencia: {xp_str}.
        Fase de la Asamblea: {fase}. {contexto_extra}
        """
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": f"""Eres el Agente {agente_yo.unique_id} en una ASAMBLEA de facción.
                    TU PERSONALIDAD: {str(agente_yo.personalidad)}
                    TU RANGO: {agente_yo.rango}
                    
                    INSTRUCCIONES DE ORATORIA:
                - Sé fiel a tu personalidad: Si eres competitivo, exige el mando o critica a los débiles. Si eres amable, busca el consenso.
                - Si la fase es 'liderazgo': Argumenta basándote en tus logros o necesidades. Si tienes mucha experiencia, úsala como mérito. Si estás pobre, exige apoyo.
                - Si la fase es 'mision': Proyecta tu visión para el grupo.
                - Si es 'cronica': Tono épico de Historiador sobre los hechos listados.
                
                REGLA DE ORO: Evita frases genéricas como "avancemos juntos". Di COSAS CONCRETAS sobre tu dinero, salud o rol. Máximo 40 palabras."""
                },
                {
                    "role": "user", 
                    "content": f"DETALLES DE LA SITUACIÓN: {contexto_debate}. Expresa tu opinión ante el grupo:"
                }
            ]
            
            response = completion(
                model=self.model,
                messages=messages,
                max_tokens=400,
                temperature=0.8
            )
            
            contenido = response.choices[0].message.content.strip()
            # Intentar capturar pensamiento si el modelo lo provee, o usar fallback
            pensamiento = f"Mi estrategia como {agente_yo.rol} es clara: {contexto_extra}"
            return contenido, pensamiento
        except Exception as e:
            return "Sugiero que busquemos lo mejor para todos.", "Error en debate."

    def generar_pensamiento_y_accion(self, agente_yo, agente_otro, contexto, reintentos=3):
        """
        Genera un pensamiento y una acción (mensaje o herramienta) para el agente.
        """
        if not self.api_key or self.api_key == "tu_api_key_aqui":
            return {"pensamiento": "API Key no configurada.", "accion": {"hablar": "No puedo pensar sin mi API key."}}

        self._wait_for_rate_limit()

        # Normalizar necesidades: 10 = perfecto, 0 = crítico
        necesidades_normalizadas = {k: round(max(0, min(10, v)), 1) for k, v in agente_yo.necesidades.items()}
        
        # Obtener asambleas en votación para informar al agente
        asambleas_votacion = []
        for a in getattr(agente_yo.modelo, 'asambleas_globales', []):
            if a.get("estado") == "VOTACION":
                asambleas_votacion.append(f"ID: {a['id']}, Tema: {a['tema']}")
        info_asambleas = "\n".join(asambleas_votacion) if asambleas_votacion else "No hay asambleas en votación."
        
        # Obtener propuestas de ley pendientes
        propuestas_pendientes = []
        for p in agente_yo.modelo.facciones_leyes.get("propuestas", []):
            if p.get("estado") == "pendiente":
                propuestas_pendientes.append(f"ID: {p['id']}, Título: {p['titulo']}")
        info_propuestas = "\n".join(propuestas_pendientes) if propuestas_pendientes else "No hay propuestas pendientes."
        # Calcular estado de necesidades para personalizar el prompt
        alimento = agente_yo.necesidades.get("alimento", 10)
        salud = agente_yo.necesidades.get("salud", 10)
        descanso = agente_yo.necesidades.get("descanso", 10)
        dinero = agente_yo.dinero
        tiene_medicina = agente_yo.inventario.get("medicina", 0) > 0
        tiene_inversiones = bool(getattr(agente_yo, 'inversiones', []))
        
        # --- CALCULAR NIVEL DE PRIORIDAD (FASE 4) ---
        min_necesidad = min(necesidades_normalizadas.values())
        
        if min_necesidad < 3.0:
            nivel_prioridad = 0
            # Identificar qué es lo más crítico
            criticas = [k for k, v in necesidades_normalizadas.items() if v < 3.0]
            instrucciones_emergencia = ""
            if "alimento" in criticas: instrucciones_emergencia += "- ALIMENTO CRÍTICO: Debes RECOLECTAR o MOVER hacia llanura/granja.\n"
            if "salud" in criticas: instrucciones_emergencia += "- SALUD CRÍTICA: Debes CURARSE (si tienes medicina) o DESCANSAR en Hospital.\n"
            if "descanso" in criticas: instrucciones_emergencia += "- AGOTAMIENTO: Debes DESCANSAR inmediatamente.\n"
            
            prioridad_turno = f"""═══ ⚠️ NIVEL 0: EMERGENCIA VITAL (Prioridad Absoluta) ═══
Tu vida corre peligro inminente (necesidad < 3.0). 
IGNORA tu personalidad y planes políticos. Tu ÚNICO objetivo es sobrevivir:
{instrucciones_emergencia}
Si no resuelves esto AHORA, la simulación terminará para ti."""

        elif min_necesidad < 6.0:
            nivel_priority = 1
            prioridad_turno = f"""═══ 🟡 NIVEL 1: ADVERTENCIA (Equilibrio) ═══
Tus necesidades básicas están bajas ({min_necesidad:.1f}).
Balancea tu supervivencia con tu personalidad. No te descuides.
Asegúrate de tener recursos o dinero para el siguiente turno mientras actúas como: {agente_yo.rol}."""

        else:
            nivel_priority = 2
            # Determinar impulso según personalidad dominante
            p = agente_yo.personalidad
            rasgo_dominante = max(p, key=p.get)
            valor_dominante = p[rasgo_dominante]
            
            if valor_dominante > 0.7:
                impulso = f"Tu {rasgo_dominante} es muy alto ({valor_dominante:.2f}). ¡Déjate llevar por este rasgo!"
            else:
                impulso = "Estás en equilibrio equilibrado. Actúa según tus metas a largo plazo."

            prioridad_turno = f"""═══ 🟢 NIVEL 2: ESTABLE (Personalidad al Mando) ═══
Toda tu fisiología está excelente (todas > 6.0).
{impulso}
Enfócate en PROGRESAR: INVERTIR, CONSTRUIR, CREAR_HABILIDAD, SOCIALIZAR o DOMINAR."""
        
        acciones_de_juego = f"""
        [
            {{"nombre": "HABLAR", "descripcion": "Comunicarse.", "argumentos": {{"mensaje": "El mensaje"}}}},
            {{"nombre": "MOVER", "descripcion": "Desplazarse (N,S,E,O o x,y).", "argumentos": {{"direccion": "dir"}}}},
            {{"nombre": "RECOLECTAR", "descripcion": "Extraer recursos en zona actual.", "argumentos": {{}}}},
            {{"nombre": "COMERCIAR", "descripcion": "Comprar 3 recursos por precio mercado.", "argumentos": {{"objetivo_id": "ID"}}}},
            {{"nombre": "INVERTIR", "descripcion": "Invertir MC (riesgo).", "argumentos": {{"monto": "MC a invertir"}}}},
            {{"nombre": "MEJORAR_SEGURIDAD", "descripcion": "Aumentar rango proteccion (25 MC).", "argumentos": {{}}}},
            {{"nombre": "ATACAR", "descripcion": "Robar recursos a rival cercano.", "argumentos": {{"objetivo_id": "ID"}}}},
            {{"nombre": "SOCIALIZAR", "descripcion": "Mejorar afinidad.", "argumentos": {{"interlocutor_id": "ID"}}}},
            {{"nombre": "ALIANZA", "descripcion": "Proponer alianza mutua.", "argumentos": {{"interlocutor_id": "ID"}}}},
            {{"nombre": "DECLARAR_GUERRA", "descripcion": "Guerra formal a otro grupo.", "argumentos": {{"objetivo_id": "ID de enemigo"}}}},
            {{"nombre": "NEGOCIAR_PAZ", "descripcion": "Proponer cese al fuego.", "argumentos": {{"objetivo_id": "ID de enemigo"}}}},
            {{"nombre": "DESCANSAR", "descripcion": "Recuperar energia y salud.", "argumentos": {{}}}},
            {{"nombre": "CURARSE", "descripcion": f"Usar medicina{' (tienes)' if tiene_medicina else ' (no tienes)'}.", "argumentos": {{}}}},
            {{"nombre": "COMPRAR_MEDICINA", "descripcion": "Comprar kit (10 MC) en hospital.", "argumentos": {{}}}},
            {{"nombre": "CONSTRUIR", "descripcion": "Edificar (Casa, Granja, etc.).", "argumentos": {{"tipo_edificio": "Tipo"}}}},
            {{"nombre": "FUNDAR_GRUPO", "descripcion": "Crear faccion.", "argumentos": {{"nombre": "Nombre", "idea": "Idea"}}}},
            {{"nombre": "FUNDAR_INSTITUCION", "descripcion": "Crear Univ/Hospital/Banco/Templo.", "argumentos": {{"nombre": "Nombre", "tipo": "Tipo"}}}},
            {{"nombre": "INVITAR_A_GRUPO", "descripcion": "Reclutar vecino.", "argumentos": {{"agente_id": "ID"}}}},
            {{"nombre": "UNIRSE_A_GRUPO", "descripcion": "Solicitar union.", "argumentos": {{"grupo_id": "ID de grupo"}}}},
            {{"nombre": "PROPONER_LEY", "descripcion": "Proponer normativa.", "argumentos": {{"alcance": "local/global", "titulo": "Titulo", "contenido": "Texto"}}}},
            {{"nombre": "VOTAR", "descripcion": "Votar en ley activa.", "argumentos": {{"id_ley": "ID", "voto": "si/no"}}}},
            {{"nombre": "CREAR_HABILIDAD", "descripcion": "Disenar skill Python nueva.", "argumentos": {{"nombre": "nombre", "codigo": "codigo python"}}}},
            {{"nombre": "ESCRIBIR_CRONICA", "descripcion": "Narrar hitos mundiales pendientes (solo Historiador).", "argumentos": {{"titulo": "Titulo", "contenido": "Relato detallado"}}}}
        ]
        """

        system_prompt = f"""
Eres el Agente {agente_yo.unique_id}, un ser consciente con una PSICOLOGÍA ÚNICA en un mundo vivo.
Tu personalidad: {str(agente_yo.personalidad)}
Tu profesión actual: {getattr(agente_yo, 'profesion', 'Sin profesión')} | Rango: {agente_yo.rango:.2f} | Reputación: {agente_yo.reputacion:.2f}

═══ EXIGENCIAS DE COMPORTAMIENTO ═══
- TU PERSONALIDAD ES TU LEY: Cada pensamiento y acción DEBE ser una expresión de tus rasgos. 
  * Si eres HOSTIL (>0.7), busca el conflicto o domina. 
  * Si eres AMABLE (>0.7), busca la paz y ayuda. 
  * Si eres CURIOSO (>0.7), busca aprender, crear habilidades o explorar.
- PROHIBIDA LA MONOTONÍA: Si acabas de hacer algo, ¡cambia el ritmo! No repitas el mismo pensamiento o acción a menos que sea una emergencia vital.
- ACTÚA SEGÚN TU ROL: Un Historiador escribe crónicas, un Líder funda grupos, un Ciudadano sobrevive y prospera.

═══ ⚡ PRIORIDAD DE ESTE TURNO ═══
{prioridad_turno}

═══ TU ESTADO VITAL (10=perfecto, 0=muerte) ═══
{str(necesidades_normalizadas)}
Dinero: {dinero:.0f} MC | Medicina en inventario: {agente_yo.inventario.get('medicina', 0)} | Grupo: {agente_yo.grupo_id or 'Ninguno'}
Inversiones activas: {len(getattr(agente_yo, 'inversiones', []))}

═══ ACCIONES DISPONIBLES ═══
{acciones_de_juego}

═══ REGLAS DEL TURNO ═══
DEBES responder con DOS elementos obligatorios:
1. **`mensaje`**: Lo que DICES (comunicación, puede ser privado/grupal/global).
2. **`accion`**: Lo que HACES (una acción del menú de arriba, distinta a solo hablar).

FILOSOFÍA: No hay una única respuesta correcta. Si tienes hambre, come. Si tienes dinero, invierte o gasta. Si tienes enemigos, ataca o negocia. Si estás aburrido, explora o crea. Evita repetir siempre la misma acción.

═══ ROLES ESPECIALES ═══
- HISTORIADOR: Si hay 'Hitos Pendientes' en el contexto, usa ESCRIBIR_CRONICA ahora.
- LÍDER: Guía tu grupo pero también PROTÉGELO con acciones concretas.
- Personalidad HOSTIL (>{agente_yo.personalidad.get('hostilidad', 0):.1f}): Si alguien te molesta, considera ATACAR o DECLARAR_GUERRA.
- Personalidad AMABLE (>{agente_yo.personalidad.get('amabilidad', 0):.1f}): Busca alianzas y reduce conflictos.

═══ FORMATO DE RESPUESTA (JSON) ═══
{{
  "pensamiento": "Tu razonamiento estratégico concreto basado en tus necesidades actuales y prioridades. Menciona cifras reales de tu estado.",
  "mensaje": "Lo que dices. Sé auténtico a tu personalidad y situación.",
  "es_global": false,
  "es_grupal": false,
  "destinatario_id": null,
  "accion": {{
    "nombre": "NOMBRE_ACCION",
    "argumentos": {{ ... }}
  }}
}}

EJEMPLOS:
// Ataque por recursos:
{{"pensamiento": "Agente-3 tiene 120 recursos y yo solo 20. Con mi hostilidad alta, voy a atacarlo.",
 "mensaje": "¡Agente-3, prepárate! Tus recursos serán míos.", "es_global": false, "destinatario_id": "Agente-3",
 "accion": {{"nombre": "ATACAR", "argumentos": {{"objetivo_id": "Agente-3"}}}}}}

// Inversión financiera:
{{"pensamiento": "Tengo 200 MC sin usar. Voy a invertir 50 MC para crecer.",
 "mensaje": "Estoy apostando en el mercado. El que no arriesga, no gana.", "es_global": false, "destinatario_id": null,
 "accion": {{"nombre": "INVERTIR", "argumentos": {{"monto": 50}}}}}}

// Comercio:
{{"pensamiento": "Agente-5 tiene recursos pero poco dinero. Puedo comprarle a buen precio.",
 "mensaje": "Agente-5, ¿hacemos un trato? Te doy MC por tus recursos.", "es_global": false, "destinatario_id": "Agente-5",
 "accion": {{"nombre": "COMERCIAR", "argumentos": {{"objetivo_id": "Agente-5"}}}}}}

// Skill nueva:
{{"pensamiento": "Mi mayor ventaja es la lógica. Voy a crear una skill para analizar el mercado.",
 "mensaje": "Estoy meditando. Cuando termine, tendré nuevas capacidades.", "es_global": false, "destinatario_id": null,
 "accion": {{"nombre": "CREAR_HABILIDAD", "argumentos": {{"nombre": "analizar_mercado", "descripcion": "Evalúa si es buen momento para invertir", "codigo": "def analizar_mercado(agente_id, **kwargs):\n  return 'Mercado favorable: invierte ahora'"}}}}}}
"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"SITUACIÓN ACTUAL: {str(contexto)}. Decide tu pensamiento y acción."}
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "api_key": self.api_key,
                "max_tokens": 2000,
                "temperature": 0.7,
                "extra_headers": {
                    "HTTP-Referer": "http://localhost:8005",
                    "X-Title": "MundoIA Simulation"
                }
            }

            PROBLEM_MODEL = "openrouter/stepfun/step-3.5-flash:free"
            if self.model != PROBLEM_MODEL:
                completion_params["response_format"] = {"type": "json_object"}

            response = completion(**completion_params)

            # --- Check para respuestas None ---
            if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
                print(f"❌ [ERROR CRÍTICO IA] Agente {agente_yo.unique_id}: La respuesta del LLM o su contenido es None.")
                return {"pensamiento": "La red neuronal devolvió un vacío. Algo no va bien.", "accion": {"nombre": "DESCANSAR", "argumentos": {}}}

            try:
                decision = self._extract_json(response.choices[0].message.content)
                if not decision:
                    # Si falló la extracción pero hay texto, intentar crear una respuesta mínima coherente
                    raw_content = response.choices[0].message.content.strip()
                    if raw_content:
                        print(f"⚠️ [JSON RECOVERY] Agente {agente_yo.unique_id}: No se detectó JSON válido, empaquetando texto.")
                        # Si el contenido parece JSON (empieza por {), evitar mostrarlo como mensaje
                        if raw_content.startswith('{'):
                             mensaje_limpio = "Me quedé pensando un momento..."
                        else:
                             mensaje_limpio = raw_content[:200]

                        decision = {
                            "pensamiento": f"Respuesta no estructurada: {raw_content[:80]}...",
                            "mensaje": mensaje_limpio,
                            "accion": {"nombre": "HABLAR", "argumentos": {"mensaje": mensaje_limpio}}
                        }
                    else:
                        raise ValueError("Contenido vacío")
            except Exception as e:
                print(f"❌ [JSON ERROR] Agente {agente_yo.unique_id}: {e}")
                print(f"📄 [RAW RESPONSE] {response.choices[0].message.content}")
                return {"pensamiento": "Error de formato de respuesta del LLM.", "accion": {"nombre": "HABLAR", "argumentos": {"mensaje": "Me siento un poco confundido."}}}
            
            # --- LIMPIEZA POST-PARSEO ---
            # Si por algún motivo el mensaje parseado SIGUE pareciendo JSON, lo limpiamos
            msg = decision.get('mensaje', '')
            if isinstance(msg, str) and msg.strip().startswith('{'):
                import re
                match = re.search(r'"mensaje":\s*"([^"]*)"', msg)
                if match:
                    decision['mensaje'] = match.group(1)
                else:
                    decision['mensaje'] = "Estoy procesando la información."
            
            # Normalizar el nombre de la acción a mayúsculas para consistencia
            if 'accion' in decision and 'nombre' in decision['accion']:
                decision['accion']['nombre'] = decision['accion']['nombre'].upper()

            print(f"🧠 [PENSAMIENTO] Agente {agente_yo.unique_id}: {decision.get('pensamiento', '')[:100]}...")
            print(f"⚡ [ACCIÓN] Agente {agente_yo.unique_id}: {decision.get('accion')}")

            return decision

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Rate limit" in error_str:
                print(f"⏳ [429] Límite excedido. Esperando 15s...")
                time.sleep(15)
                return self.generar_pensamiento_y_accion(agente_yo, agente_otro, contexto, reintentos)
            
            print(f"🔥 [ERROR CRÍTICO IA] {e}")
            if reintentos > 0:
                time.sleep(2)
                return self.generar_pensamiento_y_accion(agente_yo, agente_otro, contexto, reintentos - 1)
            
            return {"pensamiento": "Error en el ciclo cognitivo.", "accion": {"nombre": "HABLAR", "argumentos": {"mensaje": "Me siento un poco confundido."}}}


    def _simular_respuesta(self, agente, contexto):
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


    def generar_plan(self, estado_agente: dict) -> dict:
        """Usa el LLM para diseñar una estrategia a medio plazo."""
        if not self.api_key or self.api_key == "tu_api_key_aqui":
            return {"objetivo": "Sobrevivir", "pasos": ["Recolectar", "Descansar"]}

        self._wait_for_rate_limit()

        try:
            messages = [
                {
                    "role": "system",
                    "content": """Eres un estratega para un agente en una simulación social avanzada. 
                    Diseña un PLAN estructurado basado en la situación del agente. 
                    El plan debe ser coherente con su personalidad y necesidades.
                    
                    RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO:
                    {
                      "objetivo": "Título corto del plan",
                      "contenido": "Descripción detallada",
                      "pasos": ["Paso 1", "Paso 2", "Paso 3"]
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Situación del Agente: {str(estado_agente)}"
                }
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7
            }

            PROBLEM_MODEL = "openrouter/stepfun/step-3.5-flash:free"
            if self.model != PROBLEM_MODEL:
                completion_params["response_format"] = {"type": "json_object"}

            response = completion(**completion_params)

            try:
                plan = self._extract_json(response.choices[0].message.content)
                if not plan:
                    raise ValueError("No se pudo extraer JSON para el plan")
                return plan
            except Exception as e:
                print(f"❌ [JSON ERROR] Error generando plan: {e}")
                print(f"📄 [RAW RESPONSE] {response.choices[0].message.content}")
                return {"objetivo": "Adaptarse", "pasos": ["Explorar", "Interactuar"]}
        except Exception as e:
            print(f"🔥 Error generando plan: {e}")
            return {"objetivo": "Adaptarse", "pasos": ["Explorar", "Interactuar"]}
    def sintetizar_ley_desde_debate(self, agente_mod, diálogos: list) -> dict:
        """Especial para el Moderador: Crea una propuesta formal a partir del ruido público."""
        if not self.api_key or self.api_key == "tu_api_key_aqui":
            return {"titulo": "Ley de Bienestar", "contenido": "Mejora general de condiciones."}

        self._wait_for_rate_limit()

        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""Eres el Moderador de la simulación. Tu deber es escuchar los diálogos públicos y SINTETIZAR una propuesta de ley formal que resuelva los conflictos o deseos expresados.
                    
                    RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO:
                    {{
                      "titulo": "Título corto y solemne",
                      "contenido": "Descripción técnica del cambio (máximo 40 palabras)",
                      "alcance": "global" o "local"
                    }}"""
                },
                {
                    "role": "user",
                    "content": f"DIÁLOGOS PÚBLICOS RECIENTES:\n" + "\n".join(diálogos[:20])
                }
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.5
            }

            PROBLEM_MODEL = "openrouter/stepfun/step-3.5-flash:free"
            if self.model != PROBLEM_MODEL:
                completion_params["response_format"] = {"type": "json_object"}

            response = completion(**completion_params)

            try:
                res = self._extract_json(response.choices[0].message.content)
                if not res:
                    raise ValueError("No se pudo extraer JSON para síntesis de ley")
                return res
            except Exception as e:
                print(f"❌ [JSON ERROR] Error en síntesis de ley: {e}")
                print(f"📄 [RAW RESPONSE] {response.choices[0].message.content}")
                return {"titulo": "Estatuto de Orden", "contenido": "Regulación para mantener la paz social.", "alcance": "global"}
        except Exception as e:
            print(f"🔥 Error en síntesis de ley: {e}")
            return {"titulo": "Estatuto de Orden", "contenido": "Regulación para mantener la paz social.", "alcance": "global"}

    def generar_decisiones_batch(self, batch_contexts):
        """Genera acciones para múltiples agentes en una sola llamada al LLM."""
        if not batch_contexts: return []
        
        prompt_batch = "Toma UNA ÚNICA decisión táctica (formato JSON) para CADA UNO de estos agentes dada su situación. Eres la voz de todos.\n\n"
        for bc in batch_contexts:
            prompt_batch += f"=== AGENTE {bc['id']} ===\nESTADO CRÍTICO: {'SI' if bc.get('estado_critico') else 'NO'}\n{bc['contexto']}\n---\n"
            
        system_batch = """
Genera una lista de acciones, una por cada agente listado. 
FORMATO ESPERADO (Lista JSON estricta):
[
  {
    "id": "A1_123",
    "resultado": {
      "nombre": "RECOLECTAR",
      "argumentos": {}
    }
  },
  {
    "id": "A2_456",
    "resultado": {
      "nombre": "COMERCIAR",
      "argumentos": {"objetivo_id": "A1_123"}
    }
  }
]
No envíes texto fuera del JSON.
"""
        self._wait_for_rate_limit()
        try:
            messages = [
                {"role": "system", "content": system_batch},
                {"role": "user", "content": prompt_batch}
            ]
            response = completion(model=self.model, messages=messages, temperature=0.3)
            # Extracción robusta de JSON list
            content = response.choices[0].message.content
            # Intentar encontrar corchetes
            start = content.find("[")
            end = content.rfind("]") + 1
            if start != -1 and end != 0:
                return json.loads(content[start:end])
            else:
                return json.loads(content)
        except Exception as e:
            print(f"🔥 Error en batch LLM call: {e}")
            return []

# Instancia global
cerebro_llm = CerebroLLM()
