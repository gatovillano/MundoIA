
import sys
import os
import json
import time

# Añadir el directorio actual al path para poder importar los módulos
sys.path.append(os.getcwd())

from core.modelo import Simulation, SocialRecSys, Post
from api.api import SessionManager

def test_comments():
    sim = Simulation(user_id="test_user")
    sim.start_empty = True
    
    # Asegurar que social_recsys está inicializado
    from core.modelo import SocialRecSys
    sim.social_recsys = SocialRecSys(sim.db, sim.user_id, load_from_db=False, modelo=sim)
    
    # Crear un post
    post = sim.social_recsys.crear_post(
        user_id="test_user",
        autor_id="test_agent",
        contenido="Hello World",
        tipo="post",
        temas=["General"]
    )
    post_id = post.id
    print(f"Created post with ID: {post_id}")
    
    # Agregar un comentario
    sim.social_recsys.agregar_comentario(
        post_id=post_id,
        autor_id="arquitecto_test_user",
        contenido="This is a test comment"
    )
    
    # Verificar en memoria
    comments = sim.social_recsys.interest_recsys.comentarios.get(post_id, [])
    print(f"Comments in interest_recsys: {comments}")
    
    post_in_sim = sim.social_recsys.interest_recsys.posts.get(post_id)
    print(f"Comments count in post: {post_in_sim.comentarios}")
    print(f"Comments detail in post: {getattr(post_in_sim, 'comentarios_detalle', 'MISSING')}")

    # Verificar payload de stats
    sm = SessionManager()
    stats = sm._build_stats_payload(sim, "test_user")
    
    feed = stats.get("socialFeed", [])
    test_post = next((p for p in feed if p["id"] == post_id), None)
    
    if test_post:
        print(f"Post found in feed. Comments: {test_post.get('comentarios')}")
        print(f"Comments Detail: {test_post.get('comentarios_detalle')}")
    else:
        print("Post NOT found in feed!")

if __name__ == "__main__":
    test_comments()
