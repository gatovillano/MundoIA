import asyncio
import json
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from modelo import ModeloRelacional
import uvicorn
import os

app = FastAPI()

# Clase para gestionar las conexiones WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

@app.get("/tts")
async def get_tts(text: str):
    tts_url = os.getenv("TTS_URL", "http://localhost:5050/v1/audio/speech")
    payload = {
        "input": text,
        "model": "tts-1",
        "voice": "alloy"
    }
    import requests
    response = requests.post(tts_url, json=payload)
    from fastapi.responses import Response
    return Response(content=response.content, media_type="audio/mpeg")

@app.get("/")
async def get():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

import threading

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    loop = asyncio.get_running_loop()
    
    try:
        num_agentes = int(os.getenv("NUM_AGENTES", 30))
        pasos = int(os.getenv("PASOS_SIMULACION", 100))
        
        def log_to_ws(mensaje, categoria, subtitulos, tts_text):
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "log",
                    "message": mensaje,
                    "category": categoria,
                    "subtitles": subtitulos,
                    "tts_text": tts_text
                }),
                loop
            )

        modelo = ModeloRelacional(num_agentes=num_agentes, log_callback=log_to_ws)
        
        # Enviar estado inicial de agentes
        def send_initial_state():
            agents_data = []
            for a in modelo.agentes:
                agents_data.append({
                    "id": a.unique_id,
                    "resources": a.recursos,
                    "grupo": a.grupo_id,
                    "rango": a.rango,
                    "personalidad": a.personalidad,
                    "necesidades": a.necesidades
                })
            
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "initial_state",
                    "agents": agents_data
                }),
                loop
            )
        
        send_initial_state()
        
        def run_sim():
            for i in range(pasos):
                modelo.step()
                
                # Enviar estadísticas
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({
                        "type": "stats",
                        "step": i + 1,
                        "groups": len(set(a.grupo_id for a in modelo.agentes if a.grupo_id))
                    }),
                    loop
                )
                
                # Enviar relaciones cada 5 pasos
                if i % 5 == 0:
                    relationships = []
                    for a in modelo.agentes:
                        for neighbor in a.memoria.grafo.neighbors(a.unique_id):
                            tipo = a.memoria.obtener_tipo(neighbor)
                            fuerza = a.memoria.obtener_fuerza(neighbor)
                            relationships.append({
                                "source": a.unique_id,
                                "target": neighbor,
                                "type": tipo,
                                "strength": fuerza
                            })
                    
                    asyncio.run_coroutine_threadsafe(
                        manager.broadcast({
                            "type": "relationships",
                            "data": relationships
                        }),
                        loop
                    )
                
                import time
                time.sleep(0.5)

        # Ejecutar en un hilo separado
        thread = threading.Thread(target=run_sim)
        thread.start()
        
        # Mantener la conexión abierta
        while thread.is_alive():
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Error en WebSocket: {e}")
    finally:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
