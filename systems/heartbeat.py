"""
Sistema de HEARTBEAT — Inspirado en el heartbeat de OpenClaw.

Permite a los agentes actuar de forma proactiva, no solo reactiva.
Cada agente tiene su propio "ritmo vital" que determina:
- CUÁNDO actuar (no solo CÓMO)
- Cuándo reflexionar internamente
- Cuándo auto-evaluarse y ajustar propósitos
- Cuándo buscar información activamente

En OpenClaw: HEARTBEAT.md define tareas periódicas de auto-monitoreo.
Aquí: El heartbeat es un sistema interno de ritmos y impulsos.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import random


class EstadoVital(Enum):
    """Estados del ciclo vital del agente."""

    ACTIVO = "activo"  # Actuando en el mundo
    REFLEXIVO = "reflexivo"  # Pensando internamente
    OBSERVANDO = "observando"  # Mirando sin actuar
    DURMIENDO = "durmiendo"  # Recuperando energías (descanso)
    SOCIAL = "social"  # Interactuando activamente


@dataclass
class Impulso:
    """Un impulso interno que motiva al agente a actuar."""

    origen: str  # "necesidad", "curiosidad", "venganza", "ambicion", "miedo"
    descripcion: str
    urgencia: float  # 0.0 a 1.0
    turno_origen: int
    persistente: bool = False  # Si persiste entre turnos

    def decaer(self, turnos_pasados: int):
        """Los impulsos se debilitan con el tiempo si no se actúa."""
        decaimiento = turnos_pasados * 0.05
        self.urgencia = max(0, self.urgencia - decaimiento)


@dataclass
class Proposito:
    """Un propósito a medio-largo plazo del agente."""

    descripcion: str
    prioridad: float  # 0.0 a 1.0
    turno_creacion: int
    turno_objetivo: Optional[int] = None  # Cuándo quiere lograrlo
    progreso: float = 0.0  # 0.0 a 1.0
    abandonado: bool = False

    def actualizar_progreso(self, nuevo_progreso: float):
        self.progreso = min(1.0, nuevo_progreso)
        if self.progreso >= 1.0:
            self.abandonado = True  # Completado


class RitmoVital:
    """
    El ritmo interno del agente — decide CUÁNDO actuar.

    Inspirado en el HEARTBEAT de OpenClaw pero adaptado para un mundo simulado.
    En OpenClaw, el heartbeat es un cron job periódico.
    Aquí, el ritmo vital es orgánico y depende del estado del agente.
    """

    def __init__(self, agente_id: str, personalidad: Dict[str, float] = None):
        self.agente_id = agente_id
        self.personalidad = personalidad or {}

        # Estado actual
        self.estado: EstadoVital = EstadoVital.ACTIVO

        # Ritmos
        self.turno_ultima_accion = 0
        self.turno_ultima_reflexion = 0
        self.periodo_reflexion = 10  # Cada cuántos turnos reflexiona

        # Impulsos activos
        self.impulsos: List[Impulso] = []

        # Propósitos
        self.propositos: List[Proposito] = []

        # Proactividad: qué tan probable es que actúe sin estímulo externo
        self.nivel_proactividad = 0.3  # 0.0 a 1.0

        # Auto-observación
        self.historial_acciones_recientes: List[str] = []
        self.patrones_detectados: List[str] = []

        # Ajustar proactividad según personalidad
        if self.personalidad:
            curiosidad = self.personalidad.get("curiosidad", 0.5)
            competitividad = self.personalidad.get("competitividad", 0.5)
            self.nivel_proactividad = min(1.0, (curiosidad + competitividad) / 2)

            # Curiosos reflexionan más seguido
            if curiosidad > 0.7:
                self.periodo_reflexion = 5
            elif curiosidad < 0.3:
                self.periodo_reflexion = 20

    def deberia_actuar(
        self, turno_actual: int, necesidades: Dict[str, float], tiene_plan: bool = False
    ) -> bool:
        """
        Decide si el agente debe actuar en este turno.
        Retorna True si debe actuar, False si puede observar/descansar/reflexionar.
        """
        # Emergencias siempre actúan
        if necesidades.get("alimento", 10) < 3:
            return True
        if necesidades.get("salud", 10) < 3:
            return True
        if necesidades.get("descanso", 10) < 2:
            # Si está agotado, debe descansar (que es una acción)
            return True

        # Si tiene un plan BDI activo, debe ejecutarlo
        if tiene_plan:
            return True

        # Si hay impulsos urgentes, actuar
        impulsos_urgentes = [i for i in self.impulsos if i.urgencia > 0.7]
        if impulsos_urgentes:
            return True

        # Proactividad aleatoria ponderada
        turnos_desde_accion = turno_actual - self.turno_ultima_accion
        probabilidad = self.nivel_proactividad * (1 + turnos_desde_accion * 0.1)
        if random.random() < min(0.8, probabilidad):
            return True

        # Cada N turnos, reflexionar (que cuenta como actuar)
        if turno_actual - self.turno_ultima_reflexion >= self.periodo_reflexion:
            return True

        # A veces no actuar — observar y existir
        return False

    def generar_impulso(
        self,
        origen: str,
        descripcion: str,
        urgencia: float,
        turno: int,
        persistente: bool = False,
    ):
        """Genera un nuevo impulso interno."""
        impulso = Impulso(
            origen=origen,
            descripcion=descripcion,
            urgencia=urgencia,
            turno_origen=turno,
            persistente=persistente,
        )
        self.impulsos.append(impulso)

    def actualizar_impulsos(self, turno_actual: int):
        """Decae los impulsos antiguos y elimina los resueltos."""
        for impulso in self.impulsos:
            impulso.decaer(turno_actual - impulso.turno_origen)

        # Eliminar impulsos muy débiles
        self.impulsos = [i for i in self.impulsos if i.urgencia > 0.1 or i.persistente]

    def agregar_proposito(
        self,
        descripcion: str,
        prioridad: float,
        turno_actual: int,
        turno_objetivo: int = None,
    ):
        """Agrega un propósito a medio-largo plazo."""
        proposito = Proposito(
            descripcion=descripcion,
            prioridad=prioridad,
            turno_creacion=turno_actual,
            turno_objetivo=turno_objetivo,
        )
        self.propositos.append(proposito)

    def actualizar_propositos(self, turno_actual: int):
        """Verifica el progreso de los propósitos y abandona los obsoletos."""
        for prop in self.propositos:
            if prop.abandonado:
                continue

            # Si pasó mucho tiempo sin progreso, abandonar
            if turno_actual - prop.turno_creacion > 50 and prop.progreso < 0.1:
                prop.abandonado = True

            # Si el turno objetivo pasó y no se logró, abandonar
            if prop.turno_objetivo and turno_actual > prop.turno_objetivo:
                if prop.progreso < 0.5:
                    prop.abandonado = True

        # Limpiar propósitos abandonados antiguos
        self.propositos = [
            p
            for p in self.propositos
            if not p.abandonado or (turno_actual - p.turno_creacion) < 20
        ]

    def obtener_proposito_activo(self) -> Optional[Proposito]:
        """Retorna el propósito activo más prioritario."""
        activos = [p for p in self.propositos if not p.abandonado]
        if not activos:
            return None
        return max(activos, key=lambda p: p.prioridad)

    def heartbeat(
        self, turno_actual: int, alma: Any = None, memoria: Any = None
    ) -> Dict[str, Any]:
        """
        El heartbeat del agente: auto-reflexión periódica.

        Cada N turnos, el agente se detiene a:
        1. Revisar sus propósitos
        2. Reflexionar sobre experiencias recientes
        3. Actualizar su alma (si tiene)
        4. Generar nuevos impulsos

        Retorna un dict con insights del heartbeat.
        """
        self.turno_ultima_reflexion = turno_actual
        insights = {
            "turno": turno_actual,
            "tipo": "heartbeat",
            "reflexion": "",
            "nuevos_impulsos": [],
            "propositos_actualizados": [],
        }

        # 1. Revisar propósitos
        self.actualizar_propositos(turno_actual)
        proposito_activo = self.obtener_proposito_activo()
        if proposito_activo:
            insights["propositos_actualizados"].append(
                {
                    "descripcion": proposito_activo.descripcion,
                    "progreso": proposito_activo.progreso,
                    "prioridad": proposito_activo.prioridad,
                }
            )

        # 2. Actualizar impulsos
        self.actualizar_impulsos(turno_actual)

        # 3. Auto-reflexión sobre patrones
        if len(self.historial_acciones_recientes) >= 5:
            patron = self._detectar_patron()
            if patron:
                self.patrones_detectados.append(patron)
                insights["reflexion"] = f"He notado que: {patron}"

                # Si detecta un patrón negativo, generar impulso de cambio
                if "repetir" in patron.lower() or "mismo" in patron.lower():
                    self.generar_impulso(
                        origen="curiosidad",
                        descripcion="Debería intentar algo diferente",
                        urgencia=0.5,
                        turno=turno_actual,
                    )
                    insights["nuevos_impulsos"].append("Intentar algo diferente")

        # 4. Si tiene alma, reflexionar sobre ella
        if alma and hasattr(alma, "nivel_conciencia") and alma.nivel_conciencia > 0.5:
            reflexion_existencial = self._generar_reflexion_existencial(alma)
            if reflexion_existencial:
                insights["reflexion_existencial"] = reflexion_existencial

        # 5. Si tiene memoria, consolidar
        if memoria and hasattr(memoria, "consolidar_memorias"):
            memoria.consolidar_memorias(turno_actual)

        return insights

    def _detectar_patron(self) -> Optional[str]:
        """Detecta patrones en las acciones recientes del agente."""
        if len(self.historial_acciones_recientes) < 5:
            return None

        recientes = self.historial_acciones_recientes[-10:]

        # Detectar repetición excesiva
        from collections import Counter

        contador = Counter(recientes)
        accion_mas_comun, frecuencia = contador.most_common(1)[0]

        if frecuencia >= 5:
            return f"Sigo haciendo '{accion_mas_comun}' una y otra vez ({frecuencia} veces). ¿Debería variar?"

        # Detectar falta de progreso
        if len(set(recientes)) <= 2:
            return f"Mis acciones recientes son muy limitadas: {set(recientes)}. Necesito diversificar."

        return None

    def _generar_reflexion_existencial(self, alma: Any) -> Optional[str]:
        """Genera una reflexión existencial para agentes autoconscientes."""
        reflexiones = [
            f"¿Por qué sigo existiendo en este mundo? Mi narrativa dice: {alma.narrativa_personal[:100]}",
            f"Soy {alma.arquetipo.value}. ¿Es esto lo que elegí o lo que me tocó?",
            f"mis valores son {list(alma.valores.keys())}. ¿Sigo actuando de acuerdo a ellos?",
            f"He vivido {len(alma.traumas)} traumas y {len(alma.epifanias)} epifanías. ¿Quién soy ahora?",
        ]
        return random.choice(reflexiones)

    def registrar_accion(self, accion: str):
        """Registra una acción en el historial para detección de patrones."""
        self.historial_acciones_recientes.append(accion)
        if len(self.historial_acciones_recientes) > 20:
            self.historial_acciones_recientes.pop(0)

    def obtener_estado_contexto(self) -> str:
        """Genera un string de contexto del ritmo vital para el prompt del LLM."""
        lineas = []

        lineas.append(f"=== TU RITMO VITAL ===")
        lineas.append(f"Estado: {self.estado.value}")

        if self.impulsos:
            impulsos_str = ", ".join(
                f"{i.descripcion} (urgencia: {i.urgencia:.1f})"
                for i in sorted(self.impulsos, key=lambda x: x.urgencia, reverse=True)[
                    :3
                ]
            )
            lineas.append(f"Impulsos actuales: {impulsos_str}")
        else:
            lineas.append("Impulsos: Ninguno urgente.")

        if self.propositos:
            activos = [p for p in self.propositos if not p.abandonado]
            if activos:
                prop = activos[0]
                lineas.append(
                    f"Propósito principal: {prop.descripcion} (progreso: {prop.progreso:.0%})"
                )

        if self.patrones_detectados:
            lineas.append(f"Patrones detectados: {self.patrones_detectados[-1]}")

        lineas.append(f"======================")

        return "\n".join(lineas)

    def to_dict(self):
        return {
            "agente_id": self.agente_id,
            "estado": self.estado.value,
            "turno_ultima_accion": self.turno_ultima_accion,
            "turno_ultima_reflexion": self.turno_ultima_reflexion,
            "periodo_reflexion": self.periodo_reflexion,
            "impulsos": [
                {
                    "origen": i.origen,
                    "descripcion": i.descripcion,
                    "urgencia": i.urgencia,
                    "turno_origen": i.turno_origen,
                    "persistente": i.persistente,
                }
                for i in self.impulsos
            ],
            "propositos": [
                {
                    "descripcion": p.descripcion,
                    "prioridad": p.prioridad,
                    "turno_creacion": p.turno_creacion,
                    "turno_objetivo": p.turno_objetivo,
                    "progreso": p.progreso,
                    "abandonado": p.abandonado,
                }
                for p in self.propositos
            ],
            "nivel_proactividad": self.nivel_proactividad,
            "patrones_detectados": self.patrones_detectados,
        }

    @classmethod
    def from_dict(cls, data, personalidad: Dict[str, float] = None):
        if not data:
            return cls("", personalidad)

        ritmo = cls(data.get("agente_id", ""), personalidad)
        ritmo.estado = EstadoVital(data.get("estado", "activo"))
        ritmo.turno_ultima_accion = data.get("turno_ultima_accion", 0)
        ritmo.turno_ultima_reflexion = data.get("turno_ultima_reflexion", 0)
        ritmo.periodo_reflexion = data.get("periodo_reflexion", 10)
        ritmo.nivel_proactividad = data.get("nivel_proactividad", 0.3)
        ritmo.patrones_detectados = data.get("patrones_detectados", [])

        ritmo.impulsos = [Impulso(**i) for i in data.get("impulsos", [])]
        ritmo.propositos = [Proposito(**p) for p in data.get("propositos", [])]

        return ritmo
