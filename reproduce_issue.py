
import os
import sys
from dotenv import load_dotenv

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.database import DatabaseManager

load_dotenv()

def test_get_user_games():
    db = DatabaseManager()
    if db.connect():
        # Intentar con un user_id que sepamos que existe o uno genérico
        user_id = "test_user" # O cambiar por uno real si lo conocemos
        print(f"Buscando partidas para: {user_id}")
        games = db.get_user_games(user_id)
        print(f"Partidas encontradas: {games}")
        
        # También listar todos los usuarios para ver qué hay
        users = db.execute("SELECT id, username FROM usuarios LIMIT 5;")
        print(f"Usuarios en DB: {users}")
        
        # Listar entradas en estado_mundo
        states = db.execute("SELECT user_id, paso_actual FROM estado_mundo LIMIT 5;")
        print(f"Estados en estado_mundo: {states}")
    else:
        print("Fallo al conectar a la DB")

if __name__ == "__main__":
    test_get_user_games()
