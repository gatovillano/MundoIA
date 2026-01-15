-- Schema for MundoIA Architect Mode

-- World State
CREATE TABLE IF NOT EXISTS estado_mundo (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE,
    paso_actual INTEGER DEFAULT 0,
    lore TEXT,
    seed TEXT,
    precio_recurso FLOAT DEFAULT 2.0,
    indice_bursatil FLOAT DEFAULT 1000.0,
    total_dinero FLOAT DEFAULT 0.0,
    relaciones_grupos JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agents
CREATE TABLE IF NOT EXISTS agentes (
    id VARCHAR(50) PRIMARY KEY,
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
    civilizacion_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Memories (Graph edges)
CREATE TABLE IF NOT EXISTS memorias (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    agente_fuente VARCHAR(50) REFERENCES agentes(id),
    agente_objetivo VARCHAR(50) REFERENCES agentes(id),
    tipo_relacion VARCHAR(50), -- amigo, enemigo, conocido
    fuerza FLOAT DEFAULT 0.0,
    recursos_percibidos FLOAT,
    grupo_percibido VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, agente_fuente, agente_objetivo)
);

-- Global Events
CREATE TABLE IF NOT EXISTS eventos_globales (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50), -- Famine, Resource Rain, etc.
    descripcion TEXT,
    paso_inicio INTEGER,
    duracion INTEGER,
    impacto JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users
CREATE TABLE IF NOT EXISTS usuarios (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Civilizations
CREATE TABLE IF NOT EXISTS civilizaciones (
    id VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    color VARCHAR(20) DEFAULT '#00f2ff',
    user_id VARCHAR(50) REFERENCES usuarios(id),
    recursos_globales FLOAT DEFAULT 0.0,
    territorio JSONB DEFAULT '[]',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agents (Modified to include civilizacion_id)
-- Note: In a real migration we would use ALTER TABLE, but here we update the schema definition.
-- CREATE TABLE IF NOT EXISTS agentes (
--     ...
--     civilizacion_id VARCHAR(50) REFERENCES civilizaciones(id),
--     ...
-- );

-- Logs
CREATE TABLE IF NOT EXISTS logs_simulacion (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES usuarios(id),
    paso INTEGER,
    agente_id VARCHAR(50),
    mensaje TEXT,
    categoria VARCHAR(50),
    pensamiento TEXT,
    privado_para VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Proposals & Laws
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
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
