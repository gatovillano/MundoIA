"""
Skill Factory para MundoIA - Sistema de Skills Evolutivas
"""

import os
import json
import logging
import importlib.util
from typing import Dict, Any, Optional, List, Callable
from RestrictedPython import compile_restricted, safe_builtins
import signal
import time

logger = logging.getLogger(__name__)


class SkillContext:
    """Contexto de ejecución para skills evolutivas"""

    def __init__(self, agente, mundo, skill_manager):
        self.agente = agente
        self.mundo = mundo
        self.skill_manager = skill_manager
        self.resultados = {}
        self.logs = []

    def log(self, mensaje):
        """Registra actividad del skill"""
        self.logs.append(f"[{time.time()}] {mensaje}")
        logger.info(f"SKILL_CONTEXT {self.agente.unique_id}: {mensaje}")

    def get_agente_data(self):
        """Obtiene datos del agente ejecutor"""
        return {
            'id': self.agente.unique_id,
            'x': self.agente.x,
            'y': self.agente.y,
            'salud': getattr(self.agente, 'salud', 50),
            'energia': getattr(self.agente, 'energia', 50),
            'recursos': getattr(self.agente, 'recursos', 0),
            'dinero': getattr(self.agente, 'dinero', 0),
            'experiencia': getattr(self.agente, 'experiencia', {}),
            'necesidades': getattr(self.agente, 'necesidades', {}),
            'inventario': getattr(self.agente, 'inventario', []),
            'habilidades': getattr(self.agente, 'habilidades', []),
        }

    def get_mundo_data(self):
        """Obtiene datos del mundo"""
        return {
            'turno': getattr(self.mundo, 'step', 0),
            'clima': getattr(self.mundo, 'weather', 'despejado'),
            'agentes_count': len(getattr(self.mundo, 'agentes', [])),
            'grupos_count': len(getattr(self.mundo, 'grupos_dinamicos', {})),
        }

    def get_agentes_cercanos(self, radio=5):
        """Obtiene agentes cercanos"""
        agentes_cercanos = []
        for a in self.mundo.agentes:
            if a.unique_id != self.agente.unique_id:
                distancia = ((a.x - self.agente.x)**2 + (a.y - self.agente.y)**2)**0.5
                if distancia <= radio:
                    agentes_cercanos.append({
                        'id': a.unique_id,
                        'x': a.x,
                        'y': a.y,
                        'distancia': round(distancia, 1),
                        'salud': getattr(a, 'salud', 50),
                        'recursos': getattr(a, 'recursos', 0),
                    })
        return agentes_cercanos


class EvolutiveSkill:
    """Skill avanzado del sistema de skills evolutivas con capacidades extendidas"""

    def __init__(self, name: str, description: str, code: str, metadata: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.code = code
        self.metadata = metadata or {}

        # Features del sistema de skills evolutivas
        self.capabilities = self.metadata.get('capabilities', [])
        self.requirements = self.metadata.get('requirements', {})
        self.effects = self.metadata.get('effects', {})
        self.triggers = self.metadata.get('triggers', [])
        self.dependencies = self.metadata.get('dependencies', [])

        # Estado de compilación
        self.compiled_code = None
        self.is_compiled = False
        self.compile_errors = []

    def compile(self):
        """Compila el código de forma segura"""
        try:
            # Compilación con RestrictedPython
            self.compiled_code = compile_restricted(self.code, f'<skill_{self.name}>', 'exec')
            self.is_compiled = True
            return True
        except Exception as e:
            self.compile_errors.append(str(e))
            logger.error(f"Error compilando skill {self.name}: {e}")
            return False

    def execute(self, context: SkillContext, **kwargs):
        """Ejecuta el skill en contexto seguro"""
        if not self.is_compiled and not self.compile():
            return {"error": f"Skill no compilado: {self.compile_errors}"}

        try:
            # Crear entorno seguro del sistema de skills evolutivas
            safe_globals = self._create_safe_environment(context)

            # Timeout para ejecución
            def timeout_handler(signum, frame):
                raise TimeoutError("Skill execution timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)  # 5 segundos timeout

            try:
                # Ejecutar
                exec_globals = {"__builtins__": safe_globals}
                exec(self.compiled_code, exec_globals, {})

                # Obtener resultado
                result = exec_globals.get('result', 'Skill ejecutado sin resultado explícito')

                signal.alarm(0)  # Cancelar timeout
                return {"success": True, "result": result, "logs": context.logs}

            except TimeoutError:
                signal.alarm(0)
                return {"error": "Skill execution timeout"}
            except Exception as e:
                signal.alarm(0)
                return {"error": f"Execution error: {str(e)}"}

        except Exception as e:
            return {"error": f"Setup error: {str(e)}"}

    def _create_safe_environment(self, context: SkillContext):
        """Crea entorno de ejecución seguro con APIs del juego"""
        safe_globals = safe_builtins.copy()

        # Funciones matemáticas básicas
        safe_globals.update({
            "abs": abs, "min": min, "max": max, "sum": sum, "round": round, "len": len,
            "list": list, "dict": dict, "set": set, "range": range, "enumerate": enumerate,
            "int": int, "float": float, "str": str, "bool": bool, "any": any, "all": all,
            "sorted": sorted, "type": type, "isinstance": isinstance, "zip": zip,
        })

        # APIs del juego (solo lectura)
        safe_globals.update({
            "get_agente_data": lambda: context.get_agente_data(),
            "get_mundo_data": lambda: context.get_mundo_data(),
            "get_agentes_cercanos": lambda radio=5: context.get_agentes_cercanos(radio),
            "log": context.log,
        })

        # Variables útiles
        safe_globals.update({
            "agente_id": context.agente.unique_id,
            "mundo_turno": getattr(context.mundo, 'step', 0),
            "random": __import__('random'),
            "math": __import__('math'),
            "json": __import__('json'),
            "time": __import__('time'),
        })

        return safe_globals

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'metadata': self.metadata,
            'is_compiled': self.is_compiled,
            'compile_errors': self.compile_errors,
        }


class SkillFactory:
    """Factory para crear skills dinámicamente"""

    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
        self.templates = self._load_templates()

    def _load_templates(self):
        """Carga templates de skills predefinidos"""
        return {
            "data_analyzer": {
                "description": "Analiza datos del mundo y agentes",
                "capabilities": ["analysis", "statistics"],
                "template": """
def execute(**kwargs):
    agente_data = get_agente_data()
    mundo_data = get_mundo_data()
    agentes_cercanos = get_agentes_cercanos()

    # Análisis personalizado aquí
    analisis = {
        "mi_salud": agente_data.get('salud', 0),
        "agentes_cercanos": len(agentes_cercanos),
        "turno_mundo": mundo_data.get('turno', 0),
    }

    log(f"Análisis completado: {analisis}")
    result = f"Análisis: {json.dumps(analisis)}"
    return result
"""
            },

            "resource_optimizer": {
                "description": "Optimiza uso de recursos basado en análisis",
                "capabilities": ["optimization", "economics"],
                "template": """
def execute(**kwargs):
    agente_data = get_agente_data()
    mundo_data = get_mundo_data()

    recursos = agente_data.get('recursos', 0)
    dinero = agente_data.get('dinero', 0)
    necesidades = agente_data.get('necesidades', {})

    # Lógica de optimización
    if recursos > 100 and necesidades.get('alimento', 0) > 0.7:
        decision = "invertir en comida"
    elif dinero > 50 and necesidades.get('social', 0) > 0.6:
        decision = "invertir en relaciones sociales"
    else:
        decision = "mantener recursos actuales"

    log(f"Optimización decidida: {decision}")
    result = f"Optimización: {decision}"
    return result
"""
            },

            "social_analyzer": {
                "description": "Analiza dinámicas sociales",
                "capabilities": ["social", "analysis"],
                "template": """
def execute(**kwargs):
    agentes_cercanos = get_agentes_cercanos()
    agente_data = get_agente_data()

    # Análisis social
    relaciones = []
    for agente in agentes_cercanos:
        relacion = {
            "id": agente['id'],
            "distancia": agente['distancia'],
            "salud_relativa": agente['salud'] - agente_data.get('salud', 50)
        }
        relaciones.append(relacion)

    analisis_social = {
        "relaciones_cercanas": len(relaciones),
        "promedio_distancia": sum(r['distancia'] for r in relaciones) / len(relaciones) if relaciones else 0,
        "estado_social": "conectado" if len(relaciones) > 2 else "aislado"
    }

    log(f"Análisis social: {analisis_social}")
    result = f"Análisis social: {json.dumps(analisis_social)}"
    return result
"""
            }
        }

    def create_skill_from_template(self, template_name: str, customizations: Dict[str, Any] = None):
        """Crea un skill desde un template"""
        if template_name not in self.templates:
            raise ValueError(f"Template {template_name} no encontrado")

        template = self.templates[template_name]
        customizations = customizations or {}

        # Aplicar customizaciones
        name = customizations.get('name', f"{template_name}_{int(time.time())}")
        description = customizations.get('description', template['description'])
        code = customizations.get('code', template['template'])

        # Metadata
        metadata = {
            'capabilities': template['capabilities'],
            'template': template_name,
            'created_by': customizations.get('author', 'factory'),
            'customizations': customizations,
        }

        skill = EvolutiveSkill(name, description, code, metadata)
        return skill

    def create_skill_from_code(self, name: str, description: str, code: str, author: str = "factory"):
        """Crea un skill desde código personalizado"""
        metadata = {
            'capabilities': ['custom'],
            'created_by': author,
            'creation_time': time.time(),
        }

        skill = EvolutiveSkill(name, description, code, metadata)
        return skill

    def validate_skill_code(self, code: str):
        """Valida que el código sea seguro"""
        try:
            compile_restricted(code, '<validation>', 'exec')
            return True, None
        except Exception as e:
            return False, str(e)