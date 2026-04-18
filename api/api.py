import os
import json
import asyncio
import threading
import requests
import random
import time
from typing import Dict, Optional, Any
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
    Body,
)
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from core.modelo import ModeloRelacional, DatabaseManager, DateTimeEncoder
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


# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"📥 [HTTP] {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"📤 [HTTP] {request.method} {request.url.path} -> {response.status_code}")
    return response


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
        self.active_connections: Dict[str, WebSocket] = {}  # user_id -> WebSocket
        self.simulations: Dict[
            str, ModeloRelacional
        ] = {}  # user_id -> ModeloRelacional
        self.simulation_threads: Dict[str, bool] = {}  # user_id -> is_running
        self.simulation_thread_refs: Dict[
            str, threading.Thread
        ] = {}  # user_id -> thread reference
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.queue_processor_started = False
        self.main_loop = None
        self.last_stats: Dict[str, dict] = {}  # user_id -> last sent stats
        self.last_agents: Dict[
            str, Dict[str, dict]
        ] = {}  # user_id -> {agent_id -> last sent agent data}
        self.last_broadcast_time: Dict[str, float] = {}  # user_id -> timestamp of last broadcast

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"🔌 Usuario {user_id} conectado via WebSocket")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            # Limpiar rastro de estado anterior al desconectar para que al reconectar reciba estado completo
            self.last_stats.pop(user_id, None)
            self.last_agents.pop(user_id, None)
            self.last_broadcast_time.pop(user_id, None)
            print(f"🔌 Usuario {user_id} desconectado")

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            try:
                # Use DateTimeEncoder to handle potential datetime objects in the message
                await self.active_connections[user_id].send_text(
                    json.dumps(message, cls=DateTimeEncoder)
                )
            except Exception as e:
                print(f"Error enviando a {user_id}: {e}")
                self.disconnect(user_id)

    def enqueue_message(self, user_id: str, message: dict):
        """Encola un mensaje para ser procesado por el loop principal de asyncio."""
        try:
            if user_id not in self.active_connections and message.get("type") == "log":
                return

            loop = self.main_loop
            if loop is None or loop.is_closed():
                # Intentar capturar el loop actual si el guardado falló
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    return

            if not loop.is_running():
                return

            coro = self.send_to_user(user_id, message)
            asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception as e:
            pass

    async def process_message_queue(self):
        """Procesa la cola de mensajes asynchronously."""
        print("🔄 Message queue processor iniciado")
        while True:
            try:
                user_id, message = await self.message_queue.get()
                await self.send_to_user(user_id, message)
            except Exception as e:
                print(f"[QUEUE] Error procesando mensaje: {e}")

    def get_simulation(self, user_id: str) -> Optional[ModeloRelacional]:
        return self.simulations.get(user_id)

    def create_simulation(self, user_id: str, start_empty: bool = False):
        if user_id not in self.simulations:
            # Asegurar que el usuario existe en la DB antes de crear la simulación
            db = DatabaseManager()
            if db.connect():
                db.ensure_user_exists(user_id)

            # Callback personalizado para este usuario
            def user_log_callback(
                mensaje,
                categoria,
                subtitulos=None,
                tts_text=None,
                pensamiento=None,
                privado_para=None,
                agente_id=None,
            ):
                sim = self.simulations.get(user_id)
                if sim and getattr(sim, "_stopped", False):
                    return  # No enviar logs si la simulación fue detenida/reset
                paso = sim.paso_actual if sim else 0
                try:
                    self.enqueue_message(
                        user_id,
                        {
                            "type": "log",
                            "step": paso,
                            "message": mensaje,
                            "category": categoria,
                            "subtitles": subtitulos,
                            "tts_text": tts_text,
                            "thought": pensamiento,
                            "private_for": privado_para,
                            "agent_id": agente_id,
                        },
                    )
                except Exception as e:
                    print(f"[LOG_CALLBACK] Error: {e}, mensaje: {mensaje[:50]}...")

            # Callback para cambios de estado (actualización inmediata de UI)
            def on_state_change():
                sim = self.simulations.get(user_id)
                if sim and not getattr(sim, "_stopped", False):
                    try:
                        now = time.time()
                        last_time = self.last_broadcast_time.get(user_id, 0)
                        if now - last_time < 0.2:
                            return
                        
                        loop = self.main_loop
                        if loop and not loop.is_closed() and loop.is_running():
                            coro = self.broadcast_state(user_id)
                            asyncio.run_coroutine_threadsafe(coro, loop)
                    except Exception as e:
                        print(f"[STATE_CHANGE] Error en broadcast: {e}")

            # Callback para eventos en tiempo real (stream LLM / acción / social)
            def on_realtime_event(event_type: str, payload: dict):
                sim = self.simulations.get(user_id)
                if sim and getattr(sim, "_stopped", False):
                    return
                msg = {"type": event_type}
                msg.update(payload or {})
                try:
                    self.enqueue_message(user_id, msg)
                except Exception as e:
                    print(f"[REALTIME_EVENT] Error: {e}, type={event_type}")

            # Los agentes los crea el usuario desde el frontend (SPAWN_AGENT).
            # num_agentes solo se usa en CLI/tests; en la API siempre se pasa start_empty.
            self.simulations[user_id] = ModeloRelacional(
                num_agentes=0,
                log_callback=user_log_callback,
                user_id=user_id,
                start_empty=start_empty,
            )
            self.simulations[
                user_id
            ].state_change_callback = on_state_change  # Conectar callback
            self.simulations[user_id].realtime_event_callback = on_realtime_event
            self.simulations[user_id]._force_stop = False
            self.simulation_threads[user_id] = False  # Inicia pausado
            print(f"🌍 Nueva simulación creada para {user_id}")
            return self.simulations[user_id]
        return self.simulations[user_id]

    def start_simulation_loop(self, user_id: str):
        if user_id not in self.simulations:
            return

        # Check if the thread is actually alive
        existing_thread = self.simulation_thread_refs.get(user_id)
        if existing_thread and existing_thread.is_alive():
            print(f"✅ Bucle de simulación ya está corriendo para {user_id}")
            return

        self.simulation_threads[user_id] = True
        current_sim_ref = self.simulations[user_id]

        # Resetear flag de detención si ya existía
        if hasattr(current_sim_ref, "_force_stop"):
            current_sim_ref._force_stop = False
            current_sim_ref._stopped = False

        def run_loop():
            nonlocal current_sim_ref
            print(f"▶️ Iniciando bucle de simulación para {user_id}")
            try:
                while self.simulation_threads.get(user_id, False):
                    current_sim = self.simulations.get(user_id)
                    if current_sim is None:
                        print(
                            f"🛑 Simulación no encontrada, deteniendo hilo para {user_id}"
                        )
                        break
                    if current_sim is not current_sim_ref:
                        print(
                            f"🔄 Nueva simulación detectada, actualizando referencia para {user_id}"
                        )
                        current_sim_ref = current_sim
                        if hasattr(current_sim, "_force_stop"):
                            current_sim._force_stop = False

                    if getattr(current_sim, "_force_stop", False):
                        print(
                            f"🛑 Detención forzada detectada, saliendo del bucle para {user_id}"
                        )
                        break

                    # Si estamos en modo Arquitecto (control total), no avancemos pasos automáticamente.
                    if getattr(current_sim, "modo_control_total", False):
                        # Preparar ciclo controlado si aún no está activo (asegura paso_actual y agentes pendientes)
                        if not getattr(current_sim, "_control_round_active", False):
                            try:
                                current_sim._prepare_control_round()
                            except Exception:
                                pass
                        # Dejar que el usuario ejecute agente por agente; dormir brevemente.
                        time.sleep(0.1)
                        continue

                    current_sim.step()

                    # Si no hay agentes, dormir un poco más para evitar que los turnos vuelen infinitamente
                    if not current_sim.agentes:
                        time.sleep(0.5)

                    # Broadcast de estado al final de cada paso
                    try:
                        loop = self.main_loop
                        if loop and not loop.is_closed() and loop.is_running():
                            coro = self.broadcast_state(user_id, include_logs=False)
                            asyncio.run_coroutine_threadsafe(coro, loop)
                    except Exception as e:
                        print(f"[RUN_LOOP] Error en broadcast: {e}")

                    # Pausa mínima entre pasos
                    time.sleep(0.0)
            except Exception as e:
                print(f"💥 ERROR CRÍTICO en el bucle de simulación para {user_id}: {e}")
                import traceback

                traceback.print_exc()
            finally:
                self.simulation_threads[user_id] = False
                self.simulation_thread_refs.pop(user_id, None)
                print(f"⏹️ Bucle de simulación terminado para {user_id}")

        thread = threading.Thread(target=run_loop, daemon=True)
        self.simulation_thread_refs[user_id] = thread
        thread.start()

    def stop_simulation_loop(self, user_id: str):
        self.simulation_threads[user_id] = False
        if user_id in self.simulations and hasattr(
            self.simulations[user_id], "_force_stop"
        ):
            self.simulations[user_id]._force_stop = True
            self.simulations[user_id]._stopped = True
        # Esperar a que el hilo de simulación termine completamente
        thread = self.simulation_thread_refs.pop(user_id, None)
        if thread and thread.is_alive():
            print(f"⏳ Esperando a que el hilo de simulación termine para {user_id}...")
            thread.join(timeout=15)
            if thread.is_alive():
                print(
                    f"⚠️ El hilo de simulación para {user_id} no terminó en 15s, continuando de todas formas"
                )
        print(f"⏸️ Simulación detenida para {user_id}")

    async def broadcast_state(
        self, user_id: str, include_logs: bool = False, include_map: bool = False
    ):
        sim = self.simulations.get(user_id)
        if not sim:
            return

        map_was_dirty = bool(getattr(sim, "_map_dirty", False))
        if map_was_dirty:
            include_map = True

        is_first = user_id not in self.last_stats

        # Throttle: no enviar más de una vez por 500ms
        now = time.time()
        last_time = self.last_broadcast_time.get(user_id, 0)
        if now - last_time < 0.5 and not (include_map or include_logs or is_first):
            return  # Skip this broadcast
        self.last_broadcast_time[user_id] = now

        # Determinar si enviamos delta o completo (enviar completo cada 50 pasos para sincronización)
        force_full = (
            include_map or is_first or include_logs or (sim.paso_actual % 50 == 0)
        )

        # Si es la primera vez, forzar la inclusión del mapa si no viene marcada
        effective_include_map = include_map or is_first

        # Construir el payload completo de estadísticas usando el método auxiliar
        current_stats = self._build_stats_payload(
            sim, user_id, include_logs, effective_include_map
        )

        if is_first or force_full:
            await self.send_to_user(user_id, {**current_stats, "type": "stats"})
            self.last_stats[user_id] = current_stats
            if map_was_dirty and hasattr(sim, "_map_dirty"):
                sim._map_dirty = False
        else:
            delta = self.get_delta(self.last_stats.get(user_id, {}), current_stats)
            if delta:
                # Asegurar que socialFeed se envíe si hay cambios
                if "socialFeed" in current_stats and (
                    "socialFeed" not in self.last_stats.get(user_id, {})
                    or len(current_stats["socialFeed"])
                    != len(self.last_stats[user_id].get("socialFeed", []))
                ):
                    delta["socialFeed"] = current_stats["socialFeed"]

                await self.send_to_user(
                    user_id,
                    {
                        "type": "stats_delta",
                        "step": sim.paso_actual,
                        "delta": delta,
                    },
                )
                self.last_stats[user_id] = current_stats
                if map_was_dirty and hasattr(sim, "_map_dirty"):
                    sim._map_dirty = False

        # Agentes
        current_agents = {}
        for a in sim.agentes:
            current_agents[a.unique_id] = {
                "id": a.unique_id,
                "x": a.x,
                "y": a.y,
                "civilizacion_id": a.civilizacion_id,
                "resources": a.recursos,
                "money": a.dinero,
                "grupo_id": a.grupo_id,
                "rol": a.rol,
                "profesion": getattr(a, "profesion", None),
                "reputacion": getattr(a, "reputacion", 1.0),
                "necesidades": a.necesidades,
                "alianzas": a.alianzas,
                "personalidad": a.personalidad,
                "experiencia": a.experiencia,
                "mensajes_enviados_count": getattr(a, "mensajes_enviados_count", 0),
                "pensamiento": getattr(
                    a, "pensamiento_actual", "Esperando estímulos..."
                ),
                "planes": getattr(a, "planes", []),
                "skills": {
                    k: (v if isinstance(v, dict) else v.to_dict())
                    for k, v in a.skills.items()
                },
                "skill_factor": getattr(a, "skill_factor", 0.3),
                "inventario": getattr(a, "inventario", {}),
                "color": sim.civilizaciones[a.grupo_id].color
                if a.grupo_id and a.grupo_id in sim.civilizaciones
                else "#ffffff",
                "is_possessed": a.unique_id == getattr(sim, "agente_poseido_id", None),
                "creencias": getattr(a, "creencias", None).to_dict()
                if hasattr(a, "creencias") and getattr(a, "creencias", None)
                else None,
                "pensamientos_recientes": getattr(a, "pensamientos_recientes", [])[
                    -10:
                ],
                "deseos": getattr(a, "deseos", None).to_dict()
                if hasattr(a, "deseos") and getattr(a, "deseos", None)
                else None,
                "intenciones": getattr(a, "intenciones", None).to_dict()
                if hasattr(a, "intenciones") and getattr(a, "intenciones", None)
                else None,
                "identidad": getattr(a, "identidad", None).to_dict()
                if hasattr(a, "identidad") and getattr(a, "identidad", None)
                else None,
                "alma": getattr(a, "alma", None).to_dict()
                if hasattr(a, "alma") and getattr(a, "alma", None)
                else None,
                "cronicas_publicadas": [
                    c.to_dict() if hasattr(c, "to_dict") else c
                    for c in getattr(a, "cronicas_publicadas", [])
                ],
            }

        last_agents = self.last_agents.get(user_id, {})
        force_full_agents = is_first or include_map

        if force_full_agents:
            await self.send_to_user(
                user_id,
                {"type": "agent_update", "agents": list(current_agents.values())},
            )
            self.last_agents[user_id] = current_agents
        else:
            updates = {}
            for agent_id, agent_data in current_agents.items():
                if agent_id not in last_agents:
                    updates[agent_id] = agent_data
                else:
                    agent_delta = self.get_delta(last_agents[agent_id], agent_data)
                    if agent_delta:
                        updates[agent_id] = agent_delta

            removals = [aid for aid in last_agents if aid not in current_agents]

            if updates or removals:
                await self.send_to_user(
                    user_id,
                    {"type": "agent_delta", "updates": updates, "removals": removals},
                )
                self.last_agents[user_id] = current_agents

        # Relaciones
        if is_first or sim.paso_actual % 5 == 0:
            relationships = []
            for a in sim.agentes:
                for neighbor in a.memoria.grafo.neighbors(a.unique_id):
                    relationships.append(
                        {
                            "source": a.unique_id,
                            "target": neighbor,
                            "type": a.memoria.obtener_tipo(neighbor),
                            "strength": a.memoria.obtener_fuerza(neighbor),
                        }
                    )
            await self.send_to_user(
                user_id, {"type": "relationships", "data": relationships}
            )

    def _build_stats_payload(self, sim, user_id, include_logs, include_map):
        grupos_dinamicos = {}
        civilizaciones_viz = {}

        for civ_id, civ in sim.civilizaciones.items():
            miembros = [
                a
                for a in sim.agentes
                if a.civilizacion_id == civ_id or a.grupo_id == civ_id
            ]
            recursos_totales = sum(a.recursos for a in miembros)

            data_viz = {
                "nombre": civ.nombre,
                "color": civ.color,
                "descripcion": getattr(civ, "descripcion", ""),
                "recursos": recursos_totales,
                "tipo": civ.tipo.lower() if hasattr(civ, "tipo") else "grupo_dinamico",
            }
            civilizaciones_viz[civ_id] = data_viz
            if not (hasattr(civ, "tipo") and civ.tipo == "Civilizacion"):
                grupos_dinamicos[civ_id] = data_viz

        todas_propuestas = []
        for g_id, leyes in sim.facciones_leyes.items():
            for ley in leyes:
                ley_copy = ley.copy()
                ley_copy["grupo_id"] = g_id
                todas_propuestas.append(ley_copy)

        for asamblea in sim.asambleas_globales:
            todas_propuestas.append(
                {
                    "id": asamblea["id"],
                    "proponente_id": asamblea["proponente_id"],
                    "texto": asamblea["tema"],
                    "tipo": "asambleas",
                    "estado": asamblea["estado"],
                    "votos_si": asamblea["votos_si"],
                    "votos_no": asamblea["votos_no"],
                }
            )

        current_stats = {
            "step": sim.paso_actual,
            "groups": len(set(a.grupo_id for a in sim.agentes if a.grupo_id)),
            "economy": sim.economia,
            "weather": sim.weather,
            "lore": sim.lore,
            "civilizaciones": civilizaciones_viz,
            "grupos_dinamicos": grupos_dinamicos,
            "propuestas": todas_propuestas,
            "relaciones_grupos": {
                f"{k[0]}:{k[1]}": v for k, v in sim.relaciones_grupos.items()
            },
            "guerras_activas": [f"{g1}:{g2}" for g1, g2 in sim.guerras_activas],
            "misiones": sim.sistema_misiones.to_dict(),
            "user_score": sim.sistema_misiones.obtener_puntaje(user_id or "default"),
            "recent_completed_missions": getattr(
                sim, "misiones_completadas_este_turno", []
            ),
            "instituciones": {k: v.to_dict() for k, v in sim.instituciones.items()},
            "historia": sim.historia.to_dict(),
            "ranking": [
                {"user_id": r[0], "username": r[1], "puntos": r[2]}
                for r in sim.db.get_ranking()
            ] if sim.db_active else [],
            "logs": (sim.historial_logs[-10:] if include_logs else []),
            "agente_poseido_id": getattr(sim, "agente_poseido_id", None),
            "modo_control_total": getattr(sim, "modo_control_total", False),
            "socialFeed": [
                {
                    "id": p.id,
                    "autor_id": p.autor_id,
                    "autor_nombre": next((a.identidad.nombre or a.unique_id for a in sim.agentes if a.unique_id == p.autor_id), p.autor_id),
                    "contenido": p.contenido,
                    "tipo": p.tipo,
                    "temas": p.temas,
                    "likes": p.likes,
                    "likes_por": getattr(p, "likes_por", []),
                    "comentarios": p.comentarios,
                    "comentarios_detalle": [
                        {
                            "id": c["id"],
                            "autor_id": c["autor_id"],
                            "autor_nombre": next((a.identidad.nombre or a.unique_id for a in sim.agentes if a.unique_id == c["autor_id"]), c["autor_id"]),
                            "contenido": c["contenido"],
                            "timestamp": c["timestamp"],
                        }
                        for c in (
                            sim.social_recsys.interest_recsys.comentarios.get(p.id, [])
                            if hasattr(sim, "social_recsys") and sim.social_recsys
                            else []
                        )
                    ],
                    "timestamp": p.timestamp,
                }
                for p in sorted(
                    (sim.social_recsys.interest_recsys.posts.values() if hasattr(sim, "social_recsys") and sim.social_recsys else []),
                    key=lambda x: x.timestamp,
                    reverse=True
                )[:10]
            ],
        }

        if include_map:
            if hasattr(sim, "world") and sim.world:
                current_stats["mapa"] = sim.world.get_serializable()
            elif hasattr(sim, "mapa") and sim.mapa:
                current_stats["mapa"] = [[t.to_dict() if hasattr(t, "to_dict") else t for t in row] for row in sim.mapa]
        
        return current_stats

    def get_delta(self, old, new):
        if not isinstance(old, dict) or not isinstance(new, dict):
            return new if old != new else None
        diff = {}
        for k, v in new.items():
            if k not in old:
                diff[k] = v
            else:
                if isinstance(v, dict):
                    sub_diff = self.get_delta(old[k], v)
                    if sub_diff is not None:
                        diff[k] = sub_diff
                elif isinstance(v, list):
                    if old[k] != v:
                        diff[k] = v
                elif old[k] != v:
                    diff[k] = v
        return diff if diff else None


session_manager = SessionManager()

# --- MODELOS PYDANTIC ---

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class GameAction(BaseModel):
    user_id: str
    action: str
    modo_control_total: Optional[bool] = False

class SpeedControl(BaseModel):
    ritmo: float

class AIConfig(BaseModel):
    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
    tavily_api_key: Optional[str] = None

class SocialPostRequest(BaseModel):
    content: str
    tipo: str = "opinion"
    temas: list = []

class SocialLikeRequest(BaseModel):
    post_id: str

class SocialCommentRequest(BaseModel):
    post_id: str
    content: str

class QuickPlayRequest(BaseModel):
    user_id: str
    num_agents: int = 12
    save: bool = True

class SaveLoadRequest(BaseModel):
    user_id: str

# --- ENDPOINTS ---

@app.get("/")
async def get():
    return {"message": "MundoIA Game Server Running"}

@app.post("/auth/register")
async def register(req: UserRegister):
    db = DatabaseManager()
    if not db.connect(): raise HTTPException(status_code=500, detail="DB Error")
    user_id = db.create_user(req.username, req.password)
    if user_id: return {"status": "success", "user_id": user_id, "username": req.username}
    raise HTTPException(status_code=400, detail="User exists")

@app.post("/auth/login")
async def login(req: UserLogin):
    db = DatabaseManager()
    if not db.connect(): raise HTTPException(status_code=500, detail="DB Error")
    user_id = db.verify_user(req.username, req.password)
    if user_id: return {"status": "success", "user_id": user_id, "username": req.username}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/game/control")
async def game_control(req: GameAction):
    sim = session_manager.get_simulation(req.user_id)
    if req.action == "start":
        if sim and req.modo_control_total is not None:
            sim.modo_control_total = req.modo_control_total
            # Si activamos modo control total desde la API, preparar el ciclo controlado
            if req.modo_control_total:
                try:
                    sim._prepare_control_round()
                except Exception:
                    pass
        session_manager.start_simulation_loop(req.user_id)
        return {"status": "success"}
    elif req.action == "pause":
        session_manager.stop_simulation_loop(req.user_id)
        return {"status": "success"}
    elif req.action == "step":
        if sim:
            sim.step()
            await session_manager.broadcast_state(req.user_id)
            return {"status": "success"}
    elif req.action == "reset":
        # 1. Detener el bucle actual
        session_manager.stop_simulation_loop(req.user_id)
        
        # 2. Eliminar rastro de la simulación anterior
        session_manager.simulations.pop(req.user_id, None)
        session_manager.last_stats.pop(req.user_id, None)
        session_manager.last_agents.pop(req.user_id, None)
        
        # 3. Crear una nueva simulación vacía
        sim = session_manager.create_simulation(req.user_id, start_empty=True)
        
        # 4. Forzar guardado del estado vacío en DB para limpiar la partida anterior
        if sim.db_active:
            try:
                sim.guardar_estado()
                print(f"🧹 [RESET] Base de Datos limpiada para {req.user_id}")
            except Exception as e:
                print(f"⚠️ [RESET] Error limpiando DB: {e}")
        
        # 5. Notificar al frontend el nuevo estado vacío
        await session_manager.broadcast_state(req.user_id, include_map=True, include_logs=True)
        
        return {"status": "success", "message": "Nueva realidad generada y persistida"}
    return {"status": "error"}

class GodAction(BaseModel):
    action_type: str
    params: Dict[str, Any]

@app.post("/game/god-mode/{user_id}")
async def god_mode(user_id: str, req: GodAction):
    sim = session_manager.get_simulation(user_id)
    if not sim: sim = session_manager.create_simulation(user_id)
    
    action_type = req.action_type
    params = req.params

    if action_type == "POSSESS_AGENT":
        sim.agente_poseido_id = params.get("agent_id")
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif action_type == "SPAWN_AGENT":
        count = params.get("count", 1)
        role = params.get("role")
        for _ in range(count):
            # spawn_agent expects a config dict — pass role inside it
            cfg = {} if not role else {"rol": role}
            sim.spawn_agent(cfg)
        
        # Forzar envío completo tras spawn para evitar condiciones de throttle
        # que podrían impedir que el frontend reciba los nuevos agentes.
        await session_manager.broadcast_state(user_id, include_map=True)
        return {"status": "success", "message": f"{count} agentes invocados"}

    elif action_type == "AGENT_EXECUTE_ACTION":
        agent_id = params.get("agent_id")
        action = params.get("action")
        payload = params.get("payload", {})
        
        agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
        if not agent: raise HTTPException(status_code=404, detail="Agent not found")
        
        user_action = {"nombre": action.upper(), "argumentos": payload}
        
        from agents.cerebro_langgraph import analizar_situacion
        res = analizar_situacion({"agente_yo_id": agent.unique_id, "modelo_instance": sim, "info_externa": ""})
        contexto = res.get("info_externa", "Control total.")
        
        # En modo control total, delegar al método de turno controlado y marcar agente como completado.
        if getattr(sim, "modo_control_total", False):
            # Preparar ciclo si aún no está activo
            if not getattr(sim, "_control_round_active", False):
                try:
                    sim._prepare_control_round()
                except Exception:
                    pass

            # Asignar la acción de control al agente y procesar su turno completo
            agent.acciones_control_usuario = [user_action]
            try:
                sim._procesar_turno_agente(agent)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error ejecutando turno del agente: {e}")

            # Marcar que el agente completó su acción en este ciclo controlado
            try:
                sim._mark_control_agent_done(agent.unique_id)
            except Exception:
                pass

            await session_manager.broadcast_state(user_id)
            return {"status": "success"}

        # Modo autónomo / fallback: generar decisión rápida y ejecutar acción
        if hasattr(sim, "cerebro_llm") and sim.cerebro_llm:
            decision = sim.cerebro_llm.generar_pensamiento_para_accion_forzada(agent, None, contexto, user_action)
        else:
            decision = {"pensamiento": "Actúo.", "mensaje": "Lo hago.", "accion": user_action}
        
        if decision.get("pensamiento"): agent.pensamiento_actual = decision["pensamiento"]
        if decision.get("mensaje"): agent.decir(decision["mensaje"], pensamiento=decision.get("pensamiento"))
        
        agent.ejecutar_accion_final(decision.get("accion", user_action))
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif action_type == "SET_CONTROL_ACTIONS":
        agent_id = params.get("agent_id")
        actions = params.get("actions", [])
        agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
        if agent: agent.acciones_control_usuario = actions[:3]
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    return {"status": "error"}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await session_manager.connect(user_id, websocket)
    sim = session_manager.get_simulation(user_id)
    if not sim: sim = session_manager.create_simulation(user_id)
    await session_manager.broadcast_state(user_id, include_logs=True, include_map=True)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.disconnect(user_id)

@app.get("/games/list/{user_id}")
async def list_games(user_id: str):
    db = DatabaseManager()
    if db.connect():
        # Devuelve un resumen básico para la lista
        sim = session_manager.get_simulation(user_id)
        current_score = sim.sistema_misiones.obtener_puntaje(user_id) if sim else 0
        current_step = sim.paso_actual if sim else 0
        
        # En una versión real, esto consultaría una tabla de partidas. 
        # Aquí simulamos la existencia de la partida actual si hay datos en DB.
        state = db.get_world_state(user_id)
        if state:
            return {"games": [{"id": "current", "paso_actual": state[0], "score": current_score}]}
    return {"games": []}

@app.post("/games/save")
async def save_game(req: SaveLoadRequest):
    sim = session_manager.get_simulation(req.user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación activa no encontrada")
    
    try:
        sim.guardar_estado()
        return {"status": "success", "message": "Partida guardada en PostgreSQL"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar: {e}")

@app.post("/games/load")
async def load_game(req: SaveLoadRequest):
    # Detener bucle actual si existe
    session_manager.stop_simulation_loop(req.user_id)
    
    # Crear nueva instancia (cargar_estado se llama en __init__ o explícitamente)
    sim = session_manager.create_simulation(req.user_id, start_empty=False)
    sim.cargar_estado()
    
    await session_manager.broadcast_state(req.user_id, include_map=True, include_logs=True)
    return {"status": "success", "message": "Partida cargada correctamente"}

@app.post("/games/quickplay")
async def quickplay(req: QuickPlayRequest):
    session_manager.stop_simulation_loop(req.user_id)
    
    # Resetear y crear nueva
    sim = session_manager.create_simulation(req.user_id, start_empty=True)
    sim.paso_actual = 1
    
    # Generar agentes aleatorios
    for i in range(req.num_agents):
        sim.spawn_agent()
        
    if req.save:
        sim.guardar_estado()
        
    await session_manager.broadcast_state(req.user_id, include_map=True, include_logs=True)
    return {"status": "success", "message": f"Partida rápida iniciada con {req.num_agents} agentes"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
