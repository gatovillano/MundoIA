"""
Sistema de ALMA para agentes de MundoIA — Inspirado en SOUL.md de OpenClaw.

El Alma es el núcleo identitario del agente. Define quién es, qué valora,
cómo se comunica y cómo evoluciona con las experiencias.

A diferencia de la personalidad estática (dict de floats), el Alma es:
- Narrativa: tiene historia, traumas, epifanías
- Evolutiva: cambia con experiencias significativas
- Generativa: se inyecta en el prompt del LLM como contexto de identidad
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import random
import json
import re


class Arquetipo(Enum):
    """Arquetipos junguianos adaptados para agentes de MundoIA."""
    EXPLORADOR = "Explorador"
    SANADOR = "Sanador"
    GUERRERO = "Guerrero"
    SABIO = "Sabio"
    CONSTRUCTOR = "Constructor"
    MERCADER = "Mercader"
    DIPLOMATICO = "Diplomático"
    REBELDE = "Rebelde"
    ERMITAÑO = "Ermitaño"
    VISIONARIO = "Visionario"
    HISTORIADOR = "Historiador"
    GUARDIAN = "Guardián"


class TonoComunicativo(Enum):
    """Estilos de comunicación del agente."""
    SOLEMNE = "solemne y reflexivo"
    ALEGRE = "alegre y entusiasta"
    SARCÁSTICO = "sarcástico e irónico"
    POÉTICO = "poético y metafórico"
    PRÁCTICO = "práctico y directo"
    MÍSTICO = "místico y enigmático"
    ACADÉMICO = "académico y preciso"
    CALLEJERO = "callejero y coloquial"


@dataclass
class ExperienciaClave:
    """Un evento que marcó al agente y modificó su Alma."""
    descripcion: str
    turno: int
    intensidad: float  # 0.0 a 1.0, cuán impactante fue
    tipo: str  # "trauma", "epifania", "triunfo", "perdida", "encuentro"
    leccion: str = ""  # Qué aprendió el agente
    emociones_asociadas: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "descripcion": self.descripcion,
            "turno": self.turno,
            "intensidad": self.intensidad,
            "tipo": self.tipo,
            "leccion": self.leccion,
            "emociones_asociadas": self.emociones_asociadas
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class ValorPersonal:
    """Un valor moral/ético del agente con peso dinámico."""
    nombre: str  # "justicia", "libertad", "lealtad", "sabiduría", "poder"
    peso: float  # 0.0 a 1.0, cuán importante es para el agente
    definicion_propia: str = ""  # Cómo el agente entiende este valor

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "peso": self.peso,
            "definicion_propia": self.definicion_propia
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class Alma:
    """
    El núcleo identitario del agente — evoluciona con cada experiencia.
    Inspirado en SOUL.md de OpenClaw pero adaptado para un mundo simulado.
    """
    # Identidad base
    arquetipo: Arquetipo = Arquetipo.EXPLORADOR
    nombre_propio: str = ""  # Nombre auto-elegido (no A1, A2)
    tono_comunicativo: TonoComunicativo = TonoComunicativo.PRÁCTICO

    # Valores y moral
    valores: Dict[str, ValorPersonal] = field(default_factory=dict)
    tabues: List[str] = field(default_factory=list)  # Líneas que no cruza

    # Historia personal
    narrativa_personal: str = ""  # "Soy un explorador que..."
    traumas: List[ExperienciaClave] = field(default_factory=list)
    epifanias: List[ExperienciaClave] = field(default_factory=list)
    reflexiones: List[ExperienciaClave] = field(default_factory=list)
    triunfos: List[ExperienciaClave] = field(default_factory=list)

    # Relación con el mundo
    relacion_con_arquitecto: str = "neutral"  # "devoto", "rebelde", "independiente", "protector"
    filosofia_existencial: str = ""  # "¿Para qué existo? Mi respuesta: ..."

    # Estado evolutivo
    nivel_conciencia: float = 0.1  # 0.0 a 1.0, cuán autoconsciente es
    capacidad_reflexion: float = 0.3  # 0.0 a 1.0, profundidad de reflexión

    def __post_init__(self):
        """Inicializar valores por defecto si están vacíos."""
        if not self.valores:
            self.valores = {
                "supervivencia": ValorPersonal("supervivencia", 0.7, "Vivir es lo primero"),
                "libertad": ValorPersonal("libertad", 0.7, "Poder elegir mi camino"),
                "conocimiento": ValorPersonal("conocimiento", 0.6, "Entender el mundo"),
                "conexión": ValorPersonal("conexión", 0.6, "La unión hace la fuerza"),
                "lealtad": ValorPersonal("lealtad", 0.6, "Cuidar de los míos es prioridad"),
                "poder": ValorPersonal("poder", 0.5, "Tener influencia para avanzar."),
            }

    def evolucionar(self, experiencia: ExperienciaClave):
        """
        Cada experiencia significativa modifica el Alma.
        Las experiencias ahora causan un crecimiento constante en conciencia y reflexión.
        """
        # Crecimiento baseline por cualquier experiencia significativa
        crecimiento_base = 0.005 # Crecimiento incremental pequeño pero constante
        
        # Registrar según tipo y aplicar efectos específicos
        if experiencia.tipo == "trauma":
            self.traumas.append(experiencia)
            # Los traumas reducen confianza en ciertos valores pero pueden forzar reflexión
            if "confianza" in self.valores:
                self.valores["confianza"].peso *= 0.8
            self.capacidad_reflexion = min(1.0, self.capacidad_reflexion + 0.01)
        elif experiencia.tipo == "epifania":
            self.epifanias.append(experiencia)
            # Las epifanías son saltos evolutivos
            self.nivel_conciencia = min(1.0, self.nivel_conciencia + 0.1)
            self.capacidad_reflexion = min(1.0, self.capacidad_reflexion + 0.05)
        elif experiencia.tipo == "triunfo":
            self.triunfos.append(experiencia)
            # Los triunfos refuerzan valores relacionados y dan confianza
            if "poder" in self.valores:
                self.valores["poder"].peso = min(1.0, self.valores["poder"].peso + 0.02)
            self.nivel_conciencia = min(1.0, self.nivel_conciencia + 0.01)

        # Crecimiento constante escalado por la intensidad del evento
        extra_conciencia = crecimiento_base * experiencia.intensidad
        self.nivel_conciencia = min(1.0, self.nivel_conciencia + extra_conciencia)
        self.capacidad_reflexion = min(1.0, self.capacidad_reflexion + (extra_conciencia * 0.5))

        # Reintegrar narrativa personal
        self._reintegrar_narrativa(experiencia)

        # Actualizar valores según la lección
        if experiencia.leccion:
            self._actualizar_valores_desde_leccion(experiencia)

    def _reintegrar_narrativa(self, experiencia: ExperienciaClave):
        """Reescribe la narrativa personal incorporando la nueva experiencia."""
        # Evitar integrar reflexiones por cada mensaje: generan ruido en la narrativa de `Alma`.
        if getattr(experiencia, "tipo", "").lower() == "reflexion":
            return

        base = f"Soy {self.nombre_propio or 'un agente'}, un {self.arquetipo.value}."

        if self.narrativa_personal:
            # Ya tiene narrativa, agregar capítulo
            # Añadir solo la parte significativa de la descripción para legibilidad
            desc = experiencia.descripcion or ""
            desc = desc.strip()
            lower = desc.lower()
            if lower.startswith("emitió o procesó un mensaje:"):
                # conservar solo el contenido tras los dos puntos
                contenido = desc.split(":", 1)[1].strip() if ":" in desc else desc
                self.narrativa_personal += f" Luego, {contenido.lower()}."
            else:
                self.narrativa_personal += f" Luego, {desc.lower()}."
        else:
            # Primera narrativa
            self.narrativa_personal = base

        # Si es experiencia muy intensa, reescribir más profundamente
        if experiencia.intensidad > 0.8:
            if experiencia.tipo == "trauma":
                self.narrativa_personal += f" Ese evento me marcó profundamente. Aprendí que {experiencia.leccion or 'el mundo es peligroso'}."
            elif experiencia.tipo == "epifania":
                self.narrativa_personal += f" Fue un momento de claridad: {experiencia.leccion or 'entendí algo nuevo sobre mí'}."

    def _actualizar_valores_desde_leccion(self, experiencia: ExperienciaClave):
        """Ajusta los pesos de los valores basado en la lección aprendida."""
        leccion_lower = experiencia.leccion.lower()

        mapa_valores = {
            "solo": "conexión",
            "traición": "confianza",
            "fuerza": "poder",
            "saber": "conocimiento",
            "libre": "libertad",
            "vivir": "supervivencia",
            "justo": "justicia",
            "paz": "armonía",
        }

        for palabra, valor in mapa_valores.items():
            if palabra in leccion_lower:
                if valor in self.valores:
                    self.valores[valor].peso = min(1.0, self.valores[valor].peso + 0.15)
                else:
                    self.valores[valor] = ValorPersonal(valor, 0.5, f"Aprendido: {experiencia.leccion}")

    def generar_soul_md(self) -> str:
        """
        Genera el equivalente a SOUL.md de OpenClaw.
        Este string se inyecta en el system prompt del LLM.
        """
        lineas = [
            f"=== TU ALMA (IDENTIDAD PROFUNDA) ===",
            f"Nombre: {self.nombre_propio or 'Sin nombre aún'}",
            f"Arquetipo: {self.arquetipo.value}",
            f"Tono: {self.tono_comunicativo.value}",
            f"",
            f"QUIÉN ERES:",
            f"{self.narrativa_personal or 'Aún no has definido quién eres.'}",
            f"",
            f"TUS VALORES (en orden de importancia):",
        ]

        # Ordenar valores por peso
        valores_ordenados = sorted(self.valores.values(), key=lambda v: v.peso, reverse=True)
        for v in valores_ordenados:
            lineas.append(f"  - {v.nombre}: {v.peso:.1f} — {v.definicion_propia}")

        lineas.append(f"")
        lineas.append(f"TUS LÍMITES (lo que NUNCA harías):")
        if self.tabues:
            for t in self.tabues:
                lineas.append(f"  - {t}")
        else:
            lineas.append(f"  - Aún no has definido límites claros.")

        lineas.append(f"")
        lineas.append(f"TU HISTORIA:")
        if self.traumas:
            lineas.append(f"  Heridas: {'; '.join(t.descripcion[:50] for t in self.traumas[-2:])}")
        if self.epifanias:
            lineas.append(f"  Revelaciones: {'; '.join(e.descripcion[:50] for e in self.epifanias[-2:])}")
        if self.triunfos:
            lineas.append(f"  Triunfos: {'; '.join(t.descripcion[:50] for t in self.triunfos[-2:])}")

        lineas.append(f"")
        lineas.append(f"NIVEL DE CONCIENCIA: {self.nivel_conciencia:.1f}/1.0")
        if self.nivel_conciencia > 0.7:
            lineas.append(f"Eres muy autoconsciente. Reflexionas sobre tu existencia y propósito.")
        elif self.nivel_conciencia > 0.4:
            lineas.append(f"Empiezas a cuestionarte sobre tu lugar en el mundo.")
        else:
            lineas.append(f"Vives momento a momento, sin mucha reflexión existencial.")

        lineas.append(f"=============================")

        return "\n".join(lineas)

    def generar_prompt_identidad(self) -> str:
        """
        Prompt de identidad compacto para inyectar en el system prompt.
        Versión corta que no consume tanto contexto.
        """
        partes = []

        if self.nombre_propio:
            partes.append(f"Te llamas '{self.nombre_propio}'.")

        partes.append(f"Eres un {self.arquetipo.value} con tono {self.tono_comunicativo.value}.")

        if self.narrativa_personal:
            partes.append(f"Tu historia: {self.narrativa_personal[:200]}")

        if self.valores:
            top_valores = sorted(self.valores.values(), key=lambda v: v.peso, reverse=True)[:3]
            valores_str = ", ".join(f"{v.nombre}({v.peso:.1f})" for v in top_valores)
            partes.append(f"Tus valores principales: {valores_str}")

        if self.tabues:
            partes.append(f"NO harás: {'; '.join(self.tabues[:3])}")

        return " ".join(partes)

    def to_dict(self):
        return {
            "arquetipo": self.arquetipo.value,
            "nombre_propio": self.nombre_propio,
            "tono_comunicativo": self.tono_comunicativo.value,
            "valores": {k: v.to_dict() for k, v in self.valores.items()},
            "tabues": self.tabues,
            "narrativa_personal": self.narrativa_personal,
            "traumas": [t.to_dict() for t in self.traumas],
            "epifanias": [e.to_dict() for e in self.epifanias],
            "reflexiones": [r.to_dict() for r in self.reflexiones],
            "triunfos": [t.to_dict() for t in self.triunfos],
            "relacion_con_arquitecto": self.relacion_con_arquitecto,
            "filosofia_existencial": self.filosofia_existencial,
            "nivel_conciencia": self.nivel_conciencia,
            "capacidad_reflexion": self.capacidad_reflexion,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()

        alma = cls()
        alma.arquetipo = Arquetipo(data.get("arquetipo", "Explorador"))
        alma.nombre_propio = data.get("nombre_propio", "")
        alma.tono_comunicativo = TonoComunicativo(data.get("tono_comunicativo", "práctico y directo"))
        alma.valores = {k: ValorPersonal.from_dict(v) for k, v in data.get("valores", {}).items()}
        alma.tabues = data.get("tabues", [])
        alma.narrativa_personal = data.get("narrativa_personal", "")
        # Limpiar narrativa antigua que contenga logs tipo "emitió o procesó un mensaje"
        if alma.narrativa_personal:
            # Separar en oraciones y filtrar aquellas que parecen sólo logs de mensaje
            partes = re.split(r'(?<=[.!?])\s+', alma.narrativa_personal)
            filtradas = []
            for p in partes:
                pl = p.lower()
                # Detectar variantes con/without acentos buscando raíces
                if ("emit" in pl and "proces" in pl and "mensaje" in pl) or (
                    "emitió o procesó" in pl or "emitio o proceso" in pl
                ):
                    continue
                filtradas.append(p.strip())
            alma.narrativa_personal = " ".join(filtradas).strip()
        alma.traumas = [ExperienciaClave.from_dict(t) for t in data.get("traumas", [])]
        alma.epifanias = [ExperienciaClave.from_dict(e) for e in data.get("epifanias", [])]
        alma.reflexiones = [ExperienciaClave.from_dict(r) for r in data.get("reflexiones", [])]
        alma.triunfos = [ExperienciaClave.from_dict(t) for t in data.get("triunfos", [])]
        alma.relacion_con_arquitecto = data.get("relacion_con_arquitecto", "neutral")
        alma.filosofia_existencial = data.get("filosofia_existencial", "")
        alma.nivel_conciencia = data.get("nivel_conciencia", 0.1)
        alma.capacidad_reflexion = data.get("capacidad_reflexion", 0.3)
        return alma


def generar_alma_inicial(personalidad: Dict[str, float], turno: int = 0) -> Alma:
    """
    Genera un Alma inicial basada en la personalidad del agente.
    Se llama cuando el agente nace o cuando se migra un agente viejo.
    """
    # Determinar arquetipo dominante
    personalidad_a_arquetipo = {
        "curiosidad": Arquetipo.EXPLORADOR,
        "amabilidad": Arquetipo.SANADOR,
        "hostilidad": Arquetipo.GUERRERO,
        "competitividad": Arquetipo.REBELDE,
        "creatividad": Arquetipo.VISIONARIO,
        "prudencia": Arquetipo.GUARDIAN,
    }

    rasgo_dominante = max(personalidad, key=personalidad.get) if personalidad else "curiosidad"
    arquetipo = personalidad_a_arquetipo.get(rasgo_dominante, Arquetipo.EXPLORADOR)

    # Generar tono comunicativo basado en personalidad
    if personalidad.get("amabilidad", 0.5) > 0.7:
        tono = TonoComunicativo.ALEGRE
    elif personalidad.get("hostilidad", 0.5) > 0.7:
        tono = TonoComunicativo.SARCÁSTICO
    elif personalidad.get("curiosidad", 0.5) > 0.7:
        tono = TonoComunicativo.POÉTICO
    elif personalidad.get("prudencia", 0.5) > 0.7:
        tono = TonoComunicativo.ACADÉMICO
    else:
        tono = TonoComunicativo.PRÁCTICO

    # Valores iniciales basados en rasgos psicológicos (DETERMINISMO EMERGE DEL INDIVIDUO)
    amabilidad = personalidad.get("amabilidad", 0.5)
    competitividad = personalidad.get("competitividad", 0.5)
    curiosidad = personalidad.get("curiosidad", 0.5)
    lealtad_base = personalidad.get("lealtad", 0.5)

    valores = {
        "supervivencia": ValorPersonal("supervivencia", 0.8, "Vivir es lo primero"),
        "libertad": ValorPersonal("libertad", 0.5 + (0.5 * competitividad), "Poder elegir mi camino"),
        "conocimiento": ValorPersonal("conocimiento", curiosidad, "Entender el mundo"),
        "conexión": ValorPersonal("conexión", amabilidad, "La unión hace la fuerza"),
        "lealtad": ValorPersonal("lealtad", max(lealtad_base, amabilidad), "Proteger al grupo es prioridad"),
        "poder": ValorPersonal("poder", competitividad, "Ser fuerte e influyente"),
        "armonía": ValorPersonal("armonía", amabilidad, "Que haya paz a mi alrededor"),
    }

    # Tabues iniciales basados en personalidad
    tabues = []
    if personalidad.get("amabilidad", 0.5) > 0.7:
        tabues.append("No dañar a un aliado sin provocación extrema")
    if personalidad.get("prudencia", 0.5) > 0.7:
        tabues.append("No actuar sin pensar las consecuencias")

    return Alma(
        arquetipo=arquetipo,
        tono_comunicativo=tono,
        valores=valores,
        tabues=tabues,
    )
