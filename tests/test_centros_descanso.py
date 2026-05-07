import pytest
from core.modelo import ModeloRelacional, Agente
from core.world_system import WorldSystem


def setup_model(size=10):
    m = ModeloRelacional(num_agentes=0, start_empty=True)
    m.world = WorldSystem(size=size, seed="test")
    m.mapa = m.world.generar_inicial()
    m.mapa_size = size
    return m


def test_proximity_blocks_building():
    model = setup_model(10)
    a1 = Agente("a1", model, recursos=100, x=2, y=2)
    model.agentes.append(a1)
    ok, msg = model.construir_edificio(a1, "Centro de Descanso")
    assert ok is True, msg

    # Construir muy cerca (Manhattan < 6) debe fallar
    a2 = Agente("a2", model, recursos=100, x=2, y=3)
    model.agentes.append(a2)
    ok2, msg2 = model.construir_edificio(a2, "Centro de Descanso")
    assert ok2 is False
    assert "cercano" in msg2 or "Límite" in msg2


def test_global_limit_enforced():
    # Ahora no hay límite global de centros, solo restricción de proximidad
    model = setup_model(20)  # mapa más grande para caber múltiples centros distantes
    # Crear 6 agentes en posiciones suficientemente separadas (distancia >= 6)
    # Todas las coordenadas son en terrenos GRASS (válidos para Centros de Descanso)
    coords = [(0, 0), (0, 10), (0, 19), (19, 0), (19, 19), (15, 15)]
    created = 0
    for i, (x, y) in enumerate(coords):
        a = Agente(f"a{i}", model, recursos=100, x=x, y=y)
        model.agentes.append(a)
        ok, msg = model.construir_edificio(a, "Centro de Descanso")
        assert ok is True, f"Fallo al construir centro {i} en ({x},{y}): {msg}"
        created += 1

    # Verificar que se crearon todos los centros (sin límite global)
    assert created == 6

    # Intentar construir un centro demasiado cerca de uno existente debe fallar
    a_close = Agente("a_close", model, recursos=100, x=1, y=1)  # cerca de (0,0)
    model.agentes.append(a_close)
    ok_close, msg_close = model.construir_edificio(a_close, "Centro de Descanso")
    assert ok_close is False
    assert "cercano" in msg_close
