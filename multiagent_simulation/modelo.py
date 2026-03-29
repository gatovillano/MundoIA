import random
import time
import matplotlib
matplotlib.use('Agg') # Backend para entornos sin interfaz gráfica
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from memoria import MemoriaGrafica
from cerebro_langgraph import CerebroAvanzado
from cerebro_llm import cerebro_llm
from dotenv import load_dotenv
import os
import json
import functools
from herramientas import herramientas

def synchronized(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Asegurar que tenemos acceso al modelo y su lock
        lock = getattr(self.modelo, 'lock', None) if hasattr(self, 'modelo') else None
        if lock:
            with lock:
                return func(self, *args, **kwargs)
        return func(self, *args, **kwargs)
    return wrapper
from skills_manager import skill_manager
from sistema_misiones import SistemaMisiones, Mision
from historia import LibretaHistoria
from action_validator import validar_accion, obtener_accion_fallback
from optimizador import DecisionOptimizer
import psycopg2
from psycopg2.extras import Json as _Json

# Wrapper para que Psycopg2 use nuestro encoder al guardar JSONs
def Json(data):
    return _Json(data, dumps=lambda obj: json.dumps(obj, cls=DateTimeEncoder))
import logging
from datetime import datetime, date

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import bcrypt
import uuid

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# ... (imports existentes)

class DatabaseManager:
    def __init__(self):
        self.conn_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "database": os.getenv("DB_NAME", "mundoia"),
            "user": os.getenv("DB_USER", "architect"),
            "password": os.getenv("DB_PASS", "mundoia_secret_2026"),
            "port": os.getenv("DB_PORT", "5434")
        }
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = True
            logger.info(f"✅ Conexión establecida a {self.conn_params['host']}:{self.conn_params['port']} db={self.conn_params['database']}")
            self.initialize_db()
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            return False

    def initialize_db(self):
        """Inicializa las tablas de la base de datos usando schema.sql y create_users_table.sql"""
        if not self.conn: return False
        try:
            for schema_file in ["schema.sql", "create_users_table.sql"]:
                schema_path = os.path.join(os.path.dirname(__file__), schema_file)
                if os.path.exists(schema_path):
                    with open(schema_path, "r") as f:
                        schema_sql = f.read()
                    
                    logger.info(f"📜 Intentando ejecutar esquema desde: {schema_path}")
                    with self.conn.cursor() as cur:
                        cur.execute(schema_sql)
                    logger.info(f"✅ Esquema {schema_file} verificado/inicializado.")
                else:
                    logger.warning(f"⚠️ No se encontró {schema_file} en {os.path.dirname(__file__)}")
            
            # Migración automática: Añadir columna memoria_mensajes si no existe
            try:
                with self.conn.cursor() as cur:
                   cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS memoria_mensajes JSONB DEFAULT '[]';")
                   cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '{}';")
                   cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS skill_factor FLOAT DEFAULT 0.3;")
                   # Migración para logs
                   cur.execute("ALTER TABLE logs_simulacion ADD COLUMN IF NOT EXISTS subtitulos TEXT;")
                   cur.execute("ALTER TABLE logs_simulacion ADD COLUMN IF NOT EXISTS tts_text TEXT;")
                   self.conn.commit()
            except Exception as e:
                logger.warning(f"Nota: Migración de columnas adicionales ya aplicada o error: {e}")
                self.conn.rollback()

            return True
        except Exception as e:
            logger.error(f"❌ Error inicializando esquema DB: {e}")
            return False

    def execute(self, query, params=None):
        if not self.conn: return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
            return True
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            return False

    def create_user(self, username, password):
        """Crea un nuevo usuario con contraseña hasheada."""
        try:
            user_id = str(uuid.uuid4())
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            query = "INSERT INTO usuarios (id, username, password_hash) VALUES (%s, %s, %s);"
            self.execute(query, (user_id, username, hashed_password.decode('utf-8')))
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
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                return user_id
        return None

    def ensure_user_exists(self, user_id, username=None):
        """Asegura que un usuario exista en la tabla usuarios."""
        query = "SELECT id FROM usuarios WHERE id = %s;"
        result = self.execute(query, (user_id,))
        
        if not result:
            username = username or f"user_{user_id}"
            # Usar una contraseña por defecto para usuarios autogenerados
            self.create_user(username, "default_password")
            logger.info(f"✅ Usuario {username} creado automáticamente en la base de datos")
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
                # 2. Logs de simulación
                cur.execute("DELETE FROM logs_simulacion WHERE user_id = %s;", (user_id,))
                # 3. Propuestas y leyes
                cur.execute("DELETE FROM propuestas WHERE user_id = %s;", (user_id,))
                # 4. Misiones activas del usuario
                cur.execute("DELETE FROM misiones WHERE user_id = %s;", (user_id,))
                # 5. Agentes (después de borrar memorias que los referencian)
                cur.execute("DELETE FROM agentes WHERE user_id = %s;", (user_id,))
                # 6. Civilizaciones/grupos
                cur.execute("DELETE FROM civilizaciones WHERE user_id = %s;", (user_id,))
                # 7. Estado del mundo
                cur.execute("DELETE FROM estado_mundo WHERE user_id = %s;", (user_id,))
                # NOTA: No borramos 'usuarios' ni 'puntajes_usuarios' — el historial del jugador se conserva
            self.conn.commit()
            logger.info(f"🗑️ Datos de la partida de {user_id} limpiados correctamente de la DB.")
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
        INSERT INTO agentes (id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, civilizacion_id, alianzas, tratados, memoria_mensajes, x, y, skills, skill_factor)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
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
            skill_factor = EXCLUDED.skill_factor;
        """
        self.execute(query, (
            str(agent.unique_id), user_id, agent.recursos, agent.dinero, agent.grupo_id, agent.rol,
            agent.profesion, agent.rango, agent.reputacion, Json(agent.personalidad),
            Json(agent.necesidades), Json(agent.experiencia), Json(agent.conocimientos),
            Json(agent.inventario), Json(getattr(agent, 'hitos', [])), Json(agent.historial_etico),
            agent.civilizacion_id, Json(getattr(agent, 'alianzas', [])), Json(getattr(agent, 'tratados', [])),
            Json(agent.memoria.historial_mensajes),
            agent.x, agent.y, Json(agent.skills), agent.skill_factor
        ))

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
        self.execute(query, (civ.id, civ.nombre, civ.color, civ.user_id, civ.recursos_globales, Json(civ.territorio)))

    def get_civilizations(self, user_id):
        query = "SELECT id, nombre, color, recursos_globales, territorio FROM civilizaciones WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_memory(self, owner_id, target_id, data, user_id):
        # Verificar integridad referencial para evitar errores de Foreign Key
        check_query = "SELECT COUNT(*) FROM agentes WHERE id IN (%s, %s) AND user_id = %s;"
        res = self.execute(check_query, (str(owner_id), str(target_id), user_id))
        if not res or res[0][0] < 2:
            return # No guardamos si alguno de los agentes no existe en la DB

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
            user_id, str(owner_id), str(target_id), data.get('tipo'), data.get('fuerza', 0.0),
            data.get('recursos_vistos'), data.get('grupo')
        )
        self.execute(query, params)

    def save_world_state(self, user_id, step, lore, seed, economy, relaciones_grupos=None, objetivos_grupos=None, mapa=None, infraestructura=None, historia=None):
        query = """
        INSERT INTO estado_mundo (user_id, paso_actual, lore, seed, precio_recurso, indice_bursatil, total_dinero, relaciones_grupos, objetivos_grupos, mapa, infraestructura, historia)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            historia = EXCLUDED.historia;
        """
        params = (
            user_id, step, lore, seed, economy.get('precio_recurso', 2.0),
            economy.get('indice_bursatil', 1000.0), economy.get('total_dinero', 0.0),
            Json(relaciones_grupos) if relaciones_grupos else Json({}),
            Json(objetivos_grupos) if objetivos_grupos else Json({}),
            Json(mapa) if mapa else None,
            Json(infraestructura) if infraestructura else Json([]),
            Json(historia) if historia else Json({})
        )
        self.execute(query, params)

    def get_world_state(self, user_id):
        query = "SELECT paso_actual, lore, seed, precio_recurso, indice_bursatil, total_dinero, relaciones_grupos, objetivos_grupos, mapa, infraestructura, historia FROM estado_mundo WHERE user_id = %s ORDER BY id DESC LIMIT 1;"
        result = self.execute(query, (user_id,))
        return result[0] if result else None

    def get_agents(self, user_id):
        query = """
            SELECT id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, 
                   personalidad, necesidades, experiencia, conocimientos, inventario, hitos, 
                   historial_etico, civilizacion_id, alianzas, tratados, memoria_mensajes, x, y, skills, skill_factor, timestamp 
            FROM agentes WHERE user_id = %s;
        """
        return self.execute(query, (user_id,))

    def get_memories(self, agent_id, user_id):
        query = "SELECT agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido FROM memorias WHERE agente_fuente = %s AND user_id = %s;"
        return self.execute(query, (str(agent_id), user_id))

    def save_proposal(self, prop, user_id):
        """Guarda o actualiza una propuesta/ley."""
        # Nota: Como 'id' en la DB es SERIAL, el ON CONFLICT (id) solo sirve si pasamos el ID numerico.
        # Si la propuesta tiene un ID de string (ej: LEY-XXXX), no podemos usarlo como integer 'id'.
        
        votos = Json(prop.get('votos', {}))
        estado = prop.get('estado', 'pendiente')
        titulo = prop.get('titulo')
        contenido = prop.get('contenido')
        
        # Intentar determinar si es una actualizacion o insercion
        db_id = prop.get('db_id') # Podemos guardar el ID de DB original si existe
        
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
            self.execute(query, (
                user_id, prop.get('grupo_id'), prop.get('proponente_id'),
                prop.get('texto'), prop.get('tipo'), votos,
                estado, prop.get('paso_creacion', 0), titulo, contenido
            ))

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
        self.execute(query, (
            mision.id, user_id, mision.titulo, mision.descripcion, mision.tipo,
            mision.dificultad, Json(mision.objetivo), mision.recompensa_puntos,
            mision.estado, mision.turno_inicio, mision.turno_limite,
            mision.completada_por, mision.turno_completada
        ))

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
        return self.execute(query)

    def save_log(self, user_id, paso, mensaje, categoria, pensamiento=None, privado_para=None, subtitulos=None, tts_text=None, agente_id=None):
        query = """
        INSERT INTO logs_simulacion (user_id, paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        self.execute(query, (user_id, paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id))

    def get_logs(self, user_id, limit=500):
        query = """
        SELECT paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id
        FROM logs_simulacion WHERE user_id = %s ORDER BY timestamp ASC LIMIT %s;
        """
        return self.execute(query, (user_id, limit))

        # Nota: No borramos el usuario en sí de la tabla 'usuarios'
        
        logger.info(f"✅ Base de datos limpiada completamente para el usuario {user_id}.")

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
        # Devuelve lista de dicts: [{"role": ..., "content": ..., "timestamp": ...}, ...]
        if not rows:
            return []
        # La consulta devuelve filas con 3 columnas: role, content, timestamp_utc
        return [{"role": row[0], "content": row[1], "timestamp": row[2]} for row in rows]

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
        self.profecias_activas = [] # List of dicts: {"id", "tipo", "objetivo", "recompensa"}
        self.agente_poseido_id = None
        
        self.recursos_globales = 0.0
        self.territorio = [] # Lista de (x, y)
        self.tecnologias = []
        self.leyes = []
        self.tipo = "GRUPO" # NUEVO: "GRUPO" o "CIVILIZACION"

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
            "tipo": self.tipo
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruye un objeto Civilizacion desde un diccionario serializado."""
        if not data: return None
        civ = cls(
            id=data["id"],
            nombre=data["nombre"],
            color=data["color"],
            user_id=data.get("user_id"),
            descripcion=data.get("descripcion", "")
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
        self.tipo = tipo # "EDUCATIVA", "FINANCIERA", "SANITARIA", "CIENTIFICA", "RELIGIOSA"
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
            "descripcion": self.descripcion
        }

    @classmethod
    def from_dict(cls, data):
        if not data: return None
        inst = cls(
            id=data["id"],
            nombre=data["nombre"],
            tipo=data["tipo"],
            fundador_id=data["fundador_id"],
            x=data["x"],
            y=data["y"],
            user_id=data.get("user_id")
        )
        inst.lider_id = data.get("lider_id")
        inst.miembros = data.get("miembros", [])
        inst.recursos = data.get("recursos", 0.0)
        inst.nivel = data.get("nivel", 1)
        inst.descripcion = data.get("descripcion", "")
        return inst

class TerrainType:
    GRASS = "grass"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    WATER = "water"
    DESERT = "desert"

    STATS = {
        "grass": {"yield": 1.0, "energy_cost": 0.04, "move_difficulty": 1.0, "health_risk": 0.0},
        "forest": {"yield_wood": 2.0, "yield_food": 1.5, "yield": 1.2, "energy_cost": 0.06, "move_difficulty": 1.5, "health_risk": 0.0},
        "mountain": {"yield_stone": 2.0, "yield": 0.7, "energy_cost": 0.12, "move_difficulty": 3.0, "health_risk": 0.05},
        "water": {"yield_food": 0.2, "yield": 0.1, "energy_cost": 0.10, "move_difficulty": 5.0, "health_risk": 0.02},
        "desert": {"yield": 0.5, "energy_cost": 0.15, "move_difficulty": 1.2, "health_risk": 0.08}
    }

class WeatherType:
    SUNNY = "sunny"
    RAINY = "rainy"
    STORM = "storm"
    FOGGY = "foggy"
    HEATWAVE = "heatwave"



class Tile:
    def __init__(self, x, y, terrain_type=TerrainType.GRASS):
        self.x = x
        self.y = y
        self.terrain_type = terrain_type
        self.resource_node = None # {type: "food"|"wood"|"stone", amount: 100}
        self.owner_civ_id = None
        self.buildings = [] # List of building dicts
        
        # Obtener estadísticas del terreno
        stats = TerrainType.STATS.get(terrain_type, TerrainType.STATS[TerrainType.GRASS])
        self.difficulty = stats["move_difficulty"]
        self.yield_mult = stats["yield"]
        self.energy_cost = stats["energy_cost"]
        self.health_risk = stats["health_risk"]
    
    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "terrain": self.terrain_type,
            "resource": self.resource_node,
            "owner": self.owner_civ_id,
            "buildings": self.buildings,
            "difficulty": self.difficulty
        }

class Agente:
    def __init__(self, unique_id, modelo, recursos=100, necesidades=None, personalidad=None, civ_id=None, x=None, y=None):
        self.unique_id = unique_id
        self.modelo = modelo
        self.recursos = recursos
        self.civilizacion_id = civ_id
        self.objetivo_movimiento = None # (x, y) a donde moverse
        
        # Posición en el mundo - Priorizar x, y pasados para evitar saltos al reiniciar
        if x is not None and y is not None:
            self.x = x
            self.y = y
        else:
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
                "hostilidad": random.random()
            }
            
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
                "salud": 10.0
            }
        
        # --- SISTEMA DE SKILLS ---
        self.skills = {} # Dictionary of Skill objects
        self.skill_factor = random.uniform(0.1, 0.5) # Initial skill factor
        self.decision_cacheada = None
        
        # Memoria basada en Grafos
        self.memoria = MemoriaGrafica(self.unique_id)
        
        # Cerebro Cognitivo (TODOS los agentes ahora son inteligentes)
        self.cerebro = CerebroAvanzado(self.unique_id)
        
        # Nuevos atributos: Grupo y Jerarquía
        self.grupo_id = None
        self.rol = "Ciudadano" # Rol inicial
        self.ultimo_mensaje_recibido = None # Para responder a otros
        self.dinero = 100.0 # Nueva unidad de cambio: MundoCoins (MC)
        self.rango = 1.0 # Estatus social (influye en la influencia)
        self.conocimientos = {} # Información compartida o descubierta
        self.planes = [] # Acuerdos con otros agentes
        self.gasto_turno = 0.0 # Control de gasto por turno
        self.inversiones = [] # [{monto, paso_inicio, interes_esperado}]
        self.alianzas = [] # Lista de IDs de agentes aliados (para compatibilidad)
        self.tratados = [] # Lista de dicts: {"socio_id": ID, "terminos": {...}, "pasos_restantes": N}
        self.inventario = {
            "comida": int(self.recursos),
            "madera": 0,
            "piedra": 0,
            "hierro": 0,
            "medicina": 0,
            "ocio": 0
        }
        
        # --- SISTEMA DE PROFESIONES ---
        self.profesion = None # "Médico", "Comerciante", "Guarda", "Explorador"
        self.experiencia = {
            "medicina": 0,
            "comercio": 0,
            "combate": 0,
            "exploracion": 0,
            "social": 0,
            "ingenieria": 0,
            "agricultura": 0
        }
        self.hitos = [] # Lista de logros alcanzados
        
        # --- SISTEMA POLÍTICO ---
        self.reputacion = 1.0 # 0.0 a 1.0 (Prestigio social)
        self.votos_recibidos = 0
        self.historial_etico = [] # Registro de crímenes o buenas acciones

        # --- ESTADO COGNITIVO ---
        self.pensamiento_actual = "Esperando estímulos..."
        self.mensaje_arquitecto = None # Cola prioritaria para órdenes divinas
        # --- ESTADO VITAL ---
        self.esta_vivo = True

    def __getstate__(self):
        """
        Define qué atributos del Agente se serializan.
        Excluye 'modelo' para evitar referencias circulares y 'cerebro' ya que es recreable.
        Serializa los datos de 'memoria' en lugar del objeto completo.
        """
        state = self.__dict__.copy()
        del state['modelo']
        del state['cerebro']
        state['memoria_data'] = self.memoria.exportar_datos()
        return state

    def __setstate__(self, state):
        """
        Define cómo se deserializa el Agente.
        Reconstruye 'memoria' y 'cerebro'. 'modelo' se reasigna externamente.
        """
        self.unique_id = state['unique_id'] # Asegurar que unique_id se establece primero
        self.__dict__.update(state)
        self.memoria = MemoriaGrafica(self.unique_id)
        if 'memoria_data' in state:
            self.memoria.cargar_datos(state['memoria_data'])
        self.cerebro = CerebroAvanzado(self.unique_id)
        # 'modelo' se reasigna después de la carga completa de todos los agentes
        self.modelo = None # Placeholder, será reasignado por ModeloRelacional.cargar_estado()

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
            "skills": {k: v if isinstance(v, dict) else v.to_dict() for k, v in self.skills.items()},
            "skill_factor": self.skill_factor,
            "color": self.modelo.civilizaciones[self.grupo_id].color if self.grupo_id and self.grupo_id in self.modelo.civilizaciones else "#ffffff"
        }

    @classmethod
    def from_dict(cls, data, modelo_instance):
        """Reconstruye un objeto Agente desde un diccionario serializado."""
        agente = cls(
            unique_id=data["unique_id"],
            modelo=modelo_instance, # Re-establecer la referencia al modelo
            recursos=data.get("recursos", 100),
            necesidades=data.get("necesidades"),
            personalidad=data.get("personalidad"),
            civ_id=data.get("civilizacion_id"),
            x=data.get("x"),
            y=data.get("y")
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

        if 'memoria_data' in data:
            agente.memoria.cargar_datos(data['memoria_data'])
        
        return agente

    @synchronized
    def decir(self, mensaje, pensamiento=None, privado_para=None, para_grupo=False, global_broadcast=False):
        """Imprime un mensaje directo, privado, para el grupo o global."""
        prefijo = f"[{self.unique_id}]"
        
        # Actualizar pensamiento actual si se proporciona
        if pensamiento:
            self.pensamiento_actual = pensamiento

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
        
        self.modelo.log(f'{prefijo}: "{mensaje}"', categoria="dialogo", tts_text=mensaje, pensamiento=pensamiento, privado_para=privado_para)
        
        # --- REGISTRO EN MEMORIA EPISÓDICA ---
        # Guardar en mi propia memoria que he dicho esto
        self.memoria.registrar_mensaje(self.unique_id, mensaje)

        # --- DISTRIBUCIÓN DE MENSAJES ---
        packet = {
             "emisor": self.unique_id,
             "contenido": mensaje,
             "tipo": "GLOBAL" if global_broadcast else "ASAMBLEA" if not privado_para and not para_grupo else "DIRECTO"
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
                if agent.grupo_id == self.grupo_id and agent.unique_id != self.unique_id:
                    agent.ultimo_mensaje_recibido = packet
                    agent.memoria.registrar_mensaje(self.unique_id, mensaje)
        
        # Si es privado, enviarlo solo al destinatario
        elif privado_para:
            dest_id = privado_para
            dest = next((a for a in self.modelo.agentes if a.unique_id == dest_id), None)
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
        active_assemblies = [a for a in self.modelo.asambleas_globales if a.get("estado") in ["DEBATE", "VOTACION"]]
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
                "contenido": mensaje_enviado
            }

        if tipo_interaccion == "SOCIALIZAR" or tipo_interaccion == "social":
            self.necesidades["social"] = min(10.0, self.necesidades["social"] + 3.0) # Socializar satisface una necesidad vital
            self.reputacion = min(1.0, self.reputacion + 0.01) # Socializar mejora reputación
            # Ganar experiencia social
            self.ganar_experiencia("social", 1)
            hostilidad_total = self.personalidad.get("hostilidad", 0.5) + otro_agente.personalidad.get("hostilidad", 0.5)
            afinidad_base = 0.2 * (self.personalidad["amabilidad"] + otro_agente.personalidad["amabilidad"]) - (0.15 * hostilidad_total)
            
            if otro_agente.dinero > self.dinero * 1.5:
                afinidad_base -= 0.1 * self.personalidad.get("hostilidad", 0.5)

            self.memoria.registrar_interaccion(otro_agente.unique_id, "amigo" if afinidad_base > 0 else "conocido", afinidad_base, otro_agente.recursos, otro_agente.grupo_id)
            self.modelo.log(f"  🤝 [SOCIAL] Agente {self.unique_id} socializa con {otro_agente.unique_id}. Afinidad: {afinidad_base:.2f}", categoria="social")
            
        elif tipo_interaccion == "COMPETIR":
            self.ganar_experiencia("combate", 1)
            self.reputacion = max(0.0, self.reputacion - 0.05)
            
            # El ataque/competencia daña la relación
            self.memoria.registrar_interaccion(otro_agente.unique_id, "enemigo", -0.5, otro_agente.recursos, otro_agente.grupo_id)
            otro_agente.memoria.registrar_interaccion(self.unique_id, "enemigo", -0.5, self.recursos, self.grupo_id)
            
            exito = random.random() * self.rango > random.random() * otro_agente.rango
            if exito:
                robo = 5
                self.recursos += robo
                otro_agente.recursos -= robo
                
                # Robar items del inventario
                items_probables = [k for k, v in otro_agente.inventario.items() if v > 0]
                if items_probables and random.random() < 0.4:
                    item = random.choice(items_probables)
                    otro_agente.inventario[item] -= 1
                    self.inventario[item] = self.inventario.get(item, 0) + 1
                    self.modelo.log(f"  🏴‍☠️ [ROBO] Agente {self.unique_id} le arrebató {item} a {otro_agente.unique_id}!", categoria="conflict")
                
                self.modelo.log(f"  ⚔️ [CONFLICTO] Agente {self.unique_id} robó recursos a {otro_agente.unique_id}.", categoria="conflict")
            else:
                self.modelo.log(f"  🛡️ [FALLO] Agente {self.unique_id} intentó robar a {otro_agente.unique_id} pero falló.", categoria="conflict")

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
                self.modelo.log(f"  💰 [COMERCIO] Agente {self.unique_id} vendió {item} a {otro_agente.unique_id} por {precio} MC.", categoria="economia")
                self.ganar_experiencia("comercio", 2)
                self.memoria.registrar_interaccion(otro_agente.unique_id, "amigo", 0.3, otro_agente.recursos, otro_agente.grupo_id)
            else:
                self.modelo.log(f"  🤝 [COMERCIO] Agente {self.unique_id} intentó comerciar con {otro_agente.unique_id} pero no hubo acuerdo.", categoria="economia")

        elif tipo_interaccion == "ALIANZA":
            self.formar_alianza(otro_agente)
            self.ganar_experiencia("social", 2)
            self.decir(f"¡Hemos sellado una alianza estratégica con {otro_agente.unique_id}!", pensamiento="La unión hace la fuerza. Juntos somos imparables.")

        elif tipo_interaccion == "ATACAR" or tipo_interaccion == "atacar":
            self.ganar_experiencia("combate", 2)
            self.reputacion = max(0.0, self.reputacion - 0.2)
            
            # El ataque siempre destruye la relación
            self.memoria.registrar_interaccion(otro_agente.unique_id, "enemigo", -1.0, otro_agente.recursos, otro_agente.grupo_id)
            otro_agente.memoria.registrar_interaccion(self.unique_id, "enemigo", -1.0, self.recursos, self.grupo_id)
            
            # Cálculo de daño
            daño_base = 2.0 + (self.experiencia["combate"] * 0.5)
            exito = random.random() > 0.3 # 70% éxito
            
            if exito:
                daño_final = daño_base * random.uniform(1, 2)
                self.modelo.log(f"  ⚔️ [ATAQUE] ¡Agente {self.unique_id} ha ATACADO violentamente a {otro_agente.unique_id} causando {daño_final:.1f} de daño!", categoria="conflict")
                otro_agente.recibir_daño(daño_final, f"ataque de {self.unique_id}")
                self.decir(f"¡Prepárate para la derrota, {otro_agente.unique_id}! No toleraré tu presencia.", pensamiento="Eliminar competencia es necesario para mi supremacía.")
            else:
                counter_daño = 1.0
                self.recibir_daño(counter_daño, f"contraataque de {otro_agente.unique_id}")
                self.modelo.log(f"  🛡️ [FALLO] Agente {self.unique_id} falló su ataque y recibió un golpe de {counter_daño}.", categoria="conflict")

        elif tipo_interaccion == "DECLARAR_GUERRA":
            if self.grupo_id and otro_agente.grupo_id:
                exito, msg = self.modelo.declarar_guerra(self.grupo_id, otro_agente.grupo_id)
                self.decir(f"🚩 {msg}" if exito else f"⚠️ No pude declarar la guerra: {msg}", global_broadcast=True)

        elif tipo_interaccion == "NEGOCIAR_PAZ":
            if self.grupo_id and otro_agente.grupo_id:
                exito, msg = self.modelo.finalizar_guerra(self.grupo_id, otro_agente.grupo_id)
                self.decir(f"🕊️ {msg}" if exito else f"⚠️ La negociación de paz falló: {msg}", global_broadcast=True)
        
        # --- IMPACTO DIPLOMÁTICO ---
        if self.grupo_id and otro_agente.grupo_id and self.grupo_id != otro_agente.grupo_id:
            cambio_grupal = 0.05 if (tipo_interaccion == "SOCIALIZAR" or tipo_interaccion == "social" or tipo_interaccion == "ALIANZA") else -0.1
            self.modelo.actualizar_relacion_grupal(self.grupo_id, otro_agente.grupo_id, cambio_grupal)
        
    @synchronized
    def fundar_grupo(self, nombre_grupo, descripcion):
        """El agente crea un nuevo grupo con una idea central y se convierte en líder."""
        if self.modelo.grupos_creados_este_paso >= 3:
            self.modelo.log(f"⚠️ [LIMITE] Agente {self.unique_id} intentó fundar un grupo, pero se alcanzó el límite de 3 por turno.", categoria="sistema")
            return None
        # Generar un ID basado en algo más que random para evitar colisiones si hay muchos
        nuevo_grupo_id = f"G-{random.randint(100, 999)}"
        
        # Intentar obtener un color único que no esté en uso por otra civilización
        colores_en_uso = [c.color for c in self.modelo.civilizaciones.values()]
        nuevo_color = self.modelo.colores_paleta[0] # Default
        
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
            user_id=getattr(self.modelo, 'user_id', None),
            descripcion=descripcion
        )
        # Asegurar que aparezca en el broadcast como grupo dinámico
        self.modelo.objetivos_grupos[nuevo_grupo_id] = descripcion
        
        self.grupo_id = nuevo_grupo_id
        self.civilizacion_id = nuevo_grupo_id
        self.rol = "Líder"
        self.modelo.log(f"🚩 [FUNDACION] Agente {self.unique_id} ha fundado el grupo '{nombre_final}' con el objetivo: {descripcion}", categoria="consenso")
        
        # ACTUAlIZACIÓN INMEDIATA DE UI
        self.modelo.notificar_cambio_estado()
    
        # Hito histórico
        self.modelo.historia.agregar_hito({
            "turno": self.modelo.paso_actual,
            "descripcion": f"El Agente {self.unique_id} ha fundado el grupo '{nombre_final}'.",
            "tipo": "fundacion"
        })
    
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

        mision = self.modelo.objetivos_grupos.get(self.grupo_id, "Prosperidad Colectiva")
        otro_agente.ultimo_mensaje_recibido = {
            "emisor": self.unique_id,
            "contenido": f"INVITACION_GRUPO:{self.grupo_id}:{mision}"
        }
        self.modelo.log(f"✉️ [INVITACION] Agente {self.unique_id} invita a {otro_agente.unique_id} a unirse a la Facción {self.grupo_id}.", categoria="social")
        return True

    def formar_alianza(self, otro_agente, terminos=None):
        """Crea un pacto de alianza mutua con términos específicos."""
        # Limpieza robusta de datos corruptos (strings en lugar de dicts)
        self.tratados = [t for t in self.tratados if isinstance(t, dict)]
        
        # Si no hay términos, es una alianza básica de apoyo mutuo
        if terminos is None:
            terminos = {"tipo": "apoyo_mutuo", "descripcion": "Apoyo social y suministros básicos"}

        # Evitar duplicados de tratados activos con el mismo agente
        if any(t["socio_id"] == otro_agente.unique_id for t in self.tratados):
            return False

        nuevo_tratado_yo = {
            "socio_id": otro_agente.unique_id,
            "terminos": terminos,
            "pasos_restantes": 10 # Duración estándar de 10 turnos
        }
        nuevo_tratado_otro = {
            "socio_id": self.unique_id,
            "terminos": terminos,
            "pasos_restantes": 10
        }

        self.tratados.append(nuevo_tratado_yo)
        
        # Validar lista del otro agente
        if not isinstance(otro_agente.tratados, list):
             otro_agente.tratados = []
        # Limpiar corruptos del otro agente también
        otro_agente.tratados = [t for t in otro_agente.tratados if isinstance(t, dict)]
        
        otro_agente.tratados.append(nuevo_tratado_otro)
        
        # Mantener lista de alianzas para compatibilidad visual (y reparar si hay datos corruptos)
        if not isinstance(self.alianzas, list): self.alianzas = []
        if not isinstance(otro_agente.alianzas, list): otro_agente.alianzas = []

        if otro_agente.unique_id not in self.alianzas: self.alianzas.append(otro_agente.unique_id)
        if self.unique_id not in otro_agente.alianzas: otro_agente.alianzas.append(self.unique_id)

        desc = terminos.get("descripcion", "Pacto formal")
        self.modelo.log(f"📜 [TRATADO] {self.unique_id} y {otro_agente.unique_id} han firmado: {desc}", categoria="social")
        
        # Registrar en memoria gráfica para visualización
        self.memoria.registrar_interaccion(otro_agente.unique_id, "alianza", 0.5, otro_agente.recursos, otro_agente.grupo_id)
        otro_agente.memoria.registrar_interaccion(self.unique_id, "alianza", 0.5, self.recursos, self.grupo_id)
        
        self.modelo.notificar_cambio_estado() # Actualizar alianzas en tiempo real
        return True

    @synchronized
    def comerciar(self, otro_agente, tipo="compra"):
        """Realiza una transacción económica entre agentes."""
        # Precio base influenciado por el mercado global
        precio_mercado = float(self.modelo.precio_recurso_actual)
        
        if tipo == "compra":
            # Yo compro recursos a otro_agente
            cantidad = 3 # Reducido de 5 a 3
            costo = cantidad * precio_mercado
            if self.dinero >= costo and otro_agente.recursos >= cantidad and (self.gasto_turno + costo) <= 30:
                self.dinero -= costo
                self.gasto_turno += costo
                self.recursos += cantidad
                otro_agente.dinero += costo
                otro_agente.recursos -= cantidad
                self.modelo.log(f"💰 [COMERCIO] Agente {self.unique_id} compró {cantidad} recursos a {otro_agente.unique_id} por {costo:.1f} MC.", categoria="social")
                self.modelo.notificar_cambio_estado()
                return True
        return False

    @synchronized
    def mejorar_seguridad(self):
        """Invierte dinero en mejorar el rango y la protección."""
        costo = 25.0 # Reducido de 50 a 25 para que sea viable con el límite de 30
        if self.dinero >= costo and (self.gasto_turno + costo) <= 30:
            self.dinero -= costo
            self.gasto_turno += costo
            self.rango += 0.2
            self.necesidades["seguridad"] = max(0, self.necesidades["seguridad"] - 5)
            self.modelo.log(f"🛡️ [SEGURIDAD] Agente {self.unique_id} invirtió en protección. Rango aumentado a {self.rango:.1f}.", categoria="state")
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
            self.inversiones.append({
                "monto": monto,
                "paso_final": self.modelo.paso_actual + 5,
                "interes": interes
            })
            self.modelo.log(f"📈 [INVERSIÓN] Agente {self.unique_id} invirtió {monto:.1f} MC en el mercado.", categoria="state")
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
                self.modelo.log(f"💰 [RETORNO] Inversión de {self.unique_id} finalizada: {ganancia:.1f} MC ({resultado}).", categoria="social")

        # El metabolismo consume menos recursos si hay alimento almacenado
        consumo = 0.5 + ((10 - self.necesidades["alimento"]) * 0.03)
        self.recursos -= consumo
        self.inventario["comida"] = max(0, int(self.recursos))
        
        # Necesidades disminuyen (10=perfecto, 0=emergencia)
        # EL costo del terreno afecta el consumo de descanso y alimento
        tile = self.modelo.mapa[self.x][self.y]
        energy_mod = tile.energy_cost
        
        self.necesidades["alimento"] = max(0, self.necesidades["alimento"] - (0.04 + energy_mod * 0.1))
        self.necesidades["social"] = max(0, self.necesidades["social"] - 0.03)
        self.necesidades["seguridad"] = max(0, self.necesidades["seguridad"] - 0.02)
        self.necesidades["descanso"] = max(0, self.necesidades["descanso"] - (0.05 + energy_mod))
        self.necesidades["entretenimiento"] = max(0, self.necesidades["entretenimiento"] - 0.03)
        
        # Riesgo de salud por terreno hostil (Desert, Mountain)
        if tile.health_risk > 0 and random.random() < 0.1:
            self.recibir_daño(tile.health_risk * 2, f"clima hostil en {tile.terrain_type}")
        
        # --- REGENERACIÓN PASIVA ---
        # Si el agente está bien alimentado y descansado (> 7), recupera salud
        if self.necesidades["alimento"] > 7.0 and self.necesidades["descanso"] > 7.0:
            self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 0.1)
            # Log sutil de bienestar solo de vez en cuando para no saturar
            if random.random() < 0.1:
                self.modelo.log(f"✨ [BIENESTAR] Agente {self.unique_id} se está recuperando gracias a su buen estado.", categoria="state")
        
        # --- PROCESAMIENTO DE TRATADOS FORMALES ---
        for tratado in list(self.tratados):
            if not isinstance(tratado, dict):
                # Si por error hay un string (ej. bug de carga), lo ignoramos
                continue

            aliado = next((a for a in self.modelo.agentes if a.unique_id == tratado.get("socio_id")), None)
            if not aliado: continue

            t = tratado["terminos"]
            # 1. Intercambio de Recursos por Dinero
            if t.get("tipo") == "intercambio":
                dar = t.get("da", {}) # {recurso: "medicina", cant: 1}
                recibe = t.get("recibe", {}) # {recurso: "dinero", cant: 10}

                # Ejecutar si ambos tienen lo necesario
                puedo_dar = False
                if dar.get("recurso") == "medicina" and self.inventario["medicina"] >= dar.get("cant", 0): puedo_dar = True
                elif dar.get("recurso") == "dinero" and self.dinero >= dar.get("cant", 0): puedo_dar = True
                elif dar.get("recurso") == "recursos" and self.recursos >= dar.get("cant", 0): puedo_dar = True

                if puedo_dar:
                    # Transferir lo que yo doy
                    if dar["recurso"] == "medicina": 
                        self.inventario["medicina"] -= dar["cant"]; aliado.inventario["medicina"] += dar["cant"]
                    elif dar["recurso"] == "dinero":
                        self.dinero -= dar["cant"]; aliado.dinero += dar["cant"]
                    elif dar["recurso"] == "recursos":
                        self.recursos -= dar["cant"]; aliado.recursos += dar["cant"]
                    
                    # Transferir lo que yo recibo (si el aliado puede)
                    # Nota: Simplificado para que el aliado siempre cumpla su parte si el otro empezó
                    if recibe["recurso"] == "dinero":
                        aliado.dinero -= recibe["cant"]; self.dinero += recibe["cant"]
                    elif recibe["recurso"] == "seguridad":
                        self.rango += recibe["cant"] # El aliado me brinda protección
                    
                    self.modelo.log(f"🤝 [EJECUCION TRATADO] Intercambio realizado entre {self.unique_id} y {aliado.unique_id}.", categoria="social")

            # Reducir duración
            tratado["pasos_restantes"] -= 1
            if tratado["pasos_restantes"] <= 0:
                self.tratados.remove(tratado)
                # También quitar del aliado
                aliado.tratados = [at for at in aliado.tratados if at["socio_id"] != self.unique_id]
            self.modelo.log(f"⌛ [SISTEMA] El tratado entre {self.unique_id} y {aliado.unique_id} ha expirado.", categoria="sistema")

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
            self.modelo.log(f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas a ({self.x}, {self.y}) para estar dentro del mapa.", categoria="sistema")

        # --- INSTINTO DE SUPERVIVENCIA AUTOMÁTICO ---
        tile = self.modelo.mapa[self.x][self.y]
        
        # 1. Alimentación automática si hay comida en el suelo y tiene hambre
        if tile.resource_node and tile.resource_node["type"] == "food" and self.necesidades["alimento"] < 6.0:
            comida_tomada = min(tile.resource_node["amount"], 2.0)
            tile.resource_node["amount"] -= comida_tomada
            self.necesidades["alimento"] = min(10, self.necesidades["alimento"] + (comida_tomada * 2))
            self.modelo.log(f"🍎 [INSTINTO] Agente {self.unique_id} consumió alimento del terreno automáticamente.", categoria="alimentos")
            if tile.resource_node["amount"] <= 0: tile.resource_node = None

        # 2. Uso de infraestructura (Hospitales y Centros de Recarga)
        for edif in tile.buildings:
            if edif["tipo"].lower() in ["hospital", "clinica"] and self.necesidades["salud"] < 9.0:
                self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 1.0)
                self.modelo.log(f"🏥 [SISTEMA] Agente {self.unique_id} está siendo atendido en el Hospital.", categoria="salud")
            
            if "recarga" in edif["tipo"].lower() or "eléctrica" in edif["tipo"].lower():
                self.necesidades["descanso"] = min(10.0, self.necesidades["descanso"] + 2.0)
                self.recursos += 1.0 # Carga de energía/recursos
                self.modelo.log(f"⚡ [SISTEMA] Agente {self.unique_id} recargando constantes en estación energética.", categoria="ambiente")

    @synchronized
    def recibir_daño(self, cantidad, motivo="desconocido"):
        """Reduce la salud del agente y verifica si muere."""
        self.necesidades["salud"] -= cantidad
        self.modelo.log(f"🩸 [DAÑO] Agente {self.unique_id} ha recibido {cantidad:.1f} de daño por {motivo}. Salud restante: {self.necesidades['salud']:.1f}", categoria="salud")
        if self.necesidades["salud"] <= 0:
            self.morir(motivo)

    def morir(self, motivo):
        """Finaliza la existencia del agente en la simulación."""
        if not self.esta_vivo: return
        
        self.esta_vivo = False
        self.modelo.log(f"🪦 [FUNERAL] El Agente {self.unique_id} ha MUERTO. Motivo: {motivo}.", categoria="sistema")
        
        # Registro histórico si era importante
        if self.rol in ["Líder", "Historiador", "Moderador"]:
            self.modelo.historia.agregar_hito({
                "turno": self.modelo.paso_actual,
                "descripcion": f"Luto nacional: El {self.rol} {self.unique_id} ha fallecido por {motivo}.",
                "tipo": "muerte"
            })
        
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
                self.modelo.db.execute("UPDATE agentes SET reputacion = %s WHERE id = %s", (0.0, self.unique_id))
            except: pass
            
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
            self.modelo.log(f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas en recolectar a ({self.x}, {self.y}).", categoria="sistema")
        
        tile = self.modelo.mapa[self.x][self.y]
        mult = getattr(tile, 'yield_mult', 1.0)
        
        # 1. Recolección de nodo específico
        if tile.resource_node and tile.resource_node["amount"] > 0:
            tipo = tile.resource_node["type"]
            
            # Bonos específicos por terreno
            nodo_bonus = 1.0
            if tipo == "wood" and tile.terrain_type == TerrainType.FOREST: nodo_bonus = 2.0
            if tipo == "stone" and tile.terrain_type == TerrainType.MOUNTAIN: nodo_bonus = 2.0
            if tipo == "food" and tile.terrain_type == TerrainType.GRASS: nodo_bonus = 1.5

            cantidad = min(tile.resource_node["amount"], int(random.randint(5, 15) * mult * nodo_bonus))
            tile.resource_node["amount"] -= cantidad
            
            if tipo == "food":
                self.recursos += cantidad
                self.inventario["comida"] = self.inventario.get("comida", 0) + cantidad
                self.modelo.log(f"  🍎 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de ALIMENTO en {tile.terrain_type}.", categoria="alimentos")
            elif tipo == "wood":
                self.recursos += cantidad * 0.5
                self.inventario["madera"] = self.inventario.get("madera", 0) + cantidad
                self.ganar_experiencia("ingenieria", 1)
                self.modelo.log(f"  🪵 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de MADERA en {tile.terrain_type}.", categoria="recursos")
            elif tipo == "stone":
                self.recursos += cantidad * 0.5
                self.inventario["piedra"] = self.inventario.get("piedra", 0) + cantidad
                self.ganar_experiencia("ingenieria", 1)
                self.modelo.log(f"  🪨 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de PIEDRA en {tile.terrain_type}.", categoria="recursos")
                
            if tile.resource_node["amount"] <= 0:
                tile.resource_node = None
                self.modelo.log(f"  ⚠️ [RECOLECCION] El nodo de recursos en ({self.x}, {self.y}) se ha AGOTADO.", categoria="ambiente")
            return

        # 2. Recolección genérica (baja eficiencia según terreno)
        r = random.random()
        
        if tile.terrain_type == TerrainType.FOREST:
            if r < 0.6:
                cant = random.uniform(3, 10) * mult
                self.inventario["madera"] = self.inventario.get("madera", 0) + int(cant)
                self.recursos += cant * 0.5
                self.modelo.log(f"  🌲 Agente {self.unique_id} recolectó {int(cant)} de MADERA en el bosque.", categoria="recursos")
            else:
                self.inventario["medicina"] += 1
                self.ganar_experiencia("medicina", 1)
                self.modelo.log(f"  🌿 Agente {self.unique_id} encontró HIERBAS MEDICINALES.", categoria="recursos")
        
        elif tile.terrain_type == TerrainType.MOUNTAIN:
            if r < 0.7:
                cant = random.uniform(2, 6) * mult
                self.inventario["piedra"] = self.inventario.get("piedra", 0) + int(cant)
                self.recursos += cant * 0.3
                self.modelo.log(f"  🪨 Agente {self.unique_id} picó {int(cant)} de PIEDRA en la montaña.", categoria="recursos")
            else:
                self.inventario["hierro"] = self.inventario.get("hierro", 0) + 1
                self.modelo.log(f"  ⛏️ Agente {self.unique_id} encontró una veta de HIERRO.", categoria="recursos")
                
        elif tile.terrain_type == TerrainType.WATER:
            cant = random.uniform(1, 4) * mult
            self.inventario["pescado"] = self.inventario.get("pescado", 0) + int(cant)
            self.recursos += cant * 1.5 # El pescado da mucha energía/recurso
            self.modelo.log(f"  🐟 Agente {self.unique_id} pescó {int(cant)} unidades.", categoria="alimentos")
            
        else: # Grassland o Desert
            cant = random.uniform(2, 8) * mult
            self.recursos += cant # Alimento base
            self.inventario["comida"] = self.inventario.get("comida", 0) + int(cant)
            self.modelo.log(f"  🌱 Agente {self.unique_id} forrajeó {int(cant)} de alimento.", categoria="alimentos")

        # Notificar cambio inmediato para visualización real-time en paneles
        self.modelo.notificar_cambio_estado()

    @synchronized
    def establecer_objetivo_movimiento(self, x, y):
        """Fija un destino para el movimiento del agente."""
        self.objetivo_movimiento = (x, y)
        self.modelo.log(f"🗺️ [NAVEGACION] Agente {self.unique_id} ha fijado un nuevo rumbo a ({x}, {y}).", categoria="movimiento")

    @synchronized
    def ganar_experiencia(self, area, puntos=1):
        """Aumenta la experiencia en un área y verifica si puede graduarse."""
        if area in self.experiencia:
            self.experiencia[area] += puntos
            # Si llega a 5 de experiencia en un área y no tiene esa profesión, avisar
            if self.experiencia[area] == 5 and self.profesion is None:
                self.modelo.log(f"🎓 [HITOS] Agente {self.unique_id} ha ganado suficiente experiencia en {area} para profesionalizarse.", categoria="sistema")

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
            self.modelo.log(f"⚠️ [SISTEMA] Coordenadas del Agente {self.unique_id} ajustadas en graduarse a ({self.x}, {self.y}).", categoria="sistema")

        # VERIFICACIÓN DE UBICACIÓN: Debe haber una Universidad en el tile actual
        tile = self.modelo.mapa[self.x][self.y]
        tiene_universidad = any(b["tipo"] == "Universidad" for b in tile.buildings)
        
        if not tiene_universidad:
            return False, "Debes estar en una Universidad para graduarte y obtener tu título oficial. 🏛️"

        costos = {
            "Médico": 150,
            "Comerciante": 200,
            "Guarda": 100,
            "Explorador": 120
        }
        
        requisitos = {
            "Médico": self.experiencia["medicina"] >= 5 and self.personalidad["amabilidad"] > 0.5,
            "Comerciante": self.experiencia["comercio"] >= 5,
            "Guarda": self.experiencia["combate"] >= 3 and self.personalidad["hostilidad"] < 0.6,
            "Explorador": self.experiencia["exploracion"] >= 5
        }

        if profesion_deseada not in costos:
            return False, "Profesión no válida."

        if not requisitos[profesion_deseada]:
            return False, f"No cumples los requisitos de experiencia o personalidad para ser {profesion_deseada}."

        if self.dinero < costos[profesion_deseada]:
            return False, f"Necesitas {costos[profesion_deseada]} MC para la licencia de {profesion_deseada}."

        # Éxito
        self.dinero -= costos[profesion_deseada]
        self.profesion = profesion_deseada
        self.hitos.append(f"Graduado como {profesion_deseada}")
        self.modelo.log(f"✨ [PROFESION] ¡El Agente {self.unique_id} se ha graduado como {profesion_deseada}! 🎓", categoria="consenso")
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
            universo_votantes = [a for a in self.modelo.agentes if a.grupo_id == self.grupo_id and a.esta_vivo]
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
            "paso_creacion": self.modelo.paso_actual
        }
        
        if "propuestas" not in self.modelo.facciones_leyes:
            self.modelo.facciones_leyes["propuestas"] = []
            
        self.modelo.facciones_leyes["propuestas"].append(propuesta)
        
        target_str = f"en la Facción {self.grupo_id}" if alcance == "local" else "a nivel GLOBAL"
        self.modelo.log(f"📜 [POLITICA] Agente {self.unique_id} ha PROPUESTO formalmente la ley: '{titulo}' {target_str}.", categoria="consenso")
        self.modelo.notificar_cambio_estado()
        
        return True, ley_id

    @synchronized
    def votar_ley(self, ley_id, a_favor=True):
        """Vota una propuesta de ley existente."""
        propuestas = self.modelo.facciones_leyes.get("propuestas", [])
        for p in propuestas:
            if (p["id"] == ley_id or str(p.get("titulo", "")).lower() == str(ley_id).lower()) and self.unique_id not in p["votantes"]:
                if a_favor: p["votos_si"] += 1
                else: p["votos_no"] += 1
                p["votantes"].append(self.unique_id)
                
                self.modelo.log(f"🗳️ Agente {self.unique_id} votó {'A FAVOR' if a_favor else 'EN CONTRA'} de la ley '{p['titulo']}'.", categoria="consenso")
                self.modelo.notificar_cambio_estado() # Notificar cambio para WebSocket
                return True
        return False

    def sancionar(self, motivo, gravedad=0.1):
        """Reduce la reputación del agente por acciones indebidas."""
        self.reputacion = max(0.0, self.reputacion - gravedad)
        self.historial_etico.append(f"Sanción: {motivo} (-{gravedad})")
        self.modelo.log(f"⚖️ [JUSTICIA] Agente {self.unique_id} sancionado por: {motivo}. Reputación: {self.reputacion:.2f}", categoria="sistema")

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
            categoria="general"
        )
        
        # Limpiar hitos pendientes ya narrados
        self.modelo.historia.limpiar_hitos()
        
        self.modelo.log(f"📚 [CRONICA] ¡Nueva entrada en los anales de la historia!: '{titulo}'", categoria="consenso")
        self.modelo.notificar_cambio_estado() # Para actualizar frontend
        return True, "Crónica escrita."

    def step(self):
        """Acciones que realiza el agente en un turno."""
        if not self.esta_vivo:
            return
            
        # Si el agente está siendo poseído por el Arquitecto, no actúa por su cuenta.
        if self.unique_id == getattr(self.modelo, 'agente_poseido_id', None):
            self.pensamiento_actual = "Manifestación Divina: El Arquitecto habita este ser."
            return

        self.gasto_turno = 0.0 # Resetear gasto al inicio del turno
        
        # 1. Identificar posibles objetivos (Prioridad: Respondedor > Vecinos > Azar)
        otros = [a for a in self.modelo.agentes if a.unique_id != self.unique_id]
        objetivo_cercano = None
        
        # Prioridad 1: Quien me habló recientemente
        if self.ultimo_mensaje_recibido:
            emisor_id = self.ultimo_mensaje_recibido['emisor']
            objetivo_cercano = next((a for a in otros if a.unique_id == emisor_id), None)
            
        # Prioridad 2: Vecinos en mi memoria (amigos/conocidos)
        if not objetivo_cercano:
            vecinos_ids = list(self.memoria.grafo.neighbors(self.unique_id))
            if vecinos_ids:
                vecino_id = random.choice(vecinos_ids)
                objetivo_cercano = next((a for a in otros if a.unique_id == vecino_id), None)
        
        # Prioridad 3: Azar
        if not objetivo_cercano and otros:
            objetivo_cercano = random.choice(otros)
        
        # 2. Pensar qué hacer
        if hasattr(self, 'decision_cacheada') and self.decision_cacheada:
            resultado_pensar = self.decision_cacheada
        else:
            resultado_pensar = self.cerebro.pensar(self, objetivo_id=objetivo_cercano.unique_id if objetivo_cercano else None)
        
        # Desempaquetar result (puede tener 8 o 9 valores según la versión)
        if len(resultado_pensar) == 9:
            decision, mensaje, pensamiento, es_privado, es_grupal, es_global, nuevos_planes, accion_data, destinatario_llm = resultado_pensar
        else:
            decision, mensaje, pensamiento, es_privado, es_grupal, es_global, nuevos_planes, accion_data = resultado_pensar
            destinatario_llm = None
        
        # Obtener el nombre limpio de la acción de forma robusta
        nombre_accion = "HABLAR"
        if isinstance(accion_data, dict) and accion_data.get("nombre"):
            nombre_accion = str(accion_data["nombre"]).upper()
        elif decision:
            nombre_accion = str(decision).split(":")[0].upper()

        if nuevos_planes:
            # Primero, actualizamos los planes del agente actual
            self.planes = nuevos_planes
            
            # Registrar la acción en el historial de la memoria (para evitar repeticiones en el prompt)
            self.memoria.registrar_accion(nombre_accion)
            
            # Ahora, nos aseguramos de que todos los participantes tengan el plan
            for plan in nuevos_planes:
                # Comprobamos si el plan tiene participantes
                if 'participantes' in plan and isinstance(plan.get('participantes'), list):
                    for participante_id in plan['participantes']:
                        # Obtenemos la instancia real del agente participante
                        agente_participante = self.modelo.get_agent_by_id(participante_id)
                        if agente_participante:
                            # Evitar duplicados: añadir solo si el plan no existe ya
                            if not any(p.get('id') == plan.get('id') for p in agente_participante.planes):
                                agente_participante.planes.append(plan)
                                self.modelo.log(f"📋 [PLAN COMPARTIDO] El plan '{plan.get('id')}' ha sido compartido con el Agente {participante_id}.", categoria="sistema")
        
        # Actualizar pensamiento actual guardado en el agente
        if pensamiento:
            self.pensamiento_actual = pensamiento

        # Determinar destinatario del mensaje:
        # 1. Prioridad: Si el LLM especificó un destinatario explícito (mensaje individual)
        # 2. Si la acción implica una interacción (SOCIALIZAR, ALIANZA, etc.)
        # 3. Messages grupales van al grupo
        if destinatario_llm:
            # El LLM quiso enviar un mensaje privado a un agente específico
            dest_agente = self.modelo.get_agent_by_id(destinatario_llm)
            destinatario_id = destinatario_llm if dest_agente else (objetivo_cercano.unique_id if objetivo_cercano else None)
            es_privado = True
        else:
            destinatario_id = objetivo_cercano.unique_id if (objetivo_cercano and (es_privado or nombre_accion in ["SOCIALIZAR", "COMPETIR", "COMERCIAR", "ALIANZA", "ATACAR", "INTERACCIONAR"])) else None
        
        if es_grupal:
            destinatario_id = f"GRUPO:{self.grupo_id}"
        
        # 3. Validar acción antes de ejecutar
        es_valida, error_msg = validar_accion(self, nombre_accion, accion_data, self.modelo)
        if not es_valida:
            self.modelo.log(f"⚠️ [VALIDATOR] Acción '{nombre_accion}' rechazada para {self.unique_id}: {error_msg}. Aplicando fallback.", categoria="sistema")
            accion_correcta = obtener_accion_fallback(self, accion_data, self.modelo)
            nombre_accion = accion_correcta["nombre"]
            accion_data = accion_correcta
            if pensamiento:
                pensamiento += f" [CORRECTION: {error_msg}]"

        # 4. Decir el mensaje (con el flag de global si aplica)
        self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal, global_broadcast=es_global)

        # 5. Actuar según pensamiento o acción corregida
        if nombre_accion == "HABLAR":
            # the action of speaking already handled by self.decir()
            pass

        elif nombre_accion == "INTERACCIONAR":
            if objetivo_cercano:
                tipo_interaccion = "social" # Default
                msg_lower = mensaje.lower()
                if "competir" in msg_lower: tipo_interaccion = "COMPETIR"
                elif "atacar" in msg_lower: tipo_interaccion = "ATACAR"
                elif "comerciar" in msg_lower: tipo_interaccion = "COMERCIAR"
                elif "alianza" in msg_lower or nombre_accion == "ALIANZA": tipo_interaccion = "ALIANZA"
                self.interactuar(objetivo_cercano, tipo_interaccion, mensaje_enviado=mensaje)

        elif nombre_accion == "RECOLECTAR":
            self.recolectar()

        elif nombre_accion == "SOCIALIZAR":
            if objetivo_cercano:
                if self.rol == "Líder" and random.random() > 0.5:
                    self.invitar_agente(objetivo_cercano)
                self.interactuar(objetivo_cercano, "social", mensaje_enviado=mensaje)
            else:
                self.decir("No hay nadie cerca para socializar.", pensamiento=pensamiento)

        elif nombre_accion == "COMPETIR":
            if objetivo_cercano:
                self.interactuar(objetivo_cercano, "COMPETIR", mensaje_enviado=mensaje)
            else:
                self.decir("No hay nadie cerca con quien competir.", pensamiento=pensamiento)

        elif nombre_accion in ["FUNDAR_GRUPO", "FUNDAR_FACCION", "FUNDAR_FACCIÓN", "FACCION_CREAR", "CREAR_FACCIÓN"]:
            args = accion_data.get("argumentos", {})
            nombre_propuesto = args.get("nombre") or args.get("nombre_faccion")
            idea_central = args.get("idea") or args.get("descripcion") or args.get("ideologia") or args.get("objetivo_faccion") or "Prosperidad y ayuda mutua."
            
            # Fallback if arguments are missing or unstructured
            if not nombre_propuesto:
                import re
                match = re.search(r'["«]([^"»]+)["»]|Fundamos (?:la |el |los |las )?([^!.]+)', mensaje)
                nombre_propuesto = (match.group(1) or match.group(2)) if match else f"Grupo de {self.unique_id}"

            # Validar que no sea un nombre vacío o demasiado genérico
            if not nombre_propuesto or len(nombre_propuesto) < 3:
                nombre_propuesto = f"Grupo de {self.unique_id}"

            # Asegurar unicidad: Si el nombre ya existe, la fundación falla
            nombres_en_uso = [c.nombre for c in self.modelo.civilizaciones.values()]
            if nombre_propuesto in nombres_en_uso:
                self.decir(f"⚠️ El nombre de grupo '{nombre_propuesto}' ya está en uso.", global_broadcast=False)
            else:
                nuevo_id = self.fundar_grupo(nombre_propuesto, idea_central)
                if nuevo_id:
                    self.rol = "Líder"
                    self.decir(f"¡He fundado el grupo '{nombre_propuesto}'! Idea: {idea_central}.", global_broadcast=True)
                else:
                    self.decir(f"Intenté fundar el grupo '{nombre_propuesto}', pero las leyes del mundo no permiten más fundaciones en este momento.", pensamiento="Límite de grupos alcanzado.")

        elif nombre_accion == "FUNDAR_INSTITUCION":
            import re
            match = re.search(r'["«]([^"»]+)["»]|Fundamos (?:la |el |los |las )?([^!.]+)', mensaje)
            nombre_inst = match.group(1) or match.group(2) if match else f"Institucion de {self.unique_id}"
            
            # Determinar tipo según el mensaje o pensamiento
            tipo = "CIENTIFICA"
            msg_lower = mensaje.lower()
            if "escuela" in msg_lower or "educación" in msg_lower: tipo = "EDUCATIVA"
            elif "banco" in msg_lower or "finanzas" in msg_lower: tipo = "FINANCIERA"
            elif "hospital" in msg_lower or "salud" in msg_lower: tipo = "SANITARIA"
            elif "templo" in msg_lower or "fe" in msg_lower: tipo = "RELIGIOSA"
            
            exito, res = self.modelo.fundar_institucion(self.unique_id, nombre_inst, tipo)
            if exito:
                self.decir(f"He fundado la institución '{nombre_inst}' de tipo {tipo}. Buscamos miembros comprometidos.", global_broadcast=True)
            else:
                self.decir(f"No he podido fundar la institución: {res}", pensamiento=pensamiento)

        elif nombre_accion == "UNIRSE_INSTITUCION":
            # Buscar ID de institución en el mensaje o pensamiento
            import re
            match = re.search(r'INST-\d+-\d+', mensaje + " " + pensamiento)
            if match:
                inst_id = match.group(0)
                exito, res = self.modelo.unirse_institucion(self.unique_id, inst_id)
                if exito:
                    self.decir(f"Es un honor unirme a la institución {inst_id}.", pensamiento=pensamiento)
                else:
                    self.decir(f"No pude unirme: {res}", pensamiento=pensamiento)
            else:
                self.decir("¿A qué institución debería unirme?", pensamiento=pensamiento)

        elif nombre_accion == "INVITAR_A_GRUPO":
            # Intentar obtener el ID del invitado de los argumentos
            invitado_id = accion_data.get('argumentos', {}).get('agente_id')
            invitado = self.modelo.get_agent_by_id(invitado_id) if invitado_id else objetivo_cercano
            
            if invitado:
                self.invitar_agente(invitado)
            else:
                self.decir("No hay nadie cerca a quien invitar o no encontré al agente solicitado.", pensamiento=pensamiento)

        elif nombre_accion in ["UNIRSE_A_GRUPO", "UNIRSE_FACCION", "JOIN_FACTION"]:
            # Intentar obtener el ID de la facción de los argumentos
            args = accion_data.get('argumentos', {})
            faccion_id = args.get('grupo_id') or args.get('faccion_id')
            
            # Si no hay ID, buscar si el objetivo_cercano ya pertenece a una
            if not faccion_id and objetivo_cercano and objetivo_cercano.grupo_id:
                faccion_id = objetivo_cercano.grupo_id
                
            if faccion_id:
                # Verificar si es una civilización o grupo dinámico
                if faccion_id in self.modelo.civilizaciones:
                    self.grupo_id = faccion_id
                    self.civilizacion_id = faccion_id
                    self.rol = "Miembro"
                    nombre_f = self.modelo.civilizaciones[faccion_id].nombre
                    self.modelo.log(f"🤝 [UNION] Agente {self.unique_id} se ha unido formalmente a {nombre_f}.", categoria="social")
                    self.decir(f"¡Es un orgullo unirme a {nombre_f}! Trabajaré por el bien de la facción.")
                    self.modelo.notificar_cambio_estado()
                elif faccion_id in self.modelo.grupos_dinamicos:
                    self.grupo_id = faccion_id
                    self.civilizacion_id = faccion_id
                    self.rol = "Miembro"
                    nombre_f = self.modelo.grupos_dinamicos[faccion_id].nombre
                    self.modelo.log(f"🤝 [UNION] Agente {self.unique_id} se ha unido formalmente a {nombre_f}.", categoria="social")
                    self.decir(f"¡Es un orgullo unirme a {nombre_f}! Trabajaré por el bien de la facción.")
                    self.modelo.notificar_cambio_estado()
                else:
                    self.decir(f"La facción {faccion_id} parece no existir o es inaccesible.", pensamiento=pensamiento)
            else:
                self.decir("No sé a qué facción unirme.", pensamiento=pensamiento)

        elif nombre_accion == "COMERCIAR":
            args = accion_data.get('argumentos', {})
            obj_id = args.get('objetivo_id') or args.get('agente_id')
            objetivo_comercio = self.modelo.get_agent_by_id(obj_id) if obj_id else objetivo_cercano
            if objetivo_comercio:
                exito = self.comerciar(objetivo_comercio, tipo="compra")
                if exito:
                    self.ganar_experiencia("comercio", 1)
                    self.decir(f"✅ Compré {3} recursos a {objetivo_comercio.unique_id} por el precio del mercado.", pensamiento=pensamiento, privado_para=objetivo_comercio.unique_id)
                else:
                    self.decir(f"No se pudo concretar el comercio con {objetivo_comercio.unique_id} (dinero o recursos insuficientes).", pensamiento=pensamiento, privado_para=objetivo_comercio.unique_id)
            else:
                self.decir("No encontré un socio comercial disponible.", pensamiento=pensamiento)

        elif nombre_accion == "MEJORAR_SEGURIDAD":
            exito = self.mejorar_seguridad()
            if exito:
                self.decir("🛡️ He invertido en mi seguridad personal. Me siento más protegido.", pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("Necesito más MundoCoins para mejorar mi protección.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif nombre_accion == "BUSCAR_INFO":
            # Formato esperado: BUSCAR_INFO:tema
            args = accion_data.get('argumentos', {})
            tema_solicitado = args.get('tema')
            if not tema_solicitado:
                partes = decision.split(":") if decision else []
                tema_solicitado = partes[1].lower().strip() if len(partes) > 1 else None
            
            temas_validos = ["clima", "noticias", "mercado", "medicina", "agricultura", "ingenieria", "comercio", "combate"]
            tema = tema_solicitado if tema_solicitado in temas_validos else random.choice(["clima", "noticias", "mercado"])
            
            info = f"Dato sobre {tema} en el paso {self.modelo.paso_actual}"
            self.conocimientos[tema] = info
            
            # Si el tema es una habilidad, dar XP en esa habilidad, sino en exploracion
            habilidades = ["medicina", "agricultura", "ingenieria", "comercio", "combate", "exploracion"]
            area_xp = tema if tema in habilidades else "exploracion"
            
            self.ganar_experiencia(area_xp, 1)
            if area_xp != "exploracion":
                self.modelo.log(f"  📖 [ESTUDIO] Agente {self.unique_id} estudió sobre {area_xp.upper()} y ganó experiencia.", categoria="sistema")
            else:
                self.modelo.log(f"  🔍 [INVESTIGACION] Agente {self.unique_id} obtuvo información sobre {tema}.", categoria="sistema")

        elif nombre_accion == "COMPARTIR_INFO":
            if objetivo_cercano and self.conocimientos:
                tema = random.choice(list(self.conocimientos.keys()))
                info = self.conocimientos[tema]
                # El otro agente aprende
                objetivo_cercano.conocimientos[tema] = info

        elif nombre_accion == "PLANIFICAR":
            if objetivo_cercano:
                plan = {"con_quien": self.unique_id, "accion": "COOPERAR", "paso": self.modelo.paso_actual + 2}
                self.planes.append(plan)
                objetivo_cercano.planes.append(plan)

        elif nombre_accion == "DEBATIR":
            if objetivo_cercano:
                # El debate aumenta la afinidad o competitividad
                self.interactuar(objetivo_cercano, "social", mensaje_enviado=mensaje)

        elif nombre_accion == "INVERTIR":
            monto = min(self.dinero * 0.2, 30) # Invierte el 20% de su dinero, máximo 30 MC
            exito = self.invertir(monto)

        elif nombre_accion == "FORMAR_ALIANZA" or nombre_accion == "ALIANZA":
            args = accion_data.get('argumentos', {})
            obj_id = args.get('interlocutor_id') or args.get('objetivo_id') or args.get('agente_id')
            objetivo_alianza = self.modelo.get_agent_by_id(obj_id) if obj_id else objetivo_cercano
            if objetivo_alianza:
                # ... términos de alianza según el mensaje ...
                terminos = None
                msg_lower = mensaje.lower()
                if "medicina" in msg_lower and "dinero" in msg_lower:
                    terminos = {"tipo": "intercambio", "da": {"recurso": "medicina", "cant": 1}, "recibe": {"recurso": "dinero", "cant": 15}}
                elif "seguridad" in msg_lower or "protección" in msg_lower:
                    terminos = {"tipo": "intercambio", "da": {"recurso": "recursos", "cant": 10}, "recibe": {"recurso": "seguridad", "cant": 0.1}}
                self.formar_alianza(objetivo_alianza, terminos=terminos)

        elif nombre_accion == "ATACAR":
            args = accion_data.get('argumentos', {})
            obj_id = args.get('objetivo_id') or args.get('agente_id')
            objetivo_ataque = self.modelo.get_agent_by_id(obj_id) if obj_id else objetivo_cercano
            if objetivo_ataque and objetivo_ataque.unique_id != self.unique_id:
                self.interactuar(objetivo_ataque, "ATACAR", mensaje_enviado=mensaje)
            else:
                self.decir("¡Estoy buscando a alguien a quien atacar!", pensamiento=pensamiento)

        elif nombre_accion == "DECLARAR_GUERRA":
            args = accion_data.get('argumentos', {})
            obj_id = args.get('objetivo_id') or args.get('agente_id')
            objetivo_guerra = self.modelo.get_agent_by_id(obj_id) if obj_id else objetivo_cercano
            if objetivo_guerra and objetivo_guerra.grupo_id:
                self.interactuar(objetivo_guerra, "DECLARAR_GUERRA", mensaje_enviado=mensaje)
            else:
                self.decir("Necesito un representante de otra facción para declarar la guerra formalmente.", pensamiento=pensamiento)

        elif nombre_accion == "NEGOCIAR_PAZ":
            args = accion_data.get('argumentos', {})
            obj_id = args.get('objetivo_id') or args.get('agente_id')
            objetivo_paz = self.modelo.get_agent_by_id(obj_id) if obj_id else objetivo_cercano
            if objetivo_paz and objetivo_paz.grupo_id:
                self.interactuar(objetivo_paz, "NEGOCIAR_PAZ", mensaje_enviado=mensaje)
            else:
                self.decir("Busco un emisario para proponer un cese al fuego.", pensamiento=pensamiento)


        elif nombre_accion == "DESCANSAR":
            self.necesidades["descanso"] = min(10.0, self.necesidades["descanso"] + 4.0)
            self.necesidades["salud"] = min(10, self.necesidades["salud"] + 1.0)
            self.modelo.log(f"  💤 [ACCION] Agente {self.unique_id} descansa profundamente para recuperar energías.", categoria="state")
            self.modelo.notificar_cambio_estado()

        elif nombre_accion == "CURARSE":
            if self.inventario["medicina"] > 0:
                self.inventario["medicina"] -= 1
                self.necesidades["salud"] = min(10, self.necesidades["salud"] + 6)
                self.ganar_experiencia("medicina", 1)
                self.modelo.log(f"  🏥 [ACCION] Agente {self.unique_id} usó medicina avanzada para curarse.", categoria="state")
            else:
                self.decir("¡Necesito medicina! Debo ir al Hospital a comprar suministros.", pensamiento=pensamiento)

        elif nombre_accion == "COMPRAR_MEDICINA":
            # Verificar si está en un hospital o farmacia
            tile = self.modelo.mapa[self.x][self.y]
            en_establecimiento = any(b["tipo"].lower() in ["hospital", "clinica", "farmacia"] for b in tile.buildings)
            
            if en_establecimiento:
                costo = 10.0
                if self.dinero >= costo:
                    self.dinero -= costo
                    self.inventario["medicina"] += 1
                    self.ganar_experiencia("medicina", 1) # Ganar XP por adquirir suministros médicos
                    self.modelo.log(f"  💊 [COMPRA] Agente {self.unique_id} compró un kit de medicina por {costo} MC.", categoria="comercio")
                else:
                    self.decir(f"No tengo suficiente dinero ({self.dinero} MC) para comprar medicina. Cuesta {costo} MC.", pensamiento=pensamiento)
            else:
                self.decir("Aquí no venden medicina. Necesito encontrar un Hospital o Farmacia.", pensamiento=pensamiento)

        elif nombre_accion == "DIVERTIRSE":
            if self.inventario["ocio"] > 0:
                self.inventario["ocio"] -= 1
                self.necesidades["entretenimiento"] = max(0, self.necesidades["entretenimiento"] - 8)
                self.modelo.log(f"  🎮 [ACCION] Agente {self.unique_id} usó objetos de ocio. ¡Se siente genial!", categoria="state")
            else:
                self.necesidades["entretenimiento"] = max(0, self.necesidades["entretenimiento"] - 4) # Ocio básico sin objetos
                self.modelo.log(f"  🎭 [ACCION] Agente {self.unique_id} buscó entretenimiento básico.", categoria="state")

        elif nombre_accion == "MOVER":
            # Intentar extraer destino de los argumentos del diccionario de la acción
            import re
            args = accion_data.get('argumentos', {})
            destino = args.get('direccion') or args.get('destino')
            
            if destino:
                if isinstance(destino, str):
                    # Buscar coordenadas (x, y)
                    coords = re.findall(r'\d+', destino)
                    if len(coords) >= 2:
                        self.establecer_objetivo_movimiento(int(coords[0]), int(coords[1]))
                    else:
                        # Movimiento relativo N, S, E, O (reducido para no saltar demasiado)
                        d = destino.upper()
                        if 'N' in d: self.establecer_objetivo_movimiento(self.x, self.y - 3)
                        elif 'S' in d: self.establecer_objetivo_movimiento(self.x, self.y + 3)
                        elif 'E' in d: self.establecer_objetivo_movimiento(self.x + 3, self.y)
                        elif 'O' in d: self.establecer_objetivo_movimiento(self.x - 3, self.y)
                elif isinstance(destino, (list, tuple)) and len(destino) >= 2:
                    self.establecer_objetivo_movimiento(int(destino[0]), int(destino[1]))

        elif nombre_accion.startswith("ANUNCIAR"):
            # Extraer mensaje del anuncio
            partes = decision.split(":") if decision else []
            txt_anuncio = ":".join(partes[1:]).strip() if len(partes) > 1 else mensaje
            self.decir(f"📢 [RADIO GLOBAL] {txt_anuncio}", pensamiento=pensamiento, global_broadcast=True)

        elif nombre_accion == "CONSTRUIR":
            args = accion_data.get('argumentos', {})
            tipo_edif = args.get('tipo') or (decision.split(":")[1] if decision and ":" in decision else "CASA")
            res, msg = self.modelo.construir_edificio(self, tipo_edif)
            if not res:
                self.decir(f"❌ No he podido construir el {tipo_edif}: {msg}", pensamiento=pensamiento)

        elif nombre_accion == "GRADUARSE":
            if self.modelo.ubicacion_universidad:
                uni_x, uni_y = self.modelo.ubicacion_universidad
                # Si ya está en la universidad, intentar graduarse
                if self.x == uni_x and self.y == uni_y:
                    # El mensaje del LLM debería contener la profesión deseada o la deducimos de su experiencia
                    profesion_objetivo = None
                    # Deducir la profesión con mayor experiencia
                    if self.experiencia:
                        campo_max_xp = max(self.experiencia, key=self.experiencia.get)
                        if self.experiencia[campo_max_xp] >= 15: # Umbral para graduarse
                            profesiones_map = {
                                "medicina": "Médico", "comercio": "Comerciante", "combate": "Guarda",
                                "exploracion": "Explorador", "ingenieria": "Ingeniero"
                            }
                            if campo_max_xp in profesiones_map:
                                profesion_objetivo = profesiones_map[campo_max_xp]

                    if profesion_objetivo:
                        self.graduarse(profesion_objetivo)
                    else:
                        self.decir("Estoy en la Universidad, pero aún no estoy listo para especializarme.", pensamiento=pensamiento)
                else:
                    # No está en la universidad, moverse hacia ella
                    self.establecer_objetivo_movimiento(uni_x, uni_y)
                    self.decir(f"🎓 Me dirijo a la Universidad en ({uni_x}, {uni_y}) para profesionalizarme.", pensamiento=pensamiento)
            else:
                self.decir("Quiero graduarme, pero no sé dónde está la Universidad.", pensamiento=pensamiento)

        elif nombre_accion == "PROPONER_LEY":
            # ¡CRÍTICO! Las leyes son públicas.
            args = accion_data.get('argumentos', {})
            partes = decision.split(":") if decision else []
            
            alcance = args.get('alcance') or (partes[1].lower() if len(partes) > 1 else "local")
            if alcance not in ["local", "global"]: alcance = "local"
            
            titulo_ley = args.get('titulo') or (partes[2].strip() if len(partes) > 2 else "Ley sin título")
            contenido_ley = args.get('contenido') or (":".join(partes[3:]).strip() if len(partes) > 3 else mensaje)
            
            exito, res = self.proponer_ley(titulo_ley, contenido_ley, alcance=alcance)
            if exito:
                self.decir(f"📜 [PROPUESTA PÚBLICA] He propuesto la ley: '{titulo_ley}' para el {alcance.upper()}.", pensamiento=pensamiento, global_broadcast=(alcance=="global"), para_grupo=(alcance=="local"))
                self.modelo.notificar_cambio_estado()
            else:
                self.decir(f"No pude proponer la ley: {res}", pensamiento=pensamiento)

        elif nombre_accion == "DEBATIR" or nombre_accion == "DAR_OPINION":
            # Los debates son SIEMPRE públicos (Global o Grupo según contexto)
            self.decir(mensaje, pensamiento=pensamiento, global_broadcast=True)

        elif nombre_accion == "INICIAR_ASAMBLEA":
            # Formato: INICIAR_ASAMBLEA:tema
            args = accion_data.get('argumentos', {})
            partes = decision.split(":", 1) if decision else []
            tema = args.get('tema') or (partes[1].strip() if len(partes) > 1 else "Debate General")
            
            exito, res = self.modelo.crear_asamblea(self.unique_id, tema)
            if exito:
                self.decir(f"🏛️ ¡He iniciado una asamblea global sobre '{tema}'! ID: {res}", pensamiento=pensamiento, para_grupo=True)
            else:
                self.decir(f"⚠️ No pude iniciar la asamblea sobre '{tema}': {res}", pensamiento=pensamiento, privado_para=destinatario_id)

        elif nombre_accion == "VOTAR_ASAMBLEA":
            # Formato: VOTAR_ASAMBLEA:id:voto
            args = accion_data.get('argumentos', {})
            partes = decision.split(":") if decision else []
            asamblea_id = args.get('id') or (partes[1].strip() if len(partes) > 1 else None)
            voto = args.get('voto') or (partes[2].strip() if len(partes) > 2 else "A FAVOR")
            
            # Buscar la asamblea - intentar coincidencia exacta
            asamblea_encontrada = None
            for a in self.modelo.asambleas_globales:
                if a["id"] == asamblea_id:
                    if a["estado"] == "VOTACION":
                        asamblea_encontrada = a
                        break
            
            if not asamblea_encontrada:
                # Buscar cualquier asamblea en votación
                votacion_activa = [a for a in self.modelo.asambleas_globales if a["estado"] == "VOTACION"]
                if votacion_activa:
                    asamblea_encontrada = votacion_activa[0]
                    self.modelo.log(f"⚠️ [VOTACION] No se encontró {asamblea_id}, votando en {asamblea_encontrada['id']}", categoria="sistema")
            
            if asamblea_encontrada:
                exito, res = self.modelo.registrar_voto(self.unique_id, asamblea_encontrada["id"], voto)
                if exito:
                    self.decir(f"🗳️ He votado '{voto}' en la asamblea {asamblea_encontrada['id']}.", pensamiento=pensamiento, para_grupo=True)
                else:
                    self.decir(f"⚠️ No pude votar en la asamblea {asamblea_encontrada['id']}: {res}", pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("No hay ninguna asamblea activa para recibir mi voto.", pensamiento=pensamiento)

        elif nombre_accion == "ESCRIBIR_CRONICA":
            args = accion_data.get('argumentos', {})
            titulo = args.get('titulo') or "Crónica de los Anales"
            contenido = args.get('contenido') or mensaje
            exito, res = self.escribir_cronica(titulo, contenido)
            if not exito:
                self.decir(f"❌ No pude escribir la crónica: {res}", pensamiento=pensamiento)

        elif nombre_accion == "CREAR_HABILIDAD":
             # Si no lo manejó el grafo cognitivo, lo manejamos aquí
             pass

        elif nombre_accion in ["VOTAR", "VOTAR_LEY"]:
            # Los votos registrados en asambleas/leyes son actos públicos
            args = accion_data.get('argumentos', {})
            partes = decision.split(":") if decision else []
            
            ley_id = args.get('id') or args.get('ley_id') or args.get('ley_titulo') or args.get('ley') or (partes[1].strip() if len(partes) > 1 else None)
            voto_favor = True

            if not ley_id:
                # Fallback: Buscar propuestas pendientes sugeridas en el texto
                propuestas = self.modelo.facciones_leyes.get("propuestas", [])
                for p in propuestas:
                    if p.get("estado") == "pendiente" and p.get("titulo", "").lower() in (str(mensaje) + str(pensamiento)).lower():
                        ley_id = p.get("id")
                        break
                if not ley_id and propuestas:
                    ley_id = propuestas[0].get('id')

            # Determinar sentido del voto
            v_str = str(args.get('voto', '')).lower()
            if v_str:
                voto_favor = v_str in ["si", "yes", "a favor", "a_favor", "afavor", "true"]
            elif len(partes) >= 3:
                voto_norm = partes[2].strip().lower()
                voto_favor = voto_norm in ["si", "yes", "a favor", "a_favor", "afavor"]
            else:
                voto_texto = (str(mensaje) + str(pensamiento)).lower()
                voto_favor = not any(neg in voto_texto for neg in ["no", "contra", "rechazo", "mal"])

            if ley_id:
                exito = self.votar_ley(ley_id, voto_favor)
                if exito:
                    self.decir(f"🗳️ [VOTO PÚBLICO] He votado {'A FAVOR' if voto_favor else 'EN CONTRA'} de la propuesta {ley_id}.", pensamiento=pensamiento, global_broadcast=True)
                else:
                    self.decir(f"⚠️ Intenté votar en {ley_id}, pero no fue posible.", pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("No encontré una ley o propuesta activa para votar.", pensamiento=pensamiento)

        elif nombre_accion == "EJECUTAR_CODIGO":
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)
            # El resultado ya se procesó en el cerebro y se incluyó en el mensaje/pensamiento

        # Lógica de respuesta a invitaciones
        if self.ultimo_mensaje_recibido and "INVITACION_GRUPO" in str(self.ultimo_mensaje_recibido.get('contenido')):
            emisor_id = self.ultimo_mensaje_recibido['emisor']
            # Aceptamos si:
            # 1. No tenemos grupo
            # 2. Tenemos afinidad positiva con el emisor (> 0.3)
            # 3. Somos amables o extrovertidos
            afinidad = self.memoria.obtener_fuerza(emisor_id)
            amabilidad = self.personalidad.get('amabilidad', 0.5)
            
            if self.grupo_id is None and (afinidad > 0.3 or amabilidad > 0.7):
                partes = self.ultimo_mensaje_recibido['contenido'].split(":")
                self.grupo_id = partes[1]
                self.civilizacion_id = partes[1]
                self.rol = "Miembro"
                self.modelo.log(f"🤝 [UNION] Agente {self.unique_id} ha aceptado unirse a la Facción {self.grupo_id}.", categoria="social")
                self.decir(f"¡He aceptado la invitación! Me uno a la Facción {self.grupo_id} con entusiasmo.")
                # Notificar unión inmediata para actualizar paneles de sociedades
                self.modelo.notificar_cambio_estado()
            else:
                self.decir(f"Agradezco la invitación, Agente {emisor_id}, pero por ahora seguiré mi propio camino.")
            self.ultimo_mensaje_recibido = None

        # --- REPOSICIONAMIENTO OBLIGATORIO POR TURNO ---
        # Una acción por turno: O se quedan a trabajar/interactuar, o se mueven a una nueva casilla.
        acciones_estacionarias = ["RECOLECTAR", "DESCANSAR", "CONSTRUIR", "CURARSE", "GRADUARSE", 
                                 "INTERACCIONAR", "SOCIALIZAR", "COMERCIAR", "FUNDAR_GRUPO", 
                                 "FUNDAR_INSTITUCION", "CREAR_HABILIDAD", "ESCRIBIR_CRONICA", "VOTAR", "PROPONER_LEY"]
        
        # Determinar si la decisión implica quedarse en el sitio
        se_queda = any(nombre_accion.startswith(a) for a in acciones_estacionarias)
        
        # Forzar movimiento si la decisión es MOVER o si no hizo una acción estacionaria
        if nombre_accion == "MOVER" or not se_queda:
            dx, dy = 0, 0

            # Nueva lógica de movimiento dirigido por objetivo (GPS)
            if self.objetivo_movimiento:
                dest_x, dest_y = self.objetivo_movimiento
                if self.x == dest_x and self.y == dest_y:
                    # Hemos llegado al destino
                    self.modelo.log(f"📍 [NAVEGACION] Agente {self.unique_id} ha llegado a su destino en ({self.x}, {self.y}).", categoria="movimiento")
                    self.objetivo_movimiento = None
                else:
                    # Moverse hacia el destino
                    dx = 1 if dest_x > self.x else (-1 if dest_x < self.x else 0)
                    dy = 1 if dest_y > self.y else (-1 if dest_y < self.y else 0)
            else:
                # Lógica original de movimiento errante/cohesión
                # 1. Lógica de Cohesión Grupal (Patrullas)
                if self.grupo_id:
                    aliados = [a for a in self.modelo.agentes if a.grupo_id == self.grupo_id and a.unique_id != self.unique_id]
                    if aliados:
                        # Encontrar al aliado más cercano
                        mas_cercano = min(aliados, key=lambda a: abs(a.x - self.x) + abs(a.y - self.y))
                        dist = abs(mas_cercano.x - self.x) + abs(mas_cercano.y - self.y)
                        
                        if dist > 2: # Si están lejos, ir hacia ellos (cohesión)
                            dx = 1 if mas_cercano.x > self.x else (-1 if mas_cercano.x < self.x else 0)
                            dy = 1 if mas_cercano.y > self.y else (-1 if mas_cercano.y < self.y else 0)
                        else: # Si están cerca, moverse aleatoriamente pero sin alejarse mucho
                            dx = random.choice([-1, 0, 1])
                            dy = random.choice([-1, 0, 1])
                    else:
                        dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
                else:
                    # 2. Movimiento hacia otros agentes (Cohesión Social) para facilitar grupos
                    otros = [a for a in self.modelo.agentes if a.unique_id != self.unique_id]
                    if otros and random.random() < 0.7:
                        # Encontrar al agente más cercano (viva la socialización)
                        mas_cercano = min(otros, key=lambda a: abs(a.x - self.x) + abs(a.y - self.y))
                        dist = abs(mas_cercano.x - self.x) + abs(mas_cercano.y - self.y)
                        if dist > 1:
                            dx = 1 if mas_cercano.x > self.x else (-1 if mas_cercano.x < self.x else 0)
                            dy = 1 if mas_cercano.y > self.y else (-1 if mas_cercano.y < self.y else 0)
                        else:
                            dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
                    else:
                        dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
            
            # Aplicar movimiento con seguridad
            prob_fallo = 0.6 if self.modelo.weather == "storm" else 0.05
            
            if random.random() > prob_fallo:
                nx = max(0, min(self.modelo.mapa_size - 1, self.x + dx))
                ny = max(0, min(self.modelo.mapa_size - 1, self.y + dy))
                
                # Evitar agua y respetar fronteras si es posible
                if self.modelo.mapa[nx][ny].terrain_type != "water":
                    self.x, self.y = nx, ny

        # --- DETECCIÓN DE ENCUENTROS CON OTRAS FACCIONES ---
        if self.grupo_id:
            vecinos = [a for a in self.modelo.agentes if abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1 and a.unique_id != self.unique_id]
            for v in vecinos:
                if v.grupo_id and v.grupo_id != self.grupo_id:
                    # Probabilidad pequeña por paso para no saturar la diplomacia
                    if random.random() < 0.2:
                        self.modelo.gestionar_encuentro_facciones(self, v)

        self.actualizar_estado()

class ModeloRelacional:
    def __init__(self, num_agentes=10, log_callback=None, user_id=None, start_empty=False):
        self.num_agentes = num_agentes if not start_empty else 0
        self.start_empty = start_empty
        self.log_callback = log_callback
        self.user_id = user_id
        self.agentes_cargados = False # Importante: definir antes de cargar
        self.state_change_callback = None # Callback para forzar actualización de UI
        self._force_stop = False # Control de detención para evitar race conditions en reset
        self._stopped = False # Flag para bloquear logs/callbacks después de un stop/reset
        import threading
        self.lock = threading.RLock()

        # --- PERSISTENCIA POSTGRESQL ---
        self.db = DatabaseManager()
        self.db_active = self.db.connect()

        # --- ASEGURAR QUE EL USUARIO EXISTE ---
        if self.db_active and self.user_id:
            self.db.ensure_user_exists(self.user_id)

        # Conectar herramientas y skills con el sistema de logs del modelo
        if self.log_callback:
            herramientas.log_callback = self.log
            skill_manager.log_callback = self.log
            print("🔧 [DEBUG] Skill manager log callback conectado.")


        # Inicializar atributos a un estado base/vacío antes de cargar
        self.paso_actual = 0
        self.agentes = []
        self.objetivos_grupos = {}
        self.precio_recurso_actual = 2.0
        self.economia = {}
        self.historial_relaciones = []
        self.historial_grupos = []
        self.datos = []
        self.relaciones_grupos = {}
        self.historial_logs = []
        self.asambleas_globales = []
        self.leyes_globales = []
        self.facciones_leyes = {}
        self.instituciones = {} # NUEVO: Almacena instituciones formalizadas
        self.guerras_activas = []
        self.grupos_creados_este_paso = 0
        self.moderador_id = None
        self.ultimo_paso_asamblea = -100 # Cooldown inicial para asambleas
        self.infraestructura = []
        self.civilizaciones = {}
        self.grupos_dinamicos = {}
        self.mapa_size = 20
        self.COSTO_EXPANSION = 1000.0 # Costo en MC por cada nivel de expansión
        self.mapa = None  # Se generará después de intentar cargar, o si la carga falla
        self.ubicacion_universidad = None
        self.weather = WeatherType.SUNNY
        self.weather_timer = 0
        self.weather_duration = 20
        self.lore = ""
        self.seed = ""
        self.eventos_activos = []
        self.sistema_misiones = SistemaMisiones()
        self.misiones_completadas_este_turno = []
        self.historia = LibretaHistoria()
        self.agente_poseido_id = None
        self.ritmo_lectura = 2.0  # segundos de pausa entre cada agente (ritmo de lectura)
        self.colores_paleta = [
            "#7c4dff", "#00e676", "#ff1744", "#00e5ff", "#ffea00", 
            "#d500f9", "#ff9100", "#1de9b6", "#2979ff", "#f50057",
            "#651fff", "#3d5afe", "#00b0ff", "#00b8d4", "#ff3d00",
            "#76ff03", "#ff4081", "#e040fb", "#7c4dff", "#536dfe"
        ]
        
        from cerebro_llm import cerebro_llm
        self.optimizador = DecisionOptimizer(llm_caller_batch=cerebro_llm.generar_decisiones_batch, similarity_threshold=0.3)

        self.nombres_facciones = [
            "Imperio Solar", "Federación Lunar", "Orden de la Aurora", "Confraternidad de los Ventureros",
            "Dominio de la Tierra Profunda", "Alianza de los Caminos Estelares", "Hermandad de los Chroniclers",
            "Legión de la Tempestad", "Cofradía de los Forjadores", "Sociedad de los Exploradores del Abismo",
            "Templo de la Luz Eterna", "Clan de la Sierra Negra", "Gremio de los Mariscadores", "Fraternidad de los Alquimistas",
            "Orden de los Guardiánes del Horizonte", "Consejo de los Ancianos", "Legión de los Inquebrantables",
            "Cofradía de los Músicos Errantes", "Alianza de los Mercaderes del Desierto", "Hermandad de los Jardineros Celestiales",
            "Dominio de los Volcanes Ardientes", "Sociedad de los Cartógrafos del Océano", "Templo de la Lluvia Plateada",
            "Clan de los Pescadores del Mar Profundo", "Gremio de los Herreros del Cielo", "Fraternidad de los Poetas de la Noche",
            "Orden de los Cazadores de Sombras", "Consejo de los Arquitectos de la Realidad", "Legión de los Protectoras de la Vida",
            "Cofradía de los Coleccionadores de Recuerdos", "Alianza de los Mercenarios del Tiempo", "Hermandad de los Escultores de la Luz"
        ]

        # --- Carga de estado ---
        if not self.start_empty:
            self.cargar_estado()
        
        # --- Si no se cargó un mapa, generar uno nuevo ---
        if self.mapa is None:
            self.log("🗺️ Generando nuevo mapa...", categoria="sistema")
            self.mapa = self.generar_mapa()

        # --- Inicialización de un mundo nuevo si la carga falló O si el mundo está vacío ---
        if (not self.agentes_cargados or len(self.agentes) == 0) and not self.lore:
            if self.start_empty:
                self.log("🌱 Reiniciando mundo a un estado VACÍO por orden del Arquitecto.", categoria="sistema")
            else:
                self.log("🌱 No se encontró estado previo o el mundo está vacío. Creando un nuevo universo...", categoria="sistema")
            
            # Resetear atributos por si la carga parcial dejó datos residuales
            self.paso_actual = 0
            self.objetivos_grupos = {}
            self.precio_recurso_actual = 2.0
            self.economia = {
                "indice_bursatil": 1000.0,
                "historial_indice": [1000.0],
                "total_dinero": 0.0,
                "inversiones_activas": 0,
                "volumen_transacciones": 0.0
            }
            self.datos = []
            self.relaciones_grupos = {}
            self.historial_logs = []
            self.asambleas_globales = []
            self.leyes_globales = []
            self.facciones_leyes = {}
            self.guerras_activas = []
            self.ultimo_paso_asamblea = -100
            self.infraestructura = []
            self.civilizaciones = {}
            
            # Generar mapa y colocar Universidad
            self.mapa = self.generar_mapa()
            self.ubicacion_universidad = None
            placed = False
            for _ in range(100):
                x, y = random.randint(2, self.mapa_size - 3), random.randint(2, self.mapa_size - 3)
                tile = self.mapa[x][y]
                if tile.terrain_type == TerrainType.GRASS and not tile.buildings:
                    universidad_edif = {
                        "id": "EDIF-UNICA-UNIVERSIDAD", "tipo": "Universidad", "grupo_id": None,
                        "constructor": "MundoIA", "paso_creacion": 0, "x": x, "y": y
                    }
                    self.infraestructura.append(universidad_edif)
                    self.mapa[x][y].buildings.append(universidad_edif)
                    self.ubicacion_universidad = (x, y)
                    self.log(f"🏛️ Una Universidad ha sido fundada en ({x}, {y}).", categoria="mundo")
                    placed = True
                    break
            if not placed:
                self.log("⚠️ No se pudo encontrar un lugar para la Universidad.", categoria="error")
            
            # Colocar Farmacia inicial (solución a la paradoja de medicina)
            self.log("🔍 [DEBUG] Iniciando búsqueda de ubicación para Farmacia...", categoria="sistema")
            self.ubicacion_farmacia = None
            placed_farmacia = False
            intentos = 0
            for _ in range(200):  # Más intentos que la Universidad para asegurar colocación
                intentos += 1
                x, y = random.randint(2, self.mapa_size - 3), random.randint(2, self.mapa_size - 3)
                tile = self.mapa[x][y]
                # Evitar colocar en el mismo tile que la Universidad
                if tile.terrain_type == TerrainType.GRASS and not tile.buildings and (x, y) != self.ubicacion_universidad:
                    farmacia_edif = {
                        "id": "EDIF-UNICA-FARMACIA", "tipo": "Farmacia", "grupo_id": None,
                        "constructor": "MundoIA", "paso_creacion": 0, "x": x, "y": y
                    }
                    self.infraestructura.append(farmacia_edif)
                    self.mapa[x][y].buildings.append(farmacia_edif)
                    self.ubicacion_farmacia = (x, y)
                    self.log(f"💊 Una Farmacia ha sido fundada en ({x}, {y}). ¡Medicina accesible para todos!", categoria="mundo")
                    placed_farmacia = True
                    break
            if not placed_farmacia:
                self.log(f"⚠️ No se pudo encontrar un lugar para la Farmacia después de {intentos} intentos.", categoria="error")

            # Inicializar sistemas de juego
            self.sistema_misiones = SistemaMisiones()
            if not self.start_empty:
                self.sistema_misiones.inicializar_misiones_iniciales(self.paso_actual)
            self.historia = LibretaHistoria()
            
            # ¡Crear agentes iniciales si no se pidió empezar vacío!
            if not self.start_empty:
                self.agentes = [Agente(f"A{i}_{random.randint(100,999)}", self) for i in range(self.num_agentes)]

                # Crear algunas facciones iniciales ALEATORIAS para impulsar la cohesión
                num_facciones = 2
                import random as _random
                facciones_posibles = _random.sample(self.nombres_facciones, num_facciones)
                
                for i, nombre_fac in enumerate(facciones_posibles):
                    f_id = f"G-{nombre_fac.split()[0].upper()}-{_random.randint(10,99)}"
                    color = self.colores_paleta[i % len(self.colores_paleta)]
                    self.civilizaciones[f_id] = Civilizacion(f_id, nombre_fac, color, self.user_id, f"Somos la facción {nombre_fac}, unidos por un destino común.")
                    self.objetivos_grupos[f_id] = f"Prosperar como {nombre_fac} y dominar los recursos."
                    
                    # Asignar agentes a la facción
                    agentes_por_fac = self.num_agentes // (num_facciones + 1)
                    inicio = i * agentes_por_fac
                    fin = inicio + agentes_por_fac
                    for j in range(inicio, min(fin, len(self.agentes))):
                        a = self.agentes[j]
                        a.grupo_id = f_id
                        a.civilizacion_id = f_id
                        if j == inicio: a.rol = "Líder"
            else:
                self.agentes = []
            
            self.agentes_cargados = True # Marcar como inicializado
        
        # --- RECUPERACIÓN: Si agentes_cargados es True pero no hay Universidad, re-fundarla ---
        elif self.ubicacion_universidad is None:
            self.log("🏛️ [RECOVER] La Universidad no se encontró en el estado cargado. Intentando re-fundarla...", categoria="sistema")
            placed = False
            for _ in range(200):
                x, y = random.randint(2, self.mapa_size - 3), random.randint(2, self.mapa_size - 3)
                tile = self.mapa[x][y]
                if tile.terrain_type == TerrainType.GRASS and not tile.buildings:
                    universidad_edif = {
                        "id": "EDIF-UNICA-UNIVERSIDAD", "tipo": "Universidad", "grupo_id": None,
                        "constructor": "MundoIA", "paso_creacion": self.paso_actual, "x": x, "y": y
                    }
                    self.infraestructura.append(universidad_edif)
                    self.mapa[x][y].buildings.append(universidad_edif)
                    self.ubicacion_universidad = (x, y)
                    self.log(f"🏛️ La Universidad ha sido re-fundada en ({x}, {y}) tras la restauración del sistema.", categoria="mundo")
                    placed = True
                    break
            if not placed:
                 self.log("⚠️ [RECOVER] No se pudo encontrar un lugar libre para re-fundar la Universidad.", categoria="error")


    def __getstate__(self):
        """
        Define qué atributos del ModeloRelacional se serializan.
        Excluye 'db', 'log_callback', 'state_change_callback' y serializa objetos complejos a diccionarios.
        """
        state = {
            'num_agentes': self.num_agentes,
            'user_id': self.user_id,
            'agentes_cargados': self.agentes_cargados,
            'paso_actual': self.paso_actual,
            'objetivos_grupos': self.objetivos_grupos,
            'precio_recurso_actual': self.precio_recurso_actual,
            'economia': self.economia,
            'historial_relaciones': self.historial_relaciones,
            'historial_grupos': self.historial_grupos,
            'datos': self.datos,
            'historial_logs': self.historial_logs,
            'asambleas_globales': self.asambleas_globales,
            'leyes_globales': self.leyes_globales,
            'facciones_leyes': self.facciones_leyes,
            'guerras_activas': self.guerras_activas,
            'grupos_creados_este_paso': self.grupos_creados_este_paso,
            'moderador_id': self.moderador_id,
            'ultimo_paso_asamblea': self.ultimo_paso_asamblea,
            'infraestructura': self.infraestructura,
            'mapa_size': self.mapa_size,
            'COSTO_EXPANSION': self.COSTO_EXPANSION,
            'ubicacion_universidad': self.ubicacion_universidad,
            'weather': self.weather,
            'weather_timer': self.weather_timer,
            'weather_duration': self.weather_duration,
            'lore': self.lore,
            'seed': self.seed,
            'eventos_activos': self.eventos_activos,
            'misiones_completadas_este_turno': self.misiones_completadas_este_turno,
            'colores_paleta': self.colores_paleta,
            'nombres_facciones': self.nombres_facciones,
            'agente_poseido_id': self.agente_poseido_id,
            
            # Serializar objetos complejos a diccionarios
            'agentes': [a.to_dict() for a in self.agentes],
            'mapa': [[t.to_dict() for t in row] for row in self.mapa],
            'civilizaciones': {k: v.to_dict() for k, v in self.civilizaciones.items()},
            'sistema_misiones': self.sistema_misiones.__getstate__(),
            'historia': self.historia.__getstate__(),
            'instituciones': {k: v.to_dict() for k, v in self.instituciones.items()},
            
            # Convert tuple keys in relaciones_grupos to strings (e.g., "G1:G2")
            'relaciones_grupos': {f"{k[0]}:{k[1]}": v for k, v in self.relaciones_grupos.items()}
        }
        
        return state

    def __setstate__(self, state):
        """
        Define cómo se deserializa el ModeloRelacional.
        Reconstruye objetos complejos a partir de sus diccionarios y re-inicializa atributos excluidos.
        """
        self.__dict__.update(state)
        self.agente_poseido_id = state.get('agente_poseido_id')
        
        # Re-inicializar atributos excluidos
        self.db = DatabaseManager()
        self.db_active = self.db.connect() # Re-conectar la base de datos
        self.log_callback = None # Se espera que se asigne externamente si es necesario
        self.state_change_callback = None # Se espera que se asigne externamente si es necesario
        
        # Reconstruir objetos complejos
        self.agentes = [Agente.from_dict(a_data, self) for a_data in state['agentes']]
        
        # Reconstruir mapa
        self.mapa = []
        for row_data in state['mapa']:
            row = []
            for tile_data in row_data:
                tile = Tile(tile_data["x"], tile_data["y"], tile_data["terrain"])
                tile.resource_node = tile_data.get("resource")
                tile.owner_civ_id = tile_data.get("owner")
                tile.buildings = tile_data.get("buildings", [])
                row.append(tile)
            self.mapa.append(row)
        
        # Reconstruir civilizaciones
        self.civilizaciones = {k: Civilizacion.from_dict(v_data) for k, v_data in state.get('civilizaciones', {}).items()}
        
        # Reconstruir instituciones
        self.instituciones = {k: Institucion.from_dict(v_data) for k, v_data in state.get('instituciones', {}).items()}
        
        # Reconstruir sistema_misiones
        self.sistema_misiones = SistemaMisiones()
        self.sistema_misiones.__setstate__(state['sistema_misiones'])
        
        # Reconstruir historia
        self.historia = LibretaHistoria()
        self.historia.__setstate__(state['historia'])
        
        # Reconstruir relaciones de grupos
        self.relaciones_grupos = {}
        if 'relaciones_grupos' in state:
            for k_str, v in state['relaciones_grupos'].items():
                parts = k_str.split(":")
                if len(parts) == 2:
                    self.relaciones_grupos[(parts[0], parts[1])] = v
                else:
                    # Fallback if the key format is unexpected
                    self.relaciones_grupos[k_str] = v

    def evaluar_evolucion_civilizaciones(self):
        """Evalúa si los grupos cumplen los requisitos para convertirse en Civilizaciones."""
        for civ_id, civ in self.civilizaciones.items():
            if civ.tipo == "GRUPO":
                # Criterios de evolución:
                # 1. Población mínima: 4 miembros
                # 2. Riqueza acumulada: 600 (suma de recursos de miembros)
                
                miembros = [a for a in self.agentes if a.civilizacion_id == civ_id or a.grupo_id == civ_id]
                num_miembros = len(miembros)
                recursos_totales = sum(a.recursos for a in miembros)
                
                if num_miembros >= 4 and recursos_totales >= 600:
                    civ.tipo = "CIVILIZACION"
                    self.log(f"🌟 [EVOLUCIÓN] ¡El grupo '{civ.nombre}' ha evolucionado a una CIVILIZACIÓN!", categoria="sistema")
                    self.log(f"   - Población: {num_miembros}, Riqueza: {recursos_totales:.1f}", categoria="sistema")
                    
                    self.historia.agregar_hito({
                        "turno": self.paso_actual,
                        "descripcion": f"El grupo '{civ.nombre}' se ha consolidado como una Civilización.",
                        "tipo": "evolucion"
                    })
                    self.notificar_cambio_estado()

    def notificar_cambio_estado(self):
        """Invoca el callback de cambio de estado para actualizar la UI inmediatamente."""
        if self.state_change_callback:
            self.state_change_callback()

    def expandir_mundo(self):
        """Aumenta el tamaño del mapa (+4 casillas) si el Arquitecto tiene fondos suficientes."""
        costo = self.COSTO_EXPANSION
        fondos_actuales = self.economia.get("total_dinero", 0.0)
        
        if fondos_actuales < costo:
            self.log(f"❌ [ECONOMÍA] Fondos insuficientes para expandir el mundo. Se requieren {costo} MC.", categoria="error")
            return False, f"Fondos insuficientes ({fondos_actuales:.1f} / {costo} MC)"

        nueva_size = self.mapa_size + 4 
        if nueva_size > 60: # Límite de seguridad para rendimiento
            return False, "Has alcanzado el límite máximo de expansión de este fragmento de realidad."

        # 1. Deducir fondos
        self.economia["total_dinero"] -= costo
        
        # 2. Crear nueva matriz
        vieja_size = self.mapa_size
        viejos_tiles = self.mapa
        
        nuevo_mapa = [[None for _ in range(nueva_size)] for _ in range(nueva_size)]
        
        # 3. Copiar tiles antiguos y generar nuevos
        # Calculamos un offset para que crezca radialmente si es posible, 
        # pero por simplicidad de coordenadas de agentes actuales, expandiremos hacia +X y +Y
        for x in range(nueva_size):
            for y in range(nueva_size):
                if x < vieja_size and y < vieja_size:
                    nuevo_mapa[x][y] = viejos_tiles[x][y]
                else:
                    # Generar nuevo terreno para la expansión
                    # (Usando lógica similar a generar_mapa pero localmente)
                    prob = random.random()
                    t_type = TerrainType.GRASS
                    if prob < 0.15: t_type = TerrainType.MOUNTAIN
                    elif prob < 0.35: t_type = TerrainType.FOREST
                    elif prob < 0.45: t_type = TerrainType.WATER
                    elif prob < 0.55: t_type = TerrainType.DESERT
                    
                    nuevo_tile = Tile(x, y, t_type)
                    # Añadir recursos aleatorios
                    if random.random() < 0.1:
                        r_type = random.choice(["food", "gold", "crystal"])
                        nuevo_tile.resource_node = {"type": r_type, "amount": random.randint(50, 150)}
                    
                    nuevo_mapa[x][y] = nuevo_tile

        self.mapa = nuevo_mapa
        self.mapa_size = nueva_size
        
        self.log(f"🌌 [EXPANSIÓN] El Arquitecto ha expandido los límites del mundo a {nueva_size}x{nueva_size}!", categoria="sistema")
        self.notificar_cambio_estado()
        
        # Guardar en DB inmediatamente para persistir la inversión
        if self.db_active:
            self.guardar_estado()
            
        return True, f"Mundo expandido a {nueva_size}x{nueva_size}"

    def generar_mapa(self):
        """Genera un mapa procedural básico con diferentes terrenos."""
        nuevo_mapa = [[None for _ in range(self.mapa_size)] for _ in range(self.mapa_size)]
        
        # Generación simple basada en ruido aleatorio (se puede mejorar con Perlin Noise)
        for x in range(self.mapa_size):
            for y in range(self.mapa_size):
                r = random.random()
                tipo = TerrainType.GRASS
                
                # Clusters simples
                if 0.4 < r < 0.6: tipo = TerrainType.FOREST
                elif 0.85 < r < 0.95: tipo = TerrainType.MOUNTAIN
                elif r >= 0.95: tipo = TerrainType.WATER
                elif r < 0.05: tipo = TerrainType.DESERT
                
                tile = Tile(x, y, tipo)
                
                # Recursos iniciales según terreno
                if tipo == TerrainType.FOREST:
                    tile.resource_node = {"type": "wood", "amount": random.randint(50, 200)}
                elif tipo == TerrainType.MOUNTAIN:
                    tile.resource_node = {"type": "stone", "amount": random.randint(50, 200)}
                elif tipo == TerrainType.GRASS and random.random() < 0.2:
                    tile.resource_node = {"type": "food", "amount": random.randint(20, 100)}
                
                nuevo_mapa[x][y] = tile
        
        return nuevo_mapa

    def actualizar_clima(self):
        """Ciclo de clima dinámico."""
        self.weather_timer += 1
        if self.weather_timer >= self.weather_duration:
            self.weather_timer = 0
            # Cambiar clima
            climas = [WeatherType.SUNNY, WeatherType.RAINY, WeatherType.STORM, WeatherType.FOGGY, WeatherType.HEATWAVE]
            pesos = [0.5, 0.2, 0.1, 0.1, 0.1] # Mayor probabilidad de sol
            self.weather = random.choices(climas, weights=pesos, k=1)[0]
            self.weather_duration = random.randint(10, 30)
            
            efecto = ""
            if self.weather == WeatherType.STORM: efecto = "¡Tormenta severa! Movimiento difícil."
            elif self.weather == WeatherType.RAINY: efecto = "Lluvia. Crecimiento de cultivos."
            elif self.weather == WeatherType.HEATWAVE: efecto = "Ola de calor. Mayor consumo de agua."
            
            self.log(f"🌦️ [CLIMA] El clima ha cambiado a: {self.weather.upper()}. {efecto}", categoria="ambiente")

    def crear_asamblea(self, proponente_id, tema, ley_sintetizada=None):
        """Crea una nueva asamblea global para debate y votación."""
        if not self.agentes: return False, "No hay agentes."

        asamblea_id = f"ASAMBLEA-{len(self.asambleas_globales) + 1}-{self.paso_actual}"
        
        # Priorizar al Moderador Global si existe, de lo contrario el proponente o azar
        mod_id = self.moderador_id if self.moderador_id else proponente_id
        
        nueva_asamblea = {
            "id": asamblea_id,
            "proponente_id": proponente_id,
            "tema": tema,
            "moderador_id": mod_id,
            "votos_si": 0,
            "votos_no": 0,
            "votantes": [], # Agentes que ya votaron
            "estado": "DEBATE", # Puede ser 'DEBATE', 'VOTACION', 'FINALIZADA'
            "paso_inicio": self.paso_actual,
            "pasos_restantes": 5, # Duración extendida del debate para dar tiempo a opinar
            "ley_sintetizada": ley_sintetizada # Datos para proponer ley formalmente
        }
        self.asambleas_globales.append(nueva_asamblea)
        self.ultimo_paso_asamblea = self.paso_actual
        self.notificar_cambio_estado() # Notificar creación inmediata
        self.log(f"🏛️ [ASAMBLEA] Agente {proponente_id} ha iniciado la asamblea '{tema}'. Moderador: {mod_id}. ID: {asamblea_id}", categoria="consenso")
        return True, asamblea_id

    def registrar_voto(self, agente_id, asamblea_id, voto):
        """Registra el voto de un agente en una asamblea específica."""
        for asamblea in self.asambleas_globales:
            if asamblea["id"] == asamblea_id:
                if agente_id in asamblea["votantes"]:
                    self.log(f"⚠️ Agente {agente_id} ya votó en la asamblea {asamblea_id}.", categoria="sistema")
                    return False, "Ya has votado en esta asamblea."
                
                voto_norm = voto.lower().strip()
                if voto_norm in ["si", "yes", "a favor", "a_favor", "afavor"]:
                    asamblea["votos_si"] += 1
                elif voto_norm in ["no", "en contra", "en_contra", "encontra"]:
                    asamblea["votos_no"] += 1
                else:
                    self.log(f"⚠️ Voto inválido '{voto}' del agente {agente_id} en asamblea {asamblea_id}. Se asume abstención o error.", categoria="sistema")
                    return False, "Voto inválido. Usa 'si' o 'no'."
                
                asamblea["votantes"].append(agente_id)
                self.log(f"🗳️ Agente {agente_id} votó '{voto}' en la asamblea '{asamblea['tema']}' (ID: {asamblea_id}).", categoria="consenso")
                self.notificar_cambio_estado()
                return True, "Voto registrado."
        
        self.log(f"⚠️ Asamblea {asamblea_id} no encontrada para registrar voto de {agente_id}.", categoria="sistema")
        return False, "Asamblea no encontrada."

    def procesar_asambleas(self):
        """Procesa las asambleas activas, gestionando fases de debate y votación."""
        asambleas_a_finalizar = []
        
        for asamblea in self.asambleas_globales:
            if asamblea["estado"] == "DEBATE":
                asamblea["pasos_restantes"] -= 1
                if asamblea["pasos_restantes"] <= 0:
                    asamblea["estado"] = "VOTACION"
                    asamblea["pasos_restantes"] = 15  # Votación extendida para asegurar participación
                    
                    # --- NUEVO: SÍNTESIS REACTIVA DEL DEBATE ---
                    mod_obj = self.get_agent_by_id(asamblea["moderador_id"])
                    if mod_obj:
                        # 1. Recolectar lo que se dijo durante estos pasos de debate
                        # Buscamos en los logs mensajes de diálogo que mencionen el tema o asamblea
                        palabras_clave = asamblea["tema"].lower().split()
                        dialogos_debate = []
                        for l in self.historial_logs[-60:]: # Miramos un poco hacia atrás
                            msg = l["mensaje"].lower()
                            if l["categoria"] == "dialogo" and any(k in msg for k in palabras_clave):
                                dialogos_debate.append(l["mensaje"])
                        
                        # 2. Sintetizar la ley basada en la discusión real
                        self.log(f"⚖️ [MODERADOR] El debate ha concluido. Sintetizando consenso social...", categoria="consenso")
                        ley_sintetizada = cerebro_llm.sintetizar_ley_desde_debate(mod_obj, dialogos_debate)
                        
                        # Guardar para registro
                        asamblea["ley_sintetizada"] = ley_sintetizada
                        
                        # 3. Presentar propuesta formal
                        self.log(f"⚖️ [MODERADOR] Propuesta formal: '{ley_sintetizada.get('titulo')}'", categoria="consenso")
                        mod_obj.proponer_ley(ley_sintetizada.get("titulo"), ley_sintetizada.get("contenido"), alcance=ley_sintetizada.get("alcance", "global"))
                    
                    self.log(f"🔔 [ASAMBLEA] Se abre el periodo de VOTACIÓN para la asamblea '{asamblea['tema']}'.", categoria="consenso")
                    self.notificar_cambio_estado() # Cambio de fase DEBATE -> VOTACION
                    
            elif asamblea["estado"] == "VOTACION":
                asamblea["pasos_restantes"] -= 1
                if asamblea["pasos_restantes"] <= 0:
                    asambleas_a_finalizar.append(asamblea)
        
        for asamblea in asambleas_a_finalizar:
            asamblea["estado"] = "FINALIZADA"
            self.asambleas_globales.remove(asamblea)
            self.notificar_cambio_estado() # Asamblea terminada
            
            total_votos = asamblea["votos_si"] + asamblea["votos_no"]
            if total_votos == 0:
                self.log(f"❌ [ASAMBLEA FINALIZADA] La asamblea '{asamblea['tema']}' (ID: {asamblea['id']}) finalizó sin votos. Resultado: NULO.", categoria="consenso")
                continue

            if asamblea["votos_si"] > asamblea["votos_no"]:
                resultado = "APROBADA"
                self.log(f"✅ [ASAMBLEA FINALIZADA] La asamblea '{asamblea['tema']}' (ID: {asamblea['id']}) ha sido APROBADA. Votos SI: {asamblea['votos_si']}, Votos NO: {asamblea['votos_no']}.", categoria="consenso")
                # Registro histórico
                self.historia.agregar_hito({
                    "turno": self.paso_actual,
                    "descripcion": f"La sociedad ha aprobado mediante asamblea: '{asamblea['tema']}'.",
                    "tipo": "ley"
                })
                # Aplicar resultados de la asamblea
                self.aplicar_resultado_asamblea(asamblea["tema"], asamblea["votos_si"], asamblea["votos_no"])
            else:
                resultado = "RECHAZADA"
                self.log(f"❌ [ASAMBLEA FINALIZADA] La asamblea '{asamblea['tema']}' (ID: {asamblea['id']}) ha sido RECHAZADA. Votos SI: {asamblea['votos_si']}, Votos NO: {asamblea['votos_no']}.", categoria="consenso")
    
    def aplicar_resultado_asamblea(self, tema, votos_si, votos_no):
        """Aplica el resultado de una asamblea según su tema."""
        # Aquí puedes agregar lógica para diferentes tipos de decisiones
        tema = tema.lower()
        
        if "impuestos" in tema or "fiscal" in tema:
            self.economia["impuestos"] = self.economia.get("impuestos", 0.1) + 0.05
            self.log(f"💸 [ECONOMÍA] Se han aumentado los impuestos en respuesta a la asamblea.", categoria="economia")
        
        if "seguridad" in tema or "defensa" in tema:
            for agente in self.agentes:
                agente.necesidades["seguridad"] = min(agente.necesidades["seguridad"] + 2, 10)
            self.log(f"🛡️ [SEGURIDAD] Nivel de seguridad incrementado para todos los agentes.", categoria="militar")
        
        if "infraestructura" in tema or "construir" in tema:
            # Generar un evento de construcción usando el sistema centralizado
            self.trigger_event("construcción", f"Comienzo de obras públicas por votación ({tema})", duracion=10)
            self.log(f"🏗️ [INFRAESTRUCTURA] Aprobada la construcción de obras públicas.", categoria="construccion")
        
        if "educación" in tema or "universidad" in tema:
            for agente in self.agentes:
                agente.experiencia["educacion"] = agente.experiencia.get("educacion", 0) + 1
            self.log(f"🎓 [EDUCACIÓN] Iniciada campaña de educación pública.", categoria="educacion")




    def gestionar_moderador(self):
        """Designa y gestiona el comportamiento del Moderador político."""
        if not self.agentes: return
        mod_actual = next((a for a in self.agentes if a.unique_id == self.moderador_id and a.esta_vivo), None)
        
        if not mod_actual:
            candidatos = [a for a in self.agentes if a.esta_vivo and a.rol != "Historiador"]
            if candidatos:
                nuevo_mod = max(candidatos, key=lambda x: x.reputacion + (x.experiencia.get("comercio", 0) / 100))
                self.moderador_id = nuevo_mod.unique_id
                nuevo_mod.rol = "Moderador"
                self.log(f"⚖️ [MODERADOR] {nuevo_mod.unique_id} ha sido designado para ordenar la política.", categoria="sistema")
        
        # --- NUEVO: SENSOR DE INTENCIONES POLÍTICAS ---
        # El moderador escucha TODO el ambiente (incluyendo privados) para detectar inquietud social
        # Aumentamos rango a 50 logs para mayor contexto
        mensajes_recientes = [l["mensaje"].lower() for l in self.historial_logs[-50:] if l["categoria"] in ["dialogo", "social"]]
        
        keywords_politicas = ["ley", "norma", "regla", "votar", "asamblea", "prohibido", "obligatorio", "derecho", "impuesto", "decretar", "legal", "ilegal", "reforma"]
        menciones = sum(1 for m in mensajes_recientes if any(k in m for k in keywords_politicas))
        
        # Umbral reducido a 2 para mayor agilidad legislativa
        asambleas_activas = [a for a in self.asambleas_globales if a["estado"] in ["DEBATE", "VOTACION"]]
        
        # Cooldown de 15 pasos entre asambleas
        if menciones >= 2 and not asambleas_activas and (self.paso_actual - self.ultimo_paso_asamblea > 15):
            mod_obj = self.get_agent_by_id(self.moderador_id)
            if mod_obj:
                self.log(f"🎙️ [MODERADOR] He detectado inquietud legislativa ({menciones} menciones). Abro sesión de ASAMBLEA.", categoria="consenso")
                # El moderador identifica el tema principal de las menciones para el título
                keywords_detectadas = [k for k in keywords_politicas if any(k in m for m in mensajes_recientes)]
                tema_principal = keywords_detectadas[0].title() if keywords_detectadas else "Debate General"
                
                self.crear_asamblea(self.moderador_id, f"Debate formal: {tema_principal}")

    def procesar_propuestas_ley(self):
        """Procesa el sistema de votación estandarizado (50%+1)."""
        propuestas = self.facciones_leyes.get("propuestas", [])
        for p in propuestas:
            if p["estado"] != "pendiente": continue

            # Obtener alcance con fallback por si los datos están malformados
            alcance = p.get("alcance", "global")
            propuesta_grupo_id = p.get("grupo_id")
            
            universo = [a for a in self.agentes if a.esta_vivo and (alcance == "global" or a.grupo_id == propuesta_grupo_id)]
            total_posible = len(universo)
            if total_posible == 0: continue

            mitad_mas_uno = (total_posible // 2) + 1
            pasos_vida = self.paso_actual - p.get("paso_creacion", self.paso_actual)

            votos_si = p.get("votos_si", 0)
            votos_no = p.get("votos_no", 0)

            if votos_si >= mitad_mas_uno:
                p["estado"] = "aprobada"
                self._aplicar_ley_aprobada(p)
            elif votos_no >= mitad_mas_uno or pasos_vida >= 5:
                p["estado"] = "rechazada"
                razon = "mayoría en contra" if votos_no >= mitad_mas_uno else "expiración"
                self.log(f"❌ [LEY] '{p['titulo']}' RECHAZADA por {razon}.", categoria="sistema")

    def _aplicar_ley_aprobada(self, p):
        """Efectos reales de una ley aprobada."""
        gid = p["grupo_id"]
        if gid not in self.facciones_leyes: self.facciones_leyes[gid] = []
        self.facciones_leyes[gid].append(p)
        
        # Lógica especial de liderazgo (reutilizando tu lógica de refundación)
        if "LIDERAZGO:" in p["titulo"].upper():
             partes = p["titulo"].split(":")
             if len(partes) > 1:
                nuevo_n = partes[1]
                if gid in self.civilizaciones: self.civilizaciones[gid].nombre = nuevo_n
                for a in self.agentes:
                    if a.grupo_id == gid: a.rol = "Líder" if a.unique_id == p["autor"] else "Miembro"
        
        self.log(f"⚖️ [LEY] ¡'{p['titulo']}' es ahora VIGENTE!", categoria="sistema")

    def fundar_institucion(self, agente_id, nombre, tipo):
        """Permite a un agente fundar una institución formal."""
        agente = self.get_agent_by_id(agente_id)
        if not agente: return False, "Agente no encontrado."

        if agente.dinero < 100:
            return False, "Se requieren al menos 100 MC para fundar una institución."

        inst_id = f"INST-{len(self.instituciones) + 1}-{self.paso_actual}"
        nueva_inst = Institucion(inst_id, nombre, tipo, agente_id, agente.x, agente.y, self.user_id)
        
        agente.dinero -= 100
        self.instituciones[inst_id] = nueva_inst
        agente.hitos.append(f"Fundador de {nombre}")
        
        self.log(f"🏛️ [INSTITUCION] ¡{agente_id} ha fundado '{nombre}' ({tipo}) en ({agente.x}, {agente.y})!", categoria="social")
        self.historia.agregar_hito({
            "turno": self.paso_actual,
            "descripcion": f"Se ha fundado la institución '{nombre}' de tipo {tipo}.",
            "tipo": "institucion"
        })
        self.notificar_cambio_estado()
        return True, inst_id

    def unirse_institucion(self, agente_id, inst_id):
        """Permite a un agente unirse a una institución existente."""
        agente = self.get_agent_by_id(agente_id)
        inst = self.instituciones.get(inst_id)
        
        if not agente or not inst: return False, "Datos inválidos."
        
        if agente_id in inst.miembros: return False, "Ya eres miembro."
        
        inst.miembros.append(agente_id)
        self.log(f"🤝 [INSTITUCION] Agente {agente_id} se ha unido a '{inst.nombre}'.", categoria="social")
        self.notificar_cambio_estado()
        return True, "Haste unido a la institución."

    def actualizar_territorios(self):
        """Actualiza la propiedad de las celdas del mapa basada en la presencia de agentes."""
        # Resetear dueños
        for x in range(self.mapa_size):
            for y in range(self.mapa_size):
                self.mapa[x][y].owner_civ_id = None
        
        # Marcar desde agentes (O(agentes) en vez de O(mapa² * agentes))
        for a in self.agentes:
            if a.esta_vivo:
                cid = a.civilizacion_id or a.grupo_id
                if cid:
                    self.mapa[a.x][a.y].owner_civ_id = cid
        
        # Actualizar territorio por civilización
        for civ in self.civilizaciones.values():
            civ.territorio = [
                (x, y)
                for x in range(self.mapa_size)
                for y in range(self.mapa_size)
                if self.mapa[x][y].owner_civ_id == civ.id
            ]

    def actualizar_economia(self):
        """Calcula la fluctuación del índice bursátil y el dinero total del sistema."""
        if not self.agentes: return
        
        total_dinero = sum(a.dinero for a in self.agentes)
        inversiones_activas = sum(len(a.inversiones) for a in self.agentes if hasattr(a, 'inversiones'))
        
        # El índice bursátil varía según el dinero total y las inversiones
        old_total = self.economia.get("total_dinero", total_dinero)
        variacion = (total_dinero - old_total) * 0.1 if old_total > 0 else 0
        
        self.economia["indice_bursatil"] = self.economia.get("indice_bursatil", 100.0) + variacion + (inversiones_activas * 0.5)
        self.economia["total_dinero"] = total_dinero
        self.economia["inversiones_activas"] = inversiones_activas
        
        # Mantener historial para gráficas
        if "historial_indice" not in self.economia:
            self.economia["historial_indice"] = []
        
        self.economia["historial_indice"].append(round(self.economia["indice_bursatil"], 2))
        if len(self.economia["historial_indice"]) > 50:
            self.economia["historial_indice"].pop(0)

    def step(self):
        """Avanza un paso en la simulación."""
        if getattr(self, '_stopped', False):
            return # No procesar si la simulación fue detenida
        self.paso_actual += 1
        self.grupos_creados_este_paso = 0
        self.log(f"\n================ PASO {self.paso_actual} ================", categoria="paso")
        
        # --- EFECTOS GLOBALES DE GUERRA ---
        if self.guerras_activas:
            self.log(f"⚠️ [MUNDO] Hay {len(self.guerras_activas)} guerra(s) activa(s). La tensión es palpable.", categoria="sistema")
            for a in self.agentes:
                # La guerra reduce la seguridad y aumenta el estrés
                a.necesidades["seguridad"] = max(0, a.necesidades["seguridad"] - 0.2)
                a.necesidades["entretenimiento"] = min(10.0, a.necesidades["entretenimiento"] + 0.1)

        # Actualizar territorios
        self.actualizar_territorios()
        
        # Actualizar clima
        self.actualizar_clima()
        
        # --- PROCESAR EFECTOS DE EDIFICIOS ---
        for edif in self.infraestructura:
            tipo = edif["tipo"]
            x, y = edif["x"], edif["y"]
            
            # Granjas: Generan recursos en el tile
            if tipo == "Granja":
                tile = self.mapa[x][y]
                if not tile.resource_node:
                    tile.resource_node = {"type": "food", "amount": 20}
                else:
                    tile.resource_node["amount"] = min(200, tile.resource_node["amount"] + 10)
            
            # Beneficiarios cercanos a edificios
            agentes_cerca = [a for a in self.agentes if abs(a.x - x) <= 1 and abs(a.y - y) <= 1 and a.esta_vivo]
            for a in agentes_cerca:
                if tipo == "Hospital":
                    a.necesidades["salud"] = min(10.0, a.necesidades["salud"] + 0.5)
                elif tipo == "Centro de Descanso":
                    a.necesidades["descanso"] = min(10.0, a.necesidades["descanso"] + 1.0)
                elif tipo == "Centro de Recarga":
                    a.recursos += 5
                elif tipo == "Centro Comunitario":
                    a.necesidades["social"] = max(0, a.necesidades["social"] - 0.8)
                elif tipo == "Universidad":
                    if random.random() < 0.3:
                        area = random.choice(["medicina", "comercio", "combate", "exploracion", "agricultura", "ingenieria"])
                        a.ganar_experiencia(area, 1)
                elif tipo == "Farmacia":
                    a.necesidades["salud"] = min(10.0, a.necesidades["salud"] + 0.3)
                    if a.recursos < 5: a.recursos += 2 # Ayuda básica
            
            # Minas: Generan piedra/hierro
            if tipo == "Mina":
                tile = self.mapa[x][y]
                if not tile.resource_node:
                    tipo_minero = random.choice(["stone", "stone", "iron"])
                    tile.resource_node = {"type": tipo_minero, "amount": 30}
                else:
                    tile.resource_node["amount"] = min(300, tile.resource_node["amount"] + 15)

        # --- GESTION DEL HISTORIADOR ---
        # Asegurar que siempre haya un historiador vivo y activo
        hist_id = self.historia.historiador_id
        hist_actual = next((a for a in self.agentes if a.unique_id == hist_id and a.esta_vivo), None)
        
        if not hist_actual:
            valid_candidates = [a for a in self.agentes if a.esta_vivo and a.rol != "Historiador"]
            if valid_candidates:
                # Elegir al agente más amable y experimentado socialmente
                h = max(valid_candidates, key=lambda x: x.personalidad.get("amabilidad", 0.5) + (x.experiencia.get("social", 0) / 100))
                self.historia.historiador_id = h.unique_id
                h.rol = "Historiador"
                self.log(f"📚 [CRONICA] El Agente {h.unique_id} asume el mando como Historiador. ¡La historia será escrita!", categoria="sistema")
        elif hist_actual.rol != "Historiador":
            hist_actual.rol = "Historiador"

        # Procesar vida política
        self.gestionar_moderador()
        self.procesar_asambleas()
        self.procesar_propuestas_ley()

        # Actualizar estado fisiológico de todos los agentes
        agentes_vivos = [a for a in self.agentes if a.esta_vivo]
        random.shuffle(agentes_vivos)
        
        for agente in agentes_vivos:
            agente.actualizar_estado()
            agente.decision_cacheada = None

        # --- PROCESAMIENTO SECUENCIAL CON RITMO DE LECTURA ---
        # Cada agente piensa y actúa uno a la vez, con una pausa entre ellos
        # para que el espectador pueda "leer" lo que cada uno dice/hace.
        ritmo = getattr(self, 'ritmo_lectura', 2.0)  # segundos entre agentes
        
        for agente in agentes_vivos:
            if getattr(self, '_force_stop', False):
                break
            agente.step()
            
            # Broadcast incremental: el frontend ve cada agente actuar en tiempo real
            if self.state_change_callback:
                try:
                    self.state_change_callback()
                except Exception:
                    pass
            
            # Pausa de lectura entre agentes
            if ritmo > 0 and len(agentes_vivos) > 1:
                time.sleep(ritmo)
        
        # Lógica de formación de grupos (cada 5 pasos para mayor actividad social)
        if self.paso_actual % 5 == 0:
            self.log("📢 [SISTEMA] Evaluando formación de grupos sociales...", categoria="sistema")
            self.formar_grupos()
            self.asignar_roles_consenso()
            self.evaluar_evolucion_civilizaciones() # NUEVO: Chequeo de evolución
        
        # Economía global
        self.actualizar_economia()
        
        # Registrar estadísticas/métricas para visualización
        if self.agentes:
            recursos_totales = sum(a.recursos for a in self.agentes)
            promedio_recursos = recursos_totales / len(self.agentes)
            
            self.datos.append({
                "paso": self.paso_actual,
                "recursos_promedio": promedio_recursos,
                "num_grupos": len(set(a.grupo_id for a in self.agentes if a.grupo_id is not None)),
                "gini": self.calcular_gini(),
                "felicidad": self.calcular_felicidad_promedio()
            })

        # Guardar estado: JSON cada 5 pasos, PostgreSQL cada 10 pasos
        # (evita bloquear la simulación con I/O en cada paso)
        if self.paso_actual % 5 == 0:
            self.guardar_estado()

        # Verificar misiones activas
        self.misiones_completadas_este_turno = self.sistema_misiones.verificar_misiones(self, self.user_id or "default")
        if self.misiones_completadas_este_turno:
            for mision_completada in self.misiones_completadas_este_turno:
                self.log(
                    f"🎉 ¡MISIÓN COMPLETADA! {mision_completada['titulo']}",
                    categoria="mision_completada"
                )


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
                "requisito": lambda a: a.profesion == "Médico" or a.experiencia.get("medicina", 0) >= 5,
                "efecto": "Cura agentes cercanos cada turno."
            },
            "Granja": {
                "costo": {"dinero": 30, "recursos": 20, "madera": 3},
                "requisito": lambda a: True,
                "efecto": "Genera recursos de alimento en el tile."
            },
            "Centro de Recarga": {
                "costo": {"dinero": 50, "recursos": 40},
                "requisito": lambda a: a.experiencia.get("ingenieria", 0) >= 3,
                "efecto": "Restaura energía/recursos rápidamente."
            },
            "Centro de Descanso": {
                "costo": {"dinero": 20, "recursos": 15},
                "requisito": lambda a: True, # Básico
                "efecto": "Reduce el estrés y la necesidad de descanso."
            },
            "Centro Comunitario": {
                "costo": {"dinero": 40, "recursos": 30},
                "requisito": lambda a: a.personalidad.get("amabilidad", 0.5) > 0.6,
                "efecto": "Mejora las relaciones sociales en el área."
            },
            "Comisaría": {
                "costo": {"dinero": 50, "recursos": 35},
                "requisito": lambda a: a.profesion == "Guarda" or a.experiencia.get("combate", 0) >= 3,
                "efecto": "Reduce la probabilidad de robos y aumenta la seguridad."
            },
            "Universidad": {
                "costo": {"dinero": 150, "recursos": 100, "piedra": 10, "madera": 15},
                "requisito": lambda a: a.experiencia.get("ingenieria", 0) >= 4,
                "efecto": "Permite graduarse a los agentes y otorga XP pasiva."
            },
            "Mina": {
                "costo": {"dinero": 80, "recursos": 40, "madera": 10},
                "requisito": lambda a: a.experiencia.get("ingenieria", 0) >= 4,
                "efecto": "Genera piedra y hierro en montañas."
            },
            "Farmacia": {
                "costo": {"dinero": 40, "recursos": 20, "madera": 4},
                "requisito": lambda a: a.experiencia.get("medicina", 0) >= 3,
                "efecto": "Provee salud básica y medicinas."
            }
        }
        
        if tipo not in config_edificios:
            # Posibilidad de "inventar" un edificio si tiene alta curiosidad e ingeniería
            if agente.experiencia.get("ingenieria", 0) >= 5 and agente.personalidad.get("curiosidad", 0.5) > 0.8:
                config_edificios[tipo] = {
                    "costo": {"dinero": 200, "recursos": 150},
                    "requisito": lambda a: True,
                    "efecto": "Edificio experimental con efectos únicos."
                }
            else:
                return False, "Tipo de edificio no válido o requisitos de invención no cumplidos."
        
        tile = self.mapa[agente.x][agente.y]
        if tile.buildings:
            return False, "Ya hay un edificio en esta ubicación."
            
        if tile.terrain_type == TerrainType.WATER and tipo != "Puerto":
            return False, "No se puede construir en agua (requiere Puerto)."
        if tile.terrain_type == TerrainType.MOUNTAIN and tipo != "Mina":
            return False, "En las montañas solo se pueden construir Minas."
        
        config = config_edificios[tipo]
        if not config["requisito"](agente):
            return False, f"No cumples los requisitos (XP/Profesión) para construir {tipo}."

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
                "y": agente.y
            }
            self.infraestructura.append(nuevo_edif)
            tile.buildings.append(nuevo_edif) # Add to tile
            
            self.log(f"🏗️ [CONSTRUCCION] Agente {agente.unique_id} ha construido un {tipo} en ({agente.x}, {agente.y})!", categoria="sistema")
            return True, f"¡{tipo} construido con éxito!"
        
        return False, "No tienes suficientes recursos o dinero."

    def enviar_mensaje_arquitecto(self, mensaje, agente_id=None):
        """Envía un mensaje del Arquitecto (usuario) a uno o todos los agentes."""
        import time
        payload = {
            "emisor": "Arquitecto",
            "contenido": mensaje,
            "timestamp": time.time()
        }
        
        if agente_id:
            # Mensaje privado
            target = next((a for a in self.agentes if a.unique_id == agente_id), None)
            if target:
                target.mensaje_arquitecto = payload
                self.log(f"🤫 [DIVINO] Mensaje PRIVADO enviado al Agente {agente_id}.", categoria="sistema")
                return True, f"Mensaje enviado al Agente {agente_id}"
            return False, "Agente no encontrado"
        else:
            # Mensaje global (broadcast)
            for a in self.agentes:
                a.mensaje_arquitecto = payload
            self.log(f"📢 [DIVINO] El Arquitecto ha enviado un mensaje GLOBAL: '{mensaje}'", categoria="sistema")
            return True, "Mensaje global enviado"
        
    def set_lore_and_seed(self, lore, seed):
        self.lore = lore
        self.seed = seed
        self.log(f"🌍 [MUNDO] Lore actualizado: {lore[:50]}...", categoria="sistema")

    def get_agent_by_id(self, agent_id):
        """Busca un agente por su ID único."""
        return next((a for a in self.agentes if str(a.unique_id) == str(agent_id)), None)

    def trigger_event(self, tipo, descripcion, duracion=5, impacto=None):
        evento = {
            "tipo": tipo,
            "descripcion": descripcion,
            "paso_inicio": self.paso_actual,
            "pasos_restantes": duracion,
            "impacto": impacto or {}
        }
        self.eventos_activos.append(evento)
        self.log(f"🌪️ [EVENTO GLOBAL] ¡Ha comenzado: {tipo}! {descripcion}", categoria="sistema")
        
        # Guardar en DB si está activa
        if self.db_active:
            query = "INSERT INTO eventos_globales (tipo, descripcion, paso_inicio, duracion, impacto) VALUES (%s, %s, %s, %s, %s)"
            self.db.execute(query, (tipo, descripcion, self.paso_actual, duracion, Json(impacto or {})))

    def spawn_agent(self, config=None):
        """Spawnea un nuevo agente. Puede recibir un objeto AgentConfig o un diccionario."""
        nuevo_id = f"A{len(self.agentes)}"
        
        personalidad_final = None
        recursos_init = 0.0
        dinero_init = 100.0
        pos_init = None

        if config:
            # Manejar tanto objetos Pydantic como diccionarios
            if hasattr(config, "model_dump"):
                cfg_dict = config.model_dump()
            elif isinstance(config, dict):
                cfg_dict = config
            else:
                cfg_dict = vars(config) if hasattr(config, "__dict__") else {}

            personalidad_final = cfg_dict.get("personality")
            recursos_init = cfg_dict.get("resources", 0.0)
            dinero_init = cfg_dict.get("money", 100.0)
            pos_init = cfg_dict.get("position")

        nuevo_agente = Agente(nuevo_id, self, personalidad=personalidad_final)
        nuevo_agente.recursos = recursos_init
        nuevo_agente.dinero = dinero_init
        
        if pos_init and "x" in pos_init and "y" in pos_init:
            nuevo_agente.x = pos_init["x"]
            nuevo_agente.y = pos_init["y"]
            
        self.agentes.append(nuevo_agente)
        self.log(f"✨ [SPAWNER] Nuevo agente {nuevo_id} ha entrado al mundo.", categoria="sistema")
        
        if self.db_active:
            self.db.save_agent(nuevo_agente, self.user_id)
            
        return nuevo_agente

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
             if "cantidad" not in objetivo: objetivo["cantidad"] = 1
             if "actual" not in objetivo: objetivo["actual"] = 0
             
        mision = Mision(
            id=mision_id,
            titulo=titulo,
            descripcion=descripcion,
            tipo=tipo,
            dificultad="media",
            objetivo=objetivo,
            recompensa_puntos=puntos,
            turno_inicio=self.paso_actual
        )
        
        self.sistema_misiones.misiones_activas.append(mision)
        self.log(f"🎯 [DIVINO] Nueva misión encomendada: '{titulo}'", categoria="sistema")
        
        if self.db_active:
            self.db.save_mission(mision, self.user_id)
            
        return True, f"Misión '{titulo}' creada"

    def gestionar_encuentro_facciones(self, agente_a, agente_b):
        """Gestiona la interacción cuando dos agentes de distintas facciones se encuentran."""
        id_a, id_b = agente_a.grupo_id, agente_b.grupo_id
        if not id_a or not id_b or id_a == id_b: return
        
        # Clave única para la relación entre estos dos grupos
        rel_key = tuple(sorted([id_a, id_b]))
        if rel_key not in self.relaciones_grupos:
            self.relaciones_grupos[rel_key] = 0.5 # Neutral inicial
            
        afinidad = self.relaciones_grupos[rel_key]
        
        # Probabilidad de cooperación basada en afinidad y personalidades
        prob_cooperar = afinidad * (agente_a.personalidad["amabilidad"] + agente_b.personalidad["amabilidad"]) / 2
        
        if random.random() < prob_cooperar:
            # --- COOPERACIÓN: Gesto de Buena Voluntad ---
            tipo_ayuda = random.choice(["recursos", "salud", "informacion"])
            if tipo_ayuda == "recursos" and agente_a.recursos > 20:
                donado = 10
                agente_a.recursos -= donado
                agente_b.recursos += donado
                self.log(f"🤝 [DIPLOMACIA] Gesto de paz: {agente_a.unique_id} ({id_a}) donó recursos a {agente_b.unique_id} ({id_b}).", categoria="social")
                self.relaciones_grupos[rel_key] = min(1.0, afinidad + 0.05)
            elif tipo_ayuda == "salud" and agente_a.inventario["medicina"] > 0:
                agente_a.inventario["medicina"] -= 1
                agente_b.necesidades["salud"] = min(10, agente_b.necesidades["salud"] + 2)
                self.log(f"💊 [DIPLOMACIA] Auxilio médico: {agente_a.unique_id} ({id_a}) curó a un miembro de {id_b}.", categoria="social")
                self.relaciones_grupos[rel_key] = min(1.0, afinidad + 0.1)
        else:
            # --- TENSIÓN: Competencia por territorio ---
            if random.random() < 0.3:
                self.log(f"⚠️ [TENSION] Encuentro frío entre patrullas de {id_a} y {id_b} en zona fronteriza.", categoria="social")
                self.relaciones_grupos[rel_key] = max(0.0, afinidad - 0.02)

    @synchronized
    def log(self, mensaje, categoria="info", subtitulos=None, tts_text=None, pensamiento=None, privado_para=None):
        """Envía un log al callback o a la terminal y lo guarda en el historial."""
        log_entry = {
            "paso": self.paso_actual,
            "mensaje": mensaje,
            "categoria": categoria,
            "subtitulos": subtitulos,
            "tts_text": tts_text,
            "pensamiento": pensamiento,
            "privado_para": privado_para
        }
        with self.lock:
            self.historial_logs.append(log_entry)
            if len(self.historial_logs) > 1000: # Mantener los últimos 1000 en RAM para sincronización inicial
                self.historial_logs.pop(0)

        # PERSISTENCIA EN DB
        if self.db_active and self.user_id:
            try:
                self.db.save_log(
                    self.user_id, self.paso_actual, mensaje, categoria, 
                    pensamiento, privado_para, subtitulos, tts_text
                )
            except Exception as e:
                logger.error(f"Error guardando log en DB: {e}")

        print(f"[LOG DEBUG] categoria={categoria}, mensaje={mensaje[:80]}...")
        
        if self.log_callback:
            # El callback puede no ser thread-safe (especialmente si encola en asyncio), 
            # pero ya lo manejamos con run_coroutine_threadsafe en api.py
            self.log_callback(mensaje, categoria, subtitulos, tts_text, pensamiento, privado_para)
        else:
            print(mensaje)
            if subtitulos:
                print(f"             └─ [Subtítulos: {subtitulos}]")

    def actualizar_relacion_grupal(self, g1, g2, cambio):
        """Actualiza la afinidad entre dos facciones."""
        if not g1 or not g2 or g1 == g2: return
        
        pair = tuple(sorted([str(g1), str(g2)]))
        actual = self.relaciones_grupos.get(pair, 0.0)
        nueva = max(-1.0, min(1.0, actual + cambio))
        self.relaciones_grupos[pair] = nueva
        self.notificar_cambio_estado() # Cambio en diplomacia
        
        if actual >= 0 and nueva < 0:
            self.log(f"⚠️ [DIPLOMACIA] Las facciones {g1} y {g2} han entrado en CONFLICTO.", categoria="sistema")
        elif actual < 0 and nueva >= 0:
            self.log(f"🕊️ [DIPLOMACIA] Las facciones {g1} y {g2} han firmado la PAZ.", categoria="sistema")

    def declarar_guerra(self, g1, g2):
        """Inicia un estado de guerra formal entre dos facciones."""
        if not g1 or not g2 or g1 == g2: return False, "Facciones inválidas."
        pair = tuple(sorted([str(g1), str(g2)]))
        if pair in self.guerras_activas:
            return False, "Ya existe un estado de guerra."
        
        self.guerras_activas.append(pair)
        self.relaciones_grupos[pair] = -1.0 # Odio absoluto
        self.log(f"⚔️ [GUERRA] ¡La facción {g1} ha DECLARADO LA GUERRA a {g2}!", categoria="conflict")
        
        # Registro histórico
        self.historia.agregar_hito({
            "turno": self.paso_actual,
            "descripcion": f"Conflicto total: La facción {g1} ha declarado oficialmente la guerra a {g2}.",
            "tipo": "conflicto"
        })
        
        self.notificar_cambio_estado()
        return True, f"Guerra declarada contra {g2}."

    def finalizar_guerra(self, g1, g2):
        """Termina un estado de guerra entre dos facciones."""
        pair = tuple(sorted([str(g1), str(g2)]))
        if pair not in self.guerras_activas:
            return False, "No hay una guerra activa entre estas facciones."
        
        self.guerras_activas.remove(pair)
        self.relaciones_grupos[pair] = 0.0 # Neutralidad post-guerra
        self.log(f"🕊️ [TRATADO] Se ha firmado un armisticio entre {g1} y {g2}. La guerra ha terminado.", categoria="consenso")
        
        # Registro histórico
        self.historia.agregar_hito({
            "turno": self.paso_actual,
            "descripcion": f"La paz ha vuelto: Se ha firmado un armisticio entre {g1} y {g2}.",
            "tipo": "paz"
        })

        self.notificar_cambio_estado()
        return True, f"Paz firmada con {g2}."
    def calcular_gini(self):
        """Calcula el coeficiente de Gini para la desigualdad de recursos."""
        recursos = sorted([a.recursos + a.dinero for a in self.agentes])
        n = len(recursos)
        if n == 0 or sum(recursos) == 0: return 0
        
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
            promedio_nec = sum([nec.get(k, 0) for k in ["alimento", "social", "seguridad", "descanso", "entretenimiento"]]) / 5
            felicidad = max(0, 10 - promedio_nec)
            felicidades.append(felicidad)
        return round(sum(felicidades) / len(felicidades), 2) if felicidades else 0

    def track_conflictos(self):
        """Retorna la tasa de conflictos reciente (últimos logs)."""
        conflictos = [l for l in self.historial_logs[-20:] if l['categoria'] == 'conflict']
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
                amigos = [n for n in agente.memoria.grafo.neighbors(agente.unique_id) 
                          if agente.memoria.obtener_tipo(n) == "amigo"]
                # También considerar conocidos con alta fuerza de relación
                conocidos = [n for n in agente.memoria.grafo.neighbors(agente.unique_id) 
                           if agente.memoria.obtener_tipo(n) == "conocido" 
                           and agente.memoria.obtener_fuerza(n) > 0.3]
                
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
                        color_clan = self.colores_paleta[hash(nuevo_id) % len(self.colores_paleta)]
                        
                        self.civilizaciones[nuevo_id] = Civilizacion(
                            id=nuevo_id,
                            nombre=nombre_clan,
                            color=color_clan,
                            user_id=self.user_id
                        )
                        self.objetivos_grupos[nuevo_id] = f"Cooperación de {nombre_clan}"
                        
                        # Unir a los amigos y conocidos
                        todos = amigos + conocidos
                        for id_rel in todos[:5]:  # Máximo 5 miembros iniciales
                            rel_obj = self.get_agent_by_id(id_rel)
                            if rel_obj:
                                rel_obj.grupo_id = nuevo_id
                                rel_obj.civilizacion_id = nuevo_id

                        self.log(f"🚩 [CLAN] Se ha formado un nuevo clan: '{nombre_clan}' liderado por {agente.unique_id}.", categoria="consenso")
                        self.notificar_cambio_estado()
                        self.grupos_creados_este_paso += 1

    def ejecutar(self, pasos=50):
        print("\n" + "═"*60)
        print("🚀 MISIÓN INICIAL: CREACIÓN DE IDIOMA EMERGENTE")
        print("Los agentes han decidido establecer un protocolo de comunicación")
        print("basado en glifos y símbolos para coordinar su sociedad.")
        print("═"*60 + "\n")
        
        self.log(f"Iniciando simulación con {len(self.agentes)} agentes por {pasos} pasos...", categoria="sistema")
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
        color = 'tab:blue'
        ax1.set_xlabel('Paso')
        ax1.set_ylabel('Recursos Promedio', color=color)
        ax1.plot(df['paso'], df['recursos_promedio'], color=color, label='Recursos', linewidth=2)
        ax1.tick_params(axis='y', labelcolor=color)

        # Eje secundario: Relaciones
        ax2 = ax1.twinx()
        color_amigos = 'tab:green'
        color_enemigos = 'tab:red'
        ax2.set_ylabel('Cantidad de Relaciones / Grupos', color='black')
        ax2.plot(df['paso'], df['amigos_total'], color=color_amigos, linestyle='--', label='Amigos')
        ax2.plot(df['paso'], df['enemigos_total'], color=color_enemigos, linestyle=':', label='Enemigos')
        ax2.plot(df['paso'], df['num_groups'] if 'num_groups' in df else df['num_grupos'], color='purple', label='Grupos', alpha=0.5)
        ax2.tick_params(axis='y', labelcolor='black')

        plt.title('Evolución de la Sociedad de Agentes')
        
        # Combinar leyendas de ambos ejes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        
        # Forzar el renderizado antes de guardar
        plt.savefig('resultado_simulacion.png', dpi=100, bbox_inches='tight')
        plt.close() # Limpiar memoria
        print("Gráfico guardado exitosamente como 'resultado_simulacion.png' 📊")

    def imprimir_resumen_social(self):
        print("\n--- RESUMEN SOCIAL FINAL ---")
        # Líderes por rango
        lideres = sorted(self.agentes, key=lambda a: a.rango, reverse=True)[:3]
        print("\nTop 3 Agentes con mayor Rango (Estatus):")
        for l in lideres:
            print(f"  - Agente {l.unique_id}: Rango {l.rango:.2f}, Recursos {l.recursos:.2f}, Grupo: {l.grupo_id}")
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
        """Guarda el estado actual en JSON (fallback) y PostgreSQL."""
        if getattr(self, '_force_stop', False):
            return
        # 1. Guardar en JSON (Fallback, solo si hay user_id)
        if not self.user_id:
            return # No guardar archivo JSON si no hay un ID de usuario asociado

        filename = f"estado_simulacion_{self.user_id}.json"

        datos_json = {
            "paso_actual": self.paso_actual,
            "lore": getattr(self, 'lore', ''),
            "seed": getattr(self, 'seed', ''),
            "objetivos_grupos": self.objetivos_grupos,
            "misiones": [m.to_dict() for m in (self.sistema_misiones.misiones_activas + self.sistema_misiones.misiones_completadas)],
            "datos_estadisticos": self.datos,
            "historia": self.historia.to_dict(),
            "agentes": []
        }
        for a in self.agentes:
            datos_json["agentes"].append({
                "id": a.unique_id,
                "recursos": a.recursos,
                "dinero": a.dinero,
                "necesidades": a.necesidades,
                "personalidad": a.personalidad,
                "rol": a.rol,
                "grupo_id": a.grupo_id,
                "rango": a.rango,
                "conocimientos": a.conocimientos,
                "planes": a.planes,
                "inversiones": a.inversiones,
                "alianzas": a.alianzas,
                "tratados": a.tratados,
                "profesion": a.profesion,
                "experiencia": a.experiencia,
                "hitos": a.hitos,
                "x": a.x,
                "y": a.y,
                "memoria_grafica": a.memoria.exportar_datos()
            })
        
        datos_json["economia"] = self.economia
        datos_json["relaciones_grupos"] = {f"{k[0]}-{k[1]}": v for k, v in self.relaciones_grupos.items()}
        datos_json["historial_logs"] = self.historial_logs
        datos_json["infraestructura"] = self.infraestructura
        # Serializar mapa de objetos Tile
        datos_json["mapa"] = [[t.to_dict() for t in row] for row in self.mapa]
        datos_json["civilizaciones"] = {k: {
            "nombre": v.nombre,
            "color": v.color,
            "user_id": v.user_id,
            "recursos_globales": v.recursos_globales,
            "territorio": v.territorio
        } for k, v in self.civilizaciones.items()}
        
        # NUEVO: Guardar leyes y asambleas en JSON
        datos_json["leyes_globales"] = self.leyes_globales
        datos_json["facciones_leyes"] = self.facciones_leyes
        datos_json["asambleas_globales"] = self.asambleas_globales
        
        with open(filename, "w") as f:
            json.dump(datos_json, f, indent=4, cls=DateTimeEncoder)

        
        # 2. Guardar en PostgreSQL (Si está activo)
        if self.db_active and self.user_id:
            try:
                # Convertir claves de tupla a string para JSON
                rel_str = {f"{k[0]}:{k[1]}": v for k, v in self.relaciones_grupos.items()}
                
                # Guardar estado del mundo con user_id y relaciones persistentes
                self.db.save_world_state(
                    self.user_id, self.paso_actual, getattr(self, 'lore', ''), 
                    getattr(self, 'seed', ''), self.economia, rel_str, 
                    self.objetivos_grupos, datos_json["mapa"], self.infraestructura,
                    datos_json["historia"]
                )
                
                # Guardar civilizaciones
                for civ in self.civilizaciones.values():
                    self.db.save_civilization(civ)
                
                # --- NUEVO: Estrategia de dos pases para integridad referencial ---
                # 1. Guardar todos los AGENTES primero
                for a in self.agentes:
                    self.db.save_agent(a, self.user_id)
                
                # 2. Guardar todas las MEMORIAS después
                agentes_validos = {a.unique_id for a in self.agentes}
                total_memorias = 0
                for a in self.agentes:
                    mem_data = a.memoria.exportar_datos()
                    for edge in mem_data.get('aristas', []):
                        if edge['u'] == a.unique_id:
                            target_id = edge['v']
                            if target_id in agentes_validos:
                                # edge['data'] ahora contiene recursos_vistos y grupo gracias al fix en MemoriaGrafica
                                self.db.save_memory(a.unique_id, target_id, edge['data'], self.user_id)
                                total_memorias += 1
                
                if total_memorias > 0:
                    logger.info(f"🧠 [DB] Persistidas {total_memorias} relaciones de memoria para {self.user_id}")
                
                # Guardar Leyes y Propuestas
                for ley in self.leyes_globales:
                    self.db.save_proposal(ley, self.user_id)
                for grupo_id, leyes in self.facciones_leyes.items():
                    for ley in leyes:
                        ley_copy = ley.copy()
                        ley_copy['grupo_id'] = grupo_id
                        self.db.save_proposal(ley_copy, self.user_id)
                for asamblea in self.asambleas_globales:
                    prop = {
                        "proponente_id": asamblea["proponente_id"], "texto": asamblea["tema"],
                        "tipo": "asamblea", "votos": {"si": asamblea["votos_si"], "no": asamblea["votos_no"]},
                        "estado": asamblea["estado"], "paso_creacion": asamblea["paso_inicio"]
                    }
                    self.db.save_proposal(prop, self.user_id)

                # Guardar Misiones y Puntajes (NUEVO)
                for mision in self.sistema_misiones.misiones_activas:
                    self.db.save_mission(mision, self.user_id)
                for mision in self.sistema_misiones.misiones_completadas:
                    self.db.save_mission(mision, self.user_id)
                
                puntos_actuales = self.sistema_misiones.obtener_puntaje(self.user_id)
                self.db.save_score(self.user_id, puntos_actuales)

                logger.info(f"💾 [DB] Estado Global, Leyes y Misiones guardados en PostgreSQL para {self.user_id}")
            except Exception as e:
                logger.error(f"❌ Error guardando en DB: {e}")

    def cargar_estado(self):
        """Carga el estado desde PostgreSQL (prioridad) o JSON (fallback)."""
        # 1. Intentar cargar desde PostgreSQL
        if self.db_active:
            try:
                # Obtener el user_id (podría venir de la sesión si esto fuera asíncrono, 
                # pero aquí intentamos deducirlo o usar uno por defecto temporal)
                target_user_id = self.user_id or "USER-DEFAULT"
                
                # 1. Cargar metadatos globales
                world_state = self.db.get_world_state(target_user_id)
                if world_state:
                    self.paso_actual, self.lore, self.seed, precio, indice, total_dinero, rel_data, obj_grupos, mapa_data, infra_data, historia_data = world_state
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
                        # Inicializar mapa vacío antes de cargar
                        self.mapa = [[Tile(x, y) for y in range(self.mapa_size)] for x in range(self.mapa_size)]
                        
                        for x in range(self.mapa_size):
                            for y in range(self.mapa_size):
                                if x < len(mapa_data) and y < len(mapa_data[x]):
                                    d = mapa_data[x][y]
                                    # Asegurar que d sea un diccionario válido
                                    if isinstance(d, dict) and "terrain" in d:
                                        tile = Tile(d.get("x", x), d.get("y", y), d["terrain"])
                                        tile.resource_node = d.get("resource")
                                        tile.owner_civ_id = d.get("owner")
                                        tile.buildings = d.get("buildings", [])
                                        self.mapa[x][y] = tile

                    # Restaurar relaciones de grupos
                    if rel_data:
                        self.relaciones_grupos = {}
                        for k, v in rel_data.items():
                            parts = k.split(":")
                            if len(parts) == 2:
                                self.relaciones_grupos[tuple(parts)] = v

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
                            id=m_row[0], titulo=m_row[1], descripcion=m_row[2],
                            tipo=m_row[3], dificultad=m_row[4], objetivo=m_row[5],
                            recompensa_puntos=m_row[6], estado=m_row[7],
                            turno_inicio=m_row[8], turno_limite=m_row[9],
                            completada_por=m_row[10], turno_completada=m_row[11]
                        )
                        if mision.estado == "completada":
                            self.sistema_misiones.misiones_completadas.append(mision)
                        else:
                            self.sistema_misiones.misiones_activas.append(mision)
                else:
                    logger.info("🎯 No se encontraron misiones en DB. Inicializando misiones por defecto.")
                    self.sistema_misiones.inicializar_misiones_iniciales(self.paso_actual)
                
                puntos = self.db.get_score(target_user_id)
                self.sistema_misiones.puntajes_usuarios[target_user_id] = puntos

                # 3. Cargar Agentes
                agents_data = self.db.get_agents(target_user_id)
                self.agentes = []
                for row in agents_data:
                    # id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, civ_id, alianzas, tratados, memoria_mensajes, x, y, skills, skill_factor, timestamp
                    a_id, _, rec, din, g_id, rol, prof, ran, rep, pers, nec, exp, con, inv, hitos, etico, civ_id, alianzas, tratados, mem_msgs, loaded_x, loaded_y, skills_db, s_factor, _ = row
                    a = Agente(a_id, self)
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
                    # Asegurar que experiencia tenga todas las categorías
                    exp_default = {"medicina": 0, "comercio": 0, "combate": 0, "exploracion": 0, "social": 0, "ingenieria": 0, "agricultura": 0}
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
                    if mem_msgs:
                        a.memoria.historial_mensajes = mem_msgs
                    
                    # Cargar memorias
                    memories = self.db.get_memories(a_id, target_user_id)
                    mem_dict = {"nodos": [{"id": a_id, "data": {"tipo": "yo"}}], "aristas": []}
                    for m_row in memories:
                        target_id, tipo, fuerza, rec_v, grp_v = m_row
                        mem_dict["nodos"].append({"id": target_id, "data": {"tipo": tipo, "recursos_vistos": rec_v, "grupo": grp_v}})
                        mem_dict["aristas"].append({"u": a_id, "v": target_id, "data": {"tipo": tipo, "fuerza": fuerza}})
                    
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
                        p_id, g_id, prop_id, texto, p_tipo, votos, estado, paso_p, titulo, contenido = p_row
                        prop = {
                            "id": p_id, "proponente_id": prop_id, "texto": texto, 
                            "tipo": p_tipo, "votos": votos, "estado": estado, "paso_creacion": paso_p,
                            "titulo": titulo, "contenido": contenido, "db_id": p_id
                        }
                        
                        if p_tipo == "asamblea" and estado != "FINALIZADA":
                            asamblea = {
                                "id": f"ASAMBLEA-{p_id}", "proponente_id": prop_id, "tema": texto,
                                "moderador_id": prop_id, "votos_si": votos.get("si", 0),
                                "votos_no": votos.get("no", 0), "votantes": [], "estado": estado,
                                "paso_inicio": paso_p, "pasos_restantes": 5
                            }
                            self.asambleas_globales.append(asamblea)
                        elif estado == "pendiente":
                            if "propuestas" not in self.facciones_leyes: self.facciones_leyes["propuestas"] = []
                            self.facciones_leyes["propuestas"].append(prop)
                        elif estado == "aprobada":
                            if g_id and g_id != "GLOBAL":
                                if g_id not in self.facciones_leyes: self.facciones_leyes[g_id] = []
                                self.facciones_leyes[g_id].append(prop)
                            else:
                                self.leyes_globales.append(prop)

                # 5. Cargar Logs de la sesión
                logs_db = self.db.get_logs(target_user_id, limit=1000)
                if logs_db:
                    self.historial_logs = []
                    for pr in logs_db:
                        # paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id
                        p, msg, cat, thoughts, priv, subs, tts, _ = pr
                        self.historial_logs.append({
                            "paso": p, "mensaje": msg, "categoria": cat, 
                            "pensamiento": thoughts, "privado_para": priv, 
                            "subtitulos": subs, "tts_text": tts
                        })
                    logger.info(f"📜 [DB] {len(self.historial_logs)} logs cargados de la base de datos.")
                
                # Garantizar que las misiones base existan si no se cargaron de la DB
                if not self.sistema_misiones.misiones_activas and not self.sistema_misiones.misiones_completadas:
                    logger.info("🆕 No se encontraron misiones en DB. Inicializando misiones base...")
                    self.sistema_misiones.inicializar_misiones_iniciales(self.paso_actual)

                self.agentes_cargados = True
                logger.info(f"💾 [DB] Estado y Misiones cargados desde PostgreSQL para {target_user_id}")
                return
            except Exception as e:
                logger.error(f"❌ Error cargando desde DB: {e}")

        # 2. Fallback a JSON
        filename = f"estado_simulacion_{target_user_id}.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    datos_json = json.load(f) # Renamed 'datos' to 'datos_json' for clarity
                
                self.paso_actual = datos_json.get("paso_actual", 0)
                self.lore = datos_json.get("lore", "")
                self.seed = datos_json.get("seed", "")
                self.objetivos_grupos = datos_json.get("objetivos_grupos", {})
                self.datos = datos_json.get("datos_estadisticos", [])
                self.economia = datos_json.get("economia", self.economia)
                self.economia = datos_json.get("economia", self.economia)
                self.historial_logs = datos_json.get("historial_logs", [])
                self.infraestructura = datos_json.get("infraestructura", [])
                
                if "historia" in datos_json:
                    self.historia.cargar_desde_dict(datos_json["historia"])
                
                # Cargar mapa
                mapa_data = datos_json.get("mapa")
                if mapa_data and isinstance(mapa_data[0][0], dict):
                    # Cargar desde dicts
                    for x in range(self.mapa_size):
                        for y in range(self.mapa_size):
                            d = mapa_data[x][y]
                            tile = Tile(d["x"], d["y"], d["terrain"])
                            tile.resource_node = d.get("resource")
                            tile.owner_civ_id = d.get("owner")
                            tile.buildings = d.get("buildings", [])
                            self.mapa[x][y] = tile
                else:
                    # Regenerar si es formato antiguo o no existe
                    self.mapa = self.generar_mapa()
                
                civs_data = datos_json.get("civilizaciones", {})
                for civ_id, data in civs_data.items():
                    civ = Civilizacion(civ_id, data["nombre"], data["color"], data.get("user_id"))
                    civ.recursos_globales = data.get("recursos_globales", 0.0)
                    civ.territorio = data.get("territorio", [])
                    self.civilizaciones[civ_id] = civ

                # Cargar Misiones desde JSON
                misiones_data = datos_json.get("misiones", [])
                if misiones_data:
                    self.sistema_misiones.misiones_activas = []
                    self.sistema_misiones.misiones_completadas = []
                    for m_data in misiones_data:
                        # Crear la misión de forma robusta
                        mision = Mision.from_dict(m_data)
                        if mision.estado == "completada":
                            self.sistema_misiones.misiones_completadas.append(mision)
                        else:
                            self.sistema_misiones.misiones_activas.append(mision)
                
                # Garantizar que las misiones base existan si no se cargaron del JSON
                if not self.sistema_misiones.misiones_activas and not self.sistema_misiones.misiones_completadas:
                    logger.info("🆕 No se encontraron misiones en JSON. Inicializando misiones base...")
                    self.sistema_misiones.inicializar_misiones_iniciales(self.paso_actual)

                for a_data in datos_json.get("agentes", []):
                    a = Agente(a_data["id"], self)
                    a.recursos = a_data.get("recursos", 10.0)
                    a.dinero = a_data.get("dinero", 100.0)
                    
                    # Cargar necesidades con valores por defecto para evitar KeyErrors
                    necesidades_base = {
                        "alimento": 8.0, "social": 8.0, "seguridad": 8.0,
                        "descanso": 10.0, "entretenimiento": 8.0, "salud": 10.0
                    }
                    a.necesidades = {**necesidades_base, **a_data.get("necesidades", {})}
                    
                    # Cargar personalidad con valores por defecto
                    personalidad_base = {
                        "extroversión": 0.5, "amabilidad": 0.5, "competitividad": 0.5,
                        "curiosidad": 0.5, "lealtad": 0.5, "prudencia": 0.5
                    }
                    a.personalidad = {**personalidad_base, **a_data.get("personalidad", {})}
                    
                    a.rol = a_data.get("rol", "Ciudadano")
                    a.grupo_id = a_data.get("grupo_id")
                    a.rango = a_data.get("rango", 1.0)
                    a.conocimientos = a_data.get("conocimientos", {})
                    a.planes = a_data.get("planes", [])
                    a.inversiones = a_data.get("inversiones", [])
                    a.alianzas = a_data.get("alianzas", [])
                    a.tratados = a_data.get("tratados", [])
                    a.profesion = a_data.get("profesion")
                    a.experiencia = a_data.get("experiencia", {"medicina": 0, "comercio": 0, "combate": 0, "exploracion": 0, "social": 0, "ingenieria": 0, "agricultura": 0})
                    a.hitos = a_data.get("hitos", [])
                    
                    if "memoria_grafica" in a_data:
                        a.memoria.cargar_datos(a_data["memoria_grafica"])
                    self.agentes.append(a)
                
                # RESTAURAR LEYES Y ASAMBLEAS DESDE JSON
                self.leyes_globales = datos_json.get("leyes_globales", [])
                self.facciones_leyes = datos_json.get("facciones_leyes", {})
                self.asambleas_globales = datos_json.get("asambleas_globales", [])
                
                self.economia = datos_json.get("economia", self.economia)
                self.historial_logs = datos_json.get("historial_logs", [])
                
                # Cargar relaciones grupales (convertir keys de string a tupla)
                rel_data = datos_json.get("relaciones_grupos", {})
                for k, v in rel_data.items():
                    try:
                        p1, p2 = k.split("-")
                        self.relaciones_grupos[(p1, p2)] = v
                    except: pass

                self.agentes_cargados = True
                self.log(f"💾 [SISTEMA] Estado cargado desde JSON (Paso {self.paso_actual}).", categoria="sistema")
            except Exception as e:
                self.log(f"⚠️ [ERROR] No se pudo cargar el estado desde JSON: {e}", categoria="sistema")
                self.agentes_cargados = False

    def asignar_roles_consenso(self):
        """Los grupos negocian roles internos basados en méritos y personalidad."""
        grupos = {}
        for a in self.agentes:
            if a.grupo_id is not None:
                if a.grupo_id not in grupos: grupos[a.grupo_id] = []
                grupos[a.grupo_id].append(a)
        
        for g_id, miembros in grupos.items():
            if len(miembros) < 2: continue
            
            # --- FASE DE ASAMBLEA ---
            self.log(f"🏛️ [ASAMBLEA FACCIÓN {g_id}] Los miembros se reúnen para debatir el futuro...", categoria="consenso")
            
            # Verificar si hay propuestas de liderazgo activas o si no hay líder
            lider_actual = next((m for m in miembros if m.rol == "Líder"), None)
            
            if not lider_actual:
                self.log(f"🔸 [ASAMBLEA] La Facción {g_id} no tiene un líder claro. Se anima a los miembros a presentar sus programas (PROPONER_LEY:local:LIDERAZGO:Nombre:Plan).", categoria="consenso")
                # El cerebro LLM decidirá proponerse como líder en su turno si tiene la ambición
            
            ids_miembros = [m.unique_id for m in miembros]
            lider_id = lider_actual.unique_id if lider_actual else "Ninguno"
            for m in miembros:
                ctx = f"El líder actual es {lider_id}. La facción busca consolidar su poder." if lider_actual else "No hay líder. Es momento de proponerse o buscar consensos para elegir uno."
                # Los agentes aprovechan la asamblea para expresar pensamientos generales
                argumento, pensamiento = cerebro_llm.generar_debate_consenso(m, ids_miembros, fase="asamblea", contexto_extra=ctx)
                if argumento:
                    m.decir(f"🗣️ [OPINION ASAMBLEA] {argumento}", pensamiento=pensamiento, para_grupo=True)


if __name__ == "__main__":
    # Configuración desde .env
    num_agentes = int(os.getenv("NUM_AGENTES", 30))
    pasos = int(os.getenv("PASOS_SIMULACION", 100))
    
    # Configuración de la simulación
    modelo = ModeloRelacional(num_agentes=num_agentes)
    modelo.ejecutar(pasos=pasos)
    modelo.imprimir_resumen_social()
    modelo.visualizar_resultados()
