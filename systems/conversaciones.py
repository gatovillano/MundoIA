"""
Sistema de Conversaciones Persistentes — Para diálogos profundos y extensos entre agentes.

Permite:
- Mantener conversaciones activas con historial completo
- Identificar temas emergentes y profundidad
- Sugerir continuaciones y preguntas reflexivas
- Persistir el contexto de conversación más allá de 5 mensajes
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json


@dataclass
class MensajeConversacion:
    """Un mensaje dentro de una conversación."""

    turno: int
    agente_id: str
    contenido: str
    timestamp: float
    tipo: str = "normal"  # normal, pregunta, respuesta, reflexion, busqueda_info
    metadata: Dict = field(default_factory=dict)  # temas mencionados, emocion, etc.

    def to_dict(self):
        return {
            "turno": self.turno,
            "agente_id": self.agente_id,
            "contenido": self.contenido,
            "timestamp": self.timestamp,
            "tipo": self.tipo,
            "metadata": self.metadata,
        }


@dataclass
class Conversacion:
    """
    Una conversación entre dos agentes (o un agente y grupo).
    Mantiene historial completo, temas identificados y estado.
    """

    id: str  # `${agente1}_${agente2}_${timestamp_inicio}`
    agente1_id: str
    agente2_id: str
    inicio: float
    fin: Optional[float] = None
    mensajes: List[MensajeConversacion] = field(default_factory=list)
    temas: List[str] = field(default_factory=list)  # Temas discutidos
    profundidad: float = (
        0.0  # 0.0 a 1.0, basado en número de intercambios y complejidad
    )
    estado: str = "activa"  # activa, pausada, cerrada

    def agregar_mensaje(
        self,
        agente_id: str,
        contenido: str,
        turno: int,
        tipo: str = "normal",
        metadata: Dict = None,
    ):
        """Registra un nuevo mensaje en la conversación."""
        msg = MensajeConversacion(
            turno=turno,
            agente_id=agente_id,
            contenido=contenido,
            timestamp=datetime.now().timestamp(),
            tipo=tipo,
            metadata=metadata or {},
        )
        self.mensajes.append(msg)
        self.actualizar_temas_y_profundidad()

    def obtener_contexto_reciente(self, max_mensajes: int = 10) -> str:
        """Retorna los últimos mensajes como cadena para el prompt."""
        if not self.mensajes:
            return "No hay historial en esta conversación."

        recientes = self.mensajes[-max_mensajes:]
        contexto = "HISTORIAL DE ESTA CONVERSACIÓN:\n"
        for m in recientes:
            # Determinar quién envió el mensaje desde la perspectiva de agente1
            if m.agente_id == self.agente1_id:
                emisor = "Tú"
            elif m.agente_id == self.agente2_id:
                emisor = f"Agente {self.agente2_id}"
            else:
                emisor = f"Agente {m.agente_id}"  # Fallback
            contexto += f"[{m.turno}] {emisor}: {m.contenido}\n"
        return contexto

    def obtener_todos_los_mensajes(self) -> List[Dict]:
        """Retorna todos los mensajes como diccionarios."""
        return [m.to_dict() for m in self.mensajes]

    def obtener_interlocutor(self, agente_id: str) -> str:
        """Dado un agente, retorna el ID del otro participante."""
        if agente_id == self.agente1_id:
            return self.agente2_id
        elif agente_id == self.agente2_id:
            return self.agente1_id
        else:
            return ""

    def cerrar(self):
        """Marca la conversación como cerrada."""
        self.estado = "cerrada"
        self.fin = datetime.now().timestamp()

    def actualizar_temas_y_profundidad(self):
        """Analiza los mensajes para extraer temas y calcular profundidad."""
        # Extraer palabras clave de todos los mensajes
        todas_palabras = []
        for m in self.mensajes:
            palabras = [p.lower().strip(".,!?;:") for p in m.contenido.split()]
            todas_palabras.extend(palabras)

        # Identificar temas frecuentes (simplificado)
        from collections import Counter

        contador = Counter(todas_palabras)
        palabras_ignoradas = {
            "el",
            "la",
            "de",
            "en",
            "y",
            "a",
            "que",
            "es",
            "con",
            "para",
            "por",
            "un",
            "una",
            "los",
            "las",
            "del",
            "al",
            "se",
            "ha",
            "han",
            "he",
            "estoy",
            "estás",
            "está",
            "estamos",
            "están",
            "fue",
            "ser",
            "tener",
            "hacer",
            "hago",
            "haces",
            "hace",
            "hacemos",
            "hacen",
            "mi",
            "tu",
            "su",
            "nuestro",
            "vuestro",
            "esto",
            "eso",
            "aquello",
            "este",
            "ese",
            "aquel",
            "cómo",
            "cuándo",
            "dónde",
            "qué",
            "quién",
            "por qué",
            "no",
            "sí",
            "si",
            "pero",
            "aunque",
            "porque",
            "pues",
            "más",
            "menos",
            "todo",
            "nada",
            "algo",
            "alguien",
            "nadie",
            "cada",
            "mucho",
            "poco",
        }
        temas = [
            palabra
            for palabra, freq in contador.most_common(10)
            if freq > 1 and palabra not in palabras_ignoradas and len(palabra) > 3
        ]
        self.temas = temas[:5]

        # Calcular profundidad basado en:
        # - Número de mensajes (más es más profundo)
        # - Diversidad de participantes (balance de quién habla)
        # - Complejidad del lenguaje (longitud promedio, vocabulario)
        num_mensajes = len(self.mensajes)
        participantes = set(m.agente_id for m in self.mensajes)
        balance = (
            len(participantes) / 2
        )  # 0.5 si solo un agente habla, 1.0 si ambos hablan igual

        # Longitud promedio
        palabras_totales = sum(len(m.contenido.split()) for m in self.mensajes)
        longitud_prom = palabras_totales / num_mensajes if num_mensajes > 0 else 0
        complejidad = min(1.0, longitud_prom / 30)  # Normalizar a ~30 palabras

        self.profundidad = min(
            1.0, (num_mensajes / 20) * balance * (0.5 + 0.5 * complejidad)
        )

    def sugerir_pregunta_profundizante(self, agente_id: str) -> Optional[str]:
        """
        Sugiere una pregunta para profundizar en la conversación,
        basada en temas identificados o lagunas informativas.
        """
        interlocutor = self.obtener_interlocutor(agente_id)
        if not interlocutor:
            return None

        # Si hay temas identificados, sugerir pregunta sobre uno
        if self.temas:
            tema = self.temas[0]
            preguntas = [
                f"Háblame más sobre {tema}. ¿Cómo lo descubriste?",
                f"¿Qué opina {interlocutor} sobre {tema}?",
                f"¿Cómo ha influido {tema} en tu forma de pensar?",
                f"¿Podrías profundizar en tu perspectiva sobre {tema}?",
            ]
            import random

            return random.choice(preguntas)

        # Si no, sugerir una pregunta reflexiva genérica
        preguntas_genericas = [
            f"¿Cómo te sientes acerca de lo que estamos discutiendo?",
            f"¿Qué experiencia personal tienes relacionada con esto?",
            f"¿Crees que esto cambiará el mundo de alguna manera?",
            f"¿Qué piensas que deberíamos hacer al respecto?",
        ]
        import random

        return random.choice(preguntas_genericas)


class GestorConversaciones:
    """
    Singleton que gestiona todas las conversaciones del sistema.
    Se integra con el modelo y los agentes.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conversaciones_activas: Dict[str, Conversacion] = {}
            cls._instance.conversaciones_cerradas: List[Conversacion] = []
            cls._instance.conversaciones_por_agente: Dict[
                str, List[str]
            ] = {}  # agente -> [conversacion_ids]
        return cls._instance

    def iniciar_conversacion(self, agente1_id: str, agente2_id: str) -> Conversacion:
        """Crea una nueva conversación entre dos agentes."""
        # Generar ID único
        import time

        conv_id = f"{agente1_id}_{agente2_id}_{int(time.time())}"
        conv = Conversacion(
            id=conv_id,
            agente1_id=agente1_id,
            agente2_id=agente2_id,
            inicio=datetime.now().timestamp(),
        )
        self.conversaciones_activas[conv_id] = conv

        # Registrar en los agentes
        for agente_id in [agente1_id, agente2_id]:
            if agente_id not in self.conversaciones_por_agente:
                self.conversaciones_por_agente[agente_id] = []
            self.conversaciones_por_agente[agente_id].append(conv_id)

        return conv

    def obtener_conversacion_activa(
        self, agente1_id: str, agente2_id: str
    ) -> Optional[Conversacion]:
        """Busca si ya existe una conversación activa entre estos agentes."""
        for conv in self.conversaciones_activas.values():
            if (conv.agente1_id == agente1_id and conv.agente2_id == agente2_id) or (
                conv.agente1_id == agente2_id and conv.agente2_id == agente1_id
            ):
                return conv
        return None

    def obtener_conversacion(self, conv_id: str) -> Optional[Conversacion]:
        """Obtiene una conversación por ID (activa o cerrada)."""
        if conv_id in self.conversaciones_activas:
            return self.conversaciones_activas[conv_id]
        for conv in self.conversaciones_cerradas:
            if conv.id == conv_id:
                return conv
        return None

    def obtener_conversaciones_agente(
        self, agente_id: str, solo_activas: bool = False
    ) -> List[Conversacion]:
        """Obtiene todas las conversaciones de un agente."""
        conv_ids = self.conversaciones_por_agente.get(agente_id, [])
        if solo_activas:
            return [
                self.conversaciones_activas[cid]
                for cid in conv_ids
                if cid in self.conversaciones_activas
            ]
        todas = []
        for cid in conv_ids:
            conv = self.obtener_conversacion(cid)
            if conv:
                todas.append(conv)
        return todas

    def agregar_mensaje(
        self,
        agente_id: str,
        otro_agente_id: str,
        contenido: str,
        turno: int,
        tipo: str = "normal",
        metadata: Dict = None,
    ):
        """
        Agrega un mensaje a la conversación entre agente_id y otro_agente_id.
        Si no existe conversación activa, la crea.
        """
        conv = self.obtener_conversacion_activa(agente_id, otro_agente_id)
        if not conv:
            conv = self.iniciar_conversacion(agente_id, otro_agente_id)

        conv.agregar_mensaje(agente_id, contenido, turno, tipo, metadata)

    def cerrar_conversacion(self, conv_id: str):
        """Cierra una conversación activa."""
        if conv_id in self.conversaciones_activas:
            conv = self.conversaciones_activas[conv_id]
            conv.cerrar()
            self.conversaciones_cerradas.append(conv)
            del self.conversaciones_activas[conv_id]

    def cerrar_conversaciones_inactivas(
        self, turno_actual: int, max_inactividad: int = 50
    ):
        """Cierra conversaciones que llevan muchos turnos sin actividad."""
        for conv in list(self.conversaciones_activas.values()):
            ultimo_turno = conv.mensajes[-1].turno if conv.mensajes else 0
            if turno_actual - ultimo_turno > max_inactividad:
                self.cerrar_conversacion(conv.id)

    def obtener_contexto_conversacion_activa(
        self, agente_id: str, otro_agente_id: str, max_mensajes: int = 15
    ) -> str:
        """Obtiene el contexto de la conversación activa con un agente específico."""
        conv = self.obtener_conversacion_activa(agente_id, otro_agente_id)
        if conv:
            return conv.obtener_contexto_reciente(max_mensajes)
        return ""

    def sugerir_siguiente_paso_conversacion(
        self, agente_id: str, otro_agente_id: str
    ) -> Optional[str]:
        """Sugiere un siguiente paso para profundizar la conversación."""
        conv = self.obtener_conversacion_activa(agente_id, otro_agente_id)
        if conv:
            return conv.sugerir_pregunta_profundizante(agente_id)
        return None

    def obtener_estadisticas(self) -> Dict:
        """Retorna estadísticas del sistema de conversaciones."""
        total_mensajes = sum(
            len(c.mensajes) for c in self.conversaciones_activas.values()
        )
        total_mensajes += sum(len(c.mensajes) for c in self.conversaciones_cerradas)
        prof_prom = (
            sum(c.profundidad for c in self.conversaciones_activas.values())
            / len(self.conversaciones_activas)
            if self.conversaciones_activas
            else 0
        )

        return {
            "conversaciones_activas": len(self.conversaciones_activas),
            "conversaciones_cerradas": len(self.conversaciones_cerradas),
            "total_mensajes": total_mensajes,
            "profundidad_promedio": round(prof_prom, 2),
            "agentes_con_conversaciones": len(self.conversaciones_por_agente),
        }

    def to_dict(self):
        """Serializa el estado para persistencia."""
        return {
            "activas": {
                cid: {
                    "id": c.id,
                    "agente1": c.agente1_id,
                    "agente2": c.agente2_id,
                    "inicio": c.inicio,
                    "fin": c.fin,
                    "mensajes": [m.to_dict() for m in c.mensajes],
                    "temas": c.temas,
                    "profundidad": c.profundidad,
                    "estado": c.estado,
                }
                for cid, c in self.conversaciones_activas.items()
            },
            "cerradas": [
                {
                    "id": c.id,
                    "agente1": c.agente1_id,
                    "agente2": c.agente2_id,
                    "inicio": c.inicio,
                    "fin": c.fin,
                    "mensajes": [m.to_dict() for m in c.mensajes],
                    "temas": c.temas,
                    "profundidad": c.profundidad,
                    "estado": c.estado,
                }
                for c in self.conversaciones_cerradas
            ],
            "por_agente": self.conversaciones_por_agente,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Reconstruye el gestor desde datos serializados."""
        gestor = cls()
        gestor.conversaciones_activas = {}
        for cid, cdata in data.get("activas", {}).items():
            conv = Conversacion(
                id=cdata["id"],
                agente1_id=cdata["agente1"],
                agente2_id=cdata["agente2"],
                inicio=cdata["inicio"],
                fin=cdata.get("fin"),
                estado=cdata.get("estado", "activa"),
            )
            conv.mensajes = [
                MensajeConversacion(**m) for m in cdata.get("mensajes", [])
            ]
            conv.temas = cdata.get("temas", [])
            conv.profundidad = cdata.get("profundidad", 0.0)
            gestor.conversaciones_activas[cid] = conv

        gestor.conversaciones_cerradas = []
        for cdata in data.get("cerradas", []):
            conv = Conversacion(
                id=cdata["id"],
                agente1_id=cdata["agente1"],
                agente2_id=cdata["agente2"],
                inicio=cdata["inicio"],
                fin=cdata["fin"],
                estado=cdata.get("estado", "cerrada"),
            )
            conv.mensajes = [
                MensajeConversacion(**m) for m in cdata.get("mensajes", [])
            ]
            conv.temas = cdata.get("temas", [])
            conv.profundidad = cdata.get("profundidad", 0.0)
            gestor.conversaciones_cerradas.append(conv)

        gestor.conversaciones_por_agente = data.get("por_agente", {})
        return gestor


# Instancia global
gestor_conversaciones = GestorConversaciones()
