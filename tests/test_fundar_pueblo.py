import pytest
from core.modelo import ModeloRelacional, Agente
from core.world_system import WorldSystem, TerrainType


def setup_model(size=10):
    m = ModeloRelacional(num_agentes=0, start_empty=True)
    m.world = WorldSystem(size=size, seed="test")
    m.mapa = m.world.generar_inicial()
    m.mapa_size = size
    return m


def test_fundar_pueblo_crea_centro_2x2():
    model = setup_model(10)

    # Crear líder y fundar grupo
    leader = Agente("leader", model, recursos=200, x=2, y=2)
    model.agentes.append(leader)
    res = leader.fundar_grupo("PuebloPrueba", "Una descripción suficientemente larga para validar la fundación del grupo.")
    assert isinstance(res, dict) and res.get("exito") is True
    grupo_id = leader.grupo_id
    assert grupo_id in model.civilizaciones

    # Añadir miembros para alcanzar el mínimo (5)
    for i in range(4):
        a = Agente(f"m{i}", model, recursos=50, x=2 + (i + 1), y=2)
        a.grupo_id = grupo_id
        model.agentes.append(a)

    # Ejecutar fundar_pueblo desde el líder
    ok, msg = leader.fundar_pueblo()
    assert ok is True, msg

    # Comprobar infraestructura creada
    centros = [e for e in model.infraestructura if e.get("tipo") == "CentroPueblo" and e.get("grupo_id") == grupo_id]
    assert len(centros) >= 1, "No se creó CentroPueblo en infraestructura"
    centro = centros[0]

    # Verificar que ocupa 4 casillas y que las casillas están marcadas
    tiles = centro.get("tiles", [])
    assert len(tiles) == 4

    for (x, y) in tiles:
        assert 0 <= x < len(model.mapa)
        assert 0 <= y < len(model.mapa[0])
        tile = model.mapa[x][y]
        assert tile.owner_civ_id == grupo_id
        # El edificio debe estar en la lista de buildings de la casilla
        assert any(b.get("id") == centro.get("id") for b in tile.buildings)
        # Terreno opcionalmente marcado como PATH
        assert getattr(tile, "terrain", None) == TerrainType.PATH
