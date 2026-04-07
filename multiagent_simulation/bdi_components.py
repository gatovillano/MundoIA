from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import random
import math

class TipoDeseo(Enum):
    """Categorías de deseos en simulación social"""
    SUPERVIVENCIA = "supervivencia"
    ESTATUS = "estatus_social"
    RECURSOS = "acumulacion_recursos"
    ARMONIA = "armonia_grupal"
    CONOCIMIENTO = "aprendizaje"
    AUTONOMIA = "autonomia"
    REPRODUCCION = "reproduccion"

class TipoAccion(Enum):
    """Acciones disponibles en el mundo (mapeadas a las existentes en el motor)"""
    MOVER = "MOVER"
    RECOLECTAR = "RECOLECTAR"
    INTERCAMBIAR = "COMERCIAR"
    ATACAR = "ATACAR"
    AYUDAR = "SOCIALIZAR"
    NEGOCIAR = "NEGOCIAR_PAZ"
    UNIRSE_FACCION = "UNIRSE_GRUPO"
    ABANDONAR_FACCION = "ABANDONAR_GRUPO"
    FUNDAR_FACCION = "FUNDAR_GRUPO"
    OBSERVAR = "OBSERVAR"
    DESCANSAR = "DESCANSAR"
    COMER = "COMER"
    CURAR = "CURAR"
    HABLAR = "HABLAR"

@dataclass
class Credencia:
    """Una creencia individual del agente"""
    proposicion: str                    # Ej: "el_agua_es_contaminada", "vecino_X_es_confiable"
    probabilidad: float = 0.5          # Valor entre 0.0 y 1.0
    fuerza: float = 1.0               # Cuánto influye esta creencia (0.5-2.0)
    fuente: str = "inicial"            # Cómo se adquirió: "inicial", "observacion", "testimonio", "inferencia"
    ultimo_update: int = 0             # Turno del último update

    def to_dict(self):
        return {
            "proposicion": self.proposicion,
            "probabilidad": self.probabilidad,
            "fuerza": self.fuerza,
            "fuente": self.fuente,
            "ultimo_update": self.ultimo_update
        }

@dataclass
class SistemaCreencias:
    """Conjunto de creencias de un agente"""
    creencias: Dict[str, Credencia] = field(default_factory=dict)
    
    def to_dict(self):
        return {k: v.to_dict() for k, v in self.creencias.items()}
    
    @classmethod
    def from_dict(cls, data):
        sc = cls()
        if data:
            sc.creencias = {k: Credencia(**v) for k, v in data.items()}
        return sc
    
    def get_creencia(self, proposicion: str) -> float:
        """Retorna probabilidad de una proposición (default 0.5 si no existe)"""
        if proposicion not in self.creencias:
            self.creencias[proposicion] = Credencia(proposicion)
        return self.creencias[proposicion].probabilidad
    
    def actualizar_creencia(self, proposicion: str, evidencia: float, 
                            fuerza_fuente: float = 1.0, turno_actual: int = 0):
        """Actualización bayesiana simple de creencias."""
        if proposicion not in self.creencias:
            self.creencias[proposicion] = Credencia(proposicion)
        
        c = self.creencias[proposicion]
        
        # Actualización bayesiana simplificada
        normalizador = (evidencia * c.probabilidad * fuerza_fuente + 
                       (1 - evidencia) * (1 - c.probabilidad) * (2 - fuerza_fuente))
        
        if normalizador > 0:
            nueva_prob = (evidencia * c.probabilidad * fuerza_fuente) / normalizador
            c.probabilidad = 0.3 * c.probabilidad + 0.7 * nueva_prob  # Suavizado
        
        c.fuerza = min(2.0, c.fuerza + 0.05 * fuerza_fuente)
        c.ultimo_update = turno_actual
    
    def get_proposiciones_relevantes(self, umbral_prob: float = 0.6) -> List[str]:
        """Retorna creencias con probabilidad alta o baja"""
        return [p for p, c in self.creencias.items() 
                if c.probabilidad > umbral_prob or c.probabilidad < (1 - umbral_prob)]

@dataclass
class Deseo:
    """Un deseo individual con prioridad dinámica"""
    tipo: TipoDeseo
    intensidad: float = 0.5           # 0.0 a 1.0, cuán fuerte es el deseo AHORA
    estabilidad: float = 0.9         # Cuánto resiste al cambio (0.5-1.0)
    
    def to_dict(self):
        return {
            "tipo": self.tipo.value,
            "intensidad": self.intensidad,
            "estabilidad": self.estabilidad
        }

    def actualizar_intensidad(self, cambio: float):
        """Actualiza intensidad con decaimiento y cambio"""
        decaimiento = (self.intensidad - 0.5) * 0.1
        self.intensidad -= decaimiento
        self.intensidad = max(0.0, min(1.0, self.intensidad + cambio))

@dataclass
class SistemaDeseos:
    """Conjunto de deseos con función de utilidad multi-dimensional"""
    deseos: Dict[TipoDeseo, Deseo] = field(default_factory=dict)
    pesos: Dict[TipoDeseo, float] = field(default_factory=dict)  # Importancia relativa
    
    def to_dict(self):
        return {
            "deseos": {k.value: v.to_dict() for k, v in self.deseos.items()},
            "pesos": {k.value: v for k, v in self.pesos.items()}
        }
    
    @classmethod
    def from_dict(cls, data):
        sd = cls()
        if data:
            if "deseos" in data:
                sd.deseos = {TipoDeseo(k): Deseo(tipo=TipoDeseo(v['tipo']), intensidad=v['intensidad'], estabilidad=v['estabilidad']) for k, v in data["deseos"].items()}
            if "pesos" in data:
                sd.pesos = {TipoDeseo(k): v for k, v in data["pesos"].items()}
        return sd

    def __post_init__(self):
        for tipo in TipoDeseo:
            if tipo not in self.deseos:
                self.deseos[tipo] = Deseo(tipo, intensidad=0.5)
            if tipo not in self.pesos:
                self.pesos[tipo] = 1.0
    
    def calcular_utilidad(self, agente: Any) -> float:
        utilidad_total = 0.0
        peso_total = sum(self.pesos.values())
        for tipo, deseo in self.deseos.items():
            util = self._utilidad_por_tipo(tipo, agente)
            peso = self.pesos[tipo] * deseo.intensidad
            utilidad_total += util * peso
        return utilidad_total / peso_total if peso_total > 0 else 0.0
    
    def _utilidad_por_tipo(self, tipo: TipoDeseo, agente: Any) -> float:
        if tipo == TipoDeseo.SUPERVIVENCIA:
            salud = agente.necesidades.get("salud", 5.0) / 10.0
            alimento = agente.necesidades.get("alimento", 5.0) / 10.0
            return (salud + alimento) / 2.0
        elif tipo == TipoDeseo.RECURSOS:
            return min(1.0, agente.recursos / 500.0)
        elif tipo == TipoDeseo.ESTATUS:
            return agente.reputacion
        elif tipo == TipoDeseo.ARMONIA:
            relaciones = list(agente.memoria.grafo.neighbors(agente.unique_id))
            return min(1.0, len(relaciones) / 10.0) if relaciones else 0.5
        return 0.5

@dataclass
class AccionBDI:
    """Una acción individual en el modelo BDI"""
    tipo: TipoAccion
    objetivo: Optional[str] = None
    parametros: Dict = field(default_factory=dict)
    costo_estimado: float = 1.0
    probabilidad_exito: float = 0.8
    meta: str = ""

    def to_dict(self):
        return {
            "nombre": self.tipo.value,
            "objetivo": self.objetivo,
            "argumentos": self.parametros,
            "costo_estimado": self.costo_estimado,
            "probabilidad_exito": self.probabilidad_exito,
            "meta": self.meta
        }

@dataclass
class PlanBDI:
    """Un plan de acciones para alcanzar una intención"""
    acciones: List[AccionBDI] = field(default_factory=list)
    meta: str = ""
    prioridad: float = 0.5
    tiempo_maximo: int = 10
    tiempo_actual: int = 0
    
    def to_dict(self):
        return {
            "acciones": [a.to_dict() for a in self.acciones],
            "meta": self.meta,
            "prioridad": self.prioridad,
            "tiempo_maximo": self.tiempo_maximo,
            "tiempo_actual": self.tiempo_actual
        }
    
    @classmethod
    def from_dict(cls, data):
        if not data: return None
        plan = cls(meta=data.get("meta", ""), prioridad=data.get("prioridad", 0.5), tiempo_maximo=data.get("tiempo_maximo", 10), tiempo_actual=data.get("tiempo_actual", 0))
        plan.acciones = [AccionBDI(tipo=TipoAccion(a["tipo"]), objetivo=a.get("objetivo"), parametros=a.get("parametros", {}), costo_estimado=a.get("costo_estimado", 1.0), probabilidad_exito=a.get("probabilidad_exito", 0.8), meta=a.get("meta", "")) for a in data.get("acciones", [])]
        return plan

    def es_valido(self) -> bool:
        return self.tiempo_actual < self.tiempo_maximo and self.tiempo_actual < len(self.acciones)

@dataclass
class SistemaIntenciones:
    """Sistema de intenciones y planificación"""
    plan_actual: Optional[PlanBDI] = None
    historial_planes: List[PlanBDI] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "plan_actual": self.plan_actual.to_dict() if self.plan_actual else None,
            "historial_planes": [p.to_dict() for p in self.historial_planes]
        }
    
    @classmethod
    def from_dict(cls, data):
        si = cls()
        if data:
            si.plan_actual = PlanBDI.from_dict(data.get("plan_actual"))
            si.historial_planes = [PlanBDI.from_dict(p) for p in data.get("historial_planes", [])]
        return si

    def seleccionar_mejor_plan(self, agente: Any, planes_candidatos: List[PlanBDI]) -> Optional[PlanBDI]:
        if not planes_candidatos: return None
        planes_validos = [p for p in planes_candidatos if p.es_valido()]
        if not planes_validos: return None
        return max(planes_validos, key=lambda p: p.prioridad)

    def generar_planes_candidatos(self, agente: Any, entorno: Dict) -> List[PlanBDI]:
        """
        Genera planes candidatos basados en deseos activos y estado del agente.
        Considera múltiples dimensiones BDI y asigna prioridades dinámicas.
        """
        planes = []
        necesidades = getattr(agente, 'necesidades', {})
        deseos_sistema = getattr(agente, 'deseos', None)
        if deseos_sistema is None:
            return planes
        deseos = deseos_sistema.deseos
        pesos = deseos_sistema.pesos

        # Valores de necesidades con defaults (escala 0-10)
        alimento = necesidades.get('alimento', 5.0)
        salud = necesidades.get('salud', 5.0)
        social = necesidades.get('social', 5.0)
        # pueden usarse luego: seguridad, descanso, entretenimiento

        # 1. SUPERVIVENCIA (alimento y salud)
        if TipoDeseo.SUPERVIVENCIA in deseos:
            d = deseos[TipoDeseo.SUPERVIVENCIA]
            w = pesos.get(TipoDeseo.SUPERVIVENCIA, 1.0)
            # Hambre
            if alimento < 4.0:
                inventario = getattr(agente, 'inventario', {})
                if inventario.get('comida', 0) > 0:
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.COMER)],
                        meta="Comer para sobrevivir",
                        prioridad=d.intensidad * w * (1.0 - alimento/10.0)
                    ))
                else:
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.RECOLECTAR)],
                        meta="Buscar comida",
                        prioridad=d.intensidad * w * (1.0 - alimento/10.0)
                    ))
            # Salud
            if salud < 4.0:
                inventario = getattr(agente, 'inventario', {})
                tiene_medicina = any(('medicine' in k.lower() or 'medicina' in k.lower()) for k in inventario.keys())
                if tiene_medicina:
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.CURAR)],
                        meta="Curarse",
                        prioridad=d.intensidad * w * (1.0 - salud/10.0)
                    ))
                else:
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.DESCANSAR)],
                        meta="Descansar para recuperar salud",
                        prioridad=d.intensidad * w * (1.0 - salud/10.0)
                    ))

        # 2. ESTATUS (reputación)
        if TipoDeseo.ESTATUS in deseos:
            d = deseos[TipoDeseo.ESTATUS]
            w = pesos.get(TipoDeseo.ESTATUS, 1.0)
            reputacion = getattr(agente, 'reputacion', 0.5)
            estatus_need = 1.0 - reputacion
            if estatus_need > 0.3:
                agentes_cercanos = entorno.get('agentes_cercanos', [])
                if agentes_cercanos:
                    target = random.choice(agentes_cercanos)
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.HABLAR, objetivo=target.unique_id)],
                        meta="Mejorar estatus social",
                        prioridad=d.intensidad * w * estatus_need
                    ))

        # 3. RECURSOS (dinero y recursos materiales)
        if TipoDeseo.RECURSOS in deseos:
            d = deseos[TipoDeseo.RECURSOS]
            w = pesos.get(TipoDeseo.RECURSOS, 1.0)
            recursos = getattr(agente, 'recursos', 0.0)
            dinero = getattr(agente, 'dinero', 0.0)
            res_need = 1.0 - min(1.0, recursos / 500.0)
            dinero_need = 1.0 - min(1.0, dinero / 1000.0)
            need = max(res_need, dinero_need)
            if need > 0.3:
                if recursos < 200:
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.RECOLECTAR)],
                        meta="Recolectar recursos",
                        prioridad=d.intensidad * w * need
                    ))
                else:
                    agentes_cercanos = entorno.get('agentes_cercanos', [])
                    if agentes_cercanos:
                        target = random.choice(agentes_cercanos)
                        planes.append(PlanBDI(
                            acciones=[AccionBDI(TipoAccion.INTERCAMBIAR, objetivo=target.unique_id)],
                            meta="Comerciar para obtener recursos",
                            prioridad=d.intensidad * w * need * 0.7
                        ))

        # 4. ARMONÍA (social) - basado en necesidad social
        if TipoDeseo.ARMONIA in deseos:
            d = deseos[TipoDeseo.ARMONIA]
            w = pesos.get(TipoDeseo.ARMONIA, 1.0)
            social_need = 1.0 - (social / 10.0)
            if social_need > 0.3:
                agentes_cercanos = entorno.get('agentes_cercanos', [])
                if agentes_cercanos:
                    target = random.choice(agentes_cercanos)
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.AYUDAR, objetivo=target.unique_id)],
                        meta="Ayudar para armonía grupal",
                        prioridad=d.intensidad * w * social_need
                    ))
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.HABLAR, objetivo=target.unique_id)],
                        meta="Socializar para armonía",
                        prioridad=d.intensidad * w * social_need * 0.8
                    ))

        # 5. CONOCIMIENTO
        if TipoDeseo.CONOCIMIENTO in deseos:
            d = deseos[TipoDeseo.CONOCIMIENTO]
            w = pesos.get(TipoDeseo.CONOCIMIENTO, 1.0)
            planes.append(PlanBDI(
                acciones=[AccionBDI(TipoAccion.OBSERVAR)],
                meta="Observar para aprender",
                prioridad=d.intensidad * w * 0.5
            ))

        # 6. AUTONOMÍA
        if TipoDeseo.AUTONOMIA in deseos:
            d = deseos[TipoDeseo.AUTONOMIA]
            w = pesos.get(TipoDeseo.AUTONOMIA, 1.0)
            if len(entorno.get('agentes_cercanos', [])) > 3:
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.MOVER)],
                    meta="Mover para autonomía",
                    prioridad=d.intensidad * w * 0.6
                ))

        # 7. REPRODUCCIÓN
        if TipoDeseo.REPRODUCCION in deseos:
            d = deseos[TipoDeseo.REPRODUCCION]
            w = pesos.get(TipoDeseo.REPRODUCCION, 1.0)
            if social < 7.0:
                agentes_cercanos = entorno.get('agentes_cercanos', [])
                if agentes_cercanos:
                    target = random.choice(agentes_cercanos)
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.HABLAR, objetivo=target.unique_id)],
                        meta="Buscar compañía",
                        prioridad=d.intensidad * w * (1.0 - social/10.0)
                    ))

        return planes
