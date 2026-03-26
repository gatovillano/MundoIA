-- Script para crear la tabla de usuarios si no existe
CREATE TABLE IF NOT EXISTS usuarios (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para mejorar el rendimiento de las consultas
CREATE INDEX IF NOT EXISTS idx_username ON usuarios(username);