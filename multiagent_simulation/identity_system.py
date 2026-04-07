"""
Sistema de Identidad — Inspirado en IDENTITY.md de OpenClaw.

Cada agente tiene una identidad rica y personalizada:
- Nombre propio generado por IA (no A1, A2)
- Emoji representativo
- "Especie" o tipo de ser
- Vibe/personalidad visual
- Avatar conceptual
- Historia personal acumulada

En OpenClaw, IDENTITY.md define cómo el agente se presenta al mundo.
Aquí, la identidad es dinámica y evoluciona con las experiencias.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random


# Pool de nombres por arquetipo/tema
NOMBRES_POR_ARQUETIPO = {
    "Explorador": {
        "prefijos": ["Ael", "Nim", "Syl", "Cael", "Ori", "Lum", "Ves", "Wyn", "Far", "Ast"],
        "sufijos": ["ius", "a", "or", "is", "an", "el", "ix", "ar", "on", "en"],
    },
    "Sanador": {
        "prefijos": ["El", "Ari", "Sol", "Pax", "Lia", "Mia", "Noa", "Cel", "Vita", "San"],
        "sufijos": ["a", "is", "ia", "el", "us", "en", "or", "ae", "ix", "an"],
    },
    "Guerrero": {
        "prefijos": ["Krag", "Vex", "Dra", "Mor", "Zul", "Gor", "Rax", "Tor", "Fen", "Bor"],
        "sufijos": ["us", "ax", "or", "ak", "ar", "ok", "urn", "ath", "ar", "on"],
    },
    "Sabio": {
        "prefijos": ["Sage", "Wis", "Cal", "Pru", "Sob", "Tem", "Agi", "Phi", "Log", "Soph"],
        "sufijos": ["ius", "is", "a", "on", "es", "or", "an", "us", "ax", "en"],
    },
    "Constructor": {
        "prefijos": ["Tec", "Fab", "Str", "Ark", "For", "Bui", "Cra", "Wri", "Dwe", "Gno"],
        "sufijos": ["or", "us", "an", "ix", "ar", "on", "ek", "ak", "um", "is"],
    },
    "Mercader": {
        "prefijos": ["Mer", "Com", "Tra", "Ven", "Aur", "Mon", "Ric", "Oro", "Arg", "Gem"],
        "sufijos": ["or", "us", "is", "an", "ix", "ar", "on", "en", "el", "a"],
    },
    "Diplomático": {
        "prefijos": ["Pax", "Con", "Har", "Uni", "Ale", "Gra", "Cor", "Dip", "Leg", "Emb"],
        "sufijos": ["us", "is", "a", "on", "es", "or", "an", "el", "ix", "en"],
    },
    "Rebelde": {
        "prefijos": ["Rex", "Rev", "Lib", "Fre", "Def", "Zel", "Fur", "Ira", "Rab", "Wra"],
        "sufijos": ["ax", "ex", "ix", "ox", "ux", "ar", "or", "us", "is", "an"],
    },
    "Ermitaño": {
        "prefijos": ["Sol", "Izo", "Mud", "Sil", "Lun", "Sta", "Noc", "Vac", "Hum", "Qui"],
        "sufijos": ["us", "a", "on", "is", "el", "an", "ix", "or", "en", "ar"],
    },
    "Visionario": {
        "prefijos": ["Vis", "Dre", "Ojo", "Fut", "Pro", "Des", "Aur", "Luz", "Neb", "Cos"],
        "sufijos": ["or", "a", "is", "us", "ix", "an", "el", "on", "ar", "en"],
    },
    "Historiador": {
        "prefijos": ["Cro", "Mem", "His", "Rel", "Arc", "Ver", "Tes", "Epo", "Sig", "Era"],
        "sufijos": ["ius", "is", "a", "on", "es", "or", "an", "us", "ax", "en"],
    },
    "Guardián": {
        "prefijos": ["Cus", "Vig", "Pro", "Esc", "Mur", "Tor", "Bal", "Sen", "Vela", "Pre"],
        "sufijos": ["or", "us", "an", "ix", "ar", "on", "ek", "ak", "um", "is"],
    },
}

# Emojis por arquetipo
EMOJIS_ARQUETIPO = {
    "Explorador": ["🧭", "🗺️", "⛰️", "🌍", "🔭", "🏔️", "🌊"],
    "Sanador": ["💚", "🌿", "✨", "💫", "🕊️", "🌸", "💊"],
    "Guerrero": ["⚔️", "🗡️", "🛡️", "💪", "🔥", "⚡", "🪓"],
    "Sabio": ["📚", "🧠", "🔮", "📖", "🎓", "🌙", "⭐"],
    "Constructor": ["🔨", "🏗️", "⚙️", "🧱", "🔧", "🏠", "🏰"],
    "Mercader": ["💰", "🪙", "💎", "📦", "🏪", "⚖️", "💵"],
    "Diplomático": ["🤝", "🕊️", "📜", "🏛️", "⚖️", "🌐", "💬"],
    "Rebelde": ["🔥", "⚡", "🏴", "💥", "🗯️", "✊", "🌪️"],
    "Ermitaño": ["🌑", "🏔️", "🌲", "🕯️", "📿", "🧘", "🌌"],
    "Visionario": ["👁️", "🌟", "🔮", "💡", "🌈", "🌀", "✨"],
    "Historiador": ["📜", "📚", "🏛️", "🕰️", "📝", "🗞️", "📖"],
    "Guardián": ["🛡️", "🏰", "⚔️", "🔒", "👁️", "🗼", "🚨"],
}

# Especies posibles
ESPECIES = [
    "Humano de los Valles", "Elfo del Bosque Antiguo", "Enano de las Montañas",
    "Nómada del Desierto", "Espíritu del Río", "Guardián de las Ruinas",
    "Viajero Estelar", "Hijo de la Tormenta", "Tejedor de Sombras",
    "Caminante del Crepúsculo", "Sabio de la Cueva", "Forjador de Destinos",
    "Semidiós Menor", "Constructo Mágico", "Elemental de Tierra",
    "Sylvestre Ancestral", "Dríada Moderna", "Golem Consciente",
]

# Vibe descriptions
VIBES = [
    "misterioso y profundo",
    "alegre y contagioso",
    "solemne y respetable",
    "travieso e impredecible",
    "calmo y sereno",
    "intenso y apasionado",
    "práctico y terrenal",
    "soñador y distante",
    "carismático y magnético",
    "melancólico y poético",
    "feroz y determinado",
    "sabio y paciente",
    "curioso e inquieto",
    "protector y leal",
    "astuto y calculador",
]


@dataclass
class Identidad:
    """
    La identidad pública del agente — cómo se presenta al mundo.
    Inspirado en IDENTITY.md de OpenClaw.
    """
    nombre: str = ""
    emoji: str = "🤖"
    especie: str = ""
    vibe: str = ""
    titulo: str = ""  # "El Sabio", "El Intrépido", etc.
    lema: str = ""  # Frase que define al agente

    # Identidad visual conceptual
    colores_asociados: List[str] = field(default_factory=list)
    simbolo_personal: str = ""  # Descripción textual de un símbolo

    # Historia pública
    origen: str = ""  # De dónde viene
    logros_publicos: List[str] = field(default_factory=list)
    reputacion_mundial: float = 0.0  # -1.0 a 1.0

    # Metadatos
    turno_nacimiento: int = 0
    edad_turnos: int = 0

    def generar_presentacion(self) -> str:
        """Genera cómo el agente se presenta a otros."""
        partes = []

        if self.nombre:
            partes.append(f"{self.emoji} **{self.nombre}**")

        if self.especie:
            partes.append(f"({self.especie})")

        if self.titulo:
            partes.append(f"— {self.titulo}")

        if self.vibe:
            partes.append(f"\n  _{self.vibe}_")

        if self.lema:
            partes.append(f'\n  "{self.lema}"')

        if self.origen:
            partes.append(f"\n  Origen: {self.origen}")

        if self.logros_publicos:
            partes.append(f"\n  Logros: {' • '.join(self.logros_publicos[:3])}")

        return "\n".join(partes)

    def generar_prompt_identidad(self) -> str:
        """Prompt compacto para inyectar en el LLM."""
        partes = []

        if self.nombre:
            partes.append(f"Tu nombre es '{self.nombre}' ({self.emoji}).")

        if self.especie:
            partes.append(f"Eres un/a {self.especie}.")

        if self.vibe:
            partes.append(f"Tu vibe es: {self.vibe}.")

        if self.titulo:
            partes.append(f"Te conocen como '{self.titulo}'.")

        if self.lema:
            partes.append(f"Tu lema: '{self.lema}'.")

        return " ".join(partes)

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "emoji": self.emoji,
            "especie": self.especie,
            "vibe": self.vibe,
            "titulo": self.titulo,
            "lema": self.lema,
            "colores_asociados": self.colores_asociados,
            "simbolo_personal": self.simbolo_personal,
            "origen": self.origen,
            "logros_publicos": self.logros_publicos,
            "reputacion_mundial": self.reputacion_mundial,
            "turno_nacimiento": self.turno_nacimiento,
            "edad_turnos": self.edad_turnos,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def generar_identidad_inicial(arquetipo: str, turno: int = 0) -> Identidad:
    """
    Genera una identidad inicial para un agente nuevo.
    Se llama cuando el agente nace.
    """
    # Generar nombre
    datos_nombres = NOMBRES_POR_ARQUETIPO.get(arquetipo, NOMBRES_POR_ARQUETIPO["Explorador"])
    nombre = random.choice(datos_nombres["prefijos"]) + random.choice(datos_nombres["sufijos"])

    # Emoji
    emoji = random.choice(EMOJIS_ARQUETIPO.get(arquetipo, ["🤖"]))

    # Especie
    especie = random.choice(ESPECIES)

    # Vibe
    vibe = random.choice(VIBES)

    # Título basado en arquetipo
    titulos_por_arquetipo = {
        "Explorador": ["el Explorador", "el Intrépido", "el Caminante", "el Viajero"],
        "Sanador": ["el Sanador", "el Compasivo", "el Restaurador", "el Pacífico"],
        "Guerrero": ["el Guerrero", "el Implacable", "el Temerario", "el Victorioso"],
        "Sabio": ["el Sabio", "el Filósofo", "el Erudito", "el Contemplativo"],
        "Constructor": ["el Constructor", "el Forjador", "el Artesano", "el Arquitecto"],
        "Mercader": ["el Mercader", "el Rico", "el Astuto", "el Negociante"],
        "Diplomático": ["el Diplomático", "el Pacificador", "el Mediador", "el Conciliador"],
        "Rebelde": ["el Rebelde", "el Desafiante", "el Libertario", "el Revolucionario"],
        "Ermitaño": ["el Ermitaño", "el Solitario", "el Contemplativo", "el Silencioso"],
        "Visionario": ["el Visionario", "el Profeta", "el Soñador", "el Iluminado"],
        "Historiador": ["el Historiador", "el Cronista", "el Memorioso", "el Testigo"],
        "Guardián": ["el Guardián", "el Protector", "el Vigilante", "el Centinela"],
    }
    titulo = f"{nombre} {random.choice(titulos_por_arquetipo.get(arquetipo, ['el Desconocido']))}"

    # Lema
    lemas = [
        "El mundo es mi hogar",
        "Conocimiento antes que fuerza",
        "Cada día es una nueva aventura",
        "La paz se construye con acciones",
        "El que no arriesga, no gana",
        "La verdad siempre prevalece",
        "Primero sobrevivir, luego prosperar",
        "El conocimiento es el verdadero poder",
        "Juntos somos más fuertes",
        "Cada encuentro es una lección",
    ]
    lema = random.choice(lemas)

    # Colores asociados
    colores = random.sample(["azul", "rojo", "verde", "dorado", "plateado", "púrpura", "bronce", "blanco", "negro", "turquesa"], k=2)

    return Identidad(
        nombre=nombre,
        emoji=emoji,
        especie=especie,
        vibe=vibe,
        titulo=titulo,
        lema=lema,
        colores_asociados=colores,
        turno_nacimiento=turno,
    )


class SistemaIdentidades:
    """
    Gestiona las identidades de todos los agentes del mundo.
    Permite buscar, actualizar y evolucionar identidades.
    """

    def __init__(self):
        self.identidades: Dict[str, Identidad] = {}

    def registrar_agente(self, agente_id: str, identidad: Identidad):
        """Registra la identidad de un agente."""
        self.identidades[agente_id] = identidad

    def obtener_identidad(self, agente_id: str) -> Optional[Identidad]:
        """Obtiene la identidad de un agente."""
        return self.identidades.get(agente_id)

    def actualizar_titulo(self, agente_id: str, nuevo_titulo: str):
        """Actualiza el título de un agente (por logros, etc.)."""
        identidad = self.identidades.get(agente_id)
        if identidad:
            identidad.titulo = nuevo_titulo

    def agregar_logro(self, agente_id: str, logro: str):
        """Agrega un logro público a la identidad de un agente."""
        identidad = self.identidades.get(agente_id)
        if identidad:
            identidad.logros_publicos.append(logro)

    def actualizar_reputacion(self, agente_id: str, delta: float):
        """Actualiza la reputación mundial de un agente."""
        identidad = self.identidades.get(agente_id)
        if identidad:
            identidad.reputacion_mundial = max(-1.0, min(1.0, identidad.reputacion_mundial + delta))

    def buscar_por_nombre(self, nombre: str) -> Optional[str]:
        """Busca un agente por su nombre (case insensitive)."""
        nombre_lower = nombre.lower()
        for agente_id, identidad in self.identidades.items():
            if identidad.nombre.lower() == nombre_lower:
                return agente_id
        return None

    def obtener_todas_identidades(self) -> Dict[str, Identidad]:
        """Retorna todas las identidades."""
        return self.identidades.copy()

    def generar_directorio_publico(self) -> str:
        """Genera un directorio público de todos los agentes conocidos."""
        lineas = ["=== DIRECTORIO DEL MUNDO ===", ""]

        for agente_id, identidad in sorted(self.identidades.items(),
                                           key=lambda x: x[1].reputacion_mundial,
                                           reverse=True):
            lineas.append(f"{identidad.emoji} **{identidad.nombre}** — {identidad.titulo}")
            lineas.append(f"  {identidad.especie} | {identidad.vibe}")
            if identidad.logros_publicos:
                lineas.append(f"  Logros: {' • '.join(identidad.logros_publicos[:2])}")
            lineas.append("")

        lineas.append("===========================")
        return "\n".join(lineas)

    def to_dict(self):
        return {k: v.to_dict() for k, v in self.identidades.items()}

    @classmethod
    def from_dict(cls, data):
        sistema = cls()
        for agente_id, identidad_data in data.items():
            sistema.identidades[agente_id] = Identidad.from_dict(identidad_data)
        return sistema
