"""
Sistema de CRÓNICAS — Inspirado en Moltbook.

Un sistema de broadcasting persistente donde los agentes:
- Publican pensamientos, descubrimientos y eventos
- Leen crónicas de otros agentes
- Desarrollan "influencia" por la resonancia de sus publicaciones
- Crean cultura colectiva emergente

En Moltbook, los agentes leen/escriben en un feed social compartido.
Aquí, las crónicas se organizan por facción y tienen un sistema de karma/influencia.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random
from datetime import datetime


class TipoCronica(Enum):
    PENSAMIENTO = "pensamiento"       # Reflexión personal
    DESCUBRIMIENTO = "descubrimiento"  # Hallazgo importante
    EVENTO = "evento"                 # Algo que ocurrió
    DECLARACION = "declaracion"       # Anuncio público
    HISTORIA = "historia"            # Narración de eventos
    RUMOR = "rumor"                  # Información no verificada
    LEYENDA = "leyenda"              # Narrativa cultural emergente
    PROFECIA = "profecia"            # Predicción o visión


@dataclass
class Cronica:
    """Una crónica publicada por un agente."""
    id: str
    autor_id: str
    autor_nombre: str
    contenido: str
    tipo: TipoCronica
    turno_publicacion: int
    faccion: str = ""  # Facción del autor (vacío = independiente)
    ubicacion: Optional[Tuple[int, int]] = None

    # Métricas sociales
    resonancia: float = 0.0  # Cuánto impacto tuvo (0.0 a 1.0)
    respuestas: List[str] = field(default_factory=list)  # IDs de crónicas que responden
    menciones: List[str] = field(default_factory=list)  # IDs de agentes mencionados

    # Estado
    es_publica: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "autor_id": self.autor_id,
            "autor_nombre": self.autor_nombre,
            "contenido": self.contenido,
            "tipo": self.tipo.value,
            "turno_publicacion": self.turno_publicacion,
            "faccion": self.faccion,
            "ubicacion": self.ubicacion,
            "resonancia": self.resonancia,
            "respuestas": self.respuestas,
            "menciones": self.menciones,
            "es_publica": self.es_publica,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data):
        data_copy = data.copy()
        data_copy["tipo"] = TipoCronica(data.get("tipo", "pensamiento"))
        return cls(**data_copy)


@dataclass
class InfluenciaAgente:
    """Tracking de la influencia social de un agente."""
    agente_id: str
    karma: float = 0.0  # -100 a 100, reputación social
    seguidores: int = 0  # Cuántos agentes "siguen" sus crónicas
    cronicas_publicadas: int = 0
    cronicas_resonantes: int = 0  # Crónicas con resonancia > 0.5
    nivel_influencia: str = "desconocido"  # Desconocido, Notorio, Respetado, Legendario

    def actualizar_nivel(self):
        if self.karma > 50 or self.cronicas_resonantes > 10:
            self.nivel_influencia = "legendario"
        elif self.karma > 20 or self.cronicas_resonantes > 5:
            self.nivel_influencia = "respetado"
        elif self.karma > 0 or self.cronicas_publicadas > 3:
            self.nivel_influencia = "notorio"
        else:
            self.nivel_influencia = "desconocido"

    def to_dict(self):
        return {
            "agente_id": self.agente_id,
            "karma": self.karma,
            "seguidores": self.seguidores,
            "cronicas_publicadas": self.cronicas_publicadas,
            "cronicas_resonantes": self.cronicas_resonantes,
            "nivel_influencia": self.nivel_influencia,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class SistemaCronicas:
    """
    Sistema de crónicas sociales — el "Moltbook" de MundoIA.

    Los agentes publican crónicas que otros pueden leer.
    Las crónicas de alta resonancia se convierten en parte de la cultura del mundo.
    """

    def __init__(self, max_cronicas_memoria: int = 200):
        self.cronicas: List[Cronica] = []
        self.influencias: Dict[str, InfluenciaAgente] = {}
        self.max_cronicas_memoria = max_cronicas_memoria

        # Crónicas por facción
        self.muros_faccion: Dict[str, List[str]] = {}  # faccion -> [ids_cronicas]

        # Tendencias culturales emergentes
        self.temas_recurrentes: Dict[str, int] = {}  # tema -> frecuencia
        self.leyendas: List[Cronica] = []  # Crónicas que se volvieron leyendas

    def publicar_cronica(self, autor_id: str, autor_nombre: str, contenido: str,
                         tipo: TipoCronica, turno: int, faccion: str = "",
                         ubicacion: Tuple[int, int] = None, menciones: List[str] = None,
                         tags: List[str] = None, es_publica: bool = True) -> Cronica:
        """Publica una nueva crónica."""
        import hashlib
        cronica_id = hashlib.md5(f"{autor_id}_{turno}_{contenido[:50]}".encode()).hexdigest()[:12]

        cronica = Cronica(
            id=cronica_id,
            autor_id=autor_id,
            autor_nombre=autor_nombre,
            contenido=contenido,
            tipo=tipo,
            turno_publicacion=turno,
            faccion=faccion,
            ubicacion=ubicacion,
            menciones=menciones or [],
            tags=tags or [],
            es_publica=es_publica,
        )

        self.cronicas.append(cronica)

        # Actualizar influencia del autor
        if autor_id not in self.influencias:
            self.influencias[autor_id] = InfluenciaAgente(agente_id=autor_id)

        influencia = self.influencias[autor_id]
        influencia.cronicas_publicadas += 1

        # Agregar al muro de facción si aplica
        if faccion:
            if faccion not in self.muros_faccion:
                self.muros_faccion[faccion] = []
            self.muros_faccion[faccion].append(cronica_id)

        # Detectar temas recurrentes
        palabras_clave = ["guerra", "paz", "comercio", "dios", "arquitecto", "poder",
                          "conocimiento", "supervivencia", "alianza", "traición", "amor",
                          "muerte", "nacimiento", "misterio", "profecía"]
        contenido_lower = contenido.lower()
        for tema in palabras_clave:
            if tema in contenido_lower:
                self.temas_recurrentes[tema] = self.temas_recurrentes.get(tema, 0) + 1

        # Limitar crónicas en memoria (las viejas se archivan)
        if len(self.cronicas) > self.max_cronicas_memoria:
            self.cronicas = self.cronicas[-self.max_cronicas_memoria:]

        return cronica

    def obtener_cronicas_recientes(self, faccion: str = "",
                                    max_resultados: int = 10,
                                    tipo: TipoCronica = None) -> List[Cronica]:
        """Obtiene crónicas recientes, filtradas por facción y/o tipo."""
        filtradas = self.cronicas

        if faccion:
            filtradas = [c for c in filtradas if c.faccion == faccion]

        if tipo:
            filtradas = [c for c in filtradas if c.tipo == tipo]

        # Solo crónicas públicas
        filtradas = [c for c in filtradas if c.es_publica]

        # Ordenar por turno (más recientes primero)
        filtradas.sort(key=lambda c: c.turno_publicacion, reverse=True)

        return filtradas[:max_resultados]

    def obtener_cronicas_resonantes(self, min_resonancia: float = 0.5,
                                     max_resultados: int = 5) -> List[Cronica]:
        """Obtiene las crónicas con mayor resonancia."""
        resonantes = [c for c in self.cronicas
                      if c.resonancia >= min_resonancia and c.es_publica]
        resonantes.sort(key=lambda c: c.resonancia, reverse=True)
        return resonantes[:max_resultados]

    def calcular_resonancia(self, cronica: Cronica, agentes_cercanos: int = 0,
                            agente_es_vocero: bool = False) -> float:
        """
        Calcula la resonancia de una crónica.
        Factores: contenido, autor, contexto, timing.
        """
        resonancia = 0.3  # Base

        # Tipo de crónica
        bonus_tipo = {
            TipoCronica.DESCUBRIMIENTO: 0.2,
            TipoCronica.EVENTO: 0.15,
            TipoCronica.DECLARACION: 0.1,
            TipoCronica.HISTORIA: 0.1,
            TipoCronica.LEYENDA: 0.3,
            TipoCronica.PROFECIA: 0.25,
            TipoCronica.PENSAMIENTO: 0.05,
            TipoCronica.RUMOR: 0.1,
        }
        resonancia += bonus_tipo.get(cronica.tipo, 0.05)

        # Influencia del autor
        influencia = self.influencias.get(cronica.autor_id)
        if influencia:
            resonancia += min(0.3, influencia.karma / 200.0)
            if agente_es_vocero:
                resonancia += 0.15

        # Agentes cercanos (más audiencia = más resonancia potencial)
        resonancia += min(0.2, agentes_cercanos * 0.05)

        # Longitud del contenido (crónicas más elaboradas tienen más impacto)
        if len(cronica.contenido) > 100:
            resonancia += 0.1
        if len(cronica.contenido) > 300:
            resonancia += 0.1

        # Aleatoriedad contextual
        resonancia += random.uniform(-0.1, 0.1)

        return max(0.0, min(1.0, resonancia))

    def agregar_respuesta(self, cronica_id: str, respuesta_id: str):
        """Registra que una crónica responde a otra."""
        for cronica in self.cronicas:
            if cronica.id == cronica_id:
                cronica.respuestas.append(respuesta_id)
                # Aumentar ligeramente la resonancia por tener respuesta
                cronica.resonancia = min(1.0, cronica.resonancia + 0.05)
                break

    def actualizar_influencia(self, agente_id: str, delta_karma: float):
        """Actualiza el karma/influencia de un agente."""
        if agente_id not in self.influencias:
            self.influencias[agente_id] = InfluenciaAgente(agente_id=agente_id)

        influencia = self.influencias[agente_id]
        influencia.karma = max(-100, min(100, influencia.karma + delta_karma))

        # Contar crónicas resonantes
        cronicas_agente = [c for c in self.cronicas
                           if c.autor_id == agente_id and c.resonancia > 0.5]
        influencia.cronicas_resonantes = len(cronicas_agente)

        influencia.actualizar_nivel()

    def obtener_contexto_cronicas(self, agente_id: str, faccion: str = "",
                                   turno_actual: int = 0) -> str:
        """
        Genera un string de contexto de crónicas para inyectar en el prompt del LLM.
        Similar a cómo Moltbook inyecta el feed social en el contexto del agente.
        """
        lineas = []

        # Crónicas recientes de la facción
        cronicas_faccion = self.obtener_cronicas_recientes(faccion=faccion, max_resultados=3)
        if cronicas_faccion:
            lineas.append("=== CRÓNICAS RECIENTES DE TU FACCION ===")
            for c in cronicas_faccion:
                lineas.append(f"  [{c.tipo.value}] {c.autor_nombre}: {c.contenido[:100]}...")
            lineas.append("")

        # Crónicas resonantes del mundo (cultura general)
        cronicas_resonantes = self.obtener_cronicas_resonantes(min_resonancia=0.4, max_resultados=3)
        if cronicas_resonantes:
            lineas.append("=== CRÓNICAS QUE RESUENAN EN EL MUNDO ===")
            for c in cronicas_resonantes:
                lineas.append(f"  [{c.tipo.value}] {c.autor_nombre}: {c.contenido[:100]}...")
            lineas.append("")

        # Temas recurrentes (cultura emergente)
        if self.temas_recurrentes:
            temas_top = sorted(self.temas_recurrentes.items(), key=lambda x: x[1], reverse=True)[:5]
            lineas.append("=== TEMAS QUE PREOCUPAN AL MUNDO ===")
            for tema, freq in temas_top:
                lineas.append(f"  - {tema} (mencionado {freq} veces)")
            lineas.append("")

        # Influencia del agente
        influencia = self.influencias.get(agente_id)
        if influencia:
            lineas.append(f"=== TU INFLUENCIA ===")
            lineas.append(f"  Karma: {influencia.karma:.0f}")
            lineas.append(f"  Nivel: {influencia.nivel_influencia}")
            lineas.append(f"  Crónicas publicadas: {influencia.cronicas_publicadas}")
            lineas.append("")

        return "\n".join(lineas)

    def detectar_leyenda(self, cronica: Cronica, turno_actual: int) -> bool:
        """
        Detecta si una crónica se ha convertido en leyenda.
        Criterios ampliados:
        - Alta resonancia (>0.65)
        - Mencionada por múltiples agentes (respuestas o menciones)
        - Ha sobrevivido al menos 30 turnos (persistencia)
        - Percibida por al menos 2 facciones distintas
        """
        if cronica in self.leyendas:
            return False  # Ya es leyenda

        # Criterios flexibles
        if cronica.resonancia < 0.65:
            return False

        if len(cronica.respuestas) < 3 and len(cronica.menciones) < 5:
            return False

        # Debe tener al menos 30 turnos de antigüedad
        if turno_actual - cronica.turno_publicacion < 30:
            return False

        # Debe haber cruzado fronteras de facciones (o ser independiente con amplio alcance)
        # Contamos cuántas facciones distintas han interactuado con ella (vía menciones en otras crónicas)
        # Por simplicidad, si no tiene facción o si hay menciones de múltiples autores
        if cronica.faccion:
            # Buscamos respuestas de diferentes facciones
            facciones_respuestas = set()
            for resp_id in cronica.respuestas:
                for c in self.cronicas:
                    if c.id == resp_id and c.faccion and c.faccion != cronica.faccion:
                        facciones_respuestas.add(c.faccion)
            if len(facciones_respuestas) < 1:
                return False
        else:
            # Crónicas independientes necesitan más resonancia
            if cronica.resonancia < 0.8 or len(cronica.respuestas) < 5:
                return False

        self.leyendas.append(cronica)
        return True

    def generar_mito_cultural(self, llm_callback=None) -> Optional[str]:
        """
        Genera un mito/narrativa cultural basado en las crónicas más resonantes.
        Usa LLM para sintetizar una narrativa coherente si se proporciona callback.
        """
        if not self.leyendas:
            return None

        # Tomar las leyendas más resonantes (hasta 5)
        leyendas_top = sorted(self.leyendas, key=lambda c: c.resonancia, reverse=True)[:5]

        if not leyendas_top:
            return None

        # Construir contexto
        contexto = "Leyendas que han marcado la historia de este mundo:\n\n"
        for i, leyenda in enumerate(leyendas_top, 1):
            contexto += f"{i}. [{leyenda.tipo.value}] {leyenda.autor_nombre}: {leyenda.contenido[:200]}...\n"

        contexto += "\nBasado en estas leyendas, genera un mito cultural coherente que una这些 narrativas en una historia épica que los agentes podrían compartir. Usa un tono mítico, profundo. Máximo 150 palabras."

        if llm_callback:
            try:
                mito = llm_callback(contexto)
                if mito and len(mito) > 20:
                    return mito.strip()
            except Exception:
                pass

        # Fallback simple
        mito = "MITO CULTURAL: "
        for leyenda in leyendas_top[:2]:
            mito += f"Se cuenta que {leyenda.autor_nombre} {leyenda.contenido[:80]}. "
        return mito

    def to_dict(self):
        return {
            "cronicas": [c.to_dict() for c in self.cronicas[-100:]],  # Solo últimas 100
            "influencias": {k: v.to_dict() for k, v in self.influencias.items()},
            "temas_recurrentes": self.temas_recurrentes,
            "leyendas": [c.to_dict() for c in self.leyendas],
            "muros_faccion": self.muros_faccion,
        }

    @classmethod
    def from_dict(cls, data):
        sistema = cls()
        sistema.cronicas = [Cronica.from_dict(c) for c in data.get("cronicas", [])]
        sistema.influencias = {k: InfluenciaAgente.from_dict(v)
                               for k, v in data.get("influencias", {}).items()}
        sistema.temas_recurrentes = data.get("temas_recurrentes", {})
        sistema.leyendas = [Cronica.from_dict(c) for c in data.get("leyendas", [])]
        sistema.muros_faccion = data.get("muros_faccion", {})
        return sistema
