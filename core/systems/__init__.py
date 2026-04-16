"""
core.systems - Subsistemas de simulación desacoplados.

Módulos:
    economy  → Motor de economía global (precios, bolsa, Gini)
    climate  → Motor climático dinámico (clima → efectos en agentes y tiles)
"""
from core.systems.economy import MotorEconomia
from core.systems.climate import MotorClima

__all__ = ["MotorEconomia", "MotorClima"]
