#!/usr/bin/env python3
import sys
import time
sys.path.append('.')
from api import api as api_module

# Crear simulación de prueba
sm = api_module.session_manager
sm.simulations.pop('debug_voto', None)
sim = sm.create_simulation('debug_voto', start_empty=True)
print('Created sim:', sim is not None)

# Asegurar una civilización/facción para votos locales
from core.entities.faction import Civilizacion
sim.civilizaciones['FAC1'] = Civilizacion('FAC1', 'FAC1', '#ffffff', user_id=sim.user_id)

# Spawn agents y asignarles la misma facción
agents = []
for i in range(5):
    a = sim.spawn_agent({'x': i, 'y': 0})
    a.grupo_id = 'FAC1'
    agents.append(a)

print('Spawned', len(agents), 'agents')

# Proponer una ley local por el primer agente
res = agents[0].proponer_ley('LeyTest', 'Reducir impuestos para prueba', alcance='local')
print('Proposed:', res)

# Ejecutar varios pasos para observar el flujo de debate/votación
for step in range(20):
    print('\n=== STEP', step, 'sim.paso_actual=', sim.paso_actual, '===')
    sim.step()
    print(' Asambleas count:', len(sim.asambleas_globales))
    for a in sim.asambleas_globales:
        print('  AS:', a.get('id'), 'estado:', a.get('estado'), 'pasos_restantes:', a.get('pasos_restantes'), 'turno_idx:', a.get('agente_turno_idx'), 'votos_si:', a.get('votos_si'), 'votos_no:', a.get('votos_no'), 'participantes:', len(a.get('participantes_votos', {})))
    # Mostrar propuestas y sus contadores
    print(' Propuestas count:', len(sim.facciones_leyes.get('propuestas', [])))
    for p in sim.facciones_leyes.get('propuestas', []):
        print('  Prop:', p.get('id'), 'estado:', p.get('estado'), 'votos_si:', p.get('votos_si'), 'votos_no:', p.get('votos_no'), 'votantes:', p.get('votantes'))

    # Mostrar últimos logs relevantes
    last_logs = sim.historial_logs[-20:]
    for lg in last_logs:
        if lg['categoria'] in ('consenso', 'sistema', 'error') or 'VOT' in lg['mensaje'].upper() or 'ASAMBLEA' in lg['mensaje'].upper():
            print('  LOG:', lg['paso'], lg['categoria'], lg['mensaje'])

    time.sleep(0.05)

print('\nFinal asambleas:', sim.asambleas_globales)
print('Final propuestas:', sim.facciones_leyes.get('propuestas', []))
