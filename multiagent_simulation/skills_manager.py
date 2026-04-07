import logging
import signal
from typing import Dict, Any, Optional, List
from RestrictedPython import compile_restricted, safe_builtins

logger = logging.getLogger(__name__)


class Skill:
    def __init__(
        self,
        name: str,
        description: str,
        code: str,
        author_id: Optional[str] = None,
        version: str = "1.0.0",
        experiencia_ganada: Optional[Dict[str, float]] = None,
        efecto_necesidades: Optional[Dict[str, float]] = None,
    ):
        self.name = name
        self.description = description
        self.code = code
        self.author_id = author_id
        self.version = version
        self.experiencia_ganada = experiencia_ganada or {}
        self.efecto_necesidades = efecto_necesidades or {}

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "author_id": self.author_id,
            "version": self.version,
            "experiencia_ganada": self.experiencia_ganada,
            "efecto_necesidades": self.efecto_necesidades,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            description=data["description"],
            code=data["code"],
            author_id=data.get("author_id"),
            version=data.get("version", "1.0.0"),
            experiencia_ganada=data.get("experiencia_ganada", {}),
            efecto_necesidades=data.get("efecto_necesidades", {}),
        )


class SkillManager:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.base_skills: Dict[str, Skill] = {}
        self._initialize_base_skills()

    def _log(self, mensaje, categoria="skill"):
        if self.log_callback:
            self.log_callback(mensaje, categoria)

    def _initialize_base_skills(self):
        # Migrated from herramientas.py
        # Cada skill ahora puede tener:
        # - experiencia_ganada: dict con categorías de experiencia (ej: {"medicina": 0.5, "social": 0.2})
        # - efecto_necesidades: dict con cambios en necesidades (ej: {"alimento": -0.5, "social": 0.3})

        self.base_skills["web_search"] = Skill(
            name="web_search",
            description="Realiza una búsqueda general en la web usando la API de Brave.",
            code="""
def execute(query, agente_id=None, **kwargs):
    import os
    import requests
    brave_key = os.getenv("BRAVE_API_KEY")
    if not brave_key:
        return "No tengo configurada la llave de búsqueda web (Brave)."
    
    try:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": brave_key
        }
        params = {"q": query, "count": 5}
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        results = data.get("web", {}).get("results", [])
        if not results:
            return "No se encontraron resultados relevantes en la web."
        
        info = "Resultados de búsqueda web: "
        for r in results:
            info += f"- {r['title']}: {r['description']} "
        return info
    except Exception as e:
        return f"Error en la búsqueda web: {str(e)}"
""",
            experiencia_ganada={"exploracion": 0.3, "social": 0.1},
            efecto_necesidades={"alimento": -0.3, "social": 0.1},
        )

        self.base_skills["consultar_mercado"] = Skill(
            name="consultar_mercado",
            description="Devuelve el precio actual de los recursos en MundoCoins.",
            code="""
def execute(agente_id=None, **kwargs):
    import random
    precio = random.uniform(1.5, 5.0)
    return f"El precio actual del recurso es de {precio:.2f} MC por unidad."
""",
            experiencia_ganada={"comercio": 0.3},
            efecto_necesidades={"alimento": -0.2},
        )

        self.base_skills["ejecutar_codigo_seguro"] = Skill(
            name="ejecutar_codigo_seguro",
            description="Ejecuta código Python en un entorno restringido.",
            code="""
def execute(codigo, agente_id=None, **kwargs):
    from RestrictedPython import compile_restricted, safe_builtins
    import sys
    from io import StringIO
    
    try:
        # 1. Compilación restringida
        bytecode = compile_restricted(codigo, '<string>', 'exec')
        
        # 2. Entorno seguro
        safe_globals = safe_builtins.copy()
        safe_globals.update({
            "abs": abs, "min": min, "max": max, "sum": sum, "round": round,
            "len": len, "list": list, "dict": dict, "set": set, "range": range,
            "int": int, "float": float, "str": str, "bool": bool, "any": any, "all": all,
            "sorted": sorted, "type": type
        })
        
        # 3. Redirigir stdout para capturar print
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        
        # 4. Ejecución
        exec_globals = {"__builtins__": safe_globals}
        exec(bytecode, exec_globals, {})
        
        sys.stdout = old_stdout
        result = redirected_output.getvalue()
        
        if len(result) > 1000:
            result = result[:1000] + "\\n... [Resultado truncado]"
        
        return result if result else "Código ejecutado sin salida."
    except Exception as e:
        if 'sys' in locals() and 'old_stdout' in locals():
            sys.stdout = old_stdout
        return f"Error de ejecución: {str(e)}"
""",
            experiencia_ganada={"ingenieria": 0.5, "exploracion": 0.2},
            efecto_necesidades={"alimento": -0.5},
        )

        self.base_skills["scrapear_url"] = Skill(
            name="scrapear_url",
            description="Extrae el texto principal de una URL.",
            code="""
def execute(url, agente_id=None, **kwargs):
    import requests
    from bs4 import BeautifulSoup
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\\n'.join(chunk for chunk in chunks if chunk)
        return f"Contenido extraído de {url}: {text[:500]}..."
    except Exception as e:
        return f"Error al scrapear {url}: {str(e)}"
""",
            experiencia_ganada={"exploracion": 0.4, "social": 0.1},
            efecto_necesidades={"alimento": -0.3},
        )

        self.base_skills["obtener_clima"] = Skill(
            name="obtener_clima",
            description="Consulta el clima en una ciudad.",
            code="""
def execute(ciudad="Madrid", agente_id=None, **kwargs):
    return f"El clima en {ciudad} parece despejado y propicio para la actividad de los agentes."
""",
            experiencia_ganada={"exploracion": 0.1},
            efecto_necesidades={"alimento": -0.1, "social": 0.1},
        )

        self.base_skills["crear_habilidad"] = Skill(
            name="crear_habilidad",
            description="Crea una nueva habilidad/tool. Requiere nombre, descripción y código Python con una función execute.",
            code="""
def execute(nombre, descripcion, codigo, experiencia=None, efecto_necesidades=None, agente_id=None, **kwargs):
    # Esta skill es especial, el resultado será procesado por el motor para añadirla al agente
    experiencia = experiencia or {}
    efecto_necesidades = efecto_necesidades or {}
    return {"status": "success", "new_skill": {"name": nombre, "description": descripcion, "code": codigo, "experiencia_ganada": experiencia, "efecto_necesidades": efecto_necesidades}}
""",
            experiencia_ganada={"ingenieria": 1.0, "social": 0.3},
            efecto_necesidades={"alimento": -1.0},
        )

        # Skills adicionales para la simulación social
        self.base_skills["cultivar"] = Skill(
            name="cultivar",
            description="Cultiva alimentos en una parcela de tierra.",
            code="""
def execute(agente_id=None, **kwargs):
    return "Has cultivado alimentos."
""",
            experiencia_ganada={"agricultura": 0.5},
            efecto_necesidades={"alimento": 0.8, "salud": 0.2},
        )

        self.base_skills["medicar"] = Skill(
            name="medicar",
            description="Proporciona atención médica a otros agentes.",
            code="""
def execute(agente_id=None, **kwargs):
    return "Has proporcionado atención médica."
""",
            experiencia_ganada={"medicina": 0.6},
            efecto_necesidades={"alimento": -0.3, "social": 0.3, "salud": 0.5},
        )

        self.base_skills["comerciar"] = Skill(
            name="comerciar",
            description="Intercambia recursos con otros agentes.",
            code="""
def execute(agente_id=None, **kwargs):
    return "Has realizado un intercambio comercial."
""",
            experiencia_ganada={"comercio": 0.5},
            efecto_necesidades={"alimento": -0.2, "social": 0.2},
        )

        self.base_skills["explorar"] = Skill(
            name="explorar",
            description="Explora el mapa en busca de recursos.",
            code="""
def execute(agente_id=None, **kwargs):
    return "Has explorado el territorio."
""",
            experiencia_ganada={"exploracion": 0.5},
            efecto_necesidades={"alimento": -0.4},
        )

        self.base_skills["construir"] = Skill(
            name="construir",
            description="Construye estructuras (Granja, Hospital, Universidad, Mina, Centro de Descanso, Centro Comunitario). Requiere 'tipo'.",
            code="""
def execute(agente_id=None, **kwargs):
    return "Has construido una estructura."
""",
            experiencia_ganada={"ingenieria": 0.5, "social": 0.1},
            efecto_necesidades={"alimento": -0.5, "social": 0.1},
        )

        self.base_skills["cazar"] = Skill(
            name="cazar",
            description="Caza animales para obtener alimentos.",
            code="""
def execute(agente_id=None, **kwargs):
    return "Has cazado prey."
""",
            experiencia_ganada={"combate": 0.4, "exploracion": 0.2},
            efecto_necesidades={"alimento": 0.6, "salud": -0.1},
        )

        # Nueva skill: REFLEXIONAR
        self.base_skills["reflexionar"] = Skill(
            name="reflexionar",
            description="Reflexiona sobre un tema para evolucionar el Alma, aumentando el Nivel de Conciencia y la Capacidad de Reflexión.",
            code="""
def execute(tema=None, profundidad="media", agente_id=None, **kwargs):
    # Esta skill es virtual: no ejecuta código real, su lógica está en el motor
    if not tema:
        tema = "la vida y mi propósito"
    return {"status": "success", "tema": tema, "profundidad": profundidad, "mensaje": f"He reflexionado sobre '{tema}'."}
""",
            experiencia_ganada={"conocimiento": 0.6, "social": 0.2},
            efecto_necesidades={"descanso": 0.5, "social": 0.1},
        )

        # Nueva skill: COMPARTIR_CONOCIMIENTO (similar a SOCIALIZAR pero con foco en conocimiento)
        self.base_skills["compartir_conocimiento"] = Skill(
            name="compartir_conocimiento",
            description="Comparte un conocimiento o aprendizage específico con otro agente.",
            code="""
def execute(conocimiento=None, destinatario_id=None, agente_id=None, **kwargs):
    if not conocimiento or not destinatario_id:
        return "Debes proporcionar conocimiento específico y un destinatario."
    return f"He compartido mi conocimiento sobre '{conocimiento}' con {destinatario_id}."
""",
            experiencia_ganada={"social": 0.4, "conocimiento": 0.2},
            efecto_necesidades={"social": 0.3},
        )

    def ejecutar_skill(self, skill_name, argumentos, agente_id=None, agent_skills=None):
        self._log(
            f"🛠️ [SKILL] Agente {agente_id} ejecutando skill: {skill_name}", "skill"
        )

        skill = self.base_skills.get(skill_name)
        if not skill and agent_skills:
            skill = agent_skills.get(skill_name)
            if isinstance(skill, dict):
                skill = Skill.from_dict(skill)

        if not skill:
            return {"error": f"Error: Skill '{skill_name}' no encontrada."}

        # Definir el manejador de timeout
        def timeout_handler(signum, frame):
            raise TimeoutError(
                f"La skill '{skill_name}' excedió el tiempo límite de ejecución."
            )

        try:
            # 1. Validación estática básica (anti-bucles infinitos simples)
            if "while True" in skill.code or "while 1" in skill.code:
                return {
                    "error": f"Error: Código de skill '{skill_name}' rechazado (posible bucle infinito)."
                }

            import threading
            is_main_thread = threading.current_thread() is threading.main_thread()

            # 2. Configurar timeout (1 segundo) solo en hilo principal
            if is_main_thread:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(1)

            # 3. Compilación restringida
            try:
                bytecode = compile_restricted(skill.code, "<string>", "exec")
            except Exception as e:
                if is_main_thread:
                    signal.alarm(0)
                return {
                    "error": f"Error de compilación en skill '{skill_name}': {str(e)}"
                }

            # 4. Entorno de ejecución seguro
            safe_globals = safe_builtins.copy()
            # Añadir funciones adicionales seguras si es necesario
            from math import sqrt, sin, cos, tan, log, exp

            safe_globals.update(
                {
                    "math": __import__("math"),
                    "sqrt": sqrt,
                    "sin": sin,
                    "cos": cos,
                    "tan": tan,
                    "log": log,
                    "exp": exp,
                    "min": min,
                    "max": max,
                    "sum": sum,
                    "len": len,
                    "list": list,
                    "dict": dict,
                    "set": set,
                    "range": range,
                }
            )

            # Contexto para la ejecución
            exec_globals = {"__builtins__": safe_globals}
            exec_locals = {}

            # Ejecutar el código para definir funciones
            exec(bytecode, exec_globals, exec_locals)

            # Buscar la función 'execute'
            if "execute" in exec_locals:
                resultado = exec_locals["execute"](agente_id=agente_id, **argumentos)
                if is_main_thread:
                    signal.alarm(0)  # Cancelar alarma
                self._log(
                    f"✅ [SKILL] Skill '{skill_name}' ejecutada con éxito.", "skill"
                )

                # Devolver resultado + efectos de experiencia y necesidades
                return {
                    "resultado": resultado,
                    "experiencia_ganada": skill.experiencia_ganada,
                    "efecto_necesidades": skill.efecto_necesidades,
                    "skill_data": skill.to_dict()
                    if hasattr(skill, "to_dict")
                    else None,
                }
            else:
                if is_main_thread:
                    signal.alarm(0)
                return {
                    "error": f"Error: La skill '{skill_name}' no define una función 'execute' en su espacio local."
                }

        except TimeoutError as te:
            self._log(f"❌ [SKILL] Timeout en '{skill_name}': {str(te)}", "skill")
            return {"error": str(te)}
        except Exception as e:
            if 'is_main_thread' in locals() and is_main_thread:
                try:
                    signal.alarm(0)
                except:
                    pass
            self._log(f"❌ [SKILL] Error en skill '{skill_name}': {str(e)}", "skill")
            return {"error": f"Error al ejecutar skill '{skill_name}': {str(e)}"}


# Instancia global (similar a herramientas)
skill_manager = SkillManager()
