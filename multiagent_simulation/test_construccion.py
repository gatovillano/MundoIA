import os
from modelo import ModeloRelacional, Agente

def test_construccion():
    print("🚀 Iniciando prueba de construcción...")
    modelo = ModeloRelacional(num_agentes=5)
    
    if not modelo.agentes:
        print("⚠️ No hay agentes cargados, creando uno nuevo...")
        agente = modelo.spawn_agent()
    else:
        agente = modelo.agentes[0]
    
    # Forzar condiciones para construir
    agente.dinero = 200
    agente.recursos = 100
    agente.grupo_id = "G-TEST"
    
    print(f"Agente {agente.unique_id} recursos iniciales: Dinero={agente.dinero}, Recursos={agente.recursos}")
    
    # Intentar construir un Hospital
    exito, msg = modelo.construir_edificio(agente, "Hospital")
    print(f"Resultado construcción: {exito}, Mensaje: {msg}")
    
    if exito:
        print(f"Infraestructura actual: {modelo.infraestructura}")
        
        # Verificar recursos descontados
        print(f"Agente {agente.unique_id} recursos tras construir: Dinero={agente.dinero}, Recursos={agente.recursos}")
        
        # Verificar efecto pasivo en el siguiente step
        agente.necesidades["salud"] = 5.0
        print(f"Salud inicial del agente: {agente.necesidades['salud']}")
        
        modelo.step()
        
        print(f"Salud tras un step con Hospital: {agente.necesidades['salud']}")
        if agente.necesidades["salud"] > 5.0:
            print("✅ Efecto pasivo del Hospital verificado.")
        else:
            print("❌ El efecto pasivo del Hospital no se aplicó.")
            
    else:
        print("❌ Falló la construcción en la prueba.")

if __name__ == "__main__":
    test_construccion()
