import os
import requests
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

TTS_URL = os.getenv("TTS_URL", "http://localhost:5000/tts") # Ajusta según tu contenedor

@tool
def hablar_con_voz(texto: str, agente_id: int):
    """
    Envía el texto al contenedor de TTS para que el agente hable físicamente.
    """
    try:
        # Formato compatible con OpenAI TTS (que usa tu contenedor)
        payload = {
            "input": texto,
            "model": "tts-1",
            "voice": "alloy" if agente_id % 2 == 0 else "nova"
        }
        response = requests.post(TTS_URL, json=payload, timeout=5)
        if response.status_code == 200:
            # En una simulación real, aquí podrías guardar el audio o enviarlo al frontend
            # Por ahora, confirmamos que se generó.
            return f"Voz generada para Agente {agente_id}"
        return f"Error TTS: {response.status_code}"
    except Exception as e:
        return f"Servicio TTS no disponible: {str(e)}"

@tool
def registrar_en_diario(agente_id: int, pensamiento: str):
    """
    Permite al agente guardar un pensamiento privado en su diario personal.
    """
    folder = "diarios"
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    filename = f"{folder}/agente_{agente_id}.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"Pensamiento: {pensamiento}\n")
    return f"Pensamiento guardado en el diario del Agente {agente_id}"

# Lista de herramientas disponibles para los agentes
herramientas_agentes = [hablar_con_voz, registrar_en_diario]
