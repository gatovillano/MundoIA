-- Schema for MundoIA Architect Mode

-- World State
CREATE TABLE IF NOT EXISTS estado_mundo (
    id SERIAL PRIMARY KEY,
    paso_actual INTEGER DEFAULT 0,
    lore TEXT,
    seed TEXT,
    precio_recurso FLOAT DEFAULT 2.0,
    indice_bursatil FLOAT DEFAULT 1000.0,
    total_dinero FLOAT DEFAULT 0.0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agents
CREATE TABLE IF NOT EXISTS agentes (
    id VARCHAR(50) PRIMARY KEY,
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
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Memories (Graph edges)
CREATE TABLE IF NOT EXISTS memorias (
    id SERIAL PRIMARY KEY,
    agente_fuente VARCHAR(50) REFERENCES agentes(id),
    agente_objetivo VARCHAR(50) REFERENCES agentes(id),
    tipo_relacion VARCHAR(50), -- amigo, enemigo, conocido
    fuerza FLOAT DEFAULT 0.0,
    recursos_percibidos FLOAT,
    grupo_percibido VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agente_fuente, agente_objetivo)
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

-- Logs
CREATE TABLE IF NOT EXISTS logs_simulacion (
    id SERIAL PRIMARY KEY,
    paso INTEGER,
    agente_id VARCHAR(50),
    mensaje TEXT,
    categoria VARCHAR(50),
    pensamiento TEXT,
    privado_para VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
