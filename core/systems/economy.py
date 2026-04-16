"""
core.systems.economy — Motor de Economía Global de MundoIA.

Responsabilidades:
  - Calcular el precio dinámico de recursos basado en oferta/demanda real
  - Actualizar el índice bursátil global según la actividad de los agentes
  - Calcular el coeficiente Gini (desigualdad)
  - Calcular la felicidad promedio ponderada de la población
  - Registrar el historial económico para visualización en frontend
"""
import math
import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities.agent import Agente

logger = logging.getLogger(__name__)


class MotorEconomia:
    """Motor de economía global desacoplado del simulador principal."""

    PRECIO_MIN = 0.5
    PRECIO_MAX = 20.0
    PRECIO_BASE = 2.0
    HISTORIAL_MAX = 200

    def __init__(self):
        self.estado = {
            "total_dinero": 0.0,
            "indice_bursatil": 100.0,
            "precio_recurso": self.PRECIO_BASE,
            "historial_indice": [],
            "historial_precios": [],
        }
        self.precio_recurso_actual = self.PRECIO_BASE

    # ------------------------------------------------------------------
    # API PÚBLICA — llamada desde ModeloRelacional cada paso
    # ------------------------------------------------------------------

    def tick(self, agentes: List) -> None:
        """Avanza un paso del motor económico con la lista actual de agentes."""
        self._actualizar_precio_dinamico(agentes)
        self._actualizar_indice_bursatil(agentes)
        self._actualizar_totales(agentes)

    def calcular_gini(self, agentes: List) -> float:
        """
        Coeficiente de Gini basado en (recursos + dinero) de todos los agentes.
        0.0 = igualdad perfecta | 1.0 = desigualdad máxima
        """
        riquezas = sorted(a.recursos + a.dinero for a in agentes)
        n = len(riquezas)
        if n == 0 or sum(riquezas) == 0:
            return 0.0

        suma_ponderada = sum((i + 1) * x for i, x in enumerate(riquezas))
        suma_total = sum(riquezas)
        gini = (2 * suma_ponderada / (n * suma_total)) - (n + 1) / n
        return round(max(0.0, min(1.0, gini)), 3)

    def calcular_felicidad(self, agentes: List) -> float:
        """
        Felicidad promedio ponderada por salud.
        Basada en la satisfacción de las 5 necesidades principales (escala 0-10).
        """
        if not agentes:
            return 0.0

        CLAVES = ["alimento", "social", "seguridad", "descanso", "entretenimiento"]
        puntuaciones = []
        for a in agentes:
            nec = a.necesidades
            promedio = sum(nec.get(k, 0) for k in CLAVES) / len(CLAVES)
            # La salud actúa como multiplicador (salud baja → penaliza toda la felicidad)
            factor_salud = nec.get("salud", 10.0) / 10.0
            puntuaciones.append(promedio * factor_salud)

        return round(sum(puntuaciones) / len(puntuaciones), 2)

    def snapshot(self) -> dict:
        """Devuelve una copia del estado económico actual para serialización."""
        return dict(self.estado)

    # ------------------------------------------------------------------
    # LÓGICA INTERNA
    # ------------------------------------------------------------------

    def _actualizar_precio_dinamico(self, agentes: List) -> None:
        """
        El precio sube cuando la oferta baja (pocos recursos) y baja cuando hay abundancia.
        Fórmula: precio = BASE * (DEMANDA / max(OFERTA, 1))
        """
        if not agentes:
            return

        total_recursos = sum(
            a.recursos + a.inventario.get("comida", 0) for a in agentes
        )
        demanda = sum(
            max(0, 5.0 - a.necesidades.get("alimento", 5.0)) for a in agentes
        )

        oferta_norm = max(total_recursos / max(len(agentes), 1), 1.0)
        demanda_norm = max(demanda / max(len(agentes), 1), 0.1)

        nuevo_precio = self.PRECIO_BASE * (demanda_norm / (oferta_norm / 100.0))
        nuevo_precio = round(max(self.PRECIO_MIN, min(self.PRECIO_MAX, nuevo_precio)), 2)

        self.precio_recurso_actual = nuevo_precio
        self.estado["precio_recurso"] = nuevo_precio

        historial = self.estado["historial_precios"]
        historial.append(nuevo_precio)
        if len(historial) > self.HISTORIAL_MAX:
            historial.pop(0)

    def _actualizar_indice_bursatil(self, agentes: List) -> None:
        """
        El índice bursátil refleja la salud económica colectiva.
        Sube cuando los agentes tienen dinero y baja cuando están en crisis.
        """
        if not agentes:
            return

        INDICE_BASE = 100.0
        dinero_promedio = sum(a.dinero for a in agentes) / len(agentes)
        salud_promedio = sum(
            a.necesidades.get("salud", 5.0) for a in agentes
        ) / len(agentes)

        # Factor de actividad: número de transacciones estimadas por agente
        factor_actividad = min(2.0, dinero_promedio / 100.0)
        factor_bienestar = salud_promedio / 10.0

        nuevo_indice = INDICE_BASE * factor_actividad * factor_bienestar
        # Suavizado exponencial para evitar oscilaciones bruscas
        indice_anterior = self.estado["indice_bursatil"]
        indice_suavizado = round(0.85 * indice_anterior + 0.15 * nuevo_indice, 2)

        self.estado["indice_bursatil"] = indice_suavizado
        historial = self.estado["historial_indice"]
        historial.append(indice_suavizado)
        if len(historial) > self.HISTORIAL_MAX:
            historial.pop(0)

    def _actualizar_totales(self, agentes: List) -> None:
        """Actualiza el total de dinero circulante en la economía."""
        self.estado["total_dinero"] = round(sum(a.dinero for a in agentes), 2)
