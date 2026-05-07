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
    CURIOSIDAD = "curiosidad_digital"
    AUTONOMIA = "autonomia"
    REPRODUCCION = "reproduccion"
    # Deseos políticos e institucionales
    LEGITIMIDAD = "legitimidad"           # Deseo de reconocimiento y respeto formal
    PODER_POLITICO = "poder_politico"     # Deseo de influencia sobre otros
    LEGADO = "legado"                     # Deseo de crear algo que perdure
    ASAMBLEA = "participacion_asamblearia"  # Deseo de debatir y decidir colectivamente

class TipoAccion(Enum):
    """Acciones disponibles en el mundo (mapeadas a las existentes en el motor)"""
    # Supervivencia y Básicas
    MOVER = "MOVER"
    RECOLECTAR = "RECOLECTAR"
    COMER = "COMER"
    DESCANSAR = "DESCANSAR"
    CURAR = "CURARSE"
    EXPLORAR = "EXPLORAR"
    OBSERVAR = "OBSERVAR"

    # Económicas y Sociales
    INTERCAMBIAR = "COMERCIAR"
    COMERCIAR = "COMERCIAR"
    SOCIALIZAR = "SOCIALIZAR"
    ATACAR = "ATACAR"
    NEGOCIAR = "NEGOCIAR_PAZ"
    REFLEXIONAR = "REFLEXIONAR"

    # Políticas e Institucionales
    UNIRSE_FACCION = "UNIRSE_GRUPO"
    ABANDONAR_FACCION = "ABANDONAR_GRUPO"
    FUNDAR_FACCION = "FUNDAR_GRUPO"
    INVITAR = "INVITAR_GRUPO"
    VOTAR = "VOTAR"
    PROPONER_LEY = "PROPONER_LEY"
    FUNDAR_INSTITUCION = "FUNDAR_INSTITUCION"
    UNIRSE_INSTITUCION = "UNIRSE_INSTITUCION"
    USAR_INSTITUCION = "USAR_INSTITUCION"
    POSTULARSE_CANDIDATO = "POSTULARSE_CANDIDATO"

    # Construcción y Conocimiento
    CONSTRUIR = "CONSTRUIR"
    INVESTIGAR = "INVESTIGAR"
    ESTUDIAR = "ESTUDIAR"

    # Comunicación y Redes Sociales
    HABLAR = "HABLAR"
    SUSURRAR = "MENSAJE_PRIVADO"
    MENSAJE_PRIVADO = "MENSAJE_PRIVADO"
    SOCIAL_POST = "SOCIAL_POST"
    SOCIAL_LIKE = "SOCIAL_LIKE"
    SOCIAL_COMMENT = "SOCIAL_COMMENT"
    SOCIAL_FOLLOW = "SOCIAL_FOLLOW"

    # Acciones conflictivas y de influencia
    DIFAMAR = "DIFAMAR"
    PROPAGANDA = "PROPAGANDA"
    SOBORNAR = "SOBORNAR"
    SABOTEAR = "SABOTEAR"
    RECLUTAR = "RECLUTAR"

    # Herramientas y Skills Evolutivas
    WEB_SEARCH = "WEB_SEARCH"
    SCRAPEAR_URL = "SCRAPEAR_URL"
    EJECUTAR_CODIGO = "EJECUTAR_CODIGO"
    CREAR_APP = "CREAR_APP"
    CREAR_SKILL = "CREAR_SKILL"
    EJECUTAR_SKILL = "EJECUTAR_SKILL"
    CREAR_HABILIDAD = "CREAR_HABILIDAD"


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


def _is_unique_like(name: Optional[str]) -> bool:
    """Detecta ids tipo 'ag_...' que no son nombres legibles."""
    try:
        return isinstance(name, str) and name.startswith("ag_")
    except Exception:
        return False


def default_name_and_description(agente, arquetipo: Optional[str] = None, tipo_inst: Optional[str] = None) -> Tuple[str, str]:
    """Genera un nombre legible y una descripción por defecto cuando faltan datos.

    - Si el agente tiene `identidad.nombre` o `nombre_propio` (y no es un id tipo `ag_...`), los usa.
    - Si no, construye un nombre épico combinando sustantivos y adjetivos.
    - Cuando se pide `tipo_inst`, genera nombres apropiados para instituciones.
    Devuelve (nombre, descripcion).
    """
    identidad = getattr(agente, "identidad", None)
    base_name = None
    if identidad and getattr(identidad, "nombre", None):
        base_name = identidad.nombre
    elif getattr(agente, "nombre_propio", None):
        base_name = agente.nombre_propio

    if tipo_inst:
        # Nombres de instituciones: preferir 'Tipo de <nombre>' si hay un nombre base
        if base_name and not _is_unique_like(base_name):
            nombre = f"{tipo_inst} de {base_name}"
        else:
            opciones = ["Central", "Comunitario", "Regional", "Popular"]
            nombre = f"{tipo_inst} {random.choice(opciones)}"
        descripcion = f"Una {tipo_inst.lower()} creada por {base_name or agente.unique_id} para servir a la comunidad."
        return nombre, descripcion

    # Para grupos/facciones
    if base_name and not _is_unique_like(base_name):
        nombre = f"Clan de {base_name}"
    else:
        adjetivos = ["Valientes", "Eternos", "Sabios", "Libres", "Vigilantes", "Nobles", "Resilientes"]
        sustantivos = ["Horizonte", "Fuego", "Viento", "Destino", "Saber", "Guardia", "Aurora"]
        nombre = f"{random.choice(sustantivos)} de los {random.choice(adjetivos)}"

    arq_text = f" ({arquetipo})" if arquetipo else ""
    descripcion = f"Facción fundada por {base_name or agente.unique_id}{arq_text} dedicada a proteger y colaborar entre sus miembros."
    return nombre, descripcion

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
                for k, v in data["deseos"].items():
                    try:
                        tipo_val = v.get('tipo', k) if isinstance(v, dict) else k
                        sd.deseos[TipoDeseo(k)] = Deseo(
                            tipo=TipoDeseo(tipo_val),
                            intensidad=v.get('intensidad', 0.5) if isinstance(v, dict) else 0.5,
                            estabilidad=v.get('estabilidad', 0.9) if isinstance(v, dict) else 0.9
                        )
                    except (ValueError, KeyError, TypeError):
                        pass  # Skip corrupt desire entries
            if "pesos" in data:
                for k, v in data["pesos"].items():
                    try:
                        sd.pesos[TipoDeseo(k)] = float(v)
                    except (ValueError, KeyError, TypeError):
                        pass
        # Asegurar que los nuevos deseos siempre estén inicializados
        # (para agentes cargados de versiones anteriores)
        for tipo in TipoDeseo:
            if tipo not in sd.deseos:
                sd.deseos[tipo] = Deseo(tipo, intensidad=0.5)
            if tipo not in sd.pesos:
                sd.pesos[tipo] = 1.0
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
        elif tipo == TipoDeseo.PODER_POLITICO:
            # Normalizar poder político por rango e influencia social
            rango_norm = min(1.0, getattr(agente, 'rango', 1.0) / 10.0)
            influencia = min(1.0, getattr(agente, 'capital_social', 10.0) / 100.0)
            return (rango_norm + influencia) / 2.0
        elif tipo == TipoDeseo.LEGITIMIDAD:
            return getattr(agente, 'reputacion', 0.5)
        elif tipo == TipoDeseo.LEGADO:
            return min(1.0, getattr(agente, 'recursos', 0) / 1000.0)
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
        plan = cls(
            meta=data.get("meta", ""),
            prioridad=data.get("prioridad", 0.5),
            tiempo_maximo=data.get("tiempo_maximo", 10),
            tiempo_actual=data.get("tiempo_actual", 0)
        )
        acciones = []
        for a in data.get("acciones", []):
            try:
                # AccionBDI.to_dict() serializes tipo as "nombre", so check both
                tipo_raw = a.get("tipo") or a.get("nombre", "HABLAR")
                acciones.append(AccionBDI(
                    tipo=TipoAccion(tipo_raw),
                    objetivo=a.get("objetivo"),
                    parametros=a.get("parametros", a.get("argumentos", {})),
                    costo_estimado=a.get("costo_estimado", 1.0),
                    probabilidad_exito=a.get("probabilidad_exito", 0.8),
                    meta=a.get("meta", "")
                ))
            except (ValueError, KeyError, TypeError):
                pass  # Skip corrupt action entries
        plan.acciones = acciones
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

        # 4.5 PERTENENCIA / GRUPOS (Invitar y Unirse)
        try:
            agentes_cercanos = entorno.get('agentes_cercanos', [])

            # A. Aceptar invitaciones si hay una invitación reciente
            ultimo_msg = getattr(agente, 'ultimo_mensaje_recibido', None)
            if isinstance(ultimo_msg, dict):
                contenido = ultimo_msg.get('contenido', '')
                if contenido and contenido.startswith('INVITACION_GRUPO:'):
                    parts = contenido.split(':')
                    if len(parts) >= 2:
                        grupo_target = parts[1]
                        planes.append(PlanBDI(
                            acciones=[AccionBDI(TipoAccion.UNIRSE_FACCION, parametros={'grupo_id': grupo_target})],
                            meta=f"Aceptar invitación a {grupo_target}",
                            prioridad=1.0
                        ))

            # B. Unirse a grupos cercanos si no pertenece a ninguno
            if getattr(agente, 'grupo_id', None) is None and agentes_cercanos:
                grupos_disponibles = entorno.get('grupos_disponibles', [])
                grupos_cercanos = [a.grupo_id for a in agentes_cercanos if getattr(a, 'grupo_id', None)]
                if grupos_cercanos:
                    grupo_target = random.choice(list(set(grupos_cercanos)))
                    nombre_grupo = grupo_target
                    for g in grupos_disponibles:
                        if g['id'] == grupo_target:
                            nombre_grupo = g['nombre']
                            break
                    social_need = 1.0 - (social / 10.0)
                    prioridad = 0.4 + social_need * 0.6 * (0.5 + agente.personalidad.get('extroversión', 0.5) * 0.5)
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.UNIRSE_FACCION, parametros={'grupo_id': grupo_target})],
                        meta=f"Unirse al grupo cercano '{nombre_grupo}'",
                        prioridad=prioridad
                    ))

            # C. Invitar a agentes cercanos si pertenece a un grupo
            if getattr(agente, 'grupo_id', None) and agentes_cercanos:
                grupos_disponibles = entorno.get('grupos_disponibles', [])
                nombre_mi_grupo = agente.grupo_id
                for g in grupos_disponibles:
                    if g['id'] == agente.grupo_id:
                        nombre_mi_grupo = g['nombre']
                        break
                candidatos = [a for a in agentes_cercanos if a.grupo_id != agente.grupo_id]
                if candidatos:
                    propensity = agente.personalidad.get('lealtad', 0.5) * 0.5 + agente.personalidad.get('extroversión', 0.5) * 0.3
                    if propensity > 0.35:
                        target = random.choice(candidatos)
                        prioridad = 0.4 + propensity * 0.6
                        planes.append(PlanBDI(
                            acciones=[AccionBDI(TipoAccion.INVITAR, objetivo=target.unique_id)],
                            meta=f"Invitar a {target.unique_id} a '{nombre_mi_grupo}'",
                            prioridad=prioridad
                        ))
        except Exception:
            pass

        # 5. CONOCIMIENTO
        if TipoDeseo.CONOCIMIENTO in deseos:
            d = deseos[TipoDeseo.CONOCIMIENTO]
            w = pesos.get(TipoDeseo.CONOCIMIENTO, 1.0)
            planes.append(PlanBDI(
                acciones=[AccionBDI(TipoAccion.OBSERVAR)],
                meta="Observar para aprender",
                prioridad=d.intensidad * w * 0.5
            ))

        # 6. AUTONOMÍA / EXPLORACIÓN (Mejorado para estimular movimiento)
        if TipoDeseo.AUTONOMIA in deseos:
            d = deseos[TipoDeseo.AUTONOMIA]
            w = pesos.get(TipoDeseo.AUTONOMIA, 1.0)

            # A. Evitar hacinamiento (logic existente)
            if len(entorno.get('agentes_cercanos', [])) > 4:
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.MOVER)],
                    meta="Mover para evitar hacinamiento",
                    prioridad=d.intensidad * w * 0.4
                ))

            # B. Movimiento por AFINIDAD (Hacia amigos lejanos)
            amigos = entorno.get('amigos_lejos', [])
            if amigos:
                target = random.choice(amigos)
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.MOVER, parametros={'x': target['x'], 'y': target['y'], 'target_id': target['id']})],
                    meta=f"Buscar compañía de {target.get('nombre', 'un amigo')}",
                    prioridad=d.intensidad * w * 0.55
                ))

            # C. Movimiento por PERTENENCIA (Hacia el grupo / facción)
            miembros_faccion = entorno.get('miembros_faccion_lejos', [])
            if miembros_faccion:
                target = random.choice(miembros_faccion)
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.MOVER, parametros={'x': target['x'], 'y': target['y']})],
                    meta="Reunirse con miembros de su facción",
                    prioridad=d.intensidad * w * 0.5
                ))

            # D. Movimiento por OBJETIVOS (Biomas/Recursos de interés)
            # El modelo debe proveer 'tiles_interesantes' filtrados por el arquetipo/intereses del agente
            tiles_interes = entorno.get('tiles_interesantes', [])
            if tiles_interes:
                best_tile = random.choice(tiles_interes[:3]) # Elegir entre los 3 mejores
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.MOVER, parametros={'x': best_tile['x'], 'y': best_tile['y']})],
                    meta=f"Desplazarse hacia {best_tile['tipo']} por interés personal",
                    prioridad=d.intensidad * w * 0.65
                ))

        # 7. REPRODUCCIÓN (Satisface necesidad social)
        if TipoDeseo.REPRODUCCION in deseos:
            d = deseos[TipoDeseo.REPRODUCCION]
            w = pesos.get(TipoDeseo.REPRODUCCION, 1.0)
            social_need = 1.0 - (social / 10.0)
            if social_need > 0.4:
                agentes_cercanos = entorno.get('agentes_cercanos', [])
                if agentes_cercanos:
                    target = random.choice(agentes_cercanos)
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.HABLAR, objetivo=target.unique_id)],
                        meta="Buscar interacción social profunda",
                        prioridad=d.intensidad * w * social_need
                    ))
                else:
                    # Si no hay nadie cerca, moverse a buscar a alguien (Afinidad o cualquier agente lejos)
                    alguien_lejos = entorno.get('agentes_lejos', [])
                    if alguien_lejos:
                        target = random.choice(alguien_lejos)
                        planes.append(PlanBDI(
                            acciones=[AccionBDI(TipoAccion.MOVER, parametros={'x': target['x'], 'y': target['y']})],
                            meta="Explorar para encontrar otros agentes",
                            prioridad=d.intensidad * w * social_need * 0.8
                        ))

        # 8. CURIOSIDAD (navegación digital)
        if TipoDeseo.CURIOSIDAD in deseos:
            d = deseos[TipoDeseo.CURIOSIDAD]
            w = pesos.get(TipoDeseo.CURIOSIDAD, 1.0)
            planes.append(PlanBDI(
                acciones=[AccionBDI(TipoAccion.WEB_SEARCH, parametros={"query": "temas de interés actual"})],
                meta="Explorar internet para satisfacer curiosidad",
                prioridad=d.intensidad * w * 0.7
            ))

        # 9. LEGITIMIDAD - Proponer leyes para ganar reconocimiento formal
        # ACTIVACIÓN: si tiene necesidades básicas cubiertas, impulsa propuesta de leyes
        if TipoDeseo.LEGITIMIDAD in deseos:
            d = deseos[TipoDeseo.LEGITIMIDAD]
            w = pesos.get(TipoDeseo.LEGITIMIDAD, 1.0)
            grupo_id = getattr(agente, 'grupo_id', None)
            dinero = getattr(agente, 'dinero', 0.0)
            reputacion = getattr(agente, 'reputacion', 0.5)
            # Necesidades básicas relativamente cubiertas (puede pensar en política)
            necesidades_ok = alimento >= 3.0 and salud >= 3.0 and social >= 3.0
            # Propuestas locales: más permisivas (umbral de dinero reducido)
            if grupo_id and dinero >= 10 and necesidades_ok:
                # Prioridad ALTA para competir con supervivencia - proponer ley local
                # Añadir ligera estocasticidad para evitar patrones rígidos
                if random.random() < 0.95:
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.PROPONER_LEY, parametros={
                            'titulo': 'Ley de protección de recursos',
                            'contenido': 'Establecer normas para proteger los recursos compartidos del grupo.',
                            'alcance': 'local'
                        })],
                        meta="Proponer ley para ganar legitimidad en su grupo",
                        prioridad=0.78  # Ligeramente más alta para favorecer propuestas
                    ))
            # Propuestas globales: permitir con menor umbral y probabilidad moderada
            if dinero >= 50 and necesidades_ok and random.random() < 0.45:
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.PROPONER_LEY, parametros={
                        'titulo': 'Iniciativa de prosperidad general',
                        'contenido': 'Una ley para promover el desarrollo del mundo entero.',
                        'alcance': 'global'
                    })],
                    meta="Proponer ley global para ser reconocido mundialmente",
                    prioridad=0.72
                ))

            # 9.5 POSTULACIÓN A VOCERO (solo si ya tiene grupo)
            # Activar cuando: tiene grupo, reputación alta, y no es vocero actual
            if (grupo_id and 
                getattr(agente, 'rol', None) != 'Vocero' and 
                reputacion >= 0.6 and 
                dinero >= 20 and 
                necesidades_ok and 
                random.random() < 0.3):
                
                # Verificar que no haya postulación reciente
                ya_postulado = False
                if hasattr(agente.modelo, 'candidatos_vocero'):
                    ya_postulado = agente.unique_id in agente.modelo.candidatos_vocero.get(grupo_id, [])
                
                if not ya_postulado:
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.POSTULARSE_CANDIDATO, parametros={'grupo_id': grupo_id})],
                        meta="Postularse como candidato a vocero para incrementar influencia política",
                        prioridad=d.intensidad * w * 0.85
                    ))

        # 10. PODER_POLITICO - Fundar grupos y acumular miembros
        # Este es CRÍTICO - agentes sin grupo deben priorarlo inmediatamente
        if TipoDeseo.PODER_POLITICO in deseos:
            d = deseos[TipoDeseo.PODER_POLITICO]
            w = pesos.get(TipoDeseo.PODER_POLITICO, 1.0)
            grupo_id = getattr(agente, 'grupo_id', None)
            dinero = getattr(agente, 'dinero', 0.0)
            necesidades_ok = alimento > 3.0 and salud > 3.0

            if grupo_id is None and dinero >= 30 and necesidades_ok:
                # PRIORIDAD MUY ALTA: fundar grupo es la acción más importante sin grupo
                arquetipo = getattr(agente, 'arquetipo', 'Explorador')
                nombre_grupo, descripcion_default = default_name_and_description(agente, arquetipo=arquetipo)
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.FUNDAR_FACCION, parametros={
                        'nombre': nombre_grupo,
                        'descripcion': descripcion_default
                    })],
                    meta="Fundar una facción para acumular poder político",
                    prioridad=0.90  # Muy alta - necesita grupo para tener influencia
                ))

            # También priorizar UNIRSE a grupo si no tiene (no fundar)
            if grupo_id is None and dinero < 30 and necesidades_ok:
                # Sin dinero para fundar, buscar unirse a uno existente
                grupos_disponibles = entorno.get('grupos_disponibles', [])
                if grupos_disponibles:
                    # Seleccionar un grupo por nombre, no solo por ID
                    grupo_target_data = random.choice(grupos_disponibles)
                    grupo_target = grupo_target_data['id']
                    nombre_grupo = grupo_target_data['nombre']
                    prioridad = 0.85
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.UNIRSE_FACCION, parametros={'grupo_id': grupo_target})],
                        meta=f"Unirse al grupo '{nombre_grupo}' para tener influencia política",
                        prioridad=prioridad
                    ))

            if grupo_id and agentes_cercanos:
                # Ya tiene grupo: invitar miembros para crecer
                grupos_disponibles = entorno.get('grupos_disponibles', [])
                nombre_mi_grupo = grupo_id
                for g in grupos_disponibles:
                    if g['id'] == grupo_id:
                        nombre_mi_grupo = g['nombre']
                        break
                candidatos = [a for a in agentes_cercanos if getattr(a, 'grupo_id', None) != grupo_id]
                if candidatos:
                    target = random.choice(candidatos)
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.INVITAR, objetivo=target.unique_id)],
                        meta=f"Aumentar poder político de '{nombre_mi_grupo}' invitando a {target.unique_id}",
                        prioridad=0.80  # Alta prioridad - crece el grupo
                    ))

            # Si ya tiene grupo pero no es vocero, también puede postularse
            # para acelerar su influencia política directamente
            if (grupo_id and 
                getattr(agente, 'rol', None) != 'Vocero' and 
                dinero >= 30 and 
                necesidades_ok and
                random.random() < 0.2):
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.POSTULARSE_CANDIDATO, parametros={'grupo_id': grupo_id})],
                    meta="Postularse como candidato a vocero para ganar poder político",
                    prioridad=d.intensidad * w * 0.75
                ))

        # 11. LEGADO - Fundar instituciones duraderas
        if TipoDeseo.LEGADO in deseos:
            d = deseos[TipoDeseo.LEGADO]
            w = pesos.get(TipoDeseo.LEGADO, 1.0)
            grupo_id = getattr(agente, 'grupo_id', None)
            dinero = getattr(agente, 'dinero', 0.0)
            necesidades_ok = alimento > 4.0 and salud > 4.0
            # Una institución cuesta 100 MC - requiere estabilidad
            if grupo_id and dinero >= 100 and necesidades_ok:
                # Elegir tipo de institución según arquetipo
                arquetipo_nombre = getattr(agente, 'arquetipo', 'Explorador')
                if arquetipo_nombre == 'Sanador':
                    tipo_inst = 'Hospital'
                elif arquetipo_nombre == 'Sabio':
                    tipo_inst = 'Universidad'
                elif arquetipo_nombre == 'Mercader':
                    tipo_inst = 'Banco'
                else:
                    tipo_inst = random.choice(['Hospital', 'Universidad', 'Banco', 'Centro Comunitario'])
                nombre_inst = f"{agente.nombre_propio or agente.unique_id}'s {tipo_inst}"
                nombre_inst, _ = default_name_and_description(agente, tipo_inst=tipo_inst)
                planes.append(PlanBDI(
                    acciones=[AccionBDI(TipoAccion.FUNDAR_INSTITUCION, parametros={
                        'nombre': nombre_inst,
                        'tipo': tipo_inst
                    })],
                    meta=f"Crear una institución duradera: {tipo_inst}",
                    prioridad=0.72  # Alta prioridad - legado permanente
                ))

        # 12. ASAMBLEA - Participar en debates y votaciones
        if TipoDeseo.ASAMBLEA in deseos:
            d = deseos[TipoDeseo.ASAMBLEA]
            w = pesos.get(TipoDeseo.ASAMBLEA, 1.0)
            grupo_id = getattr(agente, 'grupo_id', None)
            if grupo_id:
                # En fase de asamblea, participar activamente
                hay_asamblea = entorno.get('hay_asamblea_faccion', False)
                if hay_asamblea:
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.VOTAR)],
                        meta="Participar en votación de asamblea",
                        prioridad=d.intensidad * w * 0.8
                    ))
                    # También puede proponer en la asamblea
                    planes.append(PlanBDI(
                        acciones=[AccionBDI(TipoAccion.PROPONER_LEY, parametros={
                            'titulo': 'Reforma necesaria',
                            'contenido': 'Es hora de actualizar nuestras reglas.',
                            'alcance': 'local'
                        })],
                        meta="Proponer ley en la asamblea",
                        prioridad=d.intensidad * w * 0.7
                    ))

        return planes
