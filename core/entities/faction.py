import random

class Civilizacion:
    """Representa una facción o grupo social dentro de MundoIA."""
    def __init__(self, id, nombre, color, user_id=None, descripcion=""):
        self.id = id
        self.nombre = nombre
        self.color = color
        self.user_id = user_id
        self.descripcion = descripcion

        # --- SISTEMA DE SUCESOS DIVINOS ---
        self.profecias_activas = []  # List of dicts: {"id", "tipo", "objetivo", "recompensa"}
        self.agente_poseido_id = None

        self.recursos_globales = 0.0
        self.territorio = []  # Lista de (x, y)
        self.tecnologias = []
        self.leyes = []
        self.tipo = "GRUPO"  # "GRUPO" o "CIVILIZACION"

    def __getstate__(self):
        """Define qué atributos de Civilizacion se serializan."""
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        """Define cómo se deserializa Civilizacion."""
        self.__dict__.update(state)

    def to_dict(self):
        """Convierte el objeto Civilizacion a un diccionario serializable."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "color": self.color,
            "user_id": self.user_id,
            "descripcion": self.descripcion,
            "profecias_activas": self.profecias_activas,
            "agente_poseido_id": self.agente_poseido_id,
            "recursos_globales": self.recursos_globales,
            "territorio": self.territorio,
            "tecnologias": self.tecnologias,
            "leyes": self.leyes,
            "tipo": self.tipo,
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruye un objeto Civilizacion desde un diccionario serializado."""
        if not data:
            return None
        civ = cls(
            id=data.get("id", f"CIV-{random.randint(0, 999)}"),
            nombre=data.get("nombre", "Civilización"),
            color=data.get("color", "#ffffff"),
            user_id=data.get("user_id"),
            descripcion=data.get("descripcion", ""),
        )
        civ.profecias_activas = data.get("profecias_activas", [])
        civ.agente_poseido_id = data.get("agente_poseido_id")
        civ.recursos_globales = data.get("recursos_globales", 0.0)
        civ.territorio = data.get("territorio", [])
        civ.tecnologias = data.get("tecnologias", [])
        civ.leyes = data.get("leyes", [])
        civ.tipo = data.get("tipo", "GRUPO")
        return civ
