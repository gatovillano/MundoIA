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
            description="Realiza una búsqueda general en la web usando la API de Tavily.",
            code="""
def execute(query, agente_id=None, **kwargs):
    # Registrar la query para que llegue al frontend (Terminal de Eventos)
    try:
        log(f"🔍 [WEB SEARCH] Agente {agente_id} busca: '{query}'", "herramienta")
    except Exception:
        pass
    from tavily import TavilyClient
    from agents.cerebro_llm import cerebro_llm
    tavily_key = cerebro_llm.tavily_api_key
    if not tavily_key:
        return "No tengo configurada la llave de búsqueda web (Tavily)."
    
    try:
        tavily = TavilyClient(api_key=tavily_key)
        response = tavily.search(query=query, search_depth="basic", max_results=5)
        
        results = response.get("results", [])
        if not results:
            return "No se encontraron resultados relevantes en la web."
        
        info = "Resultados de búsqueda web (Tavily): "
        for r in results:
            info += f"- {r['title']} ({r['url']}): {r['content']} "
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

        self.base_skills["ejecutar_codigo"] = Skill(
            name="ejecutar_codigo",
            description="Ejecuta código Python en el sandbox. Úsalo para cálculos, automatización o probar lógica.",
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
            "sorted": sorted, "type": type, "isinstance": isinstance, "zip": zip,
            "enumerate": enumerate,
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
            result = result[:1000] + "
... [Resultado truncado]"
        
        return result if result else "Código ejecutado sin salida."
    except Exception as e:
        if 'sys' in locals() and 'old_stdout' in locals():
            sys.stdout = old_stdout
        return f"Error de ejecución: {str(e)}"
""",
            experiencia_ganada={"ingenieria": 0.8},
            efecto_necesidades={"alimento": -0.5, "entretenimiento": 0.3},
        )

        self.base_skills["crear_app"] = Skill(
            name="crear_app",
            description="Crea un script de Python persistente para el agente. Requiere 'nombre' y 'codigo'.",
            code="""
def execute(nombre, codigo, agente_id=None, **kwargs):
    import os
    from datetime import datetime
    apps_dir = os.path.join("apps", str(agente_id))
    os.makedirs(apps_dir, exist_ok=True)
    file_path = os.path.join(apps_dir, f"{nombre}.py")
    with open(file_path, "w") as f:
        f.write(codigo)
    
    return {
        "status": "success",
        "app": {
            "name": nombre,
            "code": codigo,
            "file_path": file_path,
            "created_at": datetime.now().isoformat()
        }
    }
""",
            experiencia_ganada={"ingenieria": 1.2},
            efecto_necesidades={"alimento": -0.8},
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

        self.base_skills["declarar_simpatia"] = Skill(
            name="declarar_simpatia",
            description="Se declara simpatizante de un grupo para poder entrar en su territorio. Requiere 'grupo_id' o 'nombre'.",
            code="""
def execute(grupo_id=None, nombre=None, agente_id=None, **kwargs):
    # Esta skill es procesada por el motor físico (Agente.ejecutar_accion_final)
    # pero aquí devolvemos un mensaje de confirmación para el cerebro LLM.
    if not grupo_id and not nombre:
        return "Error: Debes especificar el 'grupo_id' o el 'nombre' del grupo."
    return {"status": "success", "grupo_id": grupo_id, "nombre": nombre, "mensaje": f"Procesando declaración de simpatía..."}
""",
            experiencia_ganada={"social": 0.5},
            efecto_necesidades={"social": 0.2},
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

            # 3. Preparar entorno de ejecución potente
            import os
            import sys
            import json
            import requests
            from io import StringIO
            
            # Directorios del agente
            apps_dir = os.path.join("apps", str(agente_id))
            os.makedirs(apps_dir, exist_ok=True)
            sandbox_dir = os.path.join("sandbox", str(agente_id))
            os.makedirs(sandbox_dir, exist_ok=True)

            # Entorno de ejecución con acceso a librerías
            # Exponer `log` para que los skills puedan enviar mensajes al sistema de logs
            def _skill_log(mensaje, categoria="skill"):
                try:
                    # Preferir pasar agent_id estructurado si hay un callback configurado
                    if getattr(self, 'log_callback', None):
                        try:
                            # Intentar llamar con el parámetro agente_id al final
                            self.log_callback(mensaje, categoria, None, None, None, None, agente_id)
                            return
                        except TypeError:
                            # Fallback si la callback no acepta ese orden
                            pass
                    # Último recurso: usar _log que pasa por log_callback sin agent_id
                    self._log(mensaje, categoria)
                except Exception:
                    pass

            exec_globals = {
                "os": os, "sys": sys, "json": json, "requests": requests,
                "agente_id": agente_id, "apps_dir": apps_dir, "sandbox_dir": sandbox_dir,
                "print": print, "len": len, "range": range, "list": list, "dict": dict,
                "set": set, "open": open,
                "math": __import__("math"),
                "requests": requests,
                "log": _skill_log,
            }
            exec_locals = {}

            # 4. Ejecutar el código para definir funciones
            exec(skill.code, exec_globals, exec_locals)

            # Buscar la función 'execute'
            if "execute" in exec_locals or "execute" in exec_globals:
                execute_func = exec_locals.get("execute") or exec_globals.get("execute")
                
                # Capturar stdout
                old_stdout = sys.stdout
                redirected_output = sys.stdout = StringIO()
                
                resultado = execute_func(agente_id=agente_id, **argumentos)
                
                sys.stdout = old_stdout
                std_output = redirected_output.getvalue()
                
                if is_main_thread:
                    signal.alarm(0)  # Cancelar alarma
                
                self._log(
                    f"✅ [SKILL] Skill '{skill_name}' ejecutada con éxito.", "skill"
                )

                # Devolver resultado completo (si es dict, lo pasamos tal cual, añadiendo el stdout)
                if isinstance(resultado, dict):
                    final_res = resultado
                    if std_output:
                        final_res["_stdout"] = std_output
                else:
                    final_res = f"{resultado}\n\n[Salida estándar]:\n{std_output}" if std_output else resultado

                return {
                    "resultado": final_res,
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
