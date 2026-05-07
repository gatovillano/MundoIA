-- MUNDO IA - Schema Restoration Script (FIXED)

-- 1. Usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Agentes
CREATE TABLE IF NOT EXISTS agentes (
    id VARCHAR(100),
    user_id VARCHAR(50) REFERENCES usuarios(id),
    recursos FLOAT DEFAULT 100.0,
    dinero FLOAT DEFAULT 100.0,
    grupo_id VARCHAR(100),
    rol VARCHAR(50),
    profesion VARCHAR(50),
    rango FLOAT DEFAULT 1.0,
    reputacion FLOAT DEFAULT 1.0,
    personalidad JSONB DEFAULT '{}',
    necesidades JSONB DEFAULT '{}',
    experiencia JSONB DEFAULT '{}',
    conocimientos JSONB DEFAULT '{}',
    inventario JSONB DEFAULT '{}',
    hitos JSONB DEFAULT '[]',
    historial_etico JSONB DEFAULT '[]',
    civilizacion_id VARCHAR(100),
    alianzas JSONB DEFAULT '[]',
    tratados JSONB DEFAULT '[]',
    memoria_mensajes JSONB DEFAULT '[]',
    x INTEGER DEFAULT 0,
    y INTEGER DEFAULT 0,
    skills JSONB DEFAULT '{}',
    skill_factor FLOAT DEFAULT 0.3,
    beliefs JSONB DEFAULT '[]',
    desires JSONB DEFAULT '[]',
    intentions JSONB DEFAULT '[]',
    alma JSONB DEFAULT '{}',
    identidad JSONB DEFAULT '{}',
    heartbeat_config JSONB DEFAULT '{}',
    memoria_persistente_data JSONB DEFAULT '{}',
    apps JSONB DEFAULT '{}',
    PRIMARY KEY (id, user_id)
);

-- 3. Civilizaciones
CREATE TABLE IF NOT EXISTS civilizaciones (
    id VARCHAR(100),
    user_id VARCHAR(50) REFERENCES usuarios(id),
    nombre VARCHAR(100) NOT NULL,
    color VARCHAR(20),
    recursos_globales FLOAT DEFAULT 0.0,
    territorio JSONB DEFAULT '[]',
    PRIMARY KEY (id, user_id)
);

-- 4. Memorias (Relaciones entre agentes)
CREATE TABLE IF NOT EXISTS memorias (
    user_id VARCHAR(50) REFERENCES usuarios(id),
    agente_fuente VARCHAR(100),
    agente_objetivo VARCHAR(100),
    tipo_relacion VARCHAR(50),
    fuerza FLOAT DEFAULT 0.0,
    recursos_percibidos FLOAT DEFAULT 0.0,
    grupo_percibido VARCHAR(100),
    PRIMARY KEY (user_id, agente_fuente, agente_objetivo),
    FOREIGN KEY (agente_fuente, user_id) REFERENCES agentes(id, user_id),
    FOREIGN KEY (agente_objetivo, user_id) REFERENCES agentes(id, user_id)
);

-- 5. Chat Mensajes
CREATE TABLE IF NOT EXISTS chat_mensajes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    agent_id VARCHAR(100),
    role VARCHAR(20),
    content TEXT,
    timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id, user_id) REFERENCES agentes(id, user_id)
);

-- 6. Logs de Simulación
CREATE TABLE IF NOT EXISTS logs_simulacion (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    paso INTEGER,
    mensaje TEXT,
    categoria VARCHAR(50),
    pensamiento TEXT,
    privado_para VARCHAR(100),
    subtitulos TEXT,
    tts_text TEXT,
    agente_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Propuestas y Leyes
CREATE TABLE IF NOT EXISTS propuestas (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) REFERENCES usuarios(id),
    grupo_id VARCHAR(100),
    proponente_id VARCHAR(100),
    texto TEXT,
    tipo VARCHAR(50),
    votos JSONB DEFAULT '{"si": 0, "no": 0}',
    estado VARCHAR(20) DEFAULT 'pendiente',
    paso_creacion INTEGER,
    titulo VARCHAR(200),
    contenido TEXT
);

-- 8. Misiones
CREATE TABLE IF NOT EXISTS misiones (
    id VARCHAR(100),
    user_id VARCHAR(50) REFERENCES usuarios(id),
    titulo VARCHAR(200),
    descripcion TEXT,
    tipo VARCHAR(50),
    dificultad VARCHAR(20),
    objetivo JSONB,
    recompensa_puntos INTEGER,
    estado VARCHAR(20) DEFAULT 'activa',
    turno_inicio INTEGER,
    turno_limite INTEGER,
    completada_por VARCHAR(100),
    turno_completada INTEGER,
    PRIMARY KEY (id, user_id)
);

-- 9. Estado del Mundo (CORREGIDO)
CREATE TABLE IF NOT EXISTS estado_mundo (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE REFERENCES usuarios(id),
    paso_actual INTEGER DEFAULT 0,
    lore TEXT,
    seed INTEGER,
    precio_recurso FLOAT,
    indice_bursatil FLOAT,
    total_dinero FLOAT,
    relaciones_grupos JSONB DEFAULT '{}',
    objetivos_grupos JSONB DEFAULT '{}',
    mapa JSONB DEFAULT '[]',
    infraestructura JSONB DEFAULT '{}',
    historia JSONB DEFAULT '[]',
    social_feed JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Instituciones
CREATE TABLE IF NOT EXISTS instituciones (
    id VARCHAR(100),
    user_id VARCHAR(50) REFERENCES usuarios(id),
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(50),
    fundador_id VARCHAR(50),
    vocero_id VARCHAR(50),
    miembros JSONB DEFAULT '[]',
    x INTEGER,
    y INTEGER,
    recursos FLOAT DEFAULT 0.0,
    nivel INTEGER DEFAULT 1,
    descripcion TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, user_id)
);

-- 11. Puntajes de Usuarios
CREATE TABLE IF NOT EXISTS puntajes_usuarios (
    user_id VARCHAR(50) PRIMARY KEY REFERENCES usuarios(id),
    puntos INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Posts Sociales (NUEVO)
CREATE TABLE IF NOT EXISTS posts_sociales (
    id VARCHAR(100),
    user_id VARCHAR(50) REFERENCES usuarios(id),
    autor_id VARCHAR(100),
    contenido TEXT,
    tipo VARCHAR(50),
    temas JSONB DEFAULT '[]',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    likes INTEGER DEFAULT 0,
    likes_por JSONB DEFAULT '[]',
    comentarios JSONB DEFAULT '[]',
    PRIMARY KEY (id, user_id)
);

-- 13. Eventos Globales (NUEVO)
CREATE TABLE IF NOT EXISTS eventos_globales (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    tipo VARCHAR(50),
    descripcion TEXT,
    paso_inicio INTEGER,
    duracion INTEGER,
    impacto JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
