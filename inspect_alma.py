import json
import psycopg2

try:
    conn = psycopg2.connect("dbname=mundoia user=architect password=Qw7t9vL2pX6z host=127.0.0.1 port=5434")
    cur = conn.cursor()
    cur.execute("SELECT id, identidad, alma FROM agentes LIMIT 3;")
    rows = cur.fetchall()
    for row in rows:
        print(f"--- Agente {row[0]} ---")
        # print("Identidad:", json.dumps(row[1], indent=2))
        alma = row[2]
        if alma and "narrativa_personal" in alma:
            print("Narrativa Personal:", alma["narrativa_personal"])
        else:
            print("Alma no tiene narrativa_personal.")
except Exception as e:
    print("Error connecting to db:", e)
