
import sys
import os
from unittest.mock import MagicMock

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.entities.agent import Agente

def test_votos_recibidos():
    print("Iniciando prueba de Agente.votos_recibidos...")
    
    # Mock del modelo
    modelo = MagicMock()
    modelo.mapa_size = 20
    modelo.agentes = []
    
    try:
        agente = Agente(unique_id="test_agent", modelo=modelo)
        print(f"Agente creado: {agente.unique_id}")
        
        # Verificar que votos_recibidos existe
        print(f"votos_recibidos: {agente.votos_recibidos}")
        
        # Intentar llamar a calcular_capital_social
        # Necesitamos mockear algunos atributos si no se inicializaron
        if not hasattr(agente, 'seguidores'): agente.seguidores = 0
        if not hasattr(agente, 'siguiendo'): agente.siguiendo = 0
        if not hasattr(agente, 'likes_recibidos'): agente.likes_recibidos = 0
        if not hasattr(agente, 'posts_publicados'): agente.posts_publicados = 0
        if not hasattr(agente, 'debates_ganados'): agente.debates_ganados = 0
        if not hasattr(agente, 'debates_perdidos'): agente.debates_perdidos = 0
        if not hasattr(agente, 'comentarios_realizados'): agente.comentarios_realizados = 0
        
        capital = agente.calcular_capital_social()
        print(f"Capital Social calculado: {capital}")
        print("PRUEBA SUPERADA: No se produjo AttributeError")
        
    except AttributeError as e:
        print(f"PRUEBA FALLIDA: AttributeError detectado: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_votos_recibidos()
