
import os
import sys
from dotenv import load_dotenv

# Añadir el directorio raíz al path
sys.path.append(os.getcwd())

load_dotenv()

try:
    from core.modelo import ModeloRelacional, Agente
    print("✅ Clases ModeloRelacional y Agente importadas correctamente.")
    
    # Intentar inicializar un modelo (sin DB para evitar errores de conexión)
    os.environ["DB_HOST"] = "" 
    modelo = ModeloRelacional(num_agentes=2, start_empty=True)
    print("✅ ModeloRelacional inicializado.")
    
    # Crear un agente de prueba
    agente = Agente("TestAgent", modelo)
    print("✅ Agente de prueba creado.")
    
    # Probar el router de acciones
    print("Testing action router...")
    res = agente.ejecutar_accion_final({"tipo": "descansar", "parametros": {}})
    if res:
        print("✅ Action Router: descansar funcionó.")
    
    # Probar orquestación de turno
    print("Testing turn orchestration...")
    if hasattr(modelo, "_procesar_turno_agente"):
        modelo._procesar_turno_agente(agente)
        print("✅ Turn orchestration (_procesar_turno_agente) funcionó.")
    else:
        print("❌ _procesar_turno_agente no encontrado en modelo.")
        
except Exception as e:
    print(f"❌ Error durante la verificación: {e}")
    import traceback
    traceback.print_exc()
