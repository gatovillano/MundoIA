"""
OASIS Integration Package para MundoIA
Contiene los módulos de integración con el paradigma OASIS:
- Time Engine: Control de activación de agentes
- RecSys: Sistema de recomendación social
- Social Network: Gestión de relaciones entre agentes
"""

from .time_engine import TimeEngine, PatronActividad
from .recsys import SocialRecSys, Post, Comentario

__version__ = "0.1.0"
__all__ = ["TimeEngine", "PatronActividad", "SocialRecSys", "Post", "Comentario"]