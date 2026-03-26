
import os
import json
import asyncio
from dotenv import load_dotenv
from cerebro_llm import CerebroLLM

# Mock classes to avoid full imports
class MockModelo:
    def __init__(self):
        self.asambleas_globales = []
        self.facciones_leyes = {"propuestas": []}
        self.paso_actual = 5
        self.price_history = [1.0, 1.2, 1.1]

class MockAgente:
    def __init__(self, id, rol='Ciudadano', x=10, y=10):
        self.unique_id = id
        self.rol = rol
        self.x = x
        self.y = y
        self.dinero = 100.0
        self.recursos = 50.0
        self.necesidades = {"alimento": 8.0, "salud": 10.0, "descanso": 9.0, "social": 5.0, "seguridad": 7.0}
        self.personalidad = {"amabilidad": 0.8, "hostilidad": 0.2, "curiosidad": 0.6}
        self.experiencia = {"medicina": 0, "comercio": 0, "combate": 0, "exploracion": 0, "social": 0, "ingenieria": 0, "agricultura": 0}
        self.profesion = None
        self.grupo_id = None
        self.modelo = MockModelo()
        self.memoria = type('obj', (object,), {'obtener_fuerza': lambda x: 0.5})

async def test_cerebro():
    load_dotenv()
    # Loading .env if needed (though docker container has its own injected)
    
    cerebro = CerebroLLM()
    # Check if config is already set in cerebro_llm.py from env vars
    
    a1 = MockAgente("A1", rol="Líder")
    a2 = MockAgente("A2")
    contexto = "Estás en un claro del bosque. Ves a A2 cerca."
    
    print(f"Testing with model: {cerebro.model}")
    print(f"API key loaded: {'Yes' if cerebro.api_key and len(cerebro.api_key) > 5 else 'No'}")
    
    try:
        decision = cerebro.generar_pensamiento_y_accion(a1, a2, contexto)
        
        print("\n--- LLM RESPONSE ---")
        print(json.dumps(decision, indent=2))
        
        # Check if pensamiento is in message
        mensaje = decision.get("mensaje", "")
        pensamiento = decision.get("pensamiento", "")
        if pensamiento in mensaje and len(pensamiento) > 5:
            print("\n❌ ISSUE DETECTED: Thought is included in the message!")
        else:
            print("\n✅ Message looks clean (or thought is not a direct copy).")
            
    except Exception as e:
        print(f"Error during LLM call: {e}")

if __name__ == "__main__":
    asyncio.run(test_cerebro())
