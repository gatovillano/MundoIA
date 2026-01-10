import os
from litellm import completion
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class CerebroLLM:
    def __init__(self):
        self.model = os.getenv("MODEL_NAME", "openrouter/google/gemini-2.0-flash-exp:free")
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

    def generar_interaccion(self, agente_yo, agente_otro, contexto):
        """
        Usa LiteLLM para generar una respuesta basada en la personalidad y estado de los agentes.
        """
        prompt = f"""
        Eres un agente en una simulación social. 
        Tu ID es {agente_yo.unique_id}. 
        Tu personalidad: {agente_yo.personalidad}.
        Tus recursos: {agente_yo.recursos:.1f}.
        Tus necesidades: {agente_yo.necesidades}.
        
        Estás interactuando con el Agente {agente_otro.unique_id}.
        Relación con él: {agente_yo.memoria.obtener_tipo(agente_otro.unique_id)} (Fuerza: {agente_yo.memoria.obtener_fuerza(agente_otro.unique_id):.1f}).
        Contexto de la interacción: {contexto}.

        Escribe una frase corta (máximo 15 palabras) que dirías en esta situación. 
        Sé coherente con tu personalidad. Si eres competitivo, sé rudo. Si eres amable, sé cálido.
        Responde SOLO con la frase, sin explicaciones.
        """

        # Si no hay API KEY real, simulamos una respuesta para no romper la ejecución
        if not self.api_key or self.api_key == "tu_api_key_aqui":
            return self._simular_respuesta(agente_yo, contexto)

        try:
            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"      ⚠️ [ERROR LLM] {e}. Usando respuesta simulada.")
            return self._simular_respuesta(agente_yo, contexto)

    def _simular_respuesta(self, agente, contexto):
        """Fallback en caso de no tener API Key."""
        if "hambre" in contexto or "comida" in contexto:
            return "Necesito sustento... ¿tienes algo que compartir?"
        if "competir" in contexto or "ataque" in contexto:
            return "¡Aléjate! Estos recursos son vitales para mi ascenso."
        return "El flujo de datos es estable. Sigamos observando."

# Instancia global
cerebro_llm = CerebroLLM()
