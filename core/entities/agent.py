import random
import math
import logging
import time
import os
import json
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING

from core.utils import synchronized, logger, Json
from core.world_system import TerrainType
from core.entities.faction import Civilizacion
from systems.memoria import MemoriaGrafica
from agents.cerebro_langgraph import CerebroAvanzado
from agents.alma import generar_alma_inicial, Arquetipo
from agents.identity_system import generar_identidad_inicial
from agents.personality import generar_personalidad_neutral, aplicar_deriva_personalidad
from agents.bdi_components import (
    SistemaCreencias,
    SistemaDeseos,
    SistemaIntenciones,
    TipoDeseo,
    TipoAccion,
)
from core.action_validator import validar_accion

if TYPE_CHECKING:
    from core.modelo import ModeloRelacional

class Agente:
    """
    Entidad central de la simulación MundoIA. 
    Representa un ciudadano autónomo con profundidad psicológica, social y cognitiva.
    """
    
    def __init__(
        self,
        unique_id,
        modelo,
        recursos=100,
        necesidades=None,
        personalidad=None,
        civ_id=None,
        x=None,
        y=None,
    ):
        self.unique_id = unique_id
        self.modelo = modelo
        self.recursos = recursos
        self.civilizacion_id = civ_id
        self.objetivo_movimiento = None

        # Posicionamiento inicial robusto
        if x is not None and y is not None:
            self.x, self.y = x, y
        else:
            self._spawn_en_posicion_valida()

        # Atributos Psicológicos (OCEAN-like)
        # Por defecto partimos neutrales y permitimos deriva posterior.
        default_antagonist = getattr(self.modelo, "antagonist_prob", 0.10)
        if not isinstance(default_antagonist, (int, float)):
            default_antagonist = 0.10
        self.personalidad = (
            personalidad
            if personalidad is not None
            else generar_personalidad_neutral(
                noise_scale=0.03,
                extrema_prob=0.05,
                antagonist_prob=default_antagonist,
            )
        )

        # Estado Vital (10.0 = Óptimo, 0.0 = Crítico)
        self.necesidades = necesidades or {
            "alimento": 10.0,
            "social": 10.0,
            "seguridad": 10.0,
            "descanso": 10.0,
            "entretenimiento": 10.0,
            "salud": 10.0,
        }

        self.necesidades_intelectuales = {
            "curiosidad": random.uniform(6, 9),
            "expresion": random.uniform(6, 9),
            "debate": random.uniform(5, 8),
            "aprendizaje": random.uniform(6, 9),
        }

        # Capital Social y Redes Sociales (OASIS Integration)
        self.capital_social = 10.0
        self.seguidores = 0
        self.siguiendo = 0
        self.posts_publicados = 0
        self.comentarios_realizados = 0
        self.likes_recibidos = 0
        self.likes_dados = 0
        self.debates_ganados = 0
        self.debates_perdidos = 0
        self.intereses = []
        self.opiniones_fuertes = {}

        # Sistema de Habilidades
        self.skill_factor = random.uniform(0.1, 0.5)
        self.experiencia = {
            "medicina": 0, "comercio": 0, "combate": 0, "exploracion": 0,
            "social": 0, "ingenieria": 0, "agricultura": 0, "investigacion": 0, "ciencia": 0
        }
        self.skills = {}

        # Integración con SkillManager (FASE 1.2.1)
        # Referencia global al skill_manager para ejecutar skills
        try:
            from core.skills_manager import skill_manager
            self.skill_manager = skill_manager
            # Cargar TODAS las skills base en el diccionario personal del agente
            for skill_name, skill_obj in skill_manager.base_skills.items():
                if skill_name not in self.skills:
                    self.skills[skill_name] = skill_obj.to_dict()
        except Exception:
            # Evitar fallos por import circular o en entornos de prueba
            self.skill_manager = None
            pass

        # Subsistemas de Inteligencia y Memoria
        self.memoria = MemoriaGrafica(self.unique_id)
        self.cerebro = CerebroAvanzado(self.unique_id)
        self.creencias = SistemaCreencias()
        self.deseos = SistemaDeseos()
        # Ajustar pesos de deseos según personalidad para introducir diversidad conflictiva
        try:
            p = self.personalidad
            # Asegurar keys en pesos
            for t in TipoDeseo:
                if t not in self.deseos.pesos:
                    self.deseos.pesos[t] = 1.0
            # Potenciar deseos materiales y de estatus para agentes ambiciosos
            self.deseos.pesos[TipoDeseo.RECURSOS] = self.deseos.pesos.get(TipoDeseo.RECURSOS, 1.0) * (1.0 + (p.get('ambicion', 0.5) - 0.5) * 1.6 + (p.get('competitividad', 0.5) - 0.5) * 0.8)
            self.deseos.pesos[TipoDeseo.ESTATUS] = self.deseos.pesos.get(TipoDeseo.ESTATUS, 1.0) * (1.0 + (p.get('ambicion', 0.5) - 0.5) * 1.2 + (p.get('carisma', 0.5) - 0.5) * 1.0)
            self.deseos.pesos[TipoDeseo.PODER_POLITICO] = self.deseos.pesos.get(TipoDeseo.PODER_POLITICO, 1.0) * (1.0 + (p.get('ambicion', 0.5) - 0.5) * 2.0 + (p.get('manipulacion', 0.5) - 0.5) * 1.5)
            # Reducir armonía en agentes manipuladores/agresivos para fomentar conflicto
            factor = max(0.1, 1.0 - (p.get('hostilidad', 0.5) - 0.5) * 1.4 - (p.get('manipulacion', 0.5) - 0.5) * 0.8)
            self.deseos.pesos[TipoDeseo.ARMONIA] = self.deseos.pesos.get(TipoDeseo.ARMONIA, 1.0) * factor
        except Exception:
            pass
        self.intenciones = SistemaIntenciones()
        
        # Identidad y Alma
        self.alma = generar_alma_inicial(self.personalidad, 0)
        self.identidad = generar_identidad_inicial(self.alma.arquetipo.value, 0)
        if self.alma.nombre_propio:
            self.identidad.nombre = self.alma.nombre_propio

        # Economía y Estatus
        self.grupo_id = civ_id
        self.rol = "Ciudadano"
        self.dinero = 100.0
        self.rango = 1.0
        self.reputacion = 1.0
        self.votos_recibidos = 0
        self.profesion = None
        self.conocimientos = {}
        self.planes = []
        self.eventos_recientes = []
        self.inventario = {
            "comida": int(self.recursos), "madera": 0, "piedra": 0,
            "hierro": 0, "medicina": 0, "ocio": 0
        }
        self.alianzas = []
        self.tratados = []
        self.hitos = []
        self.historial_etico = []
        self.historial_acciones_bdi = []
        self.esta_vivo = True
        self.apps = {}
        self.acciones_control_usuario = []
        self.pensamiento_actual = "Iniciando existencia..."
        self.ultimo_mensaje_recibido = None
        self.mensaje_arquitecto = None
        self.gasto_turno = 0.0
        self.inversiones = []
        self.decision_cacheada = None
        self.descansar_skip_next = False
        self.descansando = False
        
        # engagement_social: tracking de retroalimentación positiva en redes sociales
        self.ultimo_engagement_positivo = 0  # Turno del último engagement positivo
        self.fomento_engagement = True  # Activa/desactiva mejora de engagement
        self.posts_guardados = []  # Posts que el agente ha guardado o le llamaron la atención

        # === MUNDOVIVO: Sistemas de Persistencia y Ritmo ===
        try:
            from systems.memoria_persistente import MemoriaPersistente
            from systems.heartbeat import RitmoVital
            
            self.memoria_persistente = MemoriaPersistente(
                agente_id=self.unique_id,
                user_id=getattr(self.modelo, "user_id", "default")
            )
            self.heartbeat_mundo = RitmoVital(
                agente_id=self.unique_id, 
                personalidad=self.personalidad
            )
        except ImportError:
            # Fallback por si los módulos no están disponibles en algún entorno
            self.memoria_persistente = None
            self.heartbeat_mundo = None

    def _spawn_en_posicion_valida(self):
        """Busca una posición libre en el mapa."""
        mapa_size = getattr(self.modelo, "mapa_size", 20)
        pos_encontrada = False
        for _ in range(100):
            nx = random.randint(0, mapa_size - 1)
            ny = random.randint(0, mapa_size - 1)
            # Evitar colisión con otros agentes si es posible
            if not any(a.x == nx and a.y == ny for a in self.modelo.agentes if hasattr(a, 'x')):
                self.x = nx
                self.y = ny
                pos_encontrada = True
                break
        if not pos_encontrada:
            self.x = random.randint(0, mapa_size - 1)
            self.y = random.randint(0, mapa_size - 1)

    @property
    def is_possessed(self):
        return getattr(self.modelo, "agente_poseido_id", None) == self.unique_id

    @property
    def display_name(self):
        if hasattr(self, "identidad") and self.identidad:
            nombre = getattr(self.identidad, "nombre", None)
            emoji = getattr(self.identidad, "emoji", "")
            if nombre:
                return f"{emoji} {nombre}".strip()
        return str(self.unique_id)

    def calcular_capital_social(self) -> float:
        """
        Calcula el Capital Social del agente basado en múltiples factores.
        Fórmula: ponderación de componentes sociales, engagement y participación.
        """
        # Base: seguidores con bonus por ratio de seguimiento
        ratio_follow = self.siguiendo / max(1, self.seguidores)
        base = self.seguidores * (1 + (1 / (1 + ratio_follow)))

        # Engagement: likes recibidos (peso 0.5)
        engagement = self.likes_recibidos * 0.5

        # Contenido: posts publicados (peso 2)
        contenido = self.posts_publicados * 2

        # Participación en debates (ganados - perdidos)
        debate = (self.debates_ganados * 10) - (self.debates_perdidos * 3)

        # Comentarios realizados (engagement activo)
        comentarios = self.comentarios_realizados * 1

        # Votos recibidos (participación política)
        politico = self.votos_recibidos * 0.3

        total = base + engagement + contenido + max(0, debate) + comentarios + politico

        # Normalizar a 0-100
        self.capital_social = min(100, max(0, total / 10))
        return self.capital_social

    def actualizar_intereses_por_post(self, post, engagement_level=1.0):
        """
        Refuerza los temas del post como intereses del agente.
        engagement_level: 1.0 (leyó), 2.0 (like), 3.0 (comentó), 5.0 (creó)
        """
        if not hasattr(post, 'temas') or not post.temas:
            return
        
        # Añadir/refuerzo intereses
        for tema in post.temas:
            if tema in self.intereses:
                # Ya es interés, reforzar (aumentar peso mental)
                if tema in self.opiniones_fuertes:
                    self.opiniones_fuertes[tema] = min(5.0, 
                        self.opiniones_fuertes[tema] + 0.1 * engagement_level)
                else:
                    self.opiniones_fuertes[tema] = 1.0
            else:
                # Nuevo interés potencial
                if random.random() < 0.3 * engagement_level:  # 30% chance de adoptar
                    self.intereses.append(tema)
                    self.opiniones_fuertes[tema] = 1.0
                    # Mantener máximo 5 intereses
                    if len(self.intereses) > 5:
                        # Eliminar el menos usado (mínimo opiniones_fuertes)
                        weakest = min(self.intereses, 
                                     key=lambda t: self.opiniones_fuertes.get(t, 0))
                        self.intereses.remove(weakest)
                        self.opiniones_fuertes.pop(weakest, None)
        
        # Decaimiento natural: reducir intensidad de intereses no usados
        for tema in list(self.opiniones_fuertes.keys()):
            if tema not in self.intereses:
                self.opiniones_fuertes[tema] *= 0.9
            if self.opiniones_fuertes[tema] < 0.1:
                self.opiniones_fuertes.pop(tema, None)

    def _registrar_memoria_episodica(self, descripcion: str, importancia: float = 0.5, emociones: List[str] = None, agentes: List[str] = None):
        """Registra una memoria episódica en el sistema de persistencia si está disponible."""
        if hasattr(self, "memoria_persistente") and self.memoria_persistente:
            try:
                self.memoria_persistente.guardar_episodica(
                    descripcion=descripcion,
                    turno=getattr(self.modelo, "paso_actual", 0),
                    importancia=importancia,
                    emociones=emociones or [],
                    agentes=agentes or []
                )
            except Exception as e:
                logger.error(f"Error registrando memoria episódica para {self.unique_id}: {e}")

    def get_nivel_influencia(self) -> str:
        """Retorna el nivel de influencia basado en el capital social."""
        cs = self.capital_social
        if cs >= 80:
            return "Legendario"
        elif cs >= 50:
            return "Respetado"
        elif cs >= 25:
            return "Notorio"
        else:
            return "Desconocido"

    def necesidad_intelectual_critica(self) -> bool:
        """Retorna True si alguna necesidad intelectual está en nivel crítico."""
        for v in self.necesidades_intelectuales.values():
            if v < 4:
                return True
        return False

    def necesidad_social_critica(self) -> bool:
        """Retorna True si la necesidad social está en nivel crítico."""
        return self.necesidades.get("social", 5) < 4

    def _evaluar_tipo_accion_necesidades(self) -> str:
        """
        Evalúa las necesidades del agente y retorna el tipo de acción prioritaria.
        Retorna: "SURVIVAL", "SOCIAL_REQUIRED", "INTELLECTUAL", "FREE_CHOICE"
        """
        # Supervivencia crítica
        if (
            self.necesidades.get("alimento", 5) < 3
            or self.necesidades.get("salud", 5) < 3
        ):
            return "SURVIVAL"

        # Necesidad social crítica - debe interactuar
        if self.necesidades.get("social", 5) < 4:
            return "SOCIAL_REQUIRED"

        # Necesidad intelectual crítica - debe expresar/aprender
        if self.necesidad_intelectual_critica():
            return "INTELLECTUAL"

        # Libre elección
        return "FREE_CHOICE"

    def necesidad_fisica_critica(self) -> bool:
        """Retorna True si alguna necesidad física está en nivel crítico."""
        return (
            self.necesidades.get("alimento", 5) < 4
            or self.necesidades.get("salud", 5) < 4
            or self.necesidades.get("descanso", 5) < 4
        )

    def __getstate__(self):
        """
        Define qué atributos del Agente se serializan.
        Excluye 'modelo' para evitar referencias circulares y 'cerebro' ya que es recreable.
        Serializa los datos de 'memoria' en lugar del objeto completo.
        """
        state = self.__dict__.copy()
        del state["modelo"]
        del state["cerebro"]
        state["memoria_data"] = self.memoria.exportar_datos()
        return state

    def __setstate__(self, state):
        """
        Define cómo se deserializa el Agente.
        Reconstruye 'memoria' y 'cerebro'. 'modelo' se reasigna externamente.
        """
        self.unique_id = state[
            "unique_id"
        ]  # Asegurar que unique_id se establece primero
        self.__dict__.update(state)
        self.memoria = MemoriaGrafica(self.unique_id)
        if "memoria_data" in state:
            self.memoria.cargar_datos(state["memoria_data"])
        self.cerebro = CerebroAvanzado(self.unique_id)
        # 'modelo' se reasigna después de la carga completa de todos los agentes
        self.modelo = (
            None  # Placeholder, será reasignado por ModeloRelacional.cargar_estado()
        )

    def registrar_evento(self, descripcion: str):
        """Registra un evento significativo en el diario del agente."""
        paso = getattr(self.modelo, "paso_actual", 0)
        # Evitar duplicados inmediatos
        if self.eventos_recientes and self.eventos_recientes[-1]["descripcion"] == descripcion:
            return
        
        self.eventos_recientes.append({
            "paso": paso,
            "descripcion": descripcion,
            "timestamp": time.time()
        })
        # Mantener solo los últimos 15 eventos
        if len(self.eventos_recientes) > 15:
            self.eventos_recientes.pop(0)

    def to_dict(self):
        """Convierte el objeto Agente a un diccionario serializable."""
        return {
            "unique_id": self.unique_id,
            "recursos": self.recursos,
            "civilizacion_id": self.civilizacion_id,
            "objetivo_movimiento": self.objetivo_movimiento,
            "x": self.x,
            "y": self.y,
            "necesidades": self.necesidades,
            "personalidad": self.personalidad,
            "memoria_data": self.memoria.exportar_datos(),
            "grupo_id": self.grupo_id,
            "rol": self.rol,
            "ultimo_mensaje_recibido": self.ultimo_mensaje_recibido,
            "dinero": self.dinero,
            "rango": self.rango,
            "conocimientos": self.conocimientos,
            "planes": self.planes,
            "gasto_turno": self.gasto_turno,
            "inversiones": self.inversiones,
            "alianzas": self.alianzas,
            "tratados": self.tratados,
            "eventos_recientes": self.eventos_recientes,
            "inventario": self.inventario,
            "profesion": self.profesion,
            "experiencia": self.experiencia,
            "hitos": self.hitos,
            "reputacion": self.reputacion,
            "votos_recibidos": self.votos_recibidos,
            "historial_etico": self.historial_etico,
            "pensamiento_actual": self.pensamiento_actual,
            "mensaje_arquitecto": self.mensaje_arquitecto,
            "esta_vivo": self.esta_vivo,
            "skills": {
                k: v if isinstance(v, dict) else v.to_dict()
                for k, v in self.skills.items()
            },
            "skill_factor": self.skill_factor,
            "color": self.modelo.civilizaciones[self.grupo_id].color
            if self.grupo_id and self.grupo_id in self.modelo.civilizaciones
            else "#ffffff",
            "beliefs": self.creencias.to_dict(),
            "desires": self.deseos.to_dict(),
            "intentions": self.intenciones.to_dict(),
            "historial_acciones_bdi": self.historial_acciones_bdi,
            # === MUNDOVIVO: Serialización de subsistemas ===
            "identidad": self.identidad.to_dict()
            if hasattr(self, "identidad") and self.identidad
            else None,
            "memoria_persistente_data": self.memoria_persistente.to_dict()
            if hasattr(self, "memoria_persistente") and self.memoria_persistente
            else {},
            "alma": self.alma.to_dict()
            if hasattr(self, "alma") and self.alma
            else None,
            "heartbeat_config": self.heartbeat_mundo.to_dict()
            if hasattr(self, "heartbeat_mundo") and self.heartbeat_mundo
            else None,
            "cronicas_publicadas": [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in getattr(self, "cronicas_publicadas", [])
            ],
            "apps": getattr(self, "apps", {}),
            # === FIN MUNDOVIVO ===
            # === CAPITAL SOCIAL E INTELECTUAL ===
            "capital_social": getattr(self, "capital_social", 10.0),
            "seguidores": getattr(self, "seguidores", 0),
            "siguiendo": getattr(self, "siguiendo", 0),
            "posts_publicados": getattr(self, "posts_publicados", 0),
            "comentarios_realizados": getattr(self, "comentarios_realizados", 0),
            "likes_recibidos": getattr(self, "likes_recibidos", 0),
            "likes_dados": getattr(self, "likes_dados", 0),
            "debates_ganados": getattr(self, "debates_ganados", 0),
            "debates_perdidos": getattr(self, "debates_perdidos", 0),
            "intereses": getattr(self, "intereses", []),
            "opiniones_fuertes": getattr(self, "opiniones_fuertes", {}),
            "necesidades_intelectuales": getattr(
                self,
                "necesidades_intelectuales",
                {"curiosidad": 6, "expresion": 6, "debate": 5, "aprendizaje": 6},
            ),
            "simpatizante_de": getattr(self, "simpatizante_de", []),
        }

    @classmethod
    def from_dict(cls, data, modelo_instance):
        """Reconstruye un objeto Agente desde un diccionario serializado."""
        agente = cls(
            unique_id=data["unique_id"],
            modelo=modelo_instance,  # Re-establecer la referencia al modelo
            recursos=data.get("recursos", 100),
            necesidades=data.get("necesidades"),
            personalidad=data.get("personalidad"),
            civ_id=data.get("civilizacion_id"),
            x=data.get("x"),
            y=data.get("y"),
        )
        # Actualizar otros atributos
        agente.objetivo_movimiento = data.get("objetivo_movimiento")
        agente.grupo_id = data.get("grupo_id")
        agente.rol = data.get("rol")
        agente.ultimo_mensaje_recibido = data.get("ultimo_mensaje_recibido")
        agente.dinero = data.get("dinero")
        agente.rango = data.get("rango")
        agente.conocimientos = data.get("conocimientos", {})
        agente.planes = data.get("planes", [])
        agente.gasto_turno = data.get("gasto_turno")
        agente.inversiones = data.get("inversiones", [])
        agente.alianzas = data.get("alianzas", [])
        agente.tratados = data.get("tratados", [])
        agente.eventos_recientes = data.get("eventos_recientes", [])
        agente.inventario = data.get("inventario", {})
        agente.profesion = data.get("profesion")
        agente.experiencia = data.get("experiencia", {})
        agente.hitos = data.get("hitos", [])
        agente.reputacion = data.get("reputacion")
        agente.votos_recibidos = data.get("votos_recibidos")
        agente.historial_etico = data.get("historial_etico", [])
        agente.pensamiento_actual = data.get("pensamiento_actual")
        agente.mensaje_arquitecto = data.get("mensaje_arquitecto")
        agente.esta_vivo = data.get("esta_vivo", True)
        agente.skills = data.get("skills", {})
        agente.skill_factor = data.get("skill_factor", 0.3)

        from agents.bdi_components import (
            SistemaCreencias,
            SistemaDeseos,
            SistemaIntenciones,
        )

        # Cargar BDI de forma robusta con claves en español e inglés
        bdi_beliefs = data.get("beliefs") or data.get("creencias")
        if bdi_beliefs and isinstance(bdi_beliefs, dict):
            agente.creencias = SistemaCreencias.from_dict(bdi_beliefs)

        bdi_desires = data.get("desires") or data.get("deseos")
        if bdi_desires and isinstance(bdi_desires, dict):
            agente.deseos = SistemaDeseos.from_dict(bdi_desires)

        bdi_intentions = data.get("intentions") or data.get("intenciones")
        if bdi_intentions and isinstance(bdi_intentions, dict):
            agente.intenciones = SistemaIntenciones.from_dict(bdi_intentions)

        if "historial_acciones_bdi" in data:
            agente.historial_acciones_bdi = data["historial_acciones_bdi"]

        if "memoria_data" in data:
            agente.memoria.cargar_datos(data["memoria_data"])

        # === MUNDOVIVO: Deserialización de subsistemas ===
        nombre_agente = data.get("nombre", str(agente.unique_id))

        if data.get("identidad"):
            from agents.identity_system import generar_identidad_inicial

            agente.identidad = generar_identidad_inicial(nombre_agente, 0)
            agente.identidad.actualizar_desde_dict(data["identidad"])

        if data.get("memoria_persistente_data"):
            from systems.memoria_persistente import MemoriaPersistente

            agente.memoria_persistente = MemoriaPersistente(
                agente_id=agente.unique_id,
                user_id=getattr(modelo_instance, "user_id", "default"),
                data=data["memoria_persistente_data"],
            )
        else:
            from systems.memoria_persistente import MemoriaPersistente

            agente.memoria_persistente = MemoriaPersistente(
                agente_id=agente.unique_id,
                user_id=getattr(modelo_instance, "user_id", "default"),
            )

        alma_data = data.get("alma") or data.get("alma_estado")
        if alma_data:
            from agents.alma import Alma

            agente.alma = Alma.from_dict(alma_data)

        if data.get("heartbeat_config"):
            from systems.heartbeat import RitmoVital

            agente.heartbeat_mundo = RitmoVital.from_dict(
                data["heartbeat_config"], personalidad=agente.personalidad
            )

        agente.cronicas_publicadas = []
        for c_data in data.get("cronicas_publicadas", []):
            if isinstance(c_data, dict):
                from systems.cronicas import Cronica

                agente.cronicas_publicadas.append(Cronica.from_dict(c_data))
            else:
                agente.cronicas_publicadas.append(c_data)
        # === FIN MUNDOVIVO ===

        # === CAPITAL SOCIAL E INTELECTUAL ===
        agente.capital_social = data.get("capital_social", 10.0)
        agente.seguidores = data.get("seguidores", 0)
        agente.siguiendo = data.get("siguiendo", 0)
        agente.posts_publicados = data.get("posts_publicados", 0)
        agente.comentarios_realizados = data.get("comentarios_realizados", 0)
        agente.likes_recibidos = data.get("likes_recibidos", 0)
        agente.likes_dados = data.get("likes_dados", 0)
        agente.debates_ganados = data.get("debates_ganados", 0)
        agente.debates_perdidos = data.get("debates_perdidos", 0)
        agente.intereses = data.get("intereses", [])
        agente.opiniones_fuertes = data.get("opiniones_fuertes", {})
        if "necesidades_intelectuales" in data:
            agente.necesidades_intelectuales = data["necesidades_intelectuales"]
        else:
            agente.necesidades_intelectuales = {
                "curiosidad": random.uniform(6, 9),
                "expresion": random.uniform(6, 9),
                "debate": random.uniform(5, 8),
                "aprendizaje": random.uniform(6, 9),
            }

        agente.simpatizante_de = data.get("simpatizante_de", [])

        return agente

    @synchronized
    def decir(
        self,
        mensaje,
        pensamiento=None,
        privado_para=None,
        para_grupo=False,
        global_broadcast=False,
    ):
        """Imprime un mensaje directo, privado, para el grupo o global."""
        prefijo = f"[{self.unique_id}]"

        # Actualizar pensamiento actual si se proporciona
        if pensamiento:
            self.pensamiento_actual = pensamiento

        # --- EVOLUCIÓN ESPIRITUAL ---
        # Hablar o pensar es una experiencia que hace evolucionar el alma
        if hasattr(self, "alma") and self.alma:
            from agents.alma import ExperienciaClave

            exp = ExperienciaClave(
                descripcion=f"Emitió o procesó un mensaje: {mensaje[:50]}...",
                turno=getattr(self.modelo, "paso_actual", 0),
                intensidad=0.2,  # Intensidad baja pero constante
                tipo="reflexion",  # Un tipo nuevo para crecimiento constante
            )
            self.alma.evolucionar(exp)

        # Determinar el tipo de mensaje y su alcance
        if global_broadcast:
            prefijo = f"📢 {prefijo} (ANUNCIO GLOBAL)"
            privado_para = None  # Los mensajes globales no son privados
        elif para_grupo and self.grupo_id:
            prefijo = f"👥 {prefijo} (Para Facción {self.grupo_id})"
            privado_para = f"GRUPO:{self.grupo_id}"
        elif privado_para:
            prefijo = f"🔒 {prefijo} (Privado para {privado_para})"
        elif self.personalidad["amabilidad"] > 0.7:
            prefijo = f"😇 {prefijo}"
        elif self.personalidad["competitividad"] > 0.7:
            prefijo = f"👿 {prefijo}"
        else:
            prefijo = f"🤖 {prefijo}"

        self.modelo.log(
            f'{prefijo}: "{mensaje}"',
            categoria="dialogo",
            tts_text=mensaje,
            pensamiento=pensamiento,
            privado_para=privado_para,
            agente_id=self.unique_id,
        )

        # --- REGISTRO EN MEMORIA EPISÓDICA ---
        # Guardar en mi propia memoria que he dicho esto
        self.memoria.registrar_mensaje(self.unique_id, mensaje)

        # --- DISTRIBUCIÓN DE MENSAJES ---
        packet = {
            "emisor": self.unique_id,
            "contenido": mensaje,
            "tipo": "GLOBAL"
            if global_broadcast
            else "ASAMBLEA"
            if not privado_para and not para_grupo
            else "DIRECTO",
        }

        # Si es un mensaje global, enviarlo a TODOS los agentes
        if global_broadcast:
            for agent in self.modelo.agentes:
                if agent.unique_id != self.unique_id:
                    agent.ultimo_mensaje_recibido = packet
                    agent.memoria.registrar_mensaje(self.unique_id, mensaje)

        # Si es un mensaje de grupo, enviarlo a los miembros de la facción
        elif para_grupo and self.grupo_id:
            for agent in self.modelo.agentes:
                if (
                    agent.grupo_id == self.grupo_id
                    and agent.unique_id != self.unique_id
                ):
                    agent.ultimo_mensaje_recibido = packet
                    agent.memoria.registrar_mensaje(self.unique_id, mensaje)

        # Si es privado, enviarlo solo al destinatario
        elif privado_para:
            dest_id = privado_para
            dest = next(
                (a for a in self.modelo.agentes if a.unique_id == dest_id), None
            )
            if dest:
                dest.ultimo_mensaje_recibido = packet
                dest.memoria.registrar_mensaje(self.unique_id, mensaje)

        # Si es un mensaje "en voz alta" (asamblea/vecinos), lo oyen los cercanos
        else:
            for agent in self.modelo.agentes:
                if agent.unique_id != self.unique_id:
                    # Distancia de audición (ej. 3 casillas)
                    dist = abs(self.x - agent.x) + abs(self.y - agent.y)
                    if dist <= 3:
                        agent.ultimo_mensaje_recibido = packet
                        agent.memoria.registrar_mensaje(self.unique_id, mensaje)
            return

        # --- SISTEMA DE ASAMBLEA GLOBAL ---
        # Si hay una asamblea activa, los mensajes públicos llegan a TODOS
        active_assemblies = [
            a
            for a in self.modelo.asambleas_globales
            if a.get("estado") in ["DEBATE", "VOTACION"]
        ]
        if active_assemblies and not privado_para and not para_grupo:
            packet["tipo"] = "ASAMBLEA"
            packet["contenido"] = f"[ASAMBLEA] {mensaje}"
            # Broadcast a todos los demás agentes
            for agent in self.modelo.agentes:
                if agent.unique_id != self.unique_id:
                    agent.ultimo_mensaje_recibido = packet

    @synchronized
    def interactuar(self, otro_agente, tipo_interaccion="social", mensaje_enviado=None):
        """Define cómo el agente interactúa con otro. La respuesta del otro agente es asíncrona (en su propio turno)."""

        # El otro agente guarda el mensaje para su fase de pensamiento/respuesta
        if mensaje_enviado:
            otro_agente.ultimo_mensaje_recibido = {
                "emisor": self.unique_id,
                "contenido": mensaje_enviado,
            }

        if tipo_interaccion == "SOCIALIZAR" or tipo_interaccion == "social":
            self.necesidades["social"] = min(
                10.0, self.necesidades["social"] + 3.0
            )  # Socializar satisface una necesidad vital
            self.reputacion = min(
                1.0, self.reputacion + 0.01
            )  # Socializar mejora reputación
            # Ganar experiencia social
            self.ganar_experiencia("social", 1)
            hostilidad_total = self.personalidad.get(
                "hostilidad", 0.5
            ) + otro_agente.personalidad.get("hostilidad", 0.5)
            afinidad_base = 0.2 * (
                self.personalidad["amabilidad"] + otro_agente.personalidad["amabilidad"]
            ) - (0.15 * hostilidad_total)

            if otro_agente.dinero > self.dinero * 1.5:
                afinidad_base -= 0.1 * self.personalidad.get("hostilidad", 0.5)

            self.memoria.registrar_interaccion(
                otro_agente.unique_id,
                "amigo" if afinidad_base > 0 else "conocido",
                afinidad_base,
                otro_agente.recursos,
                otro_agente.grupo_id,
            )
            # También registrar en el otro agente para reciprocidad
            otro_agente.memoria.registrar_interaccion(
                self.unique_id,
                "amigo" if afinidad_base > 0 else "conocido",
                afinidad_base,
                self.recursos,
                self.grupo_id,
            )
            self.modelo.log(
                f"  🤝 [SOCIAL] Agente {self.unique_id} socializa con {otro_agente.unique_id}. Afinidad: {afinidad_base:.2f}",
                categoria="social",
            )

            # === PERSISTENCIA MUNDOVIVO ===
            if hasattr(self, "memoria_persistente") and self.memoria_persistente:
                paso = getattr(self.modelo, "paso_actual", 0)
                tipo_rel = "amigo" if afinidad_base > 0 else "conocido"
                self.memoria_persistente.registrar_interaccion_significativa(
                    otro_agente.unique_id, tipo_rel, paso, 
                    f"Socialización normal. Afinidad: {afinidad_base:.2f}"
                )

        elif tipo_interaccion == "COMPETIR":
            self.ganar_experiencia("combate", 1)
            self.reputacion = max(0.0, self.reputacion - 0.05)

            # El ataque/competencia daña la relación
            self.memoria.registrar_interaccion(
                otro_agente.unique_id,
                "enemigo",
                -0.5,
                otro_agente.recursos,
                otro_agente.grupo_id,
            )
            otro_agente.memoria.registrar_interaccion(
                self.unique_id, "enemigo", -0.5, self.recursos, self.grupo_id
            )

            exito = random.random() * self.rango > random.random() * otro_agente.rango
            if exito:
                robo = 5
                self.recursos += robo
                otro_agente.recursos -= robo

                # Robar items del inventario
                items_probables = [
                    k for k, v in otro_agente.inventario.items() if v > 0
                ]
                if items_probables and random.random() < 0.4:
                    item = random.choice(items_probables)
                    otro_agente.inventario[item] -= 1
                    self.inventario[item] = self.inventario.get(item, 0) + 1
                    self.modelo.log(
                        f"  🏴‍☠️ [ROBO] Agente {self.unique_id} le arrebató {item} a {otro_agente.unique_id}!",
                        categoria="conflict",
                    )

                self.modelo.log(
                    f"  ⚔️ [CONFLICTO] Agente {self.unique_id} robó recursos a {otro_agente.unique_id}.",
                    categoria="conflict",
                )

                # === PERSISTENCIA MUNDOVIVO ===
                if hasattr(self, "memoria_persistente") and self.memoria_persistente:
                    paso = getattr(self.modelo, "paso_actual", 0)
                    self.memoria_persistente.registrar_interaccion_significativa(
                        otro_agente.unique_id, "enemigo", paso, 
                        f"Conflicto violento. Le robé recursos."
                    )
            else:
                self.modelo.log(
                    f"  🛡️ [FALLO] Agente {self.unique_id} intentó robar a {otro_agente.unique_id} pero falló.",
                    categoria="conflict",
                )

        elif tipo_interaccion == "COMERCIAR":
            # Lógica de comercio: si tengo mucho de algo y el otro tiene dinero, vendo
            items_vender = [k for k, v in self.inventario.items() if v > 2]
            if items_vender and otro_agente.dinero >= 10:
                item = random.choice(items_vender)
                precio = random.randint(5, 15)
                self.inventario[item] -= 1
                otro_agente.inventario[item] = otro_agente.inventario.get(item, 0) + 1
                self.dinero += precio
                otro_agente.dinero -= precio
                self.modelo.log(
                    f"  💰 [COMERCIO] Agente {self.unique_id} vendió {item} a {otro_agente.unique_id} por {precio} MC.",
                    categoria="economia",
                )
                self.ganar_experiencia("comercio", 2)

                # === PERSISTENCIA MUNDOVIVO ===
                if hasattr(self, "memoria_persistente") and self.memoria_persistente:
                    paso = getattr(self.modelo, "paso_actual", 0)
                    self.memoria_persistente.registrar_interaccion_significativa(
                        otro_agente.unique_id, "comercio", paso, 
                        f"Le vendí {item} por {precio} MC."
                    )
                self.memoria.registrar_interaccion(
                    otro_agente.unique_id,
                    "amigo",
                    0.3,
                    otro_agente.recursos,
                    otro_agente.grupo_id,
                )
            else:
                self.modelo.log(
                    f"  🤝 [COMERCIO] Agente {self.unique_id} intentó comerciar con {otro_agente.unique_id} pero no hubo acuerdo.",
                    categoria="economia",
                )

        elif tipo_interaccion == "ALIANZA":
            self.formar_alianza(otro_agente)
            self.ganar_experiencia("social", 2)
            self.decir(
                f"¡Hemos sellado una alianza estratégica con {otro_agente.unique_id}!",
                pensamiento="La unión hace la fuerza. Juntos somos imparables.",
            )

        elif tipo_interaccion == "ATACAR" or tipo_interaccion == "atacar":
            self.ganar_experiencia("combate", 2)
            self.reputacion = max(0.0, self.reputacion - 0.2)

            # El ataque siempre destruye la relación
            self.memoria.registrar_interaccion(
                otro_agente.unique_id,
                "enemigo",
                -1.0,
                otro_agente.recursos,
                otro_agente.grupo_id,
            )
            otro_agente.memoria.registrar_interaccion(
                self.unique_id, "enemigo", -1.0, self.recursos, self.grupo_id
            )

            # Cálculo de daño
            daño_base = 2.0 + (self.experiencia["combate"] * 0.5)
            exito = random.random() > 0.3  # 70% éxito

            if exito:
                daño_final = daño_base * random.uniform(1, 2)
                self.modelo.log(
                    f"  ⚔️ [ATAQUE] ¡Agente {self.unique_id} ha ATACADO violentamente a {otro_agente.unique_id} causando {daño_final:.1f} de daño!",
                    categoria="conflict",
                )
                otro_agente.recibir_daño(daño_final, f"ataque de {self.unique_id}")
                self.decir(
                    f"¡Prepárate para la derrota, {otro_agente.unique_id}! No toleraré tu presencia.",
                    pensamiento="Eliminar competencia es necesario para mi supremacía.",
                )
            else:
                counter_daño = 1.0
                self.recibir_daño(
                    counter_daño, f"contraataque de {otro_agente.unique_id}"
                )
                self.modelo.log(
                    f"  🛡️ [FALLO] Agente {self.unique_id} falló su ataque y recibió un golpe de {counter_daño}.",
                    categoria="conflict",
                )

        elif tipo_interaccion == "DECLARAR_GUERRA":
            if self.grupo_id and otro_agente.grupo_id:
                exito, msg = self.modelo.declarar_guerra(
                    self.grupo_id, otro_agente.grupo_id
                )
                self.decir(
                    f"🚩 {msg}" if exito else f"⚠️ No pude declarar la guerra: {msg}",
                    global_broadcast=True,
                )

        elif tipo_interaccion == "NEGOCIAR_PAZ":
            if self.grupo_id and otro_agente.grupo_id:
                exito, msg = self.modelo.finalizar_guerra(
                    self.grupo_id, otro_agente.grupo_id
                )
                self.decir(
                    f"🕊️ {msg}" if exito else f"⚠️ La negociación de paz falló: {msg}",
                    global_broadcast=True,
                )

        # --- IMPACTO DIPLOMÁTICO ---
        if (
            self.grupo_id
            and otro_agente.grupo_id
            and self.grupo_id != otro_agente.grupo_id
        ):
            cambio_grupal = (
                0.05
                if (
                    tipo_interaccion == "SOCIALIZAR"
                    or tipo_interaccion == "social"
                    or tipo_interaccion == "ALIANZA"
                )
                else -0.1
            )
            self.modelo.actualizar_relacion_grupal(
                self.grupo_id, otro_agente.grupo_id, cambio_grupal
            )

    @synchronized
    def atacar(self, otro_agente):
        """Ataca directamente a otro agente (mando manual)."""
        return self.interactuar(otro_agente, "ATACAR")

    @synchronized
    def curar(self):
        """Usa medicinas del inventario para recuperar salud."""
        if self.inventario.get("medicina", 0) > 0:
            self.inventario["medicina"] -= 1
            recuperacion = 3.0 + (self.experiencia.get("medicina", 0) * 0.5)
            self.necesidades["salud"] = min(
                10.0, self.necesidades["salud"] + recuperacion
            )
            self.modelo.log(
                f"💊 [CURACION] Agente {self.unique_id} usó medicina. Salud: {self.necesidades['salud']:.1f}",
                categoria="salud",
            )
            return True, f"Salud recuperada a {self.necesidades['salud']:.1f}"
        return False, "No tienes medicinas"

    @synchronized
    def comer(self):
        """Consume comida del inventario."""
        if self.inventario.get("comida", 0) > 0:
            self.inventario["comida"] -= 1
            self.necesidades["alimento"] = min(10.0, self.necesidades["alimento"] + 4.0)
            self.modelo.log(
                f"🍎 [ALIMENTO] Agente {self.unique_id} ha comido. Alimento: {self.necesidades['alimento']:.1f}",
                categoria="alimentos",
            )
            return True, "Hambre saciada"
        return False, "No tienes comida"

    @synchronized
    def descansar(self):
        """Acción manual de descanso profundo."""
        self.necesidades["descanso"] = min(10.0, self.necesidades["descanso"] + 5.0)
        self.modelo.log(
            f"💤 [DESCANSO] Agente {self.unique_id} ha descansado profundamente.",
            categoria="state",
        )
        return True, "Energía recuperada"

    @synchronized
    def explorar(self):
        """Explora el entorno cercano desplazándose físicamente y ganando experiencia."""
        if self.necesidades["descanso"] < 2.0:
            return False, "Demasiado cansado para explorar"

        self.necesidades["descanso"] -= 1.5
        self.ganar_experiencia("exploracion", 3)

        # Mover al agente físicamente 1-2 celdas en dirección aleatoria
        map_width = len(self.modelo.mapa)
        map_height = len(self.modelo.mapa[0]) if map_width > 0 else 0
        pasos = random.randint(1, 2)
        ocupadas = set(
            (a.x, a.y)
            for a in self.modelo.agentes
            if a.unique_id != self.unique_id and a.esta_vivo
        )
        for _ in range(pasos):
            deltas = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
            random.shuffle(deltas)
            for ddx, ddy in deltas:
                nx = max(0, min(self.x + ddx, map_width - 1))
                ny = max(0, min(self.y + ddy, map_height - 1))

                tile_cand = self.modelo.mapa[nx][ny]
                propietario = getattr(tile_cand, "owner_civ_id", None)
                if propietario and propietario != self.grupo_id:
                    continue

                if (nx, ny) not in ocupadas:
                    self.x = nx
                    self.y = ny
                    ocupadas.add((nx, ny))
                    break

        tile = self.modelo.mapa[self.x][self.y]
        region = self.modelo.world.get_region_name(self.x, self.y)

        # 1. Detectar sitio arqueológico sin descubrir
        if getattr(tile, "is_archaeological_site", False) and tile.discovered_by is None:
            # El SistemaEventosEmergentes se encargará del evento en su próximo ciclo.
            # Aquí simplemente notificamos al agente de inmediato.
            self.ganar_experiencia("exploracion", 5)
            self.registrar_evento(
                f"He llegado a unas ruinas ancestrales en {region}. Siento que guardan secretos importantes."
            )
            self.modelo.log(
                f"🛒 [EXPLORACIÓN] {self.unique_id} ha llegado a un sitio arqueológico en ({self.x},{self.y}) - {region}!",
                categoria="info",
            )
            self.modelo.notificar_cambio_estado()
            return True, f"Has llegado a un sitio arqueológico en {region}"

        # 2. Detectar saberes ya descubiertos en ruinas visitadas
        saberes_en_tile = getattr(tile, "saberes_descubiertos", [])
        if saberes_en_tile:
            saber = saberes_en_tile[-1]
            self.registrar_evento(
                f"En las ruinas de {region} encontré vestigios de un '{saber['tipo']}' "
                f"descubierto antes por otro explorador."
            )
            self.ganar_experiencia("exploracion", 2)

        # 3. Hallazgo genérico de recursos
        if random.random() < 0.25:
            hallazgo = random.choice(["madera", "piedra", "comida"])
            cant = random.randint(1, 4)
            self.inventario[hallazgo] = self.inventario.get(hallazgo, 0) + cant
            self.registrar_evento(f"Durante mi exploración de {region} encontré {cant} de {hallazgo}.")
            self.modelo.log(
                f"🔍 [EXPLORACIÓN] {self.unique_id} encontró {cant} de {hallazgo} en {region}!",
                categoria="info",
            )
            self.modelo.notificar_cambio_estado()
            return True, f"Encontraste {cant} {hallazgo} en {region}"

        # 4. Evaluar hidratación local
        hid = getattr(tile, "hidratacion", 70.0)
        if hid < 25.0:
            self.registrar_evento(
                f"La tierra de {region} está seca y agotada. La hidratación es crítica ({hid:.0f}%)."
            )

        self.modelo.log(
            f"🔍 [EXPLORACIÓN] {self.unique_id} exploró {region} ({self.x},{self.y}) pero no halló nada especial.",
            categoria="info",
        )
        self.registrar_evento(f"He explorado {region} sin encontrar nada de valor por ahora.")
        self.modelo.notificar_cambio_estado()
        return True, f"Zona explorada: {region}"

    @synchronized
    def estudiar(self):
        """Estudia en la ubicación actual si hay una universidad."""
        tile = self.modelo.mapa[self.x][self.y]
        tiene_uni = any(b.get("tipo") == "Universidad" for b in tile.buildings)

        if tiene_uni:
            self.ganar_experiencia("ciencia", 5)
            self.skill_factor = min(1.0, self.skill_factor + 0.02)
            self.modelo.log(
                f"📚 [ESTUDIO] Agente {self.unique_id} está estudiando en la Universidad. Factor habilidad: {self.skill_factor:.2f}",
                categoria="info",
            )
            return True, "Conocimiento aumentado"
        return False, "No hay una Universidad aquí"

    @synchronized
    def investigar(self):
        """Investigación teórica para mejorar el factor de habilidad."""
        if self.necesidades["alimento"] < 3.0:
            return False, "Demasiado hambre para investigar"

        self.necesidades["entretenimiento"] = max(
            0, self.necesidades["entretenimiento"] - 1.0
        )
        self.ganar_experiencia("investigacion", 4)
        self.skill_factor = min(1.0, self.skill_factor + 0.01)
        self.modelo.log(
            f"🧬 [INVESTIGACION] Agente {self.unique_id} realiza investigación avanzada.",
            categoria="info",
        )
        return True, "Investigación completada"

    @synchronized
    def opinar(self, mensaje):
        """Envía una opinión formal a la asamblea actual."""
        active_assemblies = [
            a for a in self.modelo.asambleas_globales if a.get("estado") == "DEBATE"
        ]
        if not active_assemblies:
            return False, "No hay asambleas en fase de debate"

        # Usar el prefijo estándar para que el sistema lo reconozca
        self.decir(f"🗣️ [OPINION ASAMBLEA] {mensaje}")
        return True, "Opinión enviada a la asamblea"

    @synchronized
    def fundar_institucion(self, nombre, tipo):
        """Llama al modelo para fundar una institución (requiere 100 MC)."""
        return self.modelo.fundar_institucion(self.unique_id, nombre, tipo)

    @synchronized
    def fundar_grupo(self, nombre_grupo, descripcion):
        """El agente crea un nuevo grupo con una idea central y se convierte en vocero."""
        if not nombre_grupo or not descripcion:
            self.modelo.log(
                f"⚠️ [RECHAZADO] Agente {self.unique_id} intentó fundar un grupo sin nombre o descripción.",
                categoria="sistema",
            )
            return {"exito": False, "error": "Falta nombre o descripción"}

        # Comprobar si el nombre es genérico o demasiado corto
            # Comprobar si el nombre es genérico o demasiado corto
        palabras_nombre = nombre_grupo.split()
        if len(palabras_nombre) < 1:
            return {"exito": False, "error": "Nombre vacío"}

        # Lista de nombres genéricos prohibidos
        prohibidos = [
            "grupo", "clan", "tribu", "alianza", "equipo", "faccion", "facción",
            "mi grupo", "el grupo", "nuevo grupo", "sociedad", "club",
            "asociación", "estado", "pueblo", "nación"
        ]
        nombre_lower = nombre_grupo.lower().strip()
        
        if nombre_lower in prohibidos:
            self.modelo.log(
                f"⚠️ [RECHAZADO] Agente {self.unique_id} usó un nombre prohibido o genérico: '{nombre_grupo}'.",
                categoria="sistema",
            )
            return {"exito": False, "error": "Nombre prohibido o genérico"}

        # Bloquear patrones genéricos tipo "Grupo de A5" o "Clan de Agente_X"
        patrones_prohibidos = [
            f"grupo de {self.unique_id}".lower(),
            f"clan de {self.unique_id}".lower(),
            f"tribu de {self.unique_id}".lower(),
            f"equipo de {self.unique_id}".lower(),
            f"alianza de {self.unique_id}".lower(),
            # También versiones con el nombre de identidad si lo tiene
            f"grupo de {self.identidad.nombre if self.identidad else self.unique_id}".lower(),
            f"clan de {self.identidad.nombre if self.identidad else self.unique_id}".lower(),
        ]
        
        if any(p in nombre_lower for p in patrones_prohibidos) or len(nombre_grupo) < 5:
            self.modelo.log(
                f"⚠️ [RECHAZADO] Agente {self.unique_id} intentó usar un nombre genérico o poco identitario: '{nombre_grupo}'.",
                categoria="sistema",
            )
            return {"exito": False, "error": "Nombre poco identitario"}

        # Validación estricta de descripción (mínimo 30 caracteres y debe ser descriptiva)
        if len(descripcion) < 30:
            self.modelo.log(
                f"⚠️ [RECHAZADO] Agente {self.unique_id} proporcionó una misión demasiado breve o genérica (requiere +30 chars).",
                categoria="sistema",
            )
            return {"exito": False, "error": "Descripción demasiado corta (+30 chars)"}

        if self.modelo.grupos_creados_este_paso >= 3:
            self.modelo.log(
                f"⚠️ [LIMITE] Agente {self.unique_id} intentó fundar un grupo, pero se alcanzó el límite de 3 por turno.",
                categoria="sistema",
            )
            return {"exito": False, "error": "Límite de grupos por turno alcanzado"}
        # Generar un ID basado en algo más que random para evitar colisiones si hay muchos
        nuevo_grupo_id = f"G-{random.randint(100, 999)}"

        # Intentar obtener un color único que no esté en uso por otra civilización
        colores_en_uso = [c.color for c in self.modelo.civilizaciones.values()]
        nuevo_color = self.modelo.colores_paleta[0]  # Default

        for color in self.modelo.colores_paleta:
            if color not in colores_en_uso:
                nuevo_color = color
                break
        else:
            # Si todos están en uso, usar uno determinista basado en el ID
            color_idx = hash(nuevo_grupo_id) % len(self.modelo.colores_paleta)
            nuevo_color = self.modelo.colores_paleta[color_idx]

        # Asegurar que el nombre del grupo sea único
        nombres_en_uso = [c.nombre for c in self.modelo.civilizaciones.values()]
        nombre_final = nombre_grupo

        # Si el nombre ya existe, agregar un número para hacerle único
        if nombre_final in nombres_en_uso:
            contador = 1
            while True:
                nombre_generado = f"{nombre_grupo} {contador}"
                if nombre_generado not in nombres_en_uso:
                    nombre_final = nombre_generado
                    break
                contador += 1

        self.modelo.civilizaciones[nuevo_grupo_id] = Civilizacion(
            id=nuevo_grupo_id,
            nombre=nombre_final,
            color=nuevo_color,
            user_id=getattr(self.modelo, "user_id", None),
            descripcion=descripcion,
        )
        # Asegurar que aparezca en el broadcast como grupo dinámico
        self.modelo.objetivos_grupos[nuevo_grupo_id] = descripcion

        self.grupo_id = nuevo_grupo_id
        self.civilizacion_id = nuevo_grupo_id
        self.rol = "Vocero"
        self.modelo.log(
            f"🚩 [FUNDACION] Agente {self.unique_id} ha fundado el grupo '{nombre_final}' con el objetivo: {descripcion}",
            categoria="consenso",
        )

        # ACTUAlIZACIÓN INMEDIATA DE UI Y PERSISTENCIA
        self.modelo.notificar_cambio_estado()
        self.modelo.guardar_estado()

        # Hito histórico
        self.modelo.historia.agregar_hito(
            {
                "turno": self.modelo.paso_actual,
                "descripcion": f"El Agente {self.unique_id} ha fundado el grupo '{nombre_final}'.",
                "tipo": "fundacion",
            }
        )

        self.modelo.grupos_creados_este_paso += 1
        return {"exito": True, "id": nuevo_grupo_id, "nombre": nombre_final}

    @synchronized
    def fundar_pueblo(self):
        """Transforma el grupo actual en un PUEBLO (requiere 5 agentes)."""
        if not self.grupo_id or self.grupo_id not in self.modelo.civilizaciones:
            return False, "No perteneces a ningún grupo."

        civ = self.modelo.civilizaciones[self.grupo_id]
        if civ.tipo != "GRUPO":
            return False, f"El grupo ya es un {civ.tipo}."

        miembros = [a for a in self.modelo.agentes if a.grupo_id == self.grupo_id]
        if len(miembros) < 5:
            return False, f"Se necesitan al menos 5 miembros (tienes {len(miembros)})."

        civ.tipo = "PUEBLO"
        self.modelo.log(
            f"🏘️ [ASENTAMIENTO] ¡Agente {self.unique_id} ha fundado el pueblo '{civ.nombre}'!",
            categoria="sistema",
        )

        # Intentar crear un centro de pueblo que ocupe 2x2 casillas (plazoleta + ayuntamiento)
        try:
            mapa = getattr(self.modelo, "mapa", None)
            if mapa:
                filas = len(mapa)
                cols = len(mapa[0]) if filas > 0 else 0

                # Escoger la casilla top-left asegurando que 2x2 quepa en el mapa
                tx = max(0, min(int(self.x), max(0, filas - 2)))
                ty = max(0, min(int(self.y), max(0, cols - 2)))

                footprint = [(tx, ty), (tx + 1, ty), (tx, ty + 1), (tx + 1, ty + 1)]

                edif_id = f"EDIF-{len(self.modelo.infraestructura) + 1}"
                nuevo_edif = {
                    "id": edif_id,
                    "tipo": "CentroPueblo",
                    "grupo_id": self.grupo_id,
                    "nombre": f"Centro de {civ.nombre}",
                    "x": tx,
                    "y": ty,
                    "tiles": footprint,
                    "es_institucion": True,
                    "paso_creacion": getattr(self.modelo, "paso_actual", 0),
                }

                # Registrar infraestructura global
                self.modelo.infraestructura.append(nuevo_edif)

                # Marcar cada casilla: propietario, añadir edificio y convertir a PATH (plazoleta)
                for (ex, ey) in footprint:
                    if 0 <= ex < filas and 0 <= ey < cols:
                        try:
                            tile = mapa[ex][ey]
                            tile.owner_civ_id = self.grupo_id
                            tile.buildings.append(
                                {
                                    "id": edif_id,
                                    "tipo": "CentroPueblo",
                                    "grupo_id": self.grupo_id,
                                    "x": ex,
                                    "y": ey,
                                    "paso_creacion": getattr(self.modelo, "paso_actual", 0),
                                }
                            )
                            # Opcional: marcar terreno como camino/plaza para distinto render
                            try:
                                tile.terrain = TerrainType.PATH
                            except Exception:
                                pass
                        except Exception:
                            # No forzar fallo si alguna casilla da error
                            continue

                try:
                    self.modelo._map_dirty = True
                except Exception:
                    pass
        except Exception:
            # No bloquear la fundación del pueblo si falla la colocación del centro
            pass

        self.modelo.notificar_cambio_estado()
        return True, f"¡Has fundado el pueblo {civ.nombre}!"

    @synchronized
    def invitar_agente(self, otro_agente):
        """Envía una invitación formal para unirse a su facción."""
        if self.grupo_id is None:
            return False

        # Solo invitamos si no tiene grupo o si queremos que cambie
        if otro_agente.grupo_id == self.grupo_id:
            return False

        mision = self.modelo.objetivos_grupos.get(
            self.grupo_id, "Prosperidad Colectiva"
        )
        otro_agente.ultimo_mensaje_recibido = {
            "emisor": self.unique_id,
            "contenido": f"INVITACION_GRUPO:{self.grupo_id}:{mision}",
        }
        self.modelo.log(
            f"✉️ [INVITACION] Agente {self.unique_id} invita a {otro_agente.unique_id} a unirse a la Facción {self.grupo_id}.",
            categoria="social",
        )
        return True

    @synchronized
    def unirse_a_grupo(self, grupo_id):
        """Une al agente formalmente a una facción/grupo conocido.

        Si la facción no existe en el modelo, se permite la unión como fallback
        pero se registra en logs para diagnóstico.
        """
        if not grupo_id:
            return False

        # Si grupo_id no existe como clave, buscar por nombre en civilizaciones
        if grupo_id not in self.modelo.civilizaciones:
            nombre_lower = str(grupo_id).lower()
            for gid, civ in self.modelo.civilizaciones.items():
                if civ.nombre.lower() == nombre_lower:
                    grupo_id = gid
                    break

        if getattr(self, 'grupo_id', None) == grupo_id:
            return False

        civ = None
        try:
            civ = self.modelo.civilizaciones.get(grupo_id)
        except Exception:
            civ = None

        self.grupo_id = grupo_id
        self.rol = "Ciudadano"

        if civ:
            self.modelo.log(
                f"🏳️ [UNION] Agente {self.unique_id} se ha unido a la facción {grupo_id} ({civ.nombre}).",
                categoria="social",
            )
        else:
            self.modelo.log(
                f"🏳️ [UNION] Agente {self.unique_id} se ha unido a la facción {grupo_id} (no registrada en el modelo).",
                categoria="social",
            )

        # Notificar cambios de estado para refrescar UI / persistencia
        try:
            if hasattr(self.modelo, 'notificar_cambio_estado'):
                self.modelo.notificar_cambio_estado()
            if hasattr(self.modelo, 'guardar_estado'):
                self.modelo.guardar_estado()
        except Exception:
            pass

        return True

    def formar_alianza(self, otro_agente, terminos=None):
        """Crea un pacto de alianza mutua con términos específicos."""
        # Limpieza robusta de datos corruptos (strings en lugar de dicts)
        self.tratados = [t for t in self.tratados if isinstance(t, dict)]

        # Si no hay términos, es una alianza básica de apoyo mutuo
        if terminos is None:
            terminos = {
                "tipo": "apoyo_mutuo",
                "descripcion": "Apoyo social y suministros básicos",
            }

        # Evitar duplicados de tratados activos con el mismo agente
        if any(t["socio_id"] == otro_agente.unique_id for t in self.tratados):
            return False

        nuevo_tratado_yo = {
            "socio_id": otro_agente.unique_id,
            "terminos": terminos,
            "pasos_restantes": 10,  # Duración estándar de 10 turnos
        }
        nuevo_tratado_otro = {
            "socio_id": self.unique_id,
            "terminos": terminos,
            "pasos_restantes": 10,
        }

        self.tratados.append(nuevo_tratado_yo)

        # Validar lista del otro agente
        if not isinstance(otro_agente.tratados, list):
            otro_agente.tratados = []
        # Limpiar corruptos del otro agente también
        otro_agente.tratados = [t for t in otro_agente.tratados if isinstance(t, dict)]

        otro_agente.tratados.append(nuevo_tratado_otro)

        # Mantener lista de alianzas para compatibilidad visual (y reparar si hay datos corruptos)
        if not isinstance(self.alianzas, list):
            self.alianzas = []
        if not isinstance(otro_agente.alianzas, list):
            otro_agente.alianzas = []

        if otro_agente.unique_id not in self.alianzas:
            self.alianzas.append(otro_agente.unique_id)
        if self.unique_id not in otro_agente.alianzas:
            otro_agente.alianzas.append(self.unique_id)

        desc = terminos.get("descripcion", "Pacto formal")
        self.modelo.log(
            f"📜 [TRATADO] {self.unique_id} y {otro_agente.unique_id} han firmado: {desc}",
            categoria="social",
        )

        # Registrar en memoria gráfica para visualización
        self.memoria.registrar_interaccion(
            otro_agente.unique_id,
            "alianza",
            0.5,
            otro_agente.recursos,
            otro_agente.grupo_id,
        )
        otro_agente.memoria.registrar_interaccion(
            self.unique_id, "alianza", 0.5, self.recursos, self.grupo_id
        )

        self.modelo.notificar_cambio_estado()  # Actualizar alianzas en tiempo real
        return True

    def declarar_simpatia(self, grupo_id):
        """Registra que este agente declara simpatía por una facción.
        
        Args:
            grupo_id: ID de la facción hacia la que se declara simpatía.
            
        Returns:
            bool: True si se registró correctamente.
        """
        if not grupo_id:
            return False
        
        # Evitar duplicados
        if grupo_id in self.simpatizante_de:
            return False
        
        # Registrar la simpatía
        self.simpatizante_de.append(grupo_id)
        
        # Aumentar afinidad entre el grupo del agente y el grupo objetivo
        if self.grupo_id and self.grupo_id != grupo_id:
            self.modelo.actualizar_relacion_grupal(self.grupo_id, grupo_id, 0.15)
        
        # Aumentar reputación
        self.reputacion = min(100, self.reputacion + 2)
        
        # Generar evento memorable
        if hasattr(self, 'eventos_recientes'):
            evento = {
                "turno": self.modelo.paso_actual,
                "tipo": "simpatia_declarada",
                "descripcion": f"Declaró simpatía por la facción {grupo_id}.",
                "impacto": "reputacion",
            }
            self.eventos_recientes.append(evento)
            if len(self.eventos_recientes) > 20:
                self.eventos_recientes = self.eventos_recientes[-20:]
        
        # Registrar en el log del modelo
        self.modelo.log(
            f"💙 [DIPLOMACIA] Agente {self.unique_id} ha declarado simpatía por la facción {grupo_id}.",
            categoria="social",
        )
        
        # Notificar cambio de estado
        self.modelo.notificar_cambio_estado()
        return True
    # === MÉTODOS SOCIALES OASIS ===
    def social_follow(self, otro_agente) -> bool:
        """El agente sigue a otro agente. Acepta objeto agente o ID string."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        # Manejar si se pasa un ID en lugar de un objeto
        if isinstance(otro_agente, str):
            target_id = otro_agente
            otro_agente_obj = next((a for a in self.modelo.agentes if a.unique_id == target_id), None)
        else:
            target_id = otro_agente.unique_id
            otro_agente_obj = otro_agente

        exito = recsys.follow(self.unique_id, target_id)
        if exito:
            self.siguiendo += 1
            if otro_agente_obj:
                otro_agente_obj.seguidores += 1
            self.modelo.log(
                f"📡 [{self.unique_id}] Ahora sigue a [{target_id}]",
                categoria="social",
            )
            if hasattr(self.modelo, "notificar_cambio_estado"):
                self.modelo.notificar_cambio_estado()
        return exito

    def social_unfollow(self, otro_agente) -> bool:
        """El agente deja de seguir a otro. Acepta objeto agente o ID string."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        if isinstance(otro_agente, str):
            target_id = otro_agente
            otro_agente_obj = next((a for a in self.modelo.agentes if a.unique_id == target_id), None)
        else:
            target_id = otro_agente.unique_id
            otro_agente_obj = otro_agente

        exito = recsys.unfollow(self.unique_id, target_id)
        if exito:
            self.siguiendo = max(0, self.siguiendo - 1)
            if otro_agente_obj:
                otro_agente_obj.seguidores = max(0, otro_agente_obj.seguidores - 1)
            if hasattr(self.modelo, "notificar_cambio_estado"):
                self.modelo.notificar_cambio_estado()
        return exito

    def social_like(self, target_id: str) -> bool:
        """El agente da like a un post."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        exito = recsys.likear_post(target_id, self.unique_id)
        if exito:
            # Incrementar likes recibidos del autor del post
            post = recsys.interest_recsys.posts.get(target_id)
            if post:
                autor_post = next(
                    (a for a in self.modelo.agentes if a.unique_id == post.autor_id),
                    None,
                )
                if autor_post:
                    autor_post.likes_recibidos += 1
                
                # --- NUEVO: Actualizar intereses basado en post likeado ---
                self.actualizar_intereses_por_post(post, engagement_level=2.0)
            
            # Recompensa biológica: un like satisface un poco la necesidad social
            self.necesidades["social"] = min(10.0, self.necesidades["social"] + 0.5)
            self.capital_social = self.calcular_capital_social()
            
            if hasattr(self.modelo, "notificar_cambio_estado"):
                self.modelo.notificar_cambio_estado()
                if hasattr(self.modelo, "difundir_social_feed"):
                    self.modelo.difundir_social_feed()
        return exito


    def social_create_post(
        self, contenido: str, tipo: str = "opinion", temas: List[str] = None
    ) -> bool:
        """El agente crea un post en la red social."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        paso = getattr(self.modelo, "paso_actual", 0)
        post = recsys.crear_post(self.modelo.user_id, self.unique_id, contenido, tipo, temas, timestamp=paso)

        self.posts_publicados += 1
        # Publicar satisface la necesidad de expresión (baja el hambre de expresión)
        if "expresion" in self.necesidades_intelectuales:
            self.necesidades_intelectuales["expresion"] = max(
                0.0, self.necesidades_intelectuales["expresion"] - 2.0
            )

        # --- NUEVO: Actualizar intereses basado en el post creado ---
        self.actualizar_intereses_por_post(post, engagement_level=5.0)  # Crear = máximo

        self.capital_social = self.calcular_capital_social()

        # Notificar cambio de estado para actualizar UI
        if hasattr(self.modelo, "notificar_cambio_estado"):
            self.modelo.notificar_cambio_estado()

        return True

    def social_comment(self, post_id: str, contenido: str) -> bool:
        """El agente comenta en un post."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        # No publicar comentarios vacíos o no-string cuando LLM no disponible
        if not contenido or not isinstance(contenido, str):
            return False

        exito = recsys.comentar(post_id, self.unique_id, contenido)
        if exito:
            # --- NUEVO: Actualizar intereses basado en post comentado ---
            post = recsys.interest_recsys.posts.get(post_id)
            if post:
                self.actualizar_intereses_por_post(post, engagement_level=3.0)
            
            self.comentarios_realizados += 1
            # Recompensa biológica: comentar es interacción social fuerte
            self.necesidades["social"] = min(10.0, self.necesidades["social"] + 1.5)
            self.capital_social = self.calcular_capital_social()
            
            # MEJORA: Registrar comentario en memoria para retroalimentación
            self.memoria.registrar_accion(f"Comenté en post: {contenido[:40]}...")
            # Incrementar contador de engagement positivo reciente
            self.ultimo_engagement_positivo = getattr(self.modelo, "paso_actual", 0)

            # Notificar cambio de estado para actualizar UI
            if hasattr(self.modelo, "notificar_cambio_estado"):
                self.modelo.notificar_cambio_estado()
        return exito

    def get_social_feed(self, limite: int = 10) -> Dict:
        """Obtiene el feed personalizado del agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return {
                "in_network": [],
                "recommended": [],
                "trending": [],
                "all_posts": [],
            }

        feed = recsys.get_feed_hibrido(self, self.modelo.paso_actual, limite)
        
        # --- NUEVO: Marcar posts como leídos para reforzar intereses ---
        for categoria_posts in feed.values():
            if isinstance(categoria_posts, list):
                for post in categoria_posts[:3]:  # Top 3 de cada categoría
                    self.actualizar_intereses_por_post(post, engagement_level=1.0)
        
        return feed

    def get_following(self) -> List[str]:
        """Retorna la lista de IDs que sigue este agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return []
        return recsys.get_siguiendo(self.unique_id)

    def get_followers(self) -> List[str]:
        """Retorna la lista de seguidores de este agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return []
        return recsys.get_seguidores(self.unique_id)

    def get_social_notifications(self) -> List[Dict]:
        """Obtiene todas las interacciones (likes/comentarios) en los posts de este agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return []
        return recsys.get_interacciones_usuario(self.unique_id)

    def _ejecutar_accion_social_automatica(self, paso: int):
        """
        Ejecuta una acción automática en la red social cada turno.
        Separa la creación de posts de las interacciones (likes/comentarios).
        """
        import random
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        # --- FASE 1: NAVEGACIÓN E INTERACCIÓN (Frecuente) ---
        ultimo_interact = getattr(self, "ultimo_paso_social_interact", -1000)
        # AUMENTADO: prob_browse de 0.3 a 0.5 para más interacción
        # Bonus por engagement previo: si el agente ha tenido buen engagement, tiene más probabilidad de seguir interactuando
        engagement_bonus = 0.1 if getattr(self, "ultimo_engagement_positivo", 0) > paso - 5 else 0.0
        prob_browse = 0.5 + (self.personalidad.get("extroversión", 0.5) * 0.3) + engagement_bonus
        
        if paso - ultimo_interact >= 1 and random.random() < prob_browse:
            self._ejecutar_interaccion_random()
            self.ultimo_paso_social_interact = paso

        # --- FASE 2: CREACIÓN DE CONTENIDO (Menos frecuente) ---
        if not getattr(self, "_ejecutando_decreto", False):
            ultimo_paso = getattr(self, "ultimo_paso_social", -10_000)
            intervalo_min = getattr(self.modelo, "social_post_min_interval", 4)
            if paso - ultimo_paso < intervalo_min:
                return False
            if random.random() > 0.5:
                return False

        self.ultimo_paso_social = paso
        tipo_contenido = self._determinar_tipo_post()

        if random.random() < getattr(self.modelo, "social_llm_ratio", 0.45):
            contenido = self._generar_contenido_post(tipo_contenido, paso)
        else:
            contenido = self._generar_contenido_post_rapido(tipo_contenido, paso)

        if contenido and len(contenido) > 10:
            temas = self._detectar_temas_post(contenido)
            self.social_create_post(contenido, tipo=tipo_contenido, temas=temas)
            nombre_agente = self.identidad.nombre if self.identidad else self.unique_id
            self.modelo.log(
                f"📱 [{nombre_agente}] Publicó en la red: {contenido[:100]}...",
                categoria="social",
            )

            if getattr(self.modelo, "realtime_event_callback", None):
                try:
                    # Usar helper que puede aplicar un pequeño retraso según el ritmo
                    self.modelo._emit_realtime_event(
                        "social_event",
                        {
                            "agent_id": self.unique_id,
                            "agent_name": nombre_agente,
                            "step": paso,
                            "event": "post_created",
                            "content": contenido,
                            "post_type": tipo_contenido,
                        },
                    )
                except Exception:
                    pass
            return True
        return False

    def _ejecutar_interaccion_random(self):
        """Elige y ejecuta una interacción social basada en el feed y personalidad."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys: return
        
        import random
        try:
            feed = recsys.get_feed_hibrido(self, self.modelo.paso_actual, limite=10)
            posts = feed.get("all_posts", [])
        except Exception:
            posts = []
            
        if not posts: return
        
        otros_posts = [p for p in posts if p.autor_id != self.unique_id]
        if not otros_posts: return
        
        post = random.choice(otros_posts)
        r = random.random()
        amabilidad = self.personalidad.get("amabilidad", 0.5)
        extroversion = self.personalidad.get("extroversión", 0.5)
        
        # MEJORA: Aumentar prioridad de comentarios (antes 35%, ahora 50%)
        # Prioridad ajustada: Like (40%), Comment (50%), Follow (10%)
        # Bonus por engagement: si el post tiene mucho engagement, aumenta probabilidad de comentar
        engagement = getattr(post, 'likes', 0) + (getattr(post, 'comentarios', 0) * 2)
        engagement_bonus_comment = min(0.15, engagement * 0.01) if getattr(self, "fomento_engagement", True) else 0.0
        
        # Guardar engagement en la memoria del agente para retroalimentación futura
        if engagement > 5:  # si el post tuvo buen engagement
            paso_actual = getattr(self.modelo, "paso_actual", 0)
            self.ultimo_engagement_positivo = paso_actual
            self.memoria.registrar_accion(f"Engagement pos: {engagement} puntos en post")
        
        if r < 0.40 + (amabilidad * 0.15):
            self._ejecutar_like_aleatorio(post.id)
        elif r < 0.90 + (extroversion * 0.08) + engagement_bonus_comment:
            # LOG para depuración
            nombre_yo = self.identidad.nombre if self.identidad else self.unique_id
            print(f"DEBUG: Agente {nombre_yo} decidió COMENTAR en post {post.id}")
            self._ejecutar_comentario_aleatorio(post.id)
        else:
            self._ejecutar_follow_aleatorio()

    def social_force_action(self, paso: int) -> bool:
        """Ejecuta forzosamente una acción en la red social por turno.

        Garantiza que cada turno el agente realice una acción social (post, like, comment o follow).
        """
        import random
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        # 1. Obtener el feed para interactuar
        try:
            feed = recsys.get_feed_hibrido(self, paso, limite=20)
            posts = []
            if isinstance(feed, dict):
                posts = feed.get("all_posts", []) or []
            elif isinstance(feed, list):
                posts = feed
        except Exception:
            posts = []

        # 2. Decidir tipo de acción
        # Probabilidades base: Post (20%), Like (30%), Comment (35%), Follow (15%)
        if not posts:
            decision = "post"
        else:
            exp_hunger = self.necesidades_intelectuales.get("expresion", 0)
            engagement_bonus = 0.15 if getattr(self, "ultimo_engagement_positivo", 0) > paso - 3 else 0.0
            if exp_hunger > 7 or self.posts_publicados < 1:
                decision = random.choices(
                    ["post", "like", "comment", "follow"], weights=[0.4, 0.2, 0.25 + engagement_bonus, 0.15]
                )[0]
            else:
                decision = random.choices(
                    ["post", "like", "comment", "follow"], weights=[0.15, 0.3, 0.40 + engagement_bonus, 0.15]
                )[0]

        # 3. Ejecutar la decisión
        from agents.cerebro_llm import cerebro_llm

        if decision == "post":
            try:
                tipo_post = self._determinar_tipo_post() if hasattr(self, "_determinar_tipo_post") else "opinion"
                # USAR CONTEXTO ENRIQUECIDO (Diary, Milestones, Weather)
                if hasattr(self, "_generar_contenido_post"):
                    contenido = self._generar_contenido_post(tipo_post, paso)
                else:
                    contenido = cerebro_llm.generar_post_social(self, f"Paso: {paso}")
            except Exception:
                contenido = None
            if contenido:
                return self.social_create_post(contenido, tipo=tipo_post, temas=[])

        elif decision == "like" and posts:
            # Likear 1-2 posts aleatorios
            num_likes = random.randint(1, 2)
            liked_any = False
            for _ in range(num_likes):
                target = random.choice(posts)
                if self.social_like(target.id):
                    liked_any = True
            if liked_any: return True

        elif decision == "comment" and posts:
            # Comentar en un post que no sea propio si es posible
            otros_posts = [p for p in posts if getattr(p, "autor_id", None) != self.unique_id]
            target = random.choice(otros_posts) if otros_posts else random.choice(posts)
            
            try:
                # Usar el nuevo método del cerebro para generar comentarios reales (requiere LLM)
                contenido_comentario = cerebro_llm.generar_comentario_social(self, target, f"Turno {paso}")
            except Exception as e:
                contenido_comentario = None
            
            # Si no se obtuvo comentario válido (p.ej. LLM ausente), no comentar
            if not contenido_comentario:
                return False
            return self.social_comment(target.id, contenido_comentario)

        elif decision == "follow" and posts:
            # Priorizar seguir a alguien que no seguimos aún
            siguiendo = self.get_following()
            otros_posts = [p for p in posts if getattr(p, "autor_id", None) != self.unique_id and getattr(p, "autor_id", None) not in siguiendo]
            target = random.choice(otros_posts) if otros_posts else random.choice(posts)
            if target and hasattr(target, 'autor_id'):
                return self.social_follow(target.autor_id)

        # Fallback a follow si no se hizo nada
        if posts and random.random() < 0.2:
            target = random.choice(posts)
            return self.social_follow(target.autor_id)

        return False

    def _generar_contenido_post_rapido(self, tipo: str, paso: int) -> str:
        """Genera un post breve sin LLM para acelerar turnos."""
        nombre = self.identidad.nombre if self.identidad else self.unique_id
        hambre = self.necesidades.get("alimento", 5)
        social = self.necesidades.get("social", 5)

        if tipo == "hungry":
            return (
                f"{nombre}: estoy con hambre ({hambre:.1f}/10). "
                "Si alguien se suma, armemos una ruta para conseguir comida."
            )
        if tipo == "social":
            return (
                f"{nombre}: hoy necesito más conexión ({social:.1f}/10). "
                "¿Quién quiere conversar o coordinar una acción conjunta?"
            )
        if tipo == "opinion":
            return (
                f"{nombre}: producir recursos ayuda, pero sin acuerdos estables "
                "la tensión vuelve. Deberíamos coordinar reglas claras."
            )
        if tipo == "question":
            return (
                f"{nombre}: paso {paso}. Pregunta abierta: "
                "¿qué estrategia les está funcionando mejor para sostenerse?"
            )
        if tipo == "event":
            return (
                f"{nombre}: hubo cambios recientes en el entorno. "
                "Compartan señales para reaccionar más rápido."
            )
        return (
            f"{nombre}: sigo observando el mundo en el paso {paso}. "
            "Si detectan una oportunidad, me sumo."
        )

    def _determinar_tipo_post(self) -> str:
        """Determina el tipo de post según el estado del agente."""
        import random

        # Basado en necesidades y eventos recientes
        if self.necesidades_intelectuales.get("expresion", 5) > 3:
            return "opinion"  # Quiere expresar opinión
        elif self.necesidades_intelectuales.get("curiosidad", 5) > 3:
            return "question"  # Tiene curiosidad
        elif self.necesidades.get("alimento", 5) < 4:
            return "hungry"  # Tiene hambre
        elif self.necesidades.get("social", 5) < 4:
            return "social"  # Necesita socializar
        else:
            return random.choice(["observation", "reflection", "event"])

    def _generar_contenido_post(self, tipo: str, paso: int) -> str:
        """Genera contenido apropiado para el tipo de post usando el LLM."""
        from agents.cerebro_llm import cerebro_llm

        # Contexto enriquecido con información del mundo
        contexto_adicional = f"=== CONTEXTO DEL MUNDO (Paso {paso}) ===\n"
        contexto_adicional += f"Tipo de post sugerido: {tipo}\n"

        # Ubicación actual
        region_name = self.modelo.world.get_region_name(self.x, self.y)
        weather = getattr(self.modelo, "weather", "despejado")
        contexto_adicional += f"Ubicación actual: Región de {region_name} (Coordenadas: {self.x}, {self.y})\n"
        contexto_adicional += f"Clima actual: {weather}\n"

        # --- NUEVO: Hechos relevantes del mundo (Hitos Históricos) ---
        if hasattr(self.modelo, "historia") and self.modelo.historia:
            hitos = self.modelo.historia.obtener_resumen_hitos()
            if hitos and "No han ocurrido" not in hitos:
                contexto_adicional += "\n=== NOTICIAS Y HECHOS RECIENTES DEL MUNDO ===\n"
                contexto_adicional += hitos + "\n"
                contexto_adicional += "==============================================\n"

        # Historial de eventos reales (Diario)
        eventos = getattr(self, "eventos_recientes", [])
        if eventos:
            contexto_adicional += "\n=== TU DIARIO PERSONAL (EVENTOS REALES RECIENTES) ===\n"
            for ev in eventos[-8:]: # Los últimos 8 eventos
                contexto_adicional += f"- [Turno {ev['paso']}] {ev['descripcion']}\n"
            contexto_adicional += "====================================================\n"
        else:
            contexto_adicional += "\n(No has registrado eventos significativos recientemente en tu diario).\n"

        # Estado personal del agente
        contexto_adicional += f"Tus valores: {', '.join(self.alma.valores) if hasattr(self, 'alma') and self.alma and self.alma.valores else 'ninguno'}\n"
        contexto_adicional += f"Tus necesidades urgentes: alimento={self.necesidades.get('alimento', 5):.1f}, social={self.necesidades.get('social', 5):.1f}, descanso={self.necesidades.get('descanso', 5):.1f}\n"
        contexto_adicional += f"Tu dinero: {self.dinero} MC\n"

        # Información contextual basada en tipo
        if tipo == "hungry":
            contexto_adicional += "Tienes hambre urgente. Publica sobre tu necesidad de alimento o critica la distribución de recursos."
        elif tipo == "social":
            contexto_adicional += "Te sientes solo. Busca conexión con otros o comenta sobre la importancia de la comunidad."
        elif tipo == "opinion":
            contexto_adicional += "Tienes opiniones fuertes. Expresa tu posición sobre la política, economía o ética del mundo."
        elif tipo == "question":
            contexto_adicional += "Tienes curiosidad. Formula preguntas sobre misterios, desafíos o posibilidades del mundo."
        elif tipo == "observation":
            contexto_adicional += "Observaste algo interesante. Comparte tu descubrimiento o inquietud."
        elif tipo == "reflection":
            contexto_adicional += "Reflexiona sobre tu propósito, tu viaje, o lecciones aprendidas."
        elif tipo == "event":
            contexto_adicional += "Algo importante sucedió. Comenta sobre su significado o impacto."

        contexto_adicional += "\n"

        # Otros agentes cercanos
        otros_vivos = [a for a in self.modelo.agentes if a.unique_id != self.unique_id and a.esta_vivo]
        if otros_vivos:
            contexto_adicional += f"Otros habitantes conocidos: {len(otros_vivos)}\n"
            # Ordenar por cercanía
            otros_vivos.sort(key=lambda a: abs(a.x - self.x) + abs(a.y - self.y))
            for otra in otros_vivos[:5]:
                dist = abs(otra.x - self.x) + abs(otra.y - self.y)
                rel = self.memoria.obtener_tipo(otra.unique_id) if hasattr(self, "memoria") else "desconocido"
                contexto_adicional += f"  - {otra.identidad.nombre or otra.unique_id}: a {dist} pasos. Relación: {rel}. Pos: ({otra.x}, {otra.y})\n"

        # Posts recientes para contexto informativo (NO para responder directamente)
        recsys = getattr(self.modelo, "social_recsys", None)
        if recsys and recsys.interest_recsys.posts:
            posts_recientes = list(recsys.interest_recsys.posts.values())[-5:]
            if posts_recientes:
                contexto_adicional += f"\nÚltimas noticias y tendencias en la red (informativo):\n"
                for post in posts_recientes:
                    if post.autor_id != self.unique_id:
                        autor_nombre = post.autor_id
                        for a in self.modelo.agentes:
                            if a.unique_id == post.autor_id:
                                autor_nombre = a.identidad.nombre or a.unique_id
                                break
                        contexto_adicional += f"  - Tendencia: {post.contenido[:100]}...\n"

        # Situación económica y política
        contexto_adicional += f"\nSituación del mundo:\n"
        contexto_adicional += f"  - Índice bursátil: {self.modelo.economia.get('indice_bursatil', 100):.1f}\n"
        contexto_adicional += f"  - Precio de recursos: {self.modelo.economia.get('precio_recurso', 2):.2f} MC\n"
        contexto_adicional += f"  - Clima: {self.modelo.weather}\n"
        contexto_adicional += f"  - Tu reputación: {self.reputacion:.1f}\n"

        if self.grupo_id:
            civ = self.modelo.civilizaciones.get(self.grupo_id)
            nombre_g = civ.nombre if civ else self.grupo_id
            contexto_adicional += f"  - Tu grupo/facción: {nombre_g}\n"

        contexto_adicional += (
            "\n[REGLAS CRÍTICAS PARA TU PUBLICACIÓN]:\n"
            "1. NO INVENTES nombres de lugares o eventos falsos.\n"
            "2. Habla sobre el mundo, tus planes, tus necesidades o tus reflexiones filosóficas.\n"
            "3. NO te dirijas a otros agentes ni respondas a posts aquí. Si quieres debatir con alguien, espera a que el sistema te permita COMENTAR.\n"
            "4. Sé sustancial (200-600 caracteres) y profundo.\n"
        )

        # Eventos emergentes activos en el mundo
        sistema_ev = getattr(self.modelo, "sistema_eventos", None)
        if sistema_ev:
            eventos_texto = sistema_ev.get_eventos_activos_para_contexto()
            if eventos_texto:
                contexto_adicional += f"\n{eventos_texto}\n"

        # Generar post usando el LLM
        return cerebro_llm.generar_post_social(self, contexto_adicional)

    def _detectar_temas_post(self, contenido: str) -> List[str]:
        """Detecta temas de un post."""
        contenido_lower = contenido.lower()
        temas = []

        if any(
            p in contenido_lower for p in ["comida", "hambre", "alimento", "recurso"]
        ):
            temas.append("supervivencia")
        if any(
            p in contenido_lower for p in ["solo", "conectar", "interactuar", "social"]
        ):
            temas.append("social")
        if any(
            p in contenido_lower
            for p in ["reflexiono", "pensamiento", "opinion", "posición"]
        ):
            temas.append("opinión")
        if any(p in contenido_lower for p in ["pregunta", "descubrir", "cómo"]):
            temas.append("curiosidad")
        if any(p in contenido_lower for p in ["observo", "entorno", "mundo"]):
            temas.append("observación")
        if any(p in contenido_lower for p in ["encuentro", "cambiar", "suceso"]):
            temas.append("evento")

        if not temas:
            temas.append("general")

        return temas

    def _ejecutar_like_aleatorio(self, target_post_id=None):
        """Da like a un post específico o uno aleatorio."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return

        if target_post_id:
            post_id = target_post_id
        else:
            posts = recsys.interest_recsys.posts
            if not posts: return
            post_ids = [pid for pid, p in posts.items() if p.autor_id != self.unique_id]
            if not post_ids: return
            import random
            # MEJORA: priorizar posts con engagement alto para dar like
            posts_con_engagement = [(pid, p) for pid, p in posts.items() if p.autor_id != self.unique_id and p.likes > 2]
            if posts_con_engagement and random.random() < 0.6:  # 60% de probabilidad de priorizar engagement
                post_id = random.choice(posts_con_engagement)[0]
            else:
                post_id = random.choice(post_ids)

        self.social_like(post_id)
        self.likes_dados += 1
        # MEJORA: si el like va a un post conengagement alto, el agente se siente más satisfecho
        post = recsys.interest_recsys.posts.get(post_id)
        if post and post.likes > 5:
            self.ultimo_engagement_positivo = getattr(self.modelo, "paso_actual", 0)

    def _ejecutar_follow_aleatorio(self):
        """Sigue a un agente aleatorio."""
        otros = [
            a
            for a in self.modelo.agentes
            if a.unique_id != self.unique_id and a.esta_vivo
        ]
        if not otros:
            return

        import random

        otro = random.choice(otros)

        # MEJORA: priorizar seguir a agentes con buen engagement o alta influencia
        # Buscar si hay agentes con posts de alto engagement
        recsys = getattr(self.modelo, "social_recsys", None)
        agentes_con_engagement = set()
        if recsys and getattr(self, "fomento_engagement", True):
            for post in recsys.interest_recsys.posts.values():
                if post.likes > 3:
                    agentes_con_engagement.add(post.autor_id)
            if agentes_con_engagement:
                # Priorizar seguir a agentes con engagement
                agentes_engagement_list = [a for a in otros if a.unique_id in agentes_con_engagement]
                if agentes_engagement_list and random.random() < 0.4:
                    otro = random.choice(agentes_engagement_list)

        # Verificar si ya lo sigue
        siguiendo = self.get_following()
        if otro.unique_id not in siguiendo:
            self.social_follow(otro)
            # Log con contexto de engagement
            nombre_otro = otro.identidad.nombre if hasattr(otro, "identidad") and otro.identidad else otro.unique_id
            if getattr(self, "fomento_engagement", True) and otro.unique_id in agentes_con_engagement:
                self.modelo.log(
                    f"📡 [{self.unique_id}] Sigue a [{nombre_otro}] (engagement alto en sus posts)",
                    categoria="social",
                )

    def _ejecutar_comentario_aleatorio(self, target_post_id=None):
        """Comenta en un post específico o uno aleatorio del feed con contexto de hilo."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return

        if target_post_id:
            post_id = target_post_id
        else:
            posts = recsys.interest_recsys.posts
            if not posts: return
            post_ids = [pid for pid, p in posts.items() if p.autor_id != self.unique_id]
            if not post_ids: return
            import random
            post_id = random.choice(post_ids)

        target_post = recsys.interest_recsys.posts.get(post_id)
        if not target_post: return

        # Obtener comentarios existentes para dar contexto de hilo
        comentarios_hilo = recsys.interest_recsys.comentarios.get(post_id, [])
        contexto_hilo = ""
        if comentarios_hilo:
            contexto_hilo = "\nOtros comentarios en este hilo:\n"
            for c in comentarios_hilo[-3:]: # Ver últimos 3 comentarios
                contexto_hilo += f"- {c['autor_id']}: {c['contenido']}\n"

        # Buscar nombre del autor del post
        autor_post_nombre = target_post.autor_id
        for a in self.modelo.agentes:
            if a.unique_id == target_post.autor_id:
                autor_post_nombre = a.identidad.nombre or a.unique_id
                break

        # --- NUEVO: Hechos relevantes del mundo para comentarios ---
        hitos_texto = ""
        if hasattr(self.modelo, "historia") and self.modelo.historia:
            hitos = self.modelo.historia.obtener_resumen_hitos()
            if hitos and "No han ocurrido" not in hitos:
                hitos_texto = f"\n=== HECHOS RECIENTES EN EL MUNDO ===\n{hitos}\n"

        from agents.cerebro_llm import cerebro_llm
        ctx = (
            f'Estás viendo un post de {autor_post_nombre} que dice: "{target_post.contenido}".'
            f'{contexto_hilo}'
            f'{hitos_texto}'
            # MEJORA: Añadir lógica de engagement para motivar comentarios
            f'\\nEste post tiene {getattr(target_post, "likes", 0)} likes y {getattr(target_post, "comentarios", 0)} comentarios.'
            f'\\nParticipa en el debate para aumentar tu influencia social!'
            f'\\nEscribe una respuesta corta, natural y significativa. '
            f'Si hay otros comentarios, puedes construir sobre ellos o discrepan suavemente.'
            f'\\nOpcionalmente, haz una pregunta para continuar el hilo.'
        )

        respuesta = cerebro_llm.generar_comentario_social(self, target_post, ctx)
        if respuesta and len(respuesta) > 5:
            self.social_comment(post_id, respuesta)
            nombre_yo = self.identidad.nombre if self.identidad else self.unique_id
            self.modelo.log(
                f"💬 [{nombre_yo}] Comentó en el post de {autor_post_nombre}: {respuesta[:60]}...",
                categoria="social",
            )

    # === FIN MÉTODOS SOCIALES ===

    @synchronized
    def comerciar(self, otro_agente, tipo="compra"):
        """Realiza una transacción económica entre agentes."""
        # Precio base influenciado por el mercado global
        precio_mercado = float(self.modelo.precio_recurso_actual)

        if tipo == "compra":
            # Yo compro recursos a otro_agente
            cantidad = 3  # Reducido de 5 a 3
            costo = cantidad * precio_mercado
            if (
                self.dinero >= costo
                and otro_agente.recursos >= cantidad
                and (self.gasto_turno + costo) <= 30
            ):
                self.dinero -= costo
                self.gasto_turno += costo
                self.recursos += cantidad
                otro_agente.dinero += costo
                otro_agente.recursos -= cantidad
                self.modelo.log(
                    f"💰 [COMERCIO] Agente {self.unique_id} compró {cantidad} recursos a {otro_agente.unique_id} por {costo:.1f} MC.",
                    categoria="social",
                )
                self.modelo.notificar_cambio_estado()
                return True
        return False

    @synchronized
    def mejorar_seguridad(self):
        """Invierte dinero en mejorar el rango y la protección."""
        costo = 25.0  # Reducido de 50 a 25 para que sea viable con el límite de 30
        if self.dinero >= costo and (self.gasto_turno + costo) <= 30:
            self.dinero -= costo
            self.gasto_turno += costo
            self.rango += 0.2
            self.necesidades["seguridad"] = max(0, self.necesidades["seguridad"] - 5)
            self.modelo.log(
                f"🛡️ [SEGURIDAD] Agente {self.unique_id} invirtió en protección. Rango aumentado a {self.rango:.1f}.",
                categoria="state",
            )
            self.modelo.notificar_cambio_estado()
            return True
        return False

    @synchronized
    def invertir(self, monto):
        """El agente coloca dinero en el mercado para obtener retornos futuros."""
        if self.dinero >= monto and (self.gasto_turno + monto) <= 30:
            self.dinero -= monto
            self.gasto_turno += monto
            # Inversión a 5 pasos con un interés aleatorio entre -5% y +15%
            interes = random.uniform(-0.05, 0.15)
            self.inversiones.append(
                {
                    "monto": monto,
                    "paso_final": self.modelo.paso_actual + 5,
                    "interes": interes,
                }
            )
            self.modelo.log(
                f"📈 [INVERSIÓN] Agente {self.unique_id} invirtió {monto:.1f} MC en el mercado.",
                categoria="state",
            )
            self.modelo.notificar_cambio_estado()
            return True
        return False

    def actualizar_estado(self):
        """Actualiza las necesidades y recursos internos en cada paso."""
        # Producción pasiva aumentada para mayor resiliencia
        self.recursos += 0.5

        # Procesar inversiones terminadas
        for inv in list(self.inversiones):
            if self.modelo.paso_actual >= inv["paso_final"]:
                ganancia = inv["monto"] * (1 + inv["interes"])
                self.dinero += ganancia
                self.inversiones.remove(inv)
                resultado = "ganancia" if inv["interes"] > 0 else "pérdida"
                self.modelo.log(
                    f"💰 [RETORNO] Inversión de {self.unique_id} finalizada: {ganancia:.1f} MC ({resultado}).",
                    categoria="social",
                )

        # El metabolismo consume menos recursos si hay alimento almacenado
        consumo = 0.5 + ((10 - self.necesidades["alimento"]) * 0.03)
        self.recursos -= consumo
        self.inventario["comida"] = max(0, int(self.recursos))

        # Necesidades disminuyen (10=perfecto, 0=emergencia)
        # EL costo del terreno afecta el consumo de descanso y alimento
        tile = self.modelo.mapa[self.x][self.y]
        energy_mod = tile.energy_cost

        self.necesidades["alimento"] = max(
            0, self.necesidades["alimento"] - (0.04 + energy_mod * 0.1)
        )
        self.necesidades["social"] = max(0, self.necesidades["social"] - 0.03)
        self.necesidades["seguridad"] = max(0, self.necesidades["seguridad"] - 0.02)
        self.necesidades["descanso"] = max(
            0, self.necesidades["descanso"] - (0.05 + energy_mod)
        )
        self.necesidades["entretenimiento"] = max(
            0, self.necesidades["entretenimiento"] - 0.03
        )

        # Riesgo de salud por terreno hostil (Desert, Mountain)
        if tile.health_risk > 0 and random.random() < 0.1:
            self.recibir_daño(
                tile.health_risk * 2, f"clima hostil en {tile.terrain_type}"
            )

        # --- REGENERACIÓN PASIVA ---
        # Si el agente está bien alimentado y descansado (> 7), recupera salud
        if self.necesidades["alimento"] > 7.0 and self.necesidades["descanso"] > 7.0:
            self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 0.1)
            # Log sutil de bienestar solo de vez en cuando para no saturar
            if random.random() < 0.1:
                self.modelo.log(
                    f"✨ [BIENESTAR] Agente {self.unique_id} se está recuperando gracias a su buen estado.",
                    categoria="state",
                )

        # --- PROCESAMIENTO DE TRATADOS FORMALES ---
        for tratado in list(self.tratados):
            if not isinstance(tratado, dict):
                # Si por error hay un string (ej. bug de carga), lo ignoramos
                continue

            aliado = next(
                (
                    a
                    for a in self.modelo.agentes
                    if a.unique_id == tratado.get("socio_id")
                ),
                None,
            )
            if not aliado:
                continue

            t = tratado["terminos"]
            # 1. Intercambio de Recursos por Dinero
            if t.get("tipo") == "intercambio":
                dar = t.get("da", {})  # {recurso: "medicina", cant: 1}
                recibe = t.get("recibe", {})  # {recurso: "dinero", cant: 10}

                # Ejecutar si ambos tienen lo necesario
                puedo_dar = False
                if dar.get("recurso") == "medicina" and self.inventario[
                    "medicina"
                ] >= dar.get("cant", 0):
                    puedo_dar = True
                elif dar.get("recurso") == "dinero" and self.dinero >= dar.get(
                    "cant", 0
                ):
                    puedo_dar = True
                elif dar.get("recurso") == "recursos" and self.recursos >= dar.get(
                    "cant", 0
                ):
                    puedo_dar = True

                if puedo_dar:
                    # Transferir lo que yo doy
                    if dar["recurso"] == "medicina":
                        self.inventario["medicina"] -= dar["cant"]
                        aliado.inventario["medicina"] += dar["cant"]
                    elif dar["recurso"] == "dinero":
                        self.dinero -= dar["cant"]
                        aliado.dinero += dar["cant"]
                    elif dar["recurso"] == "recursos":
                        self.recursos -= dar["cant"]
                        aliado.recursos += dar["cant"]

                    # Transferir lo que yo recibo (si el aliado puede)
                    # Nota: Simplificado para que el aliado siempre cumpla su parte si el otro empezó
                    if recibe["recurso"] == "dinero":
                        aliado.dinero -= recibe["cant"]
                        self.dinero += recibe["cant"]
                    elif recibe["recurso"] == "seguridad":
                        self.rango += recibe["cant"]  # El aliado me brinda protección

                    self.modelo.log(
                        f"🤝 [EJECUCION TRATADO] Intercambio realizado entre {self.unique_id} y {aliado.unique_id}.",
                        categoria="social",
                    )

            # Reducir duración
            tratado["pasos_restantes"] -= 1
            if tratado["pasos_restantes"] <= 0:
                self.tratados.remove(tratado)
                # También quitar del aliado
                aliado.tratados = [
                    at for at in aliado.tratados if at["socio_id"] != self.unique_id
                ]
            self.modelo.log(
                f"⌛ [SISTEMA] El tratado entre {self.unique_id} y {aliado.unique_id} ha expirado.",
                categoria="sistema",
            )

        # --- DEGRADACIÓN DE SALUD POR NECESIDADES ---
        if self.necesidades["alimento"] < 2.0:
            daño_hambre = (2.0 - self.necesidades["alimento"]) * 0.5
            self.recibir_daño(daño_hambre, "hambre extrema")

        if self.necesidades["seguridad"] < 2.0:
            # En zonas inseguras hay riesgo de daño pasivo
            if random.random() < 0.1:
                self.recibir_daño(0.5, "inseguridad del entorno")

        if self.necesidades["salud"] <= 0:
            self.morir("agotamiento total de constantes vitales")
            return

        # --- VALIDACIÓN DE COORDENADAS ---
        # Asegurar que las coordenadas del agente estén dentro de los límites del mapa
        map_width = len(self.modelo.mapa)
        map_height = len(self.modelo.mapa[0]) if map_width > 0 else 0

        if self.x < 0 or self.x >= map_width or self.y < 0 or self.y >= map_height:
            # Ajustar coordenadas a los límites válidos
            self.x = max(0, min(self.x, map_width - 1))
            self.y = max(0, min(self.y, map_height - 1))
            self.modelo.log(
                f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas a ({self.x}, {self.y}) para estar dentro del mapa.",
                categoria="sistema",
            )

        # --- INSTINTO DE SUPERVIVENCIA AUTOMÁTICO ---
        tile = self.modelo.mapa[self.x][self.y]

        # 1. Alimentación automática si hay comida en el suelo y tiene hambre
        if (
            tile.resource_node
            and tile.resource_node["type"] == "food"
            and self.necesidades["alimento"] < 6.0
        ):
            comida_tomada = min(tile.resource_node["amount"], 2.0)
            tile.resource_node["amount"] -= comida_tomada
            self.necesidades["alimento"] = min(
                10, self.necesidades["alimento"] + (comida_tomada * 2)
            )
            self.modelo.log(
                f"🍎 [INSTINTO] Agente {self.unique_id} consumió alimento del terreno automáticamente.",
                categoria="alimentos",
            )
            if tile.resource_node["amount"] <= 0:
                tile.resource_node = None

        # 2. Uso de infraestructura (Hospitales y Centros de Recarga)
        for edif in tile.buildings:
            if (
                edif["tipo"].lower() in ["hospital", "clinica"]
                and self.necesidades["salud"] < 9.0
            ):
                self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 1.0)
                self.modelo.log(
                    f"🏥 [SISTEMA] Agente {self.unique_id} está siendo atendido en el Hospital.",
                    categoria="salud",
                )

            if "recarga" in edif["tipo"].lower() or "eléctrica" in edif["tipo"].lower():
                self.necesidades["descanso"] = min(
                    10.0, self.necesidades["descanso"] + 2.0
                )
                self.recursos += 1.0  # Carga de energía/recursos
                self.modelo.log(
                    f"⚡ [SISTEMA] Agente {self.unique_id} recargando constantes en estación energética.",
                    categoria="ambiente",
                )

    @synchronized
    def recibir_daño(self, cantidad, motivo="desconocido"):
        """Reduce la salud del agente y verifica si muere."""
        self.necesidades["salud"] -= cantidad
        self.modelo.log(
            f"🩸 [DAÑO] Agente {self.unique_id} ha recibido {cantidad:.1f} de daño por {motivo}. Salud restante: {self.necesidades['salud']:.1f}",
            categoria="salud",
        )
        if self.necesidades["salud"] <= 0:
            self.morir(motivo)

    def morir(self, motivo):
        """Finaliza la existencia del agente en la simulación."""
        if not self.esta_vivo:
            return

        self.esta_vivo = False
        self.modelo.log(
            f"🪦 [FUNERAL] El Agente {self.unique_id} ha MUERTO. Motivo: {motivo}.",
            categoria="sistema",
        )

        # Registro histórico si era importante
        if self.rol in ["Vocero", "Historiador", "Moderador"]:
            self.modelo.historia.agregar_hito(
                {
                    "turno": self.modelo.paso_actual,
                    "descripcion": f"Luto nacional: El {self.rol} {self.unique_id} ha fallecido por {motivo}.",
                    "tipo": "muerte",
                }
            )

        # Eliminar de la lista activa del modelo
        if self in self.modelo.agentes:
            self.modelo.agentes.remove(self)

        # Limpiar tratados y alianzas
        for aliado_id in list(self.alianzas):
            aliado = self.modelo.get_agent_by_id(aliado_id)
            if aliado and self.unique_id in aliado.alianzas:
                aliado.alianzas.remove(self.unique_id)

        # Registrar en DB si es posible
        if self.modelo.db_active:
            try:
                self.modelo.db.execute(
                    "UPDATE agentes SET reputacion = %s WHERE id = %s",
                    (0.0, self.unique_id),
                )
            except:
                pass

        # Notificar muerte inmediata para actualizar listas
        self.modelo.notificar_cambio_estado()

    @synchronized
    def recolectar(self):
        """El agente busca recursos en el entorno. Prioriza los nodos de recursos del mapa."""
        # Validar coordenadas antes de acceder al mapa
        map_width = len(self.modelo.mapa)
        map_height = len(self.modelo.mapa[0]) if map_width > 0 else 0

        if self.x < 0 or self.x >= map_width or self.y < 0 or self.y >= map_height:
            self.x = max(0, min(self.x, map_width - 1))
            self.y = max(0, min(self.y, map_height - 1))
            self.modelo.log(
                f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas en recolectar a ({self.x}, {self.y}).",
                categoria="sistema",
            )

        tile = self.modelo.mapa[self.x][self.y]
        mult = getattr(tile, "yield_mult", 1.0)

        # 1. Recolección de nodo específico
        if tile.resource_node and tile.resource_node["amount"] > 0:
            tipo = (tile.resource_node["type"] or "").lower()

            # Normalizar tipo (Soportar tanto nombres en Inglés como en Español del generador de terreno)
            if tipo in ["food", "comida", "alimento"]: tipo = "food"
            elif tipo in ["wood", "madera"]: tipo = "wood"
            elif tipo in ["stone", "piedra", "mineral", "hierro"]: tipo = "stone"
            elif tipo in ["medicine", "medicina", "hierbas"]: tipo = "medicine"
            elif tipo in ["fish", "pescado"]: tipo = "fish"
            elif tipo in ["gold", "oro"]: tipo = "gold"

            # Bonos específicos por terreno
            nodo_bonus = 1.0
            if tipo == "wood" and tile.terrain_type == TerrainType.FOREST:
                nodo_bonus = 2.0
            if tipo == "stone" and tile.terrain_type == TerrainType.MOUNTAIN:
                nodo_bonus = 2.0
            if tipo == "food" and tile.terrain_type == TerrainType.GRASS:
                nodo_bonus = 1.5

            cantidad = min(
                tile.resource_node["amount"],
                int(random.randint(5, 15) * mult * nodo_bonus),
            )
            tile.resource_node["amount"] -= cantidad

            if tipo == "food":
                self.recursos += cantidad
                self.inventario["comida"] = self.inventario.get("comida", 0) + cantidad
                self.modelo.log(
                    f"  🍎 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de ALIMENTO en {tile.terrain_type}.",
                    categoria="alimentos",
                )
                self.registrar_evento(f"He recolectado {cantidad} unidades de alimento.")
            elif tipo == "wood":
                self.recursos += cantidad * 0.5
                self.inventario["madera"] = self.inventario.get("madera", 0) + cantidad
                self.ganar_experiencia("ingenieria", 1)
                self.modelo.log(
                    f"  🪵 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de MADERA en {tile.terrain_type}.",
                    categoria="recursos",
                )
                self.registrar_evento(f"He recolectado {cantidad} unidades de madera.")
            elif tipo == "stone":
                self.recursos += cantidad * 0.5
                self.inventario["piedra"] = self.inventario.get("piedra", 0) + cantidad
                self.ganar_experiencia("ingenieria", 1)
                self.modelo.log(
                    f"  🪨 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de PIEDRA en {tile.terrain_type}.",
                    categoria="recursos",
                )
                self.registrar_evento(f"He recolectado {cantidad} unidades de piedra.")
            elif tipo == "medicine":
                self.inventario["medicina"] = self.inventario.get("medicina", 0) + 1
                self.ganar_experiencia("medicina", 1)
                self.modelo.log(
                    f"  🌿 Agente {self.unique_id} encontró HIERBAS MEDICINALES.",
                    categoria="recursos",
                )
            elif tipo == "fish":
                self.inventario["pescado"] = self.inventario.get("pescado", 0) + cantidad
                self.recursos += cantidad * 1.5
                self.modelo.log(
                    f"  🐟 Agente {self.unique_id} pescó {cantidad} unidades.",
                    categoria="alimentos",
                )
            elif tipo == "gold":
                self.dinero += cantidad * 2
                self.modelo.log(
                    f"  💰 Agente {self.unique_id} encontró vetas de ORO (+{cantidad * 2} MC).",
                    categoria="sistema",
                )
                self.registrar_evento(f"¡Increíble! He encontrado oro puro (+{cantidad * 2} MC).")

            if tile.resource_node["amount"] <= 0:
                tile.resource_node = None
                self.modelo.log(
                    f"  ⚠️ [RECOLECCION] El nodo de recursos en ({self.x}, {self.y}) se ha AGOTADO.",
                    categoria="ambiente",
                )
                self.registrar_evento(f"Los recursos en esta zona se han agotado. Tendré que buscar en otro lugar.")
            return

        # 2. Recolección genérica (baja eficiencia según terreno)
        r = random.random()

        if tile.terrain_type == TerrainType.FOREST:
            if r < 0.6:
                cant = random.uniform(3, 10) * mult
                self.inventario["madera"] = self.inventario.get("madera", 0) + int(cant)
                self.recursos += cant * 0.5
                self.modelo.log(
                    f"  🌲 Agente {self.unique_id} recolectó {int(cant)} de MADERA en el bosque.",
                    categoria="recursos",
                )
            else:
                self.inventario["medicina"] += 1
                self.ganar_experiencia("medicina", 1)
                self.modelo.log(
                    f"  🌿 Agente {self.unique_id} encontró HIERBAS MEDICINALES.",
                    categoria="recursos",
                )

        elif tile.terrain_type == TerrainType.MOUNTAIN:
            if r < 0.7:
                cant = random.uniform(2, 6) * mult
                self.inventario["piedra"] = self.inventario.get("piedra", 0) + int(cant)
                self.recursos += cant * 0.3
                self.modelo.log(
                    f"  🪨 Agente {self.unique_id} picó {int(cant)} de PIEDRA en la montaña.",
                    categoria="recursos",
                )
            else:
                self.inventario["hierro"] = self.inventario.get("hierro", 0) + 1
                self.modelo.log(
                    f"  ⛏️ Agente {self.unique_id} encontró una veta de HIERRO.",
                    categoria="recursos",
                )

        elif tile.terrain_type == TerrainType.WATER:
            cant = random.uniform(1, 4) * mult
            self.inventario["pescado"] = self.inventario.get("pescado", 0) + int(cant)
            self.recursos += cant * 1.5  # El pescado da mucha energía/recurso
            self.modelo.log(
                f"  🐟 Agente {self.unique_id} pescó {int(cant)} unidades.",
                categoria="alimentos",
            )

        else:  # Grassland o Desert
            cant = random.uniform(2, 8) * mult
            self.recursos += cant  # Alimento base
            self.inventario["comida"] = self.inventario.get("comida", 0) + int(cant)
            self.modelo.log(
                f"  🌱 Agente {self.unique_id} forrajeó {int(cant)} de alimento.",
                categoria="alimentos",
            )

        # Notificar cambio inmediato para visualización real-time en paneles
        self.modelo.notificar_cambio_estado()

    @synchronized
    def moverse(self, nuevo_x, nuevo_y):
        """Mueve al agente a una nueva posición directamente."""
        map_width = len(self.modelo.mapa)
        map_height = len(self.modelo.mapa[0]) if map_width > 0 else 0

        # Validar límites
        destino_x = max(0, min(nuevo_x, map_width - 1))
        destino_y = max(0, min(nuevo_y, map_height - 1))

        if destino_x == self.x and destino_y == self.y:
            return False

        # --- NUEVO: RESTRICCIÓN POR TERRITORIO ---
        tile_destino = self.modelo.mapa[destino_x][destino_y]
        propietario_tile = getattr(tile_destino, "owner_civ_id", None)

        if propietario_tile and propietario_tile != self.grupo_id:
            # Si el territorio pertenece a otro grupo, el agente no puede entrar.
            # (Excepción: si el agente no tiene grupo, tampoco puede entrar en territorio reclamado)
            self.modelo.log(
                f"🚫 [MOVIMIENTO] Agente {self.unique_id} no puede entrar en ({destino_x}, {destino_y}): Territorio de la facción {propietario_tile}.",
                categoria="movimiento",
            )
            return False

        self.x = destino_x
        self.y = destino_y
        
        # --- NUEVO: RECLAMACIÓN DE TERRITORIO ---
        if self.grupo_id and self.grupo_id in self.modelo.civilizaciones:
            civ = self.modelo.civilizaciones[self.grupo_id]
            pos = (self.x, self.y)
            if pos not in civ.territorio:
                civ.territorio.append(pos)
                # Actualizar el dueño en el mapa físico
                tile = self.modelo.mapa[self.x][self.y]
                if hasattr(tile, 'owner_civ_id'):
                    tile.owner_civ_id = self.grupo_id
                
                self.modelo.log(
                    f"🚩 [TERRITORIO] Agente {self.unique_id} ha reclamado ({self.x}, {self.y}) para {civ.nombre}.",
                    categoria="sistema",
                )
        
        region_name = self.modelo.world.get_region_name(self.x, self.y)
        self.modelo.log(
            f"🚶 [MOVIMIENTO] Agente {self.unique_id} se ha movido a ({self.x}, {self.y}) - {region_name}.",
            categoria="movimiento",
        )
        self.registrar_evento(f"He viajado hasta {region_name}.")
        self.modelo.notificar_cambio_estado()
        return True

    @synchronized
    def establecer_objetivo_movimiento(self, x, y):
        """Fija un destino para el movimiento del agente."""
        self.objetivo_movimiento = (x, y)
        self.modelo.log(
            f"🗺️ [NAVEGACION] Agente {self.unique_id} ha fijado un nuevo rumbo a ({x}, {y}).",
            categoria="movimiento",
        )

    @synchronized
    def ganar_experiencia(self, area, puntos=1):
        """Aumenta la experiencia en un área y verifica si puede graduarse."""
        if area in self.experiencia:
            self.experiencia[area] += puntos
            # Si llega a 5 de experiencia en un área y no tiene esa profesión, avisar
            if self.experiencia[area] == 5 and self.profesion is None:
                self.modelo.log(
                    f"🎓 [HITOS] Agente {self.unique_id} ha ganado suficiente experiencia en {area} para profesionalizarse.",
                    categoria="sistema",
                )

    @synchronized
    def construir(self, tipo_edificio="Centro de Descanso"):
        """Intenta construir un edificio en la posición actual."""
        if not self.esta_vivo:
            return False, "Agente muerto."
        res, msg = self.modelo.construir_edificio(self, tipo_edificio)
        if res:
            self.modelo.notificar_cambio_estado()
        return res, msg

    @synchronized
    def graduarse(self, profesion_deseada):
        """Intenta declarar una profesión si cumple los requisitos y está en una Universidad."""
        if self.profesion:
            return False, "Ya tienes una profesión."

        # Validar coordenadas antes de acceder al mapa
        map_width = len(self.modelo.mapa)
        map_height = len(self.modelo.mapa[0]) if map_width > 0 else 0

        if self.x < 0 or self.x >= map_width or self.y < 0 or self.y >= map_height:
            self.x = max(0, min(self.x, map_width - 1))
            self.y = max(0, min(self.y, map_height - 1))
            self.modelo.log(
                f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas en graduarse a ({self.x}, {self.y}).",
                categoria="sistema",
            )

        # VERIFICACIÓN DE UBICACIÓN: Debe haber una Universidad en el tile actual
        tile = self.modelo.mapa[self.x][self.y]
        tiene_universidad = any(b["tipo"] == "Universidad" for b in tile.buildings)

        if not tiene_universidad:
            return (
                False,
                "Debes estar en una Universidad para graduarte y obtener tu título oficial. 🏛️",
            )

        costos = {"Médico": 150, "Comerciante": 200, "Guarda": 100, "Explorador": 120}

        requisitos = {
            "Médico": self.experiencia["medicina"] >= 5
            and self.personalidad["amabilidad"] > 0.5,
            "Comerciante": self.experiencia["comercio"] >= 5,
            "Guarda": self.experiencia["combate"] >= 3
            and self.personalidad["hostilidad"] < 0.6,
            "Explorador": self.experiencia["exploracion"] >= 5,
        }

        if profesion_deseada not in costos:
            return False, "Profesión no válida."

        if not requisitos[profesion_deseada]:
            return (
                False,
                f"No cumples los requisitos de experiencia o personalidad para ser {profesion_deseada}.",
            )

        if self.dinero < costos[profesion_deseada]:
            return (
                False,
                f"Necesitas {costos[profesion_deseada]} MC para la licencia de {profesion_deseada}.",
            )

        # Éxito
        self.dinero -= costos[profesion_deseada]
        self.profesion = profesion_deseada
        self.hitos.append(f"Graduado como {profesion_deseada}")
        self.modelo.log(
            f"✨ [PROFESION] ¡El Agente {self.unique_id} se ha graduado como {profesion_deseada}! 🎓",
            categoria="consenso",
        )
        return True, f"¡Felicidades! Ahora eres {profesion_deseada}."

    # --- MÉTODOS POLÍTICOS ---
    @synchronized
    def proponer_ley(self, titulo, contenido, alcance="local"):
        """Propone una nueva ley para su facción o el mundo e inicia una asamblea."""
        # Si es global, cualquiera puede proponer si tiene prestigio, si es local debe tener facción
        gid = self.grupo_id if alcance == "local" else "GLOBAL"

        if alcance == "local" and not self.grupo_id:
            return False, "Debes pertenecer a una facción para proponer leyes locales."
        if alcance == "global" and self.rango < 0.0:
            return False, "Necesitas un rango positivo para proponer leyes globales."

        ley_id = f"LEY-{random.randint(1000, 9999)}"
        # Determinar el universo de votantes en este momento
        if alcance == "local":
            universo_votantes = [
                a
                for a in self.modelo.agentes
                if a.grupo_id == self.grupo_id and a.esta_vivo
            ]
        else:
            universo_votantes = [a for a in self.modelo.agentes if a.esta_vivo]

        total_requerido = len(universo_votantes)

        propuesta = {
            "id": ley_id,
            "autor": self.unique_id,
            "titulo": titulo,
            "contenido": contenido,
            "votos_si": 1,
            "votos_no": 0,
            "votantes": [self.unique_id],
            "estado": "pendiente",
            "grupo_id": gid,
            "alcance": alcance,
            "total_requerido": total_requerido,
            "paso_creacion": self.modelo.paso_actual,
        }

        if "propuestas" not in self.modelo.facciones_leyes:
            self.modelo.facciones_leyes["propuestas"] = []

        self.modelo.facciones_leyes["propuestas"].append(propuesta)

        # OASIS BRIDGE: Crear automáticamente una asamblea para esta propuesta
        nueva_asamblea = {
            "id": f"AS-{ley_id}",
            "tema": f"Propuesta de Ley: {titulo}",
            "descripcion": contenido,
            "estado": "DEBATE",
            "pasos_restantes": 3,  # 3 pasos de debate antes de votar
            "paso_inicio": self.modelo.paso_actual,
            "votos_si": 0,
            "votos_no": 0,
            "participantes_votos": {},
            "agente_turno_idx": 0,
            "grupo_id": gid,
            "proponente_id": self.unique_id,
            "ley_id": ley_id
        }
        self.modelo.asambleas_globales.append(nueva_asamblea)

        target_str = (
            f"en la Facción {self.grupo_id}" if alcance == "local" else "a nivel GLOBAL"
        )
        self.modelo.log(
            f"📜 [POLITICA] Agente {self.unique_id} ha PROPUESTO formalmente la ley: '{titulo}' {target_str} e iniciado una ASAMBLEA.",
            categoria="consenso",
        )
        self.modelo.notificar_cambio_estado()

        return True, ley_id

    @synchronized
    def votar_ley(self, ley_id, a_favor=True):
        """Vota una propuesta de ley existente."""
        propuestas = self.modelo.facciones_leyes.get("propuestas", [])
        for p in propuestas:
            if (
                p["id"] == ley_id
                or str(p.get("titulo", "")).lower() == str(ley_id).lower()
            ) and self.unique_id not in p["votantes"]:
                if a_favor:
                    p["votos_si"] += 1
                else:
                    p["votos_no"] += 1
                p["votantes"].append(self.unique_id)

                self.modelo.log(
                    f"🗳️ Agente {self.unique_id} votó {'A FAVOR' if a_favor else 'EN CONTRA'} de la ley '{p['titulo']}'.",
                    categoria="consenso",
                )
                self.modelo.notificar_cambio_estado()  # Notificar cambio para WebSocket
                return True
        return False

    @synchronized
    def postularse_candidato(self, grupo_id=None):
        """
        El agente se postula como candidato a vocero de su facción.

        Args:
            grupo_id: ID de la facción (si None, usa su propio grupo)

        Returns:
            (True, mensaje) si éxito, (False, motivo) si falla
        """
        gid = grupo_id or self.grupo_id
        if not gid:
            return False, "Debes pertenecer a una facción para postularte."
        if self.rol == "Vocero":
            return False, "Ya eres el vocero de tu facción."
        if gid not in self.modelo.civilizaciones:
            return False, f"La facción {gid} no existe."

        # Registrar postulación
        if not hasattr(self.modelo, 'candidatos_vocero'):
            self.modelo.candidatos_vocero = {}
        self.modelo.candidatos_vocero.setdefault(gid, []).append(self.unique_id)

        nombre_faccion = self.modelo.civilizaciones[gid].nombre
        self.modelo.log(
            f"🗳️ [CANDIDATURA] Agente {self.unique_id} se postuló como candidato a vocero de {nombre_faccion}",
            categoria="consenso"
        )
        self.modelo.notificar_cambio_estado()
        return True, "Postulación registrada."

    def sancionar(self, motivo, gravedad=0.1):
        """Reduce la reputación del agente por acciones indebidas."""
        self.reputacion = max(0.0, self.reputacion - gravedad)
        self.historial_etico.append(f"Sanción: {motivo} (-{gravedad})")
        self.modelo.log(
            f"⚖️ [JUSTICIA] Agente {self.unique_id} sancionado por: {motivo}. Reputación: {self.reputacion:.2f}",
            categoria="sistema",
        )

    def escribir_cronica(self, titulo, contenido):
        """Escribe una entrada formal en la historia del mundo."""
        if self.rol != "Historiador":
            return False, "Solo el Historiador puede escribir crónicas."

        # Registrar en la libreta
        self.modelo.historia.escribir_entrada(
            self.modelo.paso_actual,
            titulo,
            contenido,
            self.unique_id,
            categoria="general",
        )

        # Limpiar hitos pendientes ya narrados
        self.modelo.historia.limpiar_hitos()

        self.modelo.log(
            f"📚 [CRONICA] ¡Nueva entrada en los anales de la historia!: '{titulo}'",
            categoria="consenso",
        )
        self.modelo.notificar_cambio_estado()  # Para actualizar frontend
        return True, "Crónica escrita."

    def tick_bdi(self):
        """Un tick de simulación - ejecuta el ciclo BDI completo."""
        turno = self.modelo.paso_actual

        # FASE 1: Percibir y actualizar creencias
        self._bdi_percibir_entorno(turno)

        # FASE 2: Actualizar deseos based on beliefs and state
        self._bdi_revisar_deseos(turno)

        # FASE 3: Deliberar (generar y seleccionar planes)
        self._bdi_deliberar(turno)

        # FASE 4: Ejecutar acción del plan actual
        return self._bdi_ejecutar_plan(turno)

    def _bdi_percibir_entorno(self, turno: int):
        """Percibe el entorno y actualiza creencias."""
        # 1. Recursos cercanos
        tile = self.modelo.mapa[self.x][self.y]
        if tile.resource_node:
            prop = f"recurso_{tile.resource_node['type']}_disponible"
            self.creencias.actualizar_creencia(
                prop, 0.9 if tile.resource_node["amount"] > 0 else 0.1, 1.5, turno
            )

        # 2. Otros agentes
        cercanos = [
            a
            for a in self.modelo.agentes
            if a.unique_id != self.unique_id
            and abs(a.x - self.x) <= 2
            and abs(a.y - self.y) <= 2
        ]
        for otro in cercanos:
            # Creencia sobre confiabilidad basada en afinidad en memoria
            afinidad = (
                self.memoria.obtener_fuerza(otro.unique_id)
                if hasattr(self.memoria, "obtener_fuerza")
                else 0.0
            )
            self.creencias.actualizar_creencia(
                f"agente_{otro.unique_id}_confiable",
                0.5 + (afinidad / 20.0),
                1.2,
                turno,
            )
            # Registrar la percepción del otro agente en la memoria
            # Percepción básica: sabemos que existe y podemos estimar recursos y grupo
            tipo_relacion = "amigo" if afinidad > 0 else "conocido"
            self.memoria.registrar_interaccion(
                otro.unique_id,
                tipo_relacion,
                0.1,  # Fuerza pequeña positiva por percibir al agente
                getattr(otro, 'recursos', 0),
                getattr(otro, 'grupo_id', None)
            )

    def _bdi_ejecutar_plan(self, turno: int):
        """Ejecuta el siguiente paso del plan BDI actual."""
        if self.intenciones.plan_actual and self.intenciones.plan_actual.es_valido():
            plan = self.intenciones.plan_actual
            accion_bdi = plan.acciones[plan.tiempo_actual]
            plan.tiempo_actual += 1

            # Convertir AccionBDI a diccionario para el router
            return accion_bdi.to_dict()
        return None

    def _bdi_revisar_deseos(self, turno: int):
        """Revisa y actualiza deseos basado en necesidades vitales del agente."""
        # Estímulos dinámicos basados en estado vital
        hambre = self.necesidades.get("alimento", 5.0)
        salud = self.necesidades.get("salud", 5.0)
        social = self.necesidades.get("social", 5.0)

        # SUPERVIVENCIA: Se activa con hambre o salud baja
        if hambre < 4.0:
            self.deseos.deseos[TipoDeseo.SUPERVIVENCIA].actualizar_intensidad(0.25)
        elif hambre < 6.0:
            self.deseos.deseos[TipoDeseo.SUPERVIVENCIA].actualizar_intensidad(0.1)
        else:
            self.deseos.deseos[TipoDeseo.SUPERVIVENCIA].actualizar_intensidad(-0.05)

        if salud < 5.0:
            self.deseos.deseos[TipoDeseo.SUPERVIVENCIA].actualizar_intensidad(0.15)

        # RECURSOS: Deseo proporcional a riqueza actual
        if self.recursos < 50:
            self.deseos.deseos[TipoDeseo.RECURSOS].actualizar_intensidad(0.2)
        elif self.recursos > 200:
            self.deseos.deseos[TipoDeseo.RECURSOS].actualizar_intensidad(-0.1)
        else:
            self.deseos.deseos[TipoDeseo.RECURSOS].actualizar_intensidad(0.05)

        # ARMONÍA: Aumenta con necesidad social baja
        if social < 4.0:
            self.deseos.deseos[TipoDeseo.ARMONIA].actualizar_intensidad(0.15)
        elif social > 7.0:
            self.deseos.deseos[TipoDeseo.ARMONIA].actualizar_intensidad(-0.05)

        # ESTATUS: Crece lentamente con reputación alta
        if self.reputacion > 0.7:
            self.deseos.deseos[TipoDeseo.ESTATUS].actualizar_intensidad(0.08)
        elif self.reputacion < 0.3:
            self.deseos.deseos[TipoDeseo.ESTATUS].actualizar_intensidad(0.12)

        # Decaimiento natural hacia punto medio (evita estancamiento)
        for d in self.deseos.deseos.values():
            d.actualizar_intensidad(0)

        # ESTÍMULO DE DESEOS POLÍTICOS E INSTITUCIONALES
        # Estos deseos deben crecer cuando las necesidades básicas están cubiertas
        grupo_id = getattr(self, 'grupo_id', None)
        necesidades_cubiertas = hambre > 4.0 and salud > 4.0
        bastante_dinero = getattr(self, 'dinero', 0) >= 30
        muchos_dinero = getattr(self, 'dinero', 0) >= 80

        # LEGITIMIDAD: Crece cuando tiene grupo y recursos
        if grupo_id and bastante_dinero and necesidades_cubiertas:
            self.deseos.deseos[TipoDeseo.LEGITIMIDAD].actualizar_intensidad(0.15)
        elif grupo_id and necesidades_cubiertas:
            self.deseos.deseos[TipoDeseo.LEGITIMIDAD].actualizar_intensidad(0.05)

        # PODER_POLITICO: Crece fuerte cuando no tiene grupo pero tiene recursos
        if grupo_id is None and necesidades_cubiertas:
            if muchos_dinero:
                self.deseos.deseos[TipoDeseo.PODER_POLITICO].actualizar_intensidad(0.20)
            elif bastante_dinero:
                self.deseos.deseos[TipoDeseo.PODER_POLITICO].actualizar_intensidad(0.15)
        elif grupo_id and necesidades_cubiertas:
            # Con grupo, el deseo de crecer es invitación activa
            self.deseos.deseos[TipoDeseo.PODER_POLITICO].actualizar_intensidad(0.10)

        # LEGADO: Crece solo con grupo, recursos abundantes y estabilidad
        if grupo_id and muchos_dinero and necesidades_cubiertas:
            self.deseos.deseos[TipoDeseo.LEGADO].actualizar_intensidad(0.15)
        elif grupo_id and bastante_dinero and necesidades_cubiertas:
            self.deseos.deseos[TipoDeseo.LEGADO].actualizar_intensidad(0.08)

        # ASAMBLEA: Crece si hay grupo y necesita interacción
        if grupo_id and social < 6.0:
            self.deseos.deseos[TipoDeseo.ASAMBLEA].actualizar_intensidad(0.12)

        # Debug: log significant desire changes
        for tipo, deseo in self.deseos.deseos.items():
            if deseo.intensidad > 0.8:
                self.modelo.log(
                    f"🔥 [{self.unique_id}] Deseo {tipo.value} intensidad={deseo.intensidad:.2f}",
                    categoria="bdi"
                )

    def _bdi_deliberar(self, turno: int):
        """Fase de deliberación mejorada con estímulos de movimiento y objetivos."""
        if (
            self.intenciones.plan_actual is None
            or not self.intenciones.plan_actual.es_valido()
        ):
            # 1. Recopilar información del entorno extendido para alimentar al BDI
            agentes_todos = [a for a in self.modelo.agentes if a.unique_id != self.unique_id]
            
            # Amigos lejanos (afinidad > 5 y distancia > 4)
            amigos_lejos = []
            for a in agentes_todos:
                dist = abs(a.x - self.x) + abs(a.y - self.y)
                afinidad = self.memoria.obtener_fuerza(a.unique_id) if hasattr(self.memoria, 'obtener_fuerza') else 0
                if afinidad > 5 and dist > 4:
                    amigos_lejos.append({'id': a.unique_id, 'x': a.x, 'y': a.y, 'nombre': a.display_name})
            
            # Miembros de facción lejanos
            miembros_faccion = []
            if self.grupo_id:
                for a in agentes_todos:
                    if a.grupo_id == self.grupo_id:
                        dist = abs(a.x - self.x) + abs(a.y - self.y)
                        if dist > 4:
                            miembros_faccion.append({'id': a.unique_id, 'x': a.x, 'y': a.y})

            # Tiles interesantes según arquetipo y bioma (Minería, Bosque, etc)
            tiles_interesantes = []
            mapa = self.modelo.mapa
            map_size = len(mapa)
            # Muestreo aleatorio para encontrar biomas de interés sin costo O(N^2)
            for _ in range(40):
                rx, ry = random.randint(0, map_size-1), random.randint(0, map_size-1)
                tile = mapa[rx][ry]
                dist = abs(rx - self.x) + abs(ry - self.y)
                if dist < 2: continue
                
                interesante = False
                arq = getattr(self.alma, 'arquetipo', Arquetipo.EXPLORADOR)
                
                # Sitios arqueológicos: siempre interesantes para posibles descubrimientos
                if getattr(tile, 'is_archaeological_site', False):
                    interesante = True
                # Afinidad de biomas según arquetipo
                if arq == Arquetipo.EXPLORADOR and tile.terrain_type in [TerrainType.FOREST, TerrainType.WATER]: interesante = True
                elif arq in [Arquetipo.CONSTRUCTOR, Arquetipo.GUERRERO, Arquetipo.MERCADER] and tile.terrain_type == TerrainType.MOUNTAIN: interesante = True
                elif arq == Arquetipo.SANADOR and tile.terrain_type == TerrainType.FOREST: interesante = True
                elif tile.resource_node and tile.resource_node.get('amount', 0) > 0: interesante = True
                
                if interesante:
                    tiles_interesantes.append({'x': rx, 'y': ry, 'tipo': tile.terrain_type, 'dist': dist})
            
            tiles_interesantes.sort(key=lambda t: t['dist'])

            entorno = {
                "agentes_cercanos": [a for a in agentes_todos if abs(a.x - self.x) <= 2 and abs(a.y - self.y) <= 2],
                "agentes_lejos": [{'id': a.unique_id, 'x': a.x, 'y': a.y} for a in agentes_todos if abs(a.x - self.x) > 3 or abs(a.y - self.y) > 3],
                "amigos_lejos": amigos_lejos,
                "miembros_faccion_lejos": miembros_faccion,
                "tiles_interesantes": tiles_interesantes,
                # Todos los grupos disponibles con sus nombres para que los agentes puedan unirse/invitar conscientemente
                "grupos_disponibles": [
                    {"id": gid, "nombre": civ.nombre, "vocero": getattr(civ, "vocero_id", None), "miembros": len([a for a in agentes_todos if getattr(a, "grupo_id", None) == gid])}
                    for gid, civ in self.modelo.civilizaciones.items()
                ]
            }

            # 2. Intentar LLM primero
            decision_llm = None
            if (
                hasattr(self.modelo, "cerebro_llm")
                and self.modelo.cerebro_llm
                and getattr(self.modelo.cerebro_llm, "model", None)
            ):
                try:
                    decision_llm = self.modelo.cerebro_llm.generar_pensamiento_y_accion(
                        self, None, {"bdi_deliberar": True, "entorno": entorno}
                    )
                    
                    if decision_llm:
                        # Procesar herramientas si las hay
                        resultados_herramientas = decision_llm.get("resultados_herramientas", [])
                        if resultados_herramientas:
                            if not hasattr(self, "resultados_herramientas_recientes"):
                                self.resultados_herramientas_recientes = ""
                            contexto_herramientas = "\n".join([
                                f"- {r['herramienta']}: {r['resultado'][:200]}..."
                                for r in resultados_herramientas if r.get("exito", False)
                            ])
                            self.resultados_herramientas_recientes = f"Resultados recientes del sistema de skills evolutivas:\n{contexto_herramientas}"
                except Exception:
                    pass

            # 3. Fallback robusto al sistema BDI Heurístico
            # Si no hay plan actual o el LLM no ha asignado uno nuevo, usamos la lógica interna
            if self.intenciones.plan_actual is None or not self.intenciones.plan_actual.es_valido():
                planes_heuristicos = self.intenciones.generar_planes_candidatos(self, entorno)
                if planes_heuristicos:
                    mejor_plan = self.intenciones.seleccionar_mejor_plan(self, planes_heuristicos)
                    if mejor_plan:
                        self.intenciones.plan_actual = mejor_plan
                        # Log discreto para trazabilidad
                        # self.modelo.log(f"🧠 [BDI] {self.unique_id} plan heurístico: {mejor_plan.meta}", categoria="sistema")

    def actualizar_necesidades(self):
        """Mantenimiento básico de necesidades físicas sin toma de decisiones."""
        # Decremento natural
        self.necesidades["alimento"] = max(0.0, self.necesidades["alimento"] - 0.05)
        self.necesidades["salud"] = max(0.0, self.necesidades["salud"] - 0.02)
        self.necesidades["descanso"] = max(0.0, self.necesidades["descanso"] - 0.04)
        
        # Salud se recupera si está descansado y alimentado
        if self.necesidades["alimento"] > 8.0 and self.necesidades["descanso"] > 8.0:
            self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 0.05)
            
        # Morir si salud es 0
        if self.necesidades["salud"] <= 0 and self.esta_vivo:
            self.esta_vivo = False
            self.modelo.log(f"💀 El agente {self.unique_id} ha muerto por descuido vital.", "sistema")

    def step(self):
        """Paso de ejecución del agente."""
        if not self.esta_vivo:
            return
        self.realizar_turno()

    def realizar_turno(self):
        """Método principal de turno para el agente - delega al modelo para la lógica completa."""
        # Delegar toda la lógica compleja al modelo, pero desde el contexto del agente
        if hasattr(self.modelo, "_procesar_turno_agente"):
            self.modelo._procesar_turno_agente(self)
        else:
            # Fallback simple si el modelo no tiene el método avanzado
            self.tick_bdi()

    def ejecutar_accion_final(self, accion_dict: Dict[str, Any]):
        """
        Router maestro de acciones físicas.
        Mapea decisiones cognitivas a métodos de interacción con el mundo.
        """
        if not accion_dict:
            return False

        # El backend usa 'tipo', pero la API/Frontend puede enviar 'nombre'
        tipo = (accion_dict.get("tipo") or accion_dict.get("nombre") or "").lower().strip()
        
        # Normalizar tipo si viene de botones del frontend que usan nombres directos
        if tipo == "comunicar": tipo = "decir"
        # Normalizar alias de BDI/LLM
        if tipo == "curar": tipo = "curarse"
        if tipo == "intercambiar": tipo = "comerciar"
        if tipo == "ayudar": tipo = "socializar"
        if tipo in ["unirse_grupo", "unirse_faccion"]: tipo = "unirse_grupo"
        if tipo in ["abandonar_grupo", "abandonar_faccion"]: tipo = "abandonar_grupo"
        if tipo == "negociar_paz": tipo = "negociar_paz"
        if tipo in ["post", "publicar", "POST", "Post"]: tipo = "social_post"
        if tipo in ["comment", "comentar", "COMMENT", "Comment"]: tipo = "social_comment"
        if tipo in ["like", "LIKE", "Like"]: tipo = "social_like"
        if tipo in ["follow", "seguir", "FOLLOW", "Follow"]: tipo = "social_follow"
        if tipo in ["susurrar", "comunicar_privado", "mensaje_privado"]: tipo = "mensaje_privado"
        if tipo in ["fundar_faccion", "crear_grupo", "crear_faccion"]: tipo = "fundar_grupo"
        if tipo in ["fundar_asentamiento", "establecer_pueblo", "crear_pueblo"]: tipo = "fundar_pueblo"
        if tipo in ["invitar_a_grupo", "invitar_al_grupo", "invitar_agente", "invitar"]: tipo = "invitar_grupo"

        # Normalizaciones para acciones sobre Instituciones (unirse / usar)
        if tipo in ["unirse_institucion", "unirse_institución", "unirseinstitucion", "join_institution", "join_institucion"]:
            tipo = "unirse_institucion"
        if tipo in ["usar_institucion", "usar_institución", "usarinstitucion", "use_institution", "utilizar_institucion"]:
            tipo = "usar_institucion"
        if tipo in ["declarar_simpatia", "declarar_simpatía", "ser_simpatizante", "apoyar_grupo", "apoyar_faccion", "simpatizar"]:
            tipo = "declarar_simpatia"
        
        params = accion_dict.get("parametros", {}) or accion_dict.get("argumentos", {})
        if not isinstance(params, dict):
            params = {}

        try:
            # 1. Acciones de Recolección y Supervivencia
            if tipo in ["recolectar", "buscar_recursos"]:
                return self.recolectar()
            elif tipo == "cultivar":
                res = self.recolectar()
                self.inventario["comida"] = self.inventario.get("comida", 0) + 2
                self.modelo.log(f"🌱 {self.unique_id} ha cultivado la tierra y obtenido alimento.", categoria="info")
                return res
            elif tipo == "comer":
                res = self.comer()
                if res: self.registrar_evento("Me he alimentado para recuperar energías.")
                return res
            elif tipo == "cazar":
                # Si existe el método cazar, usarlo. Si no, fallback a recolectar.
                if hasattr(self, 'cazar'): 
                    res = self.cazar()
                    if res: self.registrar_evento("He salido de caza para obtener sustento.")
                    return res
                return self.recolectar()
            elif tipo == "curarse":
                self.necesidades["salud"] = min(10.0, self.necesidades.get("salud", 10.0) + 2.0)
                self.modelo.log(f"💊 {self.unique_id} se ha curado. Salud: {self.necesidades['salud']:.1f}/10", categoria="info")
                self.registrar_evento("He utilizado medicinas para sanar mis heridas.")
                return True
            elif tipo == "descansar":
                self.necesidades["descanso"] = min(
                    10.0, self.necesidades["descanso"] + 2.0
                )
                self.registrar_evento("Me he tomado un tiempo para descansar y recuperar fuerzas.")
                return True

            # 2. Acciones de Movimiento
            elif tipo in ["moverse", "mover"] or "ir_a" in tipo:
                # Soporte para direcciones cardinales (norte, sur, este, oeste)
                direccion = params.get("direccion", "").lower()
                dx, dy = 0, 0
                if direccion == "norte": dy = -1
                elif direccion == "sur": dy = 1
                elif direccion == "este": dx = 1
                elif direccion == "oeste": dx = -1
                
                if dx != 0 or dy != 0:
                    return self.moverse(self.x + dx, self.y + dy)
                
                # Soporte para destino específico x,y (desde BDI o LLM)
                # Si se provee destino, movemos un paso hacia él para estimular el "viaje"
                t_x = params.get("x")
                t_y = params.get("y")
                
                if t_x is not None and t_y is not None:
                    next_x, next_y = self.x, self.y
                    if t_x > self.x: next_x += 1
                    elif t_x < self.x: next_x -= 1
                    if t_y > self.y: next_y += 1
                    elif t_y < self.y: next_y -= 1
                    
                    # Si ya estamos en el destino o no hay cambio, movimiento errático leve
                    if next_x == self.x and next_y == self.y:
                        next_x += random.randint(-1, 1)
                        next_y += random.randint(-1, 1)
                    
                    return self.moverse(next_x, next_y)

                # Fallback: Movimiento aleatorio (el original)
                dest_x = self.x + random.randint(-1, 1)
                dest_y = self.y + random.randint(-1, 1)
                return self.moverse(dest_x, dest_y)
            elif tipo == "explorar":
                return self.explorar()

            # 3. Acciones Sociales y de Redes
            elif tipo in ["social_post", "social_create_post"]:
                contenido = params.get("contenido") or params.get("mensaje")
                if contenido:
                    return self.social_create_post(contenido)
                return self._ejecutar_accion_social_automatica(self.modelo.paso_actual)
            elif tipo == "social_comment":
                post_id = params.get("post_id")
                contenido = params.get("contenido") or params.get("mensaje")
                if post_id and contenido:
                    return self.social_comment(post_id, contenido)
                # Fallback a un comentario aleatorio
                self._ejecutar_comentario_aleatorio()
                return True
            elif tipo == "social_like":
                post_id = params.get("post_id")
                if post_id:
                    self.social_like(post_id)
                else:
                    self._ejecutar_like_aleatorio()
                self.necesidades["social"] = min(10.0, self.necesidades.get("social", 5.0) + 0.5)
                return True
            elif tipo == "social_follow":
                agente_id = params.get("agente_id") or params.get("target_id")
                if agente_id and hasattr(self, 'social_follow'):
                    self.social_follow(agente_id)
                self.necesidades["social"] = min(10.0, self.necesidades.get("social", 5.0) + 0.3)
                return True
            elif tipo == "socializar":
                # Buscar agente cercano para socializar
                target_id = params.get("target_id") or accion_dict.get("objetivo")
                if target_id:
                    target = self.modelo.get_agent_by_id(target_id)
                    if target and abs(target.x - self.x) <= 2 and abs(target.y - self.y) <= 2:
                        self.necesidades["social"] = min(10.0, self.necesidades["social"] + 2.0)
                        self.modelo.log(f"🤝 {self.unique_id} ha socializado con {target.unique_id}.", categoria="social")
                        nombre_target = target.identidad.nombre if hasattr(target, "identidad") else target.unique_id
                        self.registrar_evento(f"He tenido una charla interesante con {nombre_target}.")
                        return True
                for a in self.modelo.agentes:
                    if a.unique_id != self.unique_id and abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1:
                        self.necesidades["social"] = min(10.0, self.necesidades["social"] + 2.0)
                        self.modelo.log(f"🤝 {self.unique_id} ha socializado con {a.unique_id}.", categoria="social")
                        nombre_target = a.identidad.nombre if hasattr(a, "identidad") else a.unique_id
                        self.registrar_evento(f"He compartido un momento con {nombre_target}.")
                        return True
                self.modelo.log(f"🤝 {self.unique_id} buscó socializar pero está solo.", categoria="social")
                return False
            elif tipo == "formar_alianza":
                # Intentar con el agente más cercano
                for a in self.modelo.agentes:
                    if a.unique_id != self.unique_id and abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1:
                        res = self.formar_alianza(a)
                        if res:
                            self.modelo.log(f"🕯️ {self.unique_id} ha sellado una alianza con {a.unique_id}.", categoria="social")
                        return res
                return False
            elif tipo == "votar":
                voto = params.get("voto", "si").lower() == "si"
                # Votar en la asamblea actual si existe
                for asamblea in self.modelo.asambleas_activas:
                    if self.unique_id in asamblea.get("participantes", []):
                        return self.votar_ley(asamblea["ley_id"], a_favor=voto)
                return False
            elif tipo == "comerciar":
                target_id = params.get("target_id") or accion_dict.get("objetivo")
                if target_id:
                    target = self.modelo.get_agent_by_id(target_id)
                    if target:
                        return self.comerciar(target)
                # Si no hay target, comerciar con el más cercano
                for a in self.modelo.agentes:
                    if a.unique_id != self.unique_id and abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1:
                        return self.comerciar(a)
                self.modelo.log(f"💰 {self.unique_id} quiso comerciar, pero no hay nadie suficientemente cerca.", categoria="social")
                return False
            elif tipo == "consultar_mercado":
                precio = getattr(self.modelo, "precio_recurso_actual", 10.0)
                self.modelo.log(f"📈 Mercado Global: El precio actual del recurso es {precio:.1f} MC.", categoria="sistema")
                return True
            elif tipo == "negociar_paz":
                target_id = params.get("target_id") or accion_dict.get("objetivo")
                target = None
                if target_id:
                    target = self.modelo.get_agent_by_id(target_id)
                if not target:
                    # Buscar enemigo cercano
                    for a in self.modelo.agentes:
                        if a.unique_id != self.unique_id and abs(a.x - self.x) <= 2 and abs(a.y - self.y) <= 2:
                            rel = self.memoria.obtener_tipo(a.unique_id) if hasattr(self.memoria, 'obtener_tipo') else "desconocido"
                            if rel == "enemigo":
                                target = a
                                break
                if target:
                    if hasattr(self.memoria, 'set_tipo'):
                        self.memoria.set_tipo(target.unique_id, "neutral")
                    if hasattr(target.memoria, 'set_tipo'):
                        target.memoria.set_tipo(self.unique_id, "neutral")
                    self.necesidades["social"] = min(10.0, self.necesidades["social"] + 1.5)
                    self.modelo.log(f"🕊️ {self.unique_id} ha negociado la paz con {target.unique_id}.", categoria="social")
                    return True
                self.modelo.log(f"🕊️ {self.unique_id} quiso negociar paz pero no encontró enemigos cerca.", categoria="social")
                return False
                
            # 3.5 Acciones Políticas e Institucionales
            elif tipo == "fundar_grupo":
                nombre = params.get("nombre")
                desc = params.get("descripcion")
                
                if not nombre or not desc:
                    # Usar el cerebro LLM para generar una identidad descriptiva (Requerimiento de Memoria)
                    if hasattr(self.modelo, "cerebro_llm") and self.modelo.cerebro_llm:
                        # Intentar obtener miembros cercanos para dar contexto
                        cercanos = [a for a in self.modelo.agentes if a.unique_id != self.unique_id and abs(a.x - self.x) <= 3 and abs(a.y - self.y) <= 3]
                        nombres_miembros = [a.identidad.nombre for a in cercanos]
                        nombre_gen, desc_gen = self.modelo.cerebro_llm.generar_identidad_grupo(self, nombres_miembros)
                        if not nombre: nombre = nombre_gen
                        if not desc: desc = desc_gen
                
                # Fallback si falla el LLM o no hay
                if not nombre:
                    prefijos = ["Los Peregrinos de", "Orden de", "Sindicato de", "El Despertar de", "Renacer de"]
                    tema = getattr(self.identidad, "nombre", self.unique_id)
                    nombre = f"{random.choice(prefijos)} {tema}"
                if not desc:
                    desc = f"Un nuevo movimiento fundado por {self.unique_id} en busca del destino."

                res = self.fundar_grupo(nombre, desc)
                if res and res.get("exito"):
                    self.modelo.log(f"🏁 {self.unique_id} ha fundado la facción: {nombre}", categoria="sistema")
                    self.registrar_evento(f"¡Día histórico! He fundado una nueva facción: {nombre}.")
                    return True
                return False
            elif tipo == "fundar_pueblo":
                res_pueblo = self.fundar_pueblo()
                # fundar_pueblo devuelve (bool, msg)
                if isinstance(res_pueblo, tuple):
                    res, msg = res_pueblo
                else:
                    res, msg = res_pueblo, "Error desconocido"
                
                if not res:
                    self.modelo.log(f"🏘️ {self.unique_id} intentó fundar un pueblo pero falló: {msg}", categoria="info")
                return res
            elif tipo == "unirse_grupo":
                grupo_id = params.get("grupo_id") or params.get("faccion_id")
                nombre_grupo = params.get("nombre") or accion_dict.get("nombre")
                if not grupo_id and nombre_grupo:
                    # Buscar por nombre en civilizaciones
                    nombre_lower = str(nombre_grupo).lower()
                    for gid, civ in self.modelo.civilizaciones.items():
                        if civ.nombre.lower() == nombre_lower:
                            grupo_id = gid
                            break
                if not grupo_id:
                    # Intentar unirse a la facción del agente más cercano
                    for a in self.modelo.agentes:
                        if a.unique_id != self.unique_id and a.grupo_id and abs(a.x - self.x) <= 2 and abs(a.y - self.y) <= 2:
                            grupo_id = a.grupo_id
                            break
                if grupo_id and hasattr(self, 'unirse_a_grupo'):
                    res = self.unirse_a_grupo(grupo_id)
                    if res:
                        civ = self.modelo.civilizaciones.get(grupo_id)
                        nombre_c = civ.nombre if civ else grupo_id
                        self.registrar_evento(f"He decidido unirme a la facción {nombre_c}. Comienza una nueva etapa.")
                    return res
                elif grupo_id:
                    self.grupo_id = grupo_id
                    self.modelo.log(f"🏳️ {self.unique_id} se ha unido a la facción {grupo_id}.", categoria="social")
                    self.registrar_evento(f"Me he unido a la facción {grupo_id}.")
                    return True
                return False
            elif tipo == "abandonar_grupo":
                if self.grupo_id:
                    viejo = self.grupo_id
                    if hasattr(self, 'abandonar_grupo_actual'):
                        self.abandonar_grupo_actual()
                    else:
                        self.grupo_id = None
                    self.modelo.log(f"🚪 {self.unique_id} ha abandonado la facción {viejo}.", categoria="social")
                    return True
                return False
            elif tipo == "invitar_grupo":
                target_id = params.get("target_id") or params.get("agente_id") or accion_dict.get("objetivo")
                if target_id:
                    target = self.modelo.get_agent_by_id(target_id)
                    if target:
                        return self.invitar_agente(target)
                # Fallback: invitar al más cercano
                for a in self.modelo.agentes:
                    if a.unique_id != self.unique_id and a.grupo_id != self.grupo_id and abs(a.x - self.x) <= 2 and abs(a.y - self.y) <= 2:
                        return self.invitar_agente(a)
                return False
            elif tipo == "postularse_candidato":
                grupo_id = params.get("grupo_id", self.grupo_id)
                res, msg = self.postularse_candidato(grupo_id)
                return res
            elif tipo == "proponer_ley":
                titulo = params.get("titulo", "Propuesta sin título")
                contenido = params.get("contenido", "Sin contenido")
                alcance = params.get("alcance", "local")
                # `proponer_ley` puede devolver (bool, id) o (False, msg).
                # Normalizar a booleano para que el router siempre reciba True/False.
                res = self.proponer_ley(titulo, contenido, alcance)
                if isinstance(res, tuple):
                    return bool(res[0])
                return bool(res)
            elif tipo == "unirse_institucion":
                inst_id = params.get("institucion_id") or params.get("inst_id") or params.get("id") or params.get("nombre") or params.get("name")
                inst_obj = None
                if inst_id:
                    inst_obj = self.modelo.instituciones.get(str(inst_id))
                    if not inst_obj:
                        for iid, inst in self.modelo.instituciones.items():
                            if getattr(inst, "nombre", "").lower() == str(inst_id).lower():
                                inst_obj = inst
                                inst_id = iid
                                break
                else:
                    # Buscar institución en la casilla actual
                    for iid, inst in self.modelo.instituciones.items():
                        if inst.x == self.x and inst.y == self.y:
                            inst_obj = inst
                            inst_id = iid
                            break
                if not inst_obj:
                    self.modelo.log(f"🏛️ {self.unique_id} intentó unirse a una institución inexistente: {inst_id}", categoria="info")
                    return False
                if self.unique_id in inst_obj.miembros:
                    self.modelo.log(f"ℹ️ {self.unique_id} ya es miembro de '{inst_obj.nombre}'", categoria="info")
                    return False
                inst_obj.miembros.append(self.unique_id)
                # Otorgar puntos a la institución por nuevo miembro
                try:
                    inst_obj.puntos = getattr(inst_obj, "puntos", 0.0) + 10.0
                except Exception:
                    inst_obj.puntos = 10.0

                # Intentar subir de nivel si corresponde
                try:
                    self.modelo._maybe_level_institution(inst_obj)
                except Exception:
                    pass

                # Persistir si hay DB activa (incluye puntos/nivel)
                if getattr(self.modelo, "db_active", False) and getattr(self.modelo, "db", None):
                    try:
                        self.modelo.db.save_institution(inst_obj, self.modelo.user_id)
                    except Exception:
                        pass
                self.modelo.log(f"🤝 {self.unique_id} se ha unido a la institución '{inst_obj.nombre}' ({inst_id})", categoria="social")
                try:
                    self.modelo.notificar_cambio_estado()
                except Exception:
                    pass
                return True

            elif tipo == "usar_institucion":
                inst_id = params.get("institucion_id") or params.get("inst_id") or params.get("id") or params.get("nombre")
                inst_obj = None
                if inst_id:
                    inst_obj = self.modelo.instituciones.get(str(inst_id))
                    if not inst_obj:
                        for iid, inst in self.modelo.instituciones.items():
                            if getattr(inst, "nombre", "").lower() == str(inst_id).lower():
                                inst_obj = inst
                                break
                else:
                    for iid, inst in self.modelo.instituciones.items():
                        if inst.x == self.x and inst.y == self.y:
                            inst_obj = inst
                            break
                if not inst_obj:
                    self.modelo.log(f"🏛️ {self.unique_id} intentó usar una institución inexistente: {inst_id}", categoria="info")
                    return False
                tipo_inst = getattr(inst_obj, "tipo", "").lower()
                # Hospital: curar a cambio de una tarifa
                if tipo_inst in ["hospital", "sanitaria", "salud"]:
                    costo = params.get("costo", 10)
                    try:
                        costo = float(costo)
                    except Exception:
                        costo = 10
                    if self.dinero < costo:
                        return False
                    self.dinero -= costo
                    self.necesidades["salud"] = min(10.0, self.necesidades.get("salud", 0) + 3.0)
                    self.modelo.log(f"🏥 {self.unique_id} usó {inst_obj.nombre} y recuperó salud (+3). Costo: {costo} MC", categoria="salud")
                    # Institución gana puntos por servicio prestado
                    try:
                        inst_obj.puntos = getattr(inst_obj, "puntos", 0.0) + max(1.0, float(costo) * 0.5)
                    except Exception:
                        inst_obj.puntos = 1.0
                    try:
                        self.modelo._maybe_level_institution(inst_obj)
                    except Exception:
                        pass
                    return True
                # Universidad: ganar experiencia
                if tipo_inst in ["universidad", "educativa", "educacion"]:
                    costo = params.get("costo", 5)
                    try:
                        costo = float(costo)
                    except Exception:
                        costo = 5
                    if self.dinero < costo:
                        return False
                    self.dinero -= costo
                    self.ganar_experiencia("ingenieria", 5)
                    self.modelo.log(f"🎓 {self.unique_id} estudió en {inst_obj.nombre} y ganó XP.", categoria="educacion")
                    # Institución educativa gana puntos por estudiantes
                    try:
                        inst_obj.puntos = getattr(inst_obj, "puntos", 0.0) + 5.0
                    except Exception:
                        inst_obj.puntos = 5.0
                    try:
                        self.modelo._maybe_level_institution(inst_obj)
                    except Exception:
                        pass
                    return True
                # Banco: depositar recursos
                if tipo_inst in ["banco", "financiera", "economica"]:
                    cantidad = params.get("cantidad", min(10, self.dinero))
                    try:
                        cantidad = float(cantidad)
                    except Exception:
                        cantidad = 0.0
                    if cantidad <= 0 or self.dinero < cantidad:
                        return False
                    self.dinero -= cantidad
                    inst_obj.recursos = getattr(inst_obj, "recursos", 0.0) + cantidad
                    self.modelo.log(f"🏦 {self.unique_id} depositó {cantidad:.1f} MC en {inst_obj.nombre}.", categoria="economia")
                    # Banco obtiene puntos proporcional al depósito
                    try:
                        inst_obj.puntos = getattr(inst_obj, "puntos", 0.0) + (float(cantidad) / 10.0)
                    except Exception:
                        inst_obj.puntos = max(0.0, float(cantidad) / 10.0)
                    try:
                        self.modelo._maybe_level_institution(inst_obj)
                    except Exception:
                        pass
                    if getattr(self.modelo, "db_active", False) and getattr(self.modelo, "db", None):
                        try:
                            self.modelo.db.save_institution(inst_obj, self.modelo.user_id)
                        except Exception:
                            pass
                    return True
                # Generic use
                try:
                    inst_obj.puntos = getattr(inst_obj, "puntos", 0.0) + 2.0
                except Exception:
                    inst_obj.puntos = 2.0
                try:
                    self.modelo._maybe_level_institution(inst_obj)
                except Exception:
                    pass
                try:
                    self.modelo.log(f"🏛️ {self.unique_id} usó {inst_obj.nombre} (tipo {inst_obj.tipo}).", categoria="sistema")
                except Exception:
                    pass
                return True
            elif tipo == "fundar_institucion":
                tipo_inst = params.get("tipo", "Generica")
                nombre_inst = params.get("nombre", f"Instituto de {tipo_inst} de {self.unique_id}")
                exito, msg = self.fundar_institucion(nombre_inst, tipo_inst)
                if exito:
                    self.modelo.log(f"🏛️ {self.unique_id} {msg}", categoria="sistema")
                    self._registrar_memoria_episodica(
                        descripcion=f"He fundado una nueva institución: {nombre_inst} ({tipo_inst}).",
                        importancia=0.8,
                        emociones=["orgulloso", "ambicioso"]
                    )
                return exito

            # 4. Acciones de Construcción y Conocimiento
            elif tipo in ["construir", "constrir", "build"]:
                # Determinar tipo de edificio desde los parámetros
                edificio = params.get("tipo") or params.get("edificio") or params.get("nombre")
                if not edificio:
                    # Seleccionar edificio inteligente basado en necesidades del agente
                    nec = self.necesidades
                    if nec.get("alimento", 10) < 5:
                        edificio = "Granja"
                    elif nec.get("salud", 10) < 5:
                        edificio = "Farmacia"
                    elif nec.get("descanso", 10) < 4:
                        edificio = "Centro de Descanso"
                    elif nec.get("social", 10) < 4:
                        edificio = "Centro Comunitario"
                    else:
                        # Elegir algo basado en experiencia/profesión
                        if self.profesion == "Médico" or self.experiencia.get("medicina", 0) >= 5:
                            edificio = "Hospital"
                        elif self.experiencia.get("ingenieria", 0) >= 4:
                            tile = self.modelo.mapa[self.x][self.y]
                            if tile.terrain_type == TerrainType.MOUNTAIN:
                                edificio = "Mina"
                            else:
                                edificio = "Universidad"
                        else:
                            # Selección básica según terreno
                            tile = self.modelo.mapa[self.x][self.y]
                            if tile.terrain_type == TerrainType.MOUNTAIN:
                                # No puede construir nada sin ingeniería en montaña, pero para evitar bucle fallido:
                                self.modelo.log(f"⛰️ {self.unique_id} quiere construir en montaña pero no tiene conocimientos de ingeniería.", categoria="info")
                                return False
                            
                            edificio = random.choice(["Granja", "Centro de Descanso", "Centro Comunitario"])
                    self.modelo.log(f"🏗️ {self.unique_id} decide construir: {edificio} (auto-seleccionado según necesidades)", categoria="info")
                
                # Ejecutar la construcción física en el modelo
                exito, msg = self.modelo.construir_edificio(self, edificio)
                if exito:
                    self.modelo.log(f"🏗️ {self.unique_id} ha construido exitosamente: {edificio}", categoria="sistema")
                    self.registrar_evento(f"He terminado la construcción de un nuevo edificio: {edificio}.")
                    self._registrar_memoria_episodica(
                        descripcion=f"He terminado la construcción de un nuevo edificio: {edificio}.",
                        importancia=0.6,
                        emociones=["productivo"]
                    )
                else:
                    self.modelo.log(f"🏗️ {self.unique_id} intentó construir {edificio} pero falló: {msg}", categoria="info")
                return exito
            elif tipo == "investigar":
                res = self.investigar()
                normal_res = res[0] if isinstance(res, tuple) else res
                if normal_res:
                    self._registrar_memoria_episodica(
                        descripcion="He realizado una investigación científica para expandir mi conocimiento.",
                        importancia=0.5,
                        emociones=["curioso"]
                    )
                return normal_res
            elif tipo in ["estudiar", "educar"]:
                res = self.estudiar()
                return res[0] if isinstance(res, tuple) else res
            elif tipo == "reflexionar":
                self.ganar_experiencia("espiritualidad", 5)
                self.modelo.log(f"🧠 {self.unique_id} ha reflexionado profundamente.", categoria="info")
                return True
            elif tipo == "skill_factory" or "crear_herramienta" in tipo:
                if self.skill_manager:
                    res = self.skill_manager.ejecutar_accion_evolutiva(self, accion_dict)
                    return res.get("exito", False)
                return False
            elif tipo == "invertir":
                monto = params.get("monto", min(50, self.dinero * 0.3))
                if hasattr(self, 'invertir') and callable(self.invertir):
                    return self.invertir(monto)
                self.modelo.log(f"📊 {self.unique_id} intentó invertir pero no tiene capacidad aún.", categoria="info")
                return False

            # 4.5 Acciones de Comunicación (ya manejadas por la capa superior, pero necesarias como fallback)
            elif tipo in ["hablar", "decir", "comunicar_mensaje", "comunicar"]:
                mensaje = params.get("mensaje") or params.get("contenido")
                if mensaje:
                    self.decir(mensaje)
                return True
            elif tipo == "mensaje_privado":
                mensaje = params.get("mensaje") or params.get("contenido")
                target_id = params.get("target_id") or params.get("agente_id") or accion_dict.get("objetivo")
                if mensaje and target_id:
                    self.decir(mensaje, privado_para=target_id)
                    return True
                return False
            elif tipo == "observar":
                # Acción pasiva: ganar experiencia observando el entorno
                self.ganar_experiencia("ingenieria", 1)
                self.ganar_experiencia("exploración", 1)
                self.modelo.log(f"👁️ {self.unique_id} observa atentamente su entorno.", categoria="info")
                return True

            # 5. Acciones de Combate
            elif tipo in ["atacar", "combatir", "competir"]:
                target_id = params.get("target_id") or accion_dict.get("objetivo")
                if target_id:
                    target = self.modelo.get_agent_by_id(target_id)
                    if target:
                        return self.atacar(target)
                # Si no hay target, atacar al más cercano
                for a in self.modelo.agentes:
                    if a.unique_id != self.unique_id and abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1:
                        return self.atacar(a)
                return False

            # 6. Acciones de Herramientas/Skills (delegadas al skill_manager si aplica)
            elif tipo in ["web_search", "buscar_info", "scrapear_url", "ejecutar_codigo",
                          "crear_app", "crear_skill", "ejecutar_skill", "crear_habilidad"]:
                # Estas acciones son manejadas por el nodo ejecutar_herramientas de LangGraph.
                # Si llegan aquí como acción física, tratar de ejecutarlas como skill.
                if self.skill_manager:
                    try:
                        resultado = self.skill_manager.ejecutar_skill(
                            tipo,
                            params,
                            agente_id=self.unique_id,
                            agent_skills=self.skills,
                        )
                        if isinstance(resultado, dict) and resultado.get("error"):
                            self.modelo.log(f"🔧 {self.unique_id} ejecutó {tipo}: {resultado.get('error', 'error')}", categoria="info")
                            return False
                        self.modelo.log(f"🔧 {self.unique_id} ejecutó herramienta: {tipo}", categoria="info")
                        return True
                    except Exception as e_skill:
                        self.modelo.log(f"🔧 {self.unique_id} falló al ejecutar {tipo}: {e_skill}", categoria="info")
                        return False
                return False

            # 7. Acción de Posesión Divina (turno controlado por el Arquitecto)
            elif tipo in ["posesión_divina", "posesion_divina"]:
                return True  # Ya manejado externamente

            # 8. Acción exclusiva del Historiador
            elif tipo in ["escribir_cronica", "escribir_crónica"]:
                # Verificar que el agente sea Historiador
                if self.rol != "Historiador" and self.profesion != "Historiador":
                    self.modelo.log(
                        f"⛔ [HISTORIA] {self.unique_id} intentó escribir una crónica pero no es el Historiador.",
                        categoria="sistema",
                    )
                    return False
                titulo = params.get("titulo") or params.get("title") or f"Crónica del Turno {self.modelo.paso_actual}"
                contenido = params.get("contenido") or params.get("content") or params.get("texto") or ""
                if not contenido:
                    self.modelo.log(f"📝 [HISTORIA] {self.unique_id} quiso escribir crónica pero no proporcionó contenido.", categoria="info")
                    return False
                # Escribir en la libreta de historia
                exito, msg = self.escribir_cronica(titulo, contenido)
                if exito:
                    self.modelo.log(f"📜 [HISTORIA] {self.unique_id} escribió la crónica: '{titulo}'", categoria="historia")
                    # Publicar también en sistema_cronicas si existe
                    if hasattr(self.modelo, "sistema_cronicas"):
                        try:
                            from systems.cronicas import TipoCronica
                            ubic = (getattr(self, "x", None), getattr(self, "y", None))
                            self.modelo.sistema_cronicas.publicar_cronica(
                                autor_id=self.unique_id,
                                autor_nombre=getattr(self.identidad, "nombre", self.unique_id),
                                contenido=contenido,
                                tipo=TipoCronica.HISTORIA,
                                turno=self.modelo.paso_actual,
                                faccion=getattr(self, "civilizacion_id", "") or "",
                                ubicacion=ubic,
                            )
                        except Exception as e_cron:
                            self.modelo.log(f"⚠️ Error publicando crónica: {e_cron}", categoria="error")
                    if self.modelo.state_change_callback:
                        try:
                            self.modelo.state_change_callback()
                        except Exception:
                            pass
                
                # Log de integración Fase 4
                self.modelo.log(
                    f"🎯 [{self.unique_id}] acción={tipo} éxito={bool(exito)}",
                    categoria="accion"
                )
                return bool(exito)

            # === ACCIONES CONFLICTIVAS: Difamar, Sobornar, Sabotear ===
            elif tipo in ["difamar", "difamar_objetivo", "rumor", "difundir_rumor"]:
                objetivo_id = params.get("target_id") or params.get("objetivo") or accion_dict.get("objetivo")
                if objetivo_id:
                    objetivo = self.modelo.get_agent_by_id(objetivo_id)
                    if objetivo:
                        manip = self.personalidad.get("manipulacion", 0.5)
                        car = self.personalidad.get("carisma", 0.5)
                        fuerza = 0.15 + manip * 0.6 + car * 0.2
                        daño = fuerza * random.uniform(0.6, 1.25)
                        objetivo.reputacion = max(0.0, getattr(objetivo, "reputacion", 0.5) - daño)
                        try:
                            self.memoria.registrar_interaccion(objetivo.unique_id, "conflicto", -0.2, 0, objetivo.grupo_id)
                        except Exception:
                            pass
                        self.modelo.log(f"🗣️ [DIFAMAR] {self.unique_id} difamó a {objetivo.unique_id}. Reputación -{daño:.2f}", categoria="conflict")
                        if random.random() < (car * 0.15 + manip * 0.05):
                            self.capital_social = min(100, getattr(self, "capital_social", 10.0) + random.uniform(0.5, 2.0))
                        return True
                return False
            elif tipo in ["sobornar", "soborno", "pagar"]:
                objetivo_id = params.get("target_id") or params.get("objetivo")
                cantidad = float(params.get("cantidad", 5.0))
                if objetivo_id and self.dinero >= cantidad:
                    objetivo = self.modelo.get_agent_by_id(objetivo_id)
                    if objetivo:
                        self.dinero -= cantidad
                        objetivo.dinero = getattr(objetivo, "dinero", 0.0) + cantidad
                        try:
                            self.memoria.registrar_interaccion(objetivo.unique_id, "soborno", 0.0, cantidad, objetivo.grupo_id)
                            objetivo.memoria.registrar_interaccion(self.unique_id, "sobornado", 0.1, cantidad, self.grupo_id)
                        except Exception:
                            pass
                        self.modelo.log(f"💸 [SOBORNO] {self.unique_id} sobornó a {objetivo.unique_id} por {cantidad:.1f} MC", categoria="conflict")
                        return True
                return False
            elif tipo in ["sabote", "sabotear", "saboteo"]:
                objetivo_id = params.get("target_id") or params.get("objetivo")
                if objetivo_id:
                    objetivo = self.modelo.get_agent_by_id(objetivo_id)
                    if objetivo:
                        agres = self.personalidad.get("hostilidad", 0.5)
                        exito = random.random() < (0.2 + agres * 0.4)
                        if exito:
                            reduccion = max(1, int(agres * random.uniform(1, 5)))
                            objetivo.recursos = max(0, getattr(objetivo, "recursos", 0) - reduccion)
                            self.modelo.log(f"🛠️ [SABOTAJE] {self.unique_id} saboteó a {objetivo.unique_id}, recursos -{reduccion}", categoria="conflict")
                            return True
                        else:
                            self.modelo.log(f"⚠️ [SABOTAJE FALLIDO] {self.unique_id} intentó sabotar a {objetivo.unique_id} pero fracasó.", categoria="conflict")
                            return False
                return False

            # === FALLBACK: Acción no reconocida ===
            self.modelo.log(
                f"⚠️ [ACCIÓN DESCONOCIDA] {self.unique_id} intentó ejecutar '{tipo}' pero no existe handler. Realizando exploración en su lugar.",
                categoria="sistema"
            )
            # Ejecutar una acción útil como fallback en vez de no hacer nada
            return self.explorar()

        except Exception as e:
            self.modelo.log(
                f"❌ [ERROR ACCIÓN] {self.unique_id} falló al ejecutar '{tipo}': {e}",
                categoria="error"
            )
            return False


