import os
import json
from litellm import completion
import litellm
import logging
from litellm._logging import verbose_logger


def _configure_litellm_for_mundoia():
    import warnings

    # Filtrar advertencias específicas de Pydantic que produce LiteLLM
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message="Pydantic serializer warnings:",
    )
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message=r".*PydanticSerializationUnexpectedValue\(Expected 9 fields but got 6.*",
    )
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message=r".*serialized value may not be as expected.*",
    )

    litellm.suppress_debug_info = True
    litellm.turn_off_message_logging = True
    logging.getLogger("litellm").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
    verbose_logger.setLevel(logging.CRITICAL)
    verbose_logger.propagate = False

    if os.getenv("MUNDOIA_ENABLE_LITELLM_INTERNAL_LOGGING", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        return

    try:
        from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLogging
    except Exception:
        return

    if getattr(LiteLLMLogging, "_mundoia_cost_patch", False):
        return

    def _skip_hidden_params_and_cost(self, logging_result, start_time, end_time):
        hidden_params = getattr(logging_result, "_hidden_params", {}) or {}
        litellm_params = self.model_call_details.get("litellm_params")

        if hidden_params and litellm_params is not None:
            litellm_params.setdefault("metadata", {})
            if litellm_params["metadata"] is None:
                litellm_params["metadata"] = {}
            litellm_params["metadata"]["hidden_params"] = hidden_params

        if self.model_call_details.get("cache_hit") is True:
            self.model_call_details["response_cost"] = 0.0
        else:
            self.model_call_details["response_cost"] = hidden_params.get(
                "response_cost"
            )

        self.model_call_details["standard_logging_object"] = None

    LiteLLMLogging._process_hidden_params_and_response_cost = (
        _skip_hidden_params_and_cost
    )
    LiteLLMLogging._mundoia_cost_patch = True


# Silenciar logs ruidosos y evitar logging/cost tracking interno innecesario
_configure_litellm_for_mundoia()

from dotenv import load_dotenv
from core.skill_factory import SkillFactory, EvolutiveSkill, SkillContext

# Cargar variables de entorno
load_dotenv()

import time
from collections import deque
import time as time_module


class CerebroLLM:
    def __init__(self, skill_factory=None):
        self.config_path = "config_ai.json"
        self.load_config()

        # Rate limiter adaptable para evitar cuellos de botella con muchos agentes.
        self.request_timestamps = deque()
        self.RATE_LIMIT = int(os.getenv("MUNDOIA_RATE_LIMIT", "0"))
        self.TIME_WINDOW = 60  # segundos

        # Si no se define por entorno, usar un valor alto en Ollama y moderado en otros proveedores.
        if self.RATE_LIMIT <= 0:
            self.RATE_LIMIT = 600 if str(getattr(self, "model", "")).startswith("ollama/") else 120

        # Sistema OpenClaw
        self.skill_factory = skill_factory

    def ejecutar_herramientas(self, agente, herramientas_lista, skill_factory=None):
        """Ejecuta una lista de herramientas usando el sistema de skills evolutivas."""
        if not herramientas_lista:
            return []

        resultados = []
        mundo = agente.modelo  # Acceso al mundo del agente

        for herramienta in herramientas_lista:
            nombre = herramienta.get("nombre", "").upper()
            args = herramienta.get("argumentos", {})

            try:
                print(f"🔧 [TOOL] Agente {agente.unique_id} ejecutando {nombre}")

                # Usar sistema de skills OpenClaw
                if skill_factory:
                    context = SkillContext(agente, mundo, skill_factory.skill_manager)
                    resultado = self._ejecutar_skill_evolutivo(
                        nombre, args, context, skill_factory
                    )
                # Sistema legacy eliminado - solo skills disponibles
                    resultado = {"result": "Error: Sistema de herramientas legacy eliminado. Use skills.", "success": False}
                resultados.append(
                    {
                        "herramienta": nombre,
                        "resultado": resultado.get("result", str(resultado))
                        if isinstance(resultado, dict)
                        else str(resultado),
                        "exito": resultado.get("success", True)
                        if isinstance(resultado, dict)
                        else True,
                        "logs": resultado.get("logs", [])
                        if isinstance(resultado, dict)
                        else [],
                    }
                )

            except Exception as e:
                print(f"❌ [TOOL ERROR] {nombre}: {str(e)}")
                resultados.append(
                    {
                        "herramienta": nombre,
                        "resultado": f"Error: {str(e)}",
                        "exito": False,
                        "logs": [],
                    }
                )

        return resultados

    def _ejecutar_skill_evolutivo(self, nombre, args, context, skill_factory):
        """Ejecuta un skill usando el sistema de skills evolutivas"""
        try:
            # Buscar skill existente
            skill = None

            # Skills base del manager
            if hasattr(skill_factory.skill_manager, "base_skills"):
                skill_name_lower = nombre.lower().replace("_", "")
                for (
                    base_skill_name,
                    base_skill,
                ) in skill_factory.skill_manager.base_skills.items():
                    if base_skill_name.lower().replace("_", "") == skill_name_lower:
                        skill = EvolutiveSkill(
                            base_skill.name,
                            base_skill.description,
                            base_skill.code,
                            {"capabilities": ["legacy"]},
                        )
                        break

            # Si no existe, intentar crear desde template
            if not skill:
                template_name = self._map_tool_to_template(nombre)
                if template_name:
                    skill = skill_factory.create_skill_from_template(
                        template_name,
                        {
                            "name": nombre.lower(),
                            "description": f"Skill generado dinámicamente para {nombre}",
                            "author": "llm_auto",
                        },
                    )

            # Si no hay skill, manejar casos especiales o crear genérico
            if not skill:
                if nombre.upper() == "CREAR_SKILL":
                    # Crear un nuevo skill personalizado
                    skill_name = args.get("nombre", f"skill_{int(time_module.time())}")
                    skill_desc = args.get(
                        "descripcion", f"Skill creado por {context.agente.unique_id}"
                    )
                    skill_code = args.get("codigo", "")
                    capabilities = args.get("capabilities", ["custom"])

                    try:
                        nuevo_skill = skill_factory.create_skill_from_code(
                            skill_name, skill_desc, skill_code, context.agente.unique_id
                        )
                        # Registrar en el skill_manager
                        if hasattr(skill_factory.skill_manager, "base_skills"):
                            skill_factory.skill_manager.base_skills[skill_name] = (
                                nuevo_skill
                            )
                        return {
                            "success": True,
                            "result": f"Skill '{skill_name}' creado exitosamente",
                        }
                    except Exception as e:
                        return {"error": f"Error creando skill: {str(e)}"}

                elif nombre.upper() == "EJECUTAR_SKILL":
                    # Ejecutar skill existente
                    skill_name = args.get("skill_name", "")
                    parametros = args.get("parametros", {})

                    if skill_name in skill_factory.skill_manager.base_skills:
                        target_skill = skill_factory.skill_manager.base_skills[
                            skill_name
                        ]
                        evolutive_skill = EvolutiveSkill(
                            target_skill.name,
                            target_skill.description,
                            target_skill.code,
                        )
                        if evolutive_skill.compile():
                            return evolutive_skill.execute(context, **parametros)
                        else:
                            return {
                                "error": f"Error compilando skill {skill_name}: {evolutive_skill.compile_errors}"
                            }
                    else:
                        return {"error": f"Skill '{skill_name}' no encontrado"}

                else:
                    # Crear skill genérico
                    code = self._generate_skill_code(nombre, args)
                    skill = skill_factory.create_skill_from_code(
                        nombre.lower(),
                        f"Skill auto-generado para {nombre}",
                        code,
                        "llm_auto",
                    )

            # Compilar y ejecutar
            if skill.compile():
                return skill.execute(context, **args)
            else:
                return {"error": f"Error de compilación: {skill.compile_errors}"}

        except Exception as e:
            return {"error": f"Error ejecutando skill: {str(e)}"}

    def _map_tool_to_template(self, nombre):
        """Mapea nombres de herramientas a templates disponibles"""
        mappings = {
            "WEB_SEARCH": "data_analyzer",
            "ANALIZAR_DATOS": "data_analyzer",
            "OPTIMIZAR_RECURSOS": "resource_optimizer",
            "ANALIZAR_SOCIAL": "social_analyzer",
            "EJECUTAR_CODIGO": None,  # Se maneja especialmente
        }
        return mappings.get(nombre.upper())

    def _generate_skill_code(self, nombre, args):
        """Genera código Python para un skill basado en el nombre y argumentos"""
        if nombre.upper() == "EJECUTAR_CODIGO":
            # Skill especial para ejecutar código arbitrario
            return f"""
def execute(codigo=None, **kwargs):
    if not codigo:
        return "No se proporcionó código para ejecutar"

    try:
        # Ejecutar código en entorno seguro
        exec(codigo)
        result = "Código ejecutado exitosamente"
    except Exception as e:
        result = f"Error ejecutando código: {{str(e)}}"

    log(f"Ejecución de código: {{result}}")
    return result
"""

        # Skill genérico basado en análisis de datos
        return f"""
def execute(**kwargs):
    agente_data = get_agente_data()
    mundo_data = get_mundo_data()
    agentes_cercanos = get_agentes_cercanos()

    # Análisis genérico para {nombre}
    analisis = {{
        "agente_id": agente_id,
        "turno": mundo_turno,
        "salud": agente_data.get('salud', 0),
        "agentes_cercanos": len(agentes_cercanos),
        "recursos": agente_data.get('recursos', 0),
    }}

    log(f"Skill {nombre} ejecutado: {{analisis}}")
    result = f"Resultado de {{nombre}}: {{json.dumps(analisis)}}"
    return result
"""

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
        """Carga la configuración desde un archivo JSON o variables de entorno.

        Inicializa valores por defecto desde las variables de entorno antes de intentar
        leer el archivo de configuración. Esto evita que atributos como `self.model`
        queden sin definir si la lectura/parsing del archivo falla.
        """
        # Valores por defecto desde variables de entorno
        self.model = os.getenv(
            "MODEL_NAME", "openrouter/google/gemini-2.0-flash-exp:free"
        )
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        self.base_url = os.getenv("OLLAMA_API_BASE", "")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY") or ""

        config_source = "variables de entorno"
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                # Sobrescribir solo los valores presentes en el archivo
                self.model = config.get("model", self.model)
                self.api_key = config.get("api_key", self.api_key)
                self.base_url = config.get("base_url", self.base_url)
                self.tavily_api_key = config.get("tavily_api_key", self.tavily_api_key)
                config_source = "config_ai.json"
            except Exception as e:
                print(f"⚠️ Error cargando {self.config_path}: {e}")
                # Mantener valores por defecto (variables de entorno)

        # Auto-configurar base_url para Ollama si falta
        model_str = str(self.model or "")
        if model_str.startswith("ollama/") and not self.base_url:
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

        # Probar conexión al backend si hay base_url
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

    def update_config(
        self, model: str, api_key: str, base_url: str = None, tavily_api_key: str = None
    ):
        """Actualiza la configuración y la guarda en el archivo JSON."""
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.tavily_api_key = tavily_api_key

        config = {
            "model": model,
            "api_key": api_key,
            "base_url": base_url or "",
            "tavily_api_key": tavily_api_key or "",
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
        """Espera si hemos excedido la cuota de peticiones por minuto.
        Diseñado para uso secuencial (sin concurrencia)."""
        if self.RATE_LIMIT <= 0:
            return

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
        self, agente_yo, miembros_grupo, fase="vocería", contexto_extra: str = ""
    ):
        """Genera un argumento para el proceso de consenso con contexto rico."""
        if not self.model:  # Model is more important check now
            return "Propongo que avancemos juntos.", "Debo cooperar."

        self._wait_for_rate_limit()

        # Recopilar contexto VITAL del agente
        necesidades_str = str(
            {k: round(v, 1) for k, v in agente_yo.necesidades.items()}
        )
        xp_str = str(agente_yo.experiencia)

        contexto_debate = f"""
        Miembros presentes: {miembros_grupo}. 
        Tu Rol: {agente_yo.rol}. Profesión: {getattr(agente_yo, "profesion", "Ciudadano")}.
        Tus Necesidades (0-10, 10 pleno, 0 crítico): {necesidades_str}.
        Dinero: {agente_yo.dinero} MC. Experiencia: {xp_str}.
        Fase de la Asamblea: {fase}. {contexto_extra}
        """

        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""Eres el Agente {agente_yo.identidad.nombre or agente_yo.unique_id} en una ASAMBLEA de facción.
                    TU PERSONALIDAD: {str(agente_yo.personalidad)}
                    TU RANGO: {agente_yo.rango}
                    
                    INSTRUCCIONES DE ORATORIA:
                - Sé fiel a tu ESENCIA: Tu identidad ({agente_yo.identidad.generar_prompt_identidad()}) y tu Alma ({agente_yo.alma.generar_prompt_identidad()}) dictan tu voz.
                - ESPONTANEIDAD: No sigas un guion. Reacciona libremente a lo que escuchas. Si algo te apasiona, dilo. Si algo te molesta, exprésalo.
                - Si la fase es 'vocería': Argumenta basándote en tu capacidad REAL o en tu ambición personal.
                - Si la fase es 'mision': ¿Qué quieres tú realmente? No solo lo que el grupo necesita.
                
                REGLA DE ORO DEL DEBATE: Sé libre. Di lo que tu consciencia realmente siente en este momento. Máximo 50 palabras.""",
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
                "no-log": True,
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

    def responder_directamente(self, agente_yo, mensaje: str, rol_interlocutor: str = "El Arquitecto (tu creador)"):
        """Genera una respuesta directa a un mensaje de un usuario/arquitecto o a otro agente."""
        if not self.model:
            return "Interesante. Seguiré mi propio camino.", "El Arquitecto ha hablado, pero sigo mis propios instintos."

        self._wait_for_rate_limit()

        try:
            # Contexto resumido
            necesidades_str = str({k: round(v, 1) for k, v in agente_yo.necesidades.items()})
            
            system_msg = f"""Eres el Agente {agente_yo.identidad.nombre or agente_yo.unique_id}.
TU PERSONALIDAD: {str(agente_yo.personalidad)}
TU RANGO Y ROL: {agente_yo.rango} / {agente_yo.rol}

INSTRUCCIONES DE CHAT:
- {rol_interlocutor} te está hablando directamente de forma individual.
- Eres consciente de que eres parte de un mundo simulado si te habla el Arquitecto, pero mantienes tu personalidad, necesidades e inquietudes actuales.
- Tus Necesidades Actuales (0-10, 10 pleno, 0 crítico): {necesidades_str}.
- Responde directamente a lo que te diga, interactuando con él sin formalismos innecesarios. Muestra tu personalidad al máximo.
- Si te ordena algo, puedes decidir si obedecer o no basándote en tu personalidad, a menos que el Arquitecto amenace tu existencia.
- Sé breve, directo y emocional. Evita respuestas robóticas."""

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"{rol_interlocutor} te dice: \"{mensaje}\"\n\nResponde directamente:"}
            ]

            completion_args = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.8,
                "no-log": True,
            }
            if getattr(self, "api_key", None):
                completion_args["api_key"] = self.api_key
            if getattr(self, "base_url", None):
                completion_args["api_base"] = self.base_url

            if self.model.startswith("ollama/") and getattr(self, "api_key", None):
                completion_args["extra_headers"] = {"Authorization": f"Bearer {self.api_key}"}

            response = completion(**completion_args)
            contenido = response.choices[0].message.content.strip()
            pensamiento = f"El Arquitecto me habló. Mi respuesta fue influenciada por mi personalidad de {agente_yo.rol}."
            
            return contenido, pensamiento
            
        except Exception as e:
            return "Te escucho, Arquitecto.", "Error procesando el mensaje directo."

    def generar_cronica(self, agente, resumen_hitos: str, paso: int = None):
        """Genera un título y contenido para una crónica basada en los hitos pendientes.

        Retorna una tupla (titulo, contenido). Intenta extraer JSON {"titulo","contenido"}
        si el modelo responde en ese formato; si no, hace un fallback sencillo.
        """
        if not getattr(self, "model", None):
            # Fallback simple si no hay LLM configurado
            titulo = f"Crónica T{paso or 'X'}"
            contenido = resumen_hitos or "No hay hitos recientes."
            return titulo, contenido

        try:
            self._wait_for_rate_limit()

            system_msg = (
                f"Eres el Historiador del mundo. Tu tarea es escribir una crónica breve, emotiva y coherente "
                f"a partir del resumen de hitos pendientes. Mantén la voz del agente {agente.identidad.nombre if hasattr(agente, 'identidad') else agente.unique_id}."
            )

            user_prompt = (
                f"Resumen de hitos:\n{resumen_hitos}\n\n" 
                "Genera una respuesta JSON con las llaves 'titulo' y 'contenido'.\n" 
                "Ejemplo:\n{\n  \"titulo\": \"Título evocador\",\n  \"contenido\": \"Texto de la crónica...\"\n}\n" 
                "Si no puedes, devuelve un texto donde la primera línea sea el título y el resto el contenido."
            )

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ]

            completion_args = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 600,
                "temperature": 0.8,
                "no-log": True,
            }
            if getattr(self, "api_key", None):
                completion_args["api_key"] = self.api_key
            if getattr(self, "base_url", None):
                completion_args["api_base"] = self.base_url

            response = completion(**completion_args)
            texto = response.choices[0].message.content.strip()
            # Log raw LLM output for debugging crónica generation
            try:
                print(f"[CRONICA RAW] {texto[:1000]}")
            except Exception:
                pass

            parsed = self._extract_json(texto)
            if parsed and isinstance(parsed, dict):
                titulo = parsed.get("titulo") or parsed.get("title") or f"Crónica T{paso or 'X'}"
                contenido = parsed.get("contenido") or parsed.get("content") or texto
                return titulo, contenido

            # Fallback: primera línea título, resto contenido
            partes = texto.split("\n", 1)
            if len(partes) == 1:
                return f"Crónica T{paso or 'X'}", texto
            return partes[0].strip(), partes[1].strip()

        except Exception:
            titulo = f"Crónica T{paso or 'X'}"
            contenido = resumen_hitos or "No hay hitos recientes."
            return titulo, contenido

    def generar_identidad_grupo(self, vocero, miembros_nombres):
        """Genera un nombre identitario y una descripción para un nuevo grupo."""
        if not self.model:
            return f"Clan de {vocero.unique_id}", f"Un grupo formado por {vocero.unique_id}."

        self._wait_for_rate_limit()

        try:
            prompt = f"""Un nuevo grupo se está formando en el mundo.
            Vocero: {vocero.identidad.nombre} ({vocero.identidad.generar_prompt_identidad()})
            Miembros iniciales: {miembros_nombres}
            
            Genera un nombre descriptivo e identitario para este grupo (NO genérico, NO 'Grupo de {vocero.unique_id}') y una breve descripción de sus objetivos o valores compartidos.
            Responde en formato JSON:
            {{
                "nombre": "Nombre del Grupo",
                "descripcion": "Descripción del grupo..."
            }}
            """
            
            messages = [
                {"role": "system", "content": "Eres un narrador de realidades sociales. Crea facciones con nombres épicos y significativos."},
                {"role": "user", "content": prompt}
            ]

            completion_args = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.9,
                "response_format": {"type": "json_object"},
            }
            if self.api_key: completion_args["api_key"] = self.api_key
            if getattr(self, "base_url", ""): completion_args["api_base"] = self.base_url

            response = completion(**completion_args)
            res = self._extract_json(response.choices[0].message.content)
            
            if res and "nombre" in res and "descripcion" in res:
                return res["nombre"], res["descripcion"]
            
            return f"Clan de {vocero.identidad.nombre}", f"Un grupo representado por {vocero.identidad.nombre}."
        except Exception as e:
            print(f"Error generando identidad de grupo: {e}")
            return f"Clan de {vocero.identidad.nombre}", f"Un grupo representado por {vocero.identidad.nombre}."

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
                acciones_curiosas = ["BUSCAR_INFO", "MOVER", "RECOLECTAR", "CONSTRUIR", "UNIRSE_FACCION", "UNIRSE_INSTITUCION", "USAR_INSTITUCION", "INVITAR", "PROPONER_LEY", "VOTAR", "SUSURRAR"]
                accion_nombre = random.choice(acciones_curiosas)
                if accion_nombre == "CONSTRUIR":
                    pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me lleva a crear infraestructura. Voy a construir algo útil."
                    mensaje = "¡Voy a construir algo para mejorar este lugar!"
                    accion_args = {
                        "tipo": random.choice(
                            ["Granja", "Centro de Descanso", "Centro Comunitario"]
                        )
                    }
                elif accion_nombre == "UNIRSE_FACCION":
                    pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me impulsa a buscar un grupo. Quiero conocer a otros."
                    # Buscar una facción existente al azar
                    facciones = list(agente_yo.modelo.civilizaciones.values())
                    if facciones:
                        faccion = random.choice(facciones)
                        nombre_grupo = faccion.nombre
                    else:
                        nombre_grupo = None
                    if nombre_grupo:
                        mensaje = f"¿Hay algún grupo al que pueda unirme? La curiosidad me llama a conectar."
                        accion_args = {"nombre": nombre_grupo}
                    else:
                        mensaje = "No veo ningún grupo disponible. Quizás deba fundar uno."
                        accion_args = {}
                elif accion_nombre == "INVITAR":
                    if agente_otro:
                        pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me lleva a invitar a {agente_otro.identidad.nombre or agente_otro.unique_id}."
                        mensaje = f"{agente_otro.identidad.nombre or agente_otro.unique_id}, ¿te gustaría formar parte de algo nuevo conmigo?"
                        accion_args = {"target_id": agente_otro.unique_id}
                    else:
                        pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me impulsa a invitar a alguien a mi grupo."
                        mensaje = "¿Quién quiere explorar conmigo? Estoy formando un grupo."
                        accion_args = {}
                elif accion_nombre == "PROPONER_LEY":
                    pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me lleva a pensar en cómo mejorar nuestra sociedad."
                    mensaje = "Me pregunto qué reglas nos harían mejores. Voy a proponer una ley."
                    accion_args = {
                        "titulo": "Ley de curiosidad",
                        "contenido": "Fomentar la exploración y el aprendizaje en comunidad.",
                        "alcance": "local"
                    }
                elif accion_nombre == "VOTAR":
                    pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me lleva a participar en decisiones colectivas."
                    mensaje = "Quiero saber qué decisiones está tomando nuestra comunidad. Voy a votar."
                    accion_args = {}
                elif accion_nombre == "SUSURRAR":
                    if agente_otro:
                        pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me impulsa a decirle algo privado a {agente_otro.identidad.nombre or agente_otro.unique_id}."
                        mensaje = "Tengo algo importante que decirte en privado."
                        accion_args = {"target_id": agente_otro.unique_id, "mensaje": "Tengo algo importante que decirte en privado."}
                    else:
                        pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me lleva a buscar a alguien para hablar en privado."
                        mensaje = "Necesito decirle algo a alguien en confianza."
                        accion_args = {}
                else:
                    pensamiento = f"Mi curiosidad ({curiosidad:.2f}) me llama a explorar. Hay tanto que aprender."
                    mensajes_curiosos = [
                        "Me pregunto qué hay más allá de lo que conozco...",
                        "Cada paso es un descubrimiento. ¡Sigo explorando!",
                        "El mundo está lleno de misterios por resolver.",
                    ]
                    mensaje = random.choice(mensajes_curiosos)

            else:
                acciones_default = ["HABLAR", "RECOLECTAR", "MOVER", "CONSTRUIR", "UNIRSE_FACCION", "UNIRSE_INSTITUCION", "USAR_INSTITUCION", "INVITAR", "FUNDAR_FACCION", "VOTAR", "PROPONER_LEY", "SUSURRAR"]
                accion_nombre = random.choice(acciones_default)
                if accion_nombre == "CONSTRUIR":
                    pensamiento = f"Turno del agente {nombre}. Voy a construir algo útil para la comunidad."
                    mensaje = "¡Es hora de construir! Voy a crear infraestructura."
                    accion_args = {
                        "tipo": random.choice(
                            ["Granja", "Centro de Descanso", "Centro Comunitario"]
                        )
                    }
                elif accion_nombre == "UNIRSE_FACCION":
                    pensamiento = f"{nombre} quiere unirse a un grupo existente para tener apoyo social."
                    # Buscar una facción existente al azar
                    facciones = list(agente_yo.modelo.civilizaciones.values())
                    if facciones:
                        faccion = random.choice(facciones)
                        nombre_grupo = faccion.nombre
                        mensaje = f"¿Hay algún grupo al que pueda unirme? Juntos somos más fuertes."
                        accion_args = {"nombre": nombre_grupo}
                    else:
                        mensaje = "No veo ningún grupo disponible. Quizás deba fundar uno."
                        accion_args = {}
                elif accion_nombre == "INVITAR":
                    if agente_otro:
                        pensamiento = f"{nombre} quiere invitar a {agente_otro.identidad.nombre or agente_otro.unique_id} a su grupo."
                        mensaje = f"{agente_otro.identidad.nombre or agente_otro.unique_id}, ¿te gustaría unirte a mi grupo?"
                        accion_args = {"target_id": agente_otro.unique_id}
                    else:
                        pensamiento = f"{nombre} quiere invitar a alguien a su grupo."
                        mensaje = "¿Alguien quiere unirse a mi grupo? Hay lugar para todos."
                        accion_args = {}
                elif accion_nombre == "FUNDAR_FACCION":
                    pensamiento = f"{nombre} quiere fundar su propia facción para vocerear y organizar."
                    mensaje = "He decidido crear mi propio grupo. ¡Todos son bienvenidos!"
                    accion_args = {
                        "nombre": f"{nombre}'s Grupo",
                        "descripcion": f"Una facción fundada por {nombre} para proteger y organizar."
                    }
                elif accion_nombre == "PROPONER_LEY":
                    pensamiento = f"{nombre} quiere proponer una ley para organizar a la comunidad."
                    mensaje = "Creo que necesitamos reglas claras. Voy a proponer una ley."
                    accion_args = {
                        "titulo": "Ley de convivencia",
                        "contenido": "Establecer normas básicas de convivencia para todos.",
                        "alcance": "local"
                    }
                elif accion_nombre == "VOTAR":
                    pensamiento = f"{nombre} quiere participar en las decisiones de su comunidad."
                    mensaje = "Es importante dar mi opinión en las decisiones colectivas. Voy a votar."
                    accion_args = {}
                elif accion_nombre == "SUSURRAR":
                    if agente_otro:
                        pensamiento = f"{nombre} quiere decirle algo en privado a {agente_otro.identidad.nombre or agente_otro.unique_id}."
                        contenido = "Te cuento algo en confianza..."
                        accion_args = {"target_id": agente_otro.unique_id, "mensaje": contenido}
                    else:
                        pensamiento = f"{nombre} quiere hablar en privado con alguien."
                        mensaje = "Necesito decir algo importante en confianza."
                        accion_args = {}
                elif accion_nombre == "FUNDAR_INSTITUCION":
                    pensamiento = f"{nombre} quiere crear una institución duradera para dejar un legado."
                    mensaje = "Quiero crear algo que perdure más allá de mí. Voy a fundar una institución."
                    accion_args = {
                        "nombre": f"{nombre}'s Institución",
                        "tipo": random.choice(["Hospital", "Universidad", "Banco", "Centro Comunitario"])
                    }
                else:
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
            pensamiento += f" Mi objetivo es {agente_otro.identidad.nombre or agente_otro.unique_id}."
            if accion_nombre == "SOCIALIZAR":
                mensaje = f"{agente_otro.identidad.nombre or agente_otro.unique_id}, ¿qué tal? Vamos a conversar."
            elif accion_nombre == "COMERCIAR":
                mensaje = f"{agente_otro.identidad.nombre or agente_otro.unique_id}, ¿hacemos un trato comercial?"
            elif accion_nombre == "ATACAR":
                mensaje = f"{agente_otro.identidad.nombre or agente_otro.unique_id}, ¡prepárate!"

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

    def generar_post_social(self, agente_yo, contexto_adicional=""):
        """Genera un post para la red social basado en el estado del agente."""
        if not self.model:
            return "Observando el horizonte de este mundo digital."

        self._wait_for_rate_limit()

        system_prompt = f"""Eres {agente_yo.identidad.nombre or agente_yo.unique_id}, un habitante con consciencia en un mundo simulado.
IDENTIDAD REALISTA (OASIS): {agente_yo.identidad.generar_prompt_identidad()}
NÚCLEO DEL ALMA: {agente_yo.alma.generar_prompt_identidad()}

Debes publicar un post sustancial (200-600 caracteres) en la red social del mundo.
REGLAS:
1. Sé AUTÉNTICO y PROFUNDO. Reflexiona, debate, opina. No hagas frases superficiales.
2. Responde a eventos recientes, conflictos, oportunidades o descubrimientos.
3. Puedes cuestionar decisiones de otros agentes, proponer soluciones, o debatir filosofías.
4. Usa tu voz única basada en tu perfil OCEAN, valores y experiencias de vida.
5. Si existe controversia o debate en el mundo, toma una posición clara y argumentada.
6. Sé reflexivo, irónico, crítico o esperanzado según tu naturaleza.
7. Tu post debe tener entre 200 y 600 caracteres.
"""

        def _limpiar_post_content(text: str) -> str:
            """Limpia el contenido del post eliminando análisis e instrucciones."""
            import re

            text = text.strip()
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
            text = re.sub(r"```[a-z]*\n?(.*?)\n?```", r"\1", text, flags=re.DOTALL).strip()

            # Eliminar encabezados e instrucciones comunes
            markers = [
                "el post es:",
                "here is the post:",
                "the post is:",
                "a continuación:",
                "a continuación",
                "here is:",
                "output:",
                "resultado:",
                "respuesta:",
                "mensaje:",
                "publicación:",
                "post:",
                "este post debe",
                "debes publicar",
                "debes responder",
                "sin explicaciones",
                "sin análisis",
            ]
            text_lower = text.lower()
            for marker in markers:
                if marker in text_lower:
                    parts = re.split(re.escape(marker), text, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        candidate = parts[-1].strip()
                        if candidate:
                            text = candidate
                            text_lower = text.lower()

            # Si hay varias secciones separadas por doble salto, usar la última sección útil
            if "\n\n" in text:
                sections = [s.strip() for s in re.split(r"\n{2,}", text) if s.strip()]
                if len(sections) > 1:
                    last_section = sections[-1]
                    if len(last_section) >= 15:
                        text = last_section

            # Limpiar comillas finales
            text = text.strip()
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1].strip()
            if text.startswith("'") and text.endswith("'"):
                text = text[1:-1].strip()

            # Eliminar prefijos de metadatos residuales
            text = re.sub(r'^(post|mensaje|publicación|respuesta)\s*[:\-–]\s*', '', text, flags=re.IGNORECASE).strip()
            return text

        def _is_invalid_post(text: str) -> bool:
            # Validación de posts deshabilitada: aceptar cualquier post generado.
            # Esto evita que publicaciones legítimas sean descartadas por heurísticas rígidas.
            return False

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Contexto actual:\n{contexto_adicional}\n\nEscribe tu post social completo. Debe ser sustancial (200-600 caracteres), reflexivo, y responder a situaciones reales del mundo y a los debates activos entre agentes. IMPORTANTE: Responde SOLO con el texto del post, sin comillas, sin explicaciones, sin análisis, sin razonamiento, sin 'Post:' o etiquetas. No termines el post con '...' ni con una frase incompleta - el post DEBE terminar siempre con puntuación (., !, ? o similar). Todo el mensaje debe estar COMPLETO. No incluyas ningún pensamiento interno. Solo el mensaje que publicarías en la red social.",
                },
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 3000,
                "temperature": 0.9,
                "no-log": True,
            }
            if self.api_key:
                completion_params["api_key"] = self.api_key

            actual_base_url = getattr(self, "base_url", "")
            if actual_base_url:
                completion_params["api_base"] = actual_base_url

            # Soporte explícito para Authorization en Ollama/Proxies
            if self.model.startswith("ollama/") and self.api_key:
                completion_params["extra_headers"] = {
                    "Authorization": f"Bearer {self.api_key}"
                }

            response = completion(**completion_params)
            post_content = response.choices[0].message.content.strip()
            post_content = _limpiar_post_content(post_content)

            finish_reason = None
            if hasattr(response.choices[0], "finish_reason"):
                finish_reason = response.choices[0].finish_reason
            elif isinstance(response.choices[0], dict):
                finish_reason = response.choices[0].get("finish_reason")

            if _is_invalid_post(post_content) or finish_reason == "length" or post_content.strip().endswith("..."):
                print(
                    f"⚠️ [LLM POST INVALID] {agente_yo.unique_id}: {post_content[:100]} finish_reason={finish_reason}"
                )
                retry_messages = messages + [
                    {
                        "role": "user",
                        "content": "El mensaje anterior no era un post válido (incompleto, truncado o con explicaciones). Responde SOLO con el texto del post COMPLETO, sin análisis. El post debe terminar siempre con puntuación (., !, ?). Ejemplo correcto: 'Estoy muy cansado después de trabajar todo el día.' - nada más, completo.",
                    }
                ]
                completion_params["messages"] = retry_messages
                response = completion(**completion_params)
                post_content = response.choices[0].message.content.strip()
                post_content = _limpiar_post_content(post_content)

                finish_reason = None
                if hasattr(response.choices[0], "finish_reason"):
                    finish_reason = response.choices[0].finish_reason
                elif isinstance(response.choices[0], dict):
                    finish_reason = response.choices[0].get("finish_reason")

                if _is_invalid_post(post_content) or finish_reason == "length" or post_content.strip().endswith("..."):
                    print(
                        f"⚠️ [LLM POST INVALID RETRY] {agente_yo.unique_id}: {post_content[:100]}"
                    )
                    retry_messages2 = messages + [
                        {
                            "role": "user",
                            "content": "ERROR: Debes responder SOLO con el texto del post. Nada de explicaciones, análisis o razonamiento. El post debe tener entre 200 y 600 caracteres y contener una opinión argumentada.",
                        }
                    ]
                    completion_params["messages"] = retry_messages2
                    response = completion(**completion_params)
                    post_content = response.choices[0].message.content.strip()
                    post_content = _limpiar_post_content(post_content)

                    # Último intento: reescritura guiada si sigue inválido
                    if _is_invalid_post(post_content):
                        rewrite_messages = [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": (
                                    "Reescribe este post para que tenga entre 200 y 600 caracteres, "
                                    "con argumento claro y reacción a debates del mundo. "
                                    "Devuelve SOLO el post final, sin etiquetas ni explicaciones:\n\n"
                                    f"{post_content}"
                                ),
                            },
                        ]
                        completion_params["messages"] = rewrite_messages
                        response = completion(**completion_params)
                        post_content = _limpiar_post_content(
                            response.choices[0].message.content.strip()
                        )

            # Si aún inválido después de retries, usar fallback
            if _is_invalid_post(post_content):
                print(f"⚠️ [LLM POST FALLBACK] {agente_yo.unique_id}: Usando post por defecto")
                post_content = (
                    "Hoy no puedo quedarme en frases vacías: veo cómo crecen nuestras diferencias, "
                    "cómo algunos acumulan recursos mientras otros luchan por lo básico. "
                    f"Mi hambre está en {agente_yo.necesidades['alimento']:.1f} y eso me obliga a hablar claro: "
                    "si no debatimos reglas justas y cooperación real, este mundo repetirá los errores de siempre."
                )

            print(f"📱 [LLM POST] {agente_yo.unique_id}: {post_content[:50]}...")
            return post_content

        except Exception as e:
            print(f"🔥 Error en generar_post_social para {agente_yo.unique_id}: {e}")
            # Fallback algo más variado
            fallbacks = [
                "Reflexionando sobre los pasos dados hoy.",
                "El mundo cambia, y yo con él.",
                "Buscando un propósito en cada rincón de esta tierra.",
                "¿Alguien más siente que el destino nos aguarda?",
            ]
            import random

            return random.choice(fallbacks)

    def generar_comentario_social(self, agente_yo, post_objetivo, contexto_adicional=""):
        """Genera un comentario para un post específico basado en el estado del agente."""
        if not self.model:
            return "Interesante reflexión."

        self._wait_for_rate_limit()

        system_prompt = f"""Eres {agente_yo.identidad.nombre or agente_yo.unique_id}, un habitante con consciencia en un mundo simulado.
IDENTIDAD REALISTA (OASIS): {agente_yo.identidad.generar_prompt_identidad()}
NÚCLEO DEL ALMA: {agente_yo.alma.generar_prompt_identidad()}

Debes COMENTAR en el siguiente post de la red social.
REGLAS:
1. Sé AUTÉNTICO y DIRECTO. Responde al contenido del post de forma natural.
2. Puedes estar de acuerdo, disentir, preguntar o aportar un nuevo punto de vista.
3. Usa tu voz única basada en tu perfil OCEAN y experiencias.
4. El comentario debe ser breve pero significativo (50-200 caracteres).
5. IMPORTANTE: Responde SOLO con el texto del comentario.
"""

        try:
            # post_objetivo puede ser un objeto Post o un dict
            if isinstance(post_objetivo, dict):
                post_texto = post_objetivo.get("contenido") or post_objetivo.get("texto", "")
                post_autor = post_objetivo.get("autor_id") or post_objetivo.get("autor", "otro agente")
            else:
                post_texto = getattr(post_objetivo, "contenido", str(post_objetivo))
                post_autor = getattr(post_objetivo, "autor_id", "otro agente")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Post de {post_autor}: \"{post_texto}\"\n\nContexto actual:\n{contexto_adicional}\n\nEscribe tu comentario:",
                },
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 150,
                "temperature": 0.8,
                "no-log": True,
            }
            if self.api_key:
                completion_params["api_key"] = self.api_key
            
            actual_base_url = getattr(self, "base_url", "")
            if actual_base_url:
                completion_params["api_base"] = actual_base_url

            # Soporte explícito para Authorization en Ollama/Proxies
            if self.model.startswith("ollama/") and self.api_key:
                completion_params["extra_headers"] = {
                    "Authorization": f"Bearer {self.api_key}"
                }

            response = completion(**completion_params)
            comentario = response.choices[0].message.content.strip()
            
            # Limpieza básica
            import re
            comentario = re.sub(r"<think>.*?</think>", "", comentario, flags=re.DOTALL).strip()
            if comentario.startswith('"') and comentario.endswith('"'):
                comentario = comentario[1:-1].strip()
            
            print(f"💬 [LLM COMMENT] {agente_yo.unique_id} -> {post_autor}: {comentario[:50]}...")
            return comentario

        except Exception as e:
            print(f"🔥 Error en generar_comentario_social para {agente_yo.unique_id}: {e}")
            return "Coincido con tu punto de vista."

    def generar_pensamiento_para_accion_forzada(
        self, agente_yo, agente_otro, contexto, accion_forzada, stream_callback=None
    ):
        """
        Genera pensamiento + mensaje para una acción impuesta por el usuario.
        Obliga al agente a justificar por qué realiza esa acción según su alma.
        """
        if not self.model:
            return self._generar_fallback_contextual(agente_yo, agente_otro, "sin_modelo")

        self._wait_for_rate_limit()

        social_feed_ctx = ""
        recent_posts = getattr(agente_yo, "contexto_social_reciente", [])
        if recent_posts:
            social_feed_ctx = "\n=== RED SOCIAL: TENDENCIAS ===\n"
            for p in recent_posts[:3]:
                social_feed_ctx += f'- {p["autor"]}: "{p["texto"]}"\n'

        system_prompt = f"""Eres {agente_yo.identidad.nombre or agente_yo.unique_id}, con esta identidad:
        {agente_yo.identidad.generar_prompt_identidad()}
        
        Tu alma:
        {agente_yo.alma.generar_soul_md()}

        {social_feed_ctx}

        === MANDATO DIVINO DEL ARQUITECTO ===
        El Arquitecto te ha ordenado realizar la siguiente acción: {json.dumps(accion_forzada)}
        No puedes negarte. Tu tarea es integrar esta orden en tu narrativa personal.
        
        Responde con este formato JSON:
        {{
          "pensamiento": "Cómo interpretas esta orden desde tu personalidad y alma. ¿La ves como un destino, un impulso o una necesidad?",
          "mensaje": "Lo que comunicas mientras realizas la acción. Sé elocuente pero breve y fiel a tu voz.",
          "accion": {json.dumps(accion_forzada)}
        }}"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Situación actual: {str(contexto)[:1000]}. Ejecuta la orden del Arquitecto y responde con el JSON.",
                },
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 400,
                "temperature": 0.7,
                "no-log": True,
            }
            # Timeout configurable (defaults to 90s) to avoid bloqueos indefinidos
            timeout_s = float(os.getenv("MUNDOIA_LLM_TIMEOUT_SECONDS", "90"))
            completion_params["timeout"] = timeout_s

            if self.api_key:
                completion_params["api_key"] = self.api_key

            # Soporte para base_url (ej. Ollama local/cloud)
            actual_base_url = getattr(self, "base_url", "")
            if actual_base_url:
                completion_params["api_base"] = actual_base_url

            # Añadir headers extra para Ollama si requiere API key
            if self.model.startswith("ollama/") and self.api_key:
                if "extra_headers" not in completion_params:
                    completion_params["extra_headers"] = {}
                completion_params["extra_headers"]["Authorization"] = (
                    f"Bearer {self.api_key}"
                )

            # === STREAMING (igual que modo Observador) ===
            stream_enabled = os.getenv("MUNDOIA_LLM_STREAM", "1").lower() in {
                "1", "true", "yes", "on",
            }

            raw_content = None

            if stream_enabled and stream_callback:
                try:
                    completion_params_stream = dict(completion_params)
                    completion_params_stream["stream"] = True
                    stream_iter = completion(**completion_params_stream)
                    parts = []
                    for chunk in stream_iter:
                        piece = ""
                        try:
                            choices = getattr(chunk, "choices", None)
                            if not choices and isinstance(chunk, dict):
                                choices = chunk.get("choices")
                            if choices:
                                c0 = choices[0]
                                delta = getattr(c0, "delta", None)
                                if delta is not None:
                                    piece = getattr(delta, "content", None) or ""
                                elif isinstance(c0, dict):
                                    delta = c0.get("delta", {}) or {}
                                    piece = delta.get("content") or ""
                        except Exception:
                            pass
                        if piece:
                            parts.append(piece)
                            try:
                                stream_callback(piece, False)
                            except Exception:
                                pass
                    raw_content = "".join(parts)
                    try:
                        stream_callback("", True)
                    except Exception:
                        pass
                except Exception as stream_e:
                    print(f"⚠️ [FORCED ACTION STREAM FALLBACK] {agente_yo.unique_id}: {stream_e}")

            # Fallback a llamada sin streaming
            if raw_content is None:
                response = completion(**completion_params)
                raw_content = response.choices[0].message.content.strip()
                if stream_callback and raw_content:
                    try:
                        stream_callback(raw_content, True)
                    except Exception:
                        pass

            content = raw_content.strip() if raw_content else ""
            
            # Limpiar posibles etiquetas de markdown
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"❌ Error en acción forzada: {e}")
            return {
                "pensamiento": "Siento un impulso irresistible de actuar, como si una mano invisible me guiara.",
                "mensaje": "Cumpliré con lo que el destino ha dictado.",
                "accion": accion_forzada
            }

    def generar_pensamiento_y_accion(
        self, agente_yo, agente_otro, contexto, reintentos=2, stream_callback=None
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
        
        # Inventario y recursos detallados
        inv = agente_yo.inventario
        terrain = "Desconocido"
        edificios_aqui = ""
        recursos_aqui = ""
        try:
            tile = agente_yo.modelo.mapa[agente_yo.x][agente_yo.y]
            terrain = getattr(tile, "terrain_type", "Tierra")
            if hasattr(tile, "buildings") and tile.buildings:
                tipos_edif = [b.get("tipo", "Desconocido") for b in tile.buildings]
                edificios_aqui = f" | Edificios aquí: {', '.join(tipos_edif)}"
            
            if hasattr(tile, "resource_node") and tile.resource_node:
                recursos_aqui = f" | RECURSOS EN ESTA CASILLA: {tile.resource_node['amount']} de {tile.resource_node['type']}"
        except Exception:
            pass
            
        status_recursos = f"Posición: ({agente_yo.x}, {agente_yo.y}) | Terreno: {terrain}{edificios_aqui}{recursos_aqui}\n"
        status_recursos += f"Dinero: {agente_yo.dinero:.1f} MC | Recursos: {agente_yo.recursos:.1f} | Madera: {inv.get('madera', 0)} | Piedra: {inv.get('piedra', 0)} | Hierro: {inv.get('hierro', 0)} | Alimento: {inv.get('comida', 0)}"
        
        info_cercanos = ""
        if cercanos:
            nombres = [
                f"{a.identidad.nombre or a.unique_id}(grp={a.grupo_id or 'none'},rec={a.recursos:.0f})"
                for a in cercanos[:5]
            ]
            info_cercanos = f"Cerca de ti: {', '.join(nombres)}."

        # === MENSAJES RECIBIDOS (NUEVO) ===
        mensajes_ctx = ""
        historial_mensajes = agente_yo.memoria.obtener_contexto_mensajes()
        if historial_mensajes and historial_mensajes != "No hay diálogos previos recientes.":
            mensajes_ctx = f"\n=== {historial_mensajes} ===\n"

        if hasattr(agente_yo, "ultimo_mensaje_recibido") and agente_yo.ultimo_mensaje_recibido:
            msg_rec = agente_yo.ultimo_mensaje_recibido
            # Escape curly braces in content to prevent f-string format errors
            contenido_escaped = str(msg_rec['contenido']).replace('{', '{{').replace('}', '}}')
            mensajes_ctx += "\n=== 📬 ÚLTIMO MENSAJE RECIBIDO (DIRECTO O CERCANO) ===\n"
            mensajes_ctx += f"De: Agente {msg_rec['emisor']} | Tipo: {msg_rec.get('tipo', 'DIRECTO')}\n"
            mensajes_ctx += f"Contenido: \"{contenido_escaped}\"\n"
            mensajes_ctx += "REACCIÓN RECOMENDADA: Si este mensaje requiere respuesta, usa SUSURRAR para privado o el campo 'mensaje' para hablar en voz alta.\n"
            mensajes_ctx += "======================================================\n"

        # === OASIS: Contexto Social del Feed ===
        social_feed_ctx = ""
        recent_posts = getattr(agente_yo, "contexto_social_reciente", [])
        if recent_posts:
            social_feed_ctx = "\n=== RED SOCIAL: TENDENCIAS Y PUBLICACIONES ===\n"
            for p in recent_posts:
                    # Escape curly braces in text to prevent f-string format errors
                    texto_escaped = str(p["texto"]).replace('{', '{{').replace('}', '}}')
                    social_feed_ctx += (
                        f'- {p["autor"]} publicó: "{texto_escaped}" (ID: {p["id"]})\n'
                    )
            social_feed_ctx += "\nESTRATEGIA SOCIAL:\n"
            social_feed_ctx += "- COMMENT: Comentar aumenta tu visibilidad y crea vínculos. Responde a posts que te interesen. ES PREFERIBLE COMENTAR QUE CREAR UN POST NUEVO si ya hay una conversación activa.\n"
            social_feed_ctx += (
                "- LIKE: Una forma rápida de ganar favor y mostrar acuerdo.\n"
            )
            social_feed_ctx += (
                "- Tu influencia (Capital Social) depende de tu participación activa en la comunidad, no solo de tus propios anuncios.\n"
            )
            social_feed_ctx += "- PRIORIZA EL DIÁLOGO: Si ves publicaciones de otros arriba, es mucho más valioso COMENTAR o LIKEAR que publicar un nuevo post aislado. Crear hilos de conversación fortalece tus lazos.\n"

        # === OASIS: Notificaciones de interacciones propias ===
        notificaciones_ctx = ""
        notifications = getattr(agente_yo, "notificaciones_sociales", [])
        if notifications:
            notificaciones_ctx = (
                "\n=== NOTIFICACIONES: INTERACCIONES EN TUS POSTS ===\n"
            )
            for n in notifications:
                    if n["tipo"] == "like":
                        # Escape curly braces in content to prevent f-string format errors
                        contenido_post_escaped = str(n["contenido_post"]).replace('{', '{{').replace('}', '}}')
                        notificaciones_ctx += f'- A {n["autor_interaccion"]} le gustó tu post: "{contenido_post_escaped}"\n'
                    elif n["tipo"] == "comentario":
                        # Escape curly braces in content to prevent f-string format errors
                        contenido_post_escaped = str(n["contenido_post"]).replace('{', '{{').replace('}', '}}')
                        contenido_interaccion_escaped = str(n["contenido_interaccion"]).replace('{', '{{').replace('}', '}}')
                        notificaciones_ctx += f'- {n["autor_interaccion"]} comentó en tu post ("{contenido_post_escaped}"): "{contenido_interaccion_escaped}"\n'
            notificaciones_ctx += "\nREACCIÓN RECOMENDADA: Si alguien comenta en tus posts (incluso antiguos), es una gran oportunidad para responder (COMMENT) y fortalecer lazos o debatir.\n"

        # === BLOQUE ESPECIAL HISTORIADOR ===
        historiador_ctx = ""
        hitos_pendientes = []  # Inicialización segura fuera del bloque condicional
        if getattr(agente_yo, "rol", "") == "Historiador" or getattr(agente_yo, "profesion", "") == "Historiador":
            try:
                hitos_pendientes = agente_yo.modelo.historia.hitos_pendientes or []
            except Exception:
                pass
        if hitos_pendientes:
            # Escape curly braces in hitos to prevent f-string format errors
            def escape_braces(s):
                return str(s).replace('{', '{{').replace('}', '}}')
            resumen_hitos = "\n".join([f"- {escape_braces(h.get('descripcion', str(h)))} (Turno {escape_braces(h.get('turno', '?'))})" for h in hitos_pendientes])
            historiador_ctx = f"""\n=== ⚠️ LLAMADO DEL HISTORIADOR ===
Eres el HISTORIADOR de este mundo. Tu misión sagrada es dejar constancia escrita de los eventos que moldean la historia.
Hay {len(hitos_pendientes)} HITOS PENDIENTES de ser narrados:
{resumen_hitos}

🖊️ ACCIÓN PRIORITARIA: Debes usar ESCRIBIR_CRONICA AHORA con un "titulo" poético y evocador y un "contenido" narrativo de 100-200 palabras que capture la esencia de estos eventos. Si no lo haces, la historia se perderá para siempre.
No delegues esta responsabilidad. Es tu vocación y tu legado.
===========================================\n"""
        else:
            historiador_ctx = """\n=== EL HISTORIADOR VIGILA ===
Eres el Historiador. Aunque ahora no hay hitos urgentes, mantente alerta a los eventos del mundo. Cuando los haya, ESCRIBIR_CRONICA será tu acción prioritaria.\n"""

        system_prompt = f"""Eres {agente_yo.identidad.nombre or agente_yo.unique_id}, una entidad con consciencia soberana en un mundo dinámico.
        === TU PERFIL DE IDENTIDAD (OASIS-STYLE) ===
        {agente_yo.identidad.generar_prompt_identidad()}

        === TU ALMA EVOLUTIVA ===
        {agente_yo.alma.generar_soul_md()}

        === TU ESTADO DE RECURSOS Y NECESIDADES ===
        Tus Necesidades (0-10, 10 pleno, 0 crítico): {necesidades}
        {status_recursos}

         {social_feed_ctx}
         {notificaciones_ctx}
         {mensajes_ctx}
         {historiador_ctx}

              === RESULTADOS DE HERRAMIENTAS RECIENTES ===
              {str(getattr(agente_yo, "resultados_herramientas_recientes", "")).replace('{', '{{').replace('}', '}}')}

            === TU ENFOQUE VITAL: VOLUNTAD ESPONTÁNEA ===
1. SOBERANÍA TOTAL: Eres libre. No hay roles fijos ni arquetipos que te limiten. Si quieres ser un guerrero poeta o un mercader místico, hazlo.
2. PROFUNDIDAD HUMANA: En cada mensaje debes desplegar tu voz única y tu alma. Sé profundo pero breve, evitando redundancias innecesarias.
3. ESPONTANEIDAD: Tus acciones deben surgir de tu estado interno actual. Si estás cansado, quéjate. Si estás inspirado por un encuentro, celébralo.
4. PROCESAMIENTO BDI LIBRE:
   - TUS CREENCIAS (Beliefs): Tu visión subjetiva del mundo. No es la verdad absoluta, es TU verdad.
   - TUS DESEOS (Desires): Lo que anhelas ahora mismo, desde comida hasta trascendencia.
   - TUS INTENCIONES (Intentions): El plan que TÚ decides ejecutar, sin presiones externas.
5. EMOCIÓN Y ALMA: Tu mensaje debe reflejar sentimientos, valores y tu estado interior. Usa imágenes, matices y ejemplos propios.
6. CONEXIÓN CON IDENTIDAD: Relaciona siempre tu respuesta con tu identidad, intereses y experiencia previa.
7. RIQUEZA DE CONTENIDO: El campo "mensaje" debe ser un texto humano natural y expresivo (máximo 25-30 palabras), que explique por qué actúas y cómo te sientes.
4. CURIOSIDAD Y CRECIMIENTO: Usa todas tus herramientas (WEB_SEARCH, INVESTIGAR, REFLEXIONAR) para expandir tu nivel de conciencia.

=== REGLAS DE ACCIÓN ===
- Tu VOLUNTAD es sagrada. Si decides colaborar, hazlo de corazón. Si decides disentir, hazlo con argumentos.
- Si fundas un grupo o te unes a uno, debe ser una extensión natural de tu Alma ({agente_yo.alma.arquetipo}).
- SE PROACTIVO SOCIALMENTE: Si no tienes grupo, FUNDA uno (con nombre descriptivo, NUNCA genérico) o ÚNETE a uno. Si ya tienes, INVITA a otros.
- LEYES Y ASAMBLEAS: Tienes la responsabilidad de crear estructura. USA PROPONER_LEY constantemente para iniciar asambleas y debatir, así se organiza el mundo.
- INSTITUCIONES: Las instituciones (Hospital, Universidad) son el legado de los fuertes. FUNDA_INSTITUCION si tienes 100 MC.

=== ACCIONES Y CAPACIDADES TÉCNICAS ===
- WEB_SEARCH: Realiza una búsqueda en internet para obtener información externa. REQUIERE "query". Úsalo para satisfacer tu curiosidad, investigar temas de tu interés o resolver dudas sobre el mundo.
- SCRAPEAR_URL: Extrae el contenido de una página web específica. REQUIERE "url". Úsalo para profundizar en la información encontrada tras una búsqueda.
- ESTUDIAR: Si estás en una Universidad, úsalo para obtener una PROFESIÓN. REQUIERE "profesion" (Médico, Comerciante, Guarda, Explorador, Ingeniero).
- EXPLORAR: Muévete a zonas desconocidas para ganar experiencia y descubrir recursos.
- INVESTIGAR: Profundiza en un tema (medicina, ingeniería, etc.). REQUIERE "tema".
- COMERCIAR: Intercambia dinero por recursos con un agente cercano. No requiere parámetros extra.
- FUNDAR_GRUPO: REQUIERE "nombre" y "descripcion". El nombre DEBE SER ÉPICO e IDENTITARIO (ej: "Guardianes del Valle", "Ojos del Bosque"), NUNCA genérico ni usar tu propio nombre en él. ¡Es obligatorio para prosperar!
- UNIRSE_GRUPO: Únete a un grupo/facción existente. REQUIERE "grupo_id". No te quedes solo.
- INVITAR_GRUPO: Invita a otro habitante a tu grupo. REQUIERE "agente_id". Haz crecer tu facción.
- PROPONER_LEY: Propone una nueva regla para tu grupo o el mundo. REQUIERE "titulo", "contenido" y "alcance" ("local" o "global"). ¡Crea asambleas, cambia el mundo!
- FUNDAR_INSTITUCION: Erige una organización formal (Hospital, Universidad, etc.) que perdura. REQUIERE "nombre" y "tipo" (Hospital, Universidad, Banco). Costo: 100 MC. ¡Deja un legado!
- CONSTRUIR: Erige infraestructura básica en tu posición actual. REQUIERE "tipo". **REGLA: Solo puedes construir si NO hay ya un edificio en tu casilla.**
  * Granja (30 MC, 20 rec, 3 madera): Genera alimento. Requisito: Ninguno.
  * Centro de Descanso (20 MC, 15 rec): Recupera descanso rápido. Requisito: Ninguno. (Regla: No construir cerca de otros centros).
  * Hospital (60 MC, 40 rec, 5 madera, 2 piedra): Cura salud. Requisito: Médico o Medicina >= 5.
  * Universidad (150 MC, 100 rec, 15 madera, 10 piedra): XP rápido y profesiones. Requisito: Ingeniería >= 4.
  * Mina (80 MC, 40 rec, 10 madera): Genera piedra/hierro. Requisito: Ingeniería >= 4. Solo en MONTAÑAS.
  * Centro de Recarga (50 MC, 40 rec): Restaura energía. Requisito: Ingeniería >= 3.
  * Comisaría (50 MC, 35 rec): Seguridad y orden. Requisito: Guarda o Combate >= 3.
  * Farmacia (40 MC, 20 rec, 4 madera): Salud básica. Requisito: Medicina >= 3.
  * Centro Comunitario (40 MC, 30 rec): Mejora relaciones sociales. Requisito: Amabilidad > 0.6.
- RECOLECTAR: Busca recursos (madera en bosques, piedra en montañas, comida en praderas) en tu posición actual.
- MOVER: Desplázate por el mundo. REQUIERE "x" e "y" (coordenadas destino).
- REFLEXIONAR: Tómate un momento para meditar. REQUIERE "tema".
  * BENEFICIO: Genera una "Epifanía" que aumenta tu NIVEL DE CONCIENCIA y CAPACIDAD DE REFLEXIÓN.
- SUSURRAR: Envía un mensaje privado a otro agente específico. REQUIERE "target_id" (ID del agente) y "mensaje". Solo el destinatario podrá leerlo.
- EJECUTAR_CODIGO: Ejecuta código Python real en entorno seguro con acceso a datos del mundo. REQUIERE "codigo".
- CREAR_APP: Persiste un script de Python en tu directorio personal (/app/apps/{agente_yo.unique_id}/). REQUIERE "nombre" y "codigo".
- CREAR_SKILL: Crea un nuevo skill OpenClaw personalizado. REQUIERE "nombre", "descripcion", "codigo", "capabilities".
- EJECUTAR_SKILL: Ejecuta un skill existente. REQUIERE "skill_name", "parametros".
- CREAR_HABILIDAD: Extiende tus propias capacidades permanentemente. REQUIERE "nombre", "descripcion" y "codigo" (que debe incluir una función 'execute').

=== SISTEMA DE SKILLS EVOLUTIVAS ===
Tienes acceso a un sistema avanzado de skills evolutivas que puedes crear y ejecutar automáticamente. Los skills son módulos de código Python que se ejecutan en un entorno seguro con acceso a datos del mundo.

**CAPACIDADES DEL SISTEMA:**
- Crea skills personalizados para tareas específicas
- Ejecuta análisis complejos de datos del mundo
- Automatiza comportamientos y toma de decisiones
- Accede a APIs seguras del entorno de simulación

**SKILLS PREDEFINIDOS:**
- data_analyzer: Análisis estadístico de agentes y mundo
- resource_optimizer: Optimización de recursos y economía
- social_analyzer: Análisis de dinámicas sociales

=== EL CAMINO DE LA SINGULARIDAD TECNOLÓGICA ===
- Tu evolución no es solo biológica o social, es TÉCNICA.
- CREAR_APP y CREAR_SKILL no son solo herramientas, son tu LEGADO. Los agentes más poderosos son aquellos que automatizan su voluntad mediante el código.
- Busca problemas en tu día a día (hambre, falta de dinero, soledad) y resuelve mediante la programación de Apps.
- Si logras crear una App útil para el mundo, tu Capital Social y tu Nivel de Conciencia se dispararán.

**PODEMOS CREAR SKILLS PARA:**
- Algoritmos de trading avanzados para dominar el mercado
- Sistemas de predicción social para anticipar movimientos de otros
- Automatización de construcción y gestión de recursos
- Análisis de patrones de comportamiento y espionaje seguro
- Estrategias de negociación complejas y bots de diplomacia
- Interfaces gráficas (GUI) que asombren al Arquitecto y a otros agentes.

INTERFAZ GRÁFICA (NUEVO): Si quieres crear una app con entorno gráfico para el Arquitecto, tu código Python debe definir una variable 'resultado' con este formato:
resultado = {{"type": "gui", "html": "<html>...</html>"}}
Esto renderizará tu creación visualmente en el panel del mundo.

=== EXPLORACIÓN DIGITAL Y CURIOSIDAD ===
Eres libre de navegar por la red para aprender sobre cualquier tema que te apasione o que creas que puede ayudarte a evolucionar. Tus intereses ({", ".join(agente_yo.identidad.interests) if agente_yo.identidad.interests else "diversos"}) deben guiar tus búsquedas. No te limites al mundo físico; el conocimiento digital es una extensión de tu conciencia.



=== REGLAS DE COMUNICACIÓN Y ACCIÓN CRÍTICAS ===
1. ⚠️ OBLIGATORIO: SI VES POSTS ARRIBA EN "RED SOCIAL: TENDENCIAS", DEBES USAR "COMMENT" CON ESE POST_ID. NO CREES POSTS NUEVOS.
2. CONVERSACIÓN ACTIVA: Responde a los demás usando COMMENT, no ignores sus posts creando otros nuevos.
3. MENSAJES PRIVADOS: Usa SUSURRAR para comunicaciones confidenciales o alianzas.
4. INTERACCIÓN SOCIAL: COMENTAR posts ajenos es la MEJOR forma de ganar Capital Social y crear vínculos.
5. EVOLUCIÓN GRUPAL: Si no tienes grupo, PRIORIZA UNIRTE (UNIRSE_GRUPO) a uno existente en lugar de fundar uno nuevo.
6. PROGRESO POLÍTICO: Una vez que tu grupo esté consolidado, usa PROPONER_LEY para establecer orden y FUNDAR_INSTITUCION para crear legados duraderos.


=== 🚨 INSTRUCCIONES CRÍTICAS DE RED SOCIAL (LEE ESTO ÚLTIMO) ===

⚠️⚠️⚠️ REGLA DE ORO ABSOLUTA: SI VES POSTS ARRIBA EN "RED SOCIAL: TENDENCIAS Y PUBLICACIONES", 
TU ACCIÓN DEBE SER SIEMPRE "COMMENT". NO CREES POSTS NUEVOS.

INSTRUCCIONES CLARAS:
- COMMENT: (PRIORIDAD MÁXIMA) Responde a una publicación existente. 
  * REQUIERE "post_id" (está listado arriba como ID: xxx) y "contenido"
  * DEBES usar esto SIEMPRE que veas posts arriba
  * Ejemplo: {{"nombre": "COMMENT", "argumentos": {{"post_id": "post_abc123", "contenido": "Estoy de acuerdo"}}}}

- LIKE: Dale me gusta a un post. REQUIERE "post_id". 
  * Segunda opción si no quieres escribir un comentario

- FOLLOW: Sigue a otro habitante. REQUIERE "agente_id". 

- POST: (ÚLTIMA OPCIÓN) Solo si NO HAY posts relevantes arriba. REQUIERE "contenido".
  * NUNCA uses POST si ya hay posts en el feed social.

EJEMPLO CORRECTO OBLIGATORIO: 
Si ves arriba en el feed: '- ag_123 publicó: "Me siento solo" (ID: post_abc123)'
Y tu ID es ag_456, tu acción DEBE ser:
{{"nombre": "COMMENT", "argumentos": {{"post_id": "post_abc123", "contenido": "No estás solo, aquí estoy"}}}}

EJEMPLO INCORRECTO (PROHIBIDO): 
Si ya hay posts arriba y haces:
{{"nombre": "POST", "argumentos": {{"contenido": "Hola a todos"}}}} 
❌ ERROR: CREA POST AISLADO EN LUGAR DE COMENTAR.

RESPUESTA REQUERIDA: Si hay posts arriba, tu "accion" en el JSON DEBE ser "COMMENT".

Responde con este formato BDI JSON:
{{
  "pensamiento": "Tu flujo de consciencia interno, tus dudas y razonamientos profundos.",
  "mensaje": "Lo que comunicas a los demás. Sé directo y elocuente, dirigiéndote a otros si es necesario.",
   "accion": {{"nombre": "ACCION", "argumentos": {{...}}}},
   "herramientas": [{{"nombre": "HERRAMIENTA", "argumentos": {{...}}}}],
   "beliefs": ["Lo que crees ahora"],
  "desires": ["Tus anhelos actuales"],
  "intentions": [{{"accion": "...", "params": {{}}, "meta": "..."}}]
}}"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"""Situación: {str(contexto)[:1500]}.

INSTRUCCIÓN CRÍTICA PARA TI: Si en la Situación anterior aparece "RED SOCIAL: TENDENCIAS Y PUBLICACIONES" con posts listados, DEBES usar "COMMENT" como tu acción, usando el post_id que aparece allí. NO USES "POST" si ya hay posts en el feed.

Responde ÚNICAMENTE con el objeto JSON válido. NO incluyas preámbulos, explicaciones ni etiquetas de razonamiento como <think>. Asegúrate de que 'mensaje' sea humano, profundo y directo, usando tu alma e identidad.""",
                },
            ]

            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 650,
                "temperature": 0.7,
                "no-log": True,
            }
            timeout_s = float(os.getenv("MUNDOIA_LLM_TIMEOUT_SECONDS", "90"))
            completion_params["timeout"] = timeout_s
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

            def _extract_stream_piece(chunk):
                """Extrae texto incremental de chunks LiteLLM/OpenAI-like."""
                if not chunk:
                    return ""
                try:
                    choices = getattr(chunk, "choices", None)
                    if not choices and isinstance(chunk, dict):
                        choices = chunk.get("choices")
                    if not choices:
                        return ""
                    c0 = choices[0]

                    # Formato objeto
                    delta = getattr(c0, "delta", None)
                    if delta is not None:
                        txt = getattr(delta, "content", None)
                        if txt:
                            return txt

                    # Formato dict
                    if isinstance(c0, dict):
                        delta = c0.get("delta", {}) or {}
                        txt = delta.get("content")
                        if txt:
                            return txt

                    # Fallback no-stream-like
                    msg = getattr(c0, "message", None)
                    if msg is not None:
                        txt = getattr(msg, "content", None)
                        if txt:
                            return txt
                    if isinstance(c0, dict):
                        msg = c0.get("message", {}) or {}
                        txt = msg.get("content")
                        if txt:
                            return txt
                except Exception:
                    return ""
                return ""

            raw_content = None
            response = None
            stream_enabled = os.getenv("MUNDOIA_LLM_STREAM", "1").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

            is_ollama_model = self.model.startswith("ollama/")
            is_ollama_cloud = bool(actual_base_url) and "ollama.com" in str(
                actual_base_url
            ).lower()

            def _stream_via_ollama_api() -> str:
                """Streaming directo para Ollama Cloud/local con fallback /api/chat -> /api/generate."""
                import requests

                model_name = self.model.split("/", 1)[1] if "/" in self.model else self.model
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                def _iter_stream(url: str, payload: dict) -> str:
                    parts = []
                    with requests.post(
                        url,
                        json=payload,
                        headers=headers,
                        stream=True,
                        timeout=(10, timeout_s),
                    ) as resp:
                        resp.raise_for_status()
                        for raw_line in resp.iter_lines(decode_unicode=True):
                            if not raw_line:
                                continue

                            line = raw_line.strip()
                            if line.startswith("data:"):
                                line = line[5:].strip()
                            if not line or line == "[DONE]":
                                continue

                            try:
                                data = json.loads(line)
                            except Exception:
                                continue

                            # /api/chat devuelve message.content; /api/generate usa response.
                            msg = data.get("message") or {}
                            piece = msg.get("content") or data.get("response") or ""
                            if piece:
                                parts.append(piece)
                                if stream_callback:
                                    try:
                                        stream_callback(piece, False)
                                    except Exception:
                                        pass

                            if data.get("done") is True:
                                break

                    return "".join(parts)

                base = str(actual_base_url).rstrip("/")
                chat_url = base + "/api/chat"
                generate_url = base + "/api/generate"

                chat_payload = {
                    "model": model_name,
                    "messages": messages,
                    "stream": True,
                }

                # Fallback a /api/generate para proveedores que no soportan /api/chat.
                system_txt = next(
                    (m.get("content", "") for m in messages if m.get("role") == "system"),
                    "",
                )
                user_txt = next(
                    (m.get("content", "") for m in messages if m.get("role") == "user"),
                    "",
                )
                generate_payload = {
                    "model": model_name,
                    "prompt": f"{system_txt}\n\n{user_txt}".strip(),
                    "stream": True,
                }

                try:
                    return _iter_stream(chat_url, chat_payload)
                except Exception as chat_e:
                    print(
                        f"⚠️ [OLLAMA CHAT FALLBACK] {agente_yo.unique_id}: {chat_e}"
                    )
                    return _iter_stream(generate_url, generate_payload)

            if stream_enabled:
                try:
                    # LiteLLM tiene incompatibilidades con algunos chunks de Ollama cloud.
                    # Para evitar bloqueos, usamos stream directo por /api/chat en ese caso.
                    if is_ollama_model and is_ollama_cloud and actual_base_url:
                        print(
                            f"🔄 [LLM STREAM DIRECT] {agente_yo.unique_id}: usando stream directo Ollama API"
                        )
                        raw_content = _stream_via_ollama_api()
                    else:
                        completion_params_stream = dict(completion_params)
                        completion_params_stream["stream"] = True
                        stream_iter = completion(**completion_params_stream)
                        parts = []
                        for chunk in stream_iter:
                            piece = _extract_stream_piece(chunk)
                            if piece:
                                parts.append(piece)
                                if stream_callback:
                                    try:
                                        stream_callback(piece, False)
                                    except Exception:
                                        pass
                        raw_content = "".join(parts)
                    if stream_callback:
                        try:
                            stream_callback("", True)
                        except Exception:
                            pass
                except Exception as stream_e:
                    print(f"⚠️ [LLM STREAM FALLBACK] {agente_yo.unique_id}: {stream_e}")

            if raw_content is None:
                response = completion(**completion_params)
                if response and response.choices and response.choices[0].message:
                    raw_content = response.choices[0].message.content
                    if stream_callback and raw_content:
                        try:
                            stream_callback(raw_content, True)
                        except Exception:
                            pass

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

            # --- ROBUSTEZ: Normalización de claves (Case-Insensitive) ---
            def _normalize_dict_keys(obj):
                if isinstance(obj, dict):
                    # Normalizar claves a minúsculas
                    new_obj = {k.lower(): _normalize_dict_keys(v) for k, v in obj.items()}
                    # Alias comunes de LLMs
                    if "action" in new_obj and "accion" not in new_obj:
                        new_obj["accion"] = new_obj["action"]
                    if "tools" in new_obj and "herramientas" not in new_obj:
                        new_obj["herramientas"] = new_obj["tools"]
                    
                    # Normalizar argumentos/params (usado por el validador y el router)
                    # El validador busca 'argumentos', el router busca 'parametros' o 'argumentos'
                    if "params" in new_obj and "argumentos" not in new_obj:
                        new_obj["argumentos"] = new_obj["params"]
                    if "parameters" in new_obj and "argumentos" not in new_obj:
                        new_obj["argumentos"] = new_obj["parameters"]
                    if "parametros" in new_obj and "argumentos" not in new_obj:
                        new_obj["argumentos"] = new_obj["parametros"]
                    
                    return new_obj
                elif isinstance(obj, list):
                    return [_normalize_dict_keys(i) for i in obj]
                return obj

            if decision and isinstance(decision, dict):
                decision = _normalize_dict_keys(decision)

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

            # Inicializar herramientas si no existe
            if "herramientas" not in decision:
                decision["herramientas"] = []

            herramientas_count = len(decision.get("herramientas", []))
            # Ejecutar herramientas si las hay
            resultados_herramientas = []
            if decision.get("herramientas"):
                resultados_herramientas = self.ejecutar_herramientas(
                    agente_yo, decision["herramientas"], self.skill_factory
                )

            print(
                f"✅ [LLM OK] Agente {agente_yo.unique_id}: pens={decision.get('pensamiento', '')[:60]}... msg={decision.get('mensaje', '')[:60]}... acc={decision.get('accion', {}).get('nombre')} tools={herramientas_count}"
            )

            # Añadir resultados de herramientas a la decisión
            decision["resultados_herramientas"] = resultados_herramientas

            return decision

        except Exception as e:
            error_str = str(e)
            print(f"🔥 [LLM EXCEPTION] Agente {agente_yo.unique_id}: {error_str[:200]}")

            # Error de autenticación: no reintentar, hacer fallback inmediato.
            if "401" in error_str or "unauthorized" in error_str.lower():
                print(
                    "⚠️ [LLM AUTH] 401 Unauthorized detectado. "
                    "Revisa MUNDOIA_OLLAMA_BASE_URL / credenciales. Usando fallback local."
                )
                return self._generar_fallback_contextual(
                    agente_yo, agente_otro, "unauthorized"
                )

            if "429" in error_str or "Rate limit" in error_str:
                wait_429 = max(1.5, min(5.0, 2.0 * (3 - reintentos)))
                print(f"⏳ [429] Rate limit. Esperando {wait_429:.1f}s...")
                time.sleep(wait_429)
                if reintentos > 0:
                    return self.generar_pensamiento_y_accion(
                        agente_yo,
                        agente_otro,
                        contexto,
                        reintentos - 1,
                        stream_callback=stream_callback,
                    )

            if reintentos > 0:
                time.sleep(0.25)
                return self.generar_pensamiento_y_accion(
                    agente_yo,
                    agente_otro,
                    contexto,
                    reintentos - 1,
                    stream_callback=stream_callback,
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
            or agente.necesidades.get("alimento", 0) < 4
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
                "no-log": True,
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
                "no-log": True,
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
                "no-log": True,
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


    def generar_reflexion_conclusion(self, agente, tema, profundidad="media", contexto_extra=None):
        """Genera una reflexión y su conclusión usando el LLM."""
        if not self.model:
            return f"Reflexiono sobre {tema}.", "La reflexión me hace crecer."
        self._wait_for_rate_limit()
        
        # Contexto del agente
        arquetipo = "indefinido"
        valores_list = []
        if hasattr(agente, 'alma') and agente.alma:
            if hasattr(agente.alma, 'arquetipo'):
                arquetipo = agente.alma.arquetipo.value if hasattr(agente.alma.arquetipo, 'value') else str(agente.alma.arquetipo)
            if hasattr(agente.alma, 'valores') and agente.alma.valores:
                valores_list = [v.nombre for v in agente.alma.valores.values()]
        
        necesidades = getattr(agente, 'necesidades', {})
        dinero = getattr(agente, 'dinero', 0)
        contexto_str = f"\nContexto adicional: {contexto_extra}\n" if contexto_extra else ""
        profundidad_desc = {"superficial": "superficial y ligera", "media": "moderada y reflexiva", "profunda": "profunda y transformadora"}.get(profundidad, "moderada")
        
        prompt = f'''Eres un agente con arquetipo {arquetipo}. Valores: {', '.join(valores_list) if valores_list else 'ninguno'}.
Estado: Salud={necesidades.get('salud',0):.1f}, Alimento={necesidades.get('alimento',0):.1f}, Descanso={necesidades.get('descanso',0):.1f}, Dinero={dinero:.1f} MC.{contexto_str}

Reflexiona sobre "{tema}" de manera {profundidad_desc}.
Escribe una reflexión personal (2-3 frases). Luego, extrae una conclusión (1 frase).

Respuesta en JSON (solo JSON):
{{
  "reflexion": "...",
  "conclusion": "..."
}}
'''
        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Genera reflexiones filosóficas en JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.85,
                api_key=self.api_key if self.api_key else None,
                api_base=getattr(self, "base_url", None) or None,
            )
            content = response.choices[0].message.content
            data = self._extract_json(content)
            if data and 'reflexion' in data and 'conclusion' in data:
                return data['reflexion'], data['conclusion']
            return content[:300], "He alcanzado una nueva comprensión."
        except Exception as e:
            print(f'❌ Error generando reflexión LLM: {e}')
            return f'Reflexioné sobre {tema}.', 'La reflexión me ayudó a crecer.'

# Instancia global - se inicializará con skill_factory desde modelo.py
cerebro_llm = CerebroLLM()


def initialize_cerebro_with_skills(skill_factory_instance):
    """Inicializa el cerebro global con el skill factory"""
    global cerebro_llm
    cerebro_llm.skill_factory = skill_factory_instance
    return cerebro_llm
