-- Schema for MundoIA Architect Mode
-- Updated for correct dependency order

-- 1. Users (Base entity)
CREATE TABLE IF NOT EXISTS usuarios (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Civilizations (Depends on Users)
CREATE TABLE IF NOT EXISTS civilizaciones (
    id VARCHAR(50),
    nombre VARCHAR(100) NOT NULL,
    color VARCHAR(20) DEFAULT '#00f2ff',
    user_id VARCHAR(50) REFERENCES usuarios(id),
    recursos_globales FLOAT DEFAULT 0.0,
    territorio JSONB DEFAULT '[]',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, user_id)
);

-- 3. Agents (Depends on Users)
CREATE TABLE IF NOT EXISTS agentes (
    id VARCHAR(50),
    user_id VARCHAR(50) REFERENCES usuarios(id),
    recursos FLOAT DEFAULT 100.0,
    dinero FLOAT DEFAULT 100.0,
    grupo_id VARCHAR(50),
    rol VARCHAR(50) DEFAULT 'Ciudadano',
    profesion VARCHAR(50),
    rango FLOAT DEFAULT 1.0,
    reputacion FLOAT DEFAULT 1.0,
    personalidad JSONB,
    necesidades JSONB,
    experiencia JSONB,
    conocimientos JSONB,
    inventario JSONB,
    hitos JSONB DEFAULT '[]',
    historial_etico JSONB DEFAULT '[]',
    civilizacion_id VARCHAR(50), -- Can be a soft link or FK later
    alianzas JSONB DEFAULT '[]',
    tratados JSONB DEFAULT '[]',
    x INTEGER,
    y INTEGER,
    memoria_mensajes JSONB DEFAULT '[]',
    skills JSONB DEFAULT '{}',
    skill_factor FLOAT DEFAULT 0.3,
    beliefs JSONB DEFAULT '[]',
    desires JSONB DEFAULT '[]',
    intentions JSONB DEFAULT '[]',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, user_id)
);

-- 4. World State (References Users implicitly or explicitly)
CREATE TABLE IF NOT EXISTS estado_mundo (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE REFERENCES usuarios(id), -- Added explicit reference
    paso_actual INTEGER DEFAULT 0,
    lore TEXT,
    seed TEXT,
    precio_recurso FLOAT DEFAULT 2.0,
    indice_bursatil FLOAT DEFAULT 1000.0,
    total_dinero FLOAT DEFAULT 0.0,
    relaciones_grupos JSONB DEFAULT '{}',
    objetivos_grupos JSONB DEFAULT '{}',
    mapa JSONB,
    infraestructura JSONB DEFAULT '[]',
    historia JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Memories (Depends on Users and Agents)
CREATE TABLE IF NOT EXISTS memorias (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    agente_fuente VARCHAR(50),
    agente_objetivo VARCHAR(50),
    tipo_relacion VARCHAR(50), -- amigo, enemigo, conocido
    fuerza FLOAT DEFAULT 0.0,
    recursos_percibidos FLOAT,
    grupo_percibido VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, agente_fuente, agente_objetivo),
    FOREIGN KEY (agente_fuente, user_id) REFERENCES agentes(id, user_id),
    FOREIGN KEY (agente_objetivo, user_id) REFERENCES agentes(id, user_id)
);

-- 6. Global Events (Independent)
CREATE TABLE IF NOT EXISTS eventos_globales (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50), -- Famine, Resource Rain, etc.
    descripcion TEXT,
    paso_inicio INTEGER,
    duracion INTEGER,
    impacto JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Logs (Depends on Users)
CREATE TABLE IF NOT EXISTS logs_simulacion (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    paso INTEGER,
    agente_id VARCHAR(50),
    mensaje TEXT,
    categoria VARCHAR(50),
    pensamiento TEXT,
    privado_para VARCHAR(50),
    subtitulos TEXT,
    tts_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Proposals & Laws (Depends on Users)
CREATE TABLE IF NOT EXISTS propuestas (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    grupo_id VARCHAR(50),
    proponente_id VARCHAR(50),
    texto TEXT,
    tipo VARCHAR(50), -- ley, plan, mision
    votos JSONB DEFAULT '{}', -- {agente_id: voto}
    estado VARCHAR(20) DEFAULT 'pendiente',
    paso_creacion INTEGER,
    titulo VARCHAR(200),
    contenido TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Misiones (Depends on Users)
CREATE TABLE IF NOT EXISTS misiones (
    id VARCHAR(100), -- ID de la misión del catálogo
    user_id VARCHAR(50) REFERENCES usuarios(id),
    titulo VARCHAR(100),
    descripcion TEXT,
    tipo VARCHAR(50),
    dificultad VARCHAR(20),
    objetivo JSONB,
    recompensa_puntos INTEGER,
    estado VARCHAR(20), -- activa, completada, fallida
    turno_inicio INTEGER,
    turno_limite INTEGER,
    completada_por VARCHAR(50),
    turno_completada INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, user_id)
);

-- 11. Puntajes de Usuario (Depends on Users)
CREATE TABLE IF NOT EXISTS puntajes_usuarios (
    user_id VARCHAR(50) PRIMARY KEY REFERENCES usuarios(id),
    puntos INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Chat Mensajes (Depends on Users and Agents)
CREATE TABLE IF NOT EXISTS chat_mensajes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    agent_id VARCHAR(50),
    role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'agent')),
    content TEXT NOT NULL,
    timestamp_utc DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id, user_id) REFERENCES agentes(id, user_id)
);

-- Índice para búsquedas rápidas por usuario+agente
CREATE INDEX IF NOT EXISTS idx_chat_mensajes_user_agent ON chat_mensajes(user_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_chat_mensajes_timestamp ON chat_mensajes(timestamp_utc);
