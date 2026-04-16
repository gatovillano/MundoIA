import random

class Institucion:
    """Representa una estructura u organización formal en el mundo (ej. Universidad, Hospital)."""
    def __init__(self, id, nombre, tipo, fundador_id, x, y, user_id=None):
        self.id = id
        self.nombre = nombre
        self.tipo = tipo  # "EDUCATIVA", "FINANCIERA", "SANITARIA", "CIENTIFICA", "RELIGIOSA"
        self.fundador_id = fundador_id
        self.lider_id = fundador_id
        self.miembros = [fundador_id]
        self.x = x
        self.y = y
        self.recursos = 0.0
        self.nivel = 1
        self.user_id = user_id
        self.descripcion = ""

    def to_dict(self):
        """Convierte la institución en un diccionario serializable."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "fundador_id": self.fundador_id,
            "lider_id": self.lider_id,
            "miembros": self.miembros,
            "x": self.x,
            "y": self.y,
            "recursos": self.recursos,
            "nivel": self.nivel,
            "user_id": self.user_id,
            "descripcion": self.descripcion,
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruye una institución desde un diccionario serializado."""
        if not data:
            return None
        inst = cls(
            id=data.get("id", f"INST-UNKNOWN-{random.randint(0, 999)}"),
            nombre=data.get("nombre", "Institución Desconocida"),
            tipo=data.get("tipo", "CIENCIA"),
            fundador_id=data.get("fundador_id", "SISTEMA"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            user_id=data.get("user_id"),
        )
        inst.lider_id = data.get("lider_id", inst.fundador_id)
        inst.miembros = data.get("miembros", [inst.fundador_id])
        inst.recursos = data.get("recursos", 0.0)
        inst.nivel = data.get("nivel", 1)
        inst.descripcion = data.get("descripcion", "")
        return inst
