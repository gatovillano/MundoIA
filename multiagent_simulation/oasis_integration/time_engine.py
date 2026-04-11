"""
Time Engine para MundoIA - Sistema de activación probabilística de agentes.
Inspirado en OASIS pero adaptado para simulación de mundo 2D con necesidades triples.
"""

import random
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PatronActividad:
    """Patrón temporal de actividad de un agente."""
    tipo: str  # "diurno", "nocturno", "irregular"
    pesos: List[float]  # 24 valores de probabilidad por hora


class TimeEngine:
    """
    Controla cuándo los agentes actúan en la simulación.
    - Cada paso tiene una "hora simulada"
    - Los agentes tienen patrones de actividad personal
    - Si necesidad es crítica, el agente se activa siempre
    """

    # Patrones de actividad base (24 horas)
    PATRONES_BASE = {
        "diurno": [0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.5, 0.8, 0.9, 0.9, 0.8, 0.7,
                   0.7, 0.8, 0.9, 0.9, 0.8, 0.6, 0.4, 0.3, 0.2, 0.2, 0.1, 0.1],
        "nocturno": [0.8, 0.9, 0.9, 0.8, 0.6, 0.4, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1,
                     0.1, 0.2, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.9, 0.9],
        "irregular": None,  # Se genera aleatorio
    }

    def __init__(self, minutos_por_paso: int = 3):
        """
        Args:
            minutos_por_paso: Cuántos minutos simulados pasan por cada paso
        """
        self.minutos_por_paso = minutos_por_paso
        self.paso_actual = 0
        self.patrones_agentes: Dict[str, PatronActividad] = {}

    def asignar_patron(self, agente_id: str) -> PatronActividad:
        """Asigna un patrón de actividad a un nuevo agente."""
        tipo = random.choice(["diurno", "nocturno", "irregular"])
        
        if tipo == "irregular":
            pesos = [random.uniform(0.1, 0.9) for _ in range(24)]
        else:
            pesos = self.PATRONES_BASE[tipo].copy()
        
        patron = PatronActividad(tipo=tipo, pesos=pesos)
        self.patrones_agentes[agente_id] = patron
        return patron

    def get_hora_simulada(self, paso: int) -> int:
        """Retorna la hora del día (0-23) para un paso dado."""
        minutos_totales = paso * self.minutos_por_paso
        hora = (minutos_totales // 60) % 24
        return hora

    def debe_actuar(self, agente, paso: int, forzoso: bool = False) -> bool:
        """
        Determina si un agente debe actuar en este paso.
        
        Args:
            agente: El agente a evaluar
            paso: El paso actual de la simulación
            forzoso: Si True, ignora la probabilidad y fuerza activación
            
        Returns:
            True si el agente debe actuar este paso
        """
        # Si es forzoso (necesidad crítica), siempre actúa
        if forzoso:
            return True
        
        # Si no tiene patrón, asignarle uno
        if agente.unique_id not in self.patrones_agentes:
            self.asignar_patron(agente.unique_id)
        
        patron = self.patrones_agentes[agente.unique_id]
        hora = self.get_hora_simulada(paso)
        
        # Probabilidad base según patrón
        prob = patron.pesos[hora]
        
        # Bonus por necesidad crítica (aumenta probabilidad)
        if agente.necesidad_intelectual_critica():
            prob = min(1.0, prob + 0.4)
        elif agente.necesidad_social_critica():
            prob = min(1.0, prob + 0.3)
        
        # Verificar con random
        return random.random() < prob

    def get_agentes_activos(self, agentes: List, paso: int) -> List:
        """
        Retorna la lista de agentes que deben actuar en este paso.
        Los agentes con necesidades críticas siempre se activan.
        """
        activos = []
        
        for agente in agentes:
            if not getattr(agente, "esta_vivo", True):
                continue
            
            # Determinar si es forzoso por necesidad crítica
            forzoso = (
                agente.necesidad_intelectual_critica() or 
                agente.necesidad_social_critica() or
                getattr(agente, "mensaje_arquitecto", None) is not None  # Orden del Arquitecto
            )
            
            if self.debe_actuar(agente, paso, forzoso):
                activos.append(agente)
        
        return activos

    def get_estado_turno(self, paso: int) -> Dict:
        """Retorna información del estado del tiempo para este paso."""
        hora = self.get_hora_simulada(paso)
        nombres_horas = [
            "Madrugada", "Madrugada", "Madrugada", "Amanecer", "Amanecer", "Mañana",
            "Mañana", "Mañana", "Mediodía", "Mediodía", "Tarde", "Tarde",
            "Tarde", "Tarde", "Atardecer", "Atardecer", "Noche", "Noche",
            "Noche", "Noche", "Noche", "Madrugada", "Madrugada", "Madrugada"
        ]
        return {
            "paso": paso,
            "hora": hora,
            "nombre_hora": nombres_horas[hora],
            "minutos_simulados": paso * self.minutos_por_paso,
        }

    def reset(self):
        """Reinicia el Time Engine."""
        self.paso_actual = 0
        self.patrones_agentes = {}

    def actualizar_paso(self):
        """Incrementa el paso actual."""
        self.paso_actual += 1