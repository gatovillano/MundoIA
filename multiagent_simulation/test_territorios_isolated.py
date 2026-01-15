from modelo import ModeloRelacional, Civilizacion, Agente
import random

def test_territorios_isolated():
    print("🚀 Iniciando prueba AISLADA de territorios y civilizaciones...")
    
    # Inicializar modelo sin cargar de DB
    modelo = ModeloRelacional(num_agentes=0)
    modelo.db_active = False # Desactivar DB
    
    # 1. Crear Civilizaciones
    civ1 = Civilizacion("CIV-1", "Imperio Solar", "#FF5733")
    civ2 = Civilizacion("CIV-2", "Federación Lunar", "#3357FF")
    modelo.civilizaciones["CIV-1"] = civ1
    modelo.civilizaciones["CIV-2"] = civ2
    
    # 2. Crear agentes manualmente
    for i in range(5):
        a = Agente(f"A{i}", modelo, civ_id="CIV-1")
        a.x, a.y = 5, 5
        modelo.agentes.append(a)
        
    for i in range(5, 10):
        a = Agente(f"A{i}", modelo, civ_id="CIV-2")
        a.x, a.y = 15, 15
        modelo.agentes.append(a)
        
    print(f"Agentes creados: 5 en {civ1.nombre}, 5 en {civ2.nombre}")
    
    # 3. Actualizar territorios iniciales
    modelo.actualizar_territorios()
    print(f"Territorio inicial {civ1.nombre}: {len(civ1.territorio)} celdas")
    print(f"Territorio inicial {civ2.nombre}: {len(civ2.territorio)} celdas")
    
    # 4. Simular movimiento y expansión (sin llamar a step() para evitar LLMs)
    print("\n--- Simulando 5 pasos de expansión manual ---")
    for i in range(5):
        # Mover agentes de CIV-1 hacia el centro
        for agente in [a for a in modelo.agentes if a.civilizacion_id == "CIV-1"]:
            agente.x = min(19, agente.x + 1)
            agente.y = min(19, agente.y + 1)
            
        modelo.actualizar_territorios()
        print(f"Paso {i+1}: Territorio {civ1.nombre} = {len(civ1.territorio)} celdas, {civ2.nombre} = {len(civ2.territorio)} celdas")

    if len(civ1.territorio) > 1:
        print("\n✅ El sistema de territorios se expande correctamente con el movimiento.")
    else:
        print("\n❌ El territorio no cambió.")

if __name__ == "__main__":
    test_territorios_isolated()
