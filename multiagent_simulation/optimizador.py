from functools import lru_cache
from collections import deque
import numpy as np

class DecisionOptimizer:
    def __init__(self, llm_caller_batch, similarity_threshold=0.3):
        self.llm_caller_batch = llm_caller_batch
        self.similarity_threshold = similarity_threshold
        self.decision_cache = {}  # {(agent_id, turn): decision}
        self.cache_timestamps = {}
    
    def _cosine_sim(self, a, b):
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0: return 0.0
        return dot / (norm_a * norm_b)

    def _get_state_vector(self, agente):
        necesidades = agente.necesidades
        return np.array([
            necesidades.get("alimento", 10.0) / 10.0,
            necesidades.get("salud", 10.0) / 10.0,
            necesidades.get("descanso", 10.0) / 10.0,
            min(agente.dinero / 200.0, 1.0),
            agente.personalidad.get("curiosidad", 0.5),
            agente.personalidad.get("amabilidad", 0.5)
        ])
    
    def process_agents_batch(self, agentes, turno_actual, build_context_func):
        # 1. Agrupar por similitud de estado
        state_vectors = [self._get_state_vector(a) for a in agentes]
        batches = []
        used = [False] * len(agentes)
        
        for i in range(len(agentes)):
            if used[i]: continue
            batch_indices = [i]
            for j in range(i+1, len(agentes)):
                if not used[j] and self._cosine_sim(state_vectors[i], state_vectors[j]) >= self.similarity_threshold:
                    batch_indices.append(j)
                    
            batches.append([agentes[idx] for idx in batch_indices])
            for idx in batch_indices: used[idx] = True
            
        decisiones = {}
        for batch in batches:
            batch_contexts = []
            for agente in batch:
                estado_critico = any(v < 0.3 for v in self._get_state_vector(agente)[:3])
                
                # Caching: Si el estado es MUY bueno y no hay alertas críticas repetimos si está en caché reciente
                state_hash = hash(str(np.round(self._get_state_vector(agente), decimals=1)))
                cached = None
                if not estado_critico and (turno_actual - self.cache_timestamps.get(state_hash, -10) <= 2):
                    cached = self.decision_cache.get(state_hash)
                
                if cached:
                    decisiones[agente.unique_id] = cached
                else:
                    batch_contexts.append({
                        "id": agente.unique_id,
                        "contexto": build_context_func(agente),
                        "estado_critico": estado_critico,
                        "state_hash": state_hash
                    })
            
            # Llamar LLM para los no cacheados
            if batch_contexts:
                llm_response = self.llm_caller_batch(batch_contexts)
                if llm_response:
                    for item in llm_response:
                        agente_id = item.get("id")
                        accion = item.get("resultado")
                        if agente_id and accion:
                            decisiones[agente_id] = accion
                            # Buscar el hash correspondiente para este agente_id
                            shash = next((bc["state_hash"] for bc in batch_contexts if bc["id"] == agente_id), None)
                            if shash:
                                self.decision_cache[shash] = accion
                                self.cache_timestamps[shash] = turno_actual
                                
        return decisiones
