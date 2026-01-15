from modelo import ModeloRelacional, Civilizacion, Agente
import time

def test_territorios():
    print("🚀 Iniciando prueba de territorios y civilizaciones...")
    modelo = ModeloRelacional(num_agentes=10)
    
    # 1. Crear Civilizaciones
    civ1 = Civilizacion("CIV-1", "Imperio Solar", "#FF5733")
    civ2 = Civilizacion("CIV-2", "Federación Lunar", "#3357FF")
    modelo.civilizaciones["CIV-1"] = civ1
    modelo.civilizaciones["CIV-2"] = civ2
    
    # 2. Asignar agentes a civilizaciones y posicionarlos
    for i, agente in enumerate(modelo.agentes[:5]):
        agente.civilizacion_id = "CIV-1"
        agente.x, agente.y = 5, 5 # Todos en el mismo sector inicial
        
    for i, agente in enumerate(modelo.agentes[5:]):
        agente.civilizacion_id = "CIV-2"
        agente.x, agente.y = 15, 15 # Sector opuesto
        
    print(f"Agentes asignados: 5 a {civ1.nombre}, 5 a {civ2.nombre}")
    
    # 3. Actualizar territorios iniciales
    modelo.actualizar_territorios()
    print(f"Territorio inicial {civ1.nombre}: {len(civ1.territorio)} celdas")
    print(f"Territorio inicial {civ2.nombre}: {len(civ2.territorio)} celdas")
    
    # 4. Simular movimiento y expansión
    print("\n--- Simulando 5 pasos de expansión ---")
    for i in range(5):
        # Forzar movimiento de expansión para CIV-1
        for agente in [a for a in modelo.agentes if a.civilizacion_id == "CIV-1"]:
            agente.x = min(19, agente.x + 1)
            agente.y = min(19, agente.y + 1)
            
        modelo.step()
        print(f"Paso {i+1}: Territorio {civ1.nombre} = {len(civ1.territorio)} celdas, {civ2.nombre} = {len(civ2.territorio)} celdas")

    if len(civ1.territorio) > 1:
        print("\n✅ El sistema de territorios se expande correctamente con el movimiento.")
    else:
        print("\n❌ El territorio no cambió.")

if __name__ == "__main__":
    test_territorios()
