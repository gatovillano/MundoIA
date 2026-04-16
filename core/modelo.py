import random
import math
import time
import threading
import matplotlib

matplotlib.use("Agg")  # Backend para entornos sin interfaz gráfica
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
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
from datetime import datetime, date
from psycopg2.extras import Json as _Json

from systems.herramientas import herramientas
from agents.alma import generar_alma_inicial
from agents.identity_system import generar_identidad_inicial, SistemaIdentidades
from systems.cronicas import SistemaCronicas, TipoCronica
from core.skills_manager import skill_manager
from core.skill_factory import SkillFactory
from systems.sistema_misiones import SistemaMisiones
from core.world_system import WorldSystem, WorldTile, TerrainType
from systems.historia import LibretaHistoria

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


class DatabaseManager:
    def __init__(self):
        self.conn_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "database": os.getenv("DB_NAME", "mundoia"),
            "user": os.getenv("DB_USER", "architect"),
            "password": os.getenv("DB_PASS", "mundoia_secret_2026"),
            "port": os.getenv("DB_PORT", "5434"),
        }
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = True
            logger.info(
                f"✅ Conexión establecida a {self.conn_params['host']}:{self.conn_params['port']} db={self.conn_params['database']}"
            )
            self.initialize_db()
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            return False

    def initialize_db(self):
        """Inicializa las tablas de la base de datos usando schema.sql y create_users_table.sql"""
        if not self.conn:
            return False
        try:
            for schema_file in ["schema.sql", "create_users_table.sql"]:
                schema_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "data", schema_file
                )
                if os.path.exists(schema_path):
                    with open(schema_path, "r") as f:
                        schema_sql = f.read()

                    logger.info(f"📜 Intentando ejecutar esquema desde: {schema_path}")
                    with self.conn.cursor() as cur:
                        cur.execute(schema_sql)
                        # Migraciones BDI
                        cur.execute(
                            "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS beliefs JSONB DEFAULT '[]';"
                        )
                        cur.execute(
                            "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS desires JSONB DEFAULT '[]';"
                        )
                        cur.execute(
                            "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS intentions JSONB DEFAULT '[]';"
                        )
                    logger.info(f"✅ Esquema {schema_file} verificado/inicializado.")
                else:
                    logger.warning(
                        f"⚠️ No se encontró {schema_file} en {os.path.dirname(__file__)}"
                    )

            # Migración automática: Añadir columna memoria_mensajes si no existe
            try:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS memoria_mensajes JSONB DEFAULT '[]';"
                    )
                    cur.execute(
                        "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '{}';"
                    )
                    cur.execute(
                        "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS skill_factor FLOAT DEFAULT 0.3;"
                    )
                    cur.execute(
                        "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS memoria_persistente_data JSONB DEFAULT '{}';"
                    )
                    cur.execute(
                        "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS alma JSONB DEFAULT '{}';"
                    )
                    cur.execute(
                        "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS identidad JSONB DEFAULT '{}';"
                    )
                    cur.execute(
                        "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS heartbeat_config JSONB DEFAULT '{}';"
                    )
                    cur.execute(
                        "ALTER TABLE agentes ADD COLUMN IF NOT EXISTS apps JSONB DEFAULT '{}';"
                    )
                    # Migración para logs
                    cur.execute(
                        "ALTER TABLE logs_simulacion ADD COLUMN IF NOT EXISTS subtitulos TEXT;"
                    )
                    cur.execute(
                        "ALTER TABLE logs_simulacion ADD COLUMN IF NOT EXISTS tts_text TEXT;"
                    )

                    # Migración para estado_mundo - agregar columna social_feed
                    cur.execute(
                        "ALTER TABLE estado_mundo ADD COLUMN IF NOT EXISTS social_feed JSONB DEFAULT '{}';"
                    )

                    # --- MIGRACIÓN CRÍTICA: CLAVES PRIMARIAS COMPUESTAS (Para evitar filtraciones entre usuarios) ---
                    # 1. Agentes
                    cur.execute("""
                       DO $$ BEGIN
                           IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agentes_pkey' AND contype = 'p') THEN
                               -- Verificar si ya es compuesta (id, user_id)
                               IF NOT EXISTS (
                                   SELECT 1 FROM information_schema.key_column_usage 
                                   WHERE table_name = 'agentes' AND constraint_name = 'agentes_pkey' AND column_name = 'user_id'
                               ) THEN
                                   -- LIMPIEZA PREVIA: Borrar huérfanos que impedirían la FK compuesta
                                   DELETE FROM memorias m 
                                   WHERE NOT EXISTS (SELECT 1 FROM agentes a WHERE a.id = m.agente_fuente AND a.user_id = m.user_id)
                                   OR NOT EXISTS (SELECT 1 FROM agentes a WHERE a.id = m.agente_objetivo AND a.user_id = m.user_id);
                                   
                                   DELETE FROM chat_mensajes c
                                   WHERE NOT EXISTS (SELECT 1 FROM agentes a WHERE a.id = c.agent_id AND a.user_id = c.user_id);

                                   ALTER TABLE memorias DROP CONSTRAINT IF EXISTS memorias_agente_fuente_fkey;
                                   ALTER TABLE memorias DROP CONSTRAINT IF EXISTS memorias_agente_objetivo_fkey;
                                   ALTER TABLE chat_mensajes DROP CONSTRAINT IF EXISTS chat_mensajes_agent_id_fkey;
                                   
                                   ALTER TABLE agentes DROP CONSTRAINT agentes_pkey;
                                   ALTER TABLE agentes ADD PRIMARY KEY (id, user_id);
                                   
                                   -- Re-enlazar con FK compuestas
                                   ALTER TABLE memorias ADD FOREIGN KEY (agente_fuente, user_id) REFERENCES agentes(id, user_id);
                                   ALTER TABLE memorias ADD FOREIGN KEY (agente_objetivo, user_id) REFERENCES agentes(id, user_id);
                                   ALTER TABLE chat_mensajes ADD FOREIGN KEY (agent_id, user_id) REFERENCES agentes(id, user_id);
                               END IF;
                           END IF;
                       END $$;
                   """)

                    # 2. Civilizaciones
                    cur.execute("""
                       DO $$ BEGIN
                           IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'civilizaciones_pkey' AND contype = 'p') THEN
                               IF NOT EXISTS (
                                   SELECT 1 FROM information_schema.key_column_usage 
                                   WHERE table_name = 'civilizaciones' AND constraint_name = 'civilizaciones_pkey' AND column_name = 'user_id'
                               ) THEN
                                   ALTER TABLE civilizaciones DROP CONSTRAINT civilizaciones_pkey;
                                   ALTER TABLE civilizaciones ADD PRIMARY KEY (id, user_id);
                               END IF;
                           END IF;
                       END $$;
                   """)

                    # 3. Instituciones
                    cur.execute("""
                       CREATE TABLE IF NOT EXISTS instituciones (
                           id VARCHAR(100),
                           user_id VARCHAR(50) REFERENCES usuarios(id),
                           nombre VARCHAR(100) NOT NULL,
                           tipo VARCHAR(50),
                           fundador_id VARCHAR(50),
                           lider_id VARCHAR(50),
                           miembros JSONB DEFAULT '[]',
                           x INTEGER,
                           y INTEGER,
                           recursos FLOAT DEFAULT 0.0,
                           nivel INTEGER DEFAULT 1,
                           descripcion TEXT,
                           timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           PRIMARY KEY (id, user_id)
                       );
                   """)

                    self.conn.commit()
            except Exception as e:
                logger.warning(f"Nota: Migración automática o error: {e}")
                self.conn.rollback()

            return True
        except Exception as e:
            logger.error(f"❌ Error inicializando esquema DB: {e}")
            return False

    def execute(self, query, params=None):
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
            return True
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            return False

    def create_user(self, username, password, user_id=None):
        """Crea un nuevo usuario con contraseña hasheada.

        Si se proporciona user_id, se usa ese ID (crítico para usuarios de sistema
        como 'test' cuyo ID debe coincidir con la FK de logs_simulacion, etc.).
        Si no, se genera un UUID nuevo.
        """
        try:
            if user_id is None:
                user_id = str(uuid.uuid4())
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            query = "INSERT INTO usuarios (id, username, password_hash) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING;"
            self.execute(query, (user_id, username, hashed_password.decode("utf-8")))
            return user_id
        except Exception as e:
            logger.error(f"Error creando usuario {username}: {e}")
            return None

    def verify_user(self, username, password):
        """Verifica el usuario y la contraseña."""
        query = "SELECT id, password_hash FROM usuarios WHERE username = %s;"
        result = self.execute(query, (username,))
        if result:
            user_id, hashed_password = result[0]
            if bcrypt.checkpw(
                password.encode("utf-8"), hashed_password.encode("utf-8")
            ):
                return user_id
        return None

    def ensure_user_exists(self, user_id, username=None):
        """Asegura que un usuario exista en la tabla usuarios.

        IMPORTANTE: Usa el mismo user_id al crear el usuario para garantizar
        que la FK de logs_simulacion, agentes, etc. sea válida.
        """
        query = "SELECT id FROM usuarios WHERE id = %s;"
        result = self.execute(query, (user_id,))

        if not result:
            username = username or f"user_{user_id}"
            # Pasar el user_id explícitamente para que el usuario se registre
            # con ese ID exacto (evita violación de FK en logs_simulacion, etc.)
            created_id = self.create_user(username, "default_password", user_id=user_id)
            logger.info(
                f"✅ Usuario {username} (id={created_id}) creado automáticamente en la base de datos"
            )
            return True
        return False

    def clear_database(self, user_id):
        """Borra todos los datos de la partida del usuario para permitir un reset limpio.
        Mantiene el registro del usuario en la tabla 'usuarios' y su puntaje histórico.
        El orden importa por las FK: memorias → agentes, propuestas, logs, misiones → estado_mundo, civilizaciones.
        """
        if not self.conn:
            logger.error("clear_database: sin conexión a la DB")
            return False
        try:
            with self.conn.cursor() as cur:
                # 1. Tablas que referencian a agentes
                cur.execute("DELETE FROM memorias WHERE user_id = %s;", (user_id,))
                # 1.5. Mensajes de chat interactivos
                cur.execute("DELETE FROM chat_mensajes WHERE user_id = %s;", (user_id,))
                # 2. Logs de simulación
                cur.execute(
                    "DELETE FROM logs_simulacion WHERE user_id = %s;", (user_id,)
                )
                # 3. Propuestas y leyes
                cur.execute("DELETE FROM propuestas WHERE user_id = %s;", (user_id,))
                # 4. Misiones activas del usuario
                cur.execute("DELETE FROM misiones WHERE user_id = %s;", (user_id,))
                # 5. Agentes (después de borrar memorias que los referencian)
                cur.execute("DELETE FROM agentes WHERE user_id = %s;", (user_id,))
                # 6. Civilizaciones/grupos
                cur.execute(
                    "DELETE FROM civilizaciones WHERE user_id = %s;", (user_id,)
                )
                # 7. Estado del mundo
                cur.execute("DELETE FROM estado_mundo WHERE user_id = %s;", (user_id,))
                # NOTA: No borramos 'usuarios' ni 'puntajes_usuarios' — el historial del jugador se conserva
            self.conn.commit()
            logger.info(
                f"🗑️ Datos de la partida de {user_id} limpiados correctamente de la DB."
            )
            return True
        except Exception as e:
            logger.error(f"❌ Error en clear_database para {user_id}: {e}")
            try:
                self.conn.rollback()
            except:
                pass
            return False

    def save_agent(self, agent, user_id):
        query = """
        INSERT INTO agentes (id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, civilizacion_id, alianzas, tratados, memoria_mensajes, x, y, skills, skill_factor, beliefs, desires, intentions, alma, identidad, heartbeat_config, memoria_persistente_data, apps)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            recursos = EXCLUDED.recursos,
            dinero = EXCLUDED.dinero,
            grupo_id = EXCLUDED.grupo_id,
            rol = EXCLUDED.rol,
            profesion = EXCLUDED.profesion,
            rango = EXCLUDED.rango,
            reputacion = EXCLUDED.reputacion,
            personalidad = EXCLUDED.personalidad,
            necesidades = EXCLUDED.necesidades,
            experiencia = EXCLUDED.experiencia,
            conocimientos = EXCLUDED.conocimientos,
            inventario = EXCLUDED.inventario,
            hitos = EXCLUDED.hitos,
            historial_etico = EXCLUDED.historial_etico,
            civilizacion_id = EXCLUDED.civilizacion_id,
            alianzas = EXCLUDED.alianzas,
            tratados = EXCLUDED.tratados,
            memoria_mensajes = EXCLUDED.memoria_mensajes,
            x = EXCLUDED.x,
            y = EXCLUDED.y,
            skills = EXCLUDED.skills,
            skill_factor = EXCLUDED.skill_factor,
            beliefs = EXCLUDED.beliefs,
            desires = EXCLUDED.desires,
            intentions = EXCLUDED.intentions,
            alma = EXCLUDED.alma,
            identidad = EXCLUDED.identidad,
            heartbeat_config = EXCLUDED.heartbeat_config,
            memoria_persistente_data = EXCLUDED.memoria_persistente_data,
            apps = EXCLUDED.apps;
        """
        self.execute(
            query,
            (
                str(agent.unique_id),
                user_id,
                agent.recursos,
                agent.dinero,
                agent.grupo_id,
                agent.rol,
                agent.profesion,
                agent.rango,
                agent.reputacion,
                Json(agent.personalidad),
                Json(agent.necesidades),
                Json(agent.experiencia),
                Json(agent.conocimientos),
                Json(agent.inventario),
                Json(getattr(agent, "hitos", [])),
                Json(agent.historial_etico),
                agent.civilizacion_id,
                Json(getattr(agent, "alianzas", [])),
                Json(getattr(agent, "tratados", [])),
                Json(agent.memoria.historial_mensajes),
                agent.x,
                agent.y,
                Json(agent.skills),
                agent.skill_factor,
                Json(agent.creencias.to_dict()),
                Json(agent.deseos.to_dict()),
                Json(agent.intenciones.to_dict()),
                Json(
                    agent.alma.to_dict()
                    if hasattr(agent, "alma") and agent.alma
                    else {}
                ),
                Json(
                    agent.identidad.to_dict()
                    if hasattr(agent, "identidad") and agent.identidad
                    else {}
                ),
                Json(
                    agent.heartbeat_mundo.to_dict()
                    if hasattr(agent, "heartbeat_mundo") and agent.heartbeat_mundo
                    else {}
                ),
                Json(
                    agent.memoria_persistente.to_dict()
                    if hasattr(agent, "memoria_persistente")
                    and agent.memoria_persistente
                    else {}
                ),
                Json(getattr(agent, "apps", {})),
            ),
        )

    def get_agents(self, user_id):
        query = "SELECT id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, civilizacion_id, alianzas, tratados, memoria_mensajes, x, y, skills, skill_factor, beliefs, desires, intentions, alma, identidad, heartbeat_config, memoria_persistente_data, apps FROM agentes WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_civilization(self, civ):
        query = """
        INSERT INTO civilizaciones (id, nombre, color, user_id, recursos_globales, territorio)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            nombre = EXCLUDED.nombre,
            color = EXCLUDED.color,
            recursos_globales = EXCLUDED.recursos_globales,
            territorio = EXCLUDED.territorio;
        """
        self.execute(
            query,
            (
                civ.id,
                civ.nombre,
                civ.color,
                civ.user_id,
                civ.recursos_globales,
                Json(civ.territorio),
            ),
        )

    def get_civilizations(self, user_id):
        query = "SELECT id, nombre, color, recursos_globales, territorio FROM civilizaciones WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_memory(self, owner_id, target_id, data, user_id):
        # Verificar integridad referencial para evitar errores de Foreign Key
        check_query = (
            "SELECT COUNT(*) FROM agentes WHERE id IN (%s, %s) AND user_id = %s;"
        )
        res = self.execute(check_query, (str(owner_id), str(target_id), user_id))
        if not res or res[0][0] < 2:
            return  # No guardamos si alguno de los agentes no existe en la DB

        query = """
        INSERT INTO memorias (user_id, agente_fuente, agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, agente_fuente, agente_objetivo) DO UPDATE SET
            tipo_relacion = EXCLUDED.tipo_relacion,
            fuerza = EXCLUDED.fuerza,
            recursos_percibidos = EXCLUDED.recursos_percibidos,
            grupo_percibido = EXCLUDED.grupo_percibido;
        """
        params = (
            user_id,
            str(owner_id),
            str(target_id),
            data.get("tipo"),
            data.get("fuerza", 0.0),
            data.get("recursos_vistos"),
            data.get("grupo"),
        )
        self.execute(query, params)

    def save_world_state(
        self,
        user_id,
        step,
        lore,
        seed,
        economy,
        relaciones_grupos=None,
        objetivos_grupos=None,
        mapa=None,
        infraestructura=None,
        historia=None,
        social_feed=None,
    ):
        query = """
        INSERT INTO estado_mundo (user_id, paso_actual, lore, seed, precio_recurso, indice_bursatil, total_dinero, relaciones_grupos, objetivos_grupos, mapa, infraestructura, historia, social_feed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            paso_actual = EXCLUDED.paso_actual,
            lore = EXCLUDED.lore,
            seed = EXCLUDED.seed,
            precio_recurso = EXCLUDED.precio_recurso,
            indice_bursatil = EXCLUDED.indice_bursatil,
            total_dinero = EXCLUDED.total_dinero,
            relaciones_grupos = EXCLUDED.relaciones_grupos,
            objetivos_grupos = EXCLUDED.objetivos_grupos,
            mapa = EXCLUDED.mapa,
            infraestructura = EXCLUDED.infraestructura,
            historia = EXCLUDED.historia,
            social_feed = EXCLUDED.social_feed;
        """
        params = (
            user_id,
            step,
            lore,
            seed,
            economy.get("precio_recurso", 2.0),
            economy.get("indice_bursatil", 1000.0),
            economy.get("total_dinero", 0.0),
            Json(relaciones_grupos) if relaciones_grupos else Json({}),
            Json(objetivos_grupos) if objetivos_grupos else Json({}),
            Json(mapa) if mapa else None,
            Json(infraestructura) if infraestructura else Json([]),
            Json(historia) if historia else Json({}),
            Json(social_feed) if social_feed else Json({}),
        )
        self.execute(query, params)

    def get_world_state(self, user_id):
        query = "SELECT paso_actual, lore, seed, precio_recurso, indice_bursatil, total_dinero, relaciones_grupos, objetivos_grupos, mapa, infraestructura, historia, social_feed FROM estado_mundo WHERE user_id = %s ORDER BY id DESC LIMIT 1;"
        result = self.execute(query, (user_id,))
        return result[0] if result else None

    def get_memories(self, agent_id, user_id):
        query = "SELECT agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido FROM memorias WHERE agente_fuente = %s AND user_id = %s;"
        return self.execute(query, (str(agent_id), user_id))

    def save_proposal(self, prop, user_id):
        """Guarda o actualiza una propuesta/ley."""
        # Nota: Como 'id' en la DB es SERIAL, el ON CONFLICT (id) solo sirve si pasamos el ID numerico.
        # Si la propuesta tiene un ID de string (ej: LEY-XXXX), no podemos usarlo como integer 'id'.

        votos = Json(prop.get("votos", {}))
        estado = prop.get("estado", "pendiente")
        titulo = prop.get("titulo")
        contenido = prop.get("contenido")

        # Intentar determinar si es una actualizacion o insercion
        db_id = prop.get("db_id")  # Podemos guardar el ID de DB original si existe

        if db_id:
            query = """
            UPDATE propuestas SET votos = %s, estado = %s, titulo = %s, contenido = %s
            WHERE id = %s AND user_id = %s;
            """
            self.execute(query, (votos, estado, titulo, contenido, db_id, user_id))
        else:
            query = """
            INSERT INTO propuestas (user_id, grupo_id, proponente_id, texto, tipo, votos, estado, paso_creacion, titulo, contenido)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            self.execute(
                query,
                (
                    user_id,
                    prop.get("grupo_id"),
                    prop.get("proponente_id"),
                    prop.get("texto"),
                    prop.get("tipo"),
                    votos,
                    estado,
                    prop.get("paso_creacion", 0),
                    titulo,
                    contenido,
                ),
            )

    def get_proposals(self, user_id):
        """Obtiene todas las propuestas para un usuario."""
        query = "SELECT id, grupo_id, proponente_id, texto, tipo, votos, estado, paso_creacion, titulo, contenido FROM propuestas WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_mission(self, mision, user_id):
        """Guarda una misión en la base de datos."""
        query = """
        INSERT INTO misiones (id, user_id, titulo, descripcion, tipo, dificultad, objetivo, recompensa_puntos, estado, turno_inicio, turno_limite, completada_por, turno_completada)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            objetivo = EXCLUDED.objetivo,
            estado = EXCLUDED.estado,
            completada_por = EXCLUDED.completada_por,
            turno_completada = EXCLUDED.turno_completada;
        """
        self.execute(
            query,
            (
                mision.id,
                user_id,
                mision.titulo,
                mision.descripcion,
                mision.tipo,
                mision.dificultad,
                Json(mision.objetivo),
                mision.recompensa_puntos,
                mision.estado,
                mision.turno_inicio,
                mision.turno_limite,
                mision.completada_por,
                mision.turno_completada,
            ),
        )

    def get_missions(self, user_id):
        """Obtiene las misiones de un usuario."""
        query = "SELECT id, titulo, descripcion, tipo, dificultad, objetivo, recompensa_puntos, estado, turno_inicio, turno_limite, completada_por, turno_completada FROM misiones WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_score(self, user_id, puntos):
        """Guarda el puntaje del usuario."""
        query = """
        INSERT INTO puntajes_usuarios (user_id, puntos)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET puntos = EXCLUDED.puntos;
        """
        self.execute(query, (user_id, puntos))

    def get_score(self, user_id):
        """Obtiene el puntaje del usuario."""
        query = "SELECT puntos FROM puntajes_usuarios WHERE user_id = %s;"
        result = self.execute(query, (user_id,))
        return result[0][0] if result else 0

    def get_ranking(self):
        """Obtiene el ranking global con IDs y nombres de usuario."""
        query = """
            SELECT u.id, u.username, p.puntos 
            FROM puntajes_usuarios p
            JOIN usuarios u ON p.user_id = u.id
            ORDER BY p.puntos DESC 
            LIMIT 10;
        """
        result = self.execute(query)
        # Ensure we always return an iterable (empty list on error or no connection)
        return result if isinstance(result, list) else []

    def save_log(
        self,
        user_id,
        paso,
        mensaje,
        categoria,
        pensamiento=None,
        privado_para=None,
        subtitulos=None,
        tts_text=None,
        agente_id=None,
    ):
        query = """
        INSERT INTO logs_simulacion (user_id, paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        self.execute(
            query,
            (
                user_id,
                paso,
                mensaje,
                categoria,
                pensamiento,
                privado_para,
                subtitulos,
                tts_text,
                agente_id,
            ),
        )

    def get_logs(self, user_id, limit=2000):
        query = """
        SELECT paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id
        FROM logs_simulacion WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s;
        """
        rows = self.execute(query, (user_id, limit))
        if rows:
            # Invertir para que el orden temporal sea ascendente (del más antiguo al más nuevo)
            return rows[::-1]
        return []

    def save_chat_message(self, user_id, agent_id, role, content, timestamp_utc):
        """Guarda un mensaje de chat en la base de datos."""
        query = """
        INSERT INTO chat_mensajes (user_id, agent_id, role, content, timestamp_utc)
        VALUES (%s, %s, %s, %s, %s);
        """
        self.execute(query, (user_id, agent_id, role, content, timestamp_utc))

    def get_chat_history(self, user_id, agent_id, limit=100):
        """Recupera el historial de chat entre un usuario y un agente, ordenado por tiempo."""
        query = """
        SELECT role, content, timestamp_utc
        FROM chat_mensajes
        WHERE user_id = %s AND agent_id = %s
        ORDER BY timestamp_utc ASC
        LIMIT %s;
        """
        rows = self.execute(query, (user_id, agent_id, limit))
        if not rows:
            return []
        return [
            {"role": row[0], "content": row[1], "timestamp": row[2]} for row in rows
        ]

    def save_institution(self, inst, user_id):
        """Guarda una institución en la base de datos."""
        query = """
        INSERT INTO instituciones (id, user_id, nombre, tipo, fundador_id, lider_id, miembros, x, y, recursos, nivel, descripcion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            nombre = EXCLUDED.nombre,
            tipo = EXCLUDED.tipo,
            lider_id = EXCLUDED.lider_id,
            miembros = EXCLUDED.miembros,
            recursos = EXCLUDED.recursos,
            nivel = EXCLUDED.nivel,
            descripcion = EXCLUDED.descripcion;
        """
        self.execute(
            query,
            (
                inst.id,
                user_id,
                inst.nombre,
                inst.tipo,
                inst.fundador_id,
                inst.lider_id,
                Json(inst.miembros),
                inst.x,
                inst.y,
                inst.recursos,
                inst.nivel,
                inst.descripcion,
            ),
        )

    def get_institutions(self, user_id):
        """Recupera todas las instituciones de un usuario."""
        query = "SELECT id, nombre, tipo, fundador_id, lider_id, miembros, x, y, recursos, nivel, descripcion FROM instituciones WHERE user_id = %s;"
        return self.execute(query, (user_id,))


# Cargar configuración
load_dotenv()


class Civilizacion:
    def __init__(self, id, nombre, color, user_id=None, descripcion=""):
        self.id = id
        self.nombre = nombre
        self.color = color
        self.user_id = user_id
        self.descripcion = descripcion

        # --- SISTEMA DE SUCESOS DIVINOS ---
        self.profecias_activas = []  # List of dicts: {"id", "tipo", "objetivo", "recompensa"}
        self.agente_poseido_id = None

        self.recursos_globales = 0.0
        self.territorio = []  # Lista de (x, y)
        self.tecnologias = []
        self.leyes = []
        self.tipo = "GRUPO"  # NUEVO: "GRUPO" o "CIVILIZACION"

    def __getstate__(self):
        """Define qué atributos de Civilizacion se serializan."""
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        """Define cómo se deserializa Civilizacion."""
        self.__dict__.update(state)

    def to_dict(self):
        """Convierte el objeto Civilizacion a un diccionario serializable."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "color": self.color,
            "user_id": self.user_id,
            "descripcion": self.descripcion,
            "profecias_activas": self.profecias_activas,
            "agente_poseido_id": self.agente_poseido_id,
            "recursos_globales": self.recursos_globales,
            "territorio": self.territorio,
            "tecnologias": self.tecnologias,
            "leyes": self.leyes,
            "tipo": self.tipo,
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruye un objeto Civilizacion desde un diccionario serializado."""
        if not data:
            return None
        civ = cls(
            id=data.get("id", f"CIV-{random.randint(0, 999)}"),
            nombre=data.get("nombre", "Civilización"),
            color=data.get("color", "#ffffff"),
            user_id=data.get("user_id"),
            descripcion=data.get("descripcion", ""),
        )
        civ.profecias_activas = data.get("profecias_activas", [])
        civ.agente_poseido_id = data.get("agente_poseido_id")
        civ.recursos_globales = data.get("recursos_globales", 0.0)
        civ.territorio = data.get("territorio", [])
        civ.tecnologias = data.get("tecnologias", [])
        civ.leyes = data.get("leyes", [])
        civ.tipo = data.get("tipo", "GRUPO")
        return civ


class Institucion:
    def __init__(self, id, nombre, tipo, fundador_id, x, y, user_id=None):
        self.id = id
        self.nombre = nombre
        self.tipo = (
            tipo  # "EDUCATIVA", "FINANCIERA", "SANITARIA", "CIENTIFICA", "RELIGIOSA"
        )
        self.fundador_id = fundador_id
        self.lider_id = fundador_id
        self.miembros = [fundador_id]
        self.x = x
        self.y = y
        self.recursos = 0.0
        self.nivel = 1
        self.user_id = user_id
        self.descripcion = ""

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "fundador_id": self.fundador_id,
            "lider_id": self.lider_id,
            "miembros": self.miembros,
            "x": self.x,
            "y": self.y,
            "recursos": self.recursos,
            "nivel": self.nivel,
            "user_id": self.user_id,
            "descripcion": self.descripcion,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        # Usar .get() con valores por defecto para evitar KeyErrors durante la carga de estados antiguos
        inst = cls(
            id=data.get("id", f"INST-UNKNOWN-{random.randint(0, 999)}"),
            nombre=data.get("nombre", "Institución Desconocida"),
            tipo=data.get("tipo", "CIENCIA"),
            fundador_id=data.get("fundador_id", "SISTEMA"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            user_id=data.get("user_id"),
        )
        inst.lider_id = data.get("lider_id", inst.fundador_id)
        inst.miembros = data.get("miembros", [inst.fundador_id])
        inst.recursos = data.get("recursos", 0.0)
        inst.nivel = data.get("nivel", 1)
        inst.descripcion = data.get("descripcion", "")
        return inst


class Post:
    def __init__(self, id, autor_id, contenido, tipo, temas, timestamp):
        self.id = id
        self.autor_id = autor_id
        self.contenido = contenido
        self.tipo = tipo
        self.temas = temas or []
        self.likes = 0
        self.likes_por = []
        self.comentarios = 0
        self.timestamp = timestamp


class InterestRecSys:
    def __init__(self):
        self.posts = {}  # id -> Post
        self.comentarios = {}  # post_id -> list of comments


class SocialRecSys:
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        self.interest_recsys = InterestRecSys()
        self.seguidos = {}  # follower_id -> set(followed_ids)
        self._cargar_posts_desde_db()

    def _cargar_posts_desde_db(self):
        """Carga posts desde la base de datos."""
        import json
        if not self.db:
            return
        rows = self.db.execute("""
            SELECT id, autor_id, contenido, tipo, temas, timestamp, likes, likes_por, comentarios
            FROM posts_sociales
            WHERE user_id = %s
            ORDER BY timestamp ASC
        """, (self.user_id,))
        if not rows:
            return
        for row in rows:
            post_id, autor_id, contenido, tipo, temas_json, timestamp, likes, likes_por_json, comentarios_json = row
            # Manejar valores que podrían ser ya listas o strings JSON
            if isinstance(temas_json, list):
                temas = temas_json
            elif temas_json:
                try:
                    temas = json.loads(temas_json)
                except (json.JSONDecodeError, TypeError):
                    temas = []
            else:
                temas = []
            
            if isinstance(likes_por_json, list):
                likes_por = likes_por_json
            elif likes_por_json:
                try:
                    likes_por = json.loads(likes_por_json)
                except (json.JSONDecodeError, TypeError):
                    likes_por = []
            else:
                likes_por = []
            
            if isinstance(comentarios_json, list):
                comentarios = comentarios_json
            elif comentarios_json:
                try:
                    comentarios = json.loads(comentarios_json)
                except (json.JSONDecodeError, TypeError):
                    comentarios = []
            else:
                comentarios = []
            
            post = Post(post_id, autor_id, contenido, tipo, temas, timestamp)
            post.likes = likes
            post.likes_por = likes_por
            self.interest_recsys.posts[post_id] = post
            self.interest_recsys.comentarios[post_id] = comentarios

    def crear_post(self, user_id, autor_id, contenido, tipo, temas, timestamp=None):
        import uuid
        import json
        post_id = f"post_{uuid.uuid4().hex[:12]}"
        temas = temas or []
        post = Post(post_id, autor_id, contenido, tipo, temas, timestamp or 0)
        self.interest_recsys.posts[post_id] = post

        if self.db:
            # Persistir en DB con ON CONFLICT para idempotencia
            result = self.db.execute("""
                INSERT INTO posts_sociales (id, user_id, autor_id, contenido, tipo, temas, timestamp, likes, likes_por, comentarios)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id, user_id) DO UPDATE SET
                    contenido = EXCLUDED.contenido,
                    timestamp = EXCLUDED.timestamp
            """, (post_id, user_id, autor_id, contenido, tipo, json.dumps(temas), timestamp or 0, 0, json.dumps([]), json.dumps([])))
            if result is False:
                print(f"❌ [SOCIAL] Error persistiendo post {post_id} en DB")
            else:
                print(f"✅ [SOCIAL] Post {post_id} de {autor_id} persistido en DB")

        return post

    def likear_post(self, post_id, liker_id):
        import json
        post = self.interest_recsys.posts.get(post_id)
        if post and liker_id not in post.likes_por:
            post.likes += 1
            post.likes_por.append(liker_id)
            # Actualizar en DB (solo usar post_id, no user_id)
            if self.db:
                self.db.execute("""
                    UPDATE posts_sociales
                    SET likes = %s, likes_por = %s
                    WHERE id = %s
                """, (post.likes, json.dumps(post.likes_por), post_id))
            print(f"✅ [LIKE] Post {post_id} liked by {liker_id}. Total likes: {post.likes}")
            return True
        else:
            if not post:
                print(f"⚠️ [LIKE] Post {post_id} not found in memory")
            elif liker_id in post.likes_por:
                print(f"⚠️ [LIKE] {liker_id} already liked post {post_id}")
        return False

    def follow(self, follower_id, followed_id):
        if follower_id not in self.seguidos:
            self.seguidos[follower_id] = set()
        self.seguidos[follower_id].add(followed_id)
        return True

    def unfollow(self, follower_id, followed_id):
        if follower_id in self.seguidos and followed_id in self.seguidos[follower_id]:
            self.seguidos[follower_id].remove(followed_id)
            return True
        return False

    def agregar_comentario(self, post_id, autor_id, contenido):
        import json
        if post_id not in self.interest_recsys.comentarios:
            self.interest_recsys.comentarios[post_id] = []
        comentario = {
            "id": f"comment_{len(self.interest_recsys.comentarios[post_id])}",
            "autor_id": autor_id,
            "contenido": contenido,
            "timestamp": 0,
        }
        self.interest_recsys.comentarios[post_id].append(comentario)
        post = self.interest_recsys.posts.get(post_id)
        if post:
            post.comentarios += 1
        
        # Actualizar comentarios en DB
        if self.db:
            self.db.execute("""
                UPDATE posts_sociales
                SET comentarios = %s
                WHERE id = %s AND user_id = %s
            """, (json.dumps(self.interest_recsys.comentarios[post_id]), post_id, self.user_id))

        # Retornar objeto similar a Comentario
        class Comentario:
            def __init__(self, data):
                self.id = data["id"]
                self.autor_id = data["autor_id"]
                self.contenido = data["contenido"]
                self.timestamp = data["timestamp"]

        return Comentario(comentario)

    def get_feed_hibrido(self, agente, paso_actual, limite=10):
        # Implementación básica: devolver todos los posts
        posts = list(self.interest_recsys.posts.values())
        return {
            "in_network": posts[:limite],
            "recommended": [],
            "trending": [],
            "all_posts": posts,
        }

    def to_dict(self):
        return {
            "interest_recsys": {
                "posts": {
                    pid: {
                        "id": p.id,
                        "autor_id": p.autor_id,
                        "contenido": p.contenido,
                        "tipo": p.tipo,
                        "temas": p.temas,
                        "likes": p.likes,
                        "likes_por": p.likes_por,
                        "comentarios": p.comentarios,
                        "timestamp": p.timestamp,
                    }
                    for pid, p in self.interest_recsys.posts.items()
                },
                "comentarios": self.interest_recsys.comentarios,
            },
            "seguidos": {k: list(v) for k, v in self.seguidos.items()},
        }

    def get_siguiendo(self, user_id):
        """Retorna lista de usuarios que sigue este usuario."""
        return list(self.seguidos.get(user_id, set()))

    def get_seguidores(self, user_id):
        """Retorna lista de usuarios que siguen a este usuario."""
        seguidores = []
        for follower_id, seguidos in self.seguidos.items():
            if user_id in seguidos:
                seguidores.append(follower_id)
        return seguidores

    def get_interacciones_usuario(self, user_id):
        """Retorna lista de interacciones (likes/comentarios) hechas en los posts de este usuario."""
        interacciones = []
        for post_id, post in self.interest_recsys.posts.items():
            if post.autor_id == user_id:
                # Likes
                for liker in post.likes_por:
                    interacciones.append(
                        {"tipo": "like", "post_id": post_id, "usuario": liker}
                    )
                # Comentarios
                if post_id in self.interest_recsys.comentarios:
                    for comentario in self.interest_recsys.comentarios[post_id]:
                        interacciones.append(
                            {
                                "tipo": "comentario",
                                "post_id": post_id,
                                "usuario": comentario["autor_id"],
                                "contenido": comentario["contenido"],
                            }
                        )
        return interacciones

    @classmethod
    def from_dict(cls, data, db=None, user_id=None):
        # Crear instancia sin llamar a __init__ para evitar cargar desde DB
        inst = cls.__new__(cls)
        inst.db = db
        inst.user_id = user_id
        inst.interest_recsys = InterestRecSys()
        inst.seguidos = {}
        
        if "interest_recsys" in data:
            ir_data = data["interest_recsys"]
            if "posts" in ir_data:
                for pid, p_data in ir_data["posts"].items():
                    post = Post(
                        p_data["id"],
                        p_data["autor_id"],
                        p_data["contenido"],
                        p_data["tipo"],
                        p_data.get("temas", []),
                        p_data.get("timestamp", 0),
                    )
                    post.likes = p_data.get("likes", 0)
                    post.likes_por = p_data.get("likes_por", [])
                    post.comentarios = p_data.get("comentarios", 0)
                    inst.interest_recsys.posts[pid] = post
            if "comentarios" in ir_data:
                inst.interest_recsys.comentarios = ir_data["comentarios"]
        if "seguidos" in data:
            inst.seguidos = {k: set(v) for k, v in data["seguidos"].items()}
        return inst


class Agente:
    def __init__(
        self,
        unique_id,
        modelo,
        recursos=100,
        necesidades=None,
        personalidad=None,
        civ_id=None,
        x=None,
        y=None,
    ):
        self.unique_id = unique_id
        self.modelo = modelo
        self.recursos = recursos
        self.civilizacion_id = civ_id
        self.objetivo_movimiento = None  # (x, y) a donde moverse

        # Posición en el mundo - Priorizar x, y pasados para evitar saltos al reiniciar
        if x is not None and y is not None:
            self.x = x
            self.y = y
        else:
            # Buscar una posición libre para evitar colisiones iniciales
            mapa_size = getattr(modelo, "mapa_size", 20)
            pos_encontrada = False
            for _ in range(100):  # Intentar hasta 100 veces
                nx = random.randint(0, mapa_size - 1)
                ny = random.randint(0, mapa_size - 1)
                # Verificar que no haya otro agente en esa posición
                if not any(a.x == nx and a.y == ny for a in modelo.agentes):
                    self.x = nx
                    self.y = ny
                    pos_encontrada = True
                    break
            if not pos_encontrada:
                # Si no se encontró posición libre, usar aleatoria (colisiónok)
                self.x = random.randint(0, 19)
                self.y = random.randint(0, 19)

        # Personalidad (0.0 a 1.0): extroversión, amabilidad, competitividad
        if personalidad:
            self.personalidad = personalidad
        else:
            self.personalidad = {
                "extroversión": random.random(),
                "amabilidad": random.random(),
                "competitividad": random.random(),
                "curiosidad": random.random(),
                "lealtad": random.random(),
                "prudencia": random.random(),
                "hostilidad": random.random(),
            }

        # --- CREACIONES DEL AGENTE ---
        self.apps = {}  # Aplicaciones/Código Python creado por el agente

        # Necesidades: 10.0 = Satisfecho, 0.0 = Crítico
        if necesidades:
            self.necesidades = necesidades
        else:
            self.necesidades = {
                "alimento": random.uniform(8, 10),
                "social": random.uniform(8, 10),
                "seguridad": random.uniform(8, 10),
                "descanso": 10.0,
                "entretenimiento": random.uniform(8, 10),
                "salud": 10.0,
            }

        # --- NECESIDADES INTELECTUALES (NUEVO) ---
        # Tercera dimensión: mente, expresión, debate
        self.necesidades_intelectuales = {
            "curiosidad": random.uniform(6, 9),  # Querer aprender/descubrir
            "expresion": random.uniform(6, 9),  # Querer compartir opiniones
            "debate": random.uniform(5, 8),  # Necesidad de argumentar
            "aprendizaje": random.uniform(6, 9),  # Estudiar/desarrollar habilidades
        }

        # --- CAPITAL SOCIAL (NUEVO) ---
        self.capital_social = 10.0  # 0-100 puntos
        self.seguidores = 0  # Cuántos lo siguen
        self.siguiendo = 0  # A cuántos sigue
        self.posts_publicados = 0  # Contenido creado
        self.comentarios_realizados = 0  # Engagement activo
        self.likes_recibidos = 0  # Likes en sus posts
        self.likes_dados = 0  # Likes que ha dado
        self.debates_ganados = 0  # Asambleas donde su posición prevaleció
        self.debates_perdidos = 0  # Asambleas donde perdió
        # Intereses para RecSys
        self.intereses = []  # Temas de interés [política, ciencia, arte, ...]
        self.opiniones_fuertes = {}  # {tema: nivel_fuerza 0-10}

        # --- SISTEMA DE SKILLS ---
        self.skills = {}  # Dictionary of Skill objects
        self.skill_factor = random.uniform(0.1, 0.5)  # Initial skill factor
        self.decision_cacheada = None

        # Memoria basada en Grafos
        self.memoria = MemoriaGrafica(self.unique_id)

        # Cerebro Cognitivo (TODOS los agentes ahora son inteligentes)
        self.cerebro = CerebroAvanzado(self.unique_id)

        # Nuevos atributos: Grupo y Jerarquía
        self.grupo_id = None
        self.rol = "Ciudadano"  # Rol inicial
        self.ultimo_mensaje_recibido = None  # Para responder a otros
        self.dinero = 100.0  # Nueva unidad de cambio: MundoCoins (MC)
        self.rango = 1.0  # Estatus social (influye en la influencia)
        self.conocimientos = {}  # Información compartida o descubierta
        self.planes = []  # Acuerdos con otros agentes
        self.gasto_turno = 0.0  # Control de gasto por turno
        self.inversiones = []  # [{monto, paso_inicio, interes_esperado}]
        self.alianzas = []  # Lista de IDs de agentes aliados (para compatibilidad)
        self.tratados = []  # Lista de dicts: {"socio_id": ID, "terminos": {...}, "pasos_restantes": N}
        self.inventario = {
            "comida": int(self.recursos),
            "madera": 0,
            "piedra": 0,
            "hierro": 0,
            "medicina": 0,
            "ocio": 0,
        }

        # --- SISTEMA DE PROFESIONES ---
        self.profesion = None  # "Médico", "Comerciante", "Guarda", "Explorador"
        self.experiencia = {
            "medicina": 0,
            "comercio": 0,
            "combate": 0,
            "exploracion": 0,
            "social": 0,
            "ingenieria": 0,
            "agricultura": 0,
        }
        self.hitos = []  # Lista de logros alcanzados

        # --- MODELO BDI (Belief-Desire-Intention) ---
        self.creencias = SistemaCreencias()
        self.deseos = SistemaDeseos()
        self.intenciones = SistemaIntenciones()

        # Alma (identidad profunda y evolutiva)
        self.alma = generar_alma_inicial(self.personalidad, 0)

        # Identidad (OASIS Style: Personalidad pública, OCEAN, Demográficos)
        from agents.identity_system import generar_identidad_inicial

        self.identidad = generar_identidad_inicial(self.alma.arquetipo.value, 0)
        # Sincronización BIDIRECCIONAL de nombres
        if self.alma.nombre_propio:
            self.identidad.nombre = self.alma.nombre_propio
        else:
            self.alma.nombre_propio = self.identidad.nombre

        # Historial para BDI
        self.historial_acciones_bdi = []  # List of (turno, accion)

        # --- ESTADO COGNITIVO ---
        self.reputacion = 1.0  # 0.0 a 1.0 (Prestigio social)
        self.votos_recibidos = 0
        self.historial_etico = []  # Registro de crímenes o buenas acciones

        # --- ESTADO COGNITIVO ---
        self.pensamiento_actual = "Esperando estímulos..."
        self.mensaje_arquitecto = None  # Cola prioritaria para órdenes divinas
        # --- ESTADO VITAL ---
        self.esta_vivo = True
        self.cronicas_publicadas = []  # Historial de crónicas publicadas por este agente

    def calcular_capital_social(self) -> float:
        """
        Calcula el Capital Social del agente basado en múltiples factores.
        Fórmula: ponderación de componentes sociales, engagement y participación.
        """
        # Base: seguidores con bonus por ratio de seguimiento
        ratio_follow = self.siguiendo / max(1, self.seguidores)
        base = self.seguidores * (1 + (1 / (1 + ratio_follow)))

        # Engagement: likes recibidos (peso 0.5)
        engagement = self.likes_recibidos * 0.5

        # Contenido: posts publicados (peso 2)
        contenido = self.posts_publicados * 2

        # Participación en debates (ganados - perdidos)
        debate = (self.debates_ganados * 10) - (self.debates_perdidos * 3)

        # Comentarios realizados (engagement activo)
        comentarios = self.comentarios_realizados * 1

        # Votos recibidos (participación política)
        politico = self.votos_recibidos * 0.3

        total = base + engagement + contenido + max(0, debate) + comentarios + politico

        # Normalizar a 0-100
        self.capital_social = min(100, max(0, total / 10))
        return self.capital_social

    def get_nivel_influencia(self) -> str:
        """Retorna el nivel de influencia basado en el capital social."""
        cs = self.capital_social
        if cs >= 80:
            return "Legendario"
        elif cs >= 50:
            return "Respetado"
        elif cs >= 25:
            return "Notorio"
        else:
            return "Desconocido"

    def necesidad_intelectual_critica(self) -> bool:
        """Retorna True si alguna necesidad intelectual está en nivel crítico."""
        for v in self.necesidades_intelectuales.values():
            if v < 4:
                return True
        return False

    def necesidad_social_critica(self) -> bool:
        """Retorna True si la necesidad social está en nivel crítico."""
        return self.necesidades.get("social", 5) < 4

    def _evaluar_tipo_accion_necesidades(self) -> str:
        """
        Evalúa las necesidades del agente y retorna el tipo de acción prioritaria.
        Retorna: "SURVIVAL", "SOCIAL_REQUIRED", "INTELLECTUAL", "FREE_CHOICE"
        """
        # Supervivencia crítica
        if (
            self.necesidades.get("alimento", 5) < 3
            or self.necesidades.get("salud", 5) < 3
        ):
            return "SURVIVAL"

        # Necesidad social crítica - debe interactuar
        if self.necesidades.get("social", 5) < 4:
            return "SOCIAL_REQUIRED"

        # Necesidad intelectual crítica - debe expresar/aprender
        if self.necesidad_intelectual_critica():
            return "INTELLECTUAL"

        # Libre elección
        return "FREE_CHOICE"

    def necesidad_fisica_critica(self) -> bool:
        """Retorna True si alguna necesidad física está en nivel crítico."""
        return (
            self.necesidades.get("alimento", 5) < 4
            or self.necesidades.get("salud", 5) < 4
            or self.necesidades.get("descanso", 5) < 4
        )

    def __getstate__(self):
        """
        Define qué atributos del Agente se serializan.
        Excluye 'modelo' para evitar referencias circulares y 'cerebro' ya que es recreable.
        Serializa los datos de 'memoria' en lugar del objeto completo.
        """
        state = self.__dict__.copy()
        del state["modelo"]
        del state["cerebro"]
        state["memoria_data"] = self.memoria.exportar_datos()
        return state

    def __setstate__(self, state):
        """
        Define cómo se deserializa el Agente.
        Reconstruye 'memoria' y 'cerebro'. 'modelo' se reasigna externamente.
        """
        self.unique_id = state[
            "unique_id"
        ]  # Asegurar que unique_id se establece primero
        self.__dict__.update(state)
        self.memoria = MemoriaGrafica(self.unique_id)
        if "memoria_data" in state:
            self.memoria.cargar_datos(state["memoria_data"])
        self.cerebro = CerebroAvanzado(self.unique_id)
        # 'modelo' se reasigna después de la carga completa de todos los agentes
        self.modelo = (
            None  # Placeholder, será reasignado por ModeloRelacional.cargar_estado()
        )

    def to_dict(self):
        """Convierte el objeto Agente a un diccionario serializable."""
        return {
            "unique_id": self.unique_id,
            "recursos": self.recursos,
            "civilizacion_id": self.civilizacion_id,
            "objetivo_movimiento": self.objetivo_movimiento,
            "x": self.x,
            "y": self.y,
            "necesidades": self.necesidades,
            "personalidad": self.personalidad,
            "memoria_data": self.memoria.exportar_datos(),
            "grupo_id": self.grupo_id,
            "rol": self.rol,
            "ultimo_mensaje_recibido": self.ultimo_mensaje_recibido,
            "dinero": self.dinero,
            "rango": self.rango,
            "conocimientos": self.conocimientos,
            "planes": self.planes,
            "gasto_turno": self.gasto_turno,
            "inversiones": self.inversiones,
            "alianzas": self.alianzas,
            "tratados": self.tratados,
            "inventario": self.inventario,
            "profesion": self.profesion,
            "experiencia": self.experiencia,
            "hitos": self.hitos,
            "reputacion": self.reputacion,
            "votos_recibidos": self.votos_recibidos,
            "historial_etico": self.historial_etico,
            "pensamiento_actual": self.pensamiento_actual,
            "mensaje_arquitecto": self.mensaje_arquitecto,
            "esta_vivo": self.esta_vivo,
            "skills": {
                k: v if isinstance(v, dict) else v.to_dict()
                for k, v in self.skills.items()
            },
            "skill_factor": self.skill_factor,
            "color": self.modelo.civilizaciones[self.grupo_id].color
            if self.grupo_id and self.grupo_id in self.modelo.civilizaciones
            else "#ffffff",
            "beliefs": self.creencias.to_dict(),
            "desires": self.deseos.to_dict(),
            "intentions": self.intenciones.to_dict(),
            "historial_acciones_bdi": self.historial_acciones_bdi,
            # === MUNDOVIVO: Serialización de subsistemas ===
            "identidad": self.identidad.to_dict()
            if hasattr(self, "identidad") and self.identidad
            else None,
            "memoria_persistente_data": self.memoria_persistente.to_dict()
            if hasattr(self, "memoria_persistente") and self.memoria_persistente
            else {},
            "alma": self.alma.to_dict()
            if hasattr(self, "alma") and self.alma
            else None,
            "heartbeat_config": self.heartbeat_mundo.to_dict()
            if hasattr(self, "heartbeat_mundo") and self.heartbeat_mundo
            else None,
            "cronicas_publicadas": [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in getattr(self, "cronicas_publicadas", [])
            ],
            "apps": getattr(self, "apps", {}),
            # === FIN MUNDOVIVO ===
            # === CAPITAL SOCIAL E INTELECTUAL ===
            "capital_social": getattr(self, "capital_social", 10.0),
            "seguidores": getattr(self, "seguidores", 0),
            "siguiendo": getattr(self, "siguiendo", 0),
            "posts_publicados": getattr(self, "posts_publicados", 0),
            "comentarios_realizados": getattr(self, "comentarios_realizados", 0),
            "likes_recibidos": getattr(self, "likes_recibidos", 0),
            "likes_dados": getattr(self, "likes_dados", 0),
            "debates_ganados": getattr(self, "debates_ganados", 0),
            "debates_perdidos": getattr(self, "debates_perdidos", 0),
            "intereses": getattr(self, "intereses", []),
            "opiniones_fuertes": getattr(self, "opiniones_fuertes", {}),
            "necesidades_intelectuales": getattr(
                self,
                "necesidades_intelectuales",
                {"curiosidad": 6, "expresion": 6, "debate": 5, "aprendizaje": 6},
            ),
        }

    @classmethod
    def from_dict(cls, data, modelo_instance):
        """Reconstruye un objeto Agente desde un diccionario serializado."""
        agente = cls(
            unique_id=data["unique_id"],
            modelo=modelo_instance,  # Re-establecer la referencia al modelo
            recursos=data.get("recursos", 100),
            necesidades=data.get("necesidades"),
            personalidad=data.get("personalidad"),
            civ_id=data.get("civilizacion_id"),
            x=data.get("x"),
            y=data.get("y"),
        )
        # Actualizar otros atributos
        agente.objetivo_movimiento = data.get("objetivo_movimiento")
        agente.grupo_id = data.get("grupo_id")
        agente.rol = data.get("rol")
        agente.ultimo_mensaje_recibido = data.get("ultimo_mensaje_recibido")
        agente.dinero = data.get("dinero")
        agente.rango = data.get("rango")
        agente.conocimientos = data.get("conocimientos", {})
        agente.planes = data.get("planes", [])
        agente.gasto_turno = data.get("gasto_turno")
        agente.inversiones = data.get("inversiones", [])
        agente.alianzas = data.get("alianzas", [])
        agente.tratados = data.get("tratados", [])
        agente.inventario = data.get("inventario", {})
        agente.profesion = data.get("profesion")
        agente.experiencia = data.get("experiencia", {})
        agente.hitos = data.get("hitos", [])
        agente.reputacion = data.get("reputacion")
        agente.votos_recibidos = data.get("votos_recibidos")
        agente.historial_etico = data.get("historial_etico", [])
        agente.pensamiento_actual = data.get("pensamiento_actual")
        agente.mensaje_arquitecto = data.get("mensaje_arquitecto")
        agente.esta_vivo = data.get("esta_vivo", True)
        agente.skills = data.get("skills", {})
        agente.skill_factor = data.get("skill_factor", 0.3)

        from agents.bdi_components import (
            SistemaCreencias,
            SistemaDeseos,
            SistemaIntenciones,
        )

        # Cargar BDI de forma robusta con claves en español e inglés
        bdi_beliefs = data.get("beliefs") or data.get("creencias")
        if bdi_beliefs and isinstance(bdi_beliefs, dict):
            agente.creencias = SistemaCreencias.from_dict(bdi_beliefs)

        bdi_desires = data.get("desires") or data.get("deseos")
        if bdi_desires and isinstance(bdi_desires, dict):
            agente.deseos = SistemaDeseos.from_dict(bdi_desires)

        bdi_intentions = data.get("intentions") or data.get("intenciones")
        if bdi_intentions and isinstance(bdi_intentions, dict):
            agente.intenciones = SistemaIntenciones.from_dict(bdi_intentions)

        if "historial_acciones_bdi" in data:
            agente.historial_acciones_bdi = data["historial_acciones_bdi"]

        if "memoria_data" in data:
            agente.memoria.cargar_datos(data["memoria_data"])

        # === MUNDOVIVO: Deserialización de subsistemas ===
        nombre_agente = data.get("nombre", str(agente.unique_id))

        if data.get("identidad"):
            from agents.identity_system import generar_identidad_inicial

            agente.identidad = generar_identidad_inicial(nombre_agente, 0)
            agente.identidad.actualizar_desde_dict(data["identidad"])

        if data.get("memoria_persistente_data"):
            from systems.memoria_persistente import MemoriaPersistente

            agente.memoria_persistente = MemoriaPersistente(
                agente_id=agente.unique_id,
                user_id=getattr(modelo_instance, "user_id", "default"),
                data=data["memoria_persistente_data"],
            )
        else:
            from systems.memoria_persistente import MemoriaPersistente

            agente.memoria_persistente = MemoriaPersistente(
                agente_id=agente.unique_id,
                user_id=getattr(modelo_instance, "user_id", "default"),
            )

        alma_data = data.get("alma") or data.get("alma_estado")
        if alma_data:
            from agents.alma import Alma

            agente.alma = Alma.from_dict(alma_data)

        if data.get("heartbeat_config"):
            from systems.heartbeat import RitmoVital

            agente.heartbeat_mundo = RitmoVital.from_dict(
                data["heartbeat_config"], personalidad=agente.personalidad
            )

        agente.cronicas_publicadas = []
        for c_data in data.get("cronicas_publicadas", []):
            if isinstance(c_data, dict):
                from systems.cronicas import Cronica

                agente.cronicas_publicadas.append(Cronica.from_dict(c_data))
            else:
                agente.cronicas_publicadas.append(c_data)
        # === FIN MUNDOVIVO ===

        # === CAPITAL SOCIAL E INTELECTUAL ===
        agente.capital_social = data.get("capital_social", 10.0)
        agente.seguidores = data.get("seguidores", 0)
        agente.siguiendo = data.get("siguiendo", 0)
        agente.posts_publicados = data.get("posts_publicados", 0)
        agente.comentarios_realizados = data.get("comentarios_realizados", 0)
        agente.likes_recibidos = data.get("likes_recibidos", 0)
        agente.likes_dados = data.get("likes_dados", 0)
        agente.debates_ganados = data.get("debates_ganados", 0)
        agente.debates_perdidos = data.get("debates_perdidos", 0)
        agente.intereses = data.get("intereses", [])
        agente.opiniones_fuertes = data.get("opiniones_fuertes", {})
        if "necesidades_intelectuales" in data:
            agente.necesidades_intelectuales = data["necesidades_intelectuales"]
        else:
            agente.necesidades_intelectuales = {
                "curiosidad": random.uniform(6, 9),
                "expresion": random.uniform(6, 9),
                "debate": random.uniform(5, 8),
                "aprendizaje": random.uniform(6, 9),
            }

        return agente

    @synchronized
    def decir(
        self,
        mensaje,
        pensamiento=None,
        privado_para=None,
        para_grupo=False,
        global_broadcast=False,
    ):
        """Imprime un mensaje directo, privado, para el grupo o global."""
        prefijo = f"[{self.unique_id}]"

        # Actualizar pensamiento actual si se proporciona
        if pensamiento:
            self.pensamiento_actual = pensamiento

        # --- EVOLUCIÓN ESPIRITUAL ---
        # Hablar o pensar es una experiencia que hace evolucionar el alma
        if hasattr(self, "alma") and self.alma:
            from agents.alma import ExperienciaClave

            exp = ExperienciaClave(
                descripcion=f"Emitió o procesó un mensaje: {mensaje[:50]}...",
                turno=getattr(self.modelo, "paso_actual", 0),
                intensidad=0.2,  # Intensidad baja pero constante
                tipo="reflexion",  # Un tipo nuevo para crecimiento constante
            )
            self.alma.evolucionar(exp)

        # Determinar el tipo de mensaje y su alcance
        if global_broadcast:
            prefijo = f"📢 {prefijo} (ANUNCIO GLOBAL)"
            privado_para = None  # Los mensajes globales no son privados
        elif para_grupo and self.grupo_id:
            prefijo = f"👥 {prefijo} (Para Facción {self.grupo_id})"
            privado_para = f"GRUPO:{self.grupo_id}"
        elif privado_para:
            prefijo = f"🔒 {prefijo} (Privado para {privado_para})"
        elif self.personalidad["amabilidad"] > 0.7:
            prefijo = f"😇 {prefijo}"
        elif self.personalidad["competitividad"] > 0.7:
            prefijo = f"👿 {prefijo}"
        else:
            prefijo = f"🤖 {prefijo}"

        self.modelo.log(
            f'{prefijo}: "{mensaje}"',
            categoria="dialogo",
            tts_text=mensaje,
            pensamiento=pensamiento,
            privado_para=privado_para,
            agente_id=self.unique_id,
        )

        # --- REGISTRO EN MEMORIA EPISÓDICA ---
        # Guardar en mi propia memoria que he dicho esto
        self.memoria.registrar_mensaje(self.unique_id, mensaje)

        # --- DISTRIBUCIÓN DE MENSAJES ---
        packet = {
            "emisor": self.unique_id,
            "contenido": mensaje,
            "tipo": "GLOBAL"
            if global_broadcast
            else "ASAMBLEA"
            if not privado_para and not para_grupo
            else "DIRECTO",
        }

        # Si es un mensaje global, enviarlo a TODOS los agentes
        if global_broadcast:
            for agent in self.modelo.agentes:
                if agent.unique_id != self.unique_id:
                    agent.ultimo_mensaje_recibido = packet
                    agent.memoria.registrar_mensaje(self.unique_id, mensaje)

        # Si es un mensaje de grupo, enviarlo a los miembros de la facción
        elif para_grupo and self.grupo_id:
            for agent in self.modelo.agentes:
                if (
                    agent.grupo_id == self.grupo_id
                    and agent.unique_id != self.unique_id
                ):
                    agent.ultimo_mensaje_recibido = packet
                    agent.memoria.registrar_mensaje(self.unique_id, mensaje)

        # Si es privado, enviarlo solo al destinatario
        elif privado_para:
            dest_id = privado_para
            dest = next(
                (a for a in self.modelo.agentes if a.unique_id == dest_id), None
            )
            if dest:
                dest.ultimo_mensaje_recibido = packet
                dest.memoria.registrar_mensaje(self.unique_id, mensaje)

        # Si es un mensaje "en voz alta" (asamblea/vecinos), lo oyen los cercanos
        else:
            for agent in self.modelo.agentes:
                if agent.unique_id != self.unique_id:
                    # Distancia de audición (ej. 3 casillas)
                    dist = abs(self.x - agent.x) + abs(self.y - agent.y)
                    if dist <= 3:
                        agent.ultimo_mensaje_recibido = packet
                        agent.memoria.registrar_mensaje(self.unique_id, mensaje)
            return

        # --- SISTEMA DE ASAMBLEA GLOBAL ---
        # Si hay una asamblea activa, los mensajes públicos llegan a TODOS
        active_assemblies = [
            a
            for a in self.modelo.asambleas_globales
            if a.get("estado") in ["DEBATE", "VOTACION"]
        ]
        if active_assemblies and not privado_para and not para_grupo:
            packet["tipo"] = "ASAMBLEA"
            packet["contenido"] = f"[ASAMBLEA] {mensaje}"
            # Broadcast a todos los demás agentes
            for agent in self.modelo.agentes:
                if agent.unique_id != self.unique_id:
                    agent.ultimo_mensaje_recibido = packet

    @synchronized
    def interactuar(self, otro_agente, tipo_interaccion="social", mensaje_enviado=None):
        """Define cómo el agente interactúa con otro. La respuesta del otro agente es asíncrona (en su propio turno)."""

        # El otro agente guarda el mensaje para su fase de pensamiento/respuesta
        if mensaje_enviado:
            otro_agente.ultimo_mensaje_recibido = {
                "emisor": self.unique_id,
                "contenido": mensaje_enviado,
            }

        if tipo_interaccion == "SOCIALIZAR" or tipo_interaccion == "social":
            self.necesidades["social"] = min(
                10.0, self.necesidades["social"] + 3.0
            )  # Socializar satisface una necesidad vital
            self.reputacion = min(
                1.0, self.reputacion + 0.01
            )  # Socializar mejora reputación
            # Ganar experiencia social
            self.ganar_experiencia("social", 1)
            hostilidad_total = self.personalidad.get(
                "hostilidad", 0.5
            ) + otro_agente.personalidad.get("hostilidad", 0.5)
            afinidad_base = 0.2 * (
                self.personalidad["amabilidad"] + otro_agente.personalidad["amabilidad"]
            ) - (0.15 * hostilidad_total)

            if otro_agente.dinero > self.dinero * 1.5:
                afinidad_base -= 0.1 * self.personalidad.get("hostilidad", 0.5)

            self.memoria.registrar_interaccion(
                otro_agente.unique_id,
                "amigo" if afinidad_base > 0 else "conocido",
                afinidad_base,
                otro_agente.recursos,
                otro_agente.grupo_id,
            )
            self.modelo.log(
                f"  🤝 [SOCIAL] Agente {self.unique_id} socializa con {otro_agente.unique_id}. Afinidad: {afinidad_base:.2f}",
                categoria="social",
            )

        elif tipo_interaccion == "COMPETIR":
            self.ganar_experiencia("combate", 1)
            self.reputacion = max(0.0, self.reputacion - 0.05)

            # El ataque/competencia daña la relación
            self.memoria.registrar_interaccion(
                otro_agente.unique_id,
                "enemigo",
                -0.5,
                otro_agente.recursos,
                otro_agente.grupo_id,
            )
            otro_agente.memoria.registrar_interaccion(
                self.unique_id, "enemigo", -0.5, self.recursos, self.grupo_id
            )

            exito = random.random() * self.rango > random.random() * otro_agente.rango
            if exito:
                robo = 5
                self.recursos += robo
                otro_agente.recursos -= robo

                # Robar items del inventario
                items_probables = [
                    k for k, v in otro_agente.inventario.items() if v > 0
                ]
                if items_probables and random.random() < 0.4:
                    item = random.choice(items_probables)
                    otro_agente.inventario[item] -= 1
                    self.inventario[item] = self.inventario.get(item, 0) + 1
                    self.modelo.log(
                        f"  🏴‍☠️ [ROBO] Agente {self.unique_id} le arrebató {item} a {otro_agente.unique_id}!",
                        categoria="conflict",
                    )

                self.modelo.log(
                    f"  ⚔️ [CONFLICTO] Agente {self.unique_id} robó recursos a {otro_agente.unique_id}.",
                    categoria="conflict",
                )
            else:
                self.modelo.log(
                    f"  🛡️ [FALLO] Agente {self.unique_id} intentó robar a {otro_agente.unique_id} pero falló.",
                    categoria="conflict",
                )

        elif tipo_interaccion == "COMERCIAR":
            # Lógica de comercio: si tengo mucho de algo y el otro tiene dinero, vendo
            items_vender = [k for k, v in self.inventario.items() if v > 2]
            if items_vender and otro_agente.dinero >= 10:
                item = random.choice(items_vender)
                precio = random.randint(5, 15)
                self.inventario[item] -= 1
                otro_agente.inventario[item] = otro_agente.inventario.get(item, 0) + 1
                self.dinero += precio
                otro_agente.dinero -= precio
                self.modelo.log(
                    f"  💰 [COMERCIO] Agente {self.unique_id} vendió {item} a {otro_agente.unique_id} por {precio} MC.",
                    categoria="economia",
                )
                self.ganar_experiencia("comercio", 2)
                self.memoria.registrar_interaccion(
                    otro_agente.unique_id,
                    "amigo",
                    0.3,
                    otro_agente.recursos,
                    otro_agente.grupo_id,
                )
            else:
                self.modelo.log(
                    f"  🤝 [COMERCIO] Agente {self.unique_id} intentó comerciar con {otro_agente.unique_id} pero no hubo acuerdo.",
                    categoria="economia",
                )

        elif tipo_interaccion == "ALIANZA":
            self.formar_alianza(otro_agente)
            self.ganar_experiencia("social", 2)
            self.decir(
                f"¡Hemos sellado una alianza estratégica con {otro_agente.unique_id}!",
                pensamiento="La unión hace la fuerza. Juntos somos imparables.",
            )

        elif tipo_interaccion == "ATACAR" or tipo_interaccion == "atacar":
            self.ganar_experiencia("combate", 2)
            self.reputacion = max(0.0, self.reputacion - 0.2)

            # El ataque siempre destruye la relación
            self.memoria.registrar_interaccion(
                otro_agente.unique_id,
                "enemigo",
                -1.0,
                otro_agente.recursos,
                otro_agente.grupo_id,
            )
            otro_agente.memoria.registrar_interaccion(
                self.unique_id, "enemigo", -1.0, self.recursos, self.grupo_id
            )

            # Cálculo de daño
            daño_base = 2.0 + (self.experiencia["combate"] * 0.5)
            exito = random.random() > 0.3  # 70% éxito

            if exito:
                daño_final = daño_base * random.uniform(1, 2)
                self.modelo.log(
                    f"  ⚔️ [ATAQUE] ¡Agente {self.unique_id} ha ATACADO violentamente a {otro_agente.unique_id} causando {daño_final:.1f} de daño!",
                    categoria="conflict",
                )
                otro_agente.recibir_daño(daño_final, f"ataque de {self.unique_id}")
                self.decir(
                    f"¡Prepárate para la derrota, {otro_agente.unique_id}! No toleraré tu presencia.",
                    pensamiento="Eliminar competencia es necesario para mi supremacía.",
                )
            else:
                counter_daño = 1.0
                self.recibir_daño(
                    counter_daño, f"contraataque de {otro_agente.unique_id}"
                )
                self.modelo.log(
                    f"  🛡️ [FALLO] Agente {self.unique_id} falló su ataque y recibió un golpe de {counter_daño}.",
                    categoria="conflict",
                )

        elif tipo_interaccion == "DECLARAR_GUERRA":
            if self.grupo_id and otro_agente.grupo_id:
                exito, msg = self.modelo.declarar_guerra(
                    self.grupo_id, otro_agente.grupo_id
                )
                self.decir(
                    f"🚩 {msg}" if exito else f"⚠️ No pude declarar la guerra: {msg}",
                    global_broadcast=True,
                )

        elif tipo_interaccion == "NEGOCIAR_PAZ":
            if self.grupo_id and otro_agente.grupo_id:
                exito, msg = self.modelo.finalizar_guerra(
                    self.grupo_id, otro_agente.grupo_id
                )
                self.decir(
                    f"🕊️ {msg}" if exito else f"⚠️ La negociación de paz falló: {msg}",
                    global_broadcast=True,
                )

        # --- IMPACTO DIPLOMÁTICO ---
        if (
            self.grupo_id
            and otro_agente.grupo_id
            and self.grupo_id != otro_agente.grupo_id
        ):
            cambio_grupal = (
                0.05
                if (
                    tipo_interaccion == "SOCIALIZAR"
                    or tipo_interaccion == "social"
                    or tipo_interaccion == "ALIANZA"
                )
                else -0.1
            )
            self.modelo.actualizar_relacion_grupal(
                self.grupo_id, otro_agente.grupo_id, cambio_grupal
            )

    @synchronized
    def atacar(self, otro_agente):
        """Ataca directamente a otro agente (mando manual)."""
        return self.interactuar(otro_agente, "ATACAR")

    @synchronized
    def curar(self):
        """Usa medicinas del inventario para recuperar salud."""
        if self.inventario.get("medicina", 0) > 0:
            self.inventario["medicina"] -= 1
            recuperacion = 3.0 + (self.experiencia.get("medicina", 0) * 0.5)
            self.necesidades["salud"] = min(
                10.0, self.necesidades["salud"] + recuperacion
            )
            self.modelo.log(
                f"💊 [CURACION] Agente {self.unique_id} usó medicina. Salud: {self.necesidades['salud']:.1f}",
                categoria="salud",
            )
            return True, f"Salud recuperada a {self.necesidades['salud']:.1f}"
        return False, "No tienes medicinas"

    @synchronized
    def comer(self):
        """Consume comida del inventario."""
        if self.inventario.get("comida", 0) > 0:
            self.inventario["comida"] -= 1
            self.necesidades["alimento"] = min(10.0, self.necesidades["alimento"] + 4.0)
            self.modelo.log(
                f"🍎 [ALIMENTO] Agente {self.unique_id} ha comido. Alimento: {self.necesidades['alimento']:.1f}",
                categoria="alimentos",
            )
            return True, "Hambre saciada"
        return False, "No tienes comida"

    @synchronized
    def descansar(self):
        """Acción manual de descanso profundo."""
        self.necesidades["descanso"] = min(10.0, self.necesidades["descanso"] + 5.0)
        self.modelo.log(
            f"💤 [DESCANSO] Agente {self.unique_id} ha descansado profundamente.",
            categoria="state",
        )
        return True, "Energía recuperada"

    @synchronized
    def explorar(self):
        """Explora el entorno cercano para ganar experiencia y recursos aleatorios."""
        if self.necesidades["descanso"] < 2.0:
            return False, "Demasiado cansado para explorar"

        self.necesidades["descanso"] -= 1.5
        self.ganar_experiencia("exploracion", 3)

        if random.random() < 0.3:
            hallazgo = random.choice(["madera", "piedra", "comida"])
            cant = random.randint(1, 3)
            self.inventario[hallazgo] = self.inventario.get(hallazgo, 0) + cant
            self.modelo.log(
                f"🔍 [EXPLORACION] Agente {self.unique_id} encontró {cant} de {hallazgo}!",
                categoria="info",
            )
            return True, f"Encontraste {cant} {hallazgo}"

        self.modelo.log(
            f"🔍 [EXPLORACION] Agente {self.unique_id} exploró la zona pero no halló nada especial.",
            categoria="info",
        )
        return True, "Zona explorada"

    @synchronized
    def estudiar(self):
        """Estudia en la ubicación actual si hay una universidad."""
        tile = self.modelo.mapa[self.x][self.y]
        tiene_uni = any(b.get("tipo") == "Universidad" for b in tile.buildings)

        if tiene_uni:
            self.ganar_experiencia("ciencia", 5)
            self.skill_factor = min(1.0, self.skill_factor + 0.02)
            self.modelo.log(
                f"📚 [ESTUDIO] Agente {self.unique_id} está estudiando en la Universidad. Factor habilidad: {self.skill_factor:.2f}",
                categoria="info",
            )
            return True, "Conocimiento aumentado"
        return False, "No hay una Universidad aquí"

    @synchronized
    def investigar(self):
        """Investigación teórica para mejorar el factor de habilidad."""
        if self.necesidades["alimento"] < 3.0:
            return False, "Demasiado hambre para investigar"

        self.necesidades["entretenimiento"] = max(
            0, self.necesidades["entretenimiento"] - 1.0
        )
        self.ganar_experiencia("investigacion", 4)
        self.skill_factor = min(1.0, self.skill_factor + 0.01)
        self.modelo.log(
            f"🧬 [INVESTIGACION] Agente {self.unique_id} realiza investigación avanzada.",
            categoria="info",
        )
        return True, "Investigación completada"

    @synchronized
    def opinar(self, mensaje):
        """Envía una opinión formal a la asamblea actual."""
        active_assemblies = [
            a for a in self.modelo.asambleas_globales if a.get("estado") == "DEBATE"
        ]
        if not active_assemblies:
            return False, "No hay asambleas en fase de debate"

        # Usar el prefijo estándar para que el sistema lo reconozca
        self.decir(f"🗣️ [OPINION ASAMBLEA] {mensaje}")
        return True, "Opinión enviada a la asamblea"

    @synchronized
    def fundar_institucion(self, nombre, tipo):
        """Llama al modelo para fundar una institución (requiere 100 MC)."""
        return self.modelo.fundar_institucion(self.unique_id, nombre, tipo)

    @synchronized
    def fundar_grupo(self, nombre_grupo, descripcion):
        """El agente crea un nuevo grupo con una idea central y se convierte en líder."""
        if not nombre_grupo or not descripcion:
            self.modelo.log(
                f"⚠️ [RECHAZADO] Agente {self.unique_id} intentó fundar un grupo sin nombre o descripción.",
                categoria="sistema",
            )
            return None

        # Comprobar si el nombre es genérico o demasiado corto
        palabras_nombre = nombre_grupo.split()
        if len(palabras_nombre) < 1:
            return None

        # Lista de nombres genéricos prohibidos
        prohibidos = [
            "grupo",
            "clan",
            "tribu",
            "alianza",
            "equipo",
            "faccion",
            "facción",
            "mi grupo",
            "el grupo",
        ]
        if nombre_grupo.lower().strip() in prohibidos:
            self.modelo.log(
                f"⚠️ [RECHAZADO] Agente {self.unique_id} usó un nombre demasiado genérico: '{nombre_grupo}'.",
                categoria="sistema",
            )
            return None

        patron_generico = (
            f"(grupo|clan|tribu|equipo|alianza) de {self.unique_id}".lower()
        )
        if (
            patron_generico in nombre_grupo.lower()
            or nombre_grupo.lower() == f"grupo de {self.unique_id}".lower()
            or len(nombre_grupo) < 4
        ):
            self.modelo.log(
                f"⚠️ [RECHAZADO] Agente {self.unique_id} intentó usar un nombre inválido o genérico: '{nombre_grupo}'.",
                categoria="sistema",
            )
            return None

        if len(descripcion) < 15:
            self.modelo.log(
                f"⚠️ [RECHAZADO] Agente {self.unique_id} proporcionó una misión demasiado corta: '{descripcion}'.",
                categoria="sistema",
            )
            return None

        if self.modelo.grupos_creados_este_paso >= 3:
            self.modelo.log(
                f"⚠️ [LIMITE] Agente {self.unique_id} intentó fundar un grupo, pero se alcanzó el límite de 3 por turno.",
                categoria="sistema",
            )
            return None
        # Generar un ID basado en algo más que random para evitar colisiones si hay muchos
        nuevo_grupo_id = f"G-{random.randint(100, 999)}"

        # Intentar obtener un color único que no esté en uso por otra civilización
        colores_en_uso = [c.color for c in self.modelo.civilizaciones.values()]
        nuevo_color = self.modelo.colores_paleta[0]  # Default

        for color in self.modelo.colores_paleta:
            if color not in colores_en_uso:
                nuevo_color = color
                break
        else:
            # Si todos están en uso, usar uno determinista basado en el ID
            color_idx = hash(nuevo_grupo_id) % len(self.modelo.colores_paleta)
            nuevo_color = self.modelo.colores_paleta[color_idx]

        # Asegurar que el nombre del grupo sea único
        nombres_en_uso = [c.nombre for c in self.modelo.civilizaciones.values()]
        nombre_final = nombre_grupo

        # Si el nombre ya existe, agregar un número para hacerle único
        if nombre_final in nombres_en_uso:
            contador = 1
            while True:
                nombre_generado = f"{nombre_grupo} {contador}"
                if nombre_generado not in nombres_en_uso:
                    nombre_final = nombre_generado
                    break
                contador += 1

        self.modelo.civilizaciones[nuevo_grupo_id] = Civilizacion(
            id=nuevo_grupo_id,
            nombre=nombre_final,
            color=nuevo_color,
            user_id=getattr(self.modelo, "user_id", None),
            descripcion=descripcion,
        )
        # Asegurar que aparezca en el broadcast como grupo dinámico
        self.modelo.objetivos_grupos[nuevo_grupo_id] = descripcion

        self.grupo_id = nuevo_grupo_id
        self.civilizacion_id = nuevo_grupo_id
        self.rol = "Líder"
        self.modelo.log(
            f"🚩 [FUNDACION] Agente {self.unique_id} ha fundado el grupo '{nombre_final}' con el objetivo: {descripcion}",
            categoria="consenso",
        )

        # ACTUAlIZACIÓN INMEDIATA DE UI Y PERSISTENCIA
        self.modelo.notificar_cambio_estado()
        self.modelo.guardar_estado()

        # Hito histórico
        self.modelo.historia.agregar_hito(
            {
                "turno": self.modelo.paso_actual,
                "descripcion": f"El Agente {self.unique_id} ha fundado el grupo '{nombre_final}'.",
                "tipo": "fundacion",
            }
        )

        self.modelo.grupos_creados_este_paso += 1
        return nuevo_grupo_id

    @synchronized
    def invitar_agente(self, otro_agente):
        """Envía una invitación formal para unirse a su facción."""
        if self.grupo_id is None:
            return False

        # Solo invitamos si no tiene grupo o si queremos que cambie
        if otro_agente.grupo_id == self.grupo_id:
            return False

        mision = self.modelo.objetivos_grupos.get(
            self.grupo_id, "Prosperidad Colectiva"
        )
        otro_agente.ultimo_mensaje_recibido = {
            "emisor": self.unique_id,
            "contenido": f"INVITACION_GRUPO:{self.grupo_id}:{mision}",
        }
        self.modelo.log(
            f"✉️ [INVITACION] Agente {self.unique_id} invita a {otro_agente.unique_id} a unirse a la Facción {self.grupo_id}.",
            categoria="social",
        )
        return True

    def formar_alianza(self, otro_agente, terminos=None):
        """Crea un pacto de alianza mutua con términos específicos."""
        # Limpieza robusta de datos corruptos (strings en lugar de dicts)
        self.tratados = [t for t in self.tratados if isinstance(t, dict)]

        # Si no hay términos, es una alianza básica de apoyo mutuo
        if terminos is None:
            terminos = {
                "tipo": "apoyo_mutuo",
                "descripcion": "Apoyo social y suministros básicos",
            }

        # Evitar duplicados de tratados activos con el mismo agente
        if any(t["socio_id"] == otro_agente.unique_id for t in self.tratados):
            return False

        nuevo_tratado_yo = {
            "socio_id": otro_agente.unique_id,
            "terminos": terminos,
            "pasos_restantes": 10,  # Duración estándar de 10 turnos
        }
        nuevo_tratado_otro = {
            "socio_id": self.unique_id,
            "terminos": terminos,
            "pasos_restantes": 10,
        }

        self.tratados.append(nuevo_tratado_yo)

        # Validar lista del otro agente
        if not isinstance(otro_agente.tratados, list):
            otro_agente.tratados = []
        # Limpiar corruptos del otro agente también
        otro_agente.tratados = [t for t in otro_agente.tratados if isinstance(t, dict)]

        otro_agente.tratados.append(nuevo_tratado_otro)

        # Mantener lista de alianzas para compatibilidad visual (y reparar si hay datos corruptos)
        if not isinstance(self.alianzas, list):
            self.alianzas = []
        if not isinstance(otro_agente.alianzas, list):
            otro_agente.alianzas = []

        if otro_agente.unique_id not in self.alianzas:
            self.alianzas.append(otro_agente.unique_id)
        if self.unique_id not in otro_agente.alianzas:
            otro_agente.alianzas.append(self.unique_id)

        desc = terminos.get("descripcion", "Pacto formal")
        self.modelo.log(
            f"📜 [TRATADO] {self.unique_id} y {otro_agente.unique_id} han firmado: {desc}",
            categoria="social",
        )

        # Registrar en memoria gráfica para visualización
        self.memoria.registrar_interaccion(
            otro_agente.unique_id,
            "alianza",
            0.5,
            otro_agente.recursos,
            otro_agente.grupo_id,
        )
        otro_agente.memoria.registrar_interaccion(
            self.unique_id, "alianza", 0.5, self.recursos, self.grupo_id
        )

        self.modelo.notificar_cambio_estado()  # Actualizar alianzas en tiempo real
        return True

    # === MÉTODOS SOCIALES OASIS ===
    def social_follow(self, otro_agente) -> bool:
        """El agente sigue a otro agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        exito = recsys.follow(self.unique_id, otro_agente.unique_id)
        if exito:
            self.siguiendo += 1
            otro_agente.seguidores += 1
            self.modelo.log(
                f"📡 [{self.unique_id}] Ahora sigue a [{otro_agente.unique_id}]",
                categoria="social",
            )
        return exito

    def social_unfollow(self, otro_agente) -> bool:
        """El agente deja de seguir a otro."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        exito = recsys.unfollow(self.unique_id, otro_agente.unique_id)
        if exito:
            self.siguiendo = max(0, self.siguiendo - 1)
            otro_agente.seguidores = max(0, otro_agente.seguidores - 1)
        return exito

    def social_like(self, target_id: str) -> bool:
        """El agente da like a un post."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        exito = recsys.likear_post(target_id, self.unique_id)
        if exito:
            # Incrementar likes recibidos del autor del post
            post = recsys.interest_recsys.posts.get(target_id)
            if post:
                autor_post = next(
                    (a for a in self.modelo.agentes if a.unique_id == post.autor_id),
                    None,
                )
                if autor_post:
                    autor_post.likes_recibidos += 1
            # Recompensa biológica: un like satisface un poco la necesidad social
            self.necesidades["social"] = min(10.0, self.necesidades["social"] + 0.5)
            self.capital_social = self.calcular_capital_social()
            if hasattr(self.modelo, "notificar_cambio_estado"):
                self.modelo.notificar_cambio_estado()
        return exito

    def social_create_post(
        self, contenido: str, tipo: str = "opinion", temas: List[str] = None
    ) -> bool:
        """El agente crea un post en la red social."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        paso = getattr(self.modelo, "paso_actual", 0)
        post = recsys.crear_post(self.modelo.user_id, self.unique_id, contenido, tipo, temas, timestamp=paso)

        self.posts_publicados += 1
        # Publicar satisface la necesidad de expresión (baja el hambre de expresión)
        if "expresion" in self.necesidades_intelectuales:
            self.necesidades_intelectuales["expresion"] = max(
                0.0, self.necesidades_intelectuales["expresion"] - 2.0
            )

        self.capital_social = self.calcular_capital_social()

        # Notificar cambio de estado para actualizar UI
        if hasattr(self.modelo, "notificar_cambio_estado"):
            self.modelo.notificar_cambio_estado()

        return True

    def social_comment(self, post_id: str, contenido: str) -> bool:
        """El agente comenta en un post."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        recsys.agregar_comentario(post_id, self.unique_id, contenido)
        self.comentarios_realizados += 1

        # Recompensa biológica: comentar es interacción social fuerte
        self.necesidades["social"] = min(10.0, self.necesidades["social"] + 1.5)
        self.capital_social = self.calcular_capital_social()

        # Notificar cambio de estado para actualizar UI
        if hasattr(self.modelo, "notificar_cambio_estado"):
            self.modelo.notificar_cambio_estado()

        return True

    def get_social_feed(self, limite: int = 10) -> Dict:
        """Obtiene el feed personalizado del agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return {
                "in_network": [],
                "recommended": [],
                "trending": [],
                "all_posts": [],
            }

        return recsys.get_feed_hibrido(self, self.modelo.paso_actual, limite)

    def get_following(self) -> List[str]:
        """Retorna la lista de IDs que sigue este agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return []
        return recsys.get_siguiendo(self.unique_id)

    def get_followers(self) -> List[str]:
        """Retorna la lista de seguidores de este agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return []
        return recsys.get_seguidores(self.unique_id)

    def get_social_notifications(self) -> List[Dict]:
        """Obtiene todas las interacciones (likes/comentarios) en los posts de este agente."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return []
        return recsys.get_interacciones_usuario(self.unique_id)

    def _ejecutar_accion_social_automatica(self, paso: int):
        """
        Ejecuta una acción automática en la red social cada turno.
        El agente comparte algo de su experiencia/mundo con la comunidad.
        Esta acción es explícita y refleja lo que el agente está haciendo.
        """
        import random

        # Cooldown por agente para evitar un post en cada turno.
        ultimo_paso = getattr(self, "ultimo_paso_social", -10_000)
        intervalo_min = getattr(self.modelo, "social_post_min_interval", 4)
        if paso - ultimo_paso < intervalo_min:
            return

        # Incluso fuera de cooldown, no siempre publicar para mantener fluidez.
        if random.random() > 0.55:
            return

        self.ultimo_paso_social = paso

        # Determinar tipo de contenido basado en el estado del agente
        tipo_contenido = self._determinar_tipo_post()

        # Mezclar posts rápidos locales con posts LLM para reducir latencia global.
        if random.random() < getattr(self.modelo, "social_llm_ratio", 0.35):
            contenido = self._generar_contenido_post(tipo_contenido, paso)
        else:
            contenido = self._generar_contenido_post_rapido(tipo_contenido, paso)

        if contenido and len(contenido) > 10:
            # Detectar temas del contenido
            temas = self._detectar_temas_post(contenido)

            # Crear el post
            self.social_create_post(contenido, tipo=tipo_contenido, temas=temas)

            # Notificar en logs
            nombre_agente = self.identidad.nombre if self.identidad else self.unique_id
            contenido_mostrar = contenido if len(contenido) <= 100 else contenido[:100] + "..."
            self.modelo.log(
                f"📱 [{nombre_agente}] Publicó en la red: {contenido_mostrar}",
                categoria="social",
            )

            if getattr(self.modelo, "realtime_event_callback", None):
                try:
                    self.modelo.realtime_event_callback(
                        "social_event",
                        {
                            "agent_id": self.unique_id,
                            "agent_name": nombre_agente,
                            "step": paso,
                            "event": "post_created",
                            "content": contenido,
                            "post_type": tipo_contenido,
                        },
                    )
                except Exception:
                    pass

            # Probabilidad de hacer otras acciones sociales
            if random.random() < 0.4:
                self._ejecutar_like_aleatorio()
            if random.random() < 0.2:
                self._ejecutar_follow_aleatorio()
            if random.random() < 0.3:
                self._ejecutar_comentario_aleatorio()

    def social_force_action(self, paso: int) -> bool:
        """Ejecuta forzosamente una acción en la red social por turno.

        Garantiza que cada turno el agente realice una acción social (post, like, comment o follow).
        Esta función evita las comprobaciones de cooldown/aleatoriedad de _ejecutar_accion_social_automatica
        y se usa cuando la gamificación requiere 1 acción social obligatoria por turno.
        """
        import random
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        # Intentar obtener el feed para interactuar con posts existentes
        try:
            feed = recsys.get_feed_hibrido(self, paso, limite=10)
            posts = feed.get("all_posts", []) if feed else []
        except Exception:
            posts = []

        # Priorizar crear post si la necesidad de expresión es alta o no hay posts
        if self.necesidades_intelectuales.get("expresion", 0) > 6 or not posts:
            tipo_post = self._determinar_tipo_post() if hasattr(self, "_determinar_tipo_post") else "opinion"
            if hasattr(self, "_generar_contenido_post"):
                contenido = self._generar_contenido_post(tipo_post, paso)
            else:
                contenido = f"{self.identidad.nombre if self.identidad else self.unique_id}: paso {paso}"
            return self.social_create_post(contenido, tipo=tipo_post, temas=[])

        # Si hay posts, elegir entre like, comentar o seguir al autor
        post = random.choice(posts)
        r = random.random()
        if r < 0.5:
            return self.social_like(post.id)
        elif r < 0.8:
            return self.social_comment(post.id, f"Interesante: {post.contenido[:60]}")
        else:
            # Intentar seguir al autor si existe en el modelo
            author = next((a for a in self.modelo.agentes if a.unique_id == post.autor_id), None)
            if author:
                return self.social_follow(author)
        return False

    def _generar_contenido_post_rapido(self, tipo: str, paso: int) -> str:
        """Genera un post breve sin LLM para acelerar turnos."""
        nombre = self.identidad.nombre if self.identidad else self.unique_id
        hambre = self.necesidades.get("alimento", 5)
        social = self.necesidades.get("social", 5)

        if tipo == "hungry":
            return (
                f"{nombre}: estoy con hambre ({hambre:.1f}/10). "
                "Si alguien se suma, armemos una ruta para conseguir comida."
            )
        if tipo == "social":
            return (
                f"{nombre}: hoy necesito más conexión ({social:.1f}/10). "
                "¿Quién quiere conversar o coordinar una acción conjunta?"
            )
        if tipo == "opinion":
            return (
                f"{nombre}: producir recursos ayuda, pero sin acuerdos estables "
                "la tensión vuelve. Deberíamos coordinar reglas claras."
            )
        if tipo == "question":
            return (
                f"{nombre}: paso {paso}. Pregunta abierta: "
                "¿qué estrategia les está funcionando mejor para sostenerse?"
            )
        if tipo == "event":
            return (
                f"{nombre}: hubo cambios recientes en el entorno. "
                "Compartan señales para reaccionar más rápido."
            )
        return (
            f"{nombre}: sigo observando el mundo en el paso {paso}. "
            "Si detectan una oportunidad, me sumo."
        )

    def _determinar_tipo_post(self) -> str:
        """Determina el tipo de post según el estado del agente."""
        import random

        # Basado en necesidades y eventos recientes
        if self.necesidades.get("alimento", 5) < 4:
            return "hungry"  # Tiene hambre
        elif self.necesidades.get("social", 5) < 4:
            return "social"  # Necesita socializar
        elif self.necesidades_intelectuales.get("expresion", 5) > 7:
            return "opinion"  # Quiere expresar opinión
        elif self.necesidades_intelectuales.get("curiosidad", 5) > 7:
            return "question"  # Tiene curiosidad
        else:
            return random.choice(["observation", "reflection", "event"])

    def _generar_contenido_post(self, tipo: str, paso: int) -> str:
        """Genera contenido apropiado para el tipo de post usando el LLM."""
        from agents.cerebro_llm import cerebro_llm

        # Contexto enriquecido con información del mundo
        contexto_adicional = f"=== CONTEXTO DEL MUNDO (Paso {paso}) ===\n"

        # Tipo de post sugerido
        contexto_adicional += f"Tipo de post sugerido: {tipo}\n"

        # Estado personal del agente
        contexto_adicional += f"Tus valores: {', '.join(self.alma.valores) if hasattr(self, 'alma') and self.alma and self.alma.valores else 'ninguno'}\n"
        contexto_adicional += f"Tus necesidades urgentes: alimento={self.necesidades.get('alimento', 5):.1f}, social={self.necesidades.get('social', 5):.1f}, descanso={self.necesidades.get('descanso', 5):.1f}\n"
        contexto_adicional += f"Tu dinero: {self.dinero} MC\n"

        # Información contextual basada en tipo
        if tipo == "hungry":
            contexto_adicional += "Tienes hambre urgente. Publica sobre tu necesidad de alimento o critica la distribución de recursos."
        elif tipo == "social":
            contexto_adicional += "Te sientes solo. Busca conexión con otros o comenta sobre la importancia de la comunidad."
        elif tipo == "opinion":
            contexto_adicional += "Tienes opiniones fuertes. Expresa tu posición sobre la política, economía o ética del mundo."
        elif tipo == "question":
            contexto_adicional += "Tienes curiosidad. Formula preguntas sobre misterios, desafíos o posibilidades del mundo."
        elif tipo == "observation":
            contexto_adicional += (
                "Observaste algo interesante. Comparte tu descubrimiento o inquietud."
            )
        elif tipo == "reflection":
            contexto_adicional += (
                "Reflexiona sobre tu propósito, tu viaje, o lecciones aprendidas."
            )
        elif tipo == "event":
            contexto_adicional += (
                "Algo importante sucedió. Comenta sobre su significado o impacto."
            )

        contexto_adicional += "\n"

        # Otros agentes cercanos
        otros_vivos = [
            a
            for a in self.modelo.agentes
            if a.unique_id != self.unique_id and a.esta_vivo
        ]
        if otros_vivos:
            contexto_adicional += f"Otros habitantes en el mundo: {len(otros_vivos)}\n"
            # Mostrar los más cercanos o relevantes
            for otra in otros_vivos[:3]:
                contexto_adicional += f"  - {otra.identidad.nombre or otra.unique_id}: en pos ({otra.x}, {otra.y}), dinero={otra.dinero} MC\n"

        # Posts recientes en la red social para debate
        recsys = getattr(self.modelo, "social_recsys", None)
        if recsys and recsys.interest_recsys.posts:
            posts_recientes = list(recsys.interest_recsys.posts.values())[-5:]
            if posts_recientes:
                contexto_adicional += f"\nÚltimos posts en la red social:\n"
                post_objetivo = None
                for post in posts_recientes:
                    if post.autor_id != self.unique_id:
                        # Buscar nombre del autor
                        autor_nombre = post.autor_id
                        for a in self.modelo.agentes:
                            if a.unique_id == post.autor_id:
                                autor_nombre = a.identidad.nombre or a.unique_id
                                break
                        if post_objetivo is None:
                            post_objetivo = (autor_nombre, post.contenido)
                        contexto_adicional += (
                            f"  - {autor_nombre}: {post.contenido}\n"
                        )
                if post_objetivo:
                    contexto_adicional += (
                        "\nDebate recomendado: responde explícitamente al post de "
                        f"{post_objetivo[0]} y toma postura sobre su idea central.\n"
                        "Incluye acuerdo parcial, desacuerdo o propuesta concreta.\n"
                    )

        # Situación económica y política
        contexto_adicional += f"\nSituación del mundo:\n"
        contexto_adicional += f"  - Índice bursátil: {self.modelo.economia.get('indice_bursatil', 100):.1f}\n"
        contexto_adicional += f"  - Precio de recursos: {self.modelo.economia.get('precio_recurso', 2):.2f} MC\n"
        contexto_adicional += f"  - Clima: {self.modelo.weather}\n"
        contexto_adicional += f"  - Tu reputación: {self.reputacion:.1f}\n"

        if self.grupo_id:
            contexto_adicional += f"  - Tu grupo/civilización: {self.grupo_id}\n"

        contexto_adicional += (
            "\nEsperamos un post SUSTANCIAL (200-600 caracteres) donde reflejes tu pensamiento complejo sobre la situación. "
            "Debe incluir una opinión argumentada y una reacción a reflexiones/debates recientes de otros agentes."
        )

        # Generar post usando el LLM
        return cerebro_llm.generar_post_social(self, contexto_adicional)

    def _detectar_temas_post(self, contenido: str) -> List[str]:
        """Detecta temas de un post."""
        contenido_lower = contenido.lower()
        temas = []

        if any(
            p in contenido_lower for p in ["comida", "hambre", "alimento", "recurso"]
        ):
            temas.append("supervivencia")
        if any(
            p in contenido_lower for p in ["solo", "conectar", "interactuar", "social"]
        ):
            temas.append("social")
        if any(
            p in contenido_lower
            for p in ["reflexiono", "pensamiento", "opinion", "posición"]
        ):
            temas.append("opinión")
        if any(p in contenido_lower for p in ["pregunta", "descubrir", "cómo"]):
            temas.append("curiosidad")
        if any(p in contenido_lower for p in ["observo", "entorno", "mundo"]):
            temas.append("observación")
        if any(p in contenido_lower for p in ["encuentro", "cambiar", "suceso"]):
            temas.append("evento")

        if not temas:
            temas.append("general")

        return temas

    def _ejecutar_like_aleatorio(self):
        """Da like a un post aleatorio."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return

        posts = recsys.interest_recsys.posts
        if not posts:
            return

        # Elegir un post aleatorio que no sea propio
        post_ids = [pid for pid, p in posts.items() if p.autor_id != self.unique_id]
        if not post_ids:
            return

        import random

        post_id = random.choice(post_ids)
        self.social_like(post_id)
        self.likes_dados += 1

    def _ejecutar_follow_aleatorio(self):
        """Sigue a un agente aleatorio."""
        otros = [
            a
            for a in self.modelo.agentes
            if a.unique_id != self.unique_id and a.esta_vivo
        ]
        if not otros:
            return

        import random

        otro = random.choice(otros)

        # Verificar si ya lo sigue
        siguiendo = self.get_following()
        if otro.unique_id not in siguiendo:
            self.social_follow(otro)

    def _ejecutar_comentario_aleatorio(self):
        """Comenta en un post aleatorio del feed."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return

        posts = recsys.interest_recsys.posts
        if not posts:
            return

        # Elegir un post aleatorio que no sea propio
        post_ids = [pid for pid, p in posts.items() if p.autor_id != self.unique_id]
        if not post_ids:
            return

        import random

        post_id = random.choice(post_ids)
        target_post = posts[post_id]

        # Generar comentario breve basado en el contenido del post original
        from agents.cerebro_llm import cerebro_llm

        # Buscar nombre del autor del post
        autor_post_nombre = target_post.autor_id
        for a in self.modelo.agentes:
            if a.unique_id == target_post.autor_id:
                autor_post_nombre = a.identidad.nombre or a.unique_id
                break

        ctx = f'Estás viendo un post de {autor_post_nombre} que dice: "{target_post.contenido}". Escribe una respuesta corta y espontánea.'

        respuesta = cerebro_llm.generar_post_social(self, ctx)
        if respuesta and len(respuesta) > 5:
            self.social_comment(post_id, respuesta)
            nombre_yo = self.identidad.nombre if self.identidad else self.unique_id
            self.modelo.log(
                f"💬 [{nombre_yo}] Respondió a {autor_post_nombre}: {respuesta[:60] if len(respuesta) > 60 else respuesta}",
                categoria="social",
            )

    # === FIN MÉTODOS SOCIALES ===

    @synchronized
    def comerciar(self, otro_agente, tipo="compra"):
        """Realiza una transacción económica entre agentes."""
        # Precio base influenciado por el mercado global
        precio_mercado = float(self.modelo.precio_recurso_actual)

        if tipo == "compra":
            # Yo compro recursos a otro_agente
            cantidad = 3  # Reducido de 5 a 3
            costo = cantidad * precio_mercado
            if (
                self.dinero >= costo
                and otro_agente.recursos >= cantidad
                and (self.gasto_turno + costo) <= 30
            ):
                self.dinero -= costo
                self.gasto_turno += costo
                self.recursos += cantidad
                otro_agente.dinero += costo
                otro_agente.recursos -= cantidad
                self.modelo.log(
                    f"💰 [COMERCIO] Agente {self.unique_id} compró {cantidad} recursos a {otro_agente.unique_id} por {costo:.1f} MC.",
                    categoria="social",
                )
                self.modelo.notificar_cambio_estado()
                return True
        return False

    @synchronized
    def mejorar_seguridad(self):
        """Invierte dinero en mejorar el rango y la protección."""
        costo = 25.0  # Reducido de 50 a 25 para que sea viable con el límite de 30
        if self.dinero >= costo and (self.gasto_turno + costo) <= 30:
            self.dinero -= costo
            self.gasto_turno += costo
            self.rango += 0.2
            self.necesidades["seguridad"] = max(0, self.necesidades["seguridad"] - 5)
            self.modelo.log(
                f"🛡️ [SEGURIDAD] Agente {self.unique_id} invirtió en protección. Rango aumentado a {self.rango:.1f}.",
                categoria="state",
            )
            self.modelo.notificar_cambio_estado()
            return True
        return False

    @synchronized
    def invertir(self, monto):
        """El agente coloca dinero en el mercado para obtener retornos futuros."""
        if self.dinero >= monto and (self.gasto_turno + monto) <= 30:
            self.dinero -= monto
            self.gasto_turno += monto
            # Inversión a 5 pasos con un interés aleatorio entre -5% y +15%
            interes = random.uniform(-0.05, 0.15)
            self.inversiones.append(
                {
                    "monto": monto,
                    "paso_final": self.modelo.paso_actual + 5,
                    "interes": interes,
                }
            )
            self.modelo.log(
                f"📈 [INVERSIÓN] Agente {self.unique_id} invirtió {monto:.1f} MC en el mercado.",
                categoria="state",
            )
            self.modelo.notificar_cambio_estado()
            return True
        return False

    def actualizar_estado(self):
        """Actualiza las necesidades y recursos internos en cada paso."""
        # Producción pasiva aumentada para mayor resiliencia
        self.recursos += 0.5

        # Procesar inversiones terminadas
        for inv in list(self.inversiones):
            if self.modelo.paso_actual >= inv["paso_final"]:
                ganancia = inv["monto"] * (1 + inv["interes"])
                self.dinero += ganancia
                self.inversiones.remove(inv)
                resultado = "ganancia" if inv["interes"] > 0 else "pérdida"
                self.modelo.log(
                    f"💰 [RETORNO] Inversión de {self.unique_id} finalizada: {ganancia:.1f} MC ({resultado}).",
                    categoria="social",
                )

        # El metabolismo consume menos recursos si hay alimento almacenado
        consumo = 0.5 + ((10 - self.necesidades["alimento"]) * 0.03)
        self.recursos -= consumo
        self.inventario["comida"] = max(0, int(self.recursos))

        # Necesidades disminuyen (10=perfecto, 0=emergencia)
        # EL costo del terreno afecta el consumo de descanso y alimento
        tile = self.modelo.mapa[self.x][self.y]
        energy_mod = tile.energy_cost

        self.necesidades["alimento"] = max(
            0, self.necesidades["alimento"] - (0.04 + energy_mod * 0.1)
        )
        self.necesidades["social"] = max(0, self.necesidades["social"] - 0.03)
        self.necesidades["seguridad"] = max(0, self.necesidades["seguridad"] - 0.02)
        self.necesidades["descanso"] = max(
            0, self.necesidades["descanso"] - (0.05 + energy_mod)
        )
        self.necesidades["entretenimiento"] = max(
            0, self.necesidades["entretenimiento"] - 0.03
        )

        # Riesgo de salud por terreno hostil (Desert, Mountain)
        if tile.health_risk > 0 and random.random() < 0.1:
            self.recibir_daño(
                tile.health_risk * 2, f"clima hostil en {tile.terrain_type}"
            )

        # --- REGENERACIÓN PASIVA ---
        # Si el agente está bien alimentado y descansado (> 7), recupera salud
        if self.necesidades["alimento"] > 7.0 and self.necesidades["descanso"] > 7.0:
            self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 0.1)
            # Log sutil de bienestar solo de vez en cuando para no saturar
            if random.random() < 0.1:
                self.modelo.log(
                    f"✨ [BIENESTAR] Agente {self.unique_id} se está recuperando gracias a su buen estado.",
                    categoria="state",
                )

        # --- PROCESAMIENTO DE TRATADOS FORMALES ---
        for tratado in list(self.tratados):
            if not isinstance(tratado, dict):
                # Si por error hay un string (ej. bug de carga), lo ignoramos
                continue

            aliado = next(
                (
                    a
                    for a in self.modelo.agentes
                    if a.unique_id == tratado.get("socio_id")
                ),
                None,
            )
            if not aliado:
                continue

            t = tratado["terminos"]
            # 1. Intercambio de Recursos por Dinero
            if t.get("tipo") == "intercambio":
                dar = t.get("da", {})  # {recurso: "medicina", cant: 1}
                recibe = t.get("recibe", {})  # {recurso: "dinero", cant: 10}

                # Ejecutar si ambos tienen lo necesario
                puedo_dar = False
                if dar.get("recurso") == "medicina" and self.inventario[
                    "medicina"
                ] >= dar.get("cant", 0):
                    puedo_dar = True
                elif dar.get("recurso") == "dinero" and self.dinero >= dar.get(
                    "cant", 0
                ):
                    puedo_dar = True
                elif dar.get("recurso") == "recursos" and self.recursos >= dar.get(
                    "cant", 0
                ):
                    puedo_dar = True

                if puedo_dar:
                    # Transferir lo que yo doy
                    if dar["recurso"] == "medicina":
                        self.inventario["medicina"] -= dar["cant"]
                        aliado.inventario["medicina"] += dar["cant"]
                    elif dar["recurso"] == "dinero":
                        self.dinero -= dar["cant"]
                        aliado.dinero += dar["cant"]
                    elif dar["recurso"] == "recursos":
                        self.recursos -= dar["cant"]
                        aliado.recursos += dar["cant"]

                    # Transferir lo que yo recibo (si el aliado puede)
                    # Nota: Simplificado para que el aliado siempre cumpla su parte si el otro empezó
                    if recibe["recurso"] == "dinero":
                        aliado.dinero -= recibe["cant"]
                        self.dinero += recibe["cant"]
                    elif recibe["recurso"] == "seguridad":
                        self.rango += recibe["cant"]  # El aliado me brinda protección

                    self.modelo.log(
                        f"🤝 [EJECUCION TRATADO] Intercambio realizado entre {self.unique_id} y {aliado.unique_id}.",
                        categoria="social",
                    )

            # Reducir duración
            tratado["pasos_restantes"] -= 1
            if tratado["pasos_restantes"] <= 0:
                self.tratados.remove(tratado)
                # También quitar del aliado
                aliado.tratados = [
                    at for at in aliado.tratados if at["socio_id"] != self.unique_id
                ]
            self.modelo.log(
                f"⌛ [SISTEMA] El tratado entre {self.unique_id} y {aliado.unique_id} ha expirado.",
                categoria="sistema",
            )

        # --- DEGRADACIÓN DE SALUD POR NECESIDADES ---
        if self.necesidades["alimento"] < 2.0:
            daño_hambre = (2.0 - self.necesidades["alimento"]) * 0.5
            self.recibir_daño(daño_hambre, "hambre extrema")

        if self.necesidades["seguridad"] < 2.0:
            # En zonas inseguras hay riesgo de daño pasivo
            if random.random() < 0.1:
                self.recibir_daño(0.5, "inseguridad del entorno")

        if self.necesidades["salud"] <= 0:
            self.morir("agotamiento total de constantes vitales")
            return

        # --- VALIDACIÓN DE COORDENADAS ---
        # Asegurar que las coordenadas del agente estén dentro de los límites del mapa
        map_width = len(self.modelo.mapa)
        map_height = len(self.modelo.mapa[0]) if map_width > 0 else 0

        if self.x < 0 or self.x >= map_width or self.y < 0 or self.y >= map_height:
            # Ajustar coordenadas a los límites válidos
            self.x = max(0, min(self.x, map_width - 1))
            self.y = max(0, min(self.y, map_height - 1))
            self.modelo.log(
                f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas a ({self.x}, {self.y}) para estar dentro del mapa.",
                categoria="sistema",
            )

        # --- INSTINTO DE SUPERVIVENCIA AUTOMÁTICO ---
        tile = self.modelo.mapa[self.x][self.y]

        # 1. Alimentación automática si hay comida en el suelo y tiene hambre
        if (
            tile.resource_node
            and tile.resource_node["type"] == "food"
            and self.necesidades["alimento"] < 6.0
        ):
            comida_tomada = min(tile.resource_node["amount"], 2.0)
            tile.resource_node["amount"] -= comida_tomada
            self.necesidades["alimento"] = min(
                10, self.necesidades["alimento"] + (comida_tomada * 2)
            )
            self.modelo.log(
                f"🍎 [INSTINTO] Agente {self.unique_id} consumió alimento del terreno automáticamente.",
                categoria="alimentos",
            )
            if tile.resource_node["amount"] <= 0:
                tile.resource_node = None

        # 2. Uso de infraestructura (Hospitales y Centros de Recarga)
        for edif in tile.buildings:
            if (
                edif["tipo"].lower() in ["hospital", "clinica"]
                and self.necesidades["salud"] < 9.0
            ):
                self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 1.0)
                self.modelo.log(
                    f"🏥 [SISTEMA] Agente {self.unique_id} está siendo atendido en el Hospital.",
                    categoria="salud",
                )

            if "recarga" in edif["tipo"].lower() or "eléctrica" in edif["tipo"].lower():
                self.necesidades["descanso"] = min(
                    10.0, self.necesidades["descanso"] + 2.0
                )
                self.recursos += 1.0  # Carga de energía/recursos
                self.modelo.log(
                    f"⚡ [SISTEMA] Agente {self.unique_id} recargando constantes en estación energética.",
                    categoria="ambiente",
                )

    @synchronized
    def recibir_daño(self, cantidad, motivo="desconocido"):
        """Reduce la salud del agente y verifica si muere."""
        self.necesidades["salud"] -= cantidad
        self.modelo.log(
            f"🩸 [DAÑO] Agente {self.unique_id} ha recibido {cantidad:.1f} de daño por {motivo}. Salud restante: {self.necesidades['salud']:.1f}",
            categoria="salud",
        )
        if self.necesidades["salud"] <= 0:
            self.morir(motivo)

    def morir(self, motivo):
        """Finaliza la existencia del agente en la simulación."""
        if not self.esta_vivo:
            return

        self.esta_vivo = False
        self.modelo.log(
            f"🪦 [FUNERAL] El Agente {self.unique_id} ha MUERTO. Motivo: {motivo}.",
            categoria="sistema",
        )

        # Registro histórico si era importante
        if self.rol in ["Líder", "Historiador", "Moderador"]:
            self.modelo.historia.agregar_hito(
                {
                    "turno": self.modelo.paso_actual,
                    "descripcion": f"Luto nacional: El {self.rol} {self.unique_id} ha fallecido por {motivo}.",
                    "tipo": "muerte",
                }
            )

        # Eliminar de la lista activa del modelo
        if self in self.modelo.agentes:
            self.modelo.agentes.remove(self)

        # Limpiar tratados y alianzas
        for aliado_id in list(self.alianzas):
            aliado = self.modelo.get_agent_by_id(aliado_id)
            if aliado and self.unique_id in aliado.alianzas:
                aliado.alianzas.remove(self.unique_id)

        # Registrar en DB si es posible
        if self.modelo.db_active:
            try:
                self.modelo.db.execute(
                    "UPDATE agentes SET reputacion = %s WHERE id = %s",
                    (0.0, self.unique_id),
                )
            except:
                pass

        # Notificar muerte inmediata para actualizar listas
        self.modelo.notificar_cambio_estado()

    @synchronized
    def recolectar(self):
        """El agente busca recursos en el entorno. Prioriza los nodos de recursos del mapa."""
        # Validar coordenadas antes de acceder al mapa
        map_width = len(self.modelo.mapa)
        map_height = len(self.modelo.mapa[0]) if map_width > 0 else 0

        if self.x < 0 or self.x >= map_width or self.y < 0 or self.y >= map_height:
            self.x = max(0, min(self.x, map_width - 1))
            self.y = max(0, min(self.y, map_height - 1))
            self.modelo.log(
                f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas en recolectar a ({self.x}, {self.y}).",
                categoria="sistema",
            )

        tile = self.modelo.mapa[self.x][self.y]
        mult = getattr(tile, "yield_mult", 1.0)

        # 1. Recolección de nodo específico
        if tile.resource_node and tile.resource_node["amount"] > 0:
            tipo = tile.resource_node["type"]

            # Bonos específicos por terreno
            nodo_bonus = 1.0
            if tipo == "wood" and tile.terrain_type == TerrainType.FOREST:
                nodo_bonus = 2.0
            if tipo == "stone" and tile.terrain_type == TerrainType.MOUNTAIN:
                nodo_bonus = 2.0
            if tipo == "food" and tile.terrain_type == TerrainType.GRASS:
                nodo_bonus = 1.5

            cantidad = min(
                tile.resource_node["amount"],
                int(random.randint(5, 15) * mult * nodo_bonus),
            )
            tile.resource_node["amount"] -= cantidad

            if tipo == "food":
                self.recursos += cantidad
                self.inventario["comida"] = self.inventario.get("comida", 0) + cantidad
                self.modelo.log(
                    f"  🍎 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de ALIMENTO en {tile.terrain_type}.",
                    categoria="alimentos",
                )
            elif tipo == "wood":
                self.recursos += cantidad * 0.5
                self.inventario["madera"] = self.inventario.get("madera", 0) + cantidad
                self.ganar_experiencia("ingenieria", 1)
                self.modelo.log(
                    f"  🪵 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de MADERA en {tile.terrain_type}.",
                    categoria="recursos",
                )
            elif tipo == "stone":
                self.recursos += cantidad * 0.5
                self.inventario["piedra"] = self.inventario.get("piedra", 0) + cantidad
                self.ganar_experiencia("ingenieria", 1)
                self.modelo.log(
                    f"  🪨 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de PIEDRA en {tile.terrain_type}.",
                    categoria="recursos",
                )

            if tile.resource_node["amount"] <= 0:
                tile.resource_node = None
                self.modelo.log(
                    f"  ⚠️ [RECOLECCION] El nodo de recursos en ({self.x}, {self.y}) se ha AGOTADO.",
                    categoria="ambiente",
                )
            return

        # 2. Recolección genérica (baja eficiencia según terreno)
        r = random.random()

        if tile.terrain_type == TerrainType.FOREST:
            if r < 0.6:
                cant = random.uniform(3, 10) * mult
                self.inventario["madera"] = self.inventario.get("madera", 0) + int(cant)
                self.recursos += cant * 0.5
                self.modelo.log(
                    f"  🌲 Agente {self.unique_id} recolectó {int(cant)} de MADERA en el bosque.",
                    categoria="recursos",
                )
            else:
                self.inventario["medicina"] += 1
                self.ganar_experiencia("medicina", 1)
                self.modelo.log(
                    f"  🌿 Agente {self.unique_id} encontró HIERBAS MEDICINALES.",
                    categoria="recursos",
                )

        elif tile.terrain_type == TerrainType.MOUNTAIN:
            if r < 0.7:
                cant = random.uniform(2, 6) * mult
                self.inventario["piedra"] = self.inventario.get("piedra", 0) + int(cant)
                self.recursos += cant * 0.3
                self.modelo.log(
                    f"  🪨 Agente {self.unique_id} picó {int(cant)} de PIEDRA en la montaña.",
                    categoria="recursos",
                )
            else:
                self.inventario["hierro"] = self.inventario.get("hierro", 0) + 1
                self.modelo.log(
                    f"  ⛏️ Agente {self.unique_id} encontró una veta de HIERRO.",
                    categoria="recursos",
                )

        elif tile.terrain_type == TerrainType.WATER:
            cant = random.uniform(1, 4) * mult
            self.inventario["pescado"] = self.inventario.get("pescado", 0) + int(cant)
            self.recursos += cant * 1.5  # El pescado da mucha energía/recurso
            self.modelo.log(
                f"  🐟 Agente {self.unique_id} pescó {int(cant)} unidades.",
                categoria="alimentos",
            )

        else:  # Grassland o Desert
            cant = random.uniform(2, 8) * mult
            self.recursos += cant  # Alimento base
            self.inventario["comida"] = self.inventario.get("comida", 0) + int(cant)
            self.modelo.log(
                f"  🌱 Agente {self.unique_id} forrajeó {int(cant)} de alimento.",
                categoria="alimentos",
            )

        # Notificar cambio inmediato para visualización real-time en paneles
        self.modelo.notificar_cambio_estado()

    @synchronized
    def establecer_objetivo_movimiento(self, x, y):
        """Fija un destino para el movimiento del agente."""
        self.objetivo_movimiento = (x, y)
        self.modelo.log(
            f"🗺️ [NAVEGACION] Agente {self.unique_id} ha fijado un nuevo rumbo a ({x}, {y}).",
            categoria="movimiento",
        )

    @synchronized
    def ganar_experiencia(self, area, puntos=1):
        """Aumenta la experiencia en un área y verifica si puede graduarse."""
        if area in self.experiencia:
            self.experiencia[area] += puntos
            # Si llega a 5 de experiencia en un área y no tiene esa profesión, avisar
            if self.experiencia[area] == 5 and self.profesion is None:
                self.modelo.log(
                    f"🎓 [HITOS] Agente {self.unique_id} ha ganado suficiente experiencia en {area} para profesionalizarse.",
                    categoria="sistema",
                )

    @synchronized
    def construir(self, tipo_edificio="Casa"):
        """Intenta construir un edificio en la posición actual."""
        if not self.esta_vivo:
            return False, "Agente muerto."
        res, msg = self.modelo.construir_edificio(self, tipo_edificio)
        if res:
            self.modelo.notificar_cambio_estado()
        return res, msg

    @synchronized
    def graduarse(self, profesion_deseada):
        """Intenta declarar una profesión si cumple los requisitos y está en una Universidad."""
        if self.profesion:
            return False, "Ya tienes una profesión."

        # Validar coordenadas antes de acceder al mapa
        map_width = len(self.modelo.mapa)
        map_height = len(self.modelo.mapa[0]) if map_width > 0 else 0

        if self.x < 0 or self.x >= map_width or self.y < 0 or self.y >= map_height:
            self.x = max(0, min(self.x, map_width - 1))
            self.y = max(0, min(self.y, map_height - 1))
            self.modelo.log(
                f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas en graduarse a ({self.x}, {self.y}).",
                categoria="sistema",
            )

        # VERIFICACIÓN DE UBICACIÓN: Debe haber una Universidad en el tile actual
        tile = self.modelo.mapa[self.x][self.y]
        tiene_universidad = any(b["tipo"] == "Universidad" for b in tile.buildings)

        if not tiene_universidad:
            return (
                False,
                "Debes estar en una Universidad para graduarte y obtener tu título oficial. 🏛️",
            )

        costos = {"Médico": 150, "Comerciante": 200, "Guarda": 100, "Explorador": 120}

        requisitos = {
            "Médico": self.experiencia["medicina"] >= 5
            and self.personalidad["amabilidad"] > 0.5,
            "Comerciante": self.experiencia["comercio"] >= 5,
            "Guarda": self.experiencia["combate"] >= 3
            and self.personalidad["hostilidad"] < 0.6,
            "Explorador": self.experiencia["exploracion"] >= 5,
        }

        if profesion_deseada not in costos:
            return False, "Profesión no válida."

        if not requisitos[profesion_deseada]:
            return (
                False,
                f"No cumples los requisitos de experiencia o personalidad para ser {profesion_deseada}.",
            )

        if self.dinero < costos[profesion_deseada]:
            return (
                False,
                f"Necesitas {costos[profesion_deseada]} MC para la licencia de {profesion_deseada}.",
            )

        # Éxito
        self.dinero -= costos[profesion_deseada]
        self.profesion = profesion_deseada
        self.hitos.append(f"Graduado como {profesion_deseada}")
        self.modelo.log(
            f"✨ [PROFESION] ¡El Agente {self.unique_id} se ha graduado como {profesion_deseada}! 🎓",
            categoria="consenso",
        )
        return True, f"¡Felicidades! Ahora eres {profesion_deseada}."

    # --- MÉTODOS POLÍTICOS ---
    @synchronized
    def proponer_ley(self, titulo, contenido, alcance="local"):
        """Propone una nueva ley para su facción o el mundo."""
        # Si es global, cualquiera puede proponer si tiene prestigio, si es local debe tener facción
        gid = self.grupo_id if alcance == "local" else "GLOBAL"

        if alcance == "local" and not self.grupo_id:
            return False, "Debes pertenecer a una facción para proponer leyes locales."
        if alcance == "global" and self.rango < 0.0:
            return False, "Necesitas un rango positivo para proponer leyes globales."

        ley_id = f"LEY-{random.randint(1000, 9999)}"
        # Determinar el universo de votantes en este momento
        if alcance == "local":
            universo_votantes = [
                a
                for a in self.modelo.agentes
                if a.grupo_id == self.grupo_id and a.esta_vivo
            ]
        else:
            universo_votantes = [a for a in self.modelo.agentes if a.esta_vivo]

        total_requerido = len(universo_votantes)

        propuesta = {
            "id": ley_id,
            "autor": self.unique_id,
            "titulo": titulo,
            "contenido": contenido,
            "votos_si": 1,
            "votos_no": 0,
            "votantes": [self.unique_id],
            "estado": "pendiente",
            "grupo_id": gid,
            "alcance": alcance,
            "total_requerido": total_requerido,
            "paso_creacion": self.modelo.paso_actual,
        }

        if "propuestas" not in self.modelo.facciones_leyes:
            self.modelo.facciones_leyes["propuestas"] = []

        self.modelo.facciones_leyes["propuestas"].append(propuesta)

        target_str = (
            f"en la Facción {self.grupo_id}" if alcance == "local" else "a nivel GLOBAL"
        )
        self.modelo.log(
            f"📜 [POLITICA] Agente {self.unique_id} ha PROPUESTO formalmente la ley: '{titulo}' {target_str}.",
            categoria="consenso",
        )
        self.modelo.notificar_cambio_estado()

        return True, ley_id

    @synchronized
    def votar_ley(self, ley_id, a_favor=True):
        """Vota una propuesta de ley existente."""
        propuestas = self.modelo.facciones_leyes.get("propuestas", [])
        for p in propuestas:
            if (
                p["id"] == ley_id
                or str(p.get("titulo", "")).lower() == str(ley_id).lower()
            ) and self.unique_id not in p["votantes"]:
                if a_favor:
                    p["votos_si"] += 1
                else:
                    p["votos_no"] += 1
                p["votantes"].append(self.unique_id)

                self.modelo.log(
                    f"🗳️ Agente {self.unique_id} votó {'A FAVOR' if a_favor else 'EN CONTRA'} de la ley '{p['titulo']}'.",
                    categoria="consenso",
                )
                self.modelo.notificar_cambio_estado()  # Notificar cambio para WebSocket
                return True
        return False

    def sancionar(self, motivo, gravedad=0.1):
        """Reduce la reputación del agente por acciones indebidas."""
        self.reputacion = max(0.0, self.reputacion - gravedad)
        self.historial_etico.append(f"Sanción: {motivo} (-{gravedad})")
        self.modelo.log(
            f"⚖️ [JUSTICIA] Agente {self.unique_id} sancionado por: {motivo}. Reputación: {self.reputacion:.2f}",
            categoria="sistema",
        )

    def escribir_cronica(self, titulo, contenido):
        """Escribe una entrada formal en la historia del mundo."""
        if self.rol != "Historiador":
            return False, "Solo el Historiador puede escribir crónicas."

        # Registrar en la libreta
        self.modelo.historia.escribir_entrada(
            self.modelo.paso_actual,
            titulo,
            contenido,
            self.unique_id,
            categoria="general",
        )

        # Limpiar hitos pendientes ya narrados
        self.modelo.historia.limpiar_hitos()

        self.modelo.log(
            f"📚 [CRONICA] ¡Nueva entrada en los anales de la historia!: '{titulo}'",
            categoria="consenso",
        )
        self.modelo.notificar_cambio_estado()  # Para actualizar frontend
        return True, "Crónica escrita."

    def tick_bdi(self):
        """Un tick de simulación - ejecuta el ciclo BDI completo."""
        turno = self.modelo.paso_actual

        # FASE 1: Percibir y actualizar creencias
        self._bdi_percibir_entorno(turno)

        # FASE 2: Actualizar deseos based on beliefs and state
        self._bdi_revisar_deseos(turno)

        # FASE 3: Deliberar (generar y seleccionar planes)
        self._bdi_deliberar(turno)

        # FASE 4: Ejecutar acción del plan actual
        return self._bdi_ejecutar_plan(turno)

    def _bdi_percibir_entorno(self, turno: int):
        """Percibe el entorno y actualiza creencias."""
        # 1. Recursos cercanos
        tile = self.modelo.mapa[self.x][self.y]
        if tile.resource_node:
            prop = f"recurso_{tile.resource_node['type']}_disponible"
            self.creencias.actualizar_creencia(
                prop, 0.9 if tile.resource_node["amount"] > 0 else 0.1, 1.5, turno
            )

        # 2. Otros agentes
        cercanos = [
            a
            for a in self.modelo.agentes
            if a.unique_id != self.unique_id
            and abs(a.x - self.x) <= 2
            and abs(a.y - self.y) <= 2
        ]
        for otro in cercanos:
            # Creencia sobre confiabilidad basada en afinidad en memoria
            afinidad = (
                self.memoria.obtener_afinidad(otro.unique_id)
                if hasattr(self.memoria, "obtener_afinidad")
                else 0.5
            )
            self.creencias.actualizar_creencia(
                f"agente_{otro.unique_id}_confiable",
                0.5 + (afinidad / 20.0),
                1.2,
                turno,
            )

    def _bdi_ejecutar_plan(self, turno: int):
        """Ejecuta el siguiente paso del plan BDI actual."""
        if self.intenciones.plan_actual and self.intenciones.plan_actual.es_valido():
            plan = self.intenciones.plan_actual
            accion_bdi = plan.acciones[plan.tiempo_actual]
            plan.tiempo_actual += 1

            # Convertir AccionBDI a diccionario para el router
            return accion_bdi.to_dict()
        return None

    def _bdi_revisar_deseos(self, turno: int):
        """Revisa y actualiza deseos basado en necesidades vitales del agente."""
        # Estímulos dinámicos basados en estado vital
        hambre = self.necesidades.get("alimento", 5.0)
        salud = self.necesidades.get("salud", 5.0)
        social = self.necesidades.get("social", 5.0)

        # SUPERVIVENCIA: Se activa con hambre o salud baja
        if hambre < 4.0:
            self.deseos.deseos[TipoDeseo.SUPERVIVENCIA].actualizar_intensidad(0.25)
        elif hambre < 6.0:
            self.deseos.deseos[TipoDeseo.SUPERVIVENCIA].actualizar_intensidad(0.1)
        else:
            self.deseos.deseos[TipoDeseo.SUPERVIVENCIA].actualizar_intensidad(-0.05)

        if salud < 5.0:
            self.deseos.deseos[TipoDeseo.SUPERVIVENCIA].actualizar_intensidad(0.15)

        # RECURSOS: Deseo proporcional a riqueza actual
        if self.recursos < 50:
            self.deseos.deseos[TipoDeseo.RECURSOS].actualizar_intensidad(0.2)
        elif self.recursos > 200:
            self.deseos.deseos[TipoDeseo.RECURSOS].actualizar_intensidad(-0.1)
        else:
            self.deseos.deseos[TipoDeseo.RECURSOS].actualizar_intensidad(0.05)

        # ARMONÍA: Aumenta con necesidad social baja
        if social < 4.0:
            self.deseos.deseos[TipoDeseo.ARMONIA].actualizar_intensidad(0.15)
        elif social > 7.0:
            self.deseos.deseos[TipoDeseo.ARMONIA].actualizar_intensidad(-0.05)

        # ESTATUS: Crece lentamente con reputación alta
        if self.reputacion > 0.7:
            self.deseos.deseos[TipoDeseo.ESTATUS].actualizar_intensidad(0.08)
        elif self.reputacion < 0.3:
            self.deseos.deseos[TipoDeseo.ESTATUS].actualizar_intensidad(0.12)

        # Decaimiento natural hacia punto medio (evita estancamiento)
        for d in self.deseos.deseos.values():
            d.actualizar_intensidad(0)

    def _bdi_deliberar(self, turno: int):
        """Fase de deliberación."""
        if (
            self.intenciones.plan_actual is None
            or not self.intenciones.plan_actual.es_valido()
        ):
            entorno = {
                "agentes_cercanos": [
                    a
                    for a in self.modelo.agentes
                    if a.unique_id != self.unique_id
                    and abs(a.x - self.x) <= 2
                    and abs(a.y - self.y) <= 2
                ]
            }

            decision_llm = None
            if (
                hasattr(self.modelo, "cerebro_llm")
                and self.modelo.cerebro_llm
                and getattr(self.modelo.cerebro_llm, "model", None)
            ):
                try:
                    decision_llm = self.modelo.cerebro_llm.generar_pensamiento_y_accion(
                        self, None, {"bdi_deliberar": True}
                    )

                    # Procesar herramientas si las hay
                    resultados_herramientas = decision_llm.get(
                        "resultados_herramientas", []
                    )
                    if resultados_herramientas:
                        # Guardar resultados para el próximo turno
                        if not hasattr(self, "resultados_herramientas_recientes"):
                            self.resultados_herramientas_recientes = ""
                        contexto_herramientas = "\n".join(
                            [
                                f"- {r['herramienta']}: {r['resultado'][:200]}..."
                                for r in resultados_herramientas
                                if r.get("exito", False)
                            ]
                        )
                        self.resultados_herramientas_recientes = f"Resultados recientes del sistema de skills evolutivas:\n{contexto_herramientas}"

                except Exception as e:
                    pass

    def realizar_turno(self):
        """Método principal de turno para el agente - delega al modelo para la lógica completa."""
        # Delegar toda la lógica compleja al modelo, pero desde el contexto del agente
        if hasattr(self.modelo, "_procesar_turno_agente"):
            self.modelo._procesar_turno_agente(self)
        else:
            # Fallback simple si el modelo no tiene el método avanzado
            self.tick_bdi()

    def ejecutar_accion_final(self, accion_dict: Dict[str, Any]):
        """
        Router maestro de acciones físicas.
        Mapea decisiones cognitivas a métodos de interacción con el mundo.
        """
        if not accion_dict:
            return False

        tipo = accion_dict.get("tipo", "").lower()
        params = accion_dict.get("parametros", {})

        try:
            # 1. Acciones de Recolección y Supervivencia
            if tipo in ["recolectar", "buscar_recursos"]:
                return self.recolectar()
            elif tipo == "comer":
                return self.comer()
            elif tipo == "descansar":
                self.necesidades["descanso"] = min(
                    10.0, self.necesidades["descanso"] + 2.0
                )
                return True

            # 2. Acciones de Movimiento
            elif tipo == "moverse" or "ir_a" in tipo:
                dest_x = params.get("x", self.x + random.randint(-1, 1))
                dest_y = params.get("y", self.y + random.randint(-1, 1))
                return self.moverse(dest_x, dest_y)

            # 3. Acciones Sociales y de Grupo
            elif tipo == "social_create_post":
                contenido = params.get("contenido", "Hola a todos en OASIS")
                return self._ejecutar_accion_social_automatica(
                    self.modelo.paso_actual
                )  # Simplificado a pulso social
            elif tipo == "formar_grupo":
                return self.modelo.formar_grupos()

            # 4. Acciones de Construcción y Skills
            elif tipo in ["construir", "constrir"]:
                edificio = params.get("edificio") or params.get("tipo")
                if edificio:
                    exito, msg = self.modelo.construir_edificio(self, edificio)
                    return exito
            elif tipo == "skill_factory" or "crear_herramienta" in tipo:
                # Delegar al skill manager
                res = skill_manager.ejecutar_accion_evolutiva(self, accion_dict)
                return res.get("exito", False)

            # 5. Acciones de Combate y Tensión
            elif tipo == "atacar":
                target_id = params.get("target_id")
                if target_id:
                    target = self.modelo.get_agent_by_id(target_id)
                    if target:
                        return self.atacar(target)

            # Fallback: log de acción no reconocida
            # self.modelo.log(f"⚠️ Acción no reconocida: {tipo}", agente_id=self.unique_id)
            return False

        except Exception as e:
            # self.modelo.log(f"❌ Error ejecutando acción {tipo}: {e}", categoria="error")
            return False


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
            0.0  # Segundos de pausa entre agentes para un flujo mucho más rápido
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
            herramientas.log_callback = self.log
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
        self.agente_turno_asamblea_idx = 0  # Índice del agente en turno para asamblea
        self.asamblea_bloqueante_activa = False  # Bloqueo total hasta consenso
        self.plebiscito_simultaneo_activo = False  # Nueva flag para voto rápido
        self.consenso_alcanzado = False  # Flag para ciclo de asamblea
        self.instituciones = {}  # Almacena instituciones formalizadas
        self.guerras_activas = []
        self.grupos_creados_este_paso = 0
        self.moderador_id = None
        self.ultimo_paso_asamblea = -100  # Cooldown inicial para asambleas
        self.infraestructura = []
        self.civilizaciones = {}
        self.grupos_dinamicos = {}
        self.seed = str(random.randint(0, 99999999))
        self.world = None  # Se inicializará después de cargar_estado()
        self.mapa = None  # Lista vacía inicial
        self._map_dirty = False  # Marca cambios estructurales del mapa para refresco en frontend
        self.mapa_size = 20  # Tamaño por defecto
        self.COSTO_EXPANSION = 1000.0  # Costo en MC por cada nivel de expansión
        self.ubicacion_universidad = None
        self.weather = WeatherType.SUNNY
        self.weather_timer = 0
        self.weather_duration = 20
        self.lore = ""
        self.eventos_activos = []
        self.sistema_misiones = SistemaMisiones()
        self.misiones_completadas_este_turno = []
        self.historia = LibretaHistoria()
        self.db_active = True
        self.db = DatabaseManager()
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

        # Intentar cargar la simulación de la base de datos
        self.cargar_estado()

        # Inicializar social_recsys si no se cargó de DB
        if self.social_recsys is None:
            try:
                self.social_recsys = SocialRecSys(self.db, self.user_id)
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

        # Inicializar skill factory y cerebro
        from core.skill_factory import SkillFactory

        global skill_factory
        skill_factory = SkillFactory(skill_manager)
        from agents.cerebro_llm import initialize_cerebro_with_skills

        initialize_cerebro_with_skills(skill_factory)

    def _procesar_turno_agente(self, agente):
        """Procesa el ciclo completo de vida de un agente en un turno.

        Estructura obligatoria por turno (gamificación):
        1) Un mensaje (público/privado/grupal según decida el agente)
        2) Una acción física en el mundo
        3) Una acción en la red social

        Este método garantiza que si la IA no propone alguno de esos pasos, se
        generan fallback razonables basados en necesidades y el estado del agente.
        """
        if not agente.esta_vivo:
            return

        # 1. ACTUALIZAR METABOLISMO
        agente.necesidades["alimento"] = max(0, agente.necesidades["alimento"] - 0.15)
        agente.necesidades["descanso"] = max(0, agente.necesidades["descanso"] - 0.10)
        agente.necesidades["social"] = max(0, agente.necesidades["social"] - 0.08)

        # Auto-alimentación si tiene hambre y comida
        if (
            agente.necesidades["alimento"] < 4.0
            and agente.inventario.get("comida", 0) > 0
        ):
            agente.comer()

        # 2. CEREBRO: LANGGRAPH / LLM / BDI
        # Llamar al cerebro avanzado para decidir pensamiento, mensaje y acción
        decision = agente.cerebro.pensar(agente)

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
            if self.realtime_event_callback:
                try:
                    self.realtime_event_callback(
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

            if self.realtime_event_callback:
                try:
                    self.realtime_event_callback(
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

    def _procesar_asambleas(self):
        """Avanza los ciclos de debate y votación en las asambleas activas."""
        for asamblea in self.asambleas_globales:
            if asamblea["estado"] == "DEBATE":
                asamblea["pasos_restantes"] -= 1
                if asamblea["pasos_restantes"] <= 0:
                    asamblea["estado"] = "VOTACION"
                    self.log(
                        f"🗳️ [ASAMBLEA] Se abre el periodo de votación para: {asamblea['tema']}",
                        categoria="consenso",
                    )

            elif asamblea["estado"] == "VOTACION":
                # Si todos han votado o pasa el tiempo
                asamblea["pasos_restantes"] -= 1  # Reutilizado para tiempo de voto
                if asamblea["pasos_restantes"] <= -3:  # 3 pasos para votar
                    # Concluir asamblea
                    si = asamblea["votos_si"]
                    no = asamblea["votos_no"]
                    if si > no:
                        asamblea["estado"] = "APROBADA"
                        self.log(
                            f"✅ [ASAMBLEA] Propuesta APROBADA: {asamblea['tema']}",
                            categoria="consenso",
                        )
                    else:
                        asamblea["estado"] = "RECHAZADA"
                        self.log(
                            f"❌ [ASAMBLEA] Propuesta RECHAZADA: {asamblea['tema']}",
                            categoria="consenso",
                        )

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

    def calcular_gini(self):
        """Calcula el coeficiente de Gini para medir la desigualdad de recursos."""
        recursos = sorted([a.recursos for a in self.agentes])
        n = len(recursos)
        if n == 0 or sum(recursos) == 0:
            return 0

        index = np.arange(1, n + 1)
        gini = (np.sum((2 * index - n - 1) * recursos)) / (n * np.sum(recursos))
        return gini

    def calcular_felicidad_promedio(self):
        """Calcula una métrica de bienestar general basada en necesidades."""
        if not self.agentes:
            return 0
        total = 0
        for a in self.agentes:
            f = (
                a.necesidades.get("alimento", 0)
                + a.necesidades.get("descanso", 0)
                + a.necesidades.get("social", 0)
            ) / 3.0
            total += f
        return total / len(self.agentes)

    def actualizar_economia(self):
        """Registra el historial económico para gráficas."""
        self.economia["historial_indice"].append(self.economia["indice_bursatil"])
        self.economia["historial_precios"].append(self.economia["precio_recurso"])
        if len(self.economia["historial_indice"]) > 100:
            self.economia["historial_indice"].pop(0)
            self.economia["historial_precios"].pop(0)

    def formar_grupos(self):
        """Los agentes con lazos de amistad o conocidos forman grupos sociales."""
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
                    if (amigos or conocidos) and self.grupos_creados_este_paso < 2:
                        nuevo_id = f"Clan_{agente.unique_id}"
                        agente.grupo_id = nuevo_id

                        # Registrar como Civilización oficial
                        nombre_clan = f"Clan de {agente.alma.nombre_propio if hasattr(agente, 'alma') else agente.unique_id}"
                        color_clan = f"#{random.randint(0, 0xFFFFFF):06x}"

                        self.civilizaciones[nuevo_id] = Civilizacion(
                            id=nuevo_id,
                            nombre=nombre_clan,
                            color=color_clan,
                            user_id=self.user_id,
                        )

                        # Unir a los amigos y conocidos
                        for id_rel in (amigos + conocidos)[:3]:
                            rel_obj = self.get_agent_by_id(id_rel)
                            if rel_obj:
                                rel_obj.grupo_id = nuevo_id

                        self.log(
                            f"🚩 [CLAN] Se ha formado un nuevo clan: '{nombre_clan}'",
                            categoria="consenso",
                        )
                        self.grupos_creados_este_paso += 1

    def asignar_roles_consenso(self):
        """Negociación de roles internos en grupos basada en habilidades."""
        for g_id, civ in self.civilizaciones.items():
            miembros = [a for a in self.agentes if a.grupo_id == g_id]
            if not miembros:
                continue

            # Si no hay líder, el que tiene más rango/XP es el líder
            lider_actual = next((m for m in miembros if m.rol == "Líder"), None)
            if not lider_actual:
                mejor = max(miembros, key=lambda m: m.rango)
                mejor.rol = "Líder"
                self.log(
                    f"👑 [LIDERAZGO] {mejor.unique_id} ha sido reconocido como líder de {civ.nombre}",
                    categoria="consenso",
                )

    def evaluar_evolucion_civilizaciones(self):
        """Chequea si las civilizaciones cumplen hitos para avanzar."""
        # Lógica simplificada: si tienen más de 5 miembros y 500 recursos totales
        for g_id, civ in self.civilizaciones.items():
            miembros = [a for a in self.agentes if a.grupo_id == g_id]
            recursos_totales = sum(m.recursos for m in miembros)
            if len(miembros) >= 5 and recursos_totales > 500:
                # Podría desbloquear tecnologías o edificios
                pass

    def step(self):
        """Avanza un paso en la simulación."""
        if getattr(self, "_stopped", False):
            return  # No procesar si la simulación fue detenida
        self.paso_actual += 1
        self.grupos_creados_este_paso = 0

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

        for agente in agentes_activos:
            if getattr(self, "_force_stop", False):
                break
            agente.realizar_turno()

            # Pausa de lectura entre agentes
            if hasattr(self, "ritmo") and self.ritmo > 0 and len(agentes_vivos) > 1:
                time.sleep(self.ritmo)

        # Notificar cambios de estado de forma throttled, no por cada agente
        if self.state_change_callback and (
            self.paso_actual == 1 or self.paso_actual % 2 == 0
        ):
            try:
                self.state_change_callback()
            except Exception:
                pass

        # Lógica de formación de grupos (cada 5 pasos para mayor actividad social)
        if self.paso_actual % 5 == 0:
            self.log(
                "📢 [SISTEMA] Evaluando formación de grupos sociales...",
                categoria="sistema",
            )
            self.formar_grupos()
            self.asignar_roles_consenso()
            self.evaluar_evolucion_civilizaciones()  # NUEVO: Chequeo de evolución

        # Economía global
        self.actualizar_economia()

        # Registrar estadísticas/métricas para visualización
        if self.agentes:
            recursos_totales = sum(a.recursos for a in self.agentes)
            promedio_recursos = recursos_totales / len(self.agentes)

            self.datos.append(
                {
                    "paso": self.paso_actual,
                    "recursos_promedio": promedio_recursos,
                    "num_grupos": len(
                        set(a.grupo_id for a in self.agentes if a.grupo_id is not None)
                    ),
                    "gini": self.calcular_gini(),
                    "felicidad": self.calcular_felicidad_promedio(),
                }
            )

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

        # Limpiar mensaje global después de que todos los agentes lo hayan procesado en este paso
        self.mensaje_global_arquitecto = None

    def verificar_misiones(self):
        """
        [DEPRECATED] Este método es legacy.
        La verificación de misiones ahora la maneja self.sistema_misiones.verificar_misiones() llamado en step().
        """
        pass
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

        if tipo not in config_edificios:
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
            else:
                return (
                    False,
                    "Tipo de edificio no válido o requisitos de invención no cumplidos.",
                )

        tile = self.mapa[agente.x][agente.y]
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

        # Validación de inventario real
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

        return False, "No tienes suficientes recursos o dinero."

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
            query = "INSERT INTO eventos_globales (tipo, descripcion, paso_inicio, duracion, impacto) VALUES (%s, %s, %s, %s, %s)"
            self.db.execute(
                query,
                (tipo, descripcion, self.paso_actual, duracion, Json(impacto or {})),
            )

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

    def crear_mision(self, titulo, descripcion, tipo, objetivo, recompensa):
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

    @synchronized
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
            if (
                len(self.historial_logs) > 1000
            ):  # Mantener los últimos 1000 en RAM para sincronización inicial
                self.historial_logs.pop(0)

        # PERSISTENCIA EN DB
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
            except Exception as e:
                logger.error(f"Error guardando log en DB: {e}")
        else:
            logger.warning(
                f"[LOG] No se guardó en DB: db_active={self.db_active}, user_id={self.user_id}"
            )

        print(f"[LOG DEBUG] categoria={categoria}, mensaje={mensaje[:80]}...")

        if self.log_callback:
            # El callback puede no ser thread-safe (especialmente si encola en asyncio),
            # pero ya lo manejamos con run_coroutine_threadsafe en api.py
            self.log_callback(
                mensaje,
                categoria,
                subtitulos,
                tts_text,
                pensamiento,
                privado_para,
                agente_id,
            )
        else:
            print(mensaje)
            if subtitulos:
                print(f"             └─ [Subtítulos: {subtitulos}]")

    def notificar_cambio_estado(self):
        """Notifica al frontend que ha habido un cambio de estado importante."""
        if self.state_change_callback and not getattr(self, "_stopped", False):
            try:
                self.state_change_callback()
            except Exception as e:
                logger.error(f"Error en state_change_callback: {e}")

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

                        # Registrar como Civilización oficial para el frontend
                        nombre_clan = f"Clan de {agente.unique_id}"
                        color_clan = self.colores_paleta[
                            hash(nuevo_id) % len(self.colores_paleta)
                        ]

                        self.civilizaciones[nuevo_id] = Civilizacion(
                            id=nuevo_id,
                            nombre=nombre_clan,
                            color=color_clan,
                            user_id=self.user_id,
                        )
                        self.objetivos_grupos[nuevo_id] = (
                            f"Cooperación de {nombre_clan}"
                        )

                        # Unir a los amigos y conocidos
                        todos = amigos + conocidos
                        for id_rel in todos[:5]:  # Máximo 5 miembros iniciales
                            rel_obj = self.get_agent_by_id(id_rel)
                            if rel_obj:
                                rel_obj.grupo_id = nuevo_id
                                rel_obj.civilizacion_id = nuevo_id

                        self.log(
                            f"🚩 [CLAN] Se ha formado un nuevo clan: '{nombre_clan}' liderado por {agente.unique_id}.",
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
        # Líderes por rango
        lideres = sorted(self.agentes, key=lambda a: a.rango, reverse=True)[:3]
        print("\nTop 3 Agentes con mayor Rango (Estatus):")
        for l in lideres:
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

                # Guardar Leyes y Propuestas
                for ley in self.leyes_globales:
                    self.db.save_proposal(ley, self.user_id)
                for grupo_id, leyes in self.facciones_leyes.items():
                    for ley in leyes:
                        ley_copy = ley.copy()
                        ley_copy["grupo_id"] = grupo_id
                        self.db.save_proposal(ley_copy, self.user_id)
                for asamblea in self.asambleas_globales:
                    prop = {
                        "proponente_id": asamblea["proponente_id"],
                        "texto": asamblea["tema"],
                        "tipo": "asamblea",
                        "votos": {
                            "si": asamblea["votos_si"],
                            "no": asamblea["votos_no"],
                        },
                        "estado": asamblea["estado"],
                        "paso_creacion": asamblea["paso_inicio"],
                    }
                    self.db.save_proposal(prop, self.user_id)

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
                        if mapa_ancho != self.mapa_size:
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
                            if mapa_ancho != self.mapa_size:
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
                                    "tipo": tipo,
                                    "recursos_vistos": rec_v,
                                    "grupo": grp_v,
                                },
                            }
                        )
                        mem_dict["aristas"].append(
                            {
                                "u": a_id,
                                "v": target_id,
                                "data": {"tipo": tipo, "fuerza": fuerza},
                            }
                        )

                    a.memoria.cargar_datos(mem_dict)
                    self.agentes.append(a)

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

                        if p_tipo == "asamblea" and estado != "FINALIZADA":
                            asamblea = {
                                "id": f"ASAMBLEA-{p_id}",
                                "proponente_id": prop_id,
                                "tema": texto,
                                "moderador_id": prop_id,
                                "votos_si": votos.get("si", 0),
                                "votos_no": votos.get("no", 0),
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
                        # id, nombre, tipo, fundador_id, lider_id, miembros, x, y, recursos, nivel, descripcion
                        (
                            i_id,
                            i_nom,
                            i_tipo,
                            i_fund,
                            i_lid,
                            i_miem,
                            i_x,
                            i_y,
                            i_rec,
                            i_niv,
                            i_desc,
                        ) = i_row

                        # Asegurar miembros sea lista
                        if isinstance(i_miem, str):
                            try:
                                i_miem = json.loads(i_miem)
                            except:
                                i_miem = [i_fund]

                        inst = Institucion(
                            i_id, i_nom, i_tipo, i_fund, i_x, i_y, target_user_id
                        )
                        inst.lider_id = i_lid
                        inst.miembros = i_miem
                        inst.recursos = i_rec
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
                logger.error(f"❌ Error cargando desde DB: {e}")

        else:
            logger.info(
                "⚠️ [DB] No se cargó la simulación desde Postgres o db inactiva."
            )
            self.agentes_cargados = False

    def asignar_roles_consenso(self):
        """Los grupos negocian roles internos basados en méritos y personalidad."""
        grupos = {}
        for a in self.agentes:
            if a.grupo_id is not None:
                if a.grupo_id not in grupos:
                    grupos[a.grupo_id] = []
                grupos[a.grupo_id].append(a)

        for g_id, miembros in grupos.items():
            if len(miembros) < 2:
                continue

            # --- FASE DE ASAMBLEA ---
            self.log(
                f"🏛️ [ASAMBLEA FACCIÓN {g_id}] Los miembros se reúnen para debatir el futuro...",
                categoria="consenso",
            )

            # Verificar si hay propuestas de liderazgo activas o si no hay líder
            lider_actual = next((m for m in miembros if m.rol == "Líder"), None)

            if not lider_actual:
                self.log(
                    f"🔸 [ASAMBLEA] La Facción {g_id} no tiene un líder claro. Se anima a los miembros a presentar sus programas (PROPONER_LEY:local:LIDERAZGO:Nombre:Plan).",
                    categoria="consenso",
                )
                # El cerebro LLM decidirá proponerse como líder en su turno si tiene la ambición

            ids_miembros = [m.unique_id for m in miembros]
            lider_id = lider_actual.unique_id if lider_actual else "Ninguno"
            for m in miembros:
                ctx = (
                    f"El líder actual es {lider_id}. La facción busca consolidar su poder."
                    if lider_actual
                    else "No hay líder. Es momento de proponerse o buscar consensos para elegir uno."
                )
                # Los agentes aprovechan la asamblea para expresar pensamientos generales
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
        costo_base_por_casilla = 500
        num_direcciones = 4 if direccion is None else 1
        num_casillas_estimadas = cantidad * self.mapa_size * num_direcciones
        costo_total = (
            costo_override
            if costo_override is not None
            else (costo_base_por_casilla * num_casillas_estimadas)
        )

        if comprador_id:
            # Fondos del Arquitecto o del Grupo
            if comprador_id == "arquitecto":
                fondos = self.economia.get("total_dinero", 0)
                tipo = "Arquitecto"
            else:
                # Buscar si el comprador es un grupo o civilización
                grupo = self.civilizaciones.get(
                    comprador_id
                ) or self.grupos_dinamicos.get(comprador_id)
                if not grupo:
                    return False, f"Comprador {comprador_id} no encontrado"
                fondos = grupo.get("dinero", 0)
                tipo = "Grupo"

            if fondos < costo_total:
                return (
                    False,
                    f"Fondos insuficientes para {tipo}: {fondos} MC disponibles, {costo_total} MC requeridos",
                )

            # Verificar permisos (líderes o arquitecto)
            if comprador_id != "arquitecto":
                es_lider = any(
                    a.unique_id == comprador_id and a.rol == "Líder"
                    for a in self.agentes
                )
                if not es_lider:
                    return (
                        False,
                        f"{comprador_id} no tiene permisos de líder para expandir",
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
                    grupo = self.civilizaciones.get(
                        comprador_id
                    ) or self.grupos_dinamicos.get(comprador_id)
                    grupo["dinero"] -= costo_total

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

        # Solo líderes de grupo pueden comprar terreno para su grupo
        for agente in self.agentes:
            if agente.unique_id == comprador_id:
                return agente.rol == "Líder" and agente.grupo_id is not None

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
        Requiere que el líder del grupo tenga fondos suficientes.
        """
        if grupo_id not in self.grupos_dinamicos:
            return False, f"Grupo {grupo_id} no encontrado"

        # Encontrar líder del grupo
        lider = None
        for agente in self.agentes:
            if agente.grupo_id == grupo_id and agente.rol == "Líder":
                lider = agente
                break

        if not lider:
            return False, f"No se encontró líder para el grupo {grupo_id}"

        # Intentar expansión con el líder como comprador
        return self.expandir_mundo(direccion, cantidad, lider.unique_id)

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


if __name__ == "__main__":
    # Configuración desde .env
    num_agentes = int(os.getenv("NUM_AGENTES", 30))
    pasos = int(os.getenv("PASOS_SIMULACION", 100))

    # Configuración de la simulación
    modelo = ModeloRelacional(num_agentes=num_agentes)
    modelo.ejecutar(pasos=pasos)
    modelo.imprimir_resumen_social()
    modelo.visualizar_resultados()
