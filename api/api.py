import os
import json
import asyncio
import threading
import requests
import random
import time
from contextlib import asynccontextmanager as _asynccontextmanager
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
from core.modelo import ModeloRelacional
from core.database import DatabaseManager
from core.utils import DateTimeEncoder
from agents.agent_utils import resolve_agent_unique_id, display_name_for
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

# Async null context manager (fallback when no lock is available)
class _nullcontext:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


# --- GESTOR DE SESIONES ---


class SessionManager:
    def __init__(self):
        # user_id (game_id) -> { conn_id: WebSocket }
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # user_id (game_id) -> { conn_id: {"player_id": str, "username": str, "connected_at": float} }
        self.room_players: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.simulations: Dict[
            str, ModeloRelacional
        ] = {}  # user_id -> ModeloRelacional
        self.simulation_threads: Dict[str, bool] = {}  # user_id -> is_running
        self.simulation_thread_refs: Dict[
            str, threading.Thread
        ] = {}  # user_id -> thread reference
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.queue_processor_started = False
        self.last_broadcast_time: Dict[str, float] = {}
        self.last_stats: Dict[str, dict] = {}
        self.last_agents: Dict[str, dict] = {}
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._write_locks: Dict[str, asyncio.Lock] = {}  # per-room write lock

    async def connect(
        self,
        user_id: str,
        websocket: WebSocket,
        player_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> str:
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        if user_id not in self.room_players:
            self.room_players[user_id] = {}
        if user_id not in self._write_locks:
            self._write_locks[user_id] = asyncio.Lock()

        eff_player_id = player_id or user_id
        eff_username = username or eff_player_id[:12]
        conn_id = f"{eff_player_id}_{id(websocket)}"

        self.active_connections[user_id][conn_id] = websocket
        self.room_players[user_id][conn_id] = {
            "player_id": eff_player_id,
            "username": eff_username,
            "connected_at": time.time(),
        }
        print(f"🔌 Cliente conectado a sala {user_id}: {eff_username} ({eff_player_id})")
        return conn_id

    def disconnect(self, user_id: str, websocket: WebSocket):
        conns = self.active_connections.get(user_id)
        if not conns:
            return
        to_remove = [cid for cid, ws in conns.items() if ws == websocket]
        for cid in to_remove:
            conns.pop(cid, None)
            if user_id in self.room_players:
                self.room_players[user_id].pop(cid, None)
        if not conns:
            self.active_connections.pop(user_id, None)
            self.room_players.pop(user_id, None)
        print(f"🔌 Cliente desconectado de sala: {user_id}")

    def get_connected_players(self, user_id: str) -> list:
        sim = self.simulations.get(user_id)
        agentes_poseidos = getattr(sim, "agentes_poseidos", {}) if sim else {}
        players_by_id: Dict[str, Dict[str, Any]] = {}
        for info in self.room_players.get(user_id, {}).values():
            pid = info["player_id"]
            possessed_id = agentes_poseidos.get(pid)
            players_by_id[pid] = {
                "player_id": pid,
                "username": info["username"],
                "possessed_agent_id": possessed_id,
                "possessed_agent_name": display_name_for(sim, possessed_id) if (sim and possessed_id) else None,
            }
        return list(players_by_id.values())

    def enqueue_message(self, user_id: str, message: dict):
        if self.main_loop:
            self.main_loop.call_soon_threadsafe(
                self.message_queue.put_nowait, (user_id, message)
            )

    async def send_to_user(self, user_id: str, message: dict):
        lock = self._write_locks.get(user_id)
        async with lock if lock else _nullcontext():
            conns = list(self.active_connections.get(user_id, {}).items())
            if not conns:
                return
            payload = json.dumps(message, cls=DateTimeEncoder)
            dead_sockets = []
            for _cid, websocket in conns:
                try:
                    await websocket.send_text(payload)
                except Exception as e:
                    print(f"❌ Error enviando mensaje a {user_id}: {e}")
                    dead_sockets.append(websocket)
            for ws in dead_sockets:
                self.disconnect(user_id, ws)

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
                # Si no hay simulación activa para este usuario o ya fue detenida, no enviar logs
                if not sim or getattr(sim, "_stopped", False):
                    return
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
                            # Indica explícitamente que este mensaje es un log, no un post social
                            "is_social_post": False,
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
                # Evitar procesar eventos si no hay simulación activa o ya fue detenida/reset
                if not sim or getattr(sim, "_stopped", False):
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
            # Si la simulación se crea como vacía, asegurarse de que el SocialRecSys
            # no contenga posts de partidas anteriores en memoria.
            if start_empty:
                sim = self.simulations[user_id]
                if hasattr(sim, 'social_recsys') and sim.social_recsys:
                    try:
                        sim.social_recsys.interest_recsys.posts = {}
                        sim.social_recsys.interest_recsys.comentarios = {}
                        sim.social_recsys.seguidos = {}
                    except Exception:
                        pass
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
                            coro = self.broadcast_state(user_id, include_logs=True)
                            asyncio.run_coroutine_threadsafe(coro, loop)
                    except Exception as e:
                        print(f"[RUN_LOOP] Error en broadcast: {e}")

                    # Pausa mínima entre pasos para que sea observable a escala humana
                    # Si ritmo es 0.1 y hay 10 agentes, el paso ya tarda ~1s.
                    # Añadimos un pequeño extra para la transición visual.
                    time.sleep(max(0.2, current_sim.ritmo * 2))
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

    async def stop_simulation_loop(self, user_id: str):
        self.simulation_threads[user_id] = False
        if user_id in self.simulations and hasattr(
            self.simulations[user_id], "_force_stop"
        ):
            self.simulations[user_id]._force_stop = True
            self.simulations[user_id]._stopped = True
        # Esperar a que el hilo de simulación termine completamente sin bloquear el event loop
        thread = self.simulation_thread_refs.pop(user_id, None)
        if thread and thread.is_alive():
            print(f"⏳ Esperando a que el hilo de simulación termine para {user_id}...")
            import anyio
            try:
                # Usar un hilo separado para hacer join
                await anyio.to_thread.run_sync(thread.join, 15.0)
                if thread.is_alive():
                    print(f"⚠️ El hilo de simulación para {user_id} no terminó en 15s, continuando de todas formas")
            except Exception as e:
                print(f"Error esperando hilo: {e}")
        print(f"⏸️ Simulación detenida para {user_id}")

    async def broadcast_state(
        self, user_id, include_logs=False, include_map=False, return_payload=False, force=False
    ):
        sim = self.simulations.get(user_id)
        if not sim:
            return

        map_was_dirty = bool(getattr(sim, "_map_dirty", False))
        if map_was_dirty:
            include_map = True

        is_first = user_id not in self.last_stats

        # Throttle: no enviar más de una vez por 500ms, a menos que se fuerce
        now = time.time()
        last_time = self.last_broadcast_time.get(user_id, 0)
        if not force and now - last_time < 0.5 and not (include_map or include_logs or is_first):
            return  # Skip this broadcast
        self.last_broadcast_time[user_id] = now

        # Determinar si enviamos delta o completo (enviar completo cada 50 pasos para sincronización)
        force_full = (
            include_map or is_first or include_logs or force or (sim.paso_actual % 50 == 0)
        )

        # Si es la primera vez, forzar la inclusión del mapa si no viene marcada
        effective_include_map = include_map or is_first

        # Determinar el límite de logs a enviar: 1000 para sincronización inicial, 20 para actualizaciones
        log_limit = 1000 if is_first else 20
        
        # Construir el payload completo de estadísticas usando el método auxiliar
        current_stats = self._build_stats_payload(
            sim, user_id, include_logs, effective_include_map, log_limit=log_limit
        )

        if is_first or force_full:
            await self.send_to_user(user_id, {**current_stats, "type": "stats"})
            self.last_stats[user_id] = current_stats
            if map_was_dirty and hasattr(sim, "_map_dirty"):
                sim._map_dirty = False
        else:
            delta = self.get_delta(self.last_stats.get(user_id, {}), current_stats)
            if delta:
                # Asegurar que `socialFeed` se incluya en el delta cuando haya
                # cambios relevantes. Antes solo se incluía si la longitud
                # cambiaba; esto perdía actualizaciones de likes/comentarios
                # o reemplazos en el top-N cuando la longitud permanecía.
                if "socialFeed" in current_stats:
                    try:
                        old_sf = self.last_stats.get(user_id, {}).get("socialFeed", [])
                        new_sf = current_stats.get("socialFeed", [])

                        include_sf = False

                        # Si no teníamos socialFeed previamente, incluirlo
                        if "socialFeed" not in self.last_stats.get(user_id, {}):
                            include_sf = True
                        else:
                            # Comparar listas de IDs para detectar posts nuevos/retirados
                            old_ids = [p.get("id") for p in old_sf]
                            new_ids = [p.get("id") for p in new_sf]
                            if old_ids != new_ids:
                                include_sf = True
                            else:
                                # Mismo conjunto de IDs: comprobar cambios en métricas
                                for new_p in new_sf:
                                    match = next((p for p in old_sf if p.get("id") == new_p.get("id")), None)
                                    if match and (
                                        match.get("likes") != new_p.get("likes")
                                        or match.get("comentarios") != new_p.get("comentarios")
                                        or match.get("likes_por") != new_p.get("likes_por")
                                    ):
                                        include_sf = True
                                        break

                        if include_sf:
                            delta["socialFeed"] = new_sf
                        # Si se detectó un cambio en un post mediante la comparación de IDs o métricas,
                        # y ese post tenía comentarios o likes modificados, asegurar que socialFeed
                        # se envíe completo para que el frontend reciba los comentarios_detalle
                    except Exception:
                        # En caso de fallo inesperado, enviar la versión completa
                        delta["socialFeed"] = current_stats.get("socialFeed", [])

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

        # Agentes: mantener `id` como unique_id (interno) y exponer `identidad`/nombre para la UI
        current_agents = {}
        for a in sim.agentes:
            display_name = display_name_for(sim, a.unique_id)
            current_agents[a.unique_id] = {
                "id": a.unique_id,
                "x": a.x,
                "y": a.y,
                "civilizacion_id": a.civilizacion_id,
                "resources": a.recursos,
                "money": a.dinero,
                "grupo_id": a.grupo_id,
                "rol": a.rol,
                # Mostrar 'Historiador' sólo si el agente coincide con historia.historiador_id
                "profesion": (
                    "Historiador"
                    if hasattr(sim, "historia") and getattr(sim.historia, "historiador_id", None) == a.unique_id
                    else getattr(a, "profesion", None)
                ),
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
                "is_possessed": bool(
                    a.unique_id == getattr(sim, "agente_poseido_id", None)
                    or a.unique_id in (getattr(sim, "agentes_poseidos", {}) or {}).values()
                ),
                "possessed_by": next(
                    (
                        pid
                        for pid, aid in (getattr(sim, "agentes_poseidos", {}) or {}).items()
                        if aid == a.unique_id
                    ),
                    None,
                ),
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
        force_full_agents = is_first or include_map or force

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

        # Relaciones: enviar IDs internos y nombres auxiliares para UI
        if force_full or sim.paso_actual % 5 == 0:
            relationships = []
            for a in sim.agentes:
                for neighbor in a.memoria.grafo.neighbors(a.unique_id):
                    relationships.append(
                        {
                            "source": a.unique_id,
                            "target": neighbor,
                            "source_name": display_name_for(sim, a.unique_id),
                            "target_name": display_name_for(sim, neighbor),
                            "type": a.memoria.obtener_tipo(neighbor),
                            "strength": a.memoria.obtener_fuerza(neighbor),
                        }
                    )
            await self.send_to_user(user_id, {"type": "relationships", "data": relationships})

    def _build_stats_payload(self, sim, user_id, include_logs, include_map, log_limit=10):
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
                # Normalizar contadores de votos para que la UI pueda leerlos
                if isinstance(ley_copy.get("votos"), dict):
                    ley_copy["votos_si"] = ley_copy.get("votos_si", ley_copy["votos"].get("si", 0))
                    ley_copy["votos_no"] = ley_copy.get("votos_no", ley_copy["votos"].get("no", 0))
                todas_propuestas.append(ley_copy)

        for asamblea in sim.asambleas_globales:
            # Si la asamblea está asociada a una ley (ley_id), fusionarla con la propuesta
            ley_id = asamblea.get("ley_id")
            if ley_id:
                existing = next((p for p in todas_propuestas if p.get("id") == ley_id), None)
                if existing:
                    # Adjuntar info de asamblea dentro de la propuesta para evitar duplicados en UI
                    existing["asamblea"] = {
                        "id": asamblea.get("id"),
                        "tema": asamblea.get("tema"),
                        "descripcion": asamblea.get("descripcion"),
                        "estado": asamblea.get("estado"),
                        "votos_si": asamblea.get("votos_si", 0),
                        "votos_no": asamblea.get("votos_no", 0),
                        "participantes_votos": asamblea.get("participantes_votos", {}),
                    }
                    # Actualizar contadores principales si no existen o sumar los disponibles
                    existing["votos_si"] = max(existing.get("votos_si", 0), asamblea.get("votos_si", 0))
                    existing["votos_no"] = max(existing.get("votos_no", 0), asamblea.get("votos_no", 0))
                    # Mantener referencia al grupo
                    if asamblea.get("grupo_id"):
                        existing["grupo_id"] = asamblea.get("grupo_id")
                else:
                    # No hay propuesta ligada; exponer la asamblea como propuesta independiente
                    todas_propuestas.append(
                        {
                            "id": asamblea["id"],
                            "proponente_id": asamblea.get("proponente_id"),
                            "texto": asamblea.get("tema"),
                            "tipo": "asamblea",
                            "estado": asamblea.get("estado"),
                            "votos_si": asamblea.get("votos_si", 0),
                            "votos_no": asamblea.get("votos_no", 0),
                        }
                    )
            else:
                # Fallback: exponer como entrada independiente si no tiene ley_id
                todas_propuestas.append(
                    {
                        "id": asamblea["id"],
                        "proponente_id": asamblea.get("proponente_id"),
                        "texto": asamblea.get("tema"),
                        "tipo": "asamblea",
                        "estado": asamblea.get("estado"),
                        "votos_si": asamblea.get("votos_si", 0),
                        "votos_no": asamblea.get("votos_no", 0),
                    }
                )

        # Preparar lista de posts y aplicar un límite configurable via env `SOCIAL_FEED_LIMIT` (0 = ilimitado)
        posts_source = (
            sim.social_recsys.interest_recsys.posts.values()
            if hasattr(sim, "social_recsys") and sim.social_recsys
            else []
        )
        sorted_posts = sorted(posts_source, key=lambda x: x.timestamp, reverse=True)
        try:
            social_limit = int(os.getenv("SOCIAL_FEED_LIMIT", "0"))
        except Exception:
            social_limit = 0
        if social_limit and social_limit > 0:
            sorted_posts = sorted_posts[:social_limit]

        # Usar helper `display_name_for(sim, id)` para mapear ids a nombres públicos

        # Deduplicar propuestas por `id` para evitar tarjetas repetidas en la UI
        unique_by_id = {}
        for p in todas_propuestas:
            pid = p.get("id") or p.get("db_id") or None
            if pid is None:
                pid = p.get("titulo") or p.get("texto") or str(hash(json.dumps(p, sort_keys=True, cls=DateTimeEncoder)))

            if pid in unique_by_id:
                existing = unique_by_id[pid]
                # Preferir un `grupo_id` más específico que el genérico 'propuestas'
                if existing.get("grupo_id") == "propuestas" and p.get("grupo_id") and p.get("grupo_id") != "propuestas":
                    existing["grupo_id"] = p.get("grupo_id")

                # Fusionar contadores numéricos de votos por seguridad (tomar el máximo)
                existing["votos_si"] = max(existing.get("votos_si", 0), p.get("votos_si", 0))
                existing["votos_no"] = max(existing.get("votos_no", 0), p.get("votos_no", 0))

                # Fusionar estructuras de votos si existen (mapas de votantes)
                if isinstance(existing.get("votos"), dict) or isinstance(p.get("votos"), dict):
                    ev = existing.get("votos") or {}
                    pv = p.get("votos") or {}
                    merged_v = {**ev, **pv}
                    existing["votos"] = merged_v

                # Fusionar sub-objeto `asamblea` (si existe)
                if "asamblea" in p:
                    if "asamblea" not in existing:
                        existing["asamblea"] = p["asamblea"]
                    else:
                        ae = existing["asamblea"]
                        ap = p["asamblea"]
                        ae["votos_si"] = max(ae.get("votos_si", 0), ap.get("votos_si", 0))
                        ae["votos_no"] = max(ae.get("votos_no", 0), ap.get("votos_no", 0))
                        pv_e = ae.get("participantes_votos", {}) or {}
                        pv_p = ap.get("participantes_votos", {}) or {}
                        pv_e.update(pv_p)
                        ae["participantes_votos"] = pv_e

                # Rellenar campos faltantes simples
                for k, v in p.items():
                    if k not in existing or existing.get(k) in (None, "", []):
                        existing[k] = v
            else:
                unique_by_id[pid] = p.copy()

        todas_propuestas = list(unique_by_id.values())

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
            "logs": (sim.historial_logs[-log_limit:] if include_logs else []),
            "agente_poseido_id": getattr(sim, "agente_poseido_id", None),
            "agente_poseido": display_name_for(sim, getattr(sim, "agente_poseido_id", None)),
            "agentes_poseidos": getattr(sim, "agentes_poseidos", {}),
            "connected_players": self.get_connected_players(user_id),
            "modo_control_total": getattr(sim, "modo_control_total", False),
            "socialFeed": [
                {
                    "id": p.id,
                    "autor_id": p.autor_id,
                    "autor": display_name_for(sim, p.autor_id),
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
                            "autor": display_name_for(sim, c["autor_id"]),
                            "contenido": c["contenido"],
                            "timestamp": c["timestamp"],
                        }
                        for c in (
                            # Priority: post.comentarios_detalle (actualizado directamente)
                            getattr(p, "comentarios_detalle", []) or
                            # Fallback: interest_recsys.comentarios
                            (sim.social_recsys.interest_recsys.comentarios.get(p.id, []) 
                             if hasattr(sim, "social_recsys") and sim.social_recsys 
                             else [])
                        )
                    ],
                    "timestamp": p.timestamp,
                    "timestamp": p.timestamp,
                    # Identificador de la partida (usuario) al que pertenece este post
                    "partida_id": sim.user_id,
                }
                for p in sorted_posts
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
    user_id: str
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

class AgentConfig(BaseModel):
    name: Optional[str] = None
    personality: Optional[Dict[str, float]] = None
    resources: Optional[float] = 0.0
    money: Optional[float] = 100.0
    position: Optional[Dict[str, int]] = None  # {"x": 10, "y": 10}

class ChatMessageRequest(BaseModel):
    message: str

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
    if not sim and req.action != "reset":
        sim = session_manager.create_simulation(req.user_id)
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
        await session_manager.stop_simulation_loop(req.user_id)
        return {"status": "success"}
    elif req.action == "step":
        if sim:
            sim.step()
            await session_manager.broadcast_state(req.user_id)
            return {"status": "success"}
    elif req.action == "reset":
        # 1. Detener el bucle actual
        await session_manager.stop_simulation_loop(req.user_id)
        
        # 2. Eliminar rastro de la simulación anterior
        session_manager.simulations.pop(req.user_id, None)
        session_manager.last_stats.pop(req.user_id, None)
        session_manager.last_agents.pop(req.user_id, None)
        
        # 3. Crear una nueva simulación vacía
        sim = session_manager.create_simulation(req.user_id, start_empty=True)
        
        # 4. Forzar guardado del estado vacío en DB para limpiar la partida anterior
        if sim.db_active:
            try:
                if hasattr(sim, "db") and sim.db:
                    sim.db.clear_database(req.user_id)
                sim.guardar_estado()
                print(f"🧹 [RESET] Base de Datos limpiada para {req.user_id}")
            except Exception as e:
                print(f"⚠️ [RESET] Error limpiando DB: {e}")
        
        # 5. Notificar al frontend el nuevo estado vacío
        await session_manager.broadcast_state(req.user_id, include_map=True, include_logs=True)
        
        return {"status": "success", "message": "Nueva realidad generada y persistida"}
    return {"status": "error"}

@app.post("/game/speed")
async def set_game_speed(req: SpeedControl):
    sim = session_manager.get_simulation(req.user_id)
    if not sim:
        sim = session_manager.create_simulation(req.user_id)
    
    sim.ritmo = req.ritmo
    print(f"⏱️ [SPEED] Nuevo ritmo para {req.user_id}: {req.ritmo}s entre agentes")
    return {"status": "success", "ritmo": req.ritmo}

class GodAction(BaseModel):
    action_type: str
    params: Dict[str, Any]

@app.post("/game/god-mode/{user_id:path}")
async def god_mode(user_id: str, req: dict = Body(...)):
    action_type = req.get("action_type") or req.get("action")
    params = req.get("params", {})

    if action_type == "reset":
        await session_manager.stop_simulation_loop(user_id)
        session_manager.simulations.pop(user_id, None)
        session_manager.last_stats.pop(user_id, None)
        session_manager.last_agents.pop(user_id, None)
        sim = session_manager.create_simulation(user_id, start_empty=True)
        if req.get("modo_control_total") is not None:
            sim.modo_control_total = bool(req.get("modo_control_total"))
        if sim.db_active:
            try:
                if hasattr(sim, "db") and sim.db:
                    sim.db.clear_database(user_id)
                sim.guardar_estado()
            except Exception as e:
                print(f"⚠️ [RESET] Error limpiando DB: {e}")
        await session_manager.broadcast_state(user_id, include_map=True, include_logs=True)
        return {"status": "success", "message": "Nueva realidad generada y persistida"}

    sim = session_manager.get_simulation(user_id)
    if not sim: sim = session_manager.create_simulation(user_id)

    player_id = req.get("player_id") or params.get("player_id") or user_id
    player_username = req.get("username") or params.get("username") or "ARQUITECTO"
    if not hasattr(sim, "agentes_poseidos") or sim.agentes_poseidos is None:
        sim.agentes_poseidos = {}

    if action_type == "POSSESS_AGENT":
        agent_id = params.get("agent_id")
        if not agent_id:
            # Liberar posesión del jugador actual
            released_id = sim.agentes_poseidos.pop(player_id, None)
            if sim.agente_poseido_id == released_id or not sim.agentes_poseidos:
                sim.agente_poseido_id = next(iter(sim.agentes_poseidos.values()), None)
            sim.log(f"👻 [POSESIÓN] {player_username} ha liberado el enlace mental.", categoria="sistema")
            await session_manager.broadcast_state(user_id, force=True)
            return {
                "status": "success",
                "agente_poseido": None,
                "agente_poseido_id": None,
                "agentes_poseidos": sim.agentes_poseidos,
            }

        # Resolver si se pasó un nombre en lugar del unique_id
        resolved = resolve_agent_unique_id(sim, agent_id)
        if not resolved:
            return {"status": "error", "message": f"Agente no encontrado: {agent_id}"}

        # Verificar si otro jugador ya está poseyendo a este agente
        existing_owner = next(
            (pid for pid, aid in sim.agentes_poseidos.items() if aid == resolved and pid != player_id),
            None,
        )
        if existing_owner:
            return {
                "status": "error",
                "message": f"El agente {resolved} ya está siendo poseído por otro jugador en la sala.",
            }

        sim.agentes_poseidos[player_id] = resolved
        sim.agente_poseido_id = resolved
        nombre_poseido = next((a.identidad.nombre for a in sim.agentes if a.unique_id == resolved and getattr(a, "identidad", None)), resolved)
        sim.log(f"👻 [POSESIÓN] {player_username} ha enlazado su consciencia con {nombre_poseido}.", categoria="sistema")
        print(f"👻 [GOD MODE] {player_username} ({player_id}) poseyendo agente: {resolved} ({nombre_poseido}) en sala {user_id}")
        # Forzar difusión inmediata para que la UI se actualice
        await session_manager.broadcast_state(user_id, force=True)
        return {
            "status": "success",
            "agente_poseido": nombre_poseido,
            "agente_poseido_id": resolved,
            "agentes_poseidos": sim.agentes_poseidos,
        }

    elif action_type == "SPAWN_AGENT":
        count = params.get("count", 1)
        role = params.get("role")
        for _ in range(count):
            # spawn_agent expects a config dict — pass role inside it
            cfg = {} if not role else {"rol": role}
            sim.spawn_agent(cfg)

        # Si aún no hay historiador asignado, asignar uno
        if not sim.historia.historiador_id and sim.agentes:
            sim.historia.asignar_historiador(sim.agentes)
            print(f"📜 [HISTORIADOR] {sim.historia.historiador_id} ha sido asignado como Historiador del mundo")

        # Forzar envío completo tras spawn para evitar condiciones de throttle
        # que podrían impedir que el frontend reciba los nuevos agentes.
        await session_manager.broadcast_state(user_id, include_map=True)
        return {"status": "success", "message": f"{count} agentes invocados"}

    elif action_type == "ARCHITECT_MESSAGE":
        mensaje = params.get("mensaje")
        agent_id = params.get("agent_id")
        
        # Si no se especifica agente, elegir uno aleatorio o el poseído por este jugador
        agent = None
        player_possessed = sim.agentes_poseidos.get(player_id) or getattr(sim, "agente_poseido_id", None)
        if agent_id:
            # Resolver si se pasó nombre o id
            resolved = resolve_agent_unique_id(sim, agent_id)
            agent = next((a for a in sim.agentes if a.unique_id == resolved), None) if resolved else None
        elif player_possessed:
            agent = next((a for a in sim.agentes if a.unique_id == player_possessed), None)
            
        if not agent and sim.agentes:
            agent = random.choice(sim.agentes)
            
        if not agent:
            raise HTTPException(status_code=404, detail="No hay agentes disponibles para responder")
            
        # El arquitecto le habla al agente (broadcast global o individual)
        arch_tag = f"ARQUITECTO {player_username}" if player_username and player_username != "ARQUITECTO" else "ARQUITECTO"
        is_global = agent_id is None
        if is_global:
            sim.log(f"👤 [{arch_tag}] -> [TODOS]: {mensaje}", categoria="dialogo")
        else:
            sim.log(f"👤 [{arch_tag}] -> [{agent.unique_id}]: {mensaje}", categoria="dialogo")
        # Si es un mensaje global, entregarlo explícitamente a todos los agentes
        # para que lo registren en su memoria y lo procesen en su turno.
        if is_global:
            packet = {"emisor": arch_tag, "contenido": mensaje, "tipo": "GLOBAL"}
            for a in sim.agentes:
                try:
                    a.ultimo_mensaje_recibido = packet
                    a.memoria.registrar_mensaje(arch_tag, mensaje)
                except Exception:
                    # No permitir que una memoria falle rompa el flujo
                    continue
        
        # Ejecutar LLM con timeout de 15s para evitar bloqueo
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
        from agents.cerebro_llm import cerebro_llm

        def _llm_call():
            return cerebro_llm.responder_directamente(
                agent, mensaje, rol_interlocutor="El Arquitecto (tu creador)"
            )

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_llm_call)
                res, pensamiento = future.result(timeout=15.0)
        except FuturesTimeoutError:
            res, pensamiento = "...", "El agente tardó demasiado en responder."
        except Exception:
            res, pensamiento = "...", "Error en el procesamiento."
        
        if res and res != "...":
            agent.decir(res, pensamiento=pensamiento)
            return {"status": "success", "response": res}
        
        return {"status": "success", "response": "..."}

    elif action_type == "AGENT_EXECUTE_ACTION":
        agent_id = params.get("agent_id")
        action = params.get("action")
        payload = params.get("payload", {})
        
        agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
        if not agent: raise HTTPException(status_code=404, detail="Agent not found")
        
        user_action = {"tipo": action.lower(), "parametros": payload}
        
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

        # Modo autónomo / fallback: ejecución directa garantizada como Decreto Divino
        agent._ejecutando_decreto = True
        try:
            # 1. Generar narrativa rápida (opcional, no debe impedir la ejecución física)
            decision = None
            if hasattr(sim, "cerebro_llm") and sim.cerebro_llm:
                try:
                    decision = sim.cerebro_llm.generar_pensamiento_para_accion_forzada(agent, None, contexto, user_action)
                except Exception:
                    pass
            
            if decision:
                if decision.get("pensamiento"): agent.pensamiento_actual = decision["pensamiento"]
                if decision.get("mensaje"): agent.decir(decision["mensaje"], pensamiento=decision.get("pensamiento"))
            else:
                agent.decir(f"Ejecutando orden del Arquitecto: {action}", pensamiento="Es mi destino.")

            # 2. EJECUCIÓN FÍSICA REAL E INMEDIATA
            # Usamos user_action directamente para evitar que el LLM cambie la intención
            exito = agent.ejecutar_accion_final(user_action)
            
            if not exito:
                # Si falló, intentar con el nombre de la acción en el diccionario
                exito = agent.ejecutar_accion_final({"tipo": action, "parametros": payload})
            
            await session_manager.broadcast_state(user_id)
            return {"status": "success", "executed": exito}
        finally:
            agent._ejecutando_decreto = False

    elif action_type == "UPDATE_LORE":
        lore = params.get("lore", "")
        sim.lore = lore
        sim.log(f"📖 [ARQUITECTO] ha reescrito el Lore: {lore[:100]}...", categoria="sistema")
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif action_type == "SET_WEATHER":
        weather = params.get("weather", "sunny")
        sim.clima = weather
        sim.log(f"🌤️ [ARQUITECTO] ha cambiado el clima a: {weather}", categoria="sistema")
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif action_type == "TRIGGER_EVENT":
        event = params.get("event")
        sim.log(f"⚡ [ARQUITECTO] ha desatado un evento: {event}", categoria="sistema")
        if event == "plague":
            for agent in sim.agentes:
                if random.random() < 0.3:
                    agent.salud = max(0, agent.salud - 30)
                    sim.log(f"🤢 {agent.unique_id} ha contraído la plaga", categoria="sistema")
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif action_type == "CREATE_MISSION":
        title = params.get("title")
        description = params.get("description")
        sim.crear_mision(title, description, global_mission=True)
        sim.log(f"📜 [ARQUITECTO] ha decretado una nueva misión: {title}", categoria="sistema")
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif action_type == "MODIFY_ECONOMY":
        sub_action = params.get("sub_action")
        amount = params.get("amount", 0)
        if sub_action == "inject_money":
            # Actualizar el saldo global dentro de la estructura de economía
            if hasattr(sim, "economia"):
                sim.economia["total_dinero"] = sim.economia.get("total_dinero", 0) + amount
            else:
                setattr(sim, "total_dinero", getattr(sim, "total_dinero", 0) + amount)
            sim.log(f"💰 [ARQUITECTO] ha inyectado {amount} al sistema", categoria="sistema")
        elif sub_action == "drain_money":
            if hasattr(sim, "economia"):
                sim.economia["total_dinero"] = max(0, sim.economia.get("total_dinero", 0) - amount)
            else:
                setattr(sim, "total_dinero", max(0, getattr(sim, "total_dinero", 0) - amount))
            sim.log(f"📉 [ARQUITECTO] ha drenado {amount} del sistema", categoria="sistema")
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    elif action_type == "BUY_LAND":
        direction = params.get("direction")
        count = params.get("count", 1)
        # Ejecutar la expansión en el modelo (arquitecto compra terreno)
        try:
            success, msg = sim.expandir_mundo(direccion=direction, cantidad=count, comprador_id="arquitecto")
        except Exception as e:
            sim.log(f"❌ [EXPANSIÓN] Error ejecutando expandir_mundo: {e}", categoria="sistema")
            await session_manager.broadcast_state(user_id, include_map=True)
            return {"status": "error", "message": str(e)}

        # Forzar envío del mapa actualizado al frontend
        await session_manager.broadcast_state(user_id, include_map=True)

        if success:
            sim.log(f"🗺️ [ARQUITECTO] ha expandido el territorio hacia el {direction}", categoria="sistema")
            return {"status": "success", "message": msg}
        else:
            sim.log(f"❌ [EXPANSIÓN] No se pudo expandir: {msg}", categoria="sistema")
            return {"status": "error", "message": msg}

    elif action_type == "SET_CONTROL_ACTIONS":
        agent_id = params.get("agent_id")
        actions = params.get("actions", [])
        agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
        if agent: agent.acciones_control_usuario = actions[:3]
        await session_manager.broadcast_state(user_id)
        return {"status": "success"}

    return {"status": "error"}

@app.post("/games/refresh/{user_id}")
async def refresh_game(user_id: str):
    """Forzar el re-envío del estado actual al cliente (útil tras eventos realtime)."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")

    try:
        await session_manager.broadcast_state(user_id, force=True)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CreateMultiplayerRoomRequest(BaseModel):
    nombre: str
    host_user_id: str
    host_username: str
    es_publica: bool = True
    modo_juego: str = "cooperativo"
    max_jugadores: int = 8
    num_agents: int = 12

class JoinMultiplayerRoomRequest(BaseModel):
    user_id: str
    username: str
    codigo_acceso: Optional[str] = None
    game_id: Optional[str] = None

def _generate_room_code() -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    prefix = "".join(random.choice(chars) for _ in range(3))
    suffix = "".join(random.choice(chars) for _ in range(3))
    return f"{prefix}-{suffix}"

def _enrich_room_with_live_data(room: Dict[str, Any]) -> Dict[str, Any]:
    game_id = room["game_id"]
    players = session_manager.get_connected_players(game_id)
    sim = session_manager.get_simulation(game_id)
    enriched = dict(room)
    enriched["online_count"] = len(players)
    enriched["online_players"] = players
    if sim:
        enriched["paso_actual"] = getattr(sim, "paso_actual", enriched.get("paso_actual", 0))
        enriched["num_agentes"] = len(getattr(sim, "agentes", []))
    return enriched

@app.get("/multiplayer/rooms")
async def list_multiplayer_rooms(user_id: Optional[str] = None):
    db = DatabaseManager()
    if not db.connect():
        return {"rooms": []}
    rooms = db.list_multiplayer_rooms(user_id=user_id)
    return {"rooms": [_enrich_room_with_live_data(r) for r in rooms]}

@app.get("/multiplayer/rooms/{game_id}")
async def get_multiplayer_room_info(game_id: str):
    db = DatabaseManager()
    room = None
    if db.connect():
        room = db.get_multiplayer_room(game_id)
    if not room:
        # Si es una partida compartida sin registro explícito en salas_multijugador, devolver presencia en vivo
        players = session_manager.get_connected_players(game_id)
        return {
            "room": {
                "game_id": game_id,
                "nombre": f"Realidad {game_id[-6:]}",
                "host_user_id": game_id.split("_")[0],
                "host_username": "Arquitecto",
                "codigo_acceso": game_id[-6:].upper(),
                "es_publica": False,
                "modo_juego": "cooperativo",
                "max_jugadores": 8,
                "online_count": len(players),
                "online_players": players,
            }
        }
    return {"room": _enrich_room_with_live_data(room)}

@app.post("/multiplayer/rooms/create")
async def create_multiplayer_room(req: CreateMultiplayerRoomRequest):
    db = DatabaseManager()
    if not db.connect():
        raise HTTPException(status_code=500, detail="Error conectando a PostgreSQL")

    short_host = (req.host_user_id or "host")[:8]
    game_id = f"mp_{short_host}_{int(time.time() * 1000) % 100000000:x}"
    codigo_acceso = _generate_room_code()
    for _ in range(5):
        if not db.get_multiplayer_room_by_code(codigo_acceso):
            break
        codigo_acceso = _generate_room_code()

    nombre_sala = (req.nombre or "").strip() or f"Nexo de {req.host_username}"

    # Inicializar simulación de la sala
    sim = session_manager.create_simulation(game_id, start_empty=True)
    sim.paso_actual = 1

    num_agents = max(0, min(int(req.num_agents or 0), 50))
    for _ in range(num_agents):
        sim.spawn_agent()

    if sim.agentes and not getattr(sim.historia, "historiador_id", None):
        try:
            elegido = sim.historia.asignar_historiador(sim.agentes, aleatorio=True)
            if elegido:
                elegido.profesion = "Historiador"
                elegido.rol = "Historiador"
        except Exception:
            pass

    if sim.db_active:
        try:
            sim.guardar_estado()
        except Exception as e:
            print(f"⚠️ [MULTIPLAYER] Error guardando estado inicial de sala {game_id}: {e}")

    db.create_multiplayer_room(
        game_id=game_id,
        nombre=nombre_sala,
        host_user_id=req.host_user_id,
        host_username=req.host_username,
        codigo_acceso=codigo_acceso,
        es_publica=req.es_publica,
        modo_juego=req.modo_juego,
        max_jugadores=req.max_jugadores,
    )

    sim.log(
        f"🌐 [MULTIJUGADOR] Sala '{nombre_sala}' (Código: {codigo_acceso}) creada por {req.host_username}.",
        categoria="sistema",
    )

    room = db.get_multiplayer_room(game_id) or {
        "game_id": game_id,
        "nombre": nombre_sala,
        "host_user_id": req.host_user_id,
        "host_username": req.host_username,
        "codigo_acceso": codigo_acceso,
        "es_publica": req.es_publica,
        "modo_juego": req.modo_juego,
        "max_jugadores": req.max_jugadores,
    }
    return {"status": "success", "room": _enrich_room_with_live_data(room)}

@app.post("/multiplayer/rooms/join")
async def join_multiplayer_room(req: JoinMultiplayerRoomRequest):
    db = DatabaseManager()
    if not db.connect():
        raise HTTPException(status_code=500, detail="Error conectando a PostgreSQL")

    room = None
    if req.codigo_acceso:
        room = db.get_multiplayer_room_by_code(req.codigo_acceso.strip())
    elif req.game_id:
        room = db.get_multiplayer_room(req.game_id.strip())

    if not room:
        raise HTTPException(status_code=404, detail="No se encontró ninguna sala con ese código o identificador")

    game_id = room["game_id"]
    players = session_manager.get_connected_players(game_id)
    already_in = any(p["player_id"] == req.user_id for p in players)
    if not already_in and len(players) >= int(room.get("max_jugadores", 8)):
        raise HTTPException(status_code=403, detail="La sala ha alcanzado el límite máximo de jugadores conectados")

    # Asegurar que la simulación esté cargada en memoria
    sim = session_manager.get_simulation(game_id)
    if not sim:
        sim = session_manager.create_simulation(game_id, start_empty=False)

    return {"status": "success", "room": _enrich_room_with_live_data(room)}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    player_id: Optional[str] = None,
    username: Optional[str] = None,
):
    await websocket.accept()
    await session_manager.connect(user_id, websocket, player_id=player_id, username=username)
    sim = session_manager.get_simulation(user_id)
    if not sim:
        sim = session_manager.create_simulation(user_id)

    # Notificar presencia actualizada a todos los clientes de la sala
    await session_manager.send_to_user(
        user_id,
        {
            "type": "players_update",
            "connected_players": session_manager.get_connected_players(user_id),
        },
    )

    # Enviar estado inicial completo (forzando mapa, logs y agentes para el nuevo participante)
    await session_manager.broadcast_state(user_id, include_logs=True, include_map=True, force=True)
    
    try:
        while True:
            # Mantener la conexión viva y escuchar mensajes (pings/heartbeats)
            await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.disconnect(user_id, websocket)
        await session_manager.send_to_user(
            user_id,
            {
                "type": "players_update",
                "connected_players": session_manager.get_connected_players(user_id),
            },
        )
    except Exception as e:
        print(f"⚠️ [WS] Error en socket de {user_id}: {e}")
        session_manager.disconnect(user_id, websocket)
        await session_manager.send_to_user(
            user_id,
            {
                "type": "players_update",
                "connected_players": session_manager.get_connected_players(user_id),
            },
        )

@app.get("/games/list/{user_id}")
async def list_games(user_id: str):
    db = DatabaseManager()
    if db.connect():
        user_games = db.get_user_games(user_id)
        games_response = []
        for g in user_games:
            game_id = g["id"]
            # Obtener el score de este game_id
            score = db.get_score(game_id)
            games_response.append({
                "id": game_id,
                "paso_actual": g["paso_actual"],
                "score": score
            })
        return {"games": games_response}
    return {"games": []}

@app.post("/games/save")
async def save_game(req: SaveLoadRequest):
    sim = session_manager.get_simulation(req.user_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación activa no encontrada")
    
    import anyio
    try:
        # Ejecutar en hilo separado para no bloquear el event loop (I/O pesado)
        await anyio.to_thread.run_sync(sim.guardar_estado)
        return {"status": "success", "message": "Partida guardada en PostgreSQL"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar: {e}")

@app.post("/games/load")
async def load_game(req: SaveLoadRequest):
    # Detener bucle actual si existe
    await session_manager.stop_simulation_loop(req.user_id)
    
    # IMPORTANTE: Eliminar rastro de la simulación anterior para no recargar sobre la que detuvimos
    session_manager.simulations.pop(req.user_id, None)
    session_manager.last_stats.pop(req.user_id, None)
    session_manager.last_agents.pop(req.user_id, None)
    
    # Crear nueva instancia
    sim = session_manager.create_simulation(req.user_id, start_empty=False)
    
    import anyio
    try:
        # Carga pesada en hilo secundario
        await anyio.to_thread.run_sync(sim.cargar_estado)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar: {e}")
    
    await session_manager.broadcast_state(req.user_id, include_map=True, include_logs=True)
    return {"status": "success", "message": "Partida cargada correctamente"}

@app.post("/games/quickplay")
async def quickplay(req: QuickPlayRequest):
    await session_manager.stop_simulation_loop(req.user_id)
    
    # Eliminar viejo estado
    session_manager.simulations.pop(req.user_id, None)
    session_manager.last_stats.pop(req.user_id, None)
    session_manager.last_agents.pop(req.user_id, None)
    
    # Resetear y crear nueva
    sim = session_manager.create_simulation(req.user_id, start_empty=True)
    sim.paso_actual = 1
    
    # Generar agentes aleatorios
    for i in range(req.num_agents):
        sim.spawn_agent()
    # Asignar historiador aleatorio al inicio de la partida si aún no hay uno
    try:
        if not getattr(sim.historia, "historiador_id", None) and sim.agentes:
            elegido = sim.historia.asignar_historiador(sim.agentes, aleatorio=True)
            if elegido:
                try:
                    elegido.profesion = "Historiador"
                    elegido.rol = "Historiador"
                    if hasattr(elegido, "identidad") and elegido.identidad:
                        elegido.identidad.titulo = "el Historiador"
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️ [QUICKPLAY] Error asignando historiador: {e}")

    # Asignar historiador aleatorio al inicio de la partida
    if sim.agentes and not sim.historia.historiador_id:
        sim.historia.asignar_historiador(sim.agentes)
        print(f"📜 [HISTORIADOR] {sim.historia.historiador_id} ha sido asignado como Historiador del mundo")
        
    if sim.db_active and hasattr(sim, "db") and sim.db:
        try:
            sim.db.clear_database(req.user_id)
            print(f"🧹 [QUICKPLAY] Base de Datos limpiada para {req.user_id}")
        except Exception as e:
            print(f"⚠️ [QUICKPLAY] Error limpiando DB: {e}")

    if req.save:
        sim.guardar_estado()
        
    await session_manager.broadcast_state(req.user_id, include_map=True, include_logs=True)
    return {"status": "success", "message": f"Partida rápida iniciada con {req.num_agents} agentes"}

# === CONFIGURATION ENDPOINTS ===

@app.get("/config/ai")
async def get_ai_config():
    """Retorna la configuración actual del LLM."""
    return {
        "provider": os.getenv("AI_PROVIDER", "openrouter"),
        "model": os.getenv("MODEL_NAME", "google/gemini-2.0-flash-exp:free"),
        "base_url": os.getenv("AI_BASE_URL", ""),
        "has_openrouter_key": bool(os.getenv("OPENROUTER_API_KEY")),
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "has_ollama_key": bool(os.getenv("OLLAMA_API_KEY") or os.getenv("OLLAMA_API_BASE")),
        "has_kilocode_key": bool(os.getenv("KILOCODE_API_KEY")),
        "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
    }
@app.post("/config/ai")
async def set_ai_config(req: AIConfig):
    """Actualiza la configuración del LLM en caliente."""
    os.environ["MODEL_NAME"] = req.model
    os.environ["AI_PROVIDER"] = req.provider
    # Guardar API key por proveedor
    if req.provider == "openrouter" and req.api_key:
        os.environ["OPENROUTER_API_KEY"] = req.api_key
    elif req.provider == "openai" and req.api_key:
        os.environ["OPENAI_API_KEY"] = req.api_key
    elif req.provider == "ollama" and req.api_key:
        os.environ["OLLAMA_API_KEY"] = req.api_key
    elif req.provider == "kilocode" and req.api_key:
        os.environ["KILOCODE_API_KEY"] = req.api_key
        
    if req.base_url and req.provider in ("ollama", "kilocode"):
        os.environ["AI_BASE_URL"] = req.base_url
    elif req.provider not in ("ollama", "kilocode"):
        # Limpiar AI_BASE_URL al cambiar a otros proveedores para evitar conflictos
        os.environ.pop("AI_BASE_URL", None)
        os.environ.pop("OLLAMA_API_BASE", None)
        
    if req.tavily_api_key:
        os.environ["TAVILY_API_KEY"] = req.tavily_api_key
    # Persistir en config_ai.json para que sobreviva a reinicios
    try:
        import json
        config_data = {
            "model": req.model,
            "provider": req.provider,
            "api_key": req.api_key,
            "base_url": req.base_url if req.provider in ("ollama", "kilocode") else "",
            "tavily_api_key": req.tavily_api_key or ""
        }
        with open("config_ai.json", "w") as f:
            json.dump(config_data, f, indent=2)
        print(f"✅ Configuración guardada en config_ai.json: {req.provider}/{req.model}")
    except Exception as e:
        print(f"⚠️ Error guardando config_ai.json: {e}")
    # Recargar configuración en el cerebro LLM global
    try:
        from agents.cerebro_llm import cerebro_llm
        cerebro_llm.reload_config()
    except Exception as e:
        print(f"⚠️ Error recargando config en cerebro_llm: {e}")
    return {"status": "success", "message": "Configuración actualizada"}
@app.get("/config/models/{provider}")
async def get_provider_models(provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
    """Retorna la lista de modelos disponibles para un proveedor (OpenRouter, Ollama).
    Parámetros opcionales: `api_key`, `base_url` (sobrescribe el de entorno).
    La respuesta siempre contiene la clave `models` con una lista (posiblemente vacía).
    """
    prov = (provider or "").strip().lower()
    models = []

    try:
        if prov == "ollama":
            # Determinar base_url: prioridad: query param -> AI_BASE_URL -> OLLAMA_API_BASE -> host.docker.internal
            base = base_url or os.getenv("AI_BASE_URL") or os.getenv("OLLAMA_API_BASE") or "http://host.docker.internal:11434"
            # Intentar endpoints conocidos hasta encontrar uno válido
            candidates = ["/api/tags", "/api/models", "/models", "/api/list"]
            for ep in candidates:
                url = base.rstrip("/") + ep
                try:
                    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                    resp = requests.get(url, timeout=5, headers=headers)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    raw = []
                    if isinstance(data, dict):
                        raw = data.get("models") or data.get("tags") or data.get("data") or data.get("results") or []
                    elif isinstance(data, list):
                        raw = data

                    for m in raw:
                        if isinstance(m, dict):
                            mid = m.get("id") or m.get("name") or str(m)
                            name = m.get("name") or m.get("id") or str(m)
                            models.append({"id": mid, "name": name, **{k: v for k, v in m.items() if k not in ("id", "name")}})
                        else:
                            models.append({"id": str(m), "name": str(m)})
                    # Si obtuvimos modelos, detener búsqueda
                    if models:
                        break
                except Exception:
                    continue

        elif prov == "openrouter":
            # Usar base_url si se entregó (posible proxy), sino el endpoint público
            base = base_url or os.getenv("AI_BASE_URL") or "https://openrouter.ai/api"
            if base.endswith("/v1"):
                url = base.rstrip("/") + "/models"
            else:
                url = base.rstrip("/") + "/v1/models"
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = requests.get(url, timeout=6, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                raw = []
                if isinstance(data, dict):
                    raw = data.get("models") or data.get("data") or data.get("results") or []
                elif isinstance(data, list):
                    raw = data

                for m in raw:
                    if isinstance(m, dict):
                        mid = m.get("id") or m.get("name") or str(m)
                        name = m.get("name") or m.get("id") or str(m)
                        models.append({"id": mid, "name": name, **{k: v for k, v in m.items() if k not in ("id", "name")}})
                    else:
                        models.append({"id": str(m), "name": str(m)})

        elif prov == "kilocode":
            # Usar base_url si se entregó (posible proxy), sino el endpoint público de KiloCode
            base = base_url or os.getenv("AI_BASE_URL") or "https://api.kilo.ai/api/gateway"
            url = base.rstrip("/") + "/models"
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = requests.get(url, timeout=6, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                raw = []
                if isinstance(data, dict):
                    raw = data.get("models") or data.get("data") or data.get("results") or []
                elif isinstance(data, list):
                    raw = data

                for m in raw:
                    if isinstance(m, dict):
                        mid = m.get("id") or m.get("name") or str(m)
                        name = m.get("name") or m.get("id") or str(m)
                        models.append({"id": mid, "name": name, **{k: v for k, v in m.items() if k not in ("id", "name")}})
                    else:
                        models.append({"id": str(m), "name": str(m)})

        else:
            # Proveedor desconocido: devolver lista vacía
            models = []
    except Exception as e:
        print(f"[CONFIG MODELS] Error fetching models for {provider}: {e}")

    return {"models": models, "provider": provider, "count": len(models)}

# === AGENT SPAWNING & LISTING ===

@app.post("/game/spawn/{user_id}")
async def spawn_agent_endpoint(user_id: str, config: AgentConfig = Body(None)):
    sim = session_manager.get_simulation(user_id)
    if not sim:
        sim = session_manager.create_simulation(user_id)

    agente = sim.spawn_agent(config=config)
    sim.log(f"🧬 [DIVINO] Un nuevo agente '{agente.unique_id}' ha sido manifestado.", categoria="sistema")

    # Si aún no hay historiador asignado, asignar uno
    if not sim.historia.historiador_id and sim.agentes:
        sim.historia.asignar_historiador(sim.agentes)
        print(f"📜 [HISTORIADOR] {sim.historia.historiador_id} ha sido asignado como Historiador del mundo")

    await session_manager.broadcast_state(user_id, include_map=True)
    return {
        "status": "success",
        "message": f"Agente '{agente.unique_id}' creado",
        "agent_id": agente.unique_id,
    }

@app.get("/chat/{user_id}/agents")
async def chat_get_agents(user_id: str):
    """Devuelve la lista de agentes disponibles para chat con metadata enriquecida."""
    sim = session_manager.get_simulation(user_id)
    if not sim:
        sim = session_manager.create_simulation(user_id)

    agents_list = []
    for a in sim.agentes:
        p = a.personalidad if a.personalidad else {}
        rasgo_dominante = max(p, key=p.get) if p else "neutral"
        valor_dominante = p.get(rasgo_dominante, 0) if p else 0

        color = "#ffffff"
        if a.grupo_id and a.grupo_id in sim.civilizaciones:
            color = sim.civilizaciones[a.grupo_id].color

        agents_list.append({
            "id": a.unique_id,
            # Nombre público: preferir identidad.nombre, luego atributo directo, finalmente id
            "nombre": (getattr(getattr(a, "identidad", None), "nombre", None) or getattr(a, "nombre", None) or a.unique_id),
            "rol": a.rol,
            "profesion": getattr(a, "profesion", None),
            "grupo_id": a.grupo_id,
            "reputacion": getattr(a, "reputacion", 1.0),
            "personalidad_resumen": f"{rasgo_dominante.capitalize()} ({valor_dominante:.0%})",
            "pensamiento": getattr(a, "pensamiento_actual", "..."),
            "color": color,
            "esta_vivo": a.necesidades.get("salud", 0) > 0,
            "alma": getattr(a, "alma", None).to_dict() if hasattr(a, "alma") and getattr(a, "alma", None) else None,
        })

    return {"agents": agents_list}

# === SOCIAL ENDPOINTS ===

@app.post("/social/post/{user_id}")
async def social_post(user_id: str, req: SocialPostRequest):
    sim = session_manager.get_simulation(user_id)
    if not sim: raise HTTPException(status_code=404, detail="Simulación no encontrada")
    
    if hasattr(sim, "social_recsys") and sim.social_recsys:
        architect_id = f"arquitecto_{user_id}"
        post = sim.social_recsys.crear_post(
            user_id=user_id,
            autor_id=architect_id,
            contenido=req.content,
            tipo=req.tipo,
            temas=req.temas or ["General"]
        )
        post_id = post.id
        # Notify clients - include_logs=True fuerza broadcast completo
        # para que el post nuevo se vea inmediatamente sin esperar al siguiente throttle cycle
        await session_manager.broadcast_state(user_id, include_logs=True)
        return {"status": "success", "post_id": post_id}
    raise HTTPException(status_code=500, detail="Social DB not active")

@app.post("/social/like/{user_id}")
async def social_like(user_id: str, req: SocialLikeRequest):
    sim = session_manager.get_simulation(user_id)
    if not sim: raise HTTPException(status_code=404, detail="Simulación no encontrada")
    
    if hasattr(sim, "social_recsys") and sim.social_recsys:
        architect_id = f"arquitecto_{user_id}"
        post = sim.social_recsys.interest_recsys.posts.get(req.post_id)
        if post:
            if architect_id not in post.likes_por:
                if sim.social_recsys.likear_post(req.post_id, architect_id):
                    await session_manager.broadcast_state(user_id, force=True)
                    return {"status": "success"}
            else:
                if sim.social_recsys.unlikear_post(req.post_id, architect_id):
                    await session_manager.broadcast_state(user_id, force=True)
                    return {"status": "success", "action": "unliked"}
            return {"status": "error", "message": "Already processed"}
        raise HTTPException(status_code=404, detail="Post not found")
    raise HTTPException(status_code=500, detail="Social DB not active")

@app.post("/social/comment/{user_id}")
async def social_comment(user_id: str, req: SocialCommentRequest):
    sim = session_manager.get_simulation(user_id)
    if not sim: raise HTTPException(status_code=404, detail="Simulación no encontrada")
    
    if hasattr(sim, "social_recsys") and sim.social_recsys:
        architect_id = f"arquitecto_{user_id}"
        # Forzar un ID de comentario
        from uuid import uuid4
        result = sim.social_recsys.agregar_comentario(
            post_id=req.post_id,
            autor_id=architect_id,
            contenido=req.content
        )
        # Log para debug
        post = sim.social_recsys.interest_recsys.posts.get(req.post_id)
        comentarios_count = len(sim.social_recsys.interest_recsys.comentarios.get(req.post_id, []))
        print(f"✅ [COMMENT] Comment added to post {req.post_id}. Total comments: {comentarios_count}")
        if post:
            post_comentarios = getattr(post, 'comentarios', 'N/A')
            post_detalle = len(getattr(post, 'comentarios_detalle', []))
            print(f"   Post comments count: {post_comentarios}, comentarios_detalle length: {post_detalle}")
        await session_manager.broadcast_state(user_id, include_logs=True)
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Social DB not active")

# === AGENT CHAT & THOUGHTS ===

@app.get("/chat/{user_id}/{agent_id}/history")
async def chat_get_history(user_id: str, agent_id: str):
    sim = session_manager.get_simulation(user_id)
    if not sim: raise HTTPException(status_code=404, detail="Simulación no encontrada")
    messages = sim.db.get_chat_history(user_id, agent_id)
    return {"messages": messages}

@app.post("/chat/{user_id}/{agent_id}")
async def chat_send_message(user_id: str, agent_id: str, req: ChatMessageRequest):
    sim = session_manager.get_simulation(user_id)
    if not sim: raise HTTPException(status_code=404, detail="Simulación no encontrada")

    agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
    if not agent: raise HTTPException(status_code=404, detail="Agente no encontrado")
    
    if agent.necesidades.get("salud", 0) <= 0:
        raise HTTPException(status_code=400, detail="Este agente ha fallecido")

    # Guardar mensaje del usuario
    sim.db.save_chat_message(user_id, agent_id, "user", req.message, time.time())

    # Generar respuesta in-character
    from agents.cerebro_llm import cerebro_llm
    
    res, pensamiento = cerebro_llm.responder_directamente(agent, req.message, rol_interlocutor="El Arquitecto (tu creador)")
    
    if not res: res = "..."
    
    # Guardar y loguear respuesta
    sim.db.save_chat_message(user_id, agent_id, "agent", res, time.time())
    agent.decir(res, pensamiento=pensamiento)
    
    return {"response": res}

@app.get("/agents/{user_id}/{agent_id}/thoughts")
async def get_agent_thoughts(user_id: str, agent_id: str, limit: int = 20):
    sim = session_manager.get_simulation(user_id)
    if not sim: raise HTTPException(status_code=404, detail="Simulación no encontrada")
    agent = next((a for a in sim.agentes if a.unique_id == agent_id), None)
    if not agent: raise HTTPException(status_code=404, detail="Agente no encontrado")
    
    thoughts = getattr(agent, "pensamientos_recientes", [])
    return {"agent_id": agent_id, "thoughts": thoughts[-limit:]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
