import pytest
from unittest.mock import MagicMock
from core.entities.agent import Agente

def test_unirse_institucion_no_attribute_error():
    modelo = MagicMock()
    modelo.mapa_size = 20
    modelo.instituciones = {}
    agente = Agente(unique_id="ag_test", modelo=modelo)
    
    # Intentar unirse a una institucion inexistente
    # Antes crasheaba con AttributeError: 'Agente' object has no attribute 'instituciones'
    accion = {"nombre": "UNIRSE_INSTITUCION", "argumentos": {"institucion_id": "nonexistent"}}
    res = agente.ejecutar_accion_final(accion)
    assert res is False

def test_invitar_normalization():
    modelo = MagicMock()
    modelo.mapa_size = 20
    modelo.agentes = []
    agente = Agente(unique_id="ag_test", modelo=modelo)
    
    # invitar no debe reportar "ACCIÓN DESCONOCIDA" (que cae en explorar)
    # sino normalizarse a "invitar_grupo" y retornar False (ya que no hay grupo/target)
    accion = {"nombre": "INVITAR", "argumentos": {"target_id": "other"}}
    res = agente.ejecutar_accion_final(accion)
    assert res is False
