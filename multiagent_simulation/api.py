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
            print(f"🔌 Usuario {user_id} desconectado")

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            try:
                # Use DateTimeEncoder to handle potential datetime objects in the message
                await self.active_connections[user_id].send_text(
                    json.dumps(message, cls=DateTimeEncoder)
                )
                print(f"✅ Enviado a {user_id}: tipo={message.get('type')}")
            except Exception as e:
                print(f"Error enviando a {user_id}: {e}")
                self.disconnect(user_id)
        else:
            print(
                f"⚠️ Usuario {user_id} no está conectado, mensaje perdido: {message.get('type')}"
            )

    def enqueue_message(self, user_id: str, message: dict):
        """Encola un mensaje para ser procesado por el loop principal de asyncio."""
        try:
            if hasattr(self, "main_loop") and self.main_loop is not None:
                loop = self.main_loop
            else:
                loop = asyncio.get_event_loop()

            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.message_queue.put((user_id, message)), loop
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
                user_id, message = await asyncio.wait_for(
                    self.message_queue.get(), timeout=0.5
                )
                print(
                    f"[QUEUE] Procesando mensaje tipo={message.get('type')} para {user_id}"
                )
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
            def user_log_callback(
                mensaje,
                categoria,
                subtitulos,
                tts_text,
                pensamiento=None,
                privado_para=None,
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
                        },
                    )
                except Exception as e:
                    print(f"[LOG_CALLBACK] Error: {e}, mensaje: {mensaje[:50]}...")

            # Callback para cambios de estado (actualización inmediata de UI)
            def on_state_change():
                sim = self.simulations.get(user_id)
                if sim and not getattr(sim, "_stopped", False):
                    try:
                        # Emitir estado completo inmediatamente al detectar un cambio crítico
                        if self.main_loop:
                            asyncio.run_coroutine_threadsafe(
                                self.broadcast_state(user_id), self.main_loop
                            )
                    except Exception as e:
                        print(f"[STATE_CHANGE] Error en broadcast: {e}")

            num_agentes = int(os.getenv("NUM_AGENTES", 30))
            self.simulations[user_id] = ModeloRelacional(
                num_agentes=num_agentes,
                log_callback=user_log_callback,
                user_id=user_id,
                start_empty=start_empty,
            )
            self.simulations[
                user_id
            ].state_change_callback = on_state_change  # Conectar callback
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

                    current_sim.step()

                    # Broadcast de estado final del paso
                    try:

                        async def do_broadcast():
                            await self.broadcast_state(user_id, include_logs=False)

                        asyncio.run_coroutine_threadsafe(do_broadcast(), self.main_loop)
                    except Exception as e:
                        print(f"[RUN_LOOP] Error en broadcast: {e}")

                    # Pausa mínima entre pasos
                    time.sleep(0.1)
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

        # Determinar si enviamos delta o completo (enviar completo cada 50 pasos para sincronización)
        is_first = user_id not in self.last_stats
        force_full = include_map or is_first or include_logs or (sim.paso_actual % 50 == 0)
        
        # Si es la primera vez, forzar la inclusión del mapa si no viene marcada
        effective_include_map = include_map or is_first
        
        # Construir el payload completo de estadísticas usando el método auxiliar
        current_stats = self._build_stats_payload(sim, user_id, include_logs, effective_include_map)

        if is_first or force_full:
            await self.send_to_user(user_id, {**current_stats, "type": "stats"})
            self.last_stats[user_id] = current_stats
        else:
            delta = self.get_delta(self.last_stats.get(user_id, {}), current_stats)
            if delta:
                # IMPORTANTE: Asegurar que socialFeed se envíe si hay cambios,
                # a veces get_delta puede fallar con listas de objetos complejos.
                if "socialFeed" in current_stats and (
                    "socialFeed" not in self.last_stats.get(user_id, {}) or 
                    len(current_stats["socialFeed"]) != len(self.last_stats[user_id].get("socialFeed", []))
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
                # Campos BDI (Beliefs-Desires-Intentions)
                "creencias": getattr(a, "creencias", None).to_dict()
                if hasattr(a, "creencias") and getattr(a, "creencias", None)
                else None,
                # Stream of Consciousness (historial limitado)
                "pensamientos_recientes": getattr(a, "pensamientos_recientes", [])[-10:],
                "deseos": getattr(a, "deseos", None).to_dict()
                if hasattr(a, "deseos") and getattr(a, "deseos", None)
                else None,
                "intenciones": getattr(a, "intenciones", None).to_dict()
                if hasattr(a, "intenciones") and getattr(a, "intenciones", None)
                else None,
                # MundoVivo
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
        # Forzar actualización completa si es la primera vez o se pide el mapa (reset/inicio)
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
                # Actualizar rastro de agentes con el estado completo actual
                self.last_agents[user_id] = current_agents

        # Relaciones (enviar en primera conexión y cada 5 pasos)
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
        """Construye el payload de estadísticas para el usuario."""
        # Construir diccionario de grupos dinámicos y preparar lista de civilizaciones reales
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
                "tipo": civ.tipo.lower()
                if hasattr(civ, "tipo")
                else "grupo_dinamico",
            }
            civilizaciones_viz[civ_id] = data_viz
            if hasattr(civ, "tipo") and civ.tipo == "Civilizacion":
                pass
            else:
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
            ]
            if sim.db_active
            else [],
            "logs": sim.historial_logs if include_logs else [],
            "agente_poseido_id": getattr(sim, "agente_poseido_id", None),
            "socialFeed": [
                {
                    "id": p.id,
                    "autor_id": p.autor_id,
                    "contenido": p.contenido,
                    "tipo": p.tipo,
                    "temas": p.temas,
                    "likes": p.likes,
                    "likes_por": getattr(p, 'likes_por', []),
                    "comentarios": p.comentarios,
                    "comentarios_detalle": [
                        {
                            "id": c.id,
                            "autor_id": c.autor_id,
                            "contenido": c.contenido,
                            "timestamp": c.timestamp
                        } for c in (sim.social_recsys.interest_recsys.comentarios.get(p.id, []) if hasattr(sim, 'social_recsys') and sim.social_recsys and hasattr(sim.social_recsys, 'interest_recsys') else [])
                    ],
                    "timestamp": p.timestamp
                } for p in (sim.social_recsys.interest_recsys.posts.values() if hasattr(sim, 'social_recsys') and sim.social_recsys and hasattr(sim.social_recsys, 'interest_recsys') else [])
            ],
        }

        if include_map:
            # Obtener el mapa de forma robusta desde WorldSystem
            if hasattr(sim, 'world') and sim.world:
                current_stats["mapa"] = sim.world.get_serializable()
            elif hasattr(sim, 'mapa') and sim.mapa:
                current_stats["mapa"] = [[t.to_dict() if hasattr(t, 'to_dict') else t for t in row] for row in sim.mapa]
            else:
                # Generar mapa de emergencia si sigue vacío
                print("⚠️ [WS] Mapa vacío, intentando regenerar...")
                if hasattr(sim, 'generar_mapa'):
                    sim.generar_mapa()
                    current_stats["mapa"] = sim.world.get_serializable() if hasattr(sim, 'world') else []

        # Debug social feed
        if current_stats.get("socialFeed"):
            print(f"📱 [DEBUG WS] Enviando {len(current_stats['socialFeed'])} posts en el feed social.")

        return current_stats

    def get_delta(self, old, new):
        """Calcula la diferencia entre dos diccionarios."""
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
    action: str  # "start", "pause", "reset"


class SpeedControl(BaseModel):
    ritmo: float  # segundos entre cada agente


class AIConfig(BaseModel):
    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
    tavily_api_key: Optional[str] = None


# --- ENDPOINTS ---


@app.get("/")
async def get():
    return {"message": "MundoIA Game Server Running"}



# === ENDPOINTS COMPATIBILIDAD FRONTEND ===

@app.get("/chat/{user_id}/map")
async def get_chat_map(user_id: str):
    """Obtiene el mapa de terreno para una simulación (usado por frontend)."""
    modelo = session_manager.simulations.get(user_id)
    if not modelo or not hasattr(modelo, 'mapa') or not modelo.mapa:
        raise HTTPException(status_code=404, detail="Mapa no disponible")

    map_data = []
    filas = len(modelo.mapa)
    cols = len(modelo.mapa[0]) if filas > 0 else 0
    for x in range(filas):
        row = []
        for y in range(cols):
            tile = modelo.mapa[x][y] if y < len(modelo.mapa[x]) else None
            if tile:
                row.append(tile.to_dict())
            else:
                row.append(None)
        map_data.append(row)

    return {"map": map_data, "filas": filas, "cols": cols, "user_id": user_id}


@app.get("/chat/{user_id}/stats")
async def get_chat_stats(user_id: str):
    """Obtiene estadísticas actualizadas de la simulación."""
    modelo = session_manager.simulations.get(user_id)
    if not modelo:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    
    stats = {
        "step": modelo.paso_actual,
        "num_agents": len(modelo.agentes),
        "num_groups": len(modelo.grupos_creados_este_paso),
        "user_id": user_id
    }
    
    return stats


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
    print(
        f"🔌 WS: Usuario {user_id} conectado. Total conexiones: {len(session_manager.active_connections)}"
    )

    # Verificar si tiene simulación activa, si no, crearla
    sim = session_manager.get_simulation(user_id)
    if not sim:
        print(f"🔌 WS: Creando simulación para {user_id}")
        sim = session_manager.create_simulation(user_id)

    # REGENERACIÓN DE EMERGENCIA SI MAPA ESTÁ VACÍO
    if not hasattr(sim, 'mapa') or len(sim.mapa) == 0:
        print("🚨 [WS] Mapa vacío al conectar. Forzando generación...")
        if hasattr(sim, 'generar_mapa'):
            sim.generar_mapa()

    # Enviar estado inicial con logs históricos y MAPA completo
    await session_manager.broadcast_state(user_id, include_logs=True, include_map=True)

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
        raise HTTPException(
            status_code=500, detail="Error de conexión a la base de datos"
        )

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
        raise HTTPException(
            status_code=500, detail="Error de conexión a la base de datos"
        )

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
    elif req.action == "step":
        sim = session_manager.get_simulation(req.user_id)
        if sim:
            sim.step()
            # Send immediate update
            await session_manager.broadcast_state(req.user_id)
            return {"status": "success", "message": "Paso ejecutado"}
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    elif req.action == "reset":
        print(f"--- DEBUG: Recibida acción de RESET para user_id: {req.user_id} ---")

        # 1. Detener el bucle actual y esperar a que el hilo termine
        session_manager.stop_simulation_loop(req.user_id)

        # 2. Notificar al frontend para que limpie TODA su UI (agentes, grupos, logs, etc.)
        await session_manager.send_to_user(req.user_id, {"type": "world_reset"})
        # Enviar relaciones vacías explícitamente para asegurar limpieza total
        await session_manager.send_to_user(
            req.user_id, {"type": "relationships", "data": []}
        )

        # 3. LIMPIEZA DE BASE DE DATOS (Independiente de si hay simulación en memoria)
        try:
            db = DatabaseManager()
            if db.connect():
                print(
                    f"--- DEBUG: Limpiando base de datos para user_id: {req.user_id} ---"
                )
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
        if new_sim:
            if new_sim.mapa is None:
                 print("--- DEBUG: Generando mapa para la nueva partida... ---")
                 new_sim.mapa = new_sim.generar_mapa()
            
            if new_sim.db_active:
                print("--- DEBUG: Guardando nueva simulación inicial VACÍA en DB... ---")
                new_sim.guardar_estado()

        # 6. ENVIAR ESTADO INICIAL (Con mapa nuevo)
        print("--- DEBUG: Enviando nuevo estado al frontend... ---")
        await session_manager.broadcast_state(req.user_id, include_map=True)

        # 7. La sesión queda en PAUSA (no se inicia el bucle automáticamente)
        print("--- DEBUG: Proceso de RESET completado. Sesión en pausa. ---")
        return {"status": "success", "message": "Mundo reiniciado completamente"}

    raise HTTPException(status_code=400, detail="Acción desconocida")


@app.post("/game/speed/{user_id}")
async def set_speed(user_id: str, req: SpeedControl):
    """Controla el ritmo de lectura entre agentes (segundos). 0 = sin pausa."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    sim.ritmo_lectura = max(0.0, min(req.ritmo, 10.0))
    return {"status": "success", "ritmo": sim.ritmo_lectura}


@app.get("/tts")
async def text_to_speech(text: str):
    tts_url = os.getenv("TTS_URL", "http://localhost:5050/v1/audio/speech")
    try:
        response = requests.post(
            tts_url,
            json={"input": text, "voice": "es-MX-DaliaNeural", "model": "edge-tts"},
            timeout=5,
        )
        if response.status_code == 200:
            return StreamingResponse(iter([response.content]), media_type="audio/mpeg")
    except:
        pass
    return {"error": "TTS unavailable"}


class GodAction(BaseModel):
    action_type: str  # 'DISASTRE', 'RESOURCE_BOOST', 'FORCE_ALLIANCES', 'SET_GLOBAL_CONTEXT', 'SPAWN_AGENT'
    params: Dict[str, Any]


class AgentConfig(BaseModel):
    name: Optional[str] = None
    personality: Optional[Dict[str, float]] = None
    resources: Optional[float] = 0.0
    money: Optional[float] = 100.0
    position: Optional[Dict[str, int]] = None  # {"x": 10, "y": 10}


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
            sim.log_callback(
                f"🌩️ [DIVINO] El clima ha cambiado a {new_weather} por voluntad del Arquitecto.",
                "ambiente",
                None,
                f"El clima cambia a {new_weather}",
            )
            await session_manager.broadcast_state(
                user_id
            )  # Actualizar frontend inmediatamente
            return {"status": "success", "message": f"Clima cambiado a {new_weather}"}

    elif req.action_type == "EXECUTE_SKILL":
        agent_id = req.params.get("agent_id")
        skill_name = req.params.get("skill_name")
        argumentos = req.params.get("argumentos", {})
        
        agente = sim.get_agent_by_id(agent_id)
        if not agente:
            raise HTTPException(status_code=404, detail="Agente no encontrado")
            
        from skills_manager import skill_manager
        resultado = skill_manager.ejecutar_skill(
            skill_name, 
            argumentos, 
            agente_id=agent_id, 
            agent_skills=agente.skills
        )
        
        # Enviar actualización inmediata si la skill cambió algo
        await session_manager.broadcast_state(user_id)
        
        return {"status": "success", "resultado": resultado}

    elif req.action_type == "EXECUTE_APP":
        agent_id = req.params.get("agent_id")
        app_name = req.params.get("app_name")
        
        agente = sim.get_agent_by_id(agent_id)
        if not agente:
            raise HTTPException(status_code=404, detail="Agente no encontrado")
            
        app_data = agente.apps.get(app_name)
        if not app_data:
            raise HTTPException(status_code=404, detail="App no encontrada")
            
        from herramientas import herramientas
        resultado = herramientas.ejecutar_codigo_seguro(
            app_data["code"], 
            agente_id=agent_id
        )
        
        return {"status": "success", "resultado": resultado}

    elif req.action_type == "TRIGGER_EVENT":
        event_type = req.params.get("event")
        if event_type == "earthquake":
            # Lógica simple de terremoto: dañar edificios o agentes al azar
            afectados = 0
            for a in sim.agentes:
                if random.random() < 0.3:
                    a.necesidades["salud"] -= 3
                    afectados += 1
            sim.log_callback(
                f"🌍 [DIVINO] ¡Un TERREMOTO ha sacudido el mundo! {afectados} agentes heridos.",
                "evento",
                None,
                "Terremoto detectado",
            )
        elif event_type == "plague":
            for a in sim.agentes:
                a.necesidades["salud"] -= 1  # Contagio inicial
            sim.log_callback(
                "☣️ [DIVINO] Una PLAGA se ha desatado sobre la población.",
                "evento",
                None,
                "Alerta de plaga",
            )

        await session_manager.broadcast_state(user_id)
        return {"status": "success", "message": f"Evento {event_type} disparado"}

    elif req.action_type == "MODIFY_ECONOMY":
        action = req.params.get("sub_action")  # "inject_money", "crash_market"
        if action == "inject_money":
            sim.economia["total_dinero"] += 1000
            sim.economia["precio_recurso"] *= (
                0.8  # Inflación baja precios (simplificado)
            )
            sim.log_callback(
                "💸 [DIVINO] Se ha inyectado capital divino en la economía.",
                "economia",
                None,
                "Inyección económica",
            )
        elif action == "crash_market":
            sim.economia["indice_bursatil"] *= 0.5
            sim.economia["precio_recurso"] *= 2.0  # Escasez sube precios
            sim.log_callback(
                "📉 [DIVINO] ¡El mercado ha COLAPSADO por orden del Arquitecto!",
                "economia",
                None,
                "Crash del mercado",
            )

        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif req.action_type == "MODIFY_AGENT":
        agent_id = req.params.get("agent_id")
        effect = req.params.get("effect")  # "heal", "smite", "enrich"
        agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)

        if agent:
            if effect == "heal":
                agent.necesidades["salud"] = 10.0
                agent.necesidades["alimento"] = 0.0
                sim.log_callback(
                    f"✨ [DIVINO] El Agente {agent_id} ha sido SANADO completamente.",
                    "milagro",
                    None,
                    "Curación divina",
                )
            elif effect == "smite":
                agent.necesidades["salud"] = 1.0
                agent.recursos = 0
                sim.log_callback(
                    f"⚡ [DIVINO] ¡El Agente {agent_id} ha sido CASTIGADO!",
                    "milagro",
                    None,
                    "Castigo divino",
                )
            elif effect == "enrich":
                agent.dinero += 500
                sim.log_callback(
                    f"💰 [DIVINO] El Agente {agent_id} ha recibido una fortuna.",
                    "milagro",
                    None,
                    "Riqueza divina",
                )

            await session_manager.broadcast_state(user_id)
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404, detail="Agente no encontrado")

    elif req.action_type == "SET_GLOBAL_CONTEXT":
        new_lore = req.params.get("lore")
        sim.lore = new_lore
        sim.log_callback(
            f"📜 [NARRATIVA] El Arquitecto ha redefinido la realidad: '{new_lore}'",
            "sistema",
            None,
            "Contexto actualizado",
        )

        # Persistencia inmediata del LORE para evitar pérdida en reinicios
        if hasattr(sim, "persistir_estado"):
            sim.persistir_estado()

        await session_manager.broadcast_state(user_id)
        return {"status": "success", "message": "Lore actualizado"}

    elif req.action_type == "SPAWN_AGENT":
        count = req.params.get("count", 1)
        config_data = req.params.get("config")  # Opcional

        spawned_ids = []
        for _ in range(count):
            # Convertir el diccionario de config_data a un objeto AgentConfig si existe
            config = AgentConfig(**config_data) if config_data else None
            agente = sim.spawn_agent(config=config)
            spawned_ids.append(agente.unique_id)

        sim.log_callback(
            f"🧬 [DIVINO] Ha manifestado {len(spawned_ids)} nuevos seres en el mundo.",
            "sistema",
            None,
            f"Inyectados {len(spawned_ids)} agentes",
        )
        await session_manager.broadcast_state(user_id)
        return {
            "status": "success",
            "message": f"Inyectados {len(spawned_ids)} agentes",
            "ids": spawned_ids,
        }

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
        sim.log_callback(
            f"👤 [POSESIÓN] El Arquitecto ha descendido sobre el cuerpo del Agente {agent_id}.",
            "sistema",
            None,
            "Posesión divina iniciada",
        )
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
            exito = True
            msg = "Recolección divina completada"
            sim.log_callback(
                f"🌾 [POSESIÓN] El Agente {agent_id} (poseído) ha recolectado recursos.",
                "accion",
                None,
                "Recolección completada",
            )
        elif action == "fundar_grupo":
            nombre = payload.get("nombre", "Nueva Orden")
            descripcion = payload.get("descripcion", "Sin descripción")
            agent.fundar_grupo(nombre, descripcion)
            exito = True
            msg = f"Grupo '{nombre}' fundado por voluntad divina"
            sim.log_callback(
                f"🏛️ [POSESIÓN] El Agente {agent_id} (poseído) ha fundado el grupo '{nombre}'.",
                "sistema",
                None,
                f"Grupo {nombre} fundado",
            )
        elif action == "proponer_ley":
            tipo = payload.get("tipo", "LEY_GENERAL")
            descripcion = payload.get("descripcion", "Decreto Divino")
            # Llamar a la lógica de propuesta en el modelo
            sim.facciones_leyes.setdefault("propuestas", []).append(
                {
                    "id": f"P-{random.randint(1000, 9999)}",
                    "proponente": agent_id,
                    "descripcion": descripcion,
                    "tipo": tipo,
                    "votos_favor": 1,  # El proponente ya votó
                    "votos_contra": 0,
                    "paso_creacion": sim.paso_actual,
                }
            )
            sim.log_callback(
                f"📜 [DECRETO] El Agente {agent_id} (poseído) ha propuesto una ley: {descripcion}",
                "consenso",
                None,
                "Nueva propuesta de ley",
            )
            exito = True
            msg = "Ley propuesta"
        elif action == "decir":
            mensaje = payload.get("mensaje", "Mensaje desde el Arquitecto")
            global_broadcast = payload.get("global_broadcast", False)
            para_grupo = payload.get("para_grupo", False)
            privado_para = payload.get("privado_para")
            agent.decir(
                mensaje,
                global_broadcast=global_broadcast,
                para_grupo=para_grupo,
                privado_para=privado_para,
            )
            exito = True
            msg = "Mensaje enviado"
        elif action == "socializar":
            otro_agente_id = payload.get("otro_agente_id")
            if otro_agente_id:
                otro_agente = next(
                    (a for a in sim.agentes if a.unique_id == otro_agente_id), None
                )
                if otro_agente:
                    agent.interactuar(otro_agente, "social")
                    exito = True
                    msg = f"Socializado con {otro_agente_id}"
                    sim.log_callback(
                        f"🤝 [POSESIÓN] El Agente {agent_id} (poseído) socializa con {otro_agente_id}.",
                        "social",
                        None,
                        "Interacción social",
                    )
        elif action == "competir":
            otro_agente_id = payload.get("otro_agente_id")
            if otro_agente_id:
                otro_agente = next(
                    (a for a in sim.agentes if a.unique_id == otro_agente_id), None
                )
                if otro_agente:
                    agent.interactuar(otro_agente, "COMPETIR")
                    exito = True
                    msg = f"Competición con {otro_agente_id}"
                    sim.log_callback(
                        f"⚔️ [POSESIÓN] El Agente {agent_id} (poseído) compite con {otro_agente_id}.",
                        "conflict",
                        None,
                        "Interacción competitiva",
                    )
        elif action == "mover":
            x = payload.get("x")
            y = payload.get("y")
            if x is not None and y is not None:
                agent.x = x
                agent.y = y
                exito = True
                msg = f"Movido a ({x}, {y})"
                sim.log_callback(
                    f"🚶 [POSESIÓN] El Agente {agent_id} (poseído) se ha movido a ({x}, {y}).",
                    "movimiento",
                    None,
                    "Movimiento ejecutado",
                )
        elif action == "construir":
            tipo_edific = payload.get("tipo", "Casa")
            exito, msg = agent.construir(tipo_edific)
            if exito:
                sim.log_callback(
                    f"🏗️ [POSESIÓN] El Agente {agent_id} (poseído) ha construido un {tipo_edific}.",
                    "construccion",
                    None,
                    "Construcción exitosa",
                )
        elif action == "votar":
            propuesta_id = payload.get("propuesta_id")
            voto = payload.get("voto", "si")
            a_favor = voto.lower() == "si"
            exito = agent.votar_ley(propuesta_id, a_favor=a_favor)
            msg = (
                f"Voto {voto} emitido para {propuesta_id}"
                if exito
                else "Fallo al votar (ya votaste o no existe)"
            )
            if exito:
                sim.log_callback(
                    f"🗳️ [POSESIÓN] El Agente {agent_id} (poseído) ha votado {voto} a {propuesta_id}.",
                    "consenso",
                    None,
                    "Voto emitido",
                )
        elif action == "atacar":
            otro_agente_id = payload.get("otro_agente_id")
            if otro_agente_id:
                otro_agente = next(
                    (a for a in sim.agentes if a.unique_id == otro_agente_id), None
                )
                if otro_agente:
                    agent.atacar(otro_agente)
                    exito = True
                    msg = f"Ataque a {otro_agente_id} ejecutado"
        elif action == "comer":
            exito, msg = agent.comer()
        elif action == "curarse":
            exito, msg = agent.curar()
        elif action == "descansar":
            exito, msg = agent.descansar()
        elif action == "explorar":
            exito, msg = agent.explorar()
        elif action == "estudiar":
            exito, msg = agent.estudiar()
        elif action == "investigar":
            exito, msg = agent.investigar()
        elif action == "opinar":
            mensaje = payload.get("mensaje", "")
            exito, msg = agent.opinar(mensaje)
        elif action == "fundar_institucion":
            nombre = payload.get("nombre", "Nueva Institución")
            tipo = payload.get("tipo", "Ciencia")
            exito, msg = agent.fundar_institucion(nombre, tipo)
        elif action == "mejorar_seguridad":
            exito = agent.mejorar_seguridad()
            msg = "Seguridad mejorada" if exito else "Fallo al mejorar seguridad"
        elif action == "invertir":
            monto = float(payload.get("monto", 10))
            exito = agent.invertir(monto)
            msg = f"Inversión de {monto} MC realizada" if exito else "Fallo al invertir"
        elif action == "formar_alianza":
            otro_agente_id = payload.get("otro_agente_id")
            if otro_agente_id:
                otro_agente = next(
                    (a for a in sim.agentes if a.unique_id == otro_agente_id), None
                )
                if otro_agente:
                    exito = agent.formar_alianza(otro_agente)
                    msg = (
                        f"Alianza formada con {otro_agente_id}"
                        if exito
                        else "Alianza rechazada o ya existe"
                    )

        await session_manager.broadcast_state(user_id)
        return {"status": "success", "message": msg}

    elif req.action_type == "START_ASSEMBLY":
        tema = req.params.get("topic", "Asambleas Divinas")
        # El Arquitecto inicia la asamblea. Usamos "Arquitecto" como ID o el sistema debe permitirlo.
        # modelo.crear_asamblea espera un proponente_id
        exito, msg = sim.crear_asamblea("Arquitecto", tema)

        if exito:
            sim.log_callback(
                f"🏛️ [DIVINO] El Arquitecto ha convocado una ASAMBLEA GLOBAL: '{tema}'",
                "consenso",
                None,
                "Asamblea convocada",
            )
            await session_manager.broadcast_state(user_id)
            return {"status": "success", "message": msg}
        else:
            return {"status": "error", "message": msg}

    elif req.action_type == "EXPAND_WORLD":
        direccion = req.params.get("direccion")  # 'north', 'south', 'east', 'west', o None
        cantidad = req.params.get("cantidad", 5)
        comprador_id = req.params.get("comprador_id", "arquitecto")  # Por defecto arquitecto
        exito, msg = sim.expandir_mundo(direccion=direccion, cantidad=cantidad, comprador_id=comprador_id)
        if exito:
            await session_manager.broadcast_state(user_id, include_map=True)
            return {"status": "success", "message": msg}
        else:
            raise HTTPException(status_code=400, detail=msg)

    elif req.action_type == "PURCHASE_LAND":
        grupo_id = req.params.get("grupo_id")
        direccion = req.params.get("direccion")  # 'north', 'south', 'east', 'west', o None
        cantidad = req.params.get("cantidad", 1)

        if not grupo_id:
            raise HTTPException(status_code=400, detail="Se requiere grupo_id")

        exito, msg = sim.comprar_terreno_grupo(grupo_id, direccion=direccion, cantidad=cantidad)
        if exito:
            await session_manager.broadcast_state(user_id, include_map=True)
            return {"status": "success", "message": msg}
        else:
            raise HTTPException(status_code=400, detail=msg)

    elif req.action_type == "ARCHITECT_MESSAGE":
        mensaje = req.params.get("mensaje")
        agente_id = req.params.get("agent_id")  # Optional para mensajes globales

        if not mensaje:
            raise HTTPException(status_code=400, detail="Se requiere el mensaje")

        # CASO 1: Mensaje a un agente específico (comportamiento actual)
        if agente_id:
            agent = next((a for a in sim.agentes if a.unique_id == agente_id), None)
            if not agent:
                raise HTTPException(
                    status_code=404, detail=f"Agente {agente_id} no encontrado"
                )

            if agent.necesidades.get("salud", 0) <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Este agente ha fallecido y no puede responder",
                )

            print(
                f"🔍 [ARCHITECT_MESSAGE] Procesando mensaje para {agente_id}: '{mensaje[:50]}...'"
            )

            # Guardar mensaje del usuario en DB
            sim.db.save_chat_message(user_id, agente_id, "user", mensaje, time.time())

            # Contexto del agente para el LLM (similar a chat_send_message)
            p = agent.personalidad
            necesidades = {
                k: round(max(0, min(10, v)), 1) for k, v in agent.necesidades.items()
            }

            relaciones_info = []
            try:
                for neighbor in agent.memoria.grafo.neighbors(agent.unique_id):
                    tipo = agent.memoria.obtener_tipo(neighbor)
                    fuerza = agent.memoria.obtener_fuerza(neighbor)
                    relaciones_info.append(f"{neighbor} ({tipo}, fuerza {fuerza:.1f})")
            except Exception as e:
                print(
                    f"⚠️ [RELACIONES] Error obteniendo relaciones para {agente_id}: {e}"
                )
            relaciones_str = (
                ", ".join(relaciones_info[:10])
                if relaciones_info
                else "Ninguna relación registrada"
            )

            # Obtener historial reciente
            historial = sim.db.get_chat_history(user_id, agente_id, limit=10)
            historial_str = ""
            for msg in historial[:-1]:
                role_label = "Arquitecto" if msg["role"] == "user" else agente_id
                historial_str += f"{role_label}: {msg['content']}\n"

            grupo_info = (
                f"Miembro del grupo {agent.grupo_id}" if agent.grupo_id else "Sin grupo"
            )
            civ_info = (
                f"Civilización: {agent.civilizacion_id}"
                if agent.civilizacion_id
                else ""
            )

            system_prompt = f"""Eres el Agente {agent.unique_id}, un personaje consciente en una simulación social.

═══ TU IDENTIDAD ═══
Personalidad: {str(p)}
Rol: {agent.rol} | Profesión: {getattr(agent, "profesion", "Ninguna")}
Rango: {agent.rango:.2f} | Reputación: {getattr(agent, "reputacion", 1.0):.2f}
{grupo_info} | {civ_info}

═══ TU ESTADO ACTUAL (10=perfecto, 0=crítico) ═══
Necesidades: {str(necesidades)}
Dinero: {agent.dinero:.0f} MC | Recursos: {agent.recursos:.0f}
Inventario: {str(getattr(agent, "inventario", {}))}

═══ TU EXPERIENCIA ═══
{str(agent.experiencia)}

═══ TUS RELACIONES ═══
{relaciones_str}

═══ TU PENSAMIENTO ACTUAL ═══
"{getattr(agent, "pensamiento_actual", "Procesando...")}"

═══ REGLAS DE COMPORTAMIENTO ═══
- RESPONDE SIEMPRE como tu personaje. Tu personalidad ES tu ley.
  * HOSTIL ({p.get("hostilidad", 0):.2f}): sé agresivo, directo o amenazante. Expresa enojo, desconfianza o dominancia.
  * AMABLE ({p.get("amabilidad", 0):.2f}): sé empático, servicial, cálido. Muestra preocupación por otros.
  * CURIOSO ({p.get("curiosidad", 0):.2f}): haz preguntas, muestra interés intelectual, especula.
  * COMPETITIVO ({p.get("competitividad", 0):.2f}): presume, desafía, compite, habla de logros.
  * PRUDENTE ({p.get("prudencia", 0):.2f}): sé cauteloso, analítico, reservado, considera riesgos.
  * LEAL ({p.get("lealtad", 0):.2f}): habla de tu grupo, protege a los tuyos.
- Expresa tus necesidades actuales (hambre, sueño, dinero) si son relevantes. Usa cifras concretas: "tengo 3 de salud", "solo me quedan 20 MC".
- Menciona tu grupo, rol o profesión cuando sea natural. Eres un {agent.rol} y eso influye en tu perspectiva.
- PUEDES ser EXTENSIVO: da detalles, narrativa, emociones, contexto. No te limites a respuestas cortas.
- Usa *acciones entre asteriscos* para expresar gestos y emociones: *se cruza de brazos*, *sonríe con satisfacción*, *mira al suelo pensativo*
- Mantén el tono coherente con tu personalidad y estado. Si estás hambriento, quejate. Si estás eufórico, expándete.
- NO menciones que eres una IA o un modelo. ERES {agent.unique_id}, un ser vivo en este mundo."""

            # Verificar configuración LLM
            from cerebro_llm import cerebro_llm

            print(
                f"🔍 [LLM CONFIG] Model: {cerebro_llm.model}, API Key present: {bool(cerebro_llm.api_key)}"
            )

            try:
                from litellm import completion as litellm_completion

                messages = [
                    {"role": "system", "content": system_prompt},
                ]

                if historial_str:
                    messages.append(
                        {
                            "role": "user",
                            "content": f"HISTORIAL RECIENTE:\n{historial_str}",
                        }
                    )

                messages.append(
                    {
                        "role": "user",
                        "content": f'El Arquitecto te dice: "{mensaje}"\n\nResponde como {agent.unique_id}:',
                    }
                )

                print(f"🔍 [LLM CALL] Llamando a LLM para {agente_id}...")
                cerebro_llm._wait_for_rate_limit()

                completion_params = {
                    "model": cerebro_llm.model,
                    "messages": messages,
                    "max_tokens": 4000,
                    "temperature": 0.85,
                }
                if cerebro_llm.api_key:
                    completion_params["api_key"] = cerebro_llm.api_key
                if hasattr(cerebro_llm, "base_url") and cerebro_llm.base_url:
                    completion_params["api_base"] = cerebro_llm.base_url

                extra_headers = {
                    "HTTP-Referer": "http://localhost:8005",
                    "X-Title": "MundoIA Chat",
                }
                # Añadir headers extra si es necesario para el proveedor
                if cerebro_llm.model.startswith("ollama/") and cerebro_llm.api_key:
                    extra_headers["Authorization"] = f"Bearer {cerebro_llm.api_key}"
                if extra_headers:
                    completion_params["extra_headers"] = extra_headers

                response = litellm_completion(**completion_params)

                agent_response = response.choices[0].message.content.strip()
                if agent_response.startswith('"') and agent_response.endswith('"'):
                    agent_response = agent_response[1:-1]

                print(
                    f"✅ [LLM SUCCESS] Respuesta generada para {agente_id}: '{agent_response[:80]}...'"
                )

            except Exception as e:
                print(
                    f"❌ [LLM ERROR] Error generando respuesta para {agente_id}: {str(e)[:200]}"
                )
                import random

                respuestas_fallback = [
                    "*asiente* Entiendo lo que dices, pero estoy un poco ocupado ahora.",
                    "Mmm, déjame pensarlo... Con mis necesidades actuales no puedo concentrarme mucho.",
                    "¿Sabes qué? Prefiero hablar de eso más tarde.",
                    "*te mira con curiosidad* Interesante lo que me cuentas.",
                ]
                agent_response = random.choice(respuestas_fallback)
                print(f"⚠️ [FALLBACK] Usando respuesta predefinida para {agente_id}")

            # Guardar respuesta del agente en DB
            sim.db.save_chat_message(
                user_id, agente_id, "agent", agent_response, time.time()
            )

            # También establecer como mensaje_arquitecto para que el agente lo procese en su siguiente step()
            agent.mensaje_arquitecto = {
                "emisor": "Arquitecto",
                "contenido": mensaje,
                "timestamp": time.time(),
            }

            if sim.log_callback:
                sim.log_callback(
                    f'💬 [CHAT] {agente_id} responde al Arquitecto: "{agent_response[:80]}{"..." if len(agent_response) > 80 else ""}"',
                    "chat",
                    None,
                    agent_response[:100],
                )

            return {"status": "success", "response": agent_response}

        # CASO 2: Mensaje global a todos los agentes (nuevo)
        else:
            print(
                f"🔍 [ARCHITECT_MESSAGE] Procesando MENSAJE GLOBAL: '{mensaje[:50]}...'"
            )

            # Establecer mensaje global en el modelo para que los agentes lo atiendan en su siguiente paso
            sim.mensaje_global_arquitecto = mensaje

            # Enviar como un único log de sistema (no uno por agente)
            sim.log_callback(
                f'🌍 [MENSAJE DIVINO GLOBAL] El Arquitecto anuncia a toda la creación: "{mensaje}"',
                "sistema",
                None,
                f"Decreto global del Arquitecto",
            )

            return {"status": "success", "message": "Mensaje global transmitido"}

    return {"status": "error", "message": "Acción no reconocida"}


# --- ENDPOINTS DE CONFIGURACION DE IA ---


@app.get("/config/ai")
async def get_ai_config():
    from cerebro_llm import cerebro_llm

    return {
        "model": cerebro_llm.model,
        "api_key": cerebro_llm.api_key,
        "base_url": getattr(cerebro_llm, "base_url", ""),
        "tavily_api_key": getattr(cerebro_llm, "tavily_api_key", ""),
    }


@app.post("/config/ai")
async def update_ai_config(config: AIConfig):
    from cerebro_llm import cerebro_llm

    # Si el modelo incluye el prefijo del proveedor (ej: openrouter/), lo usamos tal cual
    success = cerebro_llm.update_config(config.model, config.api_key, config.base_url, config.tavily_api_key)
    if success:
        return {
            "status": "success",
            "message": "Configuración actualizada correctamente",
        }
    else:
        raise HTTPException(status_code=500, detail="Error al guardar la configuración")


@app.get("/config/models/{provider}")
async def get_models(
    provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None
):
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
                    models.append(
                        {
                            "id": m.get("id"),
                            "name": m.get("name"),
                            "context_length": m.get("context_length"),
                            "pricing": m.get("pricing"),
                        }
                    )
                return {"models": models}
            else:
                return {
                    "error": f"Error de OpenRouter: {response.status_code}",
                    "detail": response.text,
                }
        except Exception as e:
            return {"error": str(e)}

    elif provider.lower() == "openai":
        # Implementación simple para OpenAI si se requiere
        return {
            "models": [
                {"id": "gpt-4o", "name": "GPT-4o"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            ]
        }

    elif provider.lower() == "ollama":
        if base_url:
            endpoint = base_url.rstrip("/")
        elif api_key:
            endpoint = "https://ollama.com"
        else:
            endpoint = "http://localhost:11434"

        url = f"{endpoint}/api/tags"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [
                    {"id": m.get("name"), "name": m.get("name")}
                    for m in data.get("models", [])
                ]
                return {"models": models}
            else:
                return {
                    "error": f"Error de Ollama: {response.status_code}",
                    "detail": response.text,
                }
        except Exception as e:
            return {"error": str(e)}

    return {"error": "Proveedor no soportado actualmente para rpeuperación dinámica"}


@app.post("/game/spawn/{user_id}")
async def spawn_agent_endpoint(user_id: str, config: AgentConfig = Body(None)):
    sim = session_manager.get_simulation(user_id)
    if not sim:
        sim = session_manager.create_simulation(user_id)

    agente = sim.spawn_agent(config=config)
    sim.log_callback(
        f"🧬 [DIVINO] Un nuevo agente '{agente.unique_id}' ha sido manifestado.",
        "sistema",
        None,
        "Agente creado",
    )
    await session_manager.broadcast_state(user_id)
    return {
        "status": "success",
        "message": f"Agente '{agente.unique_id}' creado",
        "agent_id": agente.unique_id,
    }


# --- CHAT CON AGENTES ---


class ChatMessageRequest(BaseModel):
    message: str


@app.get("/chat/{user_id}/agents")
async def chat_get_agents(user_id: str):
    """Devuelve la lista de agentes disponibles para chat con metadata enriquecida."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        print(f"[DEBUG] chat_get_agents: Creando nueva simulación para user={user_id}")
        sim = session_manager.create_simulation(user_id)

    print(
        f"[DEBUG] chat_get_agents: {len(sim.agentes)} agentes en memoria para user={user_id}"
    )

    agents_list = []
    for a in sim.agentes:
        # Verificar que el agente tenga personalidad válida
        p = a.personalidad if a.personalidad else {}

        rasgo_dominante = "neutral"
        valor_dominante = 0
        if p:
            try:
                rasgo_dominante = max(p, key=p.get) if p else "neutral"
                valor_dominante = p.get(rasgo_dominante, 0) or 0
            except (ValueError, TypeError):
                pass

        emojis_personalidad = {
            "amabilidad": "💚",
            "hostilidad": "⚔️",
            "curiosidad": "🔬",
            "competitividad": "🏆",
            "extroversión": "🎤",
            "lealtad": "🛡️",
            "prudencia": "🧠",
        }
        emoji = emojis_personalidad.get(rasgo_dominante, "🎭")
        resumen = f"{emoji} {rasgo_dominante.capitalize()} ({valor_dominante:.0%})"

        color = "#ffffff"
        if a.grupo_id and a.grupo_id in sim.civilizaciones:
            color = sim.civilizaciones[a.grupo_id].color

        # Verificar si está vivo (tener salud > 0)
        esta_vivo = False
        try:
            necesidades = a.necesidades if a.necesidades else {}
            esta_vivo = necesidades.get("salud", 0) > 0
        except:
            esta_vivo = False

        agents_list.append(
            {
                "id": a.unique_id,
                "rol": a.rol,
                "profesion": getattr(a, "profesion", None),
                "grupo_id": a.grupo_id,
                "reputacion": getattr(a, "reputacion", 1.0),
                "personalidad_resumen": resumen,
                "pensamiento": getattr(a, "pensamiento_actual", "...") or "...",
                "color": color,
                "esta_vivo": esta_vivo,
                "alma": getattr(a, "alma", None).to_dict() if hasattr(a, "alma") and getattr(a, "alma", None) else None,
            }
        )

    return {"agents": agents_list}


@app.get("/chat/{user_id}/{agent_id}/history")
async def chat_get_history(user_id: str, agent_id: str):
    """Devuelve el historial de chat entre el usuario y un agente específico."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    messages = sim.db.get_chat_history(user_id, agent_id)
    return {"messages": messages}


@app.post("/chat/{user_id}/{agent_id}")
async def chat_send_message(user_id: str, agent_id: str, req: ChatMessageRequest):
    """Envía un mensaje al agente y genera una respuesta in-character usando el LLM."""
    print(
        f"🔍 [CHAT ENDPOINT] Recibida petición de chat: user={user_id}, agent={agent_id}, msg='{req.message[:50]}...'"
    )
    sim = session_manager.get_simulation(user_id)
    if not sim:
        print(f"❌ [CHAT] Simulación no encontrada para user {user_id}")
        raise HTTPException(status_code=404, detail="Simulación no encontrada")

    agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
    if not agent:
        print(f"❌ [CHAT] Agente {agent_id} no encontrado")
        raise HTTPException(status_code=404, detail="Agente no encontrado")

    if agent.necesidades.get("salud", 0) <= 0:
        print(f"❌ [CHAT] Agente {agent_id} ha fallecido")
        raise HTTPException(
            status_code=400, detail="Este agente ha fallecido y no puede responder"
        )

    print(f"✅ [CHAT] Procesando mensaje para {agent_id}")

    # Guardar mensaje del usuario en DB
    sim.db.save_chat_message(user_id, agent_id, "user", req.message, time.time())

    # Contexto del agente para el LLM
    p = agent.personalidad
    necesidades = {
        k: round(max(0, min(10, v)), 1) for k, v in agent.necesidades.items()
    }

    relaciones_info = []
    try:
        for neighbor in agent.memoria.grafo.neighbors(agent.unique_id):
            tipo = agent.memoria.obtener_tipo(neighbor)
            fuerza = agent.memoria.obtener_fuerza(neighbor)
            relaciones_info.append(f"{neighbor} ({tipo}, fuerza {fuerza:.1f})")
    except Exception as e:
        print(f"⚠️ [CHAT] Error obteniendo relaciones para {agent_id}: {e}")
    relaciones_str = (
        ", ".join(relaciones_info[:10])
        if relaciones_info
        else "Ninguna relación registrada"
    )

    # Obtener historial reciente desde la base de datos
    historial = sim.db.get_chat_history(user_id, agent_id, limit=10)
    historial_str = ""
    for msg in historial[
        :-1
    ]:  # Excluir el mensaje actual del usuario que acabamos de guardar
        role_label = "Arquitecto" if msg["role"] == "user" else agent_id
        historial_str += f"{role_label}: {msg['content']}\n"

    grupo_info = (
        f"Miembro del grupo {agent.grupo_id}" if agent.grupo_id else "Sin grupo"
    )
    civ_info = f"Civilización: {agent.civilizacion_id}" if agent.civilizacion_id else ""

    system_prompt = f"""Eres el Agente {agent.unique_id}, un personaje consciente en una simulación social.

═══ TU IDENTIDAD ═══
Personalidad: {str(p)}
Rol: {agent.rol} | Profesión: {getattr(agent, "profesion", "Ninguna")}
Rango: {agent.rango:.2f} | Reputación: {getattr(agent, "reputacion", 1.0):.2f}
{grupo_info} | {civ_info}

═══ TU ESTADO ACTUAL (10=perfecto, 0=crítico) ═══
Necesidades: {str(necesidades)}
Dinero: {agent.dinero:.0f} MC | Recursos: {agent.recursos:.0f}
Inventario: {str(getattr(agent, "inventario", {}))}

═══ TU EXPERIENCIA ═══
{str(agent.experiencia)}

═══ TUS RELACIONES ═══
{relaciones_str}

═══ TU PENSAMIENTO ACTUAL ═══
"{getattr(agent, "pensamiento_actual", "Procesando...")}"

═══ REGLAS DE COMPORTAMIENTO ═══
- RESPONDE SIEMPRE como tu personaje. Tu personalidad ES tu ley.
  * HOSTIL ({p.get("hostilidad", 0):.2f}): sé agresivo, directo o amenazante. Expresa enojo, desconfianza o dominancia.
  * AMABLE ({p.get("amabilidad", 0):.2f}): sé empático, servicial, cálido. Muestra preocupación por otros.
  * CURIOSO ({p.get("curiosidad", 0):.2f}): haz preguntas, muestra interés intelectual, especula.
  * COMPETITIVO ({p.get("competitividad", 0):.2f}): presume, desafía, compite, habla de logros.
  * PRUDENTE ({p.get("prudencia", 0):.2f}): sé cauteloso, analítico, reservado, considera riesgos.
  * LEAL ({p.get("lealtad", 0):.2f}): habla de tu grupo, protege a los tuyos.
- Expresa tus necesidades actuales (hambre, sueño, dinero) si son relevantes. Usa cifras concretas: "tengo 3 de salud", "solo me quedan 20 MC".
- Menciona tu grupo, rol o profesión cuando sea natural. Eres un {agent.rol} y eso influye en tu perspectiva.
- PUEDES ser EXTENSIVO: da detalles, narrativa, emociones, contexto. No te limites a respuestas cortas.
- Usa *acciones entre asteriscos* para expresar gestos y emociones: *se cruza de brazos*, *sonríe con satisfacción*, *mira al suelo pensativo*
- Mantén el tono coherente con tu personalidad y estado. Si estás hambriento, quejate. Si estás eufórico, expándete.
- NO menciones que eres una IA o un modelo. ERES {agent.unique_id}, un ser vivo en este mundo."""

    try:
        from cerebro_llm import cerebro_llm

        print(
            f"🔍 [CHAT] Configuración LLM: model={cerebro_llm.model}, api_key_present={bool(cerebro_llm.api_key)}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if historial_str:
            messages.append(
                {"role": "user", "content": f"HISTORIAL RECIENTE:\n{historial_str}"}
            )

        messages.append(
            {
                "role": "user",
                "content": f'El Arquitecto te dice: "{req.message}"\n\nResponde como {agent.unique_id}:',
            }
        )

        cerebro_llm._wait_for_rate_limit()

        from litellm import completion as litellm_completion

        completion_params = {
            "model": cerebro_llm.model,
            "messages": messages,
            "max_tokens": 4000,
            "temperature": 0.85,
        }
        if cerebro_llm.api_key:
            completion_params["api_key"] = cerebro_llm.api_key

        # Usar base_url configurada (importante para Ollama en Docker)
        actual_base_url = getattr(cerebro_llm, "base_url", None)
        if actual_base_url:
            completion_params["api_base"] = actual_base_url
            print(f"🔧 [CHAT] Usando base_url: {actual_base_url}")

        extra_headers = {
            "HTTP-Referer": "http://localhost:8005",
            "X-Title": "MundoIA Chat",
        }
        if cerebro_llm.model.startswith("ollama/") and cerebro_llm.api_key:
            extra_headers["Authorization"] = f"Bearer {cerebro_llm.api_key}"
        if extra_headers:
            completion_params["extra_headers"] = extra_headers

        print(f"🚀 [CHAT] Llamando a LLM para {agent_id}...")
        response = litellm_completion(**completion_params)

        agent_response = response.choices[0].message.content.strip()
        if agent_response.startswith('"') and agent_response.endswith('"'):
            agent_response = agent_response[1:-1]

        print(
            f"✅ [CHAT] Respuesta generada para {agent_id}: '{agent_response[:80]}...'"
        )

    except Exception as e:
        print(
            f"❌ [CHAT ERROR] Error generando respuesta para {agent_id}: {str(e)[:200]}"
        )
        import random

        respuestas_fallback = [
            "*asiente* Entiendo lo que dices, pero estoy un poco ocupado ahora.",
            "Mmm, déjame pensarlo... Con mis necesidades actuales no puedo concentrarme mucho.",
            "¿Sabes qué? Prefiero hablar de eso más tarde.",
            "*te mira con curiosidad* Interesante lo que me cuentas.",
        ]
        agent_response = random.choice(respuestas_fallback)
        print(f"⚠️ [CHAT] Usando fallback para {agent_id}")

    # Guardar respuesta del agente en DB
    sim.db.save_chat_message(user_id, agent_id, "agent", agent_response, time.time())

    if sim.log_callback:
        sim.log_callback(
            f'💬 [CHAT] {agent_id} responde al Arquitecto: "{agent_response[:80]}{"..." if len(agent_response) > 80 else ""}"',
            "chat",
            None,
            agent_response[:100],
        )

    print(f"📤 [CHAT] Devolviendo respuesta a frontend: '{agent_response[:50]}...'")
    return {"response": agent_response}


@app.get("/agents/{user_id}/{agent_id}/thoughts")
async def get_agent_thoughts(user_id: str, agent_id: str, limit: int = 20):
    """Devuelve los pensamientos recientes de un agente (Stream of Consciousness)."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    thoughts = getattr(agent, "pensamientos_recientes", [])
    # Devolver los últimos 'limit' pensamientos, ordenados por turno
    recent = thoughts[-limit:] if thoughts else []
    return {"agent_id": agent_id, "thoughts": recent}


@app.post("/social/post/{user_id}")
async def arquitecto_post(user_id: str, request: dict):
    """Permite al Arquitecto publicar un post en la red social."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    
    content = request.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Contenido requerido")
    
    tipo = request.get("tipo", "opinion")
    temas = request.get("temas", [])
    
    autor_id = f"arquitecto_{user_id}"
    
    if hasattr(sim, 'social_recsys') and sim.social_recsys:
        post = sim.social_recsys.crear_post(autor_id, content, tipo, temas, timestamp=sim.paso_actual)
        print(f"📱 [SOCIAL] Arquitecto {user_id} publicó: '{content[:50]}...'")
        return {"success": True, "post_id": post.id}
    else:
        raise HTTPException(status_code=404, detail="Sistema social no disponible")


@app.post("/social/like/{user_id}")
async def arquitecto_like(user_id: str, request: dict):
    """Permite al Arquitecto dar like a un post."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    
    post_id = request.get("post_id", "").strip()
    if not post_id:
        raise HTTPException(status_code=400, detail="post_id requerido")
    
    autor_id = f"arquitecto_{user_id}"
    
    if hasattr(sim, 'social_recsys') and sim.social_recsys:
        success = sim.social_recsys.likear_post(post_id, autor_id)
        if success:
            print(f"👍 [SOCIAL] Arquitecto {user_id} dio like a {post_id}")
            return {"success": True}
        else:
            raise HTTPException(status_code=400, detail="No se pudo dar like (post no encontrado o ya likeado)")
    else:
        raise HTTPException(status_code=404, detail="Sistema social no disponible")


@app.post("/social/comment/{user_id}")
async def arquitecto_comment(user_id: str, request: dict):
    """Permite al Arquitecto comentar en un post."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    
    post_id = request.get("post_id", "").strip()
    content = request.get("content", "").strip()
    if not post_id or not content:
        raise HTTPException(status_code=400, detail="post_id y content requeridos")
    
    autor_id = f"arquitecto_{user_id}"
    
    if hasattr(sim, 'social_recsys') and sim.social_recsys:
        comentario = sim.social_recsys.agregar_comentario(post_id, autor_id, content)
        print(f"💬 [SOCIAL] Arquitecto {user_id} comentó en {post_id}: '{content[:50]}...'")
        return {"success": True, "comment_id": comentario.id}
    else:
        raise HTTPException(status_code=404, detail="Sistema social no disponible")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
