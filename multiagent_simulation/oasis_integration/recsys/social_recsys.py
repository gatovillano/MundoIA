"""
Recommendation System para MundoIA - Feed de contenido social.
Inspirado en OASIS: interest-based + hot-score recommendations.
"""

import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Post:
    """Representa un post/publicación en la red social."""
    id: str
    autor_id: str
    contenido: str
    tipo: str  # "opinion", "noticia", "debate", "cronica"
    temas: List[str]  # Temas tratados
    likes: int = 0
    likes_por: List[str] = None  # Lista de autor_id que dieron like
    comentarios: int = 0
    timestamp: int = 0  # Paso en que se creó
    es_controvertido: bool = False

    def __post_init__(self):
        if self.likes_por is None:
            self.likes_por = []

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el post a diccionario."""
        return {
            "id": self.id,
            "autor_id": self.autor_id,
            "contenido": self.contenido,
            "tipo": self.tipo,
            "temas": self.temas,
            "likes": self.likes,
            "likes_por": self.likes_por,
            "comentarios": self.comentarios,
            "timestamp": self.timestamp,
            "es_controvertido": self.es_controvertido,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Deserializa un post desde diccionario."""
        return cls(
            id=data["id"],
            autor_id=data["autor_id"],
            contenido=data["contenido"],
            tipo=data["tipo"],
            temas=data.get("temas", []),
            likes=data.get("likes", 0),
            likes_por=data.get("likes_por", []),
            comentarios=data.get("comentarios", 0),
            timestamp=data.get("timestamp", 0),
            es_controvertido=data.get("es_controvertido", False),
        )


@dataclass
class Comentario:
    """Representa un comentario en un post."""
    id: str
    post_id: str
    autor_id: str
    contenido: str
    timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el comentario a diccionario."""
        return {
            "id": self.id,
            "post_id": self.post_id,
            "autor_id": self.autor_id,
            "contenido": self.contenido,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Comentario':
        """Deserializa un comentario desde diccionario."""
        return cls(
            id=data["id"],
            post_id=data["post_id"],
            autor_id=data["autor_id"],
            contenido=data["contenido"],
            timestamp=data.get("timestamp", 0),
        )


class InterestBasedRecSys:
    """
    Sistema de recomendación basado en intereses del agente.
    Filtra contenido relevante según los intereses y opiniones del agente.
    """

    # Mapeo de temas a intereses relacionados
    TEMA_A_INTERES = {
        "política": ["política", "gobierno", "leyes"],
        "economía": ["economía", "comercio", "dinero"],
        "ciencia": ["ciencia", "investigación", "descubrimiento"],
        "arte": ["arte", "cultura", "creación"],
        "religión": ["religión", "creencias", "espiritual"],
        "guerra": ["guerra", "conflicto", "batalla"],
        "salud": ["salud", "medicina", "bienestar"],
        "educación": ["educación", "estudio", "aprendizaje"],
        "medio_ambiente": ["naturaleza", "recursos", "clima"],
        "social": ["social", "relaciones", "comunidad"],
    }

    def __init__(self):
        self.posts: Dict[str, Post] = {}
        self.comentarios: Dict[str, List[Comentario]] = {}
        self.contador_posts = 0

    def crear_post(self, autor_id: str, contenido: str, 
                   tipo: str = "opinion", temas: List[str] = None,
                   timestamp: int = 0) -> Post:
        """Crea un nuevo post en el sistema."""
        self.contador_posts += 1
        post_id = f"post_{self.contador_posts}"
        
        # Detectar temas del contenido
        if not temas:
            temas = self._detectar_temas(contenido)
        
        post = Post(
            id=post_id,
            autor_id=autor_id,
            contenido=contenido,
            tipo=tipo,
            temas=temas,
            timestamp=timestamp,
        )
        
        self.posts[post_id] = post
        self.comentarios[post_id] = []
        return post

    def _detectar_temas(self, contenido: str) -> List[str]:
        """Detecta los temas de un contenido basándose en palabras clave."""
        contenido_lower = contenido.lower()
        temas_encontrados = []
        
        for tema, keywords in self.TEMA_A_INTERES.items():
            if any(kw in contenido_lower for kw in keywords):
                temas_encontrados.append(tema)
        
        if not temas_encontrados:
            temas_encontrados = ["general"]
        
        return temas_encontrados

    def agregar_comentario(self, post_id: str, autor_id: str, contenido: str) -> Comentario:
        """Agrega un comentario a un post."""
        if post_id not in self.comentarios:
            self.comentarios[post_id] = []
        
        comentario_id = f"comment_{post_id}_{len(self.comentarios[post_id])}"
        comentario = Comentario(
            id=comentario_id,
            post_id=post_id,
            autor_id=autor_id,
            contenido=contenido,
            timestamp=0,
        )
        
        self.comentarios[post_id].append(comentario)
        
        # Actualizar contador de comentarios del post
        if post_id in self.posts:
            self.posts[post_id].comentarios += 1
        
        return comentario

    def likear_post(self, post_id: str, autor_id: str = None) -> bool:
        """Da like a un post. Registra quién dio el like."""
        if post_id in self.posts:
            post = self.posts[post_id]
            # Evitar likes duplicados del mismo autor
            if autor_id and autor_id not in post.likes_por:
                post.likes_por.append(autor_id)
                post.likes += 1
            elif not autor_id:
                # Backward compatibility: si no se especifica autor, solo incrementar contador
                post.likes += 1
            return True
        return False

    def get_feed(self, agente, limite: int = 10, paso_actual: int = 0) -> List[Post]:
        """
        Genera el feed personalizado para un agente.
        
        Args:
            agente: El agente que solicita el feed
            limite: Número máximo de posts a retornar
            paso_actual: Paso actual de la simulación
            
        Returns:
            Lista de posts relevantes para el agente
        """
        if not self.posts:
            return []
        
        # Obtener intereses del agente
        intereses = getattr(agente, "intereses", []) or []
        
        # Scoring de cada post
        scored_posts = []
        
        for post in self.posts.values():
            # No mostrar posts del propio agente
            if post.id == agente.unique_id:
                continue
            
            score = 0.0
            
            # 1. Score por intereses (temas)
            for tema in post.temas:
                if tema in intereses:
                    score += 3.0
            
            # 2. Score por likes (popularidad)
            score += post.likes * 0.5
            
            # 3. Score por comentarios (engagement)
            score += post.comentarios * 0.3
            
            # 4. Score por contenido reciente (recencia)
            antiguedad = paso_actual - post.timestamp
            if antiguedad < 10:
                score += 2.0
            elif antiguedad < 30:
                score += 1.0
            
            # 5. Score por opiniones fuertes del agente
            opiniones = getattr(agente, "opiniones_fuertes", {})
            for tema in post.temas:
                if tema in opiniones:
                    score += opiniones[tema] * 0.2
            
            # 6. Bonus por posts de seguidos
            # (Aquí se usaría la lista de seguidos del agente)
            
            scored_posts.append((score, post))
        
        # Ordenar por score descendente
        scored_posts.sort(key=lambda x: x[0], reverse=True)
        
        # Retornar top N
        return [post for _, post in scored_posts[:limite]]

    def get_interacciones_usuario(self, usuario_id: str) -> List[Dict]:
        """Obtiene todas las interacciones (likes y comentarios) en los posts de un usuario."""
        interacciones = []
        for post_id, post in self.posts.items():
            if post.autor_id == usuario_id:
                # Añadir likes
                for liker_id in post.likes_por:
                    interacciones.append({
                        "tipo": "like",
                        "post_id": post_id,
                        "autor_interaccion": liker_id,
                        "contenido_post": post.contenido[:30] + "..."
                    })
                # Añadir comentarios
                if post_id in self.comentarios:
                    for com in self.comentarios[post_id]:
                        interacciones.append({
                            "tipo": "comentario",
                            "post_id": post_id,
                            "autor_interaccion": com.autor_id,
                            "contenido_interaccion": com.contenido,
                            "contenido_post": post.contenido[:30] + "..."
                        })
        return interacciones

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el estado del sistema de recomendación a diccionario."""
        return {
            "posts": {post_id: post.to_dict() for post_id, post in self.posts.items()},
            "comentarios": {
                post_id: [com.to_dict() for com in com_list]
                for post_id, com_list in self.comentarios.items()
            },
            "contador_posts": self.contador_posts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterestBasedRecSys':
        """Deserializa el sistema de recomendación desde diccionario."""
        recsys = cls()
        recsys.contador_posts = data.get("contador_posts", 0)
        
        # Restaurar posts
        for post_id, post_data in data.get("posts", {}).items():
            recsys.posts[post_id] = Post.from_dict(post_data)
        
        # Restaurar comentarios
        for post_id, com_list in data.get("comentarios", {}).items():
            recsys.comentarios[post_id] = [Comentario.from_dict(com) for com in com_list]
        
        return recsys


class HotScoreRecSys:
    """
    Sistema de recomendación basado en "calor" (popularidad + recencia).
    Similar al algoritmo de Reddit para trending posts.
    """

    @staticmethod
    def calcular_hot_score(post: Post, paso_actual: int) -> float:
        """
        Calcula el 'hot score' de un post.
        Fórmula: log10(max(|upvotes - downvotes|, 1)) + sign(ups-downs) * t / 45000
        Adaptado para MundoIA: likes como upvotes, sin downvotes.
        """
        # Likes como upvotes
        ups = post.likes + 1  # Mínimo 1 para evitar log(0)
        base_score = ups
        
        # Factor de tiempo (posts más recientes tienen ventaja)
        antiguedad = paso_actual - post.timestamp
        tiempo_factor = antiguedad / 1000  # Decaimiento suave
        
        # Score final
        import math
        hot = math.log10(base_score) - tiempo_factor
        
        return hot

    @staticmethod
    def get_trending(posts: Dict[str, Post], paso_actual: int, limite: int = 10) -> List[Post]:
        """Retorna los posts trending ordenados por hot score."""
        if not posts:
            return []
        
        scored = []
        for post in posts.values():
            hot = HotScoreRecSys.calcular_hot_score(post, paso_actual)
            scored.append((hot, post))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [post for _, post in scored[:limite]]


class SocialRecSys:
    """
    Sistema de recomendación unificado que combina:
    - Interest-based recommendations
    - Hot-score (trending) recommendations
    - Following-based (in-network) content
    """

    def __init__(self):
        self.interest_recsys = InterestBasedRecSys()
        self.hot_recsys = HotScoreRecSys()
        self.seguidos: Dict[str, set] = {}  # agente_id -> set de seguidos

    def follow(self, follower_id: str, followed_id: str) -> bool:
        """Un agente sigue a otro."""
        if follower_id == followed_id:
            return False
        
        if follower_id not in self.seguidos:
            self.seguidos[follower_id] = set()
        
        self.seguidos[follower_id].add(followed_id)
        return True

    def unfollow(self, follower_id: str, followed_id: str) -> bool:
        """Un agente deja de seguir a otro."""
        if follower_id in self.seguidos and followed_id in self.seguidos[follower_id]:
            self.seguidos[follower_id].remove(followed_id)
            return True
        return False

    def get_siguiendo(self, agente_id: str) -> List[str]:
        """Retorna la lista de IDs que sigue un agente."""
        return list(self.seguidos.get(agente_id, set()))

    def get_seguidores(self, agente_id: str) -> List[str]:
        """Retorna la lista de IDs que siguen a un agente."""
        seguidores = []
        for sid, seguidos in self.seguidos.items():
            if agente_id in seguidos:
                seguidores.append(sid)
        return seguidores

    def get_feed_hibrido(self, agente, paso_actual: int, limite: int = 15) -> Dict:
        """
        Genera un feed híbrido que combina:
        - 40% contenido de seguidos (in-network)
        - 40% contenido recomendado por intereses
        - 20% contenido trending
        """
        posts = self.interest_recsys.posts
        seguidos = self.get_siguiendo(agente.unique_id)
        
        # In-network posts (de seguidos)
        in_network = [p for p in posts.values() 
                      if p.autor_id in seguidos and p.autor_id != agente.unique_id]
        in_network.sort(key=lambda p: p.timestamp, reverse=True)
        
        # Interest-based
        interest_feed = self.interest_recsys.get_feed(agente, limite=limite, paso_actual=paso_actual)
        
        # Trending
        trending = self.hot_recsys.get_trending(posts, paso_actual, limite=limite//2)
        
        # Mezclar
        resultado = {
            "in_network": in_network[:limite // 3],
            "recommended": interest_feed[:limite // 3],
            "trending": trending[:limite // 2],
            "all_posts": list(posts.values()),
        }
        
        return resultado

    # Delegar métodos
    def crear_post(self, autor_id: str, contenido: str, 
                   tipo: str = "opinion", temas: List[str] = None,
                   timestamp: int = 0) -> Post:
        return self.interest_recsys.crear_post(autor_id, contenido, tipo, temas, timestamp)

    def agregar_comentario(self, post_id: str, autor_id: str, contenido: str) -> Comentario:
        return self.interest_recsys.agregar_comentario(post_id, autor_id, contenido)

    def likear_post(self, post_id: str, autor_id: str = None) -> bool:
        return self.interest_recsys.likear_post(post_id, autor_id)

    def get_feed(self, agente, paso_actual: int, limite: int = 10) -> List[Post]:
        return self.interest_recsys.get_feed(agente, limite, paso_actual)

    def get_trending(self, paso_actual: int, limite: int = 10) -> List[Post]:
        return self.hot_recsys.get_trending(self.interest_recsys.posts, paso_actual, limite)

    def get_interacciones_usuario(self, usuario_id: str) -> List[Dict]:
        return self.interest_recsys.get_interacciones_usuario(usuario_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa todo el SocialRecSys a diccionario."""
        return {
            "interest_recsys": self.interest_recsys.to_dict(),
            "seguidos": {k: list(v) for k, v in self.seguidos.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SocialRecSys':
        """Deserializa el SocialRecSys desde diccionario."""
        social_recsys = cls()
        
        # Restaurar interest_recsys
        interest_data = data.get("interest_recsys", {})
        if interest_data:
            social_recsys.interest_recsys = InterestBasedRecSys.from_dict(interest_data)
        
        # Restaurar seguidos (convertir listas a sets)
        seguidos_data = data.get("seguidos", {})
        for follower_id, followed_list in seguidos_data.items():
            social_recsys.seguidos[follower_id] = set(followed_list)
        
        return social_recsys