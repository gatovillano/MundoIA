import os
import sys
import random
from modelo import ModeloRelacional

def run_longevity_test(steps=50, num_agents=10):
    print(f"🚀 Iniciando Test de Longevidad ({steps} pasos, {num_agents} agentes)...")
    
    # Mocking environment variables for LLM if necessary, 
    # but we want to test the full logic including cerebro.
    # If the LLM is slow/expensive, we might mock it, but the survival mode 
    # in langgraph should trigger even without LLM if it's forced.
    
    modelo = ModeloRelacional(num_agentes=num_agents)
    
    initial_count = len(modelo.agentes)
    print(f"👥 Población inicial: {initial_count}")
    
    for i in range(1, steps + 1):
        modelo.step()
        alive_count = len(modelo.agentes)
        
        # Monitorizar un agente específico (ej. el primero)
        if alive_count > 0:
            a = modelo.agentes[0]
            print(f"Paso {i:02d} | Vivos: {alive_count:02d} | Agente {a.unique_id}: Hambre {a.necesidades['alimento']:.1f}, Salud {a.necesidades['salud']:.1f}, Recursos {a.recursos:.1f}")
        else:
            print(f"💀 ¡Extinción total en el paso {i}!")
            break
            
    final_count = len(modelo.agentes)
    deaths = initial_count - final_count
    
    print("-" * 30)
    print(f"🏁 Test Finalizado.")
    print(f"💀 Muertes totales: {deaths}")
    print(f"📈 Supervivencia: {(final_count/initial_count)*100:.1f}%")
    
    if deaths == 0:
        print("✅ ÉXITO: Todos los agentes sobrevivieron el test de longevidad.")
    elif deaths < initial_count * 0.3:
        print("⚠️ PRECAUCIÓN: Hubo algunas muertes, pero la mayoría sobrevivió.")
    else:
        print("❌ FALLO: Demasiadas muertes. El sistema de supervivencia aún es insuficiente.")

if __name__ == "__main__":
    # Limitar el número de pasos para el test rápido si se desea
    run_longevity_test(steps=30, num_agents=5)
