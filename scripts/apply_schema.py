import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn_params = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "mundoia"),
    "user": os.getenv("DB_USER", "architect"),
    "password": os.getenv("DB_PASS", "mundoia_secret_2026"),
    "port": os.getenv("DB_PORT", "5434"),
}

try:
    conn = psycopg2.connect(**conn_params)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Lista de tablas para limpiar
    tables = [
        "eventos_globales", "posts_sociales", "puntajes_usuarios", "instituciones", "estado_mundo", 
        "misiones", "propuestas", "logs_simulacion", "chat_mensajes", 
        "memorias", "civilizaciones", "agentes", "usuarios"
    ]
    
    print("🧹 Limpiando tablas existentes...")
    for table in tables:
        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
    
    with open("restore_schema.sql", "r") as f:
        sql = f.read()
        
    print("🚀 Ejecutando restauración de esquema...")
    cur.execute(sql)
    print("✅ Esquema restaurado correctamente.")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Error restaurando esquema: {e}")
