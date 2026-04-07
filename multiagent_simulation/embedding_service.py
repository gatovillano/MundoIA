"""
Servicio de Embeddings y Búsqueda Vectorial para Memoria Persistente.

Integra ChromaDB con sentence-transformers para búsqueda semántica
reemplazando el keyword matching actual.
"""

import os
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

# Configuración
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


@dataclass
class VectorSearchResult:
    """Resultado de búsqueda vectorial"""
    text: str
    score: float
    metadata: Dict[str, Any]
    memory_id: str


class EmbeddingService:
    """
    Servicio singleton para manejar embeddings y búsqueda vectorial.
    Utiliza ChromaDB como store vectorial y sentence-transformers como embedding model.
    """
    _instance = None
    _client: Optional[chromadb.PersistentClient] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inicializa ChromaDB y el modelo de embeddings."""
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self._model = SentenceTransformer(EMBEDDING_MODEL)

        # Definir función de embedding para ChromaDB
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )

    def get_collection(self, agent_id: str) -> chromadb.Collection:
        """
        Obtiene o crea una colección para un agente específico.
        Las colecciones se named 'agent_{agent_id}'.
        """
        collection_name = f"agent_{agent_id}"
        try:
            collection = self._client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_fn
            )
        except Exception:
            collection = self._client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn
            )
        return collection

    def generate_embedding(self, text: str) -> List[float]:
        """Genera embedding para un texto usando el modelo local."""
        if self._model is None:
            raise RuntimeError("EmbeddingService not initialized")
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def add_memory(self,
                   agent_id: str,
                   text: str,
                   memory_id: str,
                   metadata: Dict[str, Any] = None):
        """
        Añade o actualiza una memoria en el índice vectorial del agente.

        Args:
            agent_id: ID del agente
            text: Texto de la memoria (descripción o proposición)
            memory_id: ID único de la memoria
            metadata: Metadatos adicionales (turno, tipo, importancia, etc.)
        """
        collection = self.get_collection(agent_id)
        meta = metadata.copy() if metadata else {}
        meta["memory_id"] = memory_id

        # Usar upsert para manejar IDs duplicados
        collection.upsert(
            documents=[text],
            metadatas=[meta],
            ids=[memory_id]
        )

    def search_relevant(self,
                        agent_id: str,
                        query: str,
                        k: int = 5,
                        where: Dict[str, Any] = None) -> List[VectorSearchResult]:
        """
        Busca memorias relevantes usando similitud coseno en embeddings.

        Args:
            agent_id: ID del agente
            query: Texto de consulta (contexto actual)
            k: Número máximo de resultados
            where: Filtro opcional por metadatos (ej: {"tipo": "episodica"})

        Returns:
            Lista de VectorSearchResult ordenados por score descendente.
        """
        collection = self.get_collection(agent_id)

        try:
            results = collection.query(
                query_texts=[query],
                n_results=k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            # Si la colección está vacía o hay error, retornar lista vacía
            return []

        output = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                doc = results["documents"][0][i]
                meta = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                # ChromaDB usa distancia L2, convertir a similitud coseno aproximada
                score = max(0.0, 1.0 - distance)
                output.append(VectorSearchResult(
                    text=doc,
                    score=score,
                    metadata=meta,
                    memory_id=meta.get("memory_id", results["ids"][0][i])
                ))

        return output

    def delete_agent_memories(self, agent_id: str):
        """Elimina todas las memorias de un agente (útil para reset)."""
        collection_name = f"agent_{agent_id}"
        try:
            self._client.delete_collection(name=collection_name)
        except Exception:
            pass  # Si no existía, no hay problema

    def list_agent_memories(self, agent_id: str) -> List[Dict[str, Any]]:
        """Lista todas las memorias de un agente (para depuración)."""
        collection = self.get_collection(agent_id)
        try:
            results = collection.get(include=["documents", "metadatas"])
            memories = []
            for i, doc in enumerate(results["documents"]):
                memories.append({
                    "id": results["ids"][i],
                    "text": doc,
                    "metadata": results["metadatas"][i]
                })
            return memories
        except Exception:
            return []


# Instancia global
embedding_service = EmbeddingService()