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
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'estado_mundo';")
    columns = [row[0] for row in cur.fetchall()]
    print(f"Columns in estado_mundo: {columns}")
    
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = [row[0] for row in cur.fetchall()]
    print(f"Tables in public schema: {tables}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
