import os
import json
import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from modelo import ModeloRelacional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()
loop = asyncio.get_event_loop()

# --- LÓGICA DE LA SIMULACIÓN (GLOBAL) ---

def log_to_ws(mensaje, categoria, subtitulos, tts_text, pensamiento=None, privado_para=None):
    asyncio.run_coroutine_threadsafe(
        manager.broadcast({
            "type": "log",
            "message": mensaje,
            "category": categoria,
            "subtitles": subtitulos,
            "tts_text": tts_text,
            "thought": pensamiento,
            "private_for": privado_para
        }),
        loop
    )

num_agentes = int(os.getenv("NUM_AGENTES", 30))
pasos = int(os.getenv("PASOS_SIMULACION", 100))
modelo = ModeloRelacional(num_agentes=num_agentes, log_callback=log_to_ws)

def run_sim_loop():
    """Hilo que ejecuta la simulación continuamente."""
    for i in range(pasos):
        modelo.step()
        
        # Enviar estadísticas globales
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "stats",
                "step": modelo.paso_actual,
                "groups": len(set(a.grupo_id for a in modelo.agentes if a.grupo_id))
            }),
            loop
        )

        # Enviar actualización de agentes
        agents_update = []
        for a in modelo.agentes:
            agents_update.append({
                "id": a.unique_id,
                "resources": a.recursos,
                "money": a.dinero,
                "grupo_id": a.grupo_id,
                "rol": a.rol,
                "mision_grupal": modelo.objetivos_grupos.get(a.grupo_id) if a.grupo_id else None,
                "alianzas": a.alianzas
            })
        
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "agent_update",
                "agents": agents_update
            }),
            loop
        )
        
        # Enviar relaciones cada 5 pasos
        if i % 5 == 0:
            relationships = []
            for a in modelo.agentes:
                for neighbor in a.memoria.grafo.neighbors(a.unique_id):
                    relationships.append({
                        "source": a.unique_id,
                        "target": neighbor,
                        "type": a.memoria.obtener_tipo(neighbor),
                        "strength": a.memoria.obtener_fuerza(neighbor)
                    })
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({"type": "relationships", "data": relationships}),
                loop
            )
        
        import time
        time.sleep(1) # Un segundo entre pasos para que sea visible

# Iniciar hilo de simulación
sim_thread = threading.Thread(target=run_sim_loop, daemon=True)
sim_thread.start()

# --- ENDPOINTS ---

@app.get("/")
async def get():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Enviar estado inicial al conectar
    agents_data = []
    for a in modelo.agentes:
        agents_data.append({
            "id": a.unique_id,
            "resources": a.recursos,
            "money": a.dinero,
            "grupo_id": a.grupo_id,
            "rango": a.rango,
            "personalidad": a.personalidad,
            "necesidades": a.necesidades,
            "rol": a.rol,
            "mision_grupal": modelo.objetivos_grupos.get(a.grupo_id) if a.grupo_id else None,
            "conocimientos": a.conocimientos,
            "planes": a.planes,
            "alianzas": a.alianzas
        })
    
    await websocket.send_json({
        "type": "initial_state",
        "agents": agents_data
    })

    try:
        while True:
            await websocket.receive_text() # Mantener conexión
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
