from core.world_system import WorldSystem, TerrainType

def test_generation():
    ws = WorldSystem(size=20, seed="42")
    mapa = ws.generar_inicial()
    
    symbols = {
        TerrainType.WATER: "~",
        TerrainType.MOUNTAIN: "^",
        TerrainType.FOREST: "T",
        TerrainType.GRASS: ".",
        TerrainType.DESERT: "D"
    }
    
    print("Mapa Generado (20x20):")
    for row in mapa:
        line = "".join(symbols.get(tile.terrain, "?") for tile in row)
        print(line)

    # Contar biomas
    stats = {}
    for row in mapa:
        for tile in row:
            t = tile.terrain
            stats[t] = stats.get(t, 0) + 1
    
    print("\nEstadísticas de Biomas:")
    for t, count in stats.items():
        print(f"{t.value}: {count} ({count/400*100:.1f}%)")

if __name__ == "__main__":
    test_generation()
