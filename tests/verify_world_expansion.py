import sys
import os
sys.path.append("/home/gato/MundoIA/multiagent_simulation")
from core.modelo import ModeloRelacional, TerrainType, WeatherType

def verify():
    print("Initializing Model...")
    modelo = ModeloRelacional(num_agentes=1)
    agente = modelo.agentes[0]
    
    # 1. Check Map
    print(f"Map Size: {len(modelo.mapa)}x{len(modelo.mapa[0])}")
    tile = modelo.mapa[0][0]
    print(f"Tile (0,0): {tile.terrain_type}, Resource: {tile.resource_node}")
    if not hasattr(tile, 'terrain_type'):
        print("FAIL: Tile object missing terrain_type")
        return

    # 2. Check Weather
    print(f"Weather: {modelo.weather}")
    
    # 3. Test Movement
    print("Testing Movement...")
    agente.x, agente.y = 0, 0
    # Find a valid neighbor
    target_x, target_y = 0, 1
    if modelo.mapa[0][1].terrain_type != TerrainType.WATER:
        agente.x, agente.y = 0, 1
        print(f"Agent moved to (0, 1)")
    else:
        print("Target is water, skipping move test")

    # 4. Test Construction
    print("Testing Construction...")
    agente.dinero = 1000
    agente.recursos = 1000
    # Ensure current tile is valid
    current_tile = modelo.mapa[agente.x][agente.y]
    current_tile.terrain_type = TerrainType.GRASS # Force valid terrain
    current_tile.buildings = [] # Clear existing
    
    exito, msg = modelo.construir_edificio(agente, "Torre de Vigilancia")
    print(f"Construction Result: {exito}, {msg}")
    
    if exito and len(current_tile.buildings) > 0:
        print("PASS: Building added to tile")
    else:
        print("FAIL: Building not added")

    # 5. Test Gathering
    print("Testing Gathering...")
    current_tile.resource_node = {"type": "food", "amount": 50}
    initial_resources = agente.recursos
    agente.recolectar()
    print(f"Resources: {initial_resources} -> {agente.recursos}")
    if agente.recursos > initial_resources:
        print("PASS: Resources gathered")
    else:
        print("FAIL: No resources gathered")

if __name__ == "__main__":
    verify()
