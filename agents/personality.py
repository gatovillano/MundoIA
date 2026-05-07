"""
Módulo ligero para generar y evolucionar personalidades de agentes.

Proporciona funciones que operan sobre el diccionario `personalidad` existente
para mantener compatibilidad con el resto del código base (que espera dicts).
"""
from typing import Dict, Any, Optional
import random


DEFAULT_TRAITS = [
    "extroversión",
    "amabilidad",
    "competitividad",
    "curiosidad",
    "lealtad",
    "prudencia",
    "hostilidad",
    "ambicion",
    "manipulacion",
    "carisma",
]


def generar_personalidad_neutral(noise_scale: float = 0.03, extrema_prob: float = 0.03, antagonist_prob: float = 0.1) -> Dict[str, float]:
    """Genera un dict de personalidad que parte de valores neutrales (0.5)
    y añade un pequeño ruido Gaussiano.

    - `noise_scale` controla la desviación inicial.
    - `extrema_prob` con probabilidad baja fuerza un rasgo hacia un extremo.
    - `antagonist_prob` introduce agentes con rasgos orientados a ambición/manipulación.
    """
    pers = {}
    for t in DEFAULT_TRAITS:
        val = 0.5 + random.gauss(0, noise_scale)
        pers[t] = max(0.0, min(1.0, val))

    # Introducir algunos extremos poco frecuentes para diversidad
    if random.random() < extrema_prob:
        k = random.choice(DEFAULT_TRAITS)
        if random.random() < 0.5:
            pers[k] = max(0.0, min(1.0, pers[k] + random.uniform(0.25, 0.6)))
        else:
            pers[k] = max(0.0, min(1.0, pers[k] - random.uniform(0.25, 0.6)))

    # Introducir agentes con rasgos antagonistas (ambición/manipulación alta)
    if random.random() < antagonist_prob:
        # Aumentar significativamente ambición y manipulación
        pers['ambicion'] = max(0.0, min(1.0, pers.get('ambicion', 0.5) + random.uniform(0.25, 0.6)))
        pers['manipulacion'] = max(0.0, min(1.0, pers.get('manipulacion', 0.5) + random.uniform(0.2, 0.6)))
        # Hostilidad variable para provocar fricciones
        pers['hostilidad'] = max(0.0, min(1.0, pers.get('hostilidad', 0.5) + random.uniform(0.05, 0.4)))
        # Carisma puede potenciar la capacidad de influir negativamente
        pers['carisma'] = max(0.0, min(1.0, pers.get('carisma', 0.5) + random.uniform(0.0, 0.3)))

    return pers


def aplicar_deriva_personalidad(personalidad: Dict[str, float], insights: Optional[Dict[str, Any]] = None, factor: float = 0.01, shock_prob: float = 0.02) -> Dict[str, float]:
    """Aplica una pequeña deriva a la `personalidad` (modifica in-place y la devuelve).

    - `factor` controla la magnitud de la deriva Gaussiana por rasgo.
    - `insights` (por ejemplo del heartbeat) puede cambiar la deriva en reacciones
      a impulsos o detecciones de patrón.
    - `shock_prob` es la probabilidad de un "choque" impredecible que introduce
      cambios más grandes y aporta comportamiento inesperado.
    """
    # Pequeña caminata Gaussiana en cada rasgo
    for k in personalidad.keys():
        delta = random.gauss(0, factor)
        personalidad[k] = max(0.0, min(1.0, personalidad[k] + delta))

    # Ajustes guiados por insights (si los hay)
    if insights:
        nuevos = insights.get("nuevos_impulsos", [])
        # Si el heartbeat sugiere "Intentar algo diferente", forzar un cambio mayor
        if any("Intentar algo diferente" in str(n) for n in nuevos):
            clave = random.choice(list(personalidad.keys()))
            intensidad = random.uniform(0.06, 0.2)
            personalidad[clave] = max(0.0, min(1.0, personalidad[clave] + random.choice([-1, 1]) * intensidad))

        reflexion = str(insights.get("reflexion", ""))
        if "diversificar" in reflexion.lower() or "variar" in reflexion.lower():
            # incentivar curiosidad y reducir prudencia ligeramente
            personalidad["curiosidad"] = max(0.0, min(1.0, personalidad.get("curiosidad", 0.5) + 0.04))
            personalidad["prudencia"] = max(0.0, min(1.0, personalidad.get("prudencia", 0.5) - 0.03))

    # Choque aleatorio ocasional para impredecibilidad
    if random.random() < shock_prob:
        clave = random.choice(list(personalidad.keys()))
        accion = random.choice(["extremo_alto", "extremo_bajo", "aleatorio"])
        if accion == "extremo_alto":
            personalidad[clave] = max(0.0, min(1.0, personalidad[clave] + random.uniform(0.2, 0.6)))
        elif accion == "extremo_bajo":
            personalidad[clave] = max(0.0, min(1.0, personalidad[clave] - random.uniform(0.2, 0.6)))
        else:
            personalidad[clave] = random.random()

    return personalidad


__all__ = [
    "generar_personalidad_neutral",
    "aplicar_deriva_personalidad",
    "DEFAULT_TRAITS",
]
