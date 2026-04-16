import os
import uuid
import json
import logging
import psycopg2
import bcrypt
from typing import List, Dict, Any, Optional
from core.utils import Json, logger

class DatabaseManager:
    """Administrador de la persistencia en PostgreSQL para MundoIA."""
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
            # Buscar archivos en el directorio 'data' del proyecto
            # El directorio base es el padre de 'core'
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for schema_file in ["schema.sql", "create_users_table.sql"]:
                schema_path = os.path.join(base_dir, "data", schema_file)
                if os.path.exists(schema_path):
                    with open(schema_path, "r") as f:
                        schema_sql = f.read()

                    logger.info(f"📜 Ejecutando esquema desde: {schema_path}")
                    with self.conn.cursor() as cur:
                        cur.execute(schema_sql)
                        # Migraciones BDI
                        cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS beliefs JSONB DEFAULT '[]';")
                        cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS desires JSONB DEFAULT '[]';")
                        cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS intentions JSONB DEFAULT '[]';")
                    logger.info(f"✅ Esquema {schema_file} verificado/inicializado.")
                else:
                    logger.warning(f"⚠️ No se encontró {schema_file} en {schema_path}")

            # Migraciones automáticas adicionales
            try:
                with self.conn.cursor() as cur:
                    # Columnas de los agentes
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS memoria_mensajes JSONB DEFAULT '[]';")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '{}';")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS skill_factor FLOAT DEFAULT 0.3;")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS memoria_persistente_data JSONB DEFAULT '{}';")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS alma JSONB DEFAULT '{}';")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS identidad JSONB DEFAULT '{}';")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS heartbeat_config JSONB DEFAULT '{}';")
                    cur.execute("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS apps JSONB DEFAULT '{}';")
                    
                    # Columnas de logs y estado
                    cur.execute("ALTER TABLE logs_simulacion ADD COLUMN IF NOT EXISTS subtitulos TEXT;")
                    cur.execute("ALTER TABLE logs_simulacion ADD COLUMN IF NOT EXISTS tts_text TEXT;")
                    cur.execute("ALTER TABLE estado_mundo ADD COLUMN IF NOT EXISTS social_feed JSONB DEFAULT '{}';")

                    # Migración de Claves Primarias Compuestas (Asegurar aislamiento total por usuario)
                    # 1. Agentes
                    cur.execute("""
                       DO $$ BEGIN
                           IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agentes_pkey' AND contype = 'p') THEN
                               IF NOT EXISTS (
                                   SELECT 1 FROM information_schema.key_column_usage 
                                   WHERE table_name = 'agentes' AND constraint_name = 'agentes_pkey' AND column_name = 'user_id'
                               ) THEN
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

                    # 3. Instituciones (Garantizar su existencia)
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
                logger.warning(f"Error en migraciones automáticas: {e}")
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
        check_query = "SELECT COUNT(*) FROM agentes WHERE id IN (%s, %s) AND user_id = %s;"
        res = self.execute(check_query, (str(owner_id), str(target_id), user_id))
        if not res or res[0][0] < 2: return

        query = """
        INSERT INTO memorias (user_id, agente_fuente, agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, agente_fuente, agente_objetivo) DO UPDATE SET
            tipo_relacion = EXCLUDED.tipo_relacion, fuerza = EXCLUDED.fuerza,
            recursos_percibidos = EXCLUDED.recursos_percibidos, grupo_percibido = EXCLUDED.grupo_percibido;
        """
        self.execute(query, (user_id, str(owner_id), str(target_id), data.get("tipo"), data.get("fuerza", 0.0), data.get("recursos_vistos"), data.get("grupo")))

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

    def get_memories(self, agent_id, user_id):
        query = "SELECT agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido FROM memorias WHERE agente_fuente = %s AND user_id = %s;"
        return self.execute(query, (str(agent_id), user_id))

    def save_proposal(self, prop, user_id):
        votos = Json(prop.get("votos", {}))
        estado = prop.get("estado", "pendiente")
        titulo = prop.get("titulo")
        contenido = prop.get("contenido")
        db_id = prop.get("db_id")

        if db_id:
            query = "UPDATE propuestas SET votos = %s, estado = %s, titulo = %s, contenido = %s WHERE id = %s AND user_id = %s;"
            self.execute(query, (votos, estado, titulo, contenido, db_id, user_id))
        else:
            query = "INSERT INTO propuestas (user_id, grupo_id, proponente_id, texto, tipo, votos, estado, paso_creacion, titulo, contenido) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"
            self.execute(query, (user_id, prop.get("grupo_id"), prop.get("proponente_id"), prop.get("texto"), prop.get("tipo"), votos, estado, prop.get("paso_creacion", 0), titulo, contenido))

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
        query = "INSERT INTO chat_mensajes (user_id, agent_id, role, content, timestamp_utc) VALUES (%s, %s, %s, %s, %s);"
        self.execute(query, (user_id, agent_id, role, content, timestamp_utc))

    def get_chat_history(self, user_id, agent_id, limit=100):
        query = "SELECT role, content, timestamp_utc FROM chat_mensajes WHERE user_id = %s AND agent_id = %s ORDER BY timestamp_utc ASC LIMIT %s;"
        rows = self.execute(query, (user_id, agent_id, limit))
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows] if rows else []

    def save_institution(self, inst, user_id):
        query = """
        INSERT INTO instituciones (id, user_id, nombre, tipo, fundador_id, lider_id, miembros, x, y, recursos, nivel, descripcion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            nombre = EXCLUDED.nombre, tipo = EXCLUDED.tipo, lider_id = EXCLUDED.lider_id,
            miembros = EXCLUDED.miembros, recursos = EXCLUDED.recursos, nivel = EXCLUDED.nivel,
            descripcion = EXCLUDED.descripcion;
        """
        self.execute(query, (inst.id, user_id, inst.nombre, inst.tipo, inst.fundador_id, inst.lider_id, Json(inst.miembros), inst.x, inst.y, inst.recursos, inst.nivel, inst.descripcion))

    def get_institutions(self, user_id):
        query = "SELECT id, nombre, tipo, fundador_id, lider_id, miembros, x, y, recursos, nivel, descripcion FROM instituciones WHERE user_id = %s;"
        return self.execute(query, (user_id,))
