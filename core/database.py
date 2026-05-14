import os
import uuid
import json
import logging
import psycopg2
import bcrypt
import threading
from typing import List, Dict, Any, Optional
from core.utils import Json, logger

class DatabaseManager:
    """Administrador de la persistencia en PostgreSQL para MundoIA."""
    _initialized = False

    def __init__(self):
        self.conn_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "database": os.getenv("DB_NAME", "mundoia"),
            "user": os.getenv("DB_USER", "architect"),
            "password": os.getenv("DB_PASS", "mundoia_secret_2026"),
            "port": os.getenv("DB_PORT", "5434"),
        }
        self.conn = None
        self.lock = threading.RLock()

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
        """Inicializa las tablas de la base de datos usando restore_schema.sql"""
        if not self.conn:
            return False
        
        if DatabaseManager._initialized:
            return True

        try:
            # El directorio base es el que contiene multiagent_simulation
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            schema_path = os.path.join(base_dir, "scripts", "restore_schema.sql")
            
            if os.path.exists(schema_path):
                with open(schema_path, "r") as f:
                    schema_sql = f.read()

                logger.info(f"📜 Ejecutando esquema desde: {schema_path}")
                with self.conn.cursor() as cur:
                    cur.execute(schema_sql)
                logger.info("✅ Esquema verificado/inicializado.")
            else:
                logger.warning(f"⚠️ No se encontró restore_schema.sql en {schema_path}")

            # Migraciones automáticas adicionales para asegurar que todas las columnas existan
            try:
                with self.conn.cursor() as cur:
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS alma JSONB DEFAULT '{}';")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS identidad JSONB DEFAULT '{}';")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS apps JSONB DEFAULT '{}';")
                    
                    # Aumentar tamaño de user_id para soportar slots largos
                    tables_to_alter = [
                        "agentes", "civilizaciones", "memorias", "chat_mensajes", 
                        "logs_simulacion", "propuestas", "misiones", "estado_mundo", 
                        "instituciones", "puntajes_usuarios", "posts_sociales", "eventos_globales"
                    ]
                    for table in tables_to_alter:
                        try:
                            cur.execute(f"ALTER TABLE {table} ALTER COLUMN user_id TYPE VARCHAR(100);")
                        except Exception:
                            pass
                    
                    # También en la tabla usuarios por si acaso
                    try:
                        cur.execute("ALTER TABLE usuarios ALTER COLUMN id TYPE VARCHAR(100);")
                    except Exception:
                        pass
                    # Añadir columna puntos a instituciones si no existe (migración ligera)
                    cur.execute("ALTER TABLE instituciones ADD COLUMN IF NOT EXISTS puntos numeric DEFAULT 0;")

                    # Migración Lider -> Vocero
                    try:
                        # Si existe lider_id pero no vocero_id, renombrar
                        cur.execute("""
                            DO $$ 
                            BEGIN 
                                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='instituciones' AND column_name='lider_id') 
                                AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='instituciones' AND column_name='vocero_id') THEN
                                    ALTER TABLE instituciones RENAME COLUMN lider_id TO vocero_id;
                                END IF;
                            END $$;
                        """)
                        # Asegurar que vocero_id existe
                        cur.execute("ALTER TABLE instituciones ADD COLUMN IF NOT EXISTS vocero_id VARCHAR(50);")
                    except Exception as e:
                        logger.warning(f"Error migrando lider_id a vocero_id: {e}")

                    # FIX: Asegurar que propuestas.id tenga un default si no es SERIAL (evita error null value)
                    try:
                        cur.execute("""
                            DO $$ 
                            BEGIN 
                                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='propuestas') THEN
                                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                                   WHERE table_name='propuestas' AND column_name='id' 
                                                   AND column_default IS NOT NULL) THEN
                                        CREATE SEQUENCE IF NOT EXISTS propuestas_id_seq;
                                        ALTER TABLE propuestas ALTER COLUMN id SET DEFAULT nextval('propuestas_id_seq')::text;
                                    END IF;
                                END IF;
                            END $$;
                        """)
                    except Exception as e:
                        logger.warning(f"Error asegurando default en propuestas.id: {e}")

                    self.conn.commit()
                    DatabaseManager._initialized = True
            except Exception as e:
                logger.warning(f"Error en migraciones menores: {e}")
                self.conn.rollback()

            return True
        except Exception as e:
            logger.error(f"❌ Error inicializando esquema DB: {e}")
            return False
    def execute(self, query, params=None):
        with self.lock:
            if not self.conn:
                return None
            try:
                with self.conn.cursor() as cur:
                    cur.execute(query, params)
                    if cur.description:
                        return cur.fetchall()
                    # Para INSERT/UPDATE/DELETE sin RETURNING, devolver True
                    if self.conn.autocommit:
                        return True
                return True
            except Exception as e:
                logger.error(f"❌ Error ejecutando query: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def create_user(self, username, password, user_id=None):
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
        query = "SELECT id, password_hash FROM usuarios WHERE username = %s;"
        result = self.execute(query, (username,))
        if result:
            user_id, hashed_password = result[0]
            if bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8")):
                return user_id
        return None

    def ensure_user_exists(self, user_id, username=None):
        query = "SELECT id FROM usuarios WHERE id = %s;"
        result = self.execute(query, (user_id,))
        if not result:
            username = username or f"user_{user_id}"
            created_id = self.create_user(username, "default_password", user_id=user_id)
            logger.info(f"✅ Usuario {username} (id={created_id}) creado automáticamente.")
            return True
        return False

    def clear_database(self, user_id):
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM memorias WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM chat_mensajes WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM logs_simulacion WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM propuestas WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM misiones WHERE user_id = %s;", (user_id,))
                # Eliminar posts sociales pertenecientes a esta partida/usuario
                cur.execute("DELETE FROM posts_sociales WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM agentes WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM civilizaciones WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM estado_mundo WHERE user_id = %s;", (user_id,))
            self.conn.commit()
            logger.info(f"🗑️ Datos de la partida de {user_id} limpiados.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al limpiar DB para {user_id}: {e}")
            if self.conn: self.conn.rollback()
            return False

    def save_agent(self, agent, user_id):
        query = """
        INSERT INTO agentes (id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, civilizacion_id, alianzas, tratados, memoria_mensajes, x, y, skills, skill_factor, beliefs, desires, intentions, alma, identidad, heartbeat_config, memoria_persistente_data, apps)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            recursos = EXCLUDED.recursos, dinero = EXCLUDED.dinero, grupo_id = EXCLUDED.grupo_id,
            rol = EXCLUDED.rol, profesion = EXCLUDED.profesion, rango = EXCLUDED.rango,
            reputacion = EXCLUDED.reputacion, personalidad = EXCLUDED.personalidad,
            necesidades = EXCLUDED.necesidades, experiencia = EXCLUDED.experiencia,
            conocimientos = EXCLUDED.conocimientos, inventario = EXCLUDED.inventario,
            hitos = EXCLUDED.hitos, historial_etico = EXCLUDED.historial_etico,
            civilizacion_id = EXCLUDED.civilizacion_id, alianzas = EXCLUDED.alianzas,
            tratados = EXCLUDED.tratados, memoria_mensajes = EXCLUDED.memoria_mensajes,
            x = EXCLUDED.x, y = EXCLUDED.y, skills = EXCLUDED.skills, skill_factor = EXCLUDED.skill_factor,
            beliefs = EXCLUDED.beliefs, desires = EXCLUDED.desires, intentions = EXCLUDED.intentions,
            alma = EXCLUDED.alma, identidad = EXCLUDED.identidad, heartbeat_config = EXCLUDED.heartbeat_config,
            memoria_persistente_data = EXCLUDED.memoria_persistente_data, apps = EXCLUDED.apps;
        """
        self.execute(query, (
            str(agent.unique_id), user_id, agent.recursos, agent.dinero, agent.grupo_id,
            agent.rol, agent.profesion, agent.rango, agent.reputacion, Json(agent.personalidad),
            Json(agent.necesidades), Json(agent.experiencia), Json(agent.conocimientos),
            Json(agent.inventario), Json(getattr(agent, "hitos", [])), Json(agent.historial_etico),
            agent.civilizacion_id, Json(getattr(agent, "alianzas", [])), Json(getattr(agent, "tratados", [])),
            Json(agent.memoria.historial_mensajes), agent.x, agent.y, Json(agent.skills), agent.skill_factor,
            Json(agent.creencias.to_dict()), Json(agent.deseos.to_dict()), Json(agent.intenciones.to_dict()),
            Json(agent.alma.to_dict() if hasattr(agent, "alma") and agent.alma else {}),
            Json(agent.identidad.to_dict() if hasattr(agent, "identidad") and agent.identidad else {}),
            Json(agent.heartbeat_mundo.to_dict() if hasattr(agent, "heartbeat_mundo") and agent.heartbeat_mundo else {}),
            Json(agent.memoria_persistente.to_dict() if hasattr(agent, "memoria_persistente") and agent.memoria_persistente else {}),
            Json(getattr(agent, "apps", {})),
        ))

    def get_agents(self, user_id):
        query = "SELECT id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, civilizacion_id, alianzas, tratados, memoria_mensajes, x, y, skills, skill_factor, beliefs, desires, intentions, alma, identidad, heartbeat_config, memoria_persistente_data, apps FROM agentes WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_civilization(self, civ):
        query = """
        INSERT INTO civilizaciones (id, nombre, color, user_id, recursos_globales, territorio)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            nombre = EXCLUDED.nombre, color = EXCLUDED.color,
            recursos_globales = EXCLUDED.recursos_globales, territorio = EXCLUDED.territorio;
        """
        self.execute(query, (civ.id, civ.nombre, civ.color, civ.user_id, civ.recursos_globales, Json(civ.territorio)))

    def get_civilizations(self, user_id):
        query = "SELECT id, nombre, color, recursos_globales, territorio FROM civilizaciones WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_memory(self, owner_id, target_id, data, user_id):
        # --- DIAGNÓSTICO: Verificar existencia de agentes antes de guardar memoria ---
        check_query = "SELECT COUNT(*) FROM agentes WHERE id IN (%s, %s) AND user_id = %s;"
        res = self.execute(check_query, (str(owner_id), str(target_id), user_id))
        
        expected_count = 2 if str(owner_id) != str(target_id) else 1
        if not res or res[0][0] < expected_count:
            # logger.warning(f"⚠️ [DB] No se puede guardar memoria: uno de los agentes ({owner_id}, {target_id}) no existe en la DB para {user_id}")
            return

        query = """
        INSERT INTO memorias (user_id, agente_fuente, agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, agente_fuente, agente_objetivo) DO UPDATE SET
            tipo_relacion = EXCLUDED.tipo_relacion, fuerza = EXCLUDED.fuerza,
            recursos_percibidos = EXCLUDED.recursos_percibidos, grupo_percibido = EXCLUDED.grupo_percibido;
        """
        success = self.execute(query, (user_id, str(owner_id), str(target_id), data.get("tipo"), data.get("fuerza", 0.0), data.get("recursos_vistos"), data.get("grupo")))
        # if not success:
        #    logger.error(f"❌ [DB] Error insertando memoria {owner_id} -> {target_id}")

    def save_world_state(self, user_id, step, lore, seed, economy, relaciones_grupos=None, objetivos_grupos=None, mapa=None, infraestructura=None, historia=None, social_feed=None):
        query = """
        INSERT INTO estado_mundo (user_id, paso_actual, lore, seed, precio_recurso, indice_bursatil, total_dinero, relaciones_grupos, objetivos_grupos, mapa, infraestructura, historia, social_feed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            paso_actual = EXCLUDED.paso_actual, lore = EXCLUDED.lore, seed = EXCLUDED.seed,
            precio_recurso = EXCLUDED.precio_recurso, indice_bursatil = EXCLUDED.indice_bursatil,
            total_dinero = EXCLUDED.total_dinero, relaciones_grupos = EXCLUDED.relaciones_grupos,
            objetivos_grupos = EXCLUDED.objetivos_grupos, mapa = EXCLUDED.mapa,
            infraestructura = EXCLUDED.infraestructura, historia = EXCLUDED.historia, social_feed = EXCLUDED.social_feed;
        """
        self.execute(query, (
            user_id, step, lore, seed, economy.get("precio_recurso", 2.0),
            economy.get("indice_bursatil", 1000.0), economy.get("total_dinero", 0.0),
            Json(relaciones_grupos) if relaciones_grupos else Json({}),
            Json(objetivos_grupos) if objetivos_grupos else Json({}),
            Json(mapa) if mapa else None, Json(infraestructura) if infraestructura else Json([]),
            Json(historia) if historia else Json({}), Json(social_feed) if social_feed else Json({}),
        ))

    def get_world_state(self, user_id):
        query = "SELECT paso_actual, lore, seed, precio_recurso, indice_bursatil, total_dinero, relaciones_grupos, objetivos_grupos, mapa, infraestructura, historia, social_feed FROM estado_mundo WHERE user_id = %s ORDER BY id DESC LIMIT 1;"
        result = self.execute(query, (user_id,))
        return result[0] if result else None

    def get_user_games(self, base_user_id):
        # 1. Buscar partidas con prefijo (slots nuevos)
        query = "SELECT user_id, paso_actual FROM estado_mundo WHERE user_id LIKE %s;"
        pattern = f"{base_user_id}_%"
        result = self.execute(query, (pattern,)) or []
        
        games = []
        for r in result:
            games.append({
                "id": r[0],
                "paso_actual": r[1]
            })
            
        # 2. Buscar partida base (legacy o actual si no tiene sufijo)
        old = self.get_world_state(base_user_id)
        if old:
            if not any(g['id'] == base_user_id for g in games):
                games.append({
                    "id": base_user_id,
                    "paso_actual": old[0]
                })
        
        # Ordenar por paso_actual descendente o simplemente devolver
        return games


    def get_memories(self, agent_id, user_id):
        query = "SELECT agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido FROM memorias WHERE agente_fuente = %s AND user_id = %s;"
        return self.execute(query, (str(agent_id), user_id))

    def save_proposal(self, prop, user_id):
        votos = Json(prop.get("votos", {}))
        estado = prop.get("estado", "pendiente")
        titulo = prop.get("titulo")
        contenido = prop.get("contenido")
        db_id = prop.get("db_id") or prop.get("id") if str(prop.get("id", "")).isdigit() else None

        if db_id:
            query = "UPDATE propuestas SET votos = %s, estado = %s, titulo = %s, contenido = %s WHERE id = %s AND user_id = %s;"
            self.execute(query, (votos, estado, titulo, contenido, db_id, user_id))
            return db_id
        else:
            query = "INSERT INTO propuestas (user_id, grupo_id, proponente_id, texto, tipo, votos, estado, paso_creacion, titulo, contenido) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
            result = self.execute(query, (user_id, prop.get("grupo_id"), prop.get("proponente_id"), prop.get("texto"), prop.get("tipo"), votos, estado, prop.get("paso_creacion", 0), titulo, contenido))
            if result and isinstance(result, list):
                return result[0][0]
            return None

    def get_proposals(self, user_id):
        query = "SELECT id, grupo_id, proponente_id, texto, tipo, votos, estado, paso_creacion, titulo, contenido FROM propuestas WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_mission(self, mision, user_id):
        query = """
        INSERT INTO misiones (id, user_id, titulo, descripcion, tipo, dificultad, objetivo, recompensa_puntos, estado, turno_inicio, turno_limite, completada_por, turno_completada)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            objetivo = EXCLUDED.objetivo, estado = EXCLUDED.estado,
            completada_por = EXCLUDED.completada_por, turno_completada = EXCLUDED.turno_completada;
        """
        self.execute(query, (mision.id, user_id, mision.titulo, mision.descripcion, mision.tipo, mision.dificultad, Json(mision.objetivo), mision.recompensa_puntos, mision.estado, mision.turno_inicio, mision.turno_limite, mision.completada_por, mision.turno_completada))

    def get_missions(self, user_id):
        query = "SELECT id, titulo, descripcion, tipo, dificultad, objetivo, recompensa_puntos, estado, turno_inicio, turno_limite, completada_por, turno_completada FROM misiones WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def save_score(self, user_id, puntos):
        query = "INSERT INTO puntajes_usuarios (user_id, puntos) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET puntos = EXCLUDED.puntos;"
        self.execute(query, (user_id, puntos))

    def get_score(self, user_id):
        query = "SELECT puntos FROM puntajes_usuarios WHERE user_id = %s;"
        result = self.execute(query, (user_id,))
        return result[0][0] if result else 0

    def get_ranking(self):
        query = "SELECT u.id, u.username, p.puntos FROM puntajes_usuarios p JOIN usuarios u ON p.user_id = u.id ORDER BY p.puntos DESC LIMIT 10;"
        result = self.execute(query)
        return result if isinstance(result, list) else []

    def save_log(self, user_id, paso, mensaje, categoria, pensamiento=None, privado_para=None, subtitulos=None, tts_text=None, agente_id=None):
        query = "INSERT INTO logs_simulacion (user_id, paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"
        self.execute(query, (user_id, paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id))

    def get_logs(self, user_id, limit=2000):
        query = "SELECT paso, mensaje, categoria, pensamiento, privado_para, subtitulos, tts_text, agente_id FROM logs_simulacion WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s;"
        rows = self.execute(query, (user_id, limit))
        return rows[::-1] if rows else []

    def save_chat_message(self, user_id, agent_id, role, content, timestamp_utc):
        query = "INSERT INTO chat_mensajes (user_id, agent_id, role, content, timestamp_utc) VALUES (%s, %s, %s, %s, TO_TIMESTAMP(%s));"
        self.execute(query, (user_id, agent_id, role, content, timestamp_utc))

    def get_chat_history(self, user_id, agent_id, limit=100):
        query = "SELECT role, content, timestamp_utc FROM chat_mensajes WHERE user_id = %s AND agent_id = %s ORDER BY timestamp_utc ASC LIMIT %s;"
        rows = self.execute(query, (user_id, agent_id, limit))
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows] if rows else []

    def save_institution(self, inst, user_id):
        query = """
        INSERT INTO instituciones (id, user_id, nombre, tipo, fundador_id, vocero_id, miembros, x, y, recursos, puntos, nivel, descripcion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            nombre = EXCLUDED.nombre, tipo = EXCLUDED.tipo, vocero_id = EXCLUDED.vocero_id,
            miembros = EXCLUDED.miembros, recursos = EXCLUDED.recursos, puntos = EXCLUDED.puntos, nivel = EXCLUDED.nivel,
            descripcion = EXCLUDED.descripcion;
        """
        self.execute(query, (inst.id, user_id, inst.nombre, inst.tipo, inst.fundador_id, inst.vocero_id, Json(inst.miembros), inst.x, inst.y, inst.recursos, getattr(inst, 'puntos', 0.0), inst.nivel, inst.descripcion))

    def get_institutions(self, user_id):
        query = "SELECT id, nombre, tipo, fundador_id, vocero_id, miembros, x, y, recursos, puntos, nivel, descripcion FROM instituciones WHERE user_id = %s;"
        return self.execute(query, (user_id,))
