"""
Sistema de Crónica e Historia para MundoIA
Gestiona la memoria colectiva de la sociedad y el rol del Historiador.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import random

class EntradaHistoria:
    """Una entrada individual en la libreta de la sociedad"""
    def __init__(self, turno: int, titulo: str, contenido: str, autor_id: str, categoria: str = "general"):
        self.turno = turno
        self.titulo = titulo
        self.contenido = contenido
        self.autor_id = autor_id
        self.categoria = categoria # "fundacion", "conflicto", "ley", "milagro", "general"
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "turno": self.turno,
            "titulo": self.titulo,
            "contenido": self.contenido,
            "autor_id": self.autor_id,
            "categoria": self.categoria,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntradaHistoria':
        entry = cls(
            turno=data['turno'],
            titulo=data['titulo'],
            contenido=data['contenido'],
            autor_id=data['autor_id'],
            categoria=data['categoria']
        )
        entry.timestamp = data['timestamp'] # Set timestamp explicitly
        return entry

class LibretaHistoria:
    """La gran libreta donde se escribe la historia del mundo"""
    def __init__(self):
        self.entradas: List[EntradaHistoria] = []
        self.historiador_id: Optional[str] = None
        self.hitos_pendientes: List[Dict] = [] # Eventos importantes aún no narrados por el historiador

    def __getstate__(self):
        state = self.__dict__.copy()
        state['entradas'] = [e.to_dict() for e in self.entradas]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.entradas = [EntradaHistoria.from_dict(d) for d in state['entradas']]

    def agregar_hito(self, hito: Dict):
        """Agrega un evento importante para que el historiador lo narre luego"""
        self.hitos_pendientes.append(hito)
        # Limitar para no saturar si el historiador no escribe
        if len(self.hitos_pendientes) > 10:
            self.hitos_pendientes.pop(0)
    def limpiar_hitos(self):
        """Limpia los hitos pendientes tras ser narrados."""
        self.hitos_pendientes = []

    def escribir_entrada(self, turno: int, titulo: str, contenido: str, autor_id: str, categoria: str = "general"):
        """Escribe formalmente en la libreta"""
        nueva_entrada = EntradaHistoria(turno, titulo, contenido, autor_id, categoria)
        self.entradas.append(nueva_entrada)
        return nueva_entrada

    def asignar_historiador(self, agentes: List, aleatorio: bool = True):
        """Asigna un agente como historiador.

        Por defecto selecciona aleatoriamente entre los agentes disponibles.
        Si `aleatorio` es False, se usa una heurística (curiosidad+amabilidad).
        """
        if not agentes:
            return None

        # Limpiar asignación previa (si existe) para asegurar exclusividad
        try:
            if self.historiador_id:
                previo = next((a for a in agentes if a.unique_id == self.historiador_id), None)
                if previo:
                    try:
                        previo.profesion = None
                        previo.rol = "Ciudadano"
                        if hasattr(previo, "identidad") and previo.identidad:
                            # Si tenía el título explícito de historiador, limpiarlo
                            if getattr(previo.identidad, "titulo", "").strip().lower() == "el historiador":
                                previo.identidad.titulo = ""
                    except Exception:
                        pass
        except Exception:
            pass

        if aleatorio:
            nuevo_historiador = random.choice(agentes)
        else:
            # Preferir agentes con alta curiosidad o amabilidad (perfil intelectual)
            candidatos = sorted(
                agentes,
                key=lambda a: a.personalidad.get("curiosidad", 0.5)
                + a.personalidad.get("amabilidad", 0.5),
                reverse=True,
            )
            nuevo_historiador = candidatos[0]

        # Registrar la nueva asignación y marcar atributos públicos del agente
        self.historiador_id = nuevo_historiador.unique_id
        try:
            nuevo_historiador.profesion = "Historiador"
            nuevo_historiador.rol = "Historiador"
            if hasattr(nuevo_historiador, "identidad") and nuevo_historiador.identidad:
                nuevo_historiador.identidad.titulo = "el Historiador"
        except Exception:
            pass

        return nuevo_historiador

    def obtener_resumen_hitos(self) -> str:
        """Devuelve un string con los hitos pendientes para que el LLM los procese"""
        if not self.hitos_pendientes:
            return "No han ocurrido eventos notables recientemente."
        
        resumen = "\n".join([f"- {h['descripcion']} (Turno {h['turno']})" for h in self.hitos_pendientes])
        return resumen

    def to_dict(self):
        return {
            "historiador_id": self.historiador_id,
            "entradas": [e.to_dict() for e in self.entradas],
            "num_entradas": len(self.entradas)
        }

    def cargar_desde_dict(self, data):
        """Carga los datos de la historia desde un diccionario."""
        if not data: return
        self.historiador_id = data.get("historiador_id")
        self.entradas = [EntradaHistoria.from_dict(e) for e in data.get("entradas", [])]
