"""
core.systems.climate — Motor Climático Dinámico de MundoIA.

Responsabilidades:
  - Gestionar transiciones de estado climático (Sunny → Rainy → Storm…)
  - Aplicar efectos del clima sobre los agentes (salud, descanso, rendimiento)
  - Aplicar efectos del clima sobre los tiles del mapa (modificadores de yield)
  - Emitir log de eventos climáticos significativos
"""
import random
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities.agent import Agente

logger = logging.getLogger(__name__)


# ─── Tipos de clima ────────────────────────────────────────────────────────────

class WeatherType:
    SUNNY = "sunny"
    RAINY = "rainy"
    STORM = "storm"
    FOGGY = "foggy"
    HEATWAVE = "heatwave"
    BLIZZARD = "blizzard"


# ─── Tabla de efectos por clima ────────────────────────────────────────────────

_EFECTOS_CLIMA = {
    WeatherType.SUNNY: {
        "descripcion": "☀️ Día soleado",
        "alimento_mod": +0.02,       # Ligero bono de producción
        "salud_mod": +0.00,
        "descanso_mod": -0.01,       # El calor consume energía mínima
        "tile_yield_mult": 1.1,
        "health_risk": 0.0,
        "duracion_base": 25,
    },
    WeatherType.RAINY: {
        "descripcion": "🌧️ Lluvia",
        "alimento_mod": +0.05,       # La lluvia potencia la agricultura
        "salud_mod": -0.02,          # Riesgo leve de enfermedades
        "descanso_mod": -0.03,
        "tile_yield_mult": 1.2,
        "health_risk": 0.02,
        "duracion_base": 15,
    },
    WeatherType.STORM: {
        "descripcion": "⛈️ Tormenta severa",
        "alimento_mod": -0.10,       # Destruye cultivos
        "salud_mod": -0.15,
        "descanso_mod": -0.10,
        "tile_yield_mult": 0.5,
        "health_risk": 0.08,
        "duracion_base": 8,
    },
    WeatherType.FOGGY: {
        "descripcion": "🌫️ Niebla densa",
        "alimento_mod": -0.02,
        "salud_mod": -0.03,
        "descanso_mod": -0.02,
        "tile_yield_mult": 0.9,
        "health_risk": 0.01,
        "duracion_base": 12,
    },
    WeatherType.HEATWAVE: {
        "descripcion": "🌡️ Ola de calor",
        "alimento_mod": -0.08,       # La sequía destroza cosechas
        "salud_mod": -0.10,
        "descanso_mod": -0.15,       # El calor agota
        "tile_yield_mult": 0.6,
        "health_risk": 0.06,
        "duracion_base": 10,
    },
    WeatherType.BLIZZARD: {
        "descripcion": "❄️ Ventisca",
        "alimento_mod": -0.12,
        "salud_mod": -0.20,
        "descanso_mod": -0.20,
        "tile_yield_mult": 0.3,
        "health_risk": 0.12,
        "duracion_base": 6,
    },
}

# Cadena de Markov: probabilidades de transición de clima
_TRANSICIONES = {
    WeatherType.SUNNY:    [(WeatherType.SUNNY, 0.55), (WeatherType.RAINY, 0.25), (WeatherType.FOGGY, 0.10), (WeatherType.HEATWAVE, 0.10)],
    WeatherType.RAINY:    [(WeatherType.RAINY, 0.40), (WeatherType.STORM, 0.30), (WeatherType.SUNNY, 0.20), (WeatherType.FOGGY, 0.10)],
    WeatherType.STORM:    [(WeatherType.STORM, 0.20), (WeatherType.RAINY, 0.50), (WeatherType.FOGGY, 0.20), (WeatherType.SUNNY, 0.10)],
    WeatherType.FOGGY:    [(WeatherType.FOGGY, 0.30), (WeatherType.SUNNY, 0.40), (WeatherType.RAINY, 0.30)],
    WeatherType.HEATWAVE: [(WeatherType.HEATWAVE, 0.25), (WeatherType.SUNNY, 0.50), (WeatherType.STORM, 0.25)],
    WeatherType.BLIZZARD: [(WeatherType.BLIZZARD, 0.20), (WeatherType.FOGGY, 0.40), (WeatherType.RAINY, 0.40)],
}


class MotorClima:
    """Motor climático autónomo que gestiona el ciclo meteorológico del mundo."""

    def __init__(self, log_fn: Optional[Callable] = None):
        self.clima_actual: str = WeatherType.SUNNY
        self.timer: int = 0
        self.duracion: int = _EFECTOS_CLIMA[WeatherType.SUNNY]["duracion_base"]
        self.log_fn = log_fn or (lambda msg, cat="sistema": logger.info(msg))

    @property
    def efectos(self) -> dict:
        """Retorna los efectos activos del clima actual."""
        return _EFECTOS_CLIMA.get(self.clima_actual, _EFECTOS_CLIMA[WeatherType.SUNNY])

    def tick(self, agentes: List, mapa: List) -> None:
        """
        Avanza un paso del motor climático.
        1. Aplica efectos del clima actual a agentes y tiles.
        2. Comprueba si hay que realizar transición de clima.
        """
        self._aplicar_efectos_agentes(agentes)
        self._aplicar_efectos_mapa(mapa)

        self.timer += 1
        if self.timer >= self.duracion:
            self._transicionar()

    def forzar_evento(self, tipo_clima: str) -> bool:
        """Permite al Arquitecto (usuario) provocar un cambio climático inmediato."""
        if tipo_clima not in _EFECTOS_CLIMA:
            return False
        clima_anterior = self.clima_actual
        self.clima_actual = tipo_clima
        self.timer = 0
        self.duracion = _EFECTOS_CLIMA[tipo_clima]["duracion_base"]
        self.log_fn(
            f"🌍 [ARQUITECTO] Evento climático forzado: {clima_anterior} → {tipo_clima}",
            "sistema",
        )
        return True

    def to_dict(self) -> dict:
        return {
            "clima_actual": self.clima_actual,
            "timer": self.timer,
            "duracion": self.duracion,
            "descripcion": self.efectos["descripcion"],
        }

    @classmethod
    def from_dict(cls, data: dict, log_fn=None) -> "MotorClima":
        obj = cls(log_fn=log_fn)
        obj.clima_actual = data.get("clima_actual", WeatherType.SUNNY)
        obj.timer = data.get("timer", 0)
        obj.duracion = data.get("duracion", 20)
        return obj

    # ── Efectos ────────────────────────────────────────────────────────────────

    def _aplicar_efectos_agentes(self, agentes: List) -> None:
        ef = self.efectos
        for a in agentes:
            if not a.esta_vivo:
                continue
            # Penalización de salud por clima severo
            if ef["health_risk"] > 0 and random.random() < ef["health_risk"]:
                a.recibir_daño(ef["health_risk"] * 3, f"condiciones climáticas ({self.clima_actual})")
            # Modificar descanso (el clima agotador penaliza)
            a.necesidades["descanso"] = max(
                0.0, a.necesidades["descanso"] + ef["descanso_mod"]
            )
            # Modificar alimento (reproducción de cosechas)
            a.necesidades["alimento"] = min(
                10.0, a.necesidades["alimento"] + ef["alimento_mod"]
            )

    def _aplicar_efectos_mapa(self, mapa: List) -> None:
        """Actualiza el multiplicador de rendimiento en todos los tiles activos."""
        ef = self.efectos
        mult = ef["tile_yield_mult"]
        for fila in mapa:
            for tile in fila:
                if hasattr(tile, "yield_mult"):
                    tile.yield_mult = mult

    # ── Transición ─────────────────────────────────────────────────────────────

    def _transicionar(self) -> None:
        """Realiza la transición de clima usando la cadena de Markov."""
        transiciones = _TRANSICIONES.get(self.clima_actual, [])
        if not transiciones:
            return

        # Elegir nuevo clima por ruleta ponderada
        rand = random.random()
        acumulado = 0.0
        nuevo_clima = self.clima_actual
        for clima, prob in transiciones:
            acumulado += prob
            if rand <= acumulado:
                nuevo_clima = clima
                break

        if nuevo_clima != self.clima_actual:
            descripcion_nuevo = _EFECTOS_CLIMA[nuevo_clima]["descripcion"]
            self.log_fn(
                f"🌤️ [CLIMA] Cambio meteorológico: {self.clima_actual} → {nuevo_clima} {descripcion_nuevo}",
                "ambiente",
            )

        self.clima_actual = nuevo_clima
        variacion = random.uniform(0.8, 1.2)
        self.duracion = max(5, int(_EFECTOS_CLIMA[nuevo_clima]["duracion_base"] * variacion))
        self.timer = 0
