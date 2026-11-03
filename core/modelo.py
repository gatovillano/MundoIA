import random
import math
import time
import threading
try:
    import matplotlib
    matplotlib.use("Agg")  # Backend para entornos sin interfaz gráfica
    import matplotlib.pyplot as plt
except Exception:
    matplotlib = None
    plt = None

try:
    import pandas as pd
except Exception:
    pd = None

try:
    import numpy as np
except Exception:
    np = None
from systems.memoria import MemoriaGrafica
from agents.cerebro_langgraph import CerebroAvanzado
from agents.cerebro_llm import cerebro_llm
from dotenv import load_dotenv
import os
import json
import functools
import logging
import bcrypt
import uuid
import psycopg2
from typing import List, Dict, Any, Optional
from types import SimpleNamespace
from collections import defaultdict
from datetime import datetime, date
from psycopg2.extras import Json as _Json

from agents.alma import generar_alma_inicial
from agents.identity_system import generar_identidad_inicial, SistemaIdentidades
from systems.cronicas import SistemaCronicas, TipoCronica
from systems.eventos_emergentes import SistemaEventosEmergentes
from core.skills_manager import skill_manager
from core.skill_factory import SkillFactory
from systems.sistema_misiones import SistemaMisiones
from core.world_system import WorldSystem, WorldTile, TerrainType
from systems.historia import LibretaHistoria
from core.database import DatabaseManager
from core.entities.faction import Civilizacion
from core.entities.structure import Institucion

# Alias para compatibilidad con el sistema de mundo
Tile = WorldTile


class WeatherType:
    SUNNY = "sunny"
    RAINY = "rainy"
    STORM = "storm"
    FOGGY = "foggy"
    HEATWAVE = "heatwave"


# Inicializar SkillFactory global
skill_factory = SkillFactory(skill_manager)
from core.entities.agent import Agente
from systems.sistema_misiones import SistemaMisiones, Mision
from core.action_validator import validar_accion, obtener_accion_fallback
from systems.optimizador import DecisionOptimizer
from agents.bdi_components import (
    Credencia,
    SistemaCreencias,
    Deseo,
    SistemaDeseos,
    SistemaIntenciones,
    PlanBDI,
    AccionBDI,
    TipoDeseo,
    TipoAccion,
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Wrapper para que Psycopg2 use nuestro encoder al guardar JSONs
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def Json(data):
    return _Json(data, dumps=lambda obj: json.dumps(obj, cls=DateTimeEncoder))


def synchronized(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        lock = getattr(self.modelo, "lock", None) if hasattr(self, "modelo") else None
        if lock:
            with lock:
                return func(self, *args, **kwargs)
        return func(self, *args, **kwargs)

    return wrapper


class ModeloRelacional:
    """Clase principal del modelo de simulación multi-agente."""

    def __init__(
        self, num_agentes=10, log_callback=None, user_id=None, start_empty=False
    ):
        self.num_agentes = num_agentes if not start_empty else 0
        self.start_empty = start_empty
        self.log_callback = log_callback
        self.user_id = user_id
        self.ritmo = (
            0.1  # Segundos de pausa entre agentes para un flujo observable a escala humana
        )
        self.autosave_interval = max(
            10, int(os.getenv("MUNDOIA_AUTOSAVE_INTERVAL", "20"))
        )
        self.backup_interval = max(
            self.autosave_interval,
            int(os.getenv("MUNDOIA_BACKUP_INTERVAL", "60")),
        )
        self.social_post_min_interval = max(
            1, int(os.getenv("MUNDOIA_SOCIAL_POST_MIN_INTERVAL", "4"))
        )
        self.social_llm_ratio = max(
            0.0, min(1.0, float(os.getenv("MUNDOIA_SOCIAL_LLM_RATIO", "1.0")))
        )
        self.lock = threading.RLock()

        self.agentes_cargados = False  # Importante: definir antes de cargar
        self.state_change_callback = None  # Callback para forzar actualización de UI
        self.realtime_event_callback = None  # Callback WS para eventos en vivo
        self._force_stop = (
            False  # Control de detención para evitar race conditions en reset
        )
        self._stopped = (
            False  # Flag para bloquear logs/callbacks después de un stop/reset
        )

        # Conectar herramientas y skills con el sistema de logs del modelo
        if self.log_callback:
            skill_manager.log_callback = self.log

        # Inicializar atributos a un estado base/vacío antes de cargar
        self.paso_actual = 0
        self.agentes = []
        self.objetivos_grupos = {}
        self.precio_recurso_actual = 2.0
        self.economia = {
            "total_dinero": 0,
            "indice_bursatil": 100.0,
            "precio_recurso": 2.0,
            "historial_indice": [],
            "historial_precios": [],
        }
        self.historial_relaciones = []
        self.historial_grupos = []
        self.datos = []
        self.relaciones_grupos = {}
        self.historial_logs = []
        self.asambleas_globales = []
        self.leyes_globales = []
        self.facciones_leyes = {}
        self.asamblea_bloqueante_activa = False  # Bloqueo total hasta consenso
        self.plebiscito_simultaneo_activo = False  # Nueva flag para voto rápido
        self.consenso_alcanzado = False  # Flag para ciclo de asamblea
        self.instituciones = {}  # Almacena instituciones formalizadas
        self.guerras_activas = []
        self.grupos_creados_este_paso = 0
        self.moderador_id = None
        self.ultimo_paso_asamblea = -100  # Cooldown inicial para asambleas
        self.candidatos_vocero = {}  # {grupo_id: [agent_id1, agent_id2, ...]}
        self.ultima_eleccion_paso = -100  # Última vez que se procesó elección
        self.ELECCION_FRECUENCIA = 30  # Cada 30 pasos
        self.infraestructura = []
        self.civilizaciones = {}
        self.agente_poseido_id = None  # Seguimiento global del agente bajo control del usuario
        self.colores_paleta = [
            "#7c4dff",  # Cyber Violet
            "#00e676",  # Neon Mint
            "#2979ff",  # Azure Blue
            "#ffab00",  # Amber Gold
            "#ff1744",  # Crimson Red
            "#f50057",  # Shocking Pink
            "#00b0ff",  # Vivid Cerulean
            "#d4e157",  # Lime Green
            "#ff9100",  # Vivid Orange
            "#651fff",  # Deep Purple
        ]
        self.grupos_dinamicos = {}
        self.grupos_bajas_turnos = {}
        self.seed = str(random.randint(0, 99999999))
        self.world = None  # Se inicializará después de cargar_estado()
        self.mapa = None  # Lista vacía inicial
        self._map_dirty = False  # Marca cambios estructurales del mapa para refresco en frontend
        self.mapa_size = 20  # Tamaño por defecto
        # Configuración para control de Centros de Descanso
        self.CENTRO_DESCANSO_MAX_CELLS = 10  # Más centros por celda
        self.CENTRO_DESCANSO_MIN_DISTANCE = 6  # distancia Manhattan mínima entre centros
        self.COSTO_EXPANSION = 1000.0  # Costo en MC por cada nivel de expansión
        # Configuración para relajar requisitos de compra de terreno
        # Si es True, permiten miembros no-voceroes comprar/expandir en nombre del grupo
        self.ALLOW_NON_LEADER_EXPANSION = True
        # Divisor para reducir el coste base derivado de `COSTO_EXPANSION` (más alto = más barato)
        self.EXPANSION_COST_DIVISOR = 10
        self.ubicacion_universidad = None
        self.weather = WeatherType.SUNNY
        self.weather_timer = 0
        self.weather_duration = 20
        self.lore = ""
        self.eventos_activos = []
        self.sistema_misiones = SistemaMisiones()
        self.misiones_completadas_este_turno = []
        self.historia = LibretaHistoria()
        self.sistema_eventos: Optional[SistemaEventosEmergentes] = None  # Se inicializa tras el mapa
        self.db_active = True
        self.db = DatabaseManager()
        self.cerebro_llm = cerebro_llm  # Instancia global de CerebroLLM
        self.modo_control_total = False  # Si es True, el usuario decide quién y qué hace cada turno
        if self.db:
            if self.db.connect():
                if self.user_id:
                    self.db.ensure_user_exists(self.user_id)
            else:
                logger.warning(
                    "⚠️ No se pudo conectar a la base de datos al iniciar ModeloRelacional. "
                    "La persistencia estará deshabilitada para esta sesión."
                )
                self.db_active = False
                self.db = None

        self.time_engine = None
        self.social_recsys = None

        # Control por agente (modo Arquitecto)
        self._control_pending_agents = set()
        self._control_round_active = False

        # Intentar cargar la simulación de la base de datos si no se solicita una vacía
        if not self.start_empty:
            self.cargar_estado()

        # Inicializar social_recsys si no se cargó de DB
        if self.social_recsys is None:
            try:
                # Evitar cargar posts desde la BD si la simulación se inicia como vacía
                self.social_recsys = SocialRecSys(self.db, self.user_id, load_from_db=(not self.start_empty), modelo=self)
                self.log(
                    "📱 SocialRecSys inicializado para nueva simulación",
                    categoria="sistema",
                )
            except Exception as e:
                self.log(
                    f"⚠️ No se pudo inicializar SocialRecSys: {e}. Funcionalidad social deshabilitada.",
                    categoria="sistema",
                )
                self.social_recsys = None

        # Inicializar WorldSystem y generar mapa SI NO se cargó de DB
        if self.world is None:
            self.world = WorldSystem(size=self.mapa_size, seed=self.seed)
            self.mapa = self.world.mapa
            self.world.size = self.mapa_size

        # Generar mapa inicial obligatorio si está vacío o si no se recuperó de DB
        if not self.mapa or len(self.mapa) == 0:
            self.generar_mapa()

        # Inicializar sistema de eventos emergentes (requiere mapa)
        if self.sistema_eventos is None:
            self.sistema_eventos = SistemaEventosEmergentes(self)
            self.log("🌍 SistemaEventosEmergentes inicializado.", categoria="sistema")

        # Inicializar skill factory y cerebro
        from core.skill_factory import SkillFactory

        global skill_factory
        skill_factory = SkillFactory(skill_manager)
        from agents.cerebro_llm import initialize_cerebro_with_skills

        initialize_cerebro_with_skills(skill_factory)

        # Asignar historiador al iniciar la simulación si aún no hay uno
        try:
            if not getattr(self.historia, "historiador_id", None) and self.agentes:
                elegido = self.historia.asignar_historiador(self.agentes, aleatorio=True)
                if elegido:
                    # Marcar profesión/rol y título público para que el frontend lo muestre
                    try:
                        elegido.profesion = "Historiador"
                        elegido.rol = "Historiador"
                        if hasattr(elegido, "identidad") and elegido.identidad:
                            elegido.identidad.titulo = "el Historiador"
                    except Exception:
                        pass

                    self.log(
                        f"📜 [HISTORIA] Historiador asignado: {elegido.unique_id}",
                        categoria="sistema",
                    )

                    # Persistir cambio del agente si la DB está activa
                    if self.db_active and getattr(self, "db", None):
                        try:
                            self.db.save_agent(elegido, self.user_id)
                        except Exception:
                            pass
        except Exception as e:
            self.log(f"⚠️ [HISTORIA] Error asignando historiador: {e}", categoria="sistema")

    @property
    def asambleas_activas(self):
        """Retorna la lista de asambleas que están en fase de debate o votación."""
        return [
            a
            for a in self.asambleas_globales
            if a.get("estado") in ["DEBATE", "VOTACION"]
        ]

    def _procesar_turno_agente(self, agente):
        """Procesa el ciclo completo de vida de un agente en un turno.

        Estructura obligatoria por turno (gamificación):
        1) Un mensaje (público/privado/grupal según decida el agente)
        2) Una acción física en el mundo
        3) Una acción en la red social

        Este método garantiza que si la IA no propone alguno de esos pasos, se
        generan fallback razonables basados en necesidades y el estado del agente.
        """
        with self.lock:
            if not agente.esta_vivo:
                return

            # 1. ACTUALIZAR METABOLISMO
            # MECANISMO DE DESCANSO AUTOMÁTICO (SOLICITUD USUARIO)
            # Si el descanso llega a 0, el agente salta el turno y recupera descanso.
            if agente.necesidades.get("descanso", 10.0) <= 0:
                # Recuperar descanso al saltar el turno (bono de descanso)
                agente.necesidades["descanso"] = min(10.0, agente.necesidades["descanso"] + 3.0)
                
                # Metabolismo reducido durante el sueño
                agente.necesidades["alimento"] = max(0, agente.necesidades["alimento"] - 0.05)
                agente.necesidades["social"] = max(0, agente.necesidades["social"] - 0.02)
                
                agente.pensamiento_actual = "Zzz... Estoy exhausto. Necesito descansar un turno completo para recuperar fuerzas."
                
                self.log(
                    f"💤 [DESCANSO] {agente.unique_id} ha llegado al límite de agotamiento (0) y salta su turno para descansar.",
                    categoria="sistema",
                    agente_id=agente.unique_id
                )
                
                # Auto-alimentación si es crítico y tiene comida a mano
                if agente.necesidades["alimento"] < 3.0 and agente.inventario.get("comida", 0) > 0:
                    agente.comer()
                
                # Notificar cambio para que se vea el estado 'Zzz' en la UI si aplica
                if hasattr(self, "notificar_cambio_estado"):
                    self.notificar_cambio_estado()
                
                return

            agente.necesidades["alimento"] = max(0, agente.necesidades["alimento"] - 0.15)
            agente.necesidades["descanso"] = max(0, agente.necesidades["descanso"] - 0.10)
            agente.necesidades["social"] = max(0, agente.necesidades["social"] - 0.08)

            # Auto-alimentación si tiene hambre y comida
            if (
                agente.necesidades["alimento"] < 4.0
                and agente.inventario.get("comida", 0) > 0
            ):
                agente.comer()

            # 1.1. MOVIMIENTO AUTÓNOMO (antes de la cognición)
            # Nota: El movimiento autónomo ahora se procesa COLECTIVAMENTE
            # al final del paso para evitar solapamientos y lograr reubicación
            # simultánea de hasta 2 casillas. Aquí ya no movemos agentes.

            # 1.5. CHEQUEO DE POSESIÓN (Saltar autonomía si el Arquitecto tiene el control)
            # Precomputar `acciones_plan` para evitar UnboundLocalError si se asigna más abajo.
            acciones_plan = getattr(agente, "acciones_control_usuario", [])
            if getattr(self, "agente_poseido_id", None) == agente.unique_id and not acciones_plan:
                # Si está poseído pero NO tiene acciones de control manual este turno, no hace nada autónomo.
                # Excepto metabolismo y auto-alimentación que ya se procesaron arriba.
                agente.pensamiento_actual = "Consciencia enlazada con el Arquitecto. Esperando órdenes..."
                return

            # 2. CONTROL DE USUARIO (Plan de turno forzado)
            acciones_plan = getattr(agente, "acciones_control_usuario", [])
            if acciones_plan:
                agente.acciones_control_usuario = []  # Limpiar para evitar bucles
                agente._ejecutando_decreto = True # Marcar para que las acciones físicas sean gratuitas/exitosas

                self.log(f"🎮 [CONTROL] Ejecutando plan de {len(acciones_plan)} acciones para {agente.unique_id}", categoria="sistema")

                for i, user_action in enumerate(acciones_plan):
                    try:
                        # Obtener contexto para el LLM (usando lógica del cerebro si está disponible)
                        contexto_str = "Situación normal de supervivencia."
                        if hasattr(agente, "cerebro") and hasattr(agente.cerebro, "agent_id"):
                            from agents.cerebro_langgraph import analizar_situacion
                            state_mini = {
                                "agente_yo_id": agente.unique_id,
                                "modelo_instance": self,
                                "info_externa": ""
                            }
                            res_analisis = analizar_situacion(state_mini)
                            contexto_str = res_analisis.get("info_externa", contexto_str)

                        # Generar narrativa para esta acción específica
                        # === Construir callback de streaming (igual que modo Observador) ===
                        stream_started = {"value": False}
                        def _emit_llm_stream_control(chunk: str, done: bool = False):
                            cb = getattr(self, "realtime_event_callback", None)
                            if not cb:
                                return
                            payload = {
                                "agent_id": agente.unique_id,
                                "agent_name": agente.identidad.nombre if agente.identidad else agente.unique_id,
                                "step": self.paso_actual,
                                "chunk": chunk or "",
                                "reset": not stream_started["value"],
                                "done": bool(done),
                            }
                            stream_started["value"] = True
                            try:
                                if hasattr(self, "_emit_realtime_event"):
                                    self._emit_realtime_event("llm_stream", payload)
                                else:
                                    cb("llm_stream", payload)
                            except Exception:
                                pass

                        if self.cerebro_llm and getattr(self.cerebro_llm, "model", None):
                            decision = self.cerebro_llm.generar_pensamiento_para_accion_forzada(
                                agente, None, contexto_str, user_action,
                                stream_callback=_emit_llm_stream_control
                            )
                        else:
                            decision = {
                                "pensamiento": "Siento un impulso irresistible de actuar.",
                                "mensaje": "Cumpliré con mi destino.",
                                "accion": user_action
                            }

                        pensamiento = decision.get("pensamiento", "")
                        mensaje = decision.get("mensaje", "")

                        # 1. Actualizar estado cognitivo
                        if pensamiento:
                            agente.pensamiento_actual = pensamiento

                        # 2. Comunicación
                        if mensaje:
                            agente.decir(mensaje, pensamiento=pensamiento)
                        else:
                            agente.decir("Ejecutando orden divina.", pensamiento="Mi voluntad no es mía.")

                        # 3. Ejecución física inamovible (ignorar lo que el LLM quiso alterar)
                        exito = agente.ejecutar_accion_final(user_action)
                        if not exito:
                            # Fallback de formato
                            alt_action = {"tipo": user_action.get("action", user_action.get("tipo", "")), "parametros": user_action.get("payload", user_action.get("parametros", {}))}
                            exito = agente.ejecutar_accion_final(alt_action)

                        # Notificar éxito de la acción parcial (posible retraso según ritmo)
                        if getattr(self, "realtime_event_callback", None):
                            self._emit_realtime_event("action_event", {
                                "agent_id": agente.unique_id,
                                "step": self.paso_actual,
                                "status": "completed",
                                "action_name": user_action.get("tipo", user_action.get("action", "CONTROL")),
                                "sub_step": i + 1,
                            })

                    except Exception as e:
                        self.log(f"❌ [CONTROL ERROR] Fallo en acción {i+1}: {e}", categoria="error")
                
                agente._ejecutando_decreto = False
                return  # Terminar turno controlado aquí

            # 2.5. RESPUESTA A NECESIDADES CRÍTICAS (Forzar antes del cerebro)
            umbral_critico = 3.0
            necesidades_criticas = []
            for nec in ["alimento", "descanso", "salud"]:
                if agente.necesidades.get(nec, 10) < umbral_critico:
                    necesidades_criticas.append(nec)
            
            skip_cerebro = False
            decision = None
            if necesidades_criticas:
                # Priorizar la necesidad más urgente (menor valor)
                necesidad_prioritaria = min(necesidades_criticas, key=lambda n: agente.necesidades.get(n, 10))
                x, y = agente.x, agente.y
                resultado = self.buscar_edificio_para_necesidad(x, y, necesidad_prioritaria, radio=15)
                if resultado:
                    dist, edif, dest_x, dest_y = resultado
                    # Forzar acción
                    agente.pensamiento_actual = f"¡Necesidad crítica de {necesidad_prioritaria}! Dirigiéndome a {edif.get('tipo')} en ({dest_x}, {dest_y})."
                    # Construir decisión manual
                    decision = (
                        f"FORZADO_{necesidad_prioritaria.upper()}",
                        f"Busco {edif.get('tipo')} para {necesidad_prioritaria}",
                        agente.pensamiento_actual,
                        False,
                        False,
                        False,
                        [],
                        {"nombre": f"IR_A_{edif.get('tipo').upper()}", "tipo": "MOVER", "destino": (dest_x, dest_y)},
                        None
                    )
                    skip_cerebro = True
            
            if not skip_cerebro:
                # 3. CEREBRO: LANGGRAPH / LLM / BDI
                # Llamar al cerebro avanzado para decidir pensamiento, mensaje y acción
                decision = agente.cerebro.pensar(agente)
    
            # Procesar la decisión (sea del cerebro o forzada)
            if decision is not None:
                # El cerebro avanzado devuelve:
                # (decision_str, mensaje, pensamiento, privado, es_grupal, es_global, planes, accion_dict, destinatario_id)
                (
                    _,
                    mensaje,
                    pensamiento,
                    privado,
                    es_grupal,
                    es_global,
                    _,
                    accion_dict,
                    destinatario_id,
                ) = decision
            else:
                # Fallback en caso de error
                mensaje = "No pude decidir qué hacer."
                pensamiento = agente.pensamiento_actual or "Confundido."
                privado = False
                es_grupal = False
                es_global = False
                accion_dict = None
                destinatario_id = None

            # 3. COMUNICACIÓN Y PENSAMIENTO (OBLIGATORIO)

            if pensamiento:
                agente.pensamiento_actual = pensamiento

            if mensaje:
                agente.decir(
                    mensaje,
                    pensamiento=pensamiento,
                    privado_para=destinatario_id if privado else None,
                    para_grupo=es_grupal,
                    global_broadcast=es_global,
                )
            else:
                # Fallback: forzar un mensaje breve que indique intención/estado
                action_hint = None
                if accion_dict:
                    action_hint = accion_dict.get("nombre") or accion_dict.get("tipo")
                if not action_hint:
                    try:
                        action_hint = agente._evaluar_tipo_accion_necesidades()
                    except Exception:
                        action_hint = "ACTIVIDAD"
                fallback_msg = (
                    f"{agente.identidad.nombre if getattr(agente, 'identidad', None) else agente.unique_id}: "
                    f"Realizando: {action_hint} (turno {self.paso_actual})"
                )
                agente.decir(fallback_msg, pensamiento=pensamiento)

            # 4. EJECUCIÓN FÍSICA (OBLIGATORIO)
            # Si la IA no sugiere una acción física, generar un fallback basado en necesidades
            if not accion_dict:
                try:
                    tipo_eval = agente._evaluar_tipo_accion_necesidades()
                except Exception:
                    tipo_eval = "FREE_CHOICE"

                if tipo_eval == "SURVIVAL":
                    if agente.inventario.get("comida", 0) > 0:
                        accion_dict = {"tipo": "comer", "nombre": "COMER", "parametros": {}, "argumentos": {}}
                    else:
                        accion_dict = {"tipo": "recolectar", "nombre": "RECOLECTAR", "parametros": {}, "argumentos": {}}

                elif tipo_eval == "SOCIAL_REQUIRED":
                    # Priorizar interacción cara a cara para satisfacer necesidad social
                    cercanos = [a for a in self.agentes if a.unique_id != agente.unique_id and abs(a.x - agente.x) <= 2 and abs(a.y - agente.y) <= 2]
                    if cercanos:
                        target = random.choice(cercanos)
                        accion_dict = {"tipo": "socializar", "nombre": "SOCIALIZAR", "parametros": {"mensaje": "Hola"}, "argumentos": {}, "objetivo": target.unique_id}
                    else:
                        accion_dict = {"tipo": "recolectar", "nombre": "RECOLECTAR", "parametros": {}, "argumentos": {}}

                elif tipo_eval == "INTELLECTUAL":
                    accion_dict = {"tipo": "investigar", "nombre": "INVESTIGAR", "parametros": {}, "argumentos": {}}

                else:  # FREE_CHOICE
                    accion_dict = {"tipo": "explorar", "nombre": "EXPLORAR", "parametros": {}, "argumentos": {}}

            # Ejecutar la acción física y notificar callbacks
            if accion_dict:
                action_name = accion_dict.get("nombre") or accion_dict.get("tipo") or "ACCION"
                if getattr(self, "realtime_event_callback", None):
                    try:
                        self._emit_realtime_event(
                            "action_event",
                            {
                                "agent_id": agente.unique_id,
                                "step": self.paso_actual,
                                "status": "start",
                                "action_name": action_name,
                            },
                        )
                    except Exception:
                        pass

                try:
                    print(f"🔍 [DEBUG] Ejecutando accion {action_name} para {agente.unique_id}")
                    agente.ejecutar_accion_final(accion_dict)
                    print(f"✅ [DEBUG] Accion {action_name} finalizada para {agente.unique_id}")
                except Exception as e:
                    # Registrar pero no abortar el turno
                    self.log(f"❌ Error ejecutando acción {action_name} para {agente.unique_id}: {e}", categoria="error")

                if getattr(self, "realtime_event_callback", None):
                    try:
                        self._emit_realtime_event(
                            "action_event",
                            {
                                "agent_id": agente.unique_id,
                                "step": self.paso_actual,
                                "status": "done",
                                "action_name": action_name,
                            },
                        )
                    except Exception:
                        pass

            # 5. ACCIÓN SOCIAL (OBLIGATORIA)
            # Forzar al menos una acción social por turno (post/like/comment/follow)
            try:
                if hasattr(agente, "social_force_action"):
                    agente.social_force_action(self.paso_actual)
                else:
                    # Fallback al comportamiento automático existente
                    agente._ejecutar_accion_social_automatica(self.paso_actual)
            except Exception as e:
                self.log(f"⚠️ Error en acción social forzada de {agente.unique_id}: {e}", categoria="sistema")

            # 6. HEARTBEAT Y MEMORIA PERSISTENTE (SOLICITUD USUARIO)
            # El heartbeat procesa impulsos, propósitos y reflexiones internas periódicas
            if hasattr(agente, "heartbeat_mundo") and agente.heartbeat_mundo:
                try:
                    # El heartbeat puede generar insights o nuevos impulsos basados en el alma y memoria
                    insights = agente.heartbeat_mundo.heartbeat(
                        self.paso_actual, 
                        alma=getattr(agente, "alma", None),
                        memoria=getattr(agente, "memoria_persistente", None)
                    )
                    
                    # Si el heartbeat generó una reflexión importante, registrarla como memoria episódica
                    if insights.get("reflexion") and hasattr(agente, "memoria_persistente") and agente.memoria_persistente:
                        agente.memoria_persistente.guardar_episodica(
                            descripcion=f"Reflexión interna: {insights['reflexion']}",
                            turno=self.paso_actual,
                            importancia=0.4,
                            emociones=["reflexivo"]
                        )
                except Exception as e:
                    self.log(f"⚠️ Error en heartbeat de {agente.unique_id}: {e}", categoria="sistema")

            # 7. LIMPIEZA DE ESTADO DE TURNO
            agente.ultimo_mensaje_recibido = None

    def _prepare_control_round(self):
        """Inicializa un ciclo controlado por el Arquitecto: incrementa paso y marca agentes pendientes."""
        with self.lock:
            if getattr(self, "_control_round_active", False):
                return

            agentes_vivos = [a for a in self.agentes if a.esta_vivo]
            agentes_activos = agentes_vivos

            # Incrementar paso y tareas previas al turno
            self.paso_actual += 1
            self.grupos_creados_este_paso = 0
            self._control_pending_agents = set(a.unique_id for a in agentes_activos)
            self._control_round_active = True

            # Pre-turn tasks
            self._procesar_economia()
            self.weather_timer += 1
            if self.weather_timer >= self.weather_duration:
                self._cambiar_clima()
            self._procesar_misiones_activas()
            self._actualizar_instituciones()
            self._procesar_asambleas()
            self._generar_eventos_aleatorios()
            # Procesar eventos emergentes (sequías, saberes, tensiones)
            if self.sistema_eventos:
                try:
                    self.sistema_eventos.procesar_turno()
                except Exception as _ee:
                    self.log(f"⚠️ Error en SistemaEventosEmergentes: {_ee}", categoria="sistema")

            hora = (
                self.time_engine.get_hora_simulada(self.paso_actual)
                if getattr(self, "time_engine", None)
                else (12 + (self.paso_actual // 5)) % 24
            )
            self.log(
                f"⏰ [TIME ENGINE][CONTROL] Paso {self.paso_actual}: {len(agentes_activos)}/{len(agentes_vivos)} agentes pendientes de acción. Hora simulada: {hora}:00",
                categoria="sistema",
            )

            # Notificar al frontend que comenzó un nuevo ciclo controlado
            if self.state_change_callback:
                try:
                    self.state_change_callback()
                except Exception:
                    pass

    def _mark_control_agent_done(self, agent_id):
        """Marca que un agente completó su acción en el ciclo controlado.

        Si todos los agentes pendientes completaron su acción, finaliza el ciclo.
        """
        with self.lock:
            pending = getattr(self, "_control_pending_agents", set()) or set()
            if agent_id in pending:
                pending.discard(agent_id)
                self.log(
                    f"🎮 [CONTROL] Agente {agent_id} completó su acción (restan {len(pending)})",
                    categoria="sistema",
                )
            else:
                self.log(
                    f"⚠️ [CONTROL] Agente {agent_id} reportado como completado pero no estaba pendiente.",
                    categoria="sistema",
                )
            self._control_pending_agents = pending

            if not pending:
                # Todos completaron: finalizar el ciclo controlado
                self._complete_control_round()

    def _complete_control_round(self):
        """Ejecuta la lógica posterior al ciclo controlado (formación de grupos, economía, guardado, misiones)."""
        with self.lock:
            # Notificar cambios de estado
            if self.state_change_callback and (
                self.paso_actual == 1 or self.paso_actual % 2 == 0
            ):
                try:
                    self.state_change_callback()
                except Exception:
                    pass

            # Lógica de formación de grupos al final del turno
            if self.paso_actual % 5 == 0:
                self.log(
                    "📢 [SISTEMA] Evaluando formación de grupos sociales...",
                    categoria="sistema",
                )
                self.formar_grupos()
                self.asignar_roles_consenso()
                self.evaluar_evolucion_civilizaciones()

            # Economía global (registro)
            self.actualizar_economia()

            # Guardado periódico
            if (
                self.db_active
                and self.user_id
                and self.paso_actual % self.autosave_interval == 0
            ):
                try:
                    self.guardar_estado()
                except Exception:
                    pass

            # Verificar misiones
            self.misiones_completadas_este_turno = self.sistema_misiones.verificar_misiones(
                self, self.user_id or "default"
            )
            if self.misiones_completadas_este_turno:
                for mision_completada in self.misiones_completadas_este_turno:
                    self.log(
                        f"🎉 ¡MISIÓN COMPLETADA! {mision_completada['titulo']}",
                        categoria="mision_completada",
                    )

            # Limpiar mensaje global del arquitecto
            self.mensaje_global_arquitecto = None

            # Reset control flags
            self._control_round_active = False
            self._control_pending_agents = set()

            # Notificar estado final del turno
            if self.state_change_callback:
                try:
                    self.state_change_callback()
                except Exception:
                    pass

    def _procesar_economia(self):
        """Ajusta las variables macroeconómicas del mundo en cada paso."""
        # Fluctuación del precio de recursos basada en la abundancia total
        recursos_totales = sum(a.recursos for a in self.agentes)
        if len(self.agentes) > 0:
            avg_rec = recursos_totales / len(self.agentes)
            # Si hay pocos recursos, el precio sube (inflación)
            target_price = max(0.5, 5.0 - (avg_rec / 20.0))
            self.precio_recurso_actual = (self.precio_recurso_actual * 0.9) + (
                target_price * 0.1
            )

        # Actualización del índice bursátil (fluctuación aleatoria coherente con el estado del mundo)
        cambio = random.uniform(-2.0, 2.0)
        # Bonus por paz o penalización por tensión/hambre (simulado)
        hambre_promedio = sum(
            a.necesidades.get("alimento", 10) for a in self.agentes
        ) / max(1, len(self.agentes))
        if hambre_promedio < 3.0:
            cambio -= 1.0  # El mercado sufre si hay hambre

        self.economia["indice_bursatil"] = max(
            10.0, self.economia["indice_bursatil"] + cambio
        )
        self.economia["precio_recurso"] = self.precio_recurso_actual
        # Actualizar el total de dinero circulante a partir de los saldos actuales de los agentes
        try:
            self.economia["total_dinero"] = round(sum(getattr(a, "dinero", 0) for a in self.agentes), 2)
        except Exception:
            # En caso de error no romper la simulación; mantener valor previo
            pass

    def _cambiar_clima(self):
        """Gestiona la transición de estados climáticos dinámicos."""
        self.weather_timer = 0
        self.weather_duration = random.randint(15, 40)

        posibles = [
            WeatherType.SUNNY,
            WeatherType.RAINY,
            WeatherType.STORM,
            WeatherType.FOGGY,
            WeatherType.HEATWAVE,
        ]
        # Probabilidades basadas en el clima actual (persistencia)
        nueva_weather = random.choice(posibles)

        self.weather = nueva_weather
        self.log(
            f"☁️ [CLIMA] El tiempo ha cambiado a {self.weather}",
            categoria="sistema",
        )
        self.notificar_cambio_estado()

    def _procesar_misiones_activas(self):
        """Paso intermedio para lógica de misiones compleja si es necesario."""
        pass  # La mayor parte se maneja en el verificador de SistemaMisiones
    def _actualizar_instituciones(self):
        """Ciclo de mantenimiento para instituciones formalizadas."""
        for inst_id, inst in list(self.instituciones.items()):
            # Por ejemplo, hospitales curan agentes en su tile
            if inst.tipo == "Hospital":
                tile = self.mapa[inst.x][inst.y]
                for agente in self.agentes:
                    if agente.x == inst.x and agente.y == inst.y:
                        if agente.necesidades.get("salud", 10) < 9.0:
                            agente.necesidades["salud"] = min(
                                10.0, agente.necesidades.get("salud", 0) + 0.5
                            )

            # Universidades otorgan XP pasiva
            if inst.tipo == "Universidad":
                for agente in self.agentes:
                    if agente.x == inst.x and agente.y == inst.y:
                        agente.experiencia["ingenieria"] = (
                            agente.experiencia.get("ingenieria", 0) + 0.05
                        )

            def _maybe_level_institution(self, inst):
                """Incrementa el nivel de una institución si alcanza los puntos requeridos.

                Regla simple: se requiere `100 * nivel_actual` puntos para subir al siguiente nivel.
                Consumimos los puntos utilizados para subir (puntos hacia el siguiente nivel).
                """
                try:
                    if not hasattr(inst, "puntos"):
                        inst.puntos = 0.0
                    leveled = False
                    # Mientras haya puntos suficientes para el siguiente nivel, subir
                    while inst.puntos >= 100 * inst.nivel:
                        inst.puntos -= 100 * inst.nivel
                        inst.nivel += 1
                        leveled = True
                        try:
                            self.log(f"🏛️ [INSTITUCIÓN] '{inst.nombre}' alcanzó nivel {inst.nivel}", categoria="sistema")
                        except Exception:
                            pass
                    if leveled and getattr(self, "db_active", False) and getattr(self, "db", None):
                        try:
                            self.db.save_institution(inst, self.user_id)
                        except Exception:
                            pass
                except Exception as e:
                    try:
                        self.log(f"❌ Error al actualizar nivel de institución {getattr(inst,'id','?')}: {e}", categoria="error")
                    except Exception:
                        pass

    def _procesar_asambleas(self):
        """
        Avanza los ciclos de debate y votación en las asambleas activas.
        REGLA: Procesamiento secuencial y obligatorio (uno por uno).
        """
        if not self.asambleas_globales:
            self.asamblea_bloqueante_activa = False
            return

        for asamblea in self.asambleas_globales:
            if asamblea["estado"] == "DEBATE":
                asamblea["pasos_restantes"] -= 1
                if asamblea["pasos_restantes"] <= 0:
                    asamblea["estado"] = "VOTACION"
                    self.asamblea_bloqueante_activa = True
                    asamblea["agente_turno_idx"] = 0
                    asamblea["participantes_votos"] = {} # agent_id: voto (bool)
                    self.log(
                        f"🗳️ [ASAMBLEA] Se abre el periodo de votación OBLIGATORIA para: {asamblea['tema']}",
                        categoria="consenso",
                    )

            elif asamblea["estado"] == "VOTACION":
                # Seleccionar el agente actual que debe votar
                agentes_activos = [a for a in self.agentes if a.esta_vivo]
                if not agentes_activos:
                    asamblea["estado"] = "RECHAZADA"
                    continue

                # Saltar automáticamente agentes que ya votaron para avanzar rápido
                idx = asamblea.get("agente_turno_idx", 0)
                while idx < len(agentes_activos) and agentes_activos[idx].unique_id in asamblea["participantes_votos"]:
                    idx += 1
                
                asamblea["agente_turno_idx"] = idx

                if idx < len(agentes_activos):
                    agente_actual = agentes_activos[idx]
                    
                    # Forzar al agente a deliberar su voto si no tiene un plan de usuario
                    self.log(f"⚖️ [VOTACION] Turno del agente {agente_actual.unique_id} para votar sobre '{asamblea['tema']}' ({idx+1}/{len(agentes_activos)})", categoria="consenso")
                    
                    # El agente decide su voto basado en su personalidad y el tema
                    voto = None
                    if getattr(self, "cerebro_llm", None):
                        try:
                            opinion, pensamiento = self.cerebro_llm.generar_debate_consenso(
                                agente_actual, [], fase="votacion", 
                                contexto_extra=f"Debes decidir tu VOTO FINAL sobre la propuesta: '{asamblea['tema']}'. Argumenta brevemente y termina diciendo CLARAMENTE 'Voto: SI' o 'Voto: NO'."
                            )
                            # Hacer que el agente diga su opinión en la simulación
                            agente_actual.decir(opinion, pensamiento=pensamiento, global_broadcast=True)
                            opinion_lower = opinion.lower()
                            if "voto: si" in opinion_lower or "voto si" in opinion_lower or "apruebo" in opinion_lower or "a favor" in opinion_lower:
                                voto = True
                            elif "voto: no" in opinion_lower or "voto no" in opinion_lower or "rechazo" in opinion_lower or "en contra" in opinion_lower:
                                voto = False
                            else:
                                # Fallback si no fue claro, asume SI por amabilidad
                                interes = random.random()
                                voto = interes > (1.0 - agente_actual.personalidad.get("amabilidad", 0.5))
                        except Exception as e:
                            self.log(f"⚠️ Error LLM en votación de {agente_actual.unique_id}: {e}", categoria="error")

                    if voto is None:
                        interes = random.random()
                        voto = interes > (1.0 - agente_actual.personalidad.get("amabilidad", 0.5))
                    
                    asamblea["participantes_votos"][agente_actual.unique_id] = voto
                    if voto: asamblea["votos_si"] += 1
                    else: asamblea["votos_no"] += 1
                    
                    self.log(f"🗳️ Agent {agente_actual.unique_id} ha votado: {'SÍ' if voto else 'NO'}", categoria="consenso")
                    asamblea["agente_turno_idx"] = idx + 1
                else:
                    # Todos han votado: Finalizar votación
                    si = asamblea["votos_si"]
                    no = asamblea["votos_no"]
                    
                    # Sincronizar votos con la propuesta original
                    propuestas = self.facciones_leyes.get("propuestas", [])
                    ley = next((p for p in propuestas if str(p.get("id")) == str(asamblea.get("ley_id"))), None)
                    if ley:
                        ley["votos_si"] = si
                        ley["votos_no"] = no
                        if asamblea.get("db_id") and not ley.get("db_id"):
                            ley["db_id"] = asamblea.get("db_id")

                    if si > no:
                        asamblea["estado"] = "APROBADA"
                        self.log(f"✅ [CONSENSO] Propuesta APROBADA por mayoría ({si} vs {no}): {asamblea['tema']}", categoria="consenso")
                        self._aplicar_ley(asamblea)
                    else:
                        asamblea["estado"] = "RECHAZADA"
                        if ley: ley["estado"] = "rechazada"
                        self.log(f"❌ [CONSENSO] Propuesta RECHAZADA ({si} vs {no}): {asamblea['tema']}", categoria="consenso")
                    
                    # Marcar explícitamente como finalizada para asegurar su eliminación
                    asamblea["estado"] = "FINALIZADA"
                    asamblea["agente_turno_idx"] = 0

        # Actualizar flag de bloqueo global: solo si hay asambleas en estado VOTACION
        self.asamblea_bloqueante_activa = any(
            a.get("estado") == "VOTACION" for a in self.asambleas_globales
        )

        # Limpiar asambleas terminadas de la lista activa
        self.asambleas_globales = [
            a for a in self.asambleas_globales if a.get("estado") in ["DEBATE", "VOTACION"]
        ]

    def _aplicar_ley(self, asamblea: dict):
        """Aplica los efectos de una ley aprobada a los agentes y al mundo."""
        # 1. Buscar la ley correspondiente en propuestas
        propuestas = self.facciones_leyes.get("propuestas", [])
        ley = next((p for p in propuestas if str(p.get("id")) == str(asamblea.get("ley_id"))), None)
        if not ley:
            self.log(f"⚠️ Ley no encontrada para asamblea {asamblea.get('id')}", categoria="error")
            return

        contenido = ley.get("contenido", "").lower()
        titulo = ley.get("titulo", "").lower()
        alcance = ley.get("alcance", "local")
        grupo_id = ley.get("grupo_id")

        # 2. Determinar tipo de ley por palabras clave
        tipo = "general"
        if any(kw in contenido or kw in titulo for kw in ["econom", "impuesto", "dinero", "recurso", "cost", "precio", "subsidio", "tributo", "salario"]):
            tipo = "economica"
        elif any(kw in contenido or kw in titulo for kw in ["salud", "educ", "social", "felicidad", "bienestar", "comunidad", "sanidad", "pension", "jubilacion"]):
            tipo = "social"
        elif any(kw in contenido or kw in titulo for kw in ["militar", "guerra", "defensa", "ataque", "ejército", "seguridad", "armada"]):
            tipo = "militar"
        elif any(kw in contenido or kw in titulo for kw in ["ambiente", "ecol", "naturaleza", "refugio", "parque"]):
            tipo = "ambiental"

        # 3. Seleccionar agentes afectados
        agentes_objetivo = [a for a in self.agentes if a.esta_vivo and (alcance == "global" or a.grupo_id == grupo_id)]

        # 4. Aplicar efectos por tipo a cada agente
        for agente in agentes_objetivo:
            if tipo == "economica":
                # Distinguir entre impuesto (reduce) y subsidio (aumenta)
                if "impuesto" in contenido or "tributo" in contenido:
                    reduction = random.randint(5, 10)
                    agente.dinero = max(0, getattr(agente, "dinero", 0) - reduction)
                else:
                    incremento = random.randint(5, 15)
                    agente.dinero = getattr(agente, "dinero", 0) + incremento
            elif tipo == "social":
                agente.necesidades["social"] = min(10.0, agente.necesidades.get("social", 5.0) + 1.0)
                agente.reputacion = min(1.0, getattr(agente, "reputacion", 0.5) + 0.05)
                agente.capital_social = min(100, getattr(agente, "capital_social", 10) + 5)
            elif tipo == "militar":
                # Aumentar rango (poder en combate)
                agente.rango = getattr(agente, "rango", 1.0) + 0.5
            elif tipo == "ambiental":
                agente.necesidades["salud"] = min(10.0, agente.necesidades.get("salud", 5.0) + 0.5)
            else:  # general
                agente.capital_social = min(100, getattr(agente, "capital_social", 10) + 2)

        # 5. Efectos globales (una sola vez, no por agente)
        if alcance == "global":
            if tipo == "economica":
                self.COSTO_EXPANSION = max(100, int(self.COSTO_EXPANSION * 0.95))
                self.log(f"📉 [ECONOMÍA] Costo de expansión reducido a {self.COSTO_EXPANSION} MC por ley aprobada.", categoria="economia")
            elif tipo == "militar":
                self.precio_recurso_actual = round(self.precio_recurso_actual * 1.15, 2)
                self.log(f"⚔️ [GUERRA] Precios de recursos subieron a {self.precio_recurso_actual} MC por ley militar.", categoria="economia")
            elif tipo == "social":
                for a in self.agentes:
                    if a.esta_vivo:
                        a.reputacion = min(1.0, getattr(a, "reputacion", 0.5) + 0.02)

        # 6. Marcar ley como aprobada
        ley["estado"] = "aprobada"
        self.log(f"✅ [LEY APROBADA] '{ley.get('titulo')}' ({tipo}) aplicada a {len(agentes_objetivo)} agentes.", categoria="consenso")

    def _procesar_elecciones_vocero(self):
        """Procesa elecciones de vocero cada ELECCION_FRECUENCIA pasos."""
        # Solo procesar cada ciertos pasos
        if (self.paso_actual - getattr(self, 'ultima_eleccion_paso', -100)) < self.ELECCION_FRECUENCIA:
            return
        
        self.ultima_eleccion_paso = self.paso_actual
        
        # Asegurar que existe el dict de candidatos
        if not hasattr(self, 'candidatos_vocero'):
            self.candidatos_vocero = {}
        
        for grupo_id, candidatos in list(self.candidatos_vocero.items()):
            if not candidatos:
                continue
            
            # Obtener miembros vivos de la facción
            miembros = [a for a in self.agentes if a.grupo_id == grupo_id and a.esta_vivo]
            if len(miembros) < 3:
                self.log(f"⚠️ [ELECCIÓN] Facción {grupo_id} tiene menos de 3 miembros. No se puede elegir vocero.", categoria="consenso")
                continue
            
            self.log(f"🗳️ [ELECCIÓN] Iniciando votación para vocero de facción {grupo_id}", categoria="consenso")
            
            # Votación: cada miembro vota por un candidato (basado en afinidad + reputación)
            votos = defaultdict(int)
            for m in miembros:
                # Calcular afinidad con cada candidato
                afinidades = {}
                for cand_id in candidatos:
                    cand = self.get_agent_by_id(cand_id)
                    if not cand or not cand.esta_vivo:
                        continue
                    # Afinidad base + reputación del candidato
                    afinidad = m.memoria.obtener_fuerza(cand_id) if hasattr(m.memoria, 'obtener_fuerza') else 0
                    afinidad += getattr(cand, 'reputacion', 0.5) * 10
                    afinidades[cand_id] = afinidad
                
                if afinidades:
                    mejor = max(afinidades, key=afinidades.get)
                    votos[mejor] += 1
            
            # Determinar ganador
            if votos:
                ganador_id = max(votos, key=votos.get)
                ganador = self.get_agent_by_id(ganador_id)
                if ganador and ganador.esta_vivo:
                    # Asignar rol de vocero
                    ganador.rol = "Vocero"
                    civ = self.civilizaciones.get(grupo_id)
                    if civ:
                        civ.vocero_id = ganador_id
                    
                    nombre_civ = civ.nombre if civ else grupo_id
                    self.log(
                        f"👑 [ELECCIÓN] {ganador.unique_id} ha sido elegido vocero de {nombre_civ} con {votos[ganador_id]} votos.",
                        categoria="consenso"
                    )
                    
                    # Resetear roles de otros miembros (todos son 'Miembro' excepto el vocero)
                    for m in miembros:
                        if m.unique_id != ganador_id:
                            m.rol = "Miembro"
                else:
                    self.log(f"⚠️ [ELECCIÓN] El ganador {ganador_id} no está disponible.", categoria="error")
            else:
                self.log(f"❌ [ELECCIÓN] No hubo votos válidos en facción {grupo_id}", categoria="error")
            
            # Limpiar candidatos para próxima elección
            self.candidatos_vocero[grupo_id] = []

    def _simultaneous_movement_phase(self, max_steps: int = 2):
        """
        Reubica todos los agentes simultáneamente hasta `max_steps` casillas.

        Criterios (prioritarios):
          1) Avanzar hacia `agente.objetivo_movimiento` si está fijado.
          2) Acercarse a compañeros de `grupo_id` si no hay ninguno en radio 3.
          3) Movimiento aleatorio (exploración) como fallback.

        La fase intenta resolver conflictos por posición permitiendo intercambios
        cuando ambos agentes se mueven, y garantizando que al final no haya
        dos agentes en la misma casilla.
        """
        try:
            if not getattr(self, "mapa", None):
                return

            filas = len(self.mapa)
            cols = len(self.mapa[0]) if filas > 0 else 0
            if filas == 0 or cols == 0:
                return

            agentes = [a for a in self.agentes if a.esta_vivo]
            if not agentes:
                return

            deltas = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]

            def _step_toward(ax, ay, tx, ty):
                nx, ny = ax, ay
                dx = tx - ax
                dy = ty - ay
                if abs(dx) >= abs(dy) and dx != 0:
                    nx += 1 if dx > 0 else -1
                elif dy != 0:
                    ny += 1 if dy > 0 else -1
                elif dx != 0:
                    nx += 1 if dx > 0 else -1
                nx = max(0, min(nx, filas - 1))
                ny = max(0, min(ny, cols - 1))
                return nx, ny

            # Mapa de posiciones actuales -> agente
            pos_to_agent = {(a.x, a.y): a for a in agentes}

            for step in range(max_steps):
                # Calcular destino deseado de cada agente para este subpaso
                desired = {}
                for a in agentes:
                    if not a.esta_vivo:
                        continue

                    # Prioridad 1: objetivo explícito
                    if getattr(a, "objetivo_movimiento", None):
                        ox, oy = a.objetivo_movimiento
                        nx, ny = _step_toward(a.x, a.y, ox, oy)
                        # Validar territorio
                        tile = self.mapa[nx][ny]
                        owner = getattr(tile, 'owner_civ_id', None)
                        if owner and owner != a.grupo_id:
                             desired[a.unique_id] = (a.x, a.y) # Bloqueado
                        else:
                             desired[a.unique_id] = (nx, ny)
                        continue

                    # Prioridad 2: acercarse a compañeros de grupo si están lejos
                    if a.grupo_id:
                        mates = [m for m in agentes if m.unique_id != a.unique_id and m.grupo_id == a.grupo_id]
                        if mates:
                            cercano = any(abs(m.x - a.x) <= 3 and abs(m.y - a.y) <= 3 for m in mates)
                            if not cercano:
                                mate = min(mates, key=lambda m: abs(m.x - a.x) + abs(m.y - a.y))
                                nx, ny = _step_toward(a.x, a.y, mate.x, mate.y)
                                # Validar territorio
                                tile = self.mapa[nx][ny]
                                owner = getattr(tile, 'owner_civ_id', None)
                                if owner and owner != a.grupo_id:
                                    desired[a.unique_id] = (a.x, a.y)
                                else:
                                    desired[a.unique_id] = (nx, ny)
                                continue

                    # Fallback: movimiento aleatorio corto
                    random.shuffle(deltas)
                    found_fallback = False
                    for ddx, ddy in deltas:
                        nx = max(0, min(a.x + ddx, filas - 1))
                        ny = max(0, min(a.y + ddy, cols - 1))
                        tile = self.mapa[nx][ny]
                        owner = getattr(tile, 'owner_civ_id', None)
                        if not owner or owner == a.grupo_id:
                            desired[a.unique_id] = (nx, ny)
                            found_fallback = True
                            break
                    
                    if not found_fallback:
                        desired[a.unique_id] = (a.x, a.y)

                # Resolver conflictos: agrupar reclamaciones por posición
                claims = defaultdict(list)
                for aid, pos in desired.items():
                    claims[pos].append(aid)

                reserved = set()
                assigned = {}

                # Primera pasada: posiciones únicas donde el ocupante actual se va o está vacía
                for pos, aids in claims.items():
                    if len(aids) == 1:
                        aid = aids[0]
                        agent = next((x for x in agentes if x.unique_id == aid), None)
                        if not agent:
                            continue
                        occupant = pos_to_agent.get(pos)
                        occupant_moves_away = False
                        if occupant:
                            occ_des = desired.get(occupant.unique_id)
                            if occ_des and occ_des != (occupant.x, occupant.y):
                                occupant_moves_away = True
                        if occupant is None or occupant_moves_away:
                            assigned[aid] = pos
                            reserved.add(pos)

                # Segunda pasada: resolver el resto de reclamaciones de forma estable
                for pos, aids in claims.items():
                    # Si ya fue atendida, saltar
                    if any(aid in assigned for aid in aids):
                        continue
                    # Aleatorizar orden para evitar sesgos
                    random.shuffle(aids)
                    for aid in aids:
                        if aid in assigned:
                            continue
                        agent = next((x for x in agentes if x.unique_id == aid), None)
                        if not agent:
                            continue
                        desired_pos = desired.get(aid, (agent.x, agent.y))
                        occupant = pos_to_agent.get(desired_pos)
                        occupant_stays = False
                        if occupant:
                            occ_des = desired.get(occupant.unique_id)
                            if occ_des == (occupant.x, occupant.y):
                                occupant_stays = True
                        if desired_pos not in reserved and not occupant_stays:
                            assigned[aid] = desired_pos
                            reserved.add(desired_pos)
                        else:
                            # Buscar alternativa adyacente libre
                            found = False
                            for ddx, ddy in deltas:
                                altx = max(0, min(agent.x + ddx, filas - 1))
                                alty = max(0, min(agent.y + ddy, cols - 1))
                                if (altx, alty) in reserved:
                                    continue
                                occ = pos_to_agent.get((altx, alty))
                                occ_des = desired.get(occ.unique_id) if occ else None
                                if not occ or occ_des != (occ.x, occ.y):
                                    assigned[aid] = (altx, alty)
                                    reserved.add((altx, alty))
                                    found = True
                                    break
                            if not found:
                                # No hay alternativa: quedarse
                                assigned[aid] = (agent.x, agent.y)
                                reserved.add((agent.x, agent.y))

                # Aplicar movimientos asignados (usar Agent.moverse para mantener efectos secundarios)
                for aid, pos in assigned.items():
                    agent = next((x for x in agentes if x.unique_id == aid), None)
                    if not agent:
                        continue
                    if pos != (agent.x, agent.y):
                        try:
                            agent.moverse(pos[0], pos[1])
                        except Exception as e:
                            self.log(f"⚠️ [MOVIMIENTO] Error moviendo {agent.unique_id}: {e}", categoria="error")

                # Actualizar mapa de posiciones antes del siguiente subpaso
                pos_to_agent = {(a.x, a.y): a for a in agentes}

            # Notificar un único cambio de estado al final de la fase
            self.notificar_cambio_estado()
        except Exception as e:
            self.log(f"⚠️ Error en fase de movimiento simultáneo: {e}", categoria="error")

    def detener(self):
        """Detiene la simulación de forma limpia y guarda el estado inmediatamente."""
        self._force_stop = True
        self._stopped = True
        # Guardar estado final inmediatamente antes de cerrar
        self.guardar_estado()
        logger.info(
            f"🛑 Simulación detenida y estado guardado para user_id={self.user_id}"
        )

    def _generar_eventos_aleatorios(self):
        """Desencadena eventos fortuitos para mantener el dinamismo."""
        if random.random() < 0.05:  # 5% de probabilidad por paso
            eventos = [
                (
                    "LLUVIA_DE_MANA",
                    "Han caído suministros del cielo.",
                    {"recursos": 50},
                ),
                (
                    "DESCUBRIMIENTO",
                    "Se ha encontrado una veta de minerales.",
                    {"mineral": 10},
                ),
                (
                    "MUESTRA_SOLAR",
                    "El sol brilla con fuerza, alegría general.",
                    {"felicidad": 1.0},
                ),
            ]
            tipo, desc, impacto = random.choice(eventos)
            self.trigger_event(tipo, desc, duracion=5, impacto=impacto)

    def actualizar_economia(self):
        """Registra el historial económico para gráficas."""
        self.economia["historial_indice"].append(self.economia["indice_bursatil"])
        self.economia["historial_precios"].append(self.economia["precio_recurso"])
        if len(self.economia["historial_indice"]) > 100:
            self.economia["historial_indice"].pop(0)
            self.economia["historial_precios"].pop(0)

    def evaluar_evolucion_civilizaciones(self):
        """Chequea si las civilizaciones cumplen hitos para avanzar."""
        for g_id, civ in self.civilizaciones.items():
            miembros = [a for a in self.agentes if a.grupo_id == g_id]
            recursos_totales = sum(m.recursos for m in miembros)
            
            # --- EVOLUCIÓN AUTOMÁTICA ---
            if civ.tipo == "PUEBLO" and len(miembros) >= 10:
                civ.tipo = "CIUDAD"
                self.log(
                    f"🏙️ [EVOLUCION] ¡El pueblo '{civ.nombre}' ha crecido y ahora es una CIUDAD!",
                    categoria="sistema",
                )
                self.notificar_cambio_estado()

            if len(miembros) >= 5 and recursos_totales > 500:
                # Podría desbloquear tecnologías o edificios
                pass

    def chequear_disolucion_grupos(self):
        """Disuelve grupos que llevan 5 turnos con menos de 3 miembros.

        La regla: si una civilización de tipo 'GRUPO' tiene menos de MIN_MIEMBROS
        durante LIMITE_TURNOS consecutivos, se disuelve y se eliminan sus registros.
        """
        MIN_MIEMBROS = 3
        LIMITE_TURNOS = 5

        for g_id, civ in list(self.civilizaciones.items()):
            # Aplicar sólo a grupos dinámicos/pequeños (tipo 'GRUPO')
            if getattr(civ, "tipo", "GRUPO") != "GRUPO":
                continue

            miembros = [a for a in self.agentes if a.grupo_id == g_id]
            num_miembros = len(miembros)

            if num_miembros < MIN_MIEMBROS:
                self.grupos_bajas_turnos[g_id] = self.grupos_bajas_turnos.get(g_id, 0) + 1
                # Si alcanza el límite, disolver
                if self.grupos_bajas_turnos[g_id] >= LIMITE_TURNOS:
                    # Limpiar referencias en los agentes
                    for m in miembros:
                        try:
                            m.grupo_id = None
                            m.civilizacion_id = None
                        except Exception:
                            pass

                    # Eliminar estructuras asociadas al grupo
                    self.civilizaciones.pop(g_id, None)
                    self.objetivos_grupos.pop(g_id, None)
                    self.grupos_dinamicos.pop(g_id, None)
                    try:
                        self.facciones_leyes.pop(g_id, None)
                    except Exception:
                        pass
                    # Borrar contador
                    self.grupos_bajas_turnos.pop(g_id, None)

                    self.log(
                        f"🧨 [DISOLUCIÓN] Grupo {g_id} disuelto tras {LIMITE_TURNOS} turnos con <{MIN_MIEMBROS} miembros.",
                        categoria="sistema",
                    )
                    # Emitir evento en tiempo real para frontend si hay callback
                    try:
                        payload = {
                            "event": "group_disbanded",
                            "group_id": g_id,
                            "group_name": getattr(civ, "nombre", None),
                            "turno_disolucion": getattr(self, "paso_actual", None),
                            "miembros": [m.unique_id for m in miembros],
                        }
                        self._emit_realtime_event("group_disbanded", payload)
                    except Exception:
                        pass
                    try:
                        self.notificar_cambio_estado()
                    except Exception:
                        pass
            else:
                # Resetear contador si vuelve a tener suficiente miembros
                if g_id in self.grupos_bajas_turnos:
                    self.grupos_bajas_turnos[g_id] = 0

    def step(self):
        """Avanza un paso en la simulación."""
        if getattr(self, "_stopped", False):
            return  # No procesar si la simulación fue detenida
        self.paso_actual += 1
        self.grupos_creados_este_paso = 0
        # Actualizar y disolver grupos que llevan demasiados turnos con pocos miembros
        try:
            self.chequear_disolucion_grupos()
        except Exception as e:
            self.log(f"⚠️ Error checando disolución de grupos: {e}", categoria="error")

        # Obtener agentes activos (vivos y no detenidos)
        agentes_vivos = [a for a in self.agentes if a.esta_vivo]
        agentes_activos = agentes_vivos  # Por ahora, todos los vivos están activos

        # Lógica económica y de tiempo
        self._procesar_economia()
        self.weather_timer += 1
        if self.weather_timer >= self.weather_duration:
            self._cambiar_clima()

        # Procesar misiones activas
        self._procesar_misiones_activas()

        # Actualizar instituciones
        self._actualizar_instituciones()

        # Procesar asambleas activas
        self._procesar_asambleas()
        
        # Procesar elecciones de vocero
        self._procesar_elecciones_vocero()

        # Generar eventos aleatorios
        self._generar_eventos_aleatorios()

        hora = (
            self.time_engine.get_hora_simulada(self.paso_actual)
            if getattr(self, "time_engine", None)
            else (12 + (self.paso_actual // 5)) % 24
        )
        self.log(
            f"⏰ [TIME ENGINE] Paso {self.paso_actual}: {len(agentes_activos)}/{len(agentes_vivos)} agentes activos. "
            f"Hora simulada: {hora}:00",
            categoria="sistema",
        )
        # === FIN OASIS ===

        # 2. Paso de los agentes
        if getattr(self, "asamblea_bloqueante_activa", False):
            # Durante una asamblea bloqueante, los agentes no actúan normalmente.
            # Solo procesamos mantenimiento vital básico.
            self.log("🗳️ [BLOQUEO] Simulación pausada por asamblea activa (Votación en curso).", categoria="sistema")
            for agente in self.agentes:
                if agente.esta_vivo:
                    agente.actualizar_necesidades()
        elif getattr(self, "modo_control_total", False):
            # En modo Control Total, los agentes no actúan por sí solos.
            # Solo procesamos mantenimiento vital básico.
            for agente in self.agentes:
                if agente.esta_vivo:
                    agente.actualizar_necesidades()
        else:
            # Modo autónomo normal
            # Mezclamos el orden para evitar sesgos de prioridad (Fase 4)
            agentes_turno = list(agentes_activos)
            random.shuffle(agentes_turno)
            for agente in agentes_turno:
                if getattr(self, "_force_stop", False):
                    break
                agente.step() # Usar el nuevo método step() del agente

                # Pausa de lectura entre agentes
                if hasattr(self, "ritmo") and self.ritmo > 0 and len(agentes_vivos) > 1:
                    time.sleep(self.ritmo)

        # 3. Integración Fase 4: Grupos, Economía y Métricas
        if self.paso_actual % 5 == 0:
            self.log(
                "📢 [SISTEMA] Evaluando formación de grupos sociales...",
                categoria="sistema",
            )
            self.formar_grupos()
            self.asignar_roles_consenso()
            self.evaluar_evolucion_civilizaciones()
            self.guardar_estado()
        
        self.actualizar_economia()
        
        # Guardar métricas para gráficos
        if self.agentes:
            recursos_totales = sum(getattr(a, "recursos", 0) for a in self.agentes)
            promedio_recursos = recursos_totales / len(self.agentes)
            self.datos.append({
                "paso": self.paso_actual,
                "recursos_promedio": promedio_recursos,
                "num_grupos": len(set(getattr(a, "grupo_id", None) for a in self.agentes if getattr(a, "grupo_id", None))),
                "gini": self.calcular_gini(),
                "felicidad": self.calcular_felicidad_promedio(),
            })

        # Notificar cambios de estado de forma throttled, no por cada agente
        if self.state_change_callback and (
            self.paso_actual == 1 or self.paso_actual % 2 == 0
        ):
            try:
                self.state_change_callback()
            except Exception:
                pass

        # Guardar estado persistente con menos frecuencia para evitar bloquear el loop.
        if (
            self.db_active
            and self.user_id
            and self.paso_actual % self.autosave_interval == 0
        ):
            self.guardar_estado()

        # Verificar misiones activas
        self.misiones_completadas_este_turno = self.sistema_misiones.verificar_misiones(
            self, self.user_id or "default"
        )
        if self.misiones_completadas_este_turno:
            for mision_completada in self.misiones_completadas_este_turno:
                self.log(
                    f"🎉 ¡MISIÓN COMPLETADA! {mision_completada['titulo']}",
                    categoria="mision_completada",
                )

        # === GENERACIÓN PERIÓDICA DE CRÓNICAS DEL HISTORIADOR ===
        # Si hay un historiador y hitos pendientes, generar una crónica cada 3 pasos o si hay varios hitos acumulados.
        try:
            if hasattr(self, "historia") and getattr(self.historia, "historiador_id", None):
                if getattr(self.historia, "hitos_pendientes", None):
                    if self.paso_actual % 3 == 0 or len(self.historia.hitos_pendientes) >= 3:
                        historiador_id = self.historia.historiador_id
                        historiador = next((a for a in self.agentes if a.unique_id == historiador_id), None)
                        resumen = self.historia.obtener_resumen_hitos()
                        agente_for_llm = historiador or SimpleNamespace(unique_id=historiador_id, identidad=SimpleNamespace(nombre=historiador_id))
                        titulo, contenido = cerebro_llm.generar_cronica(agente_for_llm, resumen, paso=self.paso_actual)
                        autor_nombre = getattr(historiador.identidad, "nombre", historiador_id) if historiador else historiador_id
                        # Escribir formalmente en la libreta de historia
                        try:
                            self.historia.escribir_entrada(self.paso_actual, titulo, contenido, historiador_id, categoria="historia")
                            self.log(f"📝 [HISTORIA] Historiador {autor_nombre} escribió crónica: {titulo}", categoria="historia")
                        except Exception as e:
                            self.log(f"⚠️ Error escribiendo entrada de historia: {e}", categoria="error")
                        # Publicar en el sistema de cronicas si existe
                        if hasattr(self, "sistema_cronicas"):
                            try:
                                ubic = None
                                if historiador and hasattr(historiador, "x") and hasattr(historiador, "y"):
                                    ubic = (getattr(historiador, "x", None), getattr(historiador, "y", None))
                                self.sistema_cronicas.publicar_cronica(
                                    autor_id=historiador_id,
                                    autor_nombre=autor_nombre,
                                    contenido=contenido,
                                    tipo=TipoCronica.HISTORIA,
                                    turno=self.paso_actual,
                                    faccion=getattr(historiador, "faccion", "") if historiador else "",
                                    ubicacion=ubic,
                                )
                            except Exception as e:
                                self.log(f"⚠️ Error publicando crónica en sistema_cronicas: {e}", categoria="error")
                        # Limpiar los hitos ya narrados
                        try:
                            self.historia.limpiar_hitos()
                        except Exception:
                            pass
                        if self.state_change_callback:
                            try:
                                self.state_change_callback()
                            except Exception:
                                pass
        except Exception as e:
            self.log(f"⚠️ Error generando crónica automática: {e}", categoria="error")

        # === GENERACIÓN PERIÓDICA DE MITOS CULTURALES ===
        # Cada 100 turnos, generar un mito basado en las leyendas actuales
        if self.paso_actual % 100 == 0 and hasattr(self, "sistema_cronicas"):
            try:
                from litellm import completion as litellm_completion

                # Construir prompt para el LLM
                leyendas = sorted(
                    self.sistema_cronicas.leyendas,
                    key=lambda c: c.resonancia,
                    reverse=True,
                )[:5]

                if leyendas:
                    contexto = "Leyendas que han marcado la historia de este mundo:\n\n"
                    for i, leyenda in enumerate(leyendas, 1):
                        contexto += f"{i}. [{leyenda.tipo.value}] {leyenda.autor_nombre}: {leyenda.contenido[:200]}...\n"
                    contexto += "\nBasado en estas leyendas, genera un mito cultural coherente que una estas narrativas en una historia épica que los agentes podrían compartir. Usa un tono mítico, profundo. Máximo 150 palabras."

                    # Llamar al LLM
                    model = getattr(cerebro_llm, "model", "gpt-3.5-turbo")
                    api_key = getattr(cerebro_llm, "api_key", None)
                    base_url = getattr(cerebro_llm, "base_url", None)

                    response = litellm_completion(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": "Eres un cronista mítico. Convierte leyendas en narrativas épicas que los agentes creen como verdad.",
                            },
                            {"role": "user", "content": contexto},
                        ],
                        max_tokens=300,
                        temperature=0.9,
                        **{"no-log": True},
                        api_key=api_key,
                        api_base=base_url,
                        extra_headers={
                            "HTTP-Referer": "http://localhost:8005",
                            "X-Title": "MundoIA Myths",
                        }
                        if base_url
                        else None,
                    )
                    mito = response.choices[0].message.content.strip()

                    if mito:
                        # Actualizar el lore global con el nuevo mito
                        if not hasattr(self, "lore") or not self.lore:
                            self.lore = mito
                        else:
                            self.lore += f"\n\n{mito}"
                        self.log(
                            f"📜 [MITO] Ha surgido una nueva narrativa cultural: {mito[:100]}...",
                            categoria="sistema",
                        )
                        if self.state_change_callback:
                            self.state_change_callback()
            except Exception as e:
                print(f"[MITOS] Error generando mito: {e}")

        # Ejecutar fase de reubicación simultánea al final del paso (máx. 2 casillas)
        try:
            self._simultaneous_movement_phase(max_steps=2)
        except Exception as e:
            self.log(f"⚠️ Error ejecutando movimiento simultáneo: {e}", categoria="error")

        # Limpiar mensaje global después de que todos los agentes lo hayan procesado en este paso
        self.mensaje_global_arquitecto = None

    def verificar_misiones(self):
        """
        [DEPRECATED] Este método es legacy.
        La verificación de misiones ahora la maneja self.sistema_misiones.verificar_misiones() llamado en step().
        """
        pass

    def puede_construir(self, agente, tipo):
        """Comprueba restricciones adicionales de construcción (ej: Centros de Descanso).
        Retorna (True, "") si es posible construir, o (False, mensaje) si no.
        """
        try:
            tipo_l = str(tipo).lower()
            # Solo aplicamos reglas especiales para Centros de Descanso
            if "centro de descanso" in tipo_l or tipo_l.strip() == "centro de descanso":
                if not getattr(self, "mapa", None):
                    return True, ""

                map_width = len(self.mapa)
                map_height = len(self.mapa[0]) if map_width > 0 else 0
                

                # Contar centros existentes escaneando el mapa (más robusto que infraestructura sólo)
                existing_centros = []
                for ix in range(map_width):
                    for iy in range(map_height):
                        tile = self.mapa[ix][iy]
                        for b in getattr(tile, "buildings", []) or []:
                            try:
                                if b.get("tipo") == "Centro de Descanso":
                                    existing_centros.append(b)
                            except Exception:
                                continue


                prox_limit = int(getattr(self, "CENTRO_DESCANSO_MIN_DISTANCE", 6))
                for e in existing_centros:
                    ex = int(e.get("x", 0))
                    ey = int(e.get("y", 0))
                    if abs(ex - agente.x) + abs(ey - agente.y) < prox_limit:
                        return False, f"Existe un Centro de Descanso cercano en ({ex},{ey})."

        except Exception as exc:
            # En caso de error conservador, permitir la construcción para no bloquear el juego
            try:
                self.log(f"⚠️ Error en puede_construir: {exc}", categoria="error")
            except Exception:
                pass

        return True, ""
        # """Verifica el progreso de las misiones activas."""
        # construcciones = {}
        # for edif in self.infraestructura:
        #     tipo = edif["tipo"]
        #     construcciones[tipo] = construcciones.get(tipo, 0) + 1
        #
        # total_dinero = sum(a.dinero for a in self.agentes)
        #
        # # self.misiones ya no existe directamente en ModeloRelacional
        # # for mision in self.misiones:
        # #     if mision.estado != "activa": continue
        # #
        # #     if mision.tipo == "construccion":
        # #         pass # Lógica movida a SistemaMisiones

    def construir_edificio(self, agente, tipo):
        """Permite a un agente construir una infraestructura basada en sus logros y experiencia."""
        config_edificios = {
            "Hospital": {
                "costo": {"dinero": 60, "recursos": 40, "madera": 5, "piedra": 2},
                "requisito": lambda a: (
                    a.profesion == "Médico" or a.experiencia.get("medicina", 0) >= 5
                ),
                "efecto": "Cura agentes cercanos cada turno.",
            },
            "Granja": {
                "costo": {"dinero": 30, "recursos": 20, "madera": 3},
                "requisito": lambda a: True,
                "efecto": "Genera recursos de alimento en el tile.",
            },
            "Centro de Recarga": {
                "costo": {"dinero": 50, "recursos": 40},
                "requisito": lambda a: a.experiencia.get("ingenieria", 0) >= 3,
                "efecto": "Restaura energía/recursos rápidamente.",
            },
            "Centro de Descanso": {
                "costo": {"dinero": 20, "recursos": 15},
                "requisito": lambda a: True,  # Básico
                "efecto": "Reduce el estrés y la necesidad de descanso.",
            },
            "Centro Comunitario": {
                "costo": {"dinero": 40, "recursos": 30},
                "requisito": lambda a: a.personalidad.get("amabilidad", 0.5) > 0.6,
                "efecto": "Mejora las relaciones sociales en el área.",
            },
            "Comisaría": {
                "costo": {"dinero": 50, "recursos": 35},
                "requisito": lambda a: (
                    a.profesion == "Guarda" or a.experiencia.get("combate", 0) >= 3
                ),
                "efecto": "Reduce la probabilidad de robos y aumenta la seguridad.",
            },
            "Universidad": {
                "costo": {"dinero": 150, "recursos": 100, "piedra": 10, "madera": 15},
                "requisito": lambda a: a.experiencia.get("ingenieria", 0) >= 4,
                "efecto": "Permite graduarse a los agentes y otorga XP pasiva.",
            },
            "Mina": {
                "costo": {"dinero": 80, "recursos": 40, "madera": 10},
                "requisito": lambda a: a.experiencia.get("ingenieria", 0) >= 4,
                "efecto": "Genera piedra y hierro en montañas.",
            },
            "Farmacia": {
                "costo": {"dinero": 40, "recursos": 20, "madera": 4},
                "requisito": lambda a: a.experiencia.get("medicina", 0) >= 3,
                "efecto": "Provee salud básica y medicinas.",
            },
        }

        # Búsqueda case-insensitive para mayor robustez con diferentes LLMs
        config = None
        tipo_final = tipo
        for k, v in config_edificios.items():
            if k.lower() == str(tipo).lower():
                config = v
                tipo_final = k
                break

        if not config:
            # Posibilidad de "inventar" un edificio si tiene alta curiosidad e ingeniería
            if (
                agente.experiencia.get("ingenieria", 0) >= 5
                and agente.personalidad.get("curiosidad", 0.5) > 0.8
            ):
                config_edificios[tipo] = {
                    "costo": {"dinero": 200, "recursos": 150},
                    "requisito": lambda a: True,
                    "efecto": "Edificio experimental con efectos únicos.",
                }
                config = config_edificios[tipo]
                tipo_final = tipo
            else:
                return (
                    False,
                    f"Tipo de edificio '{tipo}' no válido o requisitos de invención no cumplidos.",
                )

        tipo = tipo_final # Usar el nombre canónico


        tile = self.mapa[agente.x][agente.y]

        # Comprobar y ejecutar la construcción de forma atómica para evitar race-conditions
        with self.lock:
            ok, msg = self.puede_construir(agente, tipo)
            if not ok:
                return False, msg

            # Las comprobaciones preventivas de Centros de Descanso (proximidad y límite)
            # ya se realizaron en self.puede_construir(agente, tipo) arriba.
            # Se elimina este bloque redundante para evitar conflictos y aplicar el nuevo límite de 5.


            if tile.buildings:
                return False, "Ya hay un edificio en esta ubicación."

            if tile.terrain_type == TerrainType.WATER and tipo != "Puerto":
                return False, "No se puede construir en agua (requiere Puerto)."
            if tile.terrain_type == TerrainType.MOUNTAIN and tipo != "Mina":
                return False, "En las montañas solo se pueden construir Minas."

            config = config_edificios[tipo]
            if not config["requisito"](agente):
                return (
                    False,
                    f"No cumples los requisitos (XP/Profesión) para construir {tipo}.",
                )

            costo = config["costo"]
            # Si el agente tiene acciones de control pendientes, es un "Decreto Divino" y sale gratis
            es_decreto = getattr(agente, "_bajo_control_directo", False) or getattr(agente, "_ejecutando_decreto", False)

            if es_decreto:
                tiene_dinero = True
                tiene_recursos = True
                tiene_materiales = True
            else:
                tiene_dinero = agente.dinero >= costo.get("dinero", 0)
                tiene_recursos = agente.recursos >= costo.get("recursos", 0)
                tiene_materiales = True
                missing_material = ""

                for mat, req_cant in costo.items():
                    if mat not in ["dinero", "recursos"]:
                        if agente.inventario.get(mat, 0) < req_cant:
                            tiene_materiales = False
                            missing_material = mat
                            break

            if tiene_dinero and tiene_recursos and tiene_materiales:
                if not es_decreto:
                    agente.dinero -= costo.get("dinero", 0)
                    agente.recursos -= costo.get("recursos", 0)
                    # Consumir materiales
                    for mat, req_cant in costo.items():
                        if mat not in ["dinero", "recursos"]:
                            agente.inventario[mat] -= req_cant

                nuevo_edif = {
                    "id": f"EDIF-{len(self.infraestructura) + 1}",
                    "tipo": tipo,
                    "grupo_id": agente.grupo_id,
                    "constructor": agente.unique_id,
                    "paso_creacion": self.paso_actual,
                    "x": agente.x,
                    "y": agente.y,
                }
                self.infraestructura.append(nuevo_edif)
                tile.buildings.append(nuevo_edif)  # Add to tile
                self._map_dirty = True

                self.log(
                    f"🏗️ [CONSTRUCCION] Agente {agente.unique_id} ha construido un {tipo} en ({agente.x}, {agente.y})!",
                    categoria="sistema",
                )
                self.notificar_cambio_estado()
                return True, f"¡{tipo} construido con éxito!"

        missing_msg = "No tienes suficientes recursos o dinero."
        if not tiene_materiales:
            missing_msg = f"Faltan materiales: {missing_material} (Necesitas {costo.get(missing_material, 0)})"
        elif not tiene_dinero:
            missing_msg = f"Dinero insuficiente (Necesitas {costo.get('dinero', 0)} MC)"
        elif not tiene_recursos:
            missing_msg = f"Energía/Recursos insuficientes (Necesitas {costo.get('recursos', 0)})"

        return False, missing_msg

    def enviar_mensaje_arquitecto(self, mensaje, agente_id=None):
        """Envía un mensaje del Arquitecto (usuario) a uno o todos los agentes."""
        import time

        payload = {
            "emisor": "Arquitecto",
            "contenido": mensaje,
            "timestamp": time.time(),
        }

        if agente_id:
            # Mensaje privado
            target = next((a for a in self.agentes if a.unique_id == agente_id), None)
            if target:
                target.mensaje_arquitecto = payload
                self.log(
                    f"🤫 [DIVINO] Mensaje PRIVADO enviado al Agente {agente_id}.",
                    categoria="sistema",
                )
                return True, f"Mensaje enviado al Agente {agente_id}"
            return False, "Agente no encontrado"
        else:
            # Mensaje global (broadcast)
            for a in self.agentes:
                a.mensaje_arquitecto = payload
            self.log(
                f"📢 [DIVINO] El Arquitecto ha enviado un mensaje GLOBAL: '{mensaje}'",
                categoria="sistema",
            )
            return True, "Mensaje global enviado"

    def set_lore_and_seed(self, lore, seed):
        self.lore = lore
        self.seed = seed
        self.log(f"🌍 [MUNDO] Lore actualizado: {lore[:50]}...", categoria="sistema")

    def get_agent_by_id(self, agent_id):
        """Busca un agente por su ID único."""
        return next(
            (a for a in self.agentes if str(a.unique_id) == str(agent_id)), None
        )

    def trigger_event(self, tipo, descripcion, duracion=5, impacto=None):
        evento = {
            "tipo": tipo,
            "descripcion": descripcion,
            "paso_inicio": self.paso_actual,
            "pasos_restantes": duracion,
            "impacto": impacto or {},
        }
        self.eventos_activos.append(evento)
        self.log(
            f"🌪️ [EVENTO GLOBAL] ¡Ha comenzado: {tipo}! {descripcion}",
            categoria="sistema",
        )

        # Guardar en DB si está activa
        if self.db_active:
            query = "INSERT INTO eventos_globales (user_id, tipo, descripcion, paso_inicio, duracion, impacto) VALUES (%s, %s, %s, %s, %s, %s)"
            self.db.execute(
                query,
                (self.user_id, tipo, descripcion, self.paso_actual, duracion, Json(impacto or {})),
            )

    def buscar_edificio_para_necesidad(self, x, y, necesidad, radio=10):
        """
        Busca el edificio más cercano que supla una necesidad específica.
        Retorna (distancia, edificio_info, pos_x, pos_y) o None.
        """
        # Mapeo de necesidades a tipos de edificios
        mapa_necesidad_edificio = {
            "descanso": ["Centro de Descanso"],
            "salud": ["Hospital"],
            "alimento": ["Granja", "Mercado"],
            "social": ["Centro Comunitario", "Mercado"],
            "dinero": ["Mercado", "Banco"],
        }
        
        tipos_objetivo = mapa_necesidad_edificio.get(necesidad, [])
        if not tipos_objetivo:
            return None
            
        mejor = None
        min_dist = float('inf')
        
        # Buscar en el mapa dentro del radio
        for dx in range(-radio, radio + 1):
            for dy in range(-radio, radio + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < len(self.mapa) and 0 <= ny < len(self.mapa[0]):
                    tile = self.mapa[nx][ny]
                    if hasattr(tile, 'buildings') and tile.buildings:
                        for edif in tile.buildings:
                            if edif.get("tipo") in tipos_objetivo:
                                dist = abs(dx) + abs(dy)
                                if dist < min_dist:
                                    min_dist = dist
                                    mejor = (dist, edif, nx, ny)
        
        return mejor

    def spawn_agent(self, config=None):
        """Crea un nuevo agente con posición y atributos aleatorios."""
        from agents.identity_system import generar_identidad_inicial
        from agents.alma import generar_alma_inicial
        import uuid

        config = config or {}
        # Generar un ID más único y menos secuencial si no se provee uno
        agent_id = config.get("unique_id", f"ag_{uuid.uuid4().hex[:6]}")

        # Determinar posición aleatoria si no se especifica
        # Usamos el tamaño del mapa actual o 20 por defecto
        limit_x = self.mapa_size if hasattr(self, "mapa_size") else 20
        limit_y = self.mapa_size if hasattr(self, "mapa_size") else 20

        spawn_x = config.get("x", random.randint(0, limit_x - 1))
        spawn_y = config.get("y", random.randint(0, limit_y - 1))

        # Crear agente básico
        agente = Agente(
            unique_id=agent_id,
            modelo=self,
            recursos=config.get("recursos", 100),
            x=spawn_x,
            y=spawn_y,
        )

        # Inicializar alma e identidad con los datos correctos (Nombres Aleatorios)
        agente.alma = generar_alma_inicial(agente.personalidad, self.paso_actual)
        agente.identidad = generar_identidad_inicial(
            agente.alma.arquetipo.value, self.paso_actual
        )

        # Sincronizar nombre bidireccionalmente
        if agente.alma.nombre_propio:
            agente.identidad.nombre = agente.alma.nombre_propio
        else:
            agente.alma.nombre_propio = agente.identidad.nombre

        # Aplicar rol/profesión si se pasó en la configuración (compatibilidad 'rol'/'role')
        if isinstance(config, dict):
            if "rol" in config and config.get("rol"):
                agente.rol = config.get("rol")
            elif "role" in config and config.get("role"):
                agente.rol = config.get("role")

        self.agentes.append(agente)
        self.log(
            f"👤 [POBLACIÓN] Ha nacido {agente.identidad.nombre} en ({spawn_x}, {spawn_y})",
            categoria="sistema",
        )

        if self.db_active:
            self.db.save_agent(agente, self.user_id)

        # Notificar al frontend que existe un nuevo agente
        self.notificar_cambio_estado()

        return agente

    def crear_mision(
        self,
        titulo,
        descripcion,
        tipo="social",
        objetivo=None,
        recompensa=500,
        global_mission=True,
    ):
        """Crea una misión personalizada desde el modo Arquitecto."""
        mision_id = f"DIVINA-{random.randint(1000, 9999)}"

        # Extraer puntos de recompensa (soportar tanto int directo como dict)
        puntos = 500
        if isinstance(recompensa, dict):
            puntos = recompensa.get("puntos", recompensa.get("dinero_global", 500))
        elif isinstance(recompensa, (int, float)):
            puntos = int(recompensa)

        # Asegurar que el objetivo sea un diccionario válido para evitar NaNs en el frontend
        if not isinstance(objetivo, dict):
            objetivo = {"tipo": "especial", "cantidad": 1, "actual": 0}
        else:
            if "cantidad" not in objetivo:
                objetivo["cantidad"] = 1
            if "actual" not in objetivo:
                objetivo["actual"] = 0

        mision = Mision(
            id=mision_id,
            titulo=titulo,
            descripcion=descripcion,
            tipo=tipo,
            dificultad="media",
            objetivo=objetivo,
            recompensa_puntos=puntos,
            turno_inicio=self.paso_actual,
        )

        self.sistema_misiones.misiones_activas.append(mision)
        self.log(
            f"🎯 [DIVINO] Nueva misión encomendada: '{titulo}'", categoria="sistema"
        )

        if self.db_active:
            self.db.save_mission(mision, self.user_id)

        return True, f"Misión '{titulo}' creada"

    def gestionar_encuentro_facciones(self, agente_a, agente_b):
        """Gestiona la interacción cuando dos agentes de distintas facciones se encuentran."""
        id_a, id_b = agente_a.grupo_id, agente_b.grupo_id
        if not id_a or not id_b or id_a == id_b:
            return

        # Clave única para la relación entre estos dos grupos
        rel_key = tuple(sorted([id_a, id_b]))
        if rel_key not in self.relaciones_grupos:
            self.relaciones_grupos[rel_key] = 0.5  # Neutral inicial

        afinidad = self.relaciones_grupos[rel_key]

        # Probabilidad de cooperación basada en afinidad y personalidades
        prob_cooperar = (
            afinidad
            * (
                agente_a.personalidad["amabilidad"]
                + agente_b.personalidad["amabilidad"]
            )
            / 2
        )

        if random.random() < prob_cooperar:
            # --- COOPERACIÓN: Gesto de Buena Voluntad ---
            tipo_ayuda = random.choice(["recursos", "salud", "informacion"])
            if tipo_ayuda == "recursos" and agente_a.recursos > 20:
                donado = 10
                agente_a.recursos -= donado
                agente_b.recursos += donado
                self.log(
                    f"🤝 [DIPLOMACIA] Gesto de paz: {agente_a.unique_id} ({id_a}) donó recursos a {agente_b.unique_id} ({id_b}).",
                    categoria="social",
                )
                self.relaciones_grupos[rel_key] = min(1.0, afinidad + 0.05)
            elif tipo_ayuda == "salud" and agente_a.inventario["medicina"] > 0:
                agente_a.inventario["medicina"] -= 1
                agente_b.necesidades["salud"] = min(
                    10, agente_b.necesidades["salud"] + 2
                )
                self.log(
                    f"💊 [DIPLOMACIA] Auxilio médico: {agente_a.unique_id} ({id_a}) curó a un miembro de {id_b}.",
                    categoria="social",
                )
                self.relaciones_grupos[rel_key] = min(1.0, afinidad + 0.1)
        else:
            # --- TENSIÓN: Competencia por territorio ---
            if random.random() < 0.3:
                self.log(
                    f"⚠️ [TENSION] Encuentro frío entre patrullas de {id_a} y {id_b} en zona fronteriza.",
                    categoria="social",
                )
                self.relaciones_grupos[rel_key] = max(0.0, afinidad - 0.02)

    def log(
        self,
        mensaje,
        categoria="info",
        subtitulos=None,
        tts_text=None,
        pensamiento=None,
        privado_para=None,
        agente_id=None,
    ):
        """Envía un log al callback o a la terminal y lo guarda en el historial."""
        # Evitar recursividad infinita si el callback genera otro log
        if getattr(self, "_is_logging", False):
            return
        self._is_logging = True
        try:
            log_entry = {
                "paso": self.paso_actual,
                "mensaje": mensaje,
                "categoria": categoria,
                "subtitulos": subtitulos,
                "tts_text": tts_text,
                "pensamiento": pensamiento,
                "privado_para": privado_para,
                "agente_id": agente_id,
            }
            with self.lock:
                self.historial_logs.append(log_entry)
                if len(self.historial_logs) > 1000:
                    self.historial_logs.pop(0)

            # PERSISTENCIA EN DB (intentar) — si falla, persistir localmente
            saved_in_db = False
            if self.db_active and self.user_id:
                try:
                    self.db.save_log(
                        self.user_id,
                        self.paso_actual,
                        mensaje,
                        categoria,
                        pensamiento,
                        privado_para,
                        subtitulos,
                        tts_text,
                        agente_id,
                    )
                    saved_in_db = True
                except Exception as e:
                    logger.error(f"Error guardando log en DB: {e}")

            # Si no se pudo guardar en la DB, intentar persistir localmente
            if not saved_in_db and self.user_id:
                try:
                    self._save_log_local(log_entry)
                except Exception as e:
                    logger.error(f"Error guardando log localmente: {e}")

            print(f"[LOG DEBUG] categoria={categoria}, mensaje={mensaje[:80]}...")

            if self.log_callback:
                try:
                    ritmo = float(getattr(self, "ritmo", 0) or 0)
                except Exception:
                    ritmo = 0

                # Si el ritmo es alto (modo SLOW), programar el callback con un pequeño delay
                if ritmo and ritmo >= 0.5:
                    delay = min(2.0, ritmo * 0.6)
                    threading.Timer(
                        delay,
                        lambda m=mensaje, c=categoria, s=subtitulos, t=tts_text, p=pensamiento, priv=privado_para, a=agente_id: self.log_callback(m, c, s, t, p, priv, a),
                    ).start()
                else:
                    try:
                        self.log_callback(
                            mensaje,
                            categoria,
                            subtitulos,
                            tts_text,
                            pensamiento,
                            privado_para,
                            agente_id,
                        )
                    except Exception:
                        pass
            else:
                print(mensaje)
                if subtitulos:
                    print(f"             └─ [Subtítulos: {subtitulos}]")
        finally:
            self._is_logging = False

    def notificar_cambio_estado(self):
        """Notifica al frontend que ha habido un cambio de estado importante."""
        if self.state_change_callback and not getattr(self, "_stopped", False):
            try:
                self.state_change_callback()
            except Exception as e:
                logger.error(f"Error en state_change_callback: {e}")

    def _emit_realtime_event(self, event_type: str, payload: dict):
        """Emite eventos en tiempo real al frontend, opcionalmente con un pequeño retraso
        proporcional a `self.ritmo` para hacer el flujo más lento en modos como SLOW.
        """
        cb = getattr(self, "realtime_event_callback", None)
        if not cb:
            return

        try:
            ritmo = float(getattr(self, "ritmo", 0) or 0)
        except Exception:
            ritmo = 0

        # Ajustar multiplicador según tipo de evento (actions deberían sentirse más lentas)
        mult = 0.5
        if event_type == "action_event":
            mult = 0.8
        elif event_type == "llm_stream":
            mult = 0.15
        elif event_type == "social_event":
            mult = 0.5

        if ritmo and ritmo >= 0.4:
            delay = min(2.0, ritmo * mult)
            threading.Timer(delay, lambda cb=cb, et=event_type, pl=payload: cb(et, pl)).start()
        else:
            try:
                cb(event_type, payload)
            except Exception:
                pass

    def actualizar_relacion_grupal(self, g1, g2, cambio):
        """Actualiza la afinidad entre dos facciones."""
        if not g1 or not g2 or g1 == g2:
            return

        pair = tuple(sorted([str(g1), str(g2)]))
        actual = self.relaciones_grupos.get(pair, 0.0)
        nueva = max(-1.0, min(1.0, actual + cambio))
        self.relaciones_grupos[pair] = nueva
        self.notificar_cambio_estado()  # Cambio en diplomacia

        if actual >= 0 and nueva < 0:
            self.log(
                f"⚠️ [DIPLOMACIA] Las facciones {g1} y {g2} han entrado en CONFLICTO.",
                categoria="sistema",
            )
        elif actual < 0 and nueva >= 0:
            self.log(
                f"🕊️ [DIPLOMACIA] Las facciones {g1} y {g2} han firmado la PAZ.",
                categoria="sistema",
            )

    def declarar_guerra(self, g1, g2):
        """Inicia un estado de guerra formal entre dos facciones."""
        if not g1 or not g2 or g1 == g2:
            return False, "Facciones inválidas."
        pair = tuple(sorted([str(g1), str(g2)]))
        if pair in self.guerras_activas:
            return False, "Ya existe un estado de guerra."

        self.guerras_activas.append(pair)
        self.relaciones_grupos[pair] = -1.0  # Odio absoluto
        self.log(
            f"⚔️ [GUERRA] ¡La facción {g1} ha DECLARADO LA GUERRA a {g2}!",
            categoria="conflict",
        )

        # Registro histórico
        self.historia.agregar_hito(
            {
                "turno": self.paso_actual,
                "descripcion": f"Conflicto total: La facción {g1} ha declarado oficialmente la guerra a {g2}.",
                "tipo": "conflicto",
            }
        )

        self.notificar_cambio_estado()
        return True, f"Guerra declarada contra {g2}."

    def finalizar_guerra(self, g1, g2):
        """Termina un estado de guerra entre dos facciones."""
        pair = tuple(sorted([str(g1), str(g2)]))
        if pair not in self.guerras_activas:
            return False, "No hay una guerra activa entre estas facciones."

        self.guerras_activas.remove(pair)
        self.relaciones_grupos[pair] = 0.0  # Neutralidad post-guerra
        self.log(
            f"🕊️ [TRATADO] Se ha firmado un armisticio entre {g1} y {g2}. La guerra ha terminado.",
            categoria="consenso",
        )

        # Registro histórico
        self.historia.agregar_hito(
            {
                "turno": self.paso_actual,
                "descripcion": f"La paz ha vuelto: Se ha firmado un armisticio entre {g1} y {g2}.",
                "tipo": "paz",
            }
        )

        self.notificar_cambio_estado()
        return True, f"Paz firmada con {g2}."

    def calcular_gini(self):
        """Calcula el coeficiente de Gini para la desigualdad de recursos."""
        recursos = sorted([a.recursos + a.dinero for a in self.agentes])
        n = len(recursos)
        if n == 0 or sum(recursos) == 0:
            return 0

        # Fórmula de Gini: (2 * sum(i * x_i) / (n * sum(x_i))) - (n + 1) / n
        suma_ponderada = sum((i + 1) * x for i, x in enumerate(recursos))
        suma_total = sum(recursos)
        gini = (2 * suma_ponderada / (n * suma_total)) - (n + 1) / n
        return round(max(0, min(1, gini)), 3)

    def calcular_felicidad_promedio(self):
        """Calcula la felicidad promedio basada en la satisfacción de necesidades."""
        felicidades = []
        for a in self.agentes:
            # Felicidad = 10 - promedio de necesidades (0-10)
            nec = a.necesidades
            promedio_nec = (
                sum(
                    [
                        nec.get(k, 0)
                        for k in [
                            "alimento",
                            "social",
                            "seguridad",
                            "descanso",
                            "entretenimiento",
                        ]
                    ]
                )
                / 5
            )
            felicidad = max(0, 10 - promedio_nec)
            felicidades.append(felicidad)
        return round(sum(felicidades) / len(felicidades), 2) if felicidades else 0

    def track_conflictos(self):
        """Retorna la tasa de conflictos reciente (últimos logs)."""
        conflictos = [
            l for l in self.historial_logs[-20:] if l["categoria"] == "conflict"
        ]
        return len(conflictos)

    def ejecutar_paso_agentes(self):
        # Ejecutar el paso de cada agente
        # Mezclamos el orden para evitar sesgos de prioridad
        agentes_shuffled = list(self.agentes)
        random.shuffle(agentes_shuffled)
        for agente in agentes_shuffled:
            agente.step()

    def formar_grupos(self):
        """Los agentes con lazos de amistad o conocidos forman grupos."""
        for agente in self.agentes:
            if agente.grupo_id is None:
                # Buscar amigos en su memoria
                amigos = [
                    n
                    for n in agente.memoria.grafo.neighbors(agente.unique_id)
                    if agente.memoria.obtener_tipo(n) == "amigo"
                ]
                # También considerar conocidos con alta fuerza de relación
                conocidos = [
                    n
                    for n in agente.memoria.grafo.neighbors(agente.unique_id)
                    if agente.memoria.obtener_tipo(n) == "conocido"
                    and agente.memoria.obtener_fuerza(n) > 0.3
                ]

                # Unir a grupo existente de amigo
                for id_amigo in amigos:
                    otro = self.get_agent_by_id(id_amigo)
                    if otro and otro.grupo_id is not None:
                        agente.grupo_id = otro.grupo_id
                        break
                else:
                    # Crear nuevo grupo si tiene amigos o conocidos cercanos
                    if (amigos or conocidos) and self.grupos_creados_este_paso < 3:
                        nuevo_id = f"G{agente.unique_id}"
                        agente.grupo_id = nuevo_id
                        agente.civilizacion_id = nuevo_id

                        # Unir a los amigos y conocidos
                        todos = amigos + conocidos
                        nombres_miembros = [
                            self.get_agent_by_id(aid).identidad.nombre
                            for aid in todos
                            if self.get_agent_by_id(aid)
                        ]

                        # Generar nombre e identidad DESCRIPTIVA (Requerimiento de Memoria)
                        if hasattr(self, "cerebro_llm") and self.cerebro_llm:
                            nombre_clan, desc_clan = self.cerebro_llm.generar_identidad_grupo(
                                agente, nombres_miembros
                            )
                        else:
                            nombre_clan = f"Clan de {agente.identidad.nombre}"
                            desc_clan = f"Un grupo fundado por {agente.identidad.nombre}."

                        color_clan = self.colores_paleta[
                            hash(nuevo_id) % len(self.colores_paleta)
                        ]

                        self.civilizaciones[nuevo_id] = Civilizacion(
                            id=nuevo_id,
                            nombre=nombre_clan,
                            color=color_clan,
                            user_id=self.user_id,
                            descripcion=desc_clan,
                        )
                        self.objetivos_grupos[nuevo_id] = f"Propósito: {desc_clan}"

                        for id_rel in todos[:5]:  # Máximo 5 miembros iniciales
                            rel_obj = self.get_agent_by_id(id_rel)
                            if rel_obj:
                                rel_obj.grupo_id = nuevo_id
                                rel_obj.civilizacion_id = nuevo_id

                        self.log(
                            f"🚩 [CLAN] Se ha formado un nuevo clan: '{nombre_clan}' representado por {agente.unique_id}.",
                            categoria="consenso",
                        )
                        self.notificar_cambio_estado()
                        self.grupos_creados_este_paso += 1

    def ejecutar(self, pasos=50):
        print("\n" + "═" * 60)
        print("🚀 MISIÓN INICIAL: CREACIÓN DE IDIOMA EMERGENTE")
        print("Los agentes han decidido establecer un protocolo de comunicación")
        print("basado en glifos y símbolos para coordinar su sociedad.")
        print("═" * 60 + "\n")

        self.log(
            f"Iniciando simulación con {len(self.agentes)} agentes por {pasos} pasos...",
            categoria="sistema",
        )
        for _ in range(pasos):
            self.step()
        self.log("Simulación finalizada. ✨", categoria="sistema")

    def visualizar_resultados(self):
        if not self.datos:
            print("No hay datos para visualizar. ❌")
            return

        df = pd.DataFrame(self.datos)

        plt.figure(figsize=(10, 6))

        # Eje principal: Recursos
        ax1 = plt.gca()
        color = "tab:blue"
        ax1.set_xlabel("Paso")
        ax1.set_ylabel("Recursos Promedio", color=color)
        ax1.plot(
            df["paso"],
            df["recursos_promedio"],
            color=color,
            label="Recursos",
            linewidth=2,
        )
        ax1.tick_params(axis="y", labelcolor=color)

        # Eje secundario: Relaciones
        ax2 = ax1.twinx()
        color_amigos = "tab:green"
        color_enemigos = "tab:red"
        ax2.set_ylabel("Cantidad de Relaciones / Grupos", color="black")
        ax2.plot(
            df["paso"],
            df["amigos_total"],
            color=color_amigos,
            linestyle="--",
            label="Amigos",
        )
        ax2.plot(
            df["paso"],
            df["enemigos_total"],
            color=color_enemigos,
            linestyle=":",
            label="Enemigos",
        )
        ax2.plot(
            df["paso"],
            df["num_groups"] if "num_groups" in df else df["num_grupos"],
            color="purple",
            label="Grupos",
            alpha=0.5,
        )
        ax2.tick_params(axis="y", labelcolor="black")

        plt.title("Evolución de la Sociedad de Agentes")

        # Combinar leyendas de ambos ejes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        plt.tight_layout()

        # Forzar el renderizado antes de guardar
        plt.savefig("resultado_simulacion.png", dpi=100, bbox_inches="tight")
        plt.close()  # Limpiar memoria
        print("Gráfico guardado exitosamente como 'resultado_simulacion.png' 📊")

    def imprimir_resumen_social(self):
        print("\n--- RESUMEN SOCIAL FINAL ---")
        # Voceroes por rango
        voceros = sorted(self.agentes, key=lambda a: a.rango, reverse=True)[:3]
        print("\nTop 3 Agentes con mayor Rango (Estatus):")
        for l in voceros:
            print(
                f"  - Agente {l.unique_id}: Rango {l.rango:.2f}, Recursos {l.recursos:.2f}, Grupo: {l.grupo_id}"
            )
            l.memoria.imprimir_grafo_terminal()

        # Grupos
        grupos = {}
        for a in self.agentes:
            if a.grupo_id:
                grupos[a.grupo_id] = grupos.get(a.grupo_id, 0) + 1
        print(f"\nTotal de grupos formados: {len(grupos)}")
        for gid, count in grupos.items():
            print(f"  - Grupo {gid}: {count} miembros")
        print("----------------------------\n")

    def guardar_estado(self):
        """Guarda el estado actual en PostgreSQL."""
        if getattr(self, "_force_stop", False):
            return

        should_write_backup = (
            self.paso_actual == 0
            or self.paso_actual % self.backup_interval == 0
            or not os.path.exists(f"mapa_backup_{self.user_id}.json")
            or not os.path.exists(f"agentes_backup_{self.user_id}.json")
        )

        # 1. Guardar en PostgreSQL (Si está activo)
        if self.db_active and self.user_id and self.user_id != "USER-DEFAULT":
            try:
                # Asegurar que el user_id (o slot_id) existe en la tabla usuarios para evitar errores de FK
                if hasattr(self.db, "ensure_user_exists"):
                    self.db.ensure_user_exists(self.user_id)

                logger.debug(
                    "Guardando estado para user_id=%s, paso=%s",
                    self.user_id,
                    self.paso_actual,
                )

                # Convertir claves de tupla a string para JSON
                rel_str = {
                    f"{k[0]}:{k[1]}": v for k, v in self.relaciones_grupos.items()
                }

                # Obtener estado serializado para campos complejos (mapa, historia)
                datos_json = {
                    "mapa": [
                        [tile.to_dict() for tile in row]
                        for row in getattr(self, "mapa", [])
                    ],
                    "historia": getattr(self, "historia_mundial", {}),
                }

                logger.debug(
                    "Mapa a guardar: %sx%s",
                    len(datos_json.get("mapa", [])),
                    len(datos_json.get("mapa", [0])) if datos_json.get("mapa") else 0,
                )

                # Guardar backup local con menos frecuencia para evitar escrituras pesadas en cada autosave.
                import json
                if should_write_backup:
                    try:
                        with open(f"mapa_backup_{self.user_id}.json", "w") as f:
                            json.dump(datos_json["mapa"], f, indent=2)
                    except Exception as e:
                        logger.warning("Error guardando mapa backup: %s", e)

                # Guardar estado del mundo con user_id y relaciones persistentes
                # Serializar social_recsys si existe
                social_feed_data = None
                if hasattr(self, "social_recsys") and self.social_recsys:
                    social_feed_data = self.social_recsys.to_dict()
                    logger.debug(
                        "Guardando social_feed con %s posts",
                        len(
                            social_feed_data.get("interest_recsys", {}).get(
                                "posts", {}
                            )
                        ),
                    )

                self.db.save_world_state(
                    self.user_id,
                    self.paso_actual,
                    getattr(self, "lore", ""),
                    getattr(self, "seed", ""),
                    self.economia,
                    rel_str,
                    self.objetivos_grupos,
                    datos_json["mapa"],
                    self.infraestructura,
                    datos_json["historia"],
                    social_feed_data,
                )

                # Guardar civilizaciones
                for civ in self.civilizaciones.values():
                    self.db.save_civilization(civ)

                # --- NUEVO: Estrategia de dos pases para integridad referencial ---
                # 1. Guardar todos los AGENTES primero
                for a in self.agentes:
                    self.db.save_agent(a, self.user_id)

                # Backup de agentes en archivo, también con menor frecuencia.
                if should_write_backup:
                    try:
                        agentes_backup = []
                        for a in self.agentes:
                            agentes_backup.append({
                                "id": a.unique_id,
                                "x": a.x,
                                "y": a.y,
                                "recursos": a.recursos,
                                "dinero": a.dinero,
                                "personalidad": a.personalidad,
                                "necesidades": a.necesidades,
                                "experiencia": a.experiencia,
                                "inventario": a.inventario,
                                "alma": a.alma.to_dict() if a.alma else None,
                                "identidad": a.identidad.to_dict() if a.identidad else None,
                            })
                        with open(f"agentes_backup_{self.user_id}.json", "w") as f:
                            json.dump(agentes_backup, f, indent=2)
                    except Exception as e:
                        logger.warning("Error guardando agentes backup: %s", e)

                # 2. Guardar todas las MEMORIAS después
                agentes_validos = {a.unique_id for a in self.agentes}
                total_memorias = 0
                for a in self.agentes:
                    mem_data = a.memoria.exportar_datos()
                    for edge in mem_data.get("aristas", []):
                        if edge["u"] == a.unique_id:
                            target_id = edge["v"]
                            if target_id in agentes_validos:
                                # edge['data'] ahora contiene recursos_vistos y grupo gracias al fix en MemoriaGrafica
                                self.db.save_memory(
                                    a.unique_id, target_id, edge["data"], self.user_id
                                )
                                total_memorias += 1

                if total_memorias > 0:
                    logger.info(
                        f"🧠 [DB] Persistidas {total_memorias} relaciones de memoria para {self.user_id}"
                    )

                # Guardar Leyes y Propuestas (Sincronizando IDs para evitar pérdida de referencia)
                id_map = {} # Mapeo de IDs temporales (LEY-XXXX) a IDs reales (SERIAL DB)
                
                # 1. Procesar leyes globales
                for ley in self.leyes_globales:
                    old_id = ley.get("id")
                    new_id = self.db.save_proposal(ley, self.user_id)
                    if new_id:
                        ley["db_id"] = new_id
                        ley["id"] = str(new_id)
                        if old_id and old_id != str(new_id):
                            id_map[old_id] = str(new_id)

                # 2. Procesar leyes por facción y lista general de propuestas
                for grupo_id, leyes in self.facciones_leyes.items():
                    # Evitar duplicar procesamiento si una ley está en ambos lugares
                    for ley in leyes:
                        old_id = ley.get("id")
                        ley_copy = ley.copy()
                        if grupo_id != "propuestas":
                            ley_copy["grupo_id"] = grupo_id
                        
                        new_id = self.db.save_proposal(ley_copy, self.user_id)
                        if new_id:
                            ley["db_id"] = new_id
                            ley["id"] = str(new_id)
                            if old_id and old_id != str(new_id):
                                id_map[old_id] = str(new_id)

                # 3. Sincronizar asambleas con los nuevos IDs de las leyes y guardarlas
                for asamblea in self.asambleas_globales:
                    # Si la asamblea apuntaba a un ID temporal, actualizar al ID real de la DB
                    curr_ley_id = asamblea.get("ley_id")
                    if curr_ley_id in id_map:
                        asamblea["ley_id"] = id_map[curr_ley_id]

                    prop = {
                        "db_id": asamblea.get("db_id"),
                        "proponente_id": asamblea.get("proponente_id", "SISTEMA"),
                        "texto": asamblea.get("tema", "Asamblea sin título"),
                        "tipo": "asamblea",
                        "votos": {
                            "si": asamblea.get("votos_si", 0),
                            "no": asamblea.get("votos_no", 0),
                            "participantes": asamblea.get("participantes_votos", {}),
                            "turno_idx": asamblea.get("agente_turno_idx", 0),
                            "ley_id": asamblea.get("ley_id")
                        },
                        "estado": asamblea.get("estado", "DEBATE"),
                        "paso_creacion": asamblea.get("paso_inicio", self.paso_actual),
                    }
                    new_id = self.db.save_proposal(prop, self.user_id)
                    if new_id and not asamblea.get("db_id"):
                        asamblea["db_id"] = new_id

                # Guardar Misiones y Puntajes (NUEVO)
                for mision in self.sistema_misiones.misiones_activas:
                    self.db.save_mission(mision, self.user_id)
                for mision in self.sistema_misiones.misiones_completadas:
                    self.db.save_mission(mision, self.user_id)

                # Guardar Instituciones (NUEVO)
                for inst in self.instituciones.values():
                    self.db.save_institution(inst, self.user_id)

                puntos_actuales = self.sistema_misiones.obtener_puntaje(self.user_id)
                self.db.save_score(self.user_id, puntos_actuales)

                logger.info(
                    f"💾 [DB] Estado Global, Leyes y Misiones guardados en PostgreSQL para {self.user_id}"
                )
            except Exception as e:
                logger.error(f"❌ Error guardando en DB: {e}")

    def _save_log_local(self, log_entry):
        """Guardar un log localmente en data/logs_<user_id>.json cuando la DB no esté disponible."""
        try:
            import json as _json
            if not self.user_id:
                return False
            os.makedirs("data", exist_ok=True)
            path = os.path.join("data", f"logs_{self.user_id}.json")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = _json.load(f)
            except Exception:
                existing = []
            existing.append(log_entry)
            # Mantener un límite razonable de logs locales
            if len(existing) > 5000:
                existing = existing[-5000:]
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(existing, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error guardando log local: {e}")
            return False

    def cargar_estado(self):
        """Carga el estado desde PostgreSQL (prioridad) o JSON (fallback)."""
        if self.start_empty:
            logger.info(
                "⚠️ [DB] start_empty=True, omitiendo carga de estado desde DB para iniciar vacío."
            )
            self.agentes_cargados = False
            return

        # 1. Intentar cargar desde PostgreSQL
        if self.db_active:
            if self.db and self.db.conn is None:
                self.db.connect()
            try:
                # Obtener el user_id (podría venir de la sesión si esto fuera asíncrono,
                # pero aquí intentamos deducirlo o usar uno por defecto temporal)
                target_user_id = self.user_id or "USER-DEFAULT"

                self.log(
                    f"🔄 [DEBUG] Cargando estado para user_id={target_user_id}",
                    categoria="sistema",
                )

                # 1. Cargar metadatos globales
                world_state = self.db.get_world_state(target_user_id)
                if world_state:
                    self.log(f"✅ [DEBUG] Estado encontrado en DB", categoria="sistema")
                    (
                        self.paso_actual,
                        self.lore,
                        self.seed,
                        precio,
                        indice,
                        total_dinero,
                        rel_data,
                        obj_grupos,
                        mapa_data,
                        infra_data,
                        historia_data,
                        social_feed_data,
                    ) = world_state
                    self.economia["indice_bursatil"] = indice
                    self.economia["total_dinero"] = total_dinero
                    self.precio_recurso_actual = precio
                    self.objetivos_grupos = obj_grupos or {}
                    self.infraestructura = infra_data or []

                    if historia_data:
                        self.historia.cargar_desde_dict(historia_data)

                    # Restaurar ubicación de la universidad si existe en la infraestructura
                    for edif in self.infraestructura:
                        if edif.get("tipo") == "Universidad":
                            self.ubicacion_universidad = (edif["x"], edif["y"])
                            break

                    # Restaurar mapa si existe
                    if mapa_data:
                        mapa_ancho = len(mapa_data)
                        mapa_alto = len(mapa_data[0]) if mapa_ancho > 0 else 0
                        self.log(
                            f"🔄 [DEBUG] Restaurando mapa desde DB: {mapa_ancho}x{mapa_alto}",
                            categoria="sistema",
                        )

                        # IMPORTANTE: Reinicializar WorldSystem con el tamaño correcto del mapa guardado
                        if self.world is None or mapa_ancho != self.mapa_size:
                            self.world = WorldSystem(size=mapa_ancho, seed=self.seed)
                            self.world.mapa = []  # Limpiar mapa generado automáticamente
                            self.mapa_size = mapa_ancho

                        # Inicializar mapa vacío del tamaño CORRECTO (no 20x20 fijo)
                        self.mapa = []
                        for x in range(mapa_ancho):
                            fila = []
                            for y in range(mapa_alto):
                                if x < len(mapa_data) and y < len(mapa_data[x]):
                                    d = mapa_data[x][y]
                                    # Asegurar que d sea un diccionario válido
                                    if isinstance(d, dict) and "terrain" in d:
                                        tile = WorldTile(
                                            d.get("x", x), d.get("y", y), d["terrain"]
                                        )
                                        tile.resource_node = d.get("resource")
                                        tile.owner_civ_id = d.get("owner")
                                        tile.buildings = d.get("buildings", [])
                                        tile.is_archaeological_site = d.get(
                                            "is_archaeological_site", False
                                        )
                                        tile.artifact_type = d.get("artifact_type")
                                        tile.artifact_value = d.get("artifact_value", 0)
                                        tile.discovered_by = d.get("discovered_by")
                                        tile.discovery_turn = d.get("discovery_turn")
                                        tile.yield_rate = d.get("yield_mult", 1.0)
                                        tile.energy_cost = d.get("energy_cost", 0.05)
                                        tile.health_risk = d.get("health_risk", 0.0)
                                        tile.move_difficulty = d.get(
                                            "move_difficulty", 1.0
                                        )
                                        fila.append(tile)
                                    else:
                                        # Si no hay datos, crear tile vacío
                                        fila.append(Tile(x, y))
                                else:
                                    # Fuera de límites del mapa guardado (no debería pasar)
                                    fila.append(Tile(x, y))
                            self.mapa.append(fila)

                        # Actualizar referencia en WorldSystem
                        self.world.mapa = self.mapa
                        self.world.size = mapa_ancho

                        # Marcar que el mapa fue cargado desde DB
                        self._mapa_cargado = True
                        # Asegurar que la referencia world.mapa apunte al mismo mapa
                        if self.world:
                            self.world.mapa = self.mapa
                        self.log(
                            f"✅ [DEBUG] Mapa restaurado: {len(self.mapa)}x{len(self.mapa[0]) if self.mapa else 0}",
                            categoria="sistema",
                        )

                    # Si no se cargó mapa, generar uno nuevo
                    if not self.mapa or len(self.mapa) == 0:
                        # Intentar cargar desde archivo backup
                        import json
                        try:
                            with open(f"mapa_backup_{target_user_id}.json", "r") as f:
                                mapa_data = json.load(f)
                            self.log("🔄 [BACKUP] Mapa cargado desde archivo", categoria="sistema")
                            # Repetir la lógica de carga
                            mapa_ancho = len(mapa_data)
                            mapa_alto = len(mapa_data[0]) if mapa_ancho > 0 else 0
                            self.log(
                                f"🔄 [DEBUG] Restaurando mapa desde backup: {mapa_ancho}x{mapa_alto}",
                                categoria="sistema",
                            )
                            if self.world is None or mapa_ancho != self.mapa_size:
                                self.world = WorldSystem(size=mapa_ancho, seed=self.seed)
                                self.world.mapa = []
                                self.mapa_size = mapa_ancho
                            self.mapa = []
                            for x in range(mapa_ancho):
                                fila = []
                                for y in range(mapa_alto):
                                    if x < len(mapa_data) and y < len(mapa_data[x]):
                                        d = mapa_data[x][y]
                                        if isinstance(d, dict) and "terrain" in d:
                                            tile = WorldTile(
                                                d.get("x", x), d.get("y", y), d["terrain"]
                                            )
                                            tile.resource_node = d.get("resource")
                                            tile.owner_civ_id = d.get("owner")
                                            tile.buildings = d.get("buildings", [])
                                            tile.is_archaeological_site = d.get(
                                                "is_archaeological_site", False
                                            )
                                            tile.artifact_type = d.get("artifact_type")
                                            tile.artifact_value = d.get("artifact_value", 0)
                                            tile.discovered_by = d.get("discovered_by")
                                            tile.discovery_turn = d.get("discovery_turn")
                                            tile.yield_rate = d.get("yield_mult", 1.0)
                                            tile.energy_cost = d.get("energy_cost", 0.05)
                                            tile.health_risk = d.get("health_risk", 0.0)
                                            tile.move_difficulty = d.get(
                                                "move_difficulty", 1.0
                                            )
                                            fila.append(tile)
                                        else:
                                            fila.append(
                                                WorldTile(x, y, TerrainType.GRASS)
                                            )
                                    else:
                                        fila.append(WorldTile(x, y, TerrainType.GRASS))
                                self.mapa.append(fila)
                            # Actualizar referencia en WorldSystem
                            self.world.mapa = self.mapa
                            self.world.size = mapa_ancho
                            self._mapa_cargado = True
                        except FileNotFoundError:
                            self.log("⚠️ [BACKUP] No hay mapa backup, generando nuevo", categoria="sistema")
                            self.generar_mapa()
                        except Exception as e:
                            self.log(f"❌ [BACKUP] Error cargando mapa backup: {e}", categoria="sistema")
                            self.generar_mapa()

                    # Restaurar relaciones de grupos
                    if rel_data:
                        self.relaciones_grupos = {}
                        for k, v in rel_data.items():
                            parts = k.split(":")
                            if len(parts) == 2:
                                self.relaciones_grupos[tuple(parts)] = v

                    # Restaurar social_feed (posts, comentarios, seguidores)
                    if (
                        social_feed_data
                        and hasattr(self, "social_recsys")
                        and self.social_recsys
                    ):
                        try:
                            self.social_recsys = SocialRecSys.from_dict(
                                social_feed_data,
                                db=self.db,
                                user_id=target_user_id,
                                modelo=self,
                            )
                            num_posts = len(self.social_recsys.interest_recsys.posts)
                            num_seguidos = len(self.social_recsys.seguidos)
                            self.log(
                                f"✅ [DEBUG] Social feed restaurado: {num_posts} posts, {num_seguidos} seguidores",
                                categoria="sistema",
                            )
                        except Exception as e:
                            self.log(
                                f"⚠️ [DEBUG] Error restaurando social_feed: {e}",
                                categoria="sistema",
                            )

                # 2. Cargar Civilizaciones
                civs_db = self.db.get_civilizations(target_user_id)
                self.civilizaciones = {}
                if civs_db:
                    for c_row in civs_db:
                        c_id, c_nom, c_col, c_rec, c_ter = c_row
                        civ = Civilizacion(c_id, c_nom, c_col, target_user_id)
                        civ.recursos_globales = c_rec
                        civ.territorio = c_ter or []
                        self.civilizaciones[c_id] = civ

                # 3. Cargar Misiones y Puntajes
                misiones_db = self.db.get_missions(target_user_id)
                if misiones_db:
                    self.sistema_misiones.misiones_activas = []
                    self.sistema_misiones.misiones_completadas = []
                    for m_row in misiones_db:
                        # Estructura misiones_db: id, titulo, desc, tipo, dif, obj, puntos, estado, inicio, limite, comp_por, turn_comp
                        mision = Mision(
                            id=m_row[0],
                            titulo=m_row[1],
                            descripcion=m_row[2],
                            tipo=m_row[3],
                            dificultad=m_row[4],
                            objetivo=m_row[5],
                            recompensa_puntos=m_row[6],
                            estado=m_row[7],
                            turno_inicio=m_row[8],
                            turno_limite=m_row[9],
                            completada_por=m_row[10],
                            turno_completada=m_row[11],
                        )
                        if mision.estado == "completada":
                            self.sistema_misiones.misiones_completadas.append(mision)
                        else:
                            self.sistema_misiones.misiones_activas.append(mision)
                else:
                    logger.info(
                        "🎯 No se encontraron misiones en DB. Inicializando misiones por defecto."
                    )
                    self.sistema_misiones.inicializar_misiones_iniciales(
                        self.paso_actual
                    )

                puntos = self.db.get_score(target_user_id)
                self.sistema_misiones.puntajes_usuarios[target_user_id] = puntos

                # 3. Cargar Agentes
                agents_data = []
                if self.db_active:
                    agents_data = self.db.get_agents(target_user_id) or []
                    self.log(
                        f"🔄 [DEBUG] Agentes en DB: {len(agents_data)}",
                        categoria="sistema",
                    )

                # Si DB está inactiva o no devolvió agentes, intentar backup local.
                if not agents_data:
                    self.log(
                        "⚠️ [DEBUG] Sin agentes en DB, intentando cargar agentes desde backup",
                        categoria="sistema",
                    )
                    import json

                    try:
                        with open(f"agentes_backup_{target_user_id}.json", "r") as f:
                            agentes_backup = json.load(f)
                        self.log(
                            f"🔄 [BACKUP] Agentes cargados desde archivo: {len(agentes_backup)}",
                            categoria="sistema",
                        )
                        # Convertir a formato similar a DB
                        agents_data = []
                        for ab in agentes_backup:
                            # Crear un row simulado
                            row = (
                                ab["id"],
                                target_user_id,
                                ab["recursos"],
                                ab["dinero"],
                                None,
                                "Ciudadano",
                                None,
                                1.0,
                                1.0,
                                ab.get("personalidad", {}),
                                ab.get("necesidades", {}),
                                ab.get("experiencia", {}),
                                {},
                                ab.get("inventario", {}),
                                [],
                                [],
                                None,
                                [],
                                [],
                                {},
                                ab["x"],
                                ab["y"],
                                {},
                                0.3,
                                [],
                                [],
                                [],
                                ab.get("alma"),
                                ab.get("identidad"),
                                {},
                                {},
                                {},
                            )
                            agents_data.append(row)
                    except FileNotFoundError:
                        self.log("⚠️ [BACKUP] No hay backup de agentes", categoria="sistema")
                    except Exception as e:
                        self.log(
                            f"❌ [BACKUP] Error cargando agentes backup: {e}",
                            categoria="sistema",
                        )
                self.agentes = []
                for row in agents_data:
                    # id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, civ_id, alianzas, tratados, memoria_mensajes, x, y, skills, skill_factor, beliefs, desires, intentions, alma, identidad, heartbeat_config
                    (
                        a_id,
                        _,
                        rec,
                        din,
                        g_id,
                        rol,
                        prof,
                        ran,
                        rep,
                        pers,
                        nec,
                        exp,
                        con,
                        inv,
                        hitos,
                        etico,
                        civ_id,
                        alianzas,
                        tratados,
                        mem_msgs,
                        loaded_x,
                        loaded_y,
                        skills_db,
                        s_factor,
                        bdi_beliefs,
                        bdi_desires,
                        bdi_intentions,
                        alma_db,
                        ident_db,
                        heart_db,
                        mem_persistente,
                        apps_db,
                    ) = row
                    a = Agente(a_id, self)
                    a.apps = apps_db or {}
                    a.x = loaded_x
                    a.y = loaded_y
                    a.recursos = rec
                    a.dinero = din
                    a.grupo_id = g_id
                    a.rol = rol
                    a.profesion = prof
                    a.rango = ran
                    a.reputacion = rep
                    a.personalidad = pers
                    a.necesidades = nec

                    # Restaurar Alma
                    if alma_db:
                        from agents.alma import Alma

                        a.alma = Alma.from_dict(alma_db)

                    # Restaurar Identidad
                    if ident_db:
                        from agents.identity_system import Identidad

                        a.identidad = Identidad.from_dict(ident_db)

                    # Restaurar Heartbeat
                    if heart_db:
                        from systems.heartbeat import RitmoVital

                        a.heartbeat_mundo = RitmoVital.from_dict(
                            heart_db, personalidad=a.personalidad
                        )

                    # Restaurar Memoria Persistente (Tripartita)
                    from systems.memoria_persistente import MemoriaPersistente

                    a.memoria_persistente = MemoriaPersistente(
                        agente_id=a.unique_id,
                        user_id=target_user_id,
                        data=mem_persistente,
                    )

                    # Asegurar que experiencia tenga todas las categorías
                    exp_default = {
                        "medicina": 0,
                        "comercio": 0,
                        "combate": 0,
                        "exploracion": 0,
                        "social": 0,
                        "ingenieria": 0,
                        "agricultura": 0,
                    }
                    if exp and isinstance(exp, dict):
                        exp_default.update(exp)
                    a.experiencia = exp_default
                    a.conocimientos = con
                    a.inventario = inv
                    a.hitos = hitos
                    a.historial_etico = etico
                    a.civilizacion_id = civ_id
                    a.alianzas = alianzas or []
                    a.tratados = tratados or []
                    a.skills = skills_db or {}
                    a.skill_factor = s_factor if s_factor is not None else 0.3

                    # Reconstruir BDI con validación de tipo
                    from agents.bdi_components import (
                        SistemaCreencias,
                        SistemaDeseos,
                        SistemaIntenciones,
                    )

                    # Forzar objetos válidos incluso si la DB tiene datos antiguos/erróneos
                    if bdi_beliefs and isinstance(bdi_beliefs, dict):
                        a.creencias = SistemaCreencias.from_dict(bdi_beliefs)
                    else:
                        a.creencias = SistemaCreencias()

                    if bdi_desires and isinstance(bdi_desires, dict):
                        a.deseos = SistemaDeseos.from_dict(bdi_desires)
                    else:
                        a.deseos = SistemaDeseos()

                    if bdi_intentions and isinstance(bdi_intentions, dict):
                        a.intenciones = SistemaIntenciones.from_dict(bdi_intentions)
                    else:
                        a.intenciones = SistemaIntenciones()

                    if mem_msgs:
                        a.memoria.historial_mensajes = mem_msgs

                    # Cargar memorias
                    memories = self.db.get_memories(a_id, target_user_id)
                    mem_dict = {
                        "nodos": [{"id": a_id, "data": {"tipo": "yo"}}],
                        "aristas": [],
                    }
                    for m_row in memories:
                        target_id, tipo, fuerza, rec_v, grp_v = m_row
                        mem_dict["nodos"].append(
                            {
                                "id": target_id,
                                "data": {
                                    "tipo": "conocido", # El nodo siempre es un conocido
                                    "recursos_vistos": rec_v,
                                    "grupo": grp_v,
                                },
                            }
                        )
                        mem_dict["aristas"].append(
                            {
                                "u": a_id,
                                "v": target_id,
                                "data": {
                                    "tipo": tipo, 
                                    "fuerza": fuerza,
                                    "recursos_vistos": rec_v,
                                    "grupo": grp_v
                                },
                            }
                        )

                    a.memoria.cargar_datos(mem_dict)
                    self.agentes.append(a)

                # NORMALIZAR: Asegurar que sólo exista un `Historiador` activo.
                # Si la libreta de historia ya tiene un historiador registrado, forzar
                # que ese agente tenga la profesión/rol correctos y limpiar el resto.
                try:
                    if hasattr(self, "historia") and getattr(self.historia, "historiador_id", None):
                        hist_id = self.historia.historiador_id
                        for ag in self.agentes:
                            try:
                                if getattr(ag, "unique_id", None) == hist_id:
                                    ag.profesion = "Historiador"
                                    ag.rol = "Historiador"
                                    if hasattr(ag, "identidad") and ag.identidad:
                                        ag.identidad.titulo = "el Historiador"
                                else:
                                    if getattr(ag, "profesion", None) == "Historiador":
                                        ag.profesion = None
                                        ag.rol = "Ciudadano"
                            except Exception:
                                continue
                    else:
                        # Si no existe historiador pero hay agentes marcados como Historiador,
                        # elegir el primero y limpiar los demás.
                        candidatos = [a for a in self.agentes if getattr(a, "profesion", None) == "Historiador"]
                        if candidatos:
                            elegido = candidatos[0]
                            try:
                                # Asegurar la libreta de historia existe
                                if not hasattr(self, "historia") or self.historia is None:
                                    from systems.historia import LibretaHistoria

                                    self.historia = LibretaHistoria()
                                self.historia.historiador_id = elegido.unique_id
                                elegido.profesion = "Historiador"
                                elegido.rol = "Historiador"
                                if hasattr(elegido, "identidad") and elegido.identidad:
                                    elegido.identidad.titulo = "el Historiador"
                            except Exception:
                                pass
                            for other in candidatos[1:]:
                                try:
                                    other.profesion = None
                                    other.rol = "Ciudadano"
                                except Exception:
                                    pass
                except Exception:
                    # No queremos que un fallo aquí impida la carga del resto del estado
                    pass

                # 4. Cargar Leyes y Propuestas
                proposals = self.db.get_proposals(target_user_id)
                self.leyes_globales = []
                self.facciones_leyes = {}
                self.asambleas_globales = []

                if proposals:
                    for p_row in proposals:
                        # id, grupo_id, proponente_id, texto, tipo, votos, estado, paso_creacion, titulo, contenido
                        (
                            p_id,
                            g_id,
                            prop_id,
                            texto,
                            p_tipo,
                            votos,
                            estado,
                            paso_p,
                            titulo,
                            contenido,
                        ) = p_row

                        # Asegurar que votos sea un diccionario
                        if isinstance(votos, str):
                            try:
                                votos = json.loads(votos)
                            except:
                                votos = {"si": 0, "no": 0}
                        elif not isinstance(votos, dict):
                            votos = {"si": 0, "no": 0}

                        prop = {
                            "id": p_id,
                            "proponente_id": prop_id,
                            "texto": texto,
                            "tipo": p_tipo,
                            "votos": votos,
                            "estado": estado,
                            "paso_creacion": paso_p,
                            "titulo": titulo,
                            "contenido": contenido,
                            "db_id": p_id,
                        }

                        if "propuestas" not in self.facciones_leyes:
                            self.facciones_leyes["propuestas"] = []
                        self.facciones_leyes["propuestas"].append(prop)

                        if p_tipo == "asamblea" and estado not in ["FINALIZADA", "APROBADA", "RECHAZADA"]:
                            l_id = votos.get("ley_id")
                            # Deduplicación: Evitar duplicados por ley_id o por combinación de tema y proponente
                            if l_id and any(a.get("ley_id") == l_id for a in self.asambleas_globales):
                                continue
                            if any(a.get("tema") == texto and a.get("proponente_id") == prop_id and a.get("estado") == estado for a in self.asambleas_globales):
                                continue

                            asamblea = {
                                "id": f"ASAMBLEA-{p_id}",
                                "db_id": p_id,
                                "proponente_id": prop_id,
                                "tema": texto,
                                "moderador_id": prop_id,
                                "votos_si": votos.get("si", 0),
                                "votos_no": votos.get("no", 0),
                                "participantes_votos": votos.get("participantes", {}),
                                "agente_turno_idx": votos.get("turno_idx", 0),
                                "ley_id": l_id,
                                "votantes": [],
                                "estado": estado,
                                "paso_inicio": paso_p,
                                "pasos_restantes": 5,
                            }
                            self.asambleas_globales.append(asamblea)
                        elif estado == "pendiente":
                            if "propuestas" not in self.facciones_leyes:
                                self.facciones_leyes["propuestas"] = []
                            self.facciones_leyes["propuestas"].append(prop)
                        elif estado == "aprobada":
                            if g_id and g_id != "GLOBAL":
                                if g_id not in self.facciones_leyes:
                                    self.facciones_leyes[g_id] = []
                                self.facciones_leyes[g_id].append(prop)
                            else:
                                self.leyes_globales.append(prop)

                # 5. Cargar Instituciones (NUEVO)
                instituciones_db = self.db.get_institutions(target_user_id)
                self.instituciones = {}
                if instituciones_db:
                    for i_row in instituciones_db:
                        # Soportar esquemas con o sin la columna 'puntos'.
                        # Posibles órdenes de columnas:
                        # - Con 'puntos': id, nombre, tipo, fundador_id, vocero_id, miembros, x, y, recursos, puntos, nivel, descripcion
                        # - Sin 'puntos': id, nombre, tipo, fundador_id, vocero_id, miembros, x, y, recursos, nivel, descripcion
                        if not i_row:
                            continue
                        if len(i_row) == 12:
                            i_id, i_nom, i_tipo, i_fund, i_lid, i_miem, i_x, i_y, i_rec, i_puntos, i_niv, i_desc = i_row
                        elif len(i_row) == 11:
                            i_id, i_nom, i_tipo, i_fund, i_lid, i_miem, i_x, i_y, i_rec, i_niv, i_desc = i_row
                            i_puntos = 0.0
                        else:
                            logger.warning(f"Institución: fila inesperada (len={len(i_row)}): {i_row}")
                            # Intentar asignar por seguridad si hay suficientes campos
                            try:
                                i_id = i_row[0]
                                i_nom = i_row[1] if len(i_row) > 1 else "?"
                                i_tipo = i_row[2] if len(i_row) > 2 else None
                                i_fund = i_row[3] if len(i_row) > 3 else None
                                i_lid = i_row[4] if len(i_row) > 4 else i_fund
                                i_miem = i_row[5] if len(i_row) > 5 else [i_fund]
                                i_x = i_row[6] if len(i_row) > 6 else 0
                                i_y = i_row[7] if len(i_row) > 7 else 0
                                i_rec = i_row[8] if len(i_row) > 8 else 0.0
                                i_puntos = i_row[9] if len(i_row) > 9 else 0.0
                                i_niv = i_row[10] if len(i_row) > 10 else 1
                                i_desc = i_row[11] if len(i_row) > 11 else ""
                            except Exception:
                                continue

                        # Asegurar miembros sea lista
                        if isinstance(i_miem, str):
                            try:
                                i_miem = json.loads(i_miem)
                            except:
                                i_miem = [i_fund]

                        inst = Institucion(
                            i_id, i_nom, i_tipo, i_fund, i_x, i_y, target_user_id
                        )
                        inst.vocero_id = i_lid
                        inst.miembros = i_miem
                        inst.recursos = i_rec
                        inst.puntos = i_puntos if i_puntos is not None else 0.0
                        inst.nivel = i_niv
                        inst.descripcion = i_desc or ""
                        self.instituciones[i_id] = inst

                # 6. Cargar Logs de la sesión (Ahora con límite aumentado y orden correcto DESC->ASC)
                logs_db = self.db.get_logs(target_user_id, limit=2000)
                if logs_db:
                    self.historial_logs = []
                    for pr in logs_db:
                        # paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id
                        p, msg, cat, thoughts, priv, subs, tts, _ = pr
                        self.historial_logs.append(
                            {
                                "paso": p,
                                "mensaje": msg,
                                "categoria": cat,
                                "pensamiento": thoughts,
                                "privado_para": priv,
                                "subtitulos": subs,
                                "tts_text": tts,
                            }
                        )
                    logger.info(
                        f"📜 [DB] {len(self.historial_logs)} logs cargados de la base de datos."
                    )
                else:
                    logger.warning(
                        f"📜 [DB] No se encontraron logs en la base de datos para user_id={target_user_id}"
                    )
                # Garantizar que las misiones base existan si no se cargaron de la DB
                if (
                    not self.sistema_misiones.misiones_activas
                    and not self.sistema_misiones.misiones_completadas
                ):
                    logger.info(
                        "🆕 No se encontraron misiones en DB. Inicializando misiones base..."
                    )
                    self.sistema_misiones.inicializar_misiones_iniciales(
                        self.paso_actual
                    )

                self.agentes_cargados = True
                logger.info(
                    f"💾 [DB] Estado y Misiones cargados desde PostgreSQL para {target_user_id}"
                )
                return
            except Exception as e:
                import traceback
                logger.error(f"❌ Error cargando desde DB: {e}\n{traceback.format_exc()}")

        else:
            logger.info("⚠️ [DB] No se cargó la simulación desde Postgres o db inactiva. Intentando cargar logs locales...")
            self.agentes_cargados = False
            # Intentar cargar logs desde archivo local si existe (fallback cuando no hay DB)
            if self.user_id:
                local_path = f"data/logs_{self.user_id}.json"
                if os.path.exists(local_path):
                    try:
                        import json as _json
                        with open(local_path, "r", encoding="utf-8") as _f:
                            local_logs = _json.load(_f)
                        self.historial_logs = local_logs[-2000:]
                        logger.info(f"📜 [LOCAL] {len(self.historial_logs)} logs cargados desde {local_path}")
                    except Exception as e:
                        logger.warning(f"📜 [LOCAL] Error cargando logs locales: {e}")

    def asignar_roles_consenso(self):
        """Los grupos negocian roles internos. Optimizado: un grupo por turno para evitar sobrecarga LLM."""
        grupos_ids = list(set(a.grupo_id for a in self.agentes if a.grupo_id is not None))
        if not grupos_ids:
            return

        # Usar el paso actual para elegir un grupo de forma rotativa
        idx_grupo = (self.paso_actual // 5) % len(grupos_ids)
        g_id = grupos_ids[idx_grupo]
        miembros = [a for a in self.agentes if a.grupo_id == g_id and a.esta_vivo]

        if len(miembros) < 2:
            return

        # --- FASE DE ASAMBLEA ---
        self.log(
            f"🏛️ [ASAMBLEA FACCIÓN {g_id}] Los miembros se reúnen para debatir el futuro...",
            categoria="consenso",
        )

        # Verificar si hay propuestas de vocería activas o si no hay vocero
        vocero_actual = next((m for m in miembros if m.rol == "Vocero"), None)

        if not vocero_actual:
            self.log(
                f"🔸 [ASAMBLEA] La Facción {g_id} no tiene un vocero claro. Se anima a los miembros a presentar sus programas.",
                categoria="consenso",
            )

        ids_miembros = [m.unique_id for m in miembros]
        vocero_id = vocero_actual.unique_id if vocero_actual else "Ninguno"
        
        # En lugar de todos, solo 2 miembros aleatorios expresan su opinión para no saturar
        habladores = random.sample(miembros, min(len(miembros), 2))
        
        for m in habladores:
            ctx = (
                f"El vocero actual es {vocero_id}. La facción busca consolidar su poder."
                if vocero_actual
                else "No hay vocero. Es momento de proponerse o buscar consensos para elegir uno."
            )
            argumento, pensamiento = cerebro_llm.generar_debate_consenso(
                m, ids_miembros, fase="asamblea", contexto_extra=ctx
            )
            if argumento:
                m.decir(
                    f"🗣️ [OPINION ASAMBLEA] {argumento}",
                    pensamiento=pensamiento,
                    para_grupo=True,
                )

    def generar_mapa(self):
        """Genera el mapa inicial 20x20 delegando en WorldSystem."""
        self.world.size = 20
        self.mapa = self.world.generar_inicial()
        self.mapa_size = 20
        self.log(f"🗺️ [MAPA] Mundo 20x20 generado con WorldSystem", categoria="sistema")
        return self.mapa

    def expandir_mundo(
        self, direccion=None, cantidad=5, comprador_id=None, costo_override=None
    ):
        """
        Expande el mundo dinámicamente con sistema de costos económicos.
        Soporta 'north', 'south', 'east', 'west' o None (uniforme).
        """
        if self.world is None:
            return False, "Sistema de mundo no inicializado"

        # 1. Sistema de Costos y Verificación de Fondos
        # El coste base se deriva de la constante general `COSTO_EXPANSION` y
        # se reduce mediante `EXPANSION_COST_DIVISOR` para facilitar pruebas/ajustes.
        costo_base_por_casilla = int(getattr(self, "COSTO_EXPANSION", 1000.0) / max(1, getattr(self, "EXPANSION_COST_DIVISOR", 10)))
        num_direcciones = 4 if direccion is None else 1
        num_casillas_estimadas = cantidad * self.mapa_size * num_direcciones
        costo_total = costo_override if costo_override is not None else (costo_base_por_casilla * num_casillas_estimadas)

        # Soportar comprador como 'arquitecto', id de grupo/civilización, o id de agente
        comprador_es_grupo = False
        if comprador_id:
            if comprador_id == "arquitecto":
                try:
                    fondos = sum(getattr(a, "dinero", 0) for a in self.agentes)
                except Exception:
                    fondos = self.economia.get("total_dinero", 0)
                tipo = "Arquitecto"
            else:
                # Intentar tratar comprador_id como id de grupo/civilización primero
                grupo = self.civilizaciones.get(comprador_id) or self.grupos_dinamicos.get(comprador_id)
                if grupo:
                    # Aceptar varias claves posibles ('fondos','dinero','recursos')
                    fondos = grupo.get("fondos", grupo.get("dinero", grupo.get("recursos", 0)))
                    tipo = "Grupo"
                    comprador_es_grupo = True
                else:
                    # Tratar comprador_id como id de agente y usar helpers existentes
                    fondos, tipo = self._verificar_fondos_expansion(comprador_id)

            if fondos < costo_total:
                return (
                    False,
                    f"Fondos insuficientes para {tipo}: {fondos} MC disponibles, {costo_total} MC requeridos",
                )

            # Verificar permisos solo si la configuración lo exige
            if not getattr(self, "ALLOW_NON_LEADER_EXPANSION", True):
                if comprador_id != "arquitecto":
                    if not self._verificar_permisos_expansion(comprador_id):
                        return (
                            False,
                            f"{comprador_id} no tiene permisos de vocero para expandir",
                        )
        else:
            self.log(
                "⚠️ [EXPANSIÓN] Expansión gratuita activada (modo desarrollo)",
                categoria="sistema",
            )

        # 2. Ejecutar Expansión Física
        direcciones_a_expandir = (
            ["north", "south", "east", "west"] if direccion is None else [direccion]
        )
        exitos = []

        for d in direcciones_a_expandir:
            success = self.world.expandir(d, cantidad)
            exitos.append(success)

        if any(exitos):
            # 3. Actualizar Estado del Modelo
            self.mapa = self.world.mapa
            self.mapa_size = len(self.mapa)

            # Marcar que el mapa cambió estructuralmente para forzar envío en el broadcast
            self._map_dirty = True

            # IMPORTANTE: Reasignar todos los edificios de infraestructura al nuevo mapa expandido
            for edif in self.infraestructura:
                x = edif["x"]
                y = edif["y"]
                if 0 <= x < self.mapa_size and 0 <= y < self.mapa_size:
                    # Verificar si el edificio ya está en el tile
                    if not any(
                        b["id"] == edif["id"] for b in self.mapa[x][y].buildings
                    ):
                        self.mapa[x][y].buildings.append(edif)

            # Descontar fondos si corresponde
            if comprador_id and costo_total > 0:
                if comprador_id == "arquitecto":
                    self.economia["total_dinero"] -= costo_total
                else:
                    # Si el comprador fue un grupo identificado previamente, descontar ahí
                    if comprador_es_grupo and grupo:
                        if "fondos" in grupo:
                            grupo["fondos"] = max(0, grupo.get("fondos", 0) - costo_total)
                        elif "dinero" in grupo:
                            grupo["dinero"] = max(0, grupo.get("dinero", 0) - costo_total)
                        else:
                            grupo["recursos"] = max(0, grupo.get("recursos", 0) - costo_total)
                    else:
                        # Intentar descontar desde el agente/grupo mediante helper
                        ok, msg = self._descontar_costo_expansion(comprador_id, costo_total)
                        if not ok:
                            self.log(f"⚠️ [EXPANSIÓN] No se pudo descontar costo: {msg}", categoria="sistema")

            self.log(
                f"🌎 [EXPANSIÓN] Mundo expandido ({direccion or 'uniforme'}) por {comprador_id or 'sistema'}. Costo: {costo_total} MC",
                categoria="sistema",
            )
            self.notificar_cambio_estado()
            self.guardar_estado()  # Persistencia inmediata
            return (
                True,
                f"Mundo expandido exitosamente a {len(self.mapa)}x{len(self.mapa[0])}",
            )

        return False, "Error técnico al expandir el mapa"

    def _verificar_fondos_expansion(self, comprador_id):
        """Verifica los fondos disponibles para expansión."""
        if comprador_id == "arquitecto":
            return self.economia["total_dinero"], "Arquitecto"

        # Buscar grupo del comprador
        grupo_id = None
        for agente in self.agentes:
            if agente.unique_id == comprador_id:
                grupo_id = agente.grupo_id
                break

        if grupo_id and grupo_id in self.grupos_dinamicos:
            grupo = self.grupos_dinamicos[grupo_id]
            fondos_grupo = grupo.get("fondos", 0)
            return fondos_grupo, f"Grupo {grupo_id}"
        else:
            return 0, "Comprador desconocido"

    def _verificar_permisos_expansion(self, comprador_id):
        """Verifica si el comprador tiene permisos para expandir."""
        if comprador_id == "arquitecto":
            return True  # Arquitecto siempre puede

        # Solo voceroes de grupo pueden comprar terreno para su grupo
        for agente in self.agentes:
            if agente.unique_id == comprador_id:
                return agente.rol == "Vocero" and agente.grupo_id is not None

        return False

    def _descontar_costo_expansion(self, comprador_id, costo_total):
        """Descuenta el costo de expansión de los fondos correspondientes."""
        try:
            if comprador_id == "arquitecto":
                if self.economia["total_dinero"] >= costo_total:
                    self.economia["total_dinero"] -= costo_total
                    return (
                        True,
                        f"Costo descontado de fondos del Arquitecto: -{costo_total} MC",
                    )
                else:
                    return False, "Fondos insuficientes del Arquitecto"
            else:
                # Descontar de fondos del grupo
                grupo_id = None
                for agente in self.agentes:
                    if agente.unique_id == comprador_id:
                        grupo_id = agente.grupo_id
                        break

                if grupo_id and grupo_id in self.grupos_dinamicos:
                    grupo = self.grupos_dinamicos[grupo_id]
                    if grupo.get("fondos", 0) >= costo_total:
                        grupo["fondos"] -= costo_total
                        return (
                            True,
                            f"Costo descontado de fondos del grupo {grupo_id}: -{costo_total} MC",
                        )
                    else:
                        return False, f"Fondos insuficientes del grupo {grupo_id}"
                else:
                    return False, f"Grupo no encontrado para {comprador_id}"

        except Exception as e:
            return False, f"Error al descontar costo: {str(e)}"

    def comprar_terreno_grupo(self, grupo_id, direccion=None, cantidad=5):
        """
        Método para que un grupo compre terreno adicional.
        Requiere que el vocero del grupo tenga fondos suficientes.
        """
        if grupo_id not in self.grupos_dinamicos:
            return False, f"Grupo {grupo_id} no encontrado"

        # Encontrar vocero del grupo
        vocero = None
        for agente in self.agentes:
            if agente.grupo_id == grupo_id and agente.rol == "Vocero":
                vocero = agente
                break

        if not vocero:
            # Si no hay vocero, permitir que el grupo intente comprar directamente
            # (relaja el requisito de que haya un vocero presente)
            return self.expandir_mundo(direccion, cantidad, comprador_id=grupo_id)

        # Intentar expansión con el vocero como comprador
        return self.expandir_mundo(direccion, cantidad, comprador_id=vocero.unique_id)

    def _generar_terrain_type_random(self):
        """Genera un tipo de terreno aleatorio con distribución realista."""
        import random

        rand_val = random.random()
        if rand_val < 0.15:
            return TerrainType.MOUNTAIN
        elif rand_val < 0.35:
            return TerrainType.FOREST
        elif rand_val < 0.50:
            return TerrainType.WATER
        else:
            return TerrainType.GRASS

    def _asignar_recurso_random(self, tile):
        """Asigna recursos aleatorios a una tile según su tipo de terreno."""
        import random

        if tile.terrain_type == TerrainType.MOUNTAIN and random.random() < 0.3:
            tile.resource_node = "mineral"
        elif tile.terrain_type == TerrainType.FOREST and random.random() < 0.25:
            tile.resource_node = "madera"
        elif tile.terrain_type == TerrainType.WATER and random.random() < 0.2:
            tile.resource_node = "pescado"
        elif tile.terrain_type == TerrainType.GRASS and random.random() < 0.2:
            tile.resource_node = "comida"

    def comprar_terreno(self, grupo_id, direccion=None, cantidad=1):
        """
        Permite que un grupo dinámico o civilización compre terreno adyacente.

        Args:
            grupo_id: ID del grupo o civilización que compra
            direccion: Dirección de expansión ('north', 'south', 'east', 'west') o None para automática
            cantidad: Número de casillas a comprar

        Returns:
            (exito, mensaje)
        """
        # Verificar si es civilización o grupo dinámico
        grupo = self.civilizaciones.get(grupo_id) or self.grupos_dinamicos.get(grupo_id)
        if not grupo:
            return False, f"Grupo {grupo_id} no encontrado"

        # Calcular costo
        costo = self.COSTO_EXPANSION * cantidad
        if grupo.get("dinero", 0) < costo:
            return (
                False,
                f"Fondos insuficientes. Costo: {costo} MC, Disponible: {grupo.get('dinero', 0)} MC",
            )

        # Determinar dirección automática si no se especifica
        if direccion is None:
            direccion = self._encontrar_direccion_expansion(grupo_id)

        # Expandir el mundo
        exito, msg = self.expandir_mundo(direccion=direccion, cantidad=cantidad)
        if exito:
            # Descontar dinero
            grupo["dinero"] = grupo.get("dinero", 0) - costo
            self.log(
                f"💰 [COMPRA] {grupo_id} compró {cantidad} casillas en dirección {direccion} por {costo} MC",
                categoria="economia",
            )
            return (
                True,
                f"Terreno comprado exitosamente. Nuevas dimensiones: {len(self.mapa)}x{len(self.mapa[0])}",
            )

        return False, msg

    def _encontrar_direccion_expansion(self, grupo_id):
        """Encuentra la mejor dirección para expandir basado en las construcciones del grupo."""
        # Buscar construcciones del grupo en los bordes
        bordes = {"north": [], "south": [], "east": [], "west": []}
        filas = len(self.mapa)
        cols = len(self.mapa[0]) if filas > 0 else 0

        for x in range(filas):
            for y in range(cols):
                tile = self.mapa[x][y]
                for building in tile.buildings:
                    if building.get("grupo_id") == grupo_id:
                        # Esta en el borde norte?
                        if x == 0:
                            bordes["north"].append((x, y))
                        # Borde sur?
                        if x == filas - 1:
                            bordes["south"].append((x, y))
                        # Borde este?
                        if y == cols - 1:
                            bordes["east"].append((x, y))
                        # Borde oeste?
                        if y == 0:
                            bordes["west"].append((x, y))

        # Devolver la dirección con más construcciones en el borde
        mejor_direccion = max(bordes, key=lambda d: len(bordes[d]))
        if len(bordes[mejor_direccion]) > 0:
            return mejor_direccion

        # Si no hay construcciones en bordes, expansión uniforme
        return None

    def fundar_institucion(self, fundador_id, nombre, tipo):
        """Funda una nueva institución formal en el mundo."""
        fundador = next((a for a in self.agentes if a.unique_id == fundador_id), None)
        if not fundador:
            return False, "Fundador no encontrado."
        
        if fundador.dinero < 100:
            return False, f"Recursos insuficientes (100 MC requeridos, tienes {fundador.dinero:.1f})."
            
        inst_id = f"INST-{random.randint(1000, 9999)}"
        nueva_inst = Institucion(
            inst_id,
            nombre,
            tipo,
            fundador_id,
            fundador.x,
            fundador.y,
        )
        nueva_inst.vocero_id = fundador_id
        nueva_inst.miembros = [fundador_id]
        nueva_inst.recursos = 50
        nueva_inst.nivel = 1
        nueva_inst.descripcion = f"Institución de tipo {tipo} fundada por {fundador_id}."
        
        fundador.dinero -= 100
        self.instituciones[inst_id] = nueva_inst

        # Dar puntos iniciales por la fundación (avance hacia niveles)
        try:
            nueva_inst.puntos = getattr(nueva_inst, "puntos", 0.0) + 50.0
        except Exception:
            nueva_inst.puntos = 50.0
        try:
            self._maybe_level_institution(nueva_inst)
        except Exception:
            pass
        if getattr(self, "db_active", False) and getattr(self, "db", None):
            try:
                self.db.save_institution(nueva_inst, self.user_id)
            except Exception:
                pass

        # Crear una entrada de infraestructura/tile para que la institución se distinga en el mapa
        try:
            tile = self.mapa[fundador.x][fundador.y] if getattr(self, "mapa", None) else None
        except Exception:
            tile = None

        if tile is not None:
            nuevo_edif = {
                "id": f"EDIF-{len(self.infraestructura) + 1}",
                "tipo": tipo,  # Mantener el tipo (ej. 'Universidad', 'Hospital') para compatibilidad
                "institucion_id": inst_id,
                "constructor": fundador_id,
                "paso_creacion": self.paso_actual,
                "x": fundador.x,
                "y": fundador.y,
                "es_institucion": True,
            }
            # Registrar en la lista global de infraestructura y en el tile
            self.infraestructura.append(nuevo_edif)
            try:
                tile.buildings.append(nuevo_edif)
            except Exception:
                # Si el tile no tiene la propiedad buildings por algún motivo, ignorar sin romper
                pass
            # Marcar mapa como sucio para forzar refresco en frontend
            try:
                self._map_dirty = True
            except Exception:
                pass

        self.log(f"🏛️ [INSTITUCION] {fundador_id} ha fundado la institución '{nombre}' de tipo {tipo} en ({fundador.x}, {fundador.y}).", categoria="sistema")
        self.notificar_cambio_estado()
        self.guardar_estado()

        return True, inst_id


if __name__ == "__main__":
    # Configuración desde .env
    num_agentes = int(os.getenv("NUM_AGENTES", 30))
    pasos = int(os.getenv("PASOS_SIMULACION", 100))

    # Configuración de la simulación
    modelo = ModeloRelacional(num_agentes=num_agentes)
    modelo.ejecutar(pasos=pasos)
    modelo.imprimir_resumen_social()
    modelo.visualizar_resultados()
