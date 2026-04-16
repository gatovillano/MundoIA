"""
Sistema de Memoria Persistente Tripartita — Refactorizado para usar Base de Datos (PostgreSQL/JSONB).
Mantiene toda la lógica de scoring, indexing y consolidación original sin usar archivos locales.

Tres niveles de memoria:
1. EPISÓDICA: Qué vivió el agente (eventos, encuentros, descubrimientos)
2. SEMÁNTICA: Qué aprendió (hechos, reglas, conocimientos)
3. PROCEDIMENTAL: Qué sabe hacer (skills, técnicas, estrategias)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)

# Optional embedding service
try:
    from api.embedding_service import get_embedding_service
    HAS_EMBEDDING = True
except ImportError:
    HAS_EMBEDDING = False


class TipoMemoria(Enum):
    EPISODICA = "episodica"      # Eventos vividos
    SEMANTICA = "semantica"      # Hechos aprendidos
    PROCEDIMENTAL = "procedimental"  # Skills y conocimientos prácticos


class ImportanciaMemoria(Enum):
    TRIVIAL = 0.1
    BAJA = 0.3
    MEDIA = 0.5
    ALTA = 0.7
    CRITICA = 0.9


@dataclass
class MemoriaEpisodica:
    """Un recuerdo episódico: algo que el agente vivió."""
    id: str
    descripcion: str
    turno: int
    importancia: float  # 0.0 a 1.0
    agentes_involucrados: List[str] = field(default_factory=list)
    ubicacion: Optional[Tuple[int, int]] = None
    emociones: List[str] = field(default_factory=list)
    consolidada: bool = False  # Si ya fue integrada en MEMORY_CORE

    def to_dict(self):
        return {
            "id": self.id,
            "descripcion": self.descripcion,
            "turno": self.turno,
            "importancia": self.importancia,
            "agentes_involucrados": self.agentes_involucrados,
            "ubicacion": self.ubicacion,
            "emociones": self.emociones,
            "consolidada": self.consolidada,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class MemoriaSemantica:
    """Un hecho o conocimiento que el agente aprendió."""
    id: str
    proposicion: str  # "El desierto es peligroso de noche"
    certeza: float  # 0.0 a 1.0, cuán seguro está
    fuente: str  # "observacion_directa", "testimonio", "inferencia", "lectura_cronica"
    turno_aprendizaje: int
    contexto: str = ""  # Bajo qué circunstancias lo aprendió
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "proposicion": self.proposicion,
            "certeza": self.certeza,
            "fuente": self.fuente,
            "turno_aprendizaje": self.turno_aprendizaje,
            "contexto": self.contexto,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class MemoriaProcedimental:
    """Un saber-hacer: skill, técnica o estrategia."""
    id: str
    nombre: str
    descripcion: str
    dominio: float  # 0.0 a 1.0, qué tan bien lo domina
    contexto_uso: str  # Cuándo es útil
    turno_aprendizaje: int
    veces_usada: int = 0
    ultima_vez: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "dominio": self.dominio,
            "contexto_uso": self.contexto_uso,
            "turno_aprendizaje": self.turno_aprendizaje,
            "veces_usada": self.veces_usada,
            "ultima_vez": self.ultima_vez,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class MemoryCore:
    """
    MEMORY_CORE — Hechos duraderos que NUNCA deben olvidarse.
    """
    hechos_centrales: List[str] = field(default_factory=list)
    relaciones_clave: Dict[str, str] = field(default_factory=dict)  # agente -> tipo_relacion
    metas_activas: List[str] = field(default_factory=list)
    identidad_resumen: str = ""  # Resumen de quién es el agente

    def to_dict(self):
        return {
            "hechos_centrales": self.hechos_centrales,
            "relaciones_clave": self.relaciones_clave,
            "metas_activas": self.metas_activas,
            "identidad_resumen": self.identidad_resumen,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


def _generate_id(text: str, turno: int) -> str:
    """Genera un ID único para una memoria."""
    raw = f"{text}_{turno}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


class MemoriaPersistente:
    """
    Sistema de memoria tripartita refactorizado para persistencia basada en la DB principal (PostgreSQL).
    Mantiene la lógica original de scoring e indexing pero redirige el guardado a diccionarios para la DB.
    """

    def __init__(self, agente_id: str, user_id: str = "default", data: Optional[Dict] = None):
        self.agente_id = agente_id
        self.user_id = user_id

        # Memorias en RAM
        self.episodicas: List[MemoriaEpisodica] = []
        self.semanticas: List[MemoriaSemantica] = []
        self.procedimentales: List[MemoriaProcedimental] = []
        self.memory_core = MemoryCore()

        # Configuración
        self.max_episodicas_ram = 50
        self.max_semanticas_ram = 30
        self.umbral_consolidacion = 20
        self.ultimo_turno_consolidacion = 0

        # Flag para indexación lazy
        self.indexado = False

        # Cargar datos si se proporcionan
        if data:
            self.cargar_datos(data)

    @property
    def memoria_reciente(self) -> List[MemoriaEpisodica]:
        """Retorna las memorias episódicas recientes (últimas 10)."""
        return self.episodicas[-10:] if self.episodicas else []

    def to_dict(self) -> Dict[str, Any]:
        """Serializa todo el estado de la memoria para ser guardado en la columna JSONB de la DB."""
        return {
            "episodicas": [m.to_dict() for m in self.episodicas],
            "semanticas": [m.to_dict() for m in self.semanticas],
            "procedimentales": [m.to_dict() for m in self.procedimentales],
            "memory_core": self.memory_core.to_dict(),
            "ultimo_turno_consolidacion": self.ultimo_turno_consolidacion,
        }

    def cargar_datos(self, data: Dict[str, Any]):
        """Carga datos desde el diccionario de la DB."""
        if not data:
            return

        try:
            if data.get("memory_core"):
                self.memory_core = MemoryCore.from_dict(data["memory_core"])

            self.episodicas = [MemoriaEpisodica.from_dict(d) for d in data.get("episodicas", [])]
            self.semanticas = [MemoriaSemantica.from_dict(d) for d in data.get("semanticas", [])]
            self.procedimentales = [MemoriaProcedimental.from_dict(d) for d in data.get("procedimentales", [])]
            self.ultimo_turno_consolidacion = data.get("ultimo_turno_consolidacion", 0)

            # No indexar al cargar, será lazy
            # if HAS_EMBEDDING:
            #     self._indexar_memorias_en_chroma()
        except Exception as e:
            logger.error(f"Error cargando memoria del agente {self.agente_id}: {e}")

    def guardar_episodica(self, descripcion: str, turno: int, importancia: float,
                          agentes: List[str] = None, ubicacion: Tuple[int, int] = None,
                          emociones: List[str] = None) -> MemoriaEpisodica:
        """Registra un evento vivido por el agente."""
        mem = MemoriaEpisodica(
            id=_generate_id(descripcion, turno),
            descripcion=descripcion,
            turno=turno,
            importancia=importancia,
            agentes_involucrados=agentes or [],
            ubicacion=ubicacion,
            emociones=emociones or [],
        )
        self.episodicas.append(mem)
        self._indexar_memoria_en_chroma(mem, "episodica")

        if importancia >= 0.8:
            self.memory_core.hechos_centrales.append(f"[Turno {turno}] {descripcion}")
            if len(self.memory_core.hechos_centrales) > 50:
                self.memory_core.hechos_centrales.pop(0)

        return mem

    def _indexar_memoria_en_chroma(self, mem: Any, tipo: str):
        """Indexa memoria en ChromaDB con metadatos completos."""
        if not HAS_EMBEDDING:
            return
        try:
            if tipo == "episodica":
                texto = mem.descripcion
                metadata = {
                    "turno": mem.turno,
                    "importancia": mem.importancia,
                    "tipo": "episodica",
                    "agentes_involucrados": mem.agentes_involucrados,
                    "emociones": mem.emociones
                }
            elif tipo == "semantica":
                texto = mem.proposicion
                metadata = {
                    "turno_aprendizaje": mem.turno_aprendizaje,
                    "certeza": mem.certeza,
                    "tipo": "semantica",
                    "fuente": mem.fuente,
                    "tags": mem.tags
                }
            else:
                return

            embedding_service.add_memory(
                agent_id=self.agente_id,
                text=texto,
                memory_id=mem.id,
                metadata=metadata
            )
        except Exception:
            pass

    def _indexar_memorias_en_chroma(self):
        if not HAS_EMBEDDING: return
        for m in self.episodicas: self._indexar_memoria_en_chroma(m, "episodica")
        for m in self.semanticas: self._indexar_memoria_en_chroma(m, "semantica")

    def guardar_semantica(self, proposicion: str, turno: int, certeza: float = 0.7,
                          fuente: str = "observacion_directa", contexto: str = "",
                          tags: List[str] = None) -> MemoriaSemantica:
        mem = MemoriaSemantica(
            id=_generate_id(proposicion, turno),
            proposicion=proposicion,
            certeza=certeza,
            fuente=fuente,
            turno_aprendizaje=turno,
            contexto=contexto,
            tags=tags or [],
        )
        self.semanticas.append(mem)
        self._indexar_memoria_en_chroma(mem, "semantica")
        return mem

    def guardar_procedimental(self, nombre: str, descripcion: str, turno: int,
                               dominio: float = 0.3, contexto_uso: str = "") -> MemoriaProcedimental:
        mem = MemoriaProcedimental(_generate_id(nombre, turno), nombre, descripcion, dominio, contexto_uso, turno)
        self.procedimentales.append(mem)
        return mem

    def buscar_por_relevancia(self, contexto_actual: str, turno_actual: int,
                              max_resultados: int = 5) -> List[str]:
        """Busca relevantes usando vector indexing y scoring por recencia/importancia."""
        if HAS_EMBEDDING:
            embedding_service = get_embedding_service()
            # Indexación lazy
            if not self.indexado:
                try:
                    self._indexar_memorias_en_chroma()
                    self.indexado = True
                except Exception as e:
                    logger.error(f"Error indexando memorias para {self.agente_id}: {e}")
                    return self._buscar_por_keywords(contexto_actual, turno_actual, max_resultados)
            
            try:
                resultados = embedding_service.search_relevant(
                    agent_id=self.agente_id,
                    query=contexto_actual,
                    k=max_resultados * 3
                )
                if not resultados:
                    return self._buscar_por_keywords(contexto_actual, turno_actual, max_resultados)

                scored_results = []
                for r in resultados:
                    meta = r.metadata
                    score = r.score  # similitud coseno [0,1]
                    
                    if meta.get("tipo") == "episodica":
                        recencia = max(0.0, 1.0 - (turno_actual - meta.get("turno", turno_actual)) / 100.0)
                        imp = meta.get("importancia", 0.5)
                        rec_imp = (recencia + imp) / 2.0
                        score = score * 0.6 + rec_imp * 0.4
                        display = f"Recuerdo: {r.text}"
                    elif meta.get("tipo") == "semantica":
                        recencia = max(0.0, 1.0 - (turno_actual - meta.get("turno_aprendizaje", turno_actual)) / 100.0)
                        certeza = meta.get("certeza", 0.5)
                        rec_cer = (recencia + certeza) / 2.0
                        score = score * 0.6 + rec_cer * 0.4
                        display = f"Conocimiento: {r.text}"
                    else:
                        continue
                    scored_results.append((score, display))

                scored_results.sort(key=lambda x: x[0], reverse=True)
                return [s[1] for s in scored_results[:max_resultados]]
            except Exception:
                pass

        return self._buscar_por_keywords(contexto_actual, turno_actual, max_resultados)

    def _buscar_por_keywords(self, contexto_actual: str, turno_actual: int, max_resultados: int = 5) -> List[str]:
        contexto_lower = contexto_actual.lower()
        scores = []
        for mem in self.episodicas:
            score = (1.0 - (turno_actual - mem.turno) / 100.0) * 0.3 + mem.importancia * 0.3
            overlap = len(set(contexto_lower.split()) & set(mem.descripcion.lower().split()))
            score += (overlap / 5.0) * 0.4
            scores.append((score, f"Recuerdo: {mem.descripcion}"))
        for mem in self.semanticas:
            score = (1.0 - (turno_actual - mem.turno_aprendizaje) / 100.0) * 0.2 + mem.certeza * 0.3
            overlap = len(set(contexto_lower.split()) & set(mem.proposicion.lower().split()))
            score += (overlap / 5.0) * 0.5
            scores.append((score, f"Conocimiento: {mem.proposicion}"))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scores[:max_resultados]]

    def consolidar_memorias(self, turno_actual: int):
        if turno_actual - self.ultimo_turno_consolidacion < self.umbral_consolidacion:
            return
        self.ultimo_turno_consolidacion = turno_actual
        antiguas = [m for m in self.episodicas if m.turno < turno_actual - 30 and m.importancia < 0.6 and not m.consolidada]
        if antiguas:
            resumen = f"Resumen T{antiguas[0].turno}-{antiguas[-1].turno}: Integración de experiencias cotidianas."
            self.memory_core.hechos_centrales.append(resumen)
            for m in antiguas: m.consolidada = True
        
        if len(self.episodicas) > self.max_episodicas_ram:
            self.episodicas = self.episodicas[-self.max_episodicas_ram:]

    def obtener_contexto_memoria(self, turno_actual: int, contexto_actual: str = "") -> str:
        lineas = []
        if self.memory_core.hechos_centrales:
            lineas.append("\n=== MEMORIA CENTRAL ===")
            for hecho in self.memory_core.hechos_centrales[-10:]: lineas.append(f"  • {hecho}")
        if self.memory_core.relaciones_clave:
            lineas.append("\n=== RELACIONES ===")
            for a, r in self.memory_core.relaciones_clave.items(): lineas.append(f"  • {a}: {r}")
        if contexto_actual:
            relevantes = self.buscar_por_relevancia(contexto_actual, turno_actual, 3)
            if relevantes:
                lineas.append("\n=== ASOCIACIONES RECIENTES ===")
                for r in relevantes: lineas.append(f"  • {r}")
        return "\n".join(lineas)

    def registrar_interaccion_significativa(self, otro_agente: str, tipo: str, turno: int, detalle: str):
        self.guardar_episodica(f"{tipo.capitalize()} con {otro_agente}: {detalle}", turno, 0.7, agentes=[otro_agente])
        self.memory_core.relaciones_clave[otro_agente] = tipo
        if 0.7 >= 0.7:
            self.guardar_semantica(f"{otro_agente} es {tipo}", turno, 0.8, tags=["relacion", tipo])
