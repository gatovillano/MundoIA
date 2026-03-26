import logging
import signal
from typing import Dict, Any, Optional, List
from RestrictedPython import compile_restricted, safe_builtins

logger = logging.getLogger(__name__)

class Skill:
    def __init__(self, name: str, description: str, code: str, author_id: Optional[str] = None, version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.code = code
        self.author_id = author_id
        self.version = version

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "author_id": self.author_id,
            "version": self.version
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            description=data["description"],
            code=data["code"],
            author_id=data.get("author_id"),
            version=data.get("version", "1.0.0")
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
"""
        )

        self.base_skills["consultar_mercado"] = Skill(
            name="consultar_mercado",
            description="Devuelve el precio actual de los recursos en MundoCoins.",
            code="""
def execute(agente_id=None, **kwargs):
    import random
    precio = random.uniform(1.5, 5.0)
    return f"El precio actual del recurso es de {precio:.2f} MC por unidad."
"""
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
"""
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
"""
        )

        self.base_skills["obtener_clima"] = Skill(
            name="obtener_clima",
            description="Consulta el clima en una ciudad.",
            code="""
def execute(ciudad="Madrid", agente_id=None, **kwargs):
    return f"El clima en {ciudad} parece despejado y propicio para la actividad de los agentes."
"""
        )

        self.base_skills["crear_habilidad"] = Skill(
            name="crear_habilidad",
            description="Crea una nueva habilidad/tool. Requiere nombre, descripción y código Python con una función execute.",
            code="""
def execute(nombre, descripcion, codigo, agente_id=None, **kwargs):
    # Esta skill es especial, el resultado será procesado por el motor para añadirla al agente
    return {"status": "success", "new_skill": {"name": nombre, "description": descripcion, "code": codigo}}
"""
        )

    def ejecutar_skill(self, skill_name, argumentos, agente_id=None, agent_skills=None):
        self._log(f"🛠️ [SKILL] Agente {agente_id} ejecutando skill: {skill_name}", "skill")
        
        skill = self.base_skills.get(skill_name)
        if not skill and agent_skills:
            skill = agent_skills.get(skill_name)
            if isinstance(skill, dict):
                skill = Skill.from_dict(skill)

        if not skill:
            return f"Error: Skill '{skill_name}' no encontrada."

        # Definir el manejador de timeout
        def timeout_handler(signum, frame):
            raise TimeoutError(f"La skill '{skill_name}' excedió el tiempo límite de ejecución.")

        try:
            # 1. Validación estática básica (anti-bucles infinitos simples)
            if "while True" in skill.code or "while 1" in skill.code:
                return f"Error: Código de skill '{skill_name}' rechazado (posible bucle infinito)."

            # 2. Configurar timeout (1 segundo)
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(1)

            # 3. Compilación restringida
            try:
                bytecode = compile_restricted(skill.code, '<string>', 'exec')
            except Exception as e:
                signal.alarm(0)
                return f"Error de compilación en skill '{skill_name}': {str(e)}"

            # 4. Entorno de ejecución seguro
            safe_globals = safe_builtins.copy()
            # Añadir funciones adicionales seguras si es necesario
            from math import sqrt, sin, cos, tan, log, exp
            safe_globals.update({
                'math': __import__('math'),
                'sqrt': sqrt, 'sin': sin, 'cos': cos, 'tan': tan, 'log': log, 'exp': exp,
                'min': min, 'max': max, 'sum': sum, 'len': len,
                'list': list, 'dict': dict, 'set': set, 'range': range
            })
            
            # Contexto para la ejecución
            exec_globals = {"__builtins__": safe_globals}
            exec_locals = {}
            
            # Ejecutar el código para definir funciones
            exec(bytecode, exec_globals, exec_locals)
            
            # Buscar la función 'execute'
            if 'execute' in exec_locals:
                resultado = exec_locals['execute'](agente_id=agente_id, **argumentos)
                signal.alarm(0) # Cancelar alarma
                self._log(f"✅ [SKILL] Skill '{skill_name}' ejecutada con éxito.", "skill")
                return resultado
            else:
                signal.alarm(0)
                return f"Error: La skill '{skill_name}' no define una función 'execute' en su espacio local."

        except TimeoutError as te:
            self._log(f"❌ [SKILL] Timeout en '{skill_name}': {str(te)}", "skill")
            return str(te)
        except Exception as e:
            signal.alarm(0)
            self._log(f"❌ [SKILL] Error en skill '{skill_name}': {str(e)}", "skill")
            return f"Error al ejecutar skill '{skill_name}': {str(e)}"
        finally:
            signal.alarm(0)

# Instancia global (similar a herramientas)
skill_manager = SkillManager()
