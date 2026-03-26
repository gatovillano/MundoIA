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
from modelo import ModeloRelacional, DatabaseManager, DateTimeEncoder
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

# --- LIFESPAN para iniciar el processor de la cola ---
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Guardar referencia al loop principal
    session_manager.main_loop = asyncio.get_running_loop()
    # Iniciar el processor de la cola de mensajes
    asyncio.create_task(session_manager.process_message_queue())
    print("🚀 Message queue processor started")
    yield
    print("🛑 Shutting down...")

app.router.lifespan_context = lifespan

# --- GESTOR DE SESIONES ---

class SessionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {} # user_id -> WebSocket
        self.simulations: Dict[str, ModeloRelacional] = {} # user_id -> ModeloRelacional
        self.simulation_threads: Dict[str, bool] = {} # user_id -> is_running
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.queue_processor_started = False
        self.main_loop = None

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
                # Use DateTimeEncoder to handle potential datetime objects in the message
                await self.active_connections[user_id].send_text(json.dumps(message, cls=DateTimeEncoder))
                print(f"✅ Enviado a {user_id}: tipo={message.get('type')}")
            except Exception as e:
                print(f"Error enviando a {user_id}: {e}")
                self.disconnect(user_id)
        else:
            print(f"⚠️ Usuario {user_id} no está conectado, mensaje perdido: {message.get('type')}")

    def enqueue_message(self, user_id: str, message: dict):
        """Encola un mensaje para ser procesado por el loop principal de asyncio."""
        try:
            if hasattr(self, 'main_loop') and self.main_loop is not None:
                loop = self.main_loop
            else:
                loop = asyncio.get_event_loop()
            
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.message_queue.put((user_id, message)),
                    loop
                )
            else:
                print(f"[QUEUE] Loop no está corriendo")
        except Exception as e:
            print(f"[QUEUE] Error encolando mensaje: {e}")

    async def process_message_queue(self):
        """Procesa la cola de mensajes asynchronously."""
        print("🔄 Message queue processor iniciado")
        while True:
            try:
                user_id, message = await asyncio.wait_for(self.message_queue.get(), timeout=0.5)
                print(f"[QUEUE] Procesando mensaje tipo={message.get('type')} para {user_id}")
                await self.send_to_user(user_id, message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[QUEUE] Error procesando mensaje: {e}")

    def get_simulation(self, user_id: str) -> Optional[ModeloRelacional]:
        return self.simulations.get(user_id)

    def create_simulation(self, user_id: str, start_empty: bool = False):
        if user_id not in self.simulations:
            # NUEVO: Asegurar que el usuario existe en la DB antes de crear la simulación
            db = DatabaseManager()
            if db.connect():
                db.ensure_user_exists(user_id)
            
            # Callback personalizado para este usuario
            def user_log_callback(mensaje, categoria, subtitulos, tts_text, pensamiento=None, privado_para=None):
                sim = self.simulations.get(user_id)
                paso = sim.paso_actual if sim else 0
                try:
                    self.enqueue_message(user_id, {
                        "type": "log",
                        "step": paso,
                        "message": mensaje,
                        "category": categoria,
                        "subtitles": subtitulos,
                        "tts_text": tts_text,
                        "thought": pensamiento,
                        "private_for": privado_para
                    })
                except Exception as e:
                    print(f"[LOG_CALLBACK] Error: {e}, mensaje: {mensaje[:50]}...")
            
            # Callback para cambios de estado (actualización inmediata de UI)
            def on_state_change():
                sim = self.simulations.get(user_id)
                if sim:
                    try:
                        # Emitir estado completo inmediatamente al detectar un cambio crítico
                        if self.main_loop:
                            asyncio.run_coroutine_threadsafe(self.broadcast_state(user_id), self.main_loop)
                    except Exception as e:
                        print(f"[STATE_CHANGE] Error en broadcast: {e}")

            num_agentes = int(os.getenv("NUM_AGENTES", 30))
            self.simulations[user_id] = ModeloRelacional(num_agentes=num_agentes, log_callback=user_log_callback, user_id=user_id, start_empty=start_empty)
            self.simulations[user_id].state_change_callback = on_state_change # Conectar callback
            self.simulations[user_id]._force_stop = False
            self.simulation_threads[user_id] = False # Inicia pausado
            print(f"🌍 Nueva simulación creada para {user_id}")
            return self.simulations[user_id]
        return self.simulations[user_id]

    def start_simulation_loop(self, user_id: str):
        if user_id not in self.simulations: return
        
        if self.simulation_threads.get(user_id): return # Ya está corriendo

        self.simulation_threads[user_id] = True
        current_sim_ref = self.simulations[user_id]
        
        def run_loop():
            nonlocal current_sim_ref
            print(f"▶️ Iniciando bucle de simulación para {user_id}")
            while self.simulation_threads.get(user_id, False):
                current_sim = self.simulations.get(user_id)
                if current_sim is None:
                    print(f"🛑 Simulación no encontrada, deteniendo hilo para {user_id}")
                    break
                if current_sim is not current_sim_ref:
                    print(f"🔄 Nueva simulación detectada, actualizando referencia para {user_id}")
                    current_sim_ref = current_sim
                    if hasattr(current_sim, '_force_stop'):
                        current_sim._force_stop = False
                
                if getattr(current_sim, '_force_stop', False):
                    print(f"🛑 Detención forzada detectada, saliendo del bucle para {user_id}")
                    break
                
                current_sim.step()
                
                # Broadcast de estado usando la cola
                try:
                    async def do_broadcast():
                        await self.broadcast_state(user_id, include_logs=False)
                    asyncio.run_coroutine_threadsafe(do_broadcast(), self.main_loop)
                except Exception as e:
                    print(f"[RUN_LOOP] Error en broadcast: {e}")
                
                time.sleep(0.3) # Ritmo de juego acelerado para sensación Real-Time
            print(f"⏹️ Bucle de simulación terminado para {user_id}")

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()

    def stop_simulation_loop(self, user_id: str):
        self.simulation_threads[user_id] = False
        if user_id in self.simulations and hasattr(self.simulations[user_id], '_force_stop'):
            self.simulations[user_id]._force_stop = True
        print(f"⏸️ Simulación pausada para {user_id}")

    async def broadcast_state(self, user_id: str, include_logs: bool = False):
        sim = self.simulations.get(user_id)
        if not sim: return

        # Construir diccionario de grupos dinámicos y preparar lista de civilizaciones reales
        grupos_dinamicos = {}
        civilizaciones_viz = {}

        # Iterar sobre todas las "civilizaciones" del modelo (que ahora incluyen grupos y civs)
        for civ_id, civ in sim.civilizaciones.items():
            # Calcular recursos en tiempo real para todos
            miembros = [a for a in sim.agentes if a.civilizacion_id == civ_id or a.grupo_id == civ_id]
            recursos_totales = sum(a.recursos for a in miembros)
            
            data_viz = {
                "nombre": civ.nombre,
                "color": civ.color,
                "descripcion": getattr(civ, 'descripcion', ''),
                "recursos": recursos_totales,
                "tipo": civ.tipo.lower() if hasattr(civ, 'tipo') else "grupo_dinamico", # Fallback
                "members": len(miembros)  # Incluir número de miembros
            }

            if getattr(civ, 'tipo', 'GRUPO') == 'CIVILIZACION':
                civilizaciones_viz[civ_id] = data_viz
            else:
                grupos_dinamicos[civ_id] = data_viz

        # Añadir también grupos que solo existen en objetivos_grupos pero no han instanciado Civilizacion (caso legacy/safety)
        for grupo_id, mision in sim.objetivos_grupos.items():
            if grupo_id not in sim.civilizaciones:
                miembros = [a for a in sim.agentes if a.grupo_id == grupo_id]
                if miembros:
                    color_idx = hash(grupo_id) % len(sim.colores_paleta)
                    grupos_dinamicos[grupo_id] = {
                        "nombre": mision[:30] + "..." if len(mision) > 30 else mision,
                        "color": sim.colores_paleta[color_idx],
                        "recursos": sum(a.recursos for a in miembros),
                        "tipo": "grupo",
                        "members": len(miembros)  # Incluir número de miembros
                    }

        # Consolidar propuestas (Leyes Globales + Leyes de Facciones + Asambleas)
        todas_propuestas = list(sim.leyes_globales)
        for g_id, leyes in sim.facciones_leyes.items():
            for ley in leyes:
                ley_copy = ley.copy()
                ley_copy['grupo_id'] = g_id
                todas_propuestas.append(ley_copy)
        
        # Añadir asambleas como propuestas tipo asamblea
        for asamblea in sim.asambleas_globales:
            todas_propuestas.append({
                "id": asamblea["id"],
                "proponente_id": asamblea["proponente_id"],
                "texto": asamblea["tema"],
                "tipo": "asamblea",
                "estado": asamblea["estado"],
                "votos_si": asamblea["votos_si"],
                "votos_no": asamblea["votos_no"]
            })

        # Stats Globales + Civilizaciones + Grupos Dinámicos + Propuestas + Relaciones + Misiones
        await self.send_to_user(user_id, {
            "type": "stats",
            "step": sim.paso_actual,
            "groups": len(set(a.grupo_id for a in sim.agentes if a.grupo_id)),
            "economy": sim.economia,
            "mapa": [[t.to_dict() if t else None for t in row] for row in sim.mapa],
            "weather": sim.weather,
            "lore": sim.lore,
            "civilizaciones": civilizaciones_viz,
            "grupos_dinamicos": grupos_dinamicos,
            "propuestas": todas_propuestas,
            "relaciones_grupos": {f"{k[0]}:{k[1]}": v for k, v in sim.relaciones_grupos.items()},
            "guerras_activas": [f"{g1}:{g2}" for g1, g2 in sim.guerras_activas],
            "misiones": sim.sistema_misiones.to_dict(),
            "user_score": sim.sistema_misiones.obtener_puntaje(user_id or "default"),
            "recent_completed_missions": getattr(sim, 'misiones_completadas_este_turno', []),
            "instituciones": {k: v.to_dict() for k, v in sim.instituciones.items()},
            "historia": sim.historia.to_dict(),
            "ranking": [{"user_id": r[0], "username": r[1], "puntos": r[2]} for r in sim.db.get_ranking()] if sim.db_active else [],
            "logs": sim.historial_logs if include_logs else [],
            "agente_poseido_id": getattr(sim, 'agente_poseido_id', None)
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
                "experiencia": a.experiencia,
                "mensajes_enviados_count": getattr(a, 'mensajes_enviados_count', 0),
                "pensamiento": getattr(a, 'pensamiento_actual', "Esperando estímulos..."),
                "planes": getattr(a, 'planes', []),
                "skills": {k: (v if isinstance(v, dict) else v.to_dict()) for k, v in a.skills.items()},
                "skill_factor": getattr(a, 'skill_factor', 0.3),
                "inventario": getattr(a, 'inventario', {}),
                "color": sim.civilizaciones[a.grupo_id].color if a.grupo_id and a.grupo_id in sim.civilizaciones else "#ffffff",
                "is_possessed": a.unique_id == getattr(sim, 'agente_poseido_id', None)
            })
        
        await self.send_to_user(user_id, {
            "type": "agent_update",
            "agents": agents_update
        })

        # Relaciones (en cada turno para mantener vista 3D sincronizada)
        if True: # Antes sim.paso_actual % 5 == 0:
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
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = None

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

class AIConfig(BaseModel):
    provider: str
    api_key: str
    model: str

# --- ENDPOINTS ---

@app.get("/")
async def get():
    return {"message": "MundoIA Game Server Running"}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    print(f"🔌 WS: Nueva conexión para {user_id}")
    
    # Si ya hay una conexión activa, cerrar la anterior
    if user_id in session_manager.active_connections:
        print(f"🔌 WS: Cerrando conexión anterior para {user_id}")
        try:
            old_ws = session_manager.active_connections[user_id]
            await old_ws.close()
        except:
            pass
    
    await session_manager.connect(user_id, websocket)
    print(f"🔌 WS: Usuario {user_id} conectado. Total conexiones: {len(session_manager.active_connections)}")
    
    # Verificar si tiene simulación activa, si no, crearla
    sim = session_manager.get_simulation(user_id)
    if not sim:
        print(f"🔌 WS: Creando simulación para {user_id}")
        sim = session_manager.create_simulation(user_id)
    
    # Enviar estado inicial con logs históricos
    await session_manager.broadcast_state(user_id, include_logs=True)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"🔌 WS: Usuario {user_id} desconectado")
        session_manager.disconnect(user_id)

@app.post("/auth/register")
async def register(req: UserRegister):
    db = DatabaseManager()
    if not db.connect():
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    
    user_id = db.create_user(req.username, req.password)
    if user_id:
        print(f"Usuario registrado y guardado en DB: {req.username} -> {user_id}")
        return {"status": "success", "user_id": user_id, "username": req.username}
    else:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

@app.post("/auth/login")
async def login(req: UserLogin):
    db = DatabaseManager()
    if not db.connect():
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    
    user_id = db.verify_user(req.username, req.password)
    if user_id:
        return {"status": "success", "user_id": user_id, "username": req.username}
    else:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

@app.post("/game/control")
async def game_control(req: GameAction):
    if req.action == "start":
        session_manager.start_simulation_loop(req.user_id)
        return {"status": "success", "message": "Simulación iniciada"}
    elif req.action == "pause":
        session_manager.stop_simulation_loop(req.user_id)
        return {"status": "success", "message": "Simulación pausada"}
    elif req.action == "reset":
        print(f"--- DEBUG: Recibida acción de RESET para user_id: {req.user_id} ---")
        
        # 1. Detener el bucle actual
        session_manager.stop_simulation_loop(req.user_id)

        # 2. Notificar al frontend para que limpie TODA su UI (agentes, grupos, logs, etc.)
        await session_manager.send_to_user(req.user_id, {"type": "world_reset"})

        # 3. LIMPIEZA DE BASE DE DATOS (Independiente de si hay simulación en memoria)
        try:
            db = DatabaseManager()
            if db.connect():
                print(f"--- DEBUG: Limpiando base de datos para user_id: {req.user_id} ---")
                db.clear_database(user_id=req.user_id)
                db.conn.close()
                print(f"--- DEBUG: Base de datos limpiada. ---")
        except Exception as e:
            print(f"--- ERROR: Fallo al limpiar DB en reset: {e} ---")

        # 4. LIMPIEZA DE ARCHIVOS Y MEMORIA
        json_filename = f"estado_simulacion_{req.user_id}.json"
        if os.path.exists(json_filename):
            try:
                os.remove(json_filename)
                print(f"🗑️ Archivo {json_filename} eliminado.")
            except Exception as e:
                print(f"⚠️ Error eliminando JSON: {e}")
        
        if req.user_id in session_manager.simulations:
            del session_manager.simulations[req.user_id]
            print(f"--- DEBUG: Simulación en memoria eliminada. ---")
        
        # 5. CREACIÓN DE NUEVO MUNDO (Comenzar realmente vacío)
        print("--- DEBUG: Creando nueva simulación VACÍA... ---")
        new_sim = session_manager.create_simulation(req.user_id, start_empty=True)
        
        if new_sim and new_sim.db_active:
            print("--- DEBUG: Guardando nueva simulación inicial VACÍA en DB... ---")
            new_sim.guardar_estado()
        
        # 6. ENVIAR ESTADO INICIAL
        print("--- DEBUG: Enviando nuevo estado al frontend... ---")
        await session_manager.broadcast_state(req.user_id)
        
        # 7. REINICIAR BUCLE
        print("--- DEBUG: Reiniciando el bucle de simulación... ---")
        session_manager.start_simulation_loop(req.user_id)
        
        print("--- DEBUG: Proceso de RESET completado. ---")
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

    elif req.action_type == "CREATE_MISSION":
        params = req.params
        titulo = params.get("titulo", "Misión Divina")
        descripcion = params.get("descripcion", "Una tarea encomendada por los dioses.")
        tipo = params.get("tipo", "construccion")
        objetivo = params.get("objetivo")
        recompensa = params.get("recompensa", {"puntos": 500})
        
        exito, msg = sim.crear_mision(titulo, descripcion, tipo, objetivo, recompensa)
        if exito:
             await session_manager.broadcast_state(user_id)
             return {"status": "success", "message": msg}
        else:
             return {"status": "error", "message": msg}

    elif req.action_type == "POSSESS_AGENT":
        agent_id = req.params.get("agent_id")
        # Simplemente marcar en el modelo o devolver éxito si el frontend maneja el estado de "Poseído"
        # Podríamos guardar esto en el estado de la simulación para que el agente no tome decisiones propias
        sim.agente_poseido_id = agent_id
        sim.log_callback(f"👤 [POSESIÓN] El Arquitecto ha descendido sobre el cuerpo del Agente {agent_id}.", "sistema", None, "Posesión divina iniciada")
        await session_manager.broadcast_state(user_id)
        return {"status": "success", "message": f"Agente {agent_id} poseído"}

    elif req.action_type == "AGENT_EXECUTE_ACTION":
        agent_id = req.params.get("agent_id")
        action = req.params.get("action")
        payload = req.params.get("payload", {})
        
        agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
        if not agent:
             raise HTTPException(status_code=404, detail="Agente no encontrado")
        
        exito = False
        msg = "Acción fallida"
        
        if action == "recolectar":
            agent.recolectar()
            exito = True; msg = "Recolección divina completada"
            sim.log_callback(f"🌾 [POSESIÓN] El Agente {agent_id} (poseído) ha recolectado recursos.", "accion", None, "Recolección completada")
        elif action == "fundar_grupo":
            nombre = payload.get("nombre", "Nueva Orden")
            agent.fundar_grupo(nombre)
            exito = True; msg = f"Grupo '{nombre}' fundado por voluntad divina"
            sim.log_callback(f"🏛️ [POSESIÓN] El Agente {agent_id} (poseído) ha fundado el grupo '{nombre}'.", "sistema", None, f"Grupo {nombre} fundado")
        elif action == "proponer_ley":
            tipo = payload.get("tipo", "LEY_GENERAL")
            descripcion = payload.get("descripcion", "Decreto Divino")
            # Llamar a la lógica de propuesta en el modelo
            sim.facciones_leyes.setdefault("propuestas", []).append({
                "id": f"P-{random.randint(1000, 9999)}",
                "proponente": agent_id,
                "descripcion": descripcion,
                "tipo": tipo,
                "votos_favor": 1, # El proponente ya votó
                "votos_contra": 0,
                "paso_creacion": sim.paso_actual
            })
            sim.log_callback(f"📜 [DECRETO] El Agente {agent_id} (poseído) ha propuesto una ley: {descripcion}", "consenso", None, "Nueva propuesta de ley")
            exito = True; msg = "Ley propuesta"
        elif action == "decir":
            mensaje = payload.get("mensaje", "Mensaje desde el Arquitecto")
            global_broadcast = payload.get("global_broadcast", False)
            para_grupo = payload.get("para_grupo", False)
            privado_para = payload.get("privado_para")
            agent.decir(mensaje, global_broadcast=global_broadcast, para_grupo=para_grupo, privado_para=privado_para)
            exito = True; msg = "Mensaje enviado"
        elif action == "socializar":
            otro_agente_id = payload.get("otro_agente_id")
            if otro_agente_id:
                otro_agente = next((a for a in sim.agentes if a.unique_id == otro_agente_id), None)
                if otro_agente:
                    agent.interactuar(otro_agente, "social")
                    exito = True; msg = f"Socializado con {otro_agente_id}"
                    sim.log_callback(f"🤝 [POSESIÓN] El Agente {agent_id} (poseído) socializa con {otro_agente_id}.", "social", None, "Interacción social")
        elif action == "competir":
            otro_agente_id = payload.get("otro_agente_id")
            if otro_agente_id:
                otro_agente = next((a for a in sim.agentes if a.unique_id == otro_agente_id), None)
                if otro_agente:
                    agent.interactuar(otro_agente, "COMPETIR")
                    exito = True; msg = f"Competición con {otro_agente_id}"
                    sim.log_callback(f"⚔️ [POSESIÓN] El Agente {agent_id} (poseído) compite con {otro_agente_id}.", "conflict", None, "Interacción competitiva")
        elif action == "mover":
            x = payload.get("x")
            y = payload.get("y")
            if x is not None and y is not None:
                agent.x = x
                agent.y = y
                exito = True; msg = f"Movido a ({x}, {y})"
                sim.log_callback(f"🚶 [POSESIÓN] El Agente {agent_id} (poseído) se ha movido a ({x}, {y}).", "movimiento", None, "Movimiento ejecutado")
        elif action == "construir":
            tipo_edific = payload.get("tipo", "Casa")
            exito, msg = agent.construir(tipo_edific)
            if exito:
                sim.log_callback(f"🏗️ [POSESIÓN] El Agente {agent_id} (poseído) ha construido un {tipo_edific}.", "construccion", None, "Construcción exitosa")
        elif action == "votar":
            propuesta_id = payload.get("propuesta_id")
            voto = payload.get("voto", "si")
            exito = True; msg = f"Voto {voto} emitido para la propuesta {propuesta_id}"
            sim.log_callback(f"🗳️ [POSESIÓN] El Agente {agent_id} (poseído) ha votado {voto} a la propuesta {propuesta_id}.", "consenso", None, "Voto emitido")
            
        await session_manager.broadcast_state(user_id)
        return {"status": "success", "message": msg}

    elif req.action_type == "START_ASSEMBLY":
        tema = req.params.get("topic", "Asambleas Divinas")
        # El Arquitecto inicia la asamblea. Usamos "Arquitecto" como ID o el sistema debe permitirlo.
        # modelo.crear_asamblea espera un proponente_id
        exito, msg = sim.crear_asamblea("Arquitecto", tema)
        
        if exito:
             sim.log_callback(f"🏛️ [DIVINO] El Arquitecto ha convocado una ASAMBLEA GLOBAL: '{tema}'", "consenso", None, "Asamblea convocada")
             await session_manager.broadcast_state(user_id)
             return {"status": "success", "message": msg}
        else:
             return {"status": "error", "message": msg}


    elif req.action_type == "EXPAND_WORLD":
        exito, msg = sim.expandir_mundo()
        if exito:
            await session_manager.broadcast_state(user_id)
            return {"status": "success", "message": msg, "cost": sim.COSTO_EXPANSION}
        else:
            raise HTTPException(status_code=400, detail=msg)

    elif req.action_type == "ARCHITECT_MESSAGE":
        mensaje = req.params.get("mensaje")
        agente_id = req.params.get("agent_id")
        if mensaje:
            exito, msg = sim.enviar_mensaje_arquitecto(mensaje, agente_id)
            if exito:
                return {"status": "success", "message": msg}
            else:
                raise HTTPException(status_code=404, detail=msg)

    return {"status": "error", "message": "Acción no reconocida"}

# --- ENDPOINTS DE CONFIGURACION DE IA ---

@app.get("/config/ai")
async def get_ai_config():
    from cerebro_llm import cerebro_llm
    return {
        "model": cerebro_llm.model,
        "api_key": cerebro_llm.api_key
    }

@app.post("/config/ai")
async def update_ai_config(config: AIConfig):
    from cerebro_llm import cerebro_llm
    # Si el modelo incluye el prefijo del proveedor (ej: openrouter/), lo usamos tal cual
    success = cerebro_llm.update_config(config.model, config.api_key)
    if success:
        return {"status": "success", "message": "Configuración actualizada correctamente"}
    else:
        raise HTTPException(status_code=500, detail="Error al guardar la configuración")

@app.get("/config/models/{provider}")
async def get_models(provider: str, api_key: Optional[str] = None):
    if provider.lower() == "openrouter":
        url = "https://openrouter.ai/api/v1/models"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Extraer solo lo necesario para el frontend
                models = []
                for m in data.get("data", []):
                    models.append({
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "context_length": m.get("context_length"),
                        "pricing": m.get("pricing")
                    })
                return {"models": models}
            else:
                return {"error": f"Error de OpenRouter: {response.status_code}", "detail": response.text}
        except Exception as e:
            return {"error": str(e)}
    
    elif provider.lower() == "openai":
        # Implementación simple para OpenAI si se requiere
        return {"models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"}
        ]}
        
    return {"error": "Proveedor no soportado actualmente para rpeuperación dinámica"}

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
    uvicorn.run(app, host="0.0.0.0", port=8005)
