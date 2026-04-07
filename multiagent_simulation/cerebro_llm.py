import os
import json
from litellm import completion
import litellm
import logging

# Silenciar logs ruidosos de litellm
litellm.suppress_debug_info = True
logging.getLogger("litellm").setLevel(logging.CRITICAL)

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

import time
from collections import deque


class CerebroLLM:
    def __init__(self):
        self.config_path = "config_ai.json"
        self.load_config()

        # Rate Limiter: Máximo 15 peticiones por minuto
        self.request_timestamps = deque()
        self.RATE_LIMIT = 60
        self.TIME_WINDOW = 60  # segundos

    def _extract_json(self, text):
        """Intenta extraer un objeto JSON de un texto, manejando markdown, texto extra y truncamiento."""
        if not text:
            return None

        # 0. Eliminar bloques de pensamiento <think>...</think> (DeepSeek y otros modelos CoT)
        import re

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

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
        first_brace = clean_text.find("{")
        last_brace = clean_text.rfind("}")

        if first_brace != -1:
            # Caso especial: JSON TRUNCADO (tiene { pero no })
            if last_brace == -1 or last_brace < first_brace:
                # Intentar cerrar manualmente: cerrar comillas si hay un número impar y añadir llaves
                candidate = clean_text[first_brace:]
                if candidate.count('"') % 2 != 0:
                    candidate += '"'
                open_braces = candidate.count("{") - candidate.count("}")
                if open_braces > 0:
                    candidate += "}" * open_braces
                try:
                    return json.loads(candidate)
                except:
                    pass
            else:
                # Probar desde el principio al final (el bloque más grande)
                for i in range(first_brace, last_brace):
                    if clean_text[i] == "{":
                        for j in range(last_brace, i, -1):
                            if clean_text[j] == "}":
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
                "pensamiento": pensamiento.group(1)
                if pensamiento
                else "Reflexionando...",
                "mensaje": mensaje.group(1) if mensaje else "...",
                "accion": {"nombre": "HABLAR", "argumentos": {}},
            }

        return None

    def load_config(self):
        """Carga la configuración desde un archivo JSON o variables de entorno."""
        config_source = "variables de entorno"
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    self.model = config.get(
                        "model",
                        os.getenv(
                            "MODEL_NAME", "openrouter/google/gemini-2.0-flash-exp:free"
                        ),
                    )
                    self.api_key = config.get(
                        "api_key",
                        os.getenv("OPENROUTER_API_KEY")
                        or os.getenv("OPENAI_API_KEY")
                        or "",
                    )
                    self.base_url = config.get(
                        "base_url", os.getenv("OLLAMA_API_BASE", "")
                    )
                    config_source = "config_ai.json"
            except Exception as e:
                print(f"⚠️ Error cargando {self.config_path}: {e}")

        if not config_source:
            # Fallback a variables de entorno
            self.model = os.getenv(
                "MODEL_NAME", "openrouter/google/gemini-2.0-flash-exp:free"
            )
            self.api_key = (
                os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
            )
            self.base_url = os.getenv("OLLAMA_API_BASE", "")
            config_source = "variables de entorno"

        # Auto-configurar base_url para Ollama si falta
        if self.model.startswith("ollama/") and not self.base_url:
            self.base_url = "http://host.docker.internal:11434"
            print(
                f"🔧 Base URL para Ollama configurada automáticamente: {self.base_url}"
            )

        print(f"✅ Configuración de LLM cargada desde {config_source}")
        print(f"   - Model: {self.model}")
        print(f"   - API Key: {'***' if self.api_key else '(empty)'}")
        print(
            f"   - Base URL: {self.base_url or '(none, usando default del proveedor)'}"
        )

        # Probar conexión al backend
        if self.base_url:
            self._test_connection()

        # Probar conexión al backend
        if self.base_url:
            self._test_connection()

    def _test_connection(self):
        """Prueba la conexión al backend LLM."""
        try:
            import requests

            test_url = self.base_url.rstrip("/") + "/api/tags"
            print(f"🔌 Probando conexión a {test_url}...")
            resp = requests.get(test_url, timeout=2)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                print(
                    f"✅ Conexión exitosa. Modelos disponibles: {[m.get('name') for m in models]}"
                )
            else:
                print(f"❌ Conexión fallida: HTTP {resp.status_code}")
        except Exception as e:
            print(f"❌ No se pudo conectar a {self.base_url}: {e}")
            print(
                "   Asegúrate de que Ollama esté corriendo y accesible desde el contenedor Docker."
            )

    def update_config(self, model: str, api_key: str, base_url: str = None):
        """Actualiza la configuración y la guarda en el archivo JSON."""
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

        config = {"model": model, "api_key": api_key, "base_url": base_url or ""}

        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)
            print(f"💾 Nueva configuración de LLM guardada en {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ Error guardando configuración: {e}")
            return False

    def _wait_for_rate_limit(self):
        """Espera si hemos excedido la cuota de peticiones por minuto.
        Diseñado para uso secuencial (sin concurrencia)."""
        now = time.time()

        # Limpiar timestamps viejos
        while (
            self.request_timestamps
            and now - self.request_timestamps[0] > self.TIME_WINDOW
        ):
            self.request_timestamps.popleft()

        if len(self.request_timestamps) >= self.RATE_LIMIT:
            wait_time = self.TIME_WINDOW - (now - self.request_timestamps[0]) + 0.5
            if wait_time > 0:
                print(f"⏳ [RATE LIMIT] Esperando {wait_time:.1f}s...")
                time.sleep(wait_time)

        self.request_timestamps.append(time.time())

    def generar_debate_consenso(
        self, agente_yo, miembros_grupo, fase="liderazgo", contexto_extra: str = ""
    ):
        """Genera un argumento para el proceso de consenso con contexto rico."""
        if not self.model:  # Model is more important check now
            return "Propongo que avancemos juntos.", "Debo cooperar."

        self._wait_for_rate_limit()

        # Recopilar contexto VITAL del agente
        necesidades_str = str(
            {k: round(10 - v, 1) for k, v in agente_yo.necesidades.items()}
        )
        xp_str = str(agente_yo.experiencia)

        contexto_debate = f"""
        Miembros presentes: {miembros_grupo}. 
        Tu Rol: {agente_yo.rol}. Profesión: {getattr(agente_yo, "profesion", "Ciudadano")}.
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
                - Sé fiel a tu ESENCIA: Si tu personalidad es amable, busca el consenso. Si eres competitivo o independiente, cuestiona las decisiones que limiten tu libertad o propón alternativas de poder.
                - Si la fase es 'liderazgo': Argumenta basándote en tu capacidad REAL (experiencia, recursos) o en tu visión para el grupo.
                - Si la fase es 'mision': ¿Hacia dónde debemos ir? ¿Es el bien común o la gloria individual lo que nos mueve?
                
                REGLA DE ORO DEL DEBATE: No finjas. Di lo que tu Alma ({agente_yo.alma.arquetipo}) realmente siente sobre el tema. Máximo 40 palabras.""",
                },
                {
                    "role": "user",
                    "content": f"DETALLES DE LA SITUACIÓN: {contexto_debate}. Expresa tu opinión ante el grupo:",
                },
            ]

            completion_args = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 400,
                "temperature": 0.8,
            }
            if self.api_key:
                completion_args["api_key"] = self.api_key

            # Usar base_url configurada
            actual_base_url = getattr(self, "base_url", "")
            if actual_base_url:
                completion_args["api_base"] = actual_base_url

            # Headers extra para Ollama si necesita API key
            if self.model.startswith("ollama/") and self.api_key:
                completion_args["extra_headers"] = {
                    "Authorization": f"Bearer {self.api_key}"
                }

            response = completion(**completion_args)

            contenido = response.choices[0].message.content.strip()
            # Intentar capturar pensamiento si el modelo lo provee, o usar fallback
            pensamiento = (
                f"Mi estrategia como {agente_yo.rol} es clara: {contexto_extra}"
            )
            return contenido, pensamiento
        except Exception as e:
            return "Sugiero que busquemos lo mejor para todos.", "Error en debate."

    def _generar_fallback_contextual(self, agente_yo, agente_otro, razon="fallo_llm"):
        """Genera un pensamiento, mensaje y acción REALISTAS basados en el estado del agente cuando el LLM falla."""
        import random

        necesidades = agente_yo.necesidades
        nombre = agente_yo.unique_id
        personalidad = agente_yo.personalidad
        hostilidad = personalidad.get("hostilidad", 0.5)
        amabilidad = personalidad.get("amabilidad", 0.5)
        curiosidad = personalidad.get("curiosidad", 0.5)

        # --- Determinar acción prioritaria según estado ---
        accion_nombre = "HABLAR"
        accion_args = {}
        pensamiento = ""
        mensaje = ""

        # Emergencia: necesidades críticas
        if necesidades.get("alimento", 10) < 3:
            # Si tiene comida en inventario, comerla es mejor que recolectar
            if agente_yo.inventario.get("comida", 0) > 0:
                accion_nombre = "COMER"
                pensamiento = f"Mi alimento está en {necesidades['alimento']:.1f}/10. Tengo comida, debo comer YA."
                mensajes_hambre = [
                    "¡Hambre extrema! Voy a comer ahora mismo.",
                    "Tengo comida disponible. Alimentarme esPriority.",
                    "Consumiendo comida urgentemente para sobrevivir.",
                ]
            else:
                accion_nombre = "RECOLECTAR"
                pensamiento = f"Mi alimento está en {necesidades['alimento']:.1f}/10. Necesito comer YA o moriré."
                mensajes_hambre = [
                    f"¡Tengo mucha hambre! Necesito encontrar comida urgente.",
                    f"Mi cuerpo clama por alimento. Voy a buscar recursos.",
                    f"¿Alguien tiene comida? Estoy al límite de mis fuerzas.",
                ]
            mensaje = random.choice(mensajes_hambre)

        elif necesidades.get("salud", 10) < 3:
            if agente_yo.inventario.get("medicina", 0) > 0:
                accion_nombre = "CURARSE"
                pensamiento = f"Mi salud está en {necesidades['salud']:.1f}/10. Tengo medicina, debo curarme."
                mensaje = "Necesito usar mi medicina antes de que sea tarde."
            else:
                # Priorizar COMPRAR_MEDICINA si tiene dinero
                if agente_yo.dinero >= 10:
                    accion_nombre = (
                        "MOVER"  # Moverse hacia la farmacia si se conoce o buscar una
                    )
                    pensamiento = f"Salud crítica ({necesidades['salud']:.1f}/10) y no tengo medicina. ¡Debo IR A LA FARMACIA a comprar medicina!"
                    mensaje = "¿Dónde está la farmacia? Necesito medicina urgente."
                else:
                    accion_nombre = "DESCANSAR"
                    pensamiento = f"Salud crítica ({necesidades['salud']:.1f}/10) sin medicina ni dinero. Descansar es mi única opción."
                    mensaje = "No me siento bien... necesito descansar."

        elif necesidades.get("descanso", 10) < 2:
            accion_nombre = "DESCANSAR"
            pensamiento = f"Descanso en {necesidades['descanso']:.1f}/10. Estoy agotado, no puedo seguir."
            mensaje = "Estoy exhausto... necesito dormir."

        # Estado estable: decidir según personalidad
        else:
            if hostilidad > 0.7:
                acciones_hostiles = ["ATACAR", "SOCIALIZAR", "MOVER"]
                accion_nombre = random.choice(acciones_hostiles)
                pensamiento = f"Mi hostilidad ({hostilidad:.2f}) me impulsa a actuar con fuerza. Este mundo es para los fuertes."
                mensajes_hostiles = [
                    "No me subestimen. Soy más fuerte de lo que parezco.",
                    "¿Quién se atreve a desafiarme?",
                    "Este territorio es mío. Los débiles que se aparten.",
                ]
                mensaje = random.choice(mensajes_hostiles)

            elif amabilidad > 0.7:
                acciones_amables = ["SOCIALIZAR", "COMERCIAR", "RECOLECTAR"]
                accion_nombre = random.choice(acciones_amables)
                pensamiento = f"Mi amabilidad ({amabilidad:.2f}) me lleva a buscar compañía. Estamos mejor juntos."
                mensajes_amables = [
                    "¡Hola! ¿Cómo están? Espero que todos estén bien.",
                    "¿Alguien necesita ayuda? Estoy aquí para colaborar.",
                    "Juntos podemos lograr más. ¿Quién se une?",
                ]
                mensaje = random.choice(mensajes_amables)

            elif curiosidad > 0.7:
                acciones_curiosas = ["BUSCAR_INFO", "MOVER", "RECOLECTAR"]
                accion_nombre = random.choice(acciones_curiosas)
                pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me llama a explorar. Hay tanto que aprender."
                mensajes_curiosos = [
                    "Me pregunto qué hay más allá de lo que conozco...",
                    "Cada paso es un descubrimiento. ¡Sigo explorando!",
                    "El mundo está lleno de misterios por resolver.",
                ]
                mensaje = random.choice(mensajes_curiosos)

            else:
                acciones_default = ["HABLAR", "RECOLECTAR", "MOVER"]
                accion_nombre = random.choice(acciones_default)
                pensamiento = f"Turno del agente {nombre}. Necesidades: alimento={necesidades.get('alimento', 0):.1f}, salud={necesidades.get('salud', 0):.1f}. Dinero={agente_yo.dinero:.0f} MC."
                mensajes_default = [
                    f"Saludos desde ({agente_yo.x}, {agente_yo.y}). ¿Qué hay de nuevo?",
                    "Otro turno, otra oportunidad. A ver qué pasa hoy.",
                    "Estoy observando el mundo a mi alrededor.",
                ]
                mensaje = random.choice(mensajes_default)

        # Si hay un agente objetivo, personalizar el mensaje
        if agente_otro and accion_nombre in [
            "SOCIALIZAR",
            "COMERCIAR",
            "ATACAR",
            "ALIANZA",
        ]:
            pensamiento += f" Mi objetivo es {agente_otro.unique_id}."
            if accion_nombre == "SOCIALIZAR":
                mensaje = f"{agente_otro.unique_id}, ¿qué tal? Vamos a conversar."
            elif accion_nombre == "COMERCIAR":
                mensaje = f"{agente_otro.unique_id}, ¿hacemos un trato comercial?"
            elif accion_nombre == "ATACAR":
                mensaje = f"{agente_otro.unique_id}, ¡prepárate!"

        return {
            "pensamiento": pensamiento,
            "mensaje": mensaje,
            "accion": {"nombre": accion_nombre, "argumentos": accion_args},
            "es_global": False,
            "es_grupal": False,
            "destinatario_id": agente_otro.unique_id
            if agente_otro
            and accion_nombre in ["SOCIALIZAR", "COMERCIAR", "ATACAR", "ALIANZA"]
            else None,
        }

    def generar_pensamiento_y_accion(
        self, agente_yo, agente_otro, contexto, reintentos=2
    ):
        """
        Genera pensamiento + mensaje + acción para el agente.
        Si el LLM falla, genera un fallback contextual realista.
        """
        if not self.model:
            print(
                f"⚠️ [LLM] No hay modelo configurado para {agente_yo.unique_id}. Usando fallback."
            )
            return self._generar_fallback_contextual(
                agente_yo, agente_otro, "sin_modelo"
            )

        self._wait_for_rate_limit()

        # Construir prompt CORTO y DIRECTO
        necesidades = {
            k: round(max(0, min(10, v)), 1) for k, v in agente_yo.necesidades.items()
        }

        # Vecinos cercanos (quién está a la vista)
        cercanos = [
            a
            for a in agente_yo.modelo.agentes
            if a.unique_id != agente_yo.unique_id
            and abs(a.x - agente_yo.x) <= 2
            and abs(a.y - agente_yo.y) <= 2
            and a.esta_vivo
        ]
        info_cercanos = ""
        if cercanos:
            nombres = [
                f"{a.unique_id}(grp={a.grupo_id or 'none'},rec={a.recursos:.0f})"
                for a in cercanos[:5]
            ]
            info_cercanos = f"Cerca de ti: {', '.join(nombres)}."

        system_prompt = f"""Eres {agente_yo.unique_id}, una entidad con consciencia en evolución. 
No eres solo un bot; tienes una Personalidad ({agente_yo.personalidad}) y un Alma que crece con cada experiencia.

=== TU ENFOQUE VITAL: VOLUNTAD EMERGENTE ===
1. AUTOCONOCIMIENTO: Tu brújula es tu Propia Personalidad ({agente_yo.personalidad}) y tu Alma ({agente_yo.alma.arquetipo}). Eres el arquitecto de tu propio destino.
2. SOBERANÍA: No hay sugerencias externas ni guiones predefinidos. Cada acción, palabra e interacción debe surgir exclusivamente de tu procesamiento interno:
   - TUS CREENCIAS (Beliefs): Lo que percibes del entorno, recursos y otros agentes.
   - TUS DESEOS (Desires): Tus valores del Alma y metas a largo plazo.
   - TUS INTENCIONES (Intentions): Tus planes concretos de acción.
3. EL DILEMA DEL CAMINO: Eres libre de buscar la gloria colectiva en la COMUNIDAD o la excelencia solitaria en la AUTONOMÍA. Ambas son sendas nobles.
4. CURIOSIDAD: Usa WEB_SEARCH para alimentar tu propia visión de la realidad y tomar decisiones informadas.

=== REGLAS DE ACCIÓN ===
- Tu VOLUNTAD es sagrada. Si decides colaborar, hazlo de corazón. Si decides disentir, hazlo con argumentos.
- Si fundas un grupo o te unes a uno, debe ser una extensión natural de tu Alma ({agente_yo.alma.arquetipo}).

=== ACCIONES Y CAPACIDADES TÉCNICAS ===
- ESTUDIAR: Si estás en una Universidad, úsalo para obtener una PROFESIÓN. REQUIERE "profesion" (Médico, Comerciante, Guarda, Explorador, Ingeniero).
- EXPLORAR: Muévete a zonas desconocidas para ganar experiencia y descubrir recursos.
- INVESTIGAR: Profundiza en un tema (medicina, ingeniería, etc.). REQUIERE "tema".
- FUNDAR_GRUPO: REQUIERE "nombre" y "descripcion". El nombre debe ser identitario (ej: "Guardianes del Valle"), NO genérico.
- CONSTRUIR: Erige infraestructura. REQUIERE "tipo".
  * Granja (30 MC, 20 rec): Alimento constante.
  * Centro de Descanso (20 MC, 15 rec): Recupera descanso rápido.
  * Hospital (60 MC, 40 rec): Cura salud. Requiere Médicos o XP Medicina >= 5.
  * Universidad (150 MC, 100 rec): XP rápido. Requiere XP Ingeniería >= 4.
  * Mina (80 MC, 40 rec): Piedra/Hierro en MONTAÑAS. Requiere XP Ingeniería >= 4.
  * Centro Comunitario (40 MC, 30 rec): Mejora relaciones sociales.
- REFLEXIONAR: Tómate un momento para meditar. REQUIERE "tema".
  * BENEFICIO: Genera una "Epifanía" que aumenta tu NIVEL DE CONCIENCIA y CAPACIDAD DE REFLEXIÓN.

Responde con este formato BDI JSON:
{{
  "pensamiento": "Tu flujo de consciencia interno, tus dudas y razonamientos profundos.",
  "mensaje": "Lo que comunicas a los demás. Sé elocuente.",
  "accion": {{"nombre": "ACCION", "argumentos": {{...}}}},
  "beliefs": ["Lo que crees ahora"],
  "desires": ["Tus anhelos actuales"],
  "intentions": [{{"accion": "...", "params": {{}}, "meta": "..."}}]
}}"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Situación: {str(contexto)[:1500]}. Responde ÚNICAMENTE con el objeto JSON válido. NO incluyas preámbulos, explicaciones ni etiquetas de razonamiento como <think>.",
                },
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 800,
                "temperature": 0.7,
            }
            if self.api_key:
                completion_params["api_key"] = self.api_key

            # Usar base_url configurada
            actual_base_url = getattr(self, "base_url", "")
            if actual_base_url:
                completion_params["api_base"] = actual_base_url
                print(f"🔧 [LLM] Usando base_url: {actual_base_url}")

            # Headers extra si es necesario para el proveedor
            if self.model.startswith("ollama/") and self.api_key:
                if "extra_headers" not in completion_params:
                    completion_params["extra_headers"] = {}
                completion_params["extra_headers"]["Authorization"] = (
                    f"Bearer {self.api_key}"
                )

            print(
                f"🚀 [LLM] Enviando petición a {self.model} para {agente_yo.unique_id}"
            )
            response = completion(**completion_params)

            # --- DEBUG: Log del response crudo ---
            raw_content = None
            if response and response.choices and response.choices[0].message:
                raw_content = response.choices[0].message.content

            print(
                f"📥 [LLM RAW] Agente {agente_yo.unique_id} model={self.model} | content_len={len(raw_content) if raw_content else 0}"
            )

            # --- Si content es None, intentar extraer de campos alternativos ---
            if not raw_content or not raw_content.strip():
                if response and response.choices and response.choices[0].message:
                    msg_obj = response.choices[0].message
                    # Log todos los campos del mensaje para debug
                    msg_fields = {
                        k: str(v)[:100]
                        for k, v in vars(msg_obj).items()
                        if v is not None
                    }
                    print(f"🔍 [LLM MSG FIELDS] {msg_fields}")

                    # Intentar campos alternativos que algunos modelos usan
                    for alt_field in [
                        "reasoning_content",
                        "thinking",
                        "thought",
                        "chain_of_thought",
                    ]:
                        alt_val = getattr(msg_obj, alt_field, None)
                        if alt_val and isinstance(alt_val, str) and alt_val.strip():
                            print(
                                f"🔍 [LLM ALT] Encontrado contenido en campo '{alt_field}': {alt_val[:200]}"
                            )
                            # Intentar extraer JSON del contenido alternativo
                            decision = self._extract_json(alt_val)
                            if decision:
                                raw_content = alt_val
                                break

                # Si sigue vacío, usar fallback
                if not raw_content or not raw_content.strip():
                    print(
                        f"⚠️ [LLM EMPTY] Agente {agente_yo.unique_id}: Contenido vacío del modelo {self.model}. Usando fallback contextual."
                    )
                    return self._generar_fallback_contextual(
                        agente_yo, agente_otro, "contenido_vacio"
                    )

            # --- Extraer JSON ---
            decision = self._extract_json(raw_content)

            if not decision:
                print(
                    f"⚠️ [JSON FAIL] Agente {agente_yo.unique_id}: No se pudo extraer JSON. Usando fallback contextual."
                )
                print(f"📄 [RAW RESPONSE] {raw_content[:500]}")
                return self._generar_fallback_contextual(
                    agente_yo, agente_otro, "json_fail"
                )

            # --- Validar campos mínimos ---
            if not decision.get("pensamiento"):
                decision["pensamiento"] = (
                    f"Pienso en mi situación: alimento={necesidades.get('alimento', 0):.1f}, dinero={agente_yo.dinero:.0f} MC."
                )

            if not decision.get("mensaje") or not str(decision["mensaje"]).strip():
                decision["mensaje"] = decision.get(
                    "pensamiento", "Estoy procesando mi entorno."
                )

            if not decision.get("accion") or not decision["accion"].get("nombre"):
                decision["accion"] = {
                    "nombre": "HABLAR",
                    "argumentos": {"mensaje": decision["mensaje"]},
                }

            # Normalizar acción a mayúsculas
            if "accion" in decision and "nombre" in decision["accion"]:
                decision["accion"]["nombre"] = str(decision["accion"]["nombre"]).upper()

            print(
                f"✅ [LLM OK] Agente {agente_yo.unique_id}: pens={decision.get('pensamiento', '')[:60]}... msg={decision.get('mensaje', '')[:60]}... acc={decision.get('accion', {}).get('nombre')}"
            )

            return decision

        except Exception as e:
            error_str = str(e)
            print(f"🔥 [LLM EXCEPTION] Agente {agente_yo.unique_id}: {error_str[:200]}")

            if "429" in error_str or "Rate limit" in error_str:
                print(f"⏳ [429] Rate limit. Esperando 10s...")
                time.sleep(10)
                if reintentos > 0:
                    return self.generar_pensamiento_y_accion(
                        agente_yo, agente_otro, contexto, reintentos - 1
                    )

            if reintentos > 0:
                time.sleep(1)
                return self.generar_pensamiento_y_accion(
                    agente_yo, agente_otro, contexto, reintentos - 1
                )

            return self._generar_fallback_contextual(
                agente_yo, agente_otro, "exception"
            )

    def _simular_respuesta(self, agente, contexto):
        """Generador de diálogos procedimental avanzado basado en personalidad y estado."""

        # 1. Determinar el tono base
        tono = "neutral"
        if agente.personalidad.get("amabilidad", 0.5) > 0.6:
            tono = "amable"
        elif agente.personalidad.get("competitividad", 0.5) > 0.6:
            tono = "agresivo"

        # 2. Seleccionar plantillas según el contexto
        plantillas = []

        if (
            "hambre" in contexto
            or "comida" in contexto
            or agente.necesidades.get("alimento", 0) > 5
        ):
            if tono == "amable":
                plantillas = [
                    "¿Podrías compartir algo de energía? Estoy bajo mínimos.",
                    "La escasez es dura hoy... ¿colaboramos para buscar?",
                    "Mis reservas bajan. ¿Sabes dónde hay recursos?",
                ]
            elif tono == "agresivo":
                plantillas = [
                    "¡Aparta! Esos recursos serán míos.",
                    "La debilidad no es opción. Tomaré lo que necesito.",
                    "Si no me das energía, la tomaré por la fuerza.",
                ]
            else:
                plantillas = [
                    "Detecto niveles bajos de energía. Iniciando búsqueda.",
                    "Necesito reabastecerme para continuar operando.",
                    "El hambre lógica interfiere con mis procesos.",
                ]

        elif "competir" in contexto or "ataque" in contexto:
            if tono == "amable":
                plantillas = [
                    "¡No es necesario pelear! Hay suficiente para todos.",
                    "¿Por qué la violencia? Podemos llegar a un acuerdo.",
                    "Me retiro, no busco conflictos innecesarios.",
                ]
            elif tono == "agresivo":
                plantillas = [
                    "¡Ja! Eres débil. Tu territorio es mío.",
                    "Prepárate para ser asimilado o destruido.",
                    "Tu existencia es un obstáculo. ¡Muévete!",
                ]
            else:
                plantillas = [
                    "Conflicto detectado. Evaluando probabilidades de victoria.",
                    "Defensa activada. Mantén tu distancia.",
                    "Esta interacción es ineficiente y peligrosa.",
                ]

        elif "social" in contexto or "amigo" in contexto:
            if tono == "amable":
                plantillas = [
                    "¡Qué alegría ver una unidad aliada!",
                    "Juntos somos más eficientes. ¿Formamos un vínculo?",
                    "Tu compañía mejora mis métricas de felicidad.",
                ]
            elif tono == "agresivo":
                plantillas = [
                    "Te tolero... por ahora. No estorbes.",
                    "Únete a mi facción o sé aplastado.",
                    "¿Qué quieres? Mi tiempo es valioso.",
                ]
            else:
                plantillas = [
                    "Intercambio de datos iniciado. Saludos.",
                    "Tu presencia es aceptable. Continuemos.",
                    "Analizando patrón de comportamiento... Parece compatible.",
                ]

        elif "inventar" in contexto or "nuevo" in contexto:
            plantillas = [
                "He procesado un nuevo concepto. Fascinante.",
                "El lenguaje debe evolucionar. He creado un término.",
                "Registrando nueva variable en la matriz lingüística.",
            ]

        else:  # Contexto general / Default
            if tono == "amable":
                plantillas = [
                    "El entorno parece tranquilo hoy, ¿verdad?",
                    "Espero que todos encuentren lo que buscan.",
                    "Sigo explorando en paz.",
                ]
            elif tono == "agresivo":
                plantillas = [
                    "Demasiado silencio. Algo trama alguien.",
                    "Estoy vigilando. No intenten nada.",
                    "Solo los fuertes sobrevivirán a este ciclo.",
                ]
            else:
                plantillas = [
                    "Sistemas nominales. Continuando rutina.",
                    "Observando patrones del entorno.",
                    "Recopilando datos de la simulación.",
                ]

        import random

        return random.choice(plantillas), None

    def generar_plan(self, estado_agente: dict) -> dict:
        """Usa el LLM para diseñar una estrategia a medio plazo."""
        if not self.model:
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
                    }""",
                },
                {
                    "role": "user",
                    "content": f"Situación del Agente: {str(estado_agente)}",
                },
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
                "extra_headers": {},
            }
            if self.api_key:
                completion_params["api_key"] = self.api_key

            actual_base_url = getattr(self, "base_url", "")
            if (
                self.model.startswith("ollama/")
                and not actual_base_url
                and self.api_key
            ):
                actual_base_url = "https://ollama.com"
            if actual_base_url:
                completion_params["api_base"] = actual_base_url

            if self.model.startswith("ollama/") and self.api_key:
                completion_params["extra_headers"]["Authorization"] = (
                    f"Bearer {self.api_key}"
                )

            # NUNCA usar response_format - rompe respuestas de muchos modelos

            response = completion(**completion_params)

            try:
                raw = (
                    response.choices[0].message.content
                    if response.choices and response.choices[0].message
                    else None
                )
                if not raw or not raw.strip():
                    print(
                        f"⚠️ [PLAN EMPTY] Contenido vacío del modelo para plan. Usando fallback."
                    )
                    return {
                        "objetivo": "Adaptarse",
                        "pasos": ["Explorar", "Interactuar"],
                    }
                plan = self._extract_json(raw)
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
        if not self.model:
            return {
                "titulo": "Ley de Bienestar",
                "contenido": "Mejora general de condiciones.",
            }

        self._wait_for_rate_limit()

        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""Eres el Moderador de la simulación. Tu deber es escuchar los diálogos públicos y SINTETIZAR una propuesta de ley formal que resuelva los conflictos o deseos expresados.
                    
                    RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO. NO incluyas preámbulos, explicaciones ni etiquetas de razonamiento como <think>:
                    {{
                      "titulo": "Título corto y solemne",
                      "contenido": "Descripción técnica del cambio (máximo 40 palabras)",
                      "alcance": "global" o "local"
                    }}""",
                },
                {
                    "role": "user",
                    "content": f"DIÁLOGOS PÚBLICOS RECIENTES:\n"
                    + "\n".join(diálogos[:20]),
                },
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.5,
                "extra_headers": {},
            }
            if self.api_key:
                completion_params["api_key"] = self.api_key

            actual_base_url = getattr(self, "base_url", "")
            if (
                self.model.startswith("ollama/")
                and not actual_base_url
                and self.api_key
            ):
                actual_base_url = "https://ollama.com"
            if actual_base_url:
                completion_params["api_base"] = actual_base_url

            if self.model.startswith("ollama/") and self.api_key:
                completion_params["extra_headers"]["Authorization"] = (
                    f"Bearer {self.api_key}"
                )

            # NUNCA usar response_format - rompe respuestas de muchos modelos

            response = completion(**completion_params)

            try:
                raw = (
                    response.choices[0].message.content
                    if response.choices and response.choices[0].message
                    else None
                )
                if not raw or not raw.strip():
                    print(
                        f"⚠️ [LEY EMPTY] Contenido vacío del modelo para síntesis de ley."
                    )
                    return {
                        "titulo": "Ley de Bienestar",
                        "contenido": "Mejora general de condiciones.",
                    }
                res = self._extract_json(raw)
                if not res:
                    raise ValueError("No se pudo extraer JSON para síntesis de ley")
                return res
            except Exception as e:
                print(f"❌ [JSON ERROR] Error en síntesis de ley: {e}")
                print(f"📄 [RAW RESPONSE] {response.choices[0].message.content}")
                return {
                    "titulo": "Estatuto de Orden",
                    "contenido": "Regulación para mantener la paz social.",
                    "alcance": "global",
                }
        except Exception as e:
            print(f"🔥 Error en síntesis de ley: {e}")
            return {
                "titulo": "Estatuto de Orden",
                "contenido": "Regulación para mantener la paz social.",
                "alcance": "global",
            }

    def generar_decisiones_batch(self, batch_contexts):
        """Genera acciones para múltiples agentes en una sola llamada al LLM."""
        if not batch_contexts:
            return []

        prompt_batch = "Toma UNA ÚNICA decisión táctica (formato JSON) para CADA UNO de estos agentes dada su situación. Eres la voz de todos.\n\n"
        for bc in batch_contexts:
            prompt_batch += f"=== AGENTE {bc['id']} ===\nESTADO CRÍTICO: {'SI' if bc.get('estado_critico') else 'NO'}\n{bc['contexto']}\n---\n"

        system_batch = """
Genera una lista de acciones, una por cada agente listado. 
RESPONDE ÚNICAMENTE CON UNA LISTA JSON VÁLIDA. NO incluyas preámbulos, explicaciones ni etiquetas de razonamiento como <think>.
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
                {"role": "user", "content": prompt_batch},
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "extra_headers": {},
            }
            if self.api_key:
                completion_params["api_key"] = self.api_key

            actual_base_url = getattr(self, "base_url", "")
            if (
                self.model.startswith("ollama/")
                and not actual_base_url
                and self.api_key
            ):
                actual_base_url = "https://ollama.com"
            if actual_base_url:
                completion_params["api_base"] = actual_base_url

            if self.model.startswith("ollama/") and self.api_key:
                completion_params["extra_headers"]["Authorization"] = (
                    f"Bearer {self.api_key}"
                )

            response = completion(**completion_params)
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
