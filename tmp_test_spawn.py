#!/usr/bin/env python3
import sys
sys.path.append('.')
from api import api as api_module

def test():
    # Create an empty simulation to avoid heavy DB load
    sm = api_module.session_manager
    sm.simulations.pop('test_user_spawn', None)
    sim = sm.create_simulation('test_user_spawn', start_empty=True)
    print('Sim created:', sim is not None)

    a1 = sim.spawn_agent({'x': 0, 'y': 0})
    a2 = sim.spawn_agent({'x': 1, 'y': 1, 'rol': 'Guarda'})

    print('Agents count after spawn:', len(sim.agentes))
    if sim and sim.agentes:
        print('First agent id/name/rol:', sim.agentes[0].unique_id, getattr(sim.agentes[0], 'identidad', None).nombre if getattr(sim.agentes[0], 'identidad', None) else 'no name', sim.agentes[0].rol)
        print('Second agent id/name/rol:', sim.agentes[1].unique_id, getattr(sim.agentes[1], 'identidad', None).nombre if getattr(sim.agentes[1], 'identidad', None) else 'no name', sim.agentes[1].rol)

if __name__ == '__main__':
    test()
