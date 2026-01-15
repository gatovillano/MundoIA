import os
import json
import asyncio
import threading
import requests
import random
import time
from typing import Dict, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Body
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# --- GESTOR DE SESIONES ---

class SessionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {} # user_id -> WebSocket
        self.simulations: Dict[str, ModeloRelacional] = {} # user_id -> ModeloRelacional
        self.simulation_threads: Dict[str, bool] = {} # user_id -> is_running

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"🔌 Usuario {user_id} conectado via WebSocket")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"🔌 Usuario {user_id} desconectado")

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                print(f"Error enviando a {user_id}: {e}")
                self.disconnect(user_id)

    def get_simulation(self, user_id: str) -> Optional[ModeloRelacional]:
        return self.simulations.get(user_id)

    def create_simulation(self, user_id: str):
        if user_id not in self.simulations:
            # Callback personalizado para este usuario
            def user_log_callback(mensaje, categoria, subtitulos, tts_text, pensamiento=None, privado_para=None):
                sim = self.simulations.get(user_id)
                paso = sim.paso_actual if sim else 0
                asyncio.run_coroutine_threadsafe(
                    self.send_to_user(user_id, {
                        "type": "log",
                        "step": paso,
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
            self.simulations[user_id] = ModeloRelacional(num_agentes=num_agentes, log_callback=user_log_callback, user_id=user_id)
            self.simulation_threads[user_id] = False # Inicia pausado
            print(f"🌍 Nueva simulación creada para {user_id}")
            return self.simulations[user_id]
        return self.simulations[user_id]

    def start_simulation_loop(self, user_id: str):
        if user_id not in self.simulations: return
        
        if self.simulation_threads.get(user_id): return # Ya está corriendo

        self.simulation_threads[user_id] = True
        
        def run_loop():
            print(f"▶️ Iniciando bucle de simulación para {user_id}")
            sim = self.simulations[user_id]
            while self.simulation_threads.get(user_id, False):
                sim.step()
                
                # Broadcast de estado
                asyncio.run_coroutine_threadsafe(
                    self.broadcast_state(user_id),
                    loop
                )
                
                time.sleep(0.3) # Ritmo de juego acelerado para sensación Real-Time

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()

    def stop_simulation_loop(self, user_id: str):
        self.simulation_threads[user_id] = False
        print(f"⏸️ Simulación pausada para {user_id}")

    async def broadcast_state(self, user_id: str):
        sim = self.simulations.get(user_id)
        if not sim: return

        # Construir diccionario de grupos dinámicos
        grupos_dinamicos = {}
        for grupo_id, mision in sim.objetivos_grupos.items():
            miembros = [a for a in sim.agentes if a.grupo_id == grupo_id]
            if miembros:  # Solo incluir grupos con miembros
                # Calcular recursos totales del grupo
                recursos_totales = sum(a.recursos for a in miembros)
                
                # Generar un color único para el grupo
                colores = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#F7DC6F", "#E056FD", "#686DE0"]
                color = colores[int(grupo_id) % len(colores)] if grupo_id.isdigit() else "#7c4dff"
                
                grupos_dinamicos[grupo_id] = {
                    "nombre": mision[:30] + "..." if len(mision) > 30 else mision,
                    "color": color,
                    "recursos": recursos_totales,
                    "tipo": "grupo_dinamico"  # Distinguir de civilizaciones
                }

        # Stats Globales + Civilizaciones + Grupos Dinámicos + Propuestas
        await self.send_to_user(user_id, {
            "type": "stats",
            "step": sim.paso_actual,
            "groups": len(set(a.grupo_id for a in sim.agentes if a.grupo_id)),
            "economy": sim.economia,
            "mapa": [[t.to_dict() for t in row] for row in sim.mapa],
            "weather": sim.weather,
            "lore": sim.lore,
            "civilizaciones": {k: {"nombre": v.nombre, "color": v.color, "recursos": v.recursos_globales, "tipo": "civilizacion"} for k, v in sim.civilizaciones.items()},
            "grupos_dinamicos": grupos_dinamicos,
            "propuestas": sim.facciones_leyes.get("propuestas", [])
        })

        # Agentes
        agents_update = []
        for a in sim.agentes:
            agents_update.append({
                "id": a.unique_id,
                "x": a.x, "y": a.y,
                "civilizacion_id": a.civilizacion_id,
                "resources": a.recursos,
                "money": a.dinero,
                "grupo_id": a.grupo_id,
                "rol": a.rol,
                "profesion": getattr(a, 'profesion', None),
                "reputacion": getattr(a, 'reputacion', 1.0),
                "necesidades": a.necesidades,
                "alianzas": a.alianzas,
                "personalidad": a.personalidad,
                "pensamiento": getattr(a, 'pensamiento_actual', "Esperando estímulos...")
            })
        
        await self.send_to_user(user_id, {
            "type": "agent_update",
            "agents": agents_update
        })

        # Relaciones (menos frecuente)
        if sim.paso_actual % 5 == 0:
            relationships = []
            for a in sim.agentes:
                for neighbor in a.memoria.grafo.neighbors(a.unique_id):
                    relationships.append({
                        "source": a.unique_id,
                        "target": neighbor,
                        "type": a.memoria.obtener_tipo(neighbor),
                        "strength": a.memoria.obtener_fuerza(neighbor)
                    })
            await self.send_to_user(user_id, {"type": "relationships", "data": relationships})


session_manager = SessionManager()
loop = asyncio.get_event_loop()

# --- MODELOS PYDANTIC ---

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class GameAction(BaseModel):
    user_id: str
    action: str # "start", "pause", "reset"

# --- ENDPOINTS ---

@app.get("/")
async def get():
    return {"message": "MundoIA Game Server Running"}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await session_manager.connect(user_id, websocket)
    
    # Verificar si tiene simulación activa, si no, crearla
    sim = session_manager.get_simulation(user_id)
    if not sim:
        sim = session_manager.create_simulation(user_id)
    
    # Enviar estado inicial
    await session_manager.broadcast_state(user_id)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.disconnect(user_id)

@app.post("/auth/register")
async def register(req: UserRegister):
    # TODO: Persistencia real en DB
    user_id = f"USER-{random.randint(10000, 99999)}"
    print(f"Usuario registrado: {req.username} -> {user_id}")
    return {"status": "success", "user_id": user_id, "username": req.username}

@app.post("/auth/login")
async def login(req: UserLogin):
    # TODO: Validar contra DB
    # Por ahora, simulamos login exitoso devolviendo un ID determinista basado en el nombre
    user_id = f"USER-{abs(hash(req.username)) % 100000}"
    return {"status": "success", "user_id": user_id, "username": req.username}

@app.post("/game/control")
async def game_control(req: GameAction):
    if req.action == "start":
        session_manager.start_simulation_loop(req.user_id)
        return {"status": "success", "message": "Simulación iniciada"}
    elif req.action == "pause":
        session_manager.stop_simulation_loop(req.user_id)
        return {"status": "success", "message": "Simulación pausada"}
    elif req.action == "reset":
        session_manager.stop_simulation_loop(req.user_id)
        sim = session_manager.get_simulation(req.user_id)
        if sim:
            if sim.db_active:
                sim.db.clear_database(user_id=req.user_id)
            if os.path.exists("estado_simulacion.json"):
                try:
                    os.remove("estado_simulacion.json")
                    print("🗑️ Archivo estado_simulacion.json eliminado.")
                except Exception as e:
                    print(f"⚠️ Error eliminando JSON: {e}")
            
            if req.user_id in session_manager.simulations:
                del session_manager.simulations[req.user_id]
        
        session_manager.create_simulation(req.user_id)
        await session_manager.broadcast_state(req.user_id)
        return {"status": "success", "message": "Mundo reiniciado completamente"}
    
    raise HTTPException(status_code=400, detail="Acción desconocida")

@app.get("/tts")
async def text_to_speech(text: str):
    tts_url = os.getenv("TTS_URL", "http://localhost:5050/v1/audio/speech")
    try:
        response = requests.post(
            tts_url,
            json={"input": text, "voice": "es-MX-DaliaNeural", "model": "edge-tts"},
            timeout=5
        )
        if response.status_code == 200:
            return StreamingResponse(iter([response.content]), media_type="audio/mpeg")
    except:
        pass
    return {"error": "TTS unavailable"}

class GodAction(BaseModel):
    action_type: str # 'DISASTRE', 'RESOURCE_BOOST', 'FORCE_ALLIANCES', 'SET_GLOBAL_CONTEXT', 'SPAWN_AGENT'
    params: Dict[str, Any]

class AgentConfig(BaseModel):
    name: Optional[str] = None
    personality: Optional[Dict[str, float]] = None
    resources: Optional[float] = 0.0
    money: Optional[float] = 100.0
    position: Optional[Dict[str, int]] = None # {"x": 10, "y": 10}

@app.post("/game/god-mode/{user_id}")
async def god_mode(user_id: str, req: GodAction):
    sim = session_manager.get_simulation(user_id)
    if not sim:
        # Auto-crear simulación si no existe para evitar 404
        sim = session_manager.create_simulation(user_id)

    if req.action_type == "SET_WEATHER":
        new_weather = req.params.get("weather")
        if new_weather:
            sim.weather = new_weather
            sim.log_callback(f"🌩️ [DIVINO] El clima ha cambiado a {new_weather} por voluntad del Arquitecto.", "ambiente", None, f"El clima cambia a {new_weather}")
            await session_manager.broadcast_state(user_id) # Actualizar frontend inmediatamente
            return {"status": "success", "message": f"Clima cambiado a {new_weather}"}

    elif req.action_type == "TRIGGER_EVENT":
        event_type = req.params.get("event")
        if event_type == "earthquake":
            # Lógica simple de terremoto: dañar edificios o agentes al azar
            afectados = 0
            for a in sim.agentes:
                if random.random() < 0.3:
                    a.necesidades["salud"] -= 3
                    afectados += 1
            sim.log_callback(f"🌍 [DIVINO] ¡Un TERREMOTO ha sacudido el mundo! {afectados} agentes heridos.", "evento", None, "Terremoto detectado")
        elif event_type == "plague":
            for a in sim.agentes:
                a.necesidades["salud"] -= 1 # Contagio inicial
            sim.log_callback("☣️ [DIVINO] Una PLAGA se ha desatado sobre la población.", "evento", None, "Alerta de plaga")
        
        await session_manager.broadcast_state(user_id)
        return {"status": "success", "message": f"Evento {event_type} disparado"}

    elif req.action_type == "MODIFY_ECONOMY":
        action = req.params.get("sub_action") # "inject_money", "crash_market"
        if action == "inject_money":
            sim.economia["total_dinero"] += 1000
            sim.economia["precio_recurso"] *= 0.8 # Inflación baja precios (simplificado)
            sim.log_callback("💸 [DIVINO] Se ha inyectado capital divino en la economía.", "economia", None, "Inyección económica")
        elif action == "crash_market":
            sim.economia["indice_bursatil"] *= 0.5
            sim.economia["precio_recurso"] *= 2.0 # Escasez sube precios
            sim.log_callback("📉 [DIVINO] ¡El mercado ha COLAPSADO por orden del Arquitecto!", "economia", None, "Crash del mercado")
        
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif req.action_type == "MODIFY_AGENT":
        agent_id = req.params.get("agent_id")
        effect = req.params.get("effect") # "heal", "smite", "enrich"
        agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
        
        if agent:
            if effect == "heal":
                agent.necesidades["salud"] = 10.0
                agent.necesidades["alimento"] = 0.0
                sim.log_callback(f"✨ [DIVINO] El Agente {agent_id} ha sido SANADO completamente.", "milagro", None, "Curación divina")
            elif effect == "smite":
                agent.necesidades["salud"] = 1.0
                agent.recursos = 0
                sim.log_callback(f"⚡ [DIVINO] ¡El Agente {agent_id} ha sido CASTIGADO!", "milagro", None, "Castigo divino")
            elif effect == "enrich":
                agent.dinero += 500
                sim.log_callback(f"💰 [DIVINO] El Agente {agent_id} ha recibido una fortuna.", "milagro", None, "Riqueza divina")
            
            await session_manager.broadcast_state(user_id)
            return {"status": "success"}
        else:
             raise HTTPException(status_code=404, detail="Agente no encontrado")

    elif req.action_type == "SET_GLOBAL_CONTEXT":
        new_lore = req.params.get("lore")
        sim.lore = new_lore
        sim.log_callback(f"📜 [NARRATIVA] El Arquitecto ha redefinido la realidad: '{new_lore}'", "sistema", None, "Contexto actualizado")
        await session_manager.broadcast_state(user_id)
        return {"status": "success", "message": "Lore actualizado"}

    elif req.action_type == "SPAWN_AGENT":
        count = req.params.get("count", 1)
        config_data = req.params.get("config") # Opcional
        
        spawned_ids = []
        for _ in range(count):
            # Convertir el diccionario de config_data a un objeto AgentConfig si existe
            config = AgentConfig(**config_data) if config_data else None
            agente = sim.spawn_agent(config=config)
            spawned_ids.append(agente.unique_id)
            
        sim.log_callback(f"🧬 [DIVINO] Ha manifestado {len(spawned_ids)} nuevos seres en el mundo.", "sistema", None, f"Inyectados {len(spawned_ids)} agentes")
        await session_manager.broadcast_state(user_id)
        return {"status": "success", "message": f"Inyectados {len(spawned_ids)} agentes", "ids": spawned_ids}

    return {"status": "error", "message": "Acción no reconocida"}

@app.post("/game/spawn/{user_id}")
async def spawn_agent_endpoint(user_id: str, config: AgentConfig = Body(None)):
    sim = session_manager.get_simulation(user_id)
    if not sim:
        sim = session_manager.create_simulation(user_id)
    
    agente = sim.spawn_agent(config=config)
    sim.log_callback(f"🧬 [DIVINO] Un nuevo agente '{agente.unique_id}' ha sido manifestado.", "sistema", None, "Agente creado")
    await session_manager.broadcast_state(user_id)
    return {"status": "success", "message": f"Agente '{agente.unique_id}' creado", "agent_id": agente.unique_id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
