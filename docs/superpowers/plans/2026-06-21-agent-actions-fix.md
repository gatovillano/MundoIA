# Plan de Implementación: Corrección de Acciones de Agentes, Sistema de Votaciones y Red Social

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolver los fallos que limitan a los agentes únicamente a votar y moverse, implementando fallbacks de planificación heurística BDI, corrigiendo bugs de atributos/normalización e integrando mapeos faltantes en la red social y compatibilidad con Postgres.

**Architecture:** Mapear en LangGraph la redirección al motor heurístico BDI si el LLM no define planes; normalizar las acciones de invitar; resolver el bug de propiedades en la clase del Agente; e implementar la conversión de `timestamp` para PostgreSQL en la red social.

**Tech Stack:** Python 3, Pytest, LangGraph, PostgreSQL (Psycopg2).

---

### Task 1: Corrección de bugs de Atributos e Invitaciones en la clase Agente

**Files:**
- Modify: `core/entities/agent.py`
- Modify: `core/entities/agent_body.py`
- Create: `tests/test_agent_actions_bugfix.py`

- [ ] **Step 1: Crear la prueba unitaria fallida**

Escribir el archivo `tests/test_agent_actions_bugfix.py` con el siguiente código:
```python
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
```

- [ ] **Step 2: Ejecutar la prueba y validar que falla**

Ejecutar: `pytest tests/test_agent_actions_bugfix.py -v`
Esperado: Falla con `AttributeError: 'Agente' object has no attribute 'instituciones'` o similar.

- [ ] **Step 3: Implementar la solución en `agent.py` y `agent_body.py`**

Modificar `core/entities/agent.py` reemplazando en `unirse_institucion`:
```python
            elif tipo == "unirse_institucion":
                inst_id = params.get("institucion_id") or params.get("inst_id") or params.get("id") or params.get("nombre") or params.get("name")
                inst_obj = None
                if inst_id:
                    inst_obj = self.modelo.instituciones.get(str(inst_id))
                    if not inst_obj:
                        for iid, inst in self.modelo.instituciones.items():
                            if getattr(inst, "nombre", "").lower() == str(inst_id).lower():
                                inst_obj = inst
                                inst_id = iid
                                break
                else:
                    # Buscar institución en la casilla actual
                    for iid, inst in self.modelo.instituciones.items():
                        if inst.x == self.x and inst.y == self.y:
                            inst_obj = inst
                            inst_id = iid
                            break
```
Y añadir `"invitar"` a la normalización de `tipo` al inicio de `ejecutar_accion_final` en `core/entities/agent.py`:
```python
        if tipo in ["invitar_a_grupo", "invitar_al_grupo", "invitar_agente", "invitar"]: tipo = "invitar_grupo"
```
Hacer las mismas dos modificaciones idénticas en `core/entities/agent_body.py`.

- [ ] **Step 4: Ejecutar la prueba y verificar éxito**

Ejecutar: `pytest tests/test_agent_actions_bugfix.py -v`
Esperado: PASS

- [ ] **Step 5: Guardar en Git**

Ejecutar:
```bash
git add core/entities/agent.py core/entities/agent_body.py tests/test_agent_actions_bugfix.py
git commit -m "fix: resolve agent institutions attribute error and invitar action normalization"
```

---

### Task 2: Condicionar acción de votar en fallbacks

**Files:**
- Modify: `agents/cerebro_llm.py`
- Create: `tests/test_fallback_votar.py`

- [ ] **Step 1: Crear la prueba unitaria fallida**

Escribir el archivo `tests/test_fallback_votar.py` con el siguiente código:
```python
import pytest
from unittest.mock import MagicMock
from agents.cerebro_llm import CerebroLLM

def test_fallback_votar_filtering():
    modelo = MagicMock()
    modelo.asambleas_activas = []
    agente = MagicMock()
    agente.modelo = modelo
    agente.unique_id = "ag_test"
    agente.personalidad = {"curiosidad": 0.8}
    agente.necesidades = {"alimento": 10, "salud": 10, "descanso": 10}
    
    cllm = CerebroLLM()
    cllm.model = "mock-model"
    
    # 1. Sin asambleas activas en VOTACION, no debe retornar VOTAR
    for _ in range(50):
        res = cllm._generar_fallback_contextual(agente, None)
        assert res["accion"]["nombre"] != "VOTAR"
        
    # 2. Con asamblea activa en VOTACION en la cual no ha participado, sí puede retornar VOTAR
    asamblea = {"estado": "VOTACION", "participantes_votos": {}}
    modelo.asambleas_activas = [asamblea]
    
    votos_encontrados = False
    for _ in range(200):
        res = cllm._generar_fallback_contextual(agente, None)
        if res["accion"]["nombre"] == "VOTAR":
            votos_encontrados = True
            break
    assert votos_encontrados is True
```

- [ ] **Step 2: Ejecutar la prueba y validar que falla**

Ejecutar: `pytest tests/test_fallback_votar.py -v`
Esperado: FAIL (el primer assert falla porque VOTAR es seleccionado aunque no haya asambleas).

- [ ] **Step 3: Implementar la solución en `cerebro_llm.py`**

Modificar `agents/cerebro_llm.py` en `_generar_fallback_contextual` para condicionar `"VOTAR"`:
```python
        # Comprobar si hay una asamblea en fase de votación donde este agente pueda votar
        hay_voto_activo = False
        if hasattr(agente_yo.modelo, "asambleas_activas"):
            for asamblea in agente_yo.modelo.asambleas_activas:
                if asamblea.get("estado") == "VOTACION" and agente_yo.unique_id not in asamblea.get("participantes_votos", {}):
                    hay_voto_activo = True
                    break

        # Estado estable: decidir según personalidad
        else:
            if hostilidad > 0.7:
                ...
            elif amabilidad > 0.7:
                ...
            elif curiosidad > 0.7:
                acciones_curiosas = ["BUSCAR_INFO", "MOVER", "RECOLECTAR", "CONSTRUIR", "UNIRSE_FACCION", "UNIRSE_INSTITUCION", "USAR_INSTITUCION", "INVITAR", "PROPONER_LEY", "SUSURRAR"]
                if hay_voto_activo:
                    acciones_curiosas.append("VOTAR")
                accion_nombre = random.choice(acciones_curiosas)
                ...
            else:
                acciones_default = ["HABLAR", "RECOLECTAR", "MOVER", "CONSTRUIR", "UNIRSE_FACCION", "UNIRSE_INSTITUCION", "USAR_INSTITUCION", "INVITAR", "FUNDAR_FACCION", "PROPONER_LEY", "SUSURRAR"]
                if hay_voto_activo:
                    acciones_default.append("VOTAR")
                accion_nombre = random.choice(acciones_default)
```

- [ ] **Step 4: Ejecutar la prueba y verificar éxito**

Ejecutar: `pytest tests/test_fallback_votar.py -v`
Esperado: PASS

- [ ] **Step 5: Guardar en Git**

Ejecutar:
```bash
git add agents/cerebro_llm.py tests/test_fallback_votar.py
git commit -m "fix: restrict random VOTAR action to steps with active voting phase"
```

---

### Task 3: Implementar fallback heurístico BDI en LangGraph

**Files:**
- Modify: `agents/cerebro_langgraph.py`
- Create: `tests/test_langgraph_bdi_fallback.py`

- [ ] **Step 1: Crear la prueba unitaria fallida**

Escribir el archivo `tests/test_langgraph_bdi_fallback.py` con el siguiente código:
```python
import pytest
from unittest.mock import MagicMock, patch
from agents.cerebro_langgraph import actuar, AgentState

def test_actuar_heuristic_bdi_fallback():
    modelo = MagicMock()
    modelo.mapa = [[MagicMock() for _ in range(20)] for _ in range(20)]
    modelo.agentes = []
    
    agente = MagicMock()
    agente.modelo = modelo
    agente.unique_id = "ag_test"
    agente.intenciones.plan_actual = None
    
    from agents.bdi_components import TipoDeseo, SistemaDeseos, DeseoBDI
    agente.deseos = SistemaDeseos()
    agente.deseos.deseos[TipoDeseo.SUPERVIVENCIA] = DeseoBDI(TipoDeseo.SUPERVIVENCIA, 1.0)
    agente.deseos.pesos = {TipoDeseo.SUPERVIVENCIA: 1.0}
    
    agente.necesidades = {"alimento": 2.0, "salud": 10.0, "descanso": 10.0, "social": 10.0}
    agente.inventario = {"comida": 1}
    
    state: AgentState = {
        "agente_yo_id": "ag_test",
        "agente_otro_id": None,
        "modelo_instance": modelo,
        "pensamiento_actual": "",
        "accion_elegida": {},
        "info_externa": "",
        "mensaje_generado": "",
        "esta_poseido": False,
        "peticion_arquitecto": None,
        "dilema_usuario": None,
        "es_global": False,
        "es_grupal": False,
        "privado": False,
        "destinatario_id": None,
        "planes": [],
        "beliefs": {},
        "desires": {},
        "intentions": [],
    }
    
    modelo.get_agent_by_id.return_value = agente
    
    with patch("agents.cerebro_langgraph.cerebro_llm") as mock_llm:
        mock_llm.generar_pensamiento_y_accion.return_value = {
            "pensamiento": "No sé qué hacer.",
            "mensaje": "...",
            "accion": {"nombre": "HABLAR"},
            "intentions": []
        }
        
        res = actuar(state)
        
        assert agente.intenciones.plan_actual is not None
        assert agente.intenciones.plan_actual.meta == "Comer para sobrevivir"
```

- [ ] **Step 2: Ejecutar la prueba y validar que falla**

Ejecutar: `pytest tests/test_langgraph_bdi_fallback.py -v`
Esperado: FAIL (`plan_actual` es None)

- [ ] **Step 3: Implementar la solución en `cerebro_langgraph.py`**

Modificar la rama `else` de `actuar` en `agents/cerebro_langgraph.py`:
```python
    else:
        # Fallback al sistema BDI Heurístico si no hay intenciones del LLM/fallback
        # Reconstruir 'entorno' como lo hace `_bdi_deliberar`
        agente_yo.modelo.log(
            f"🧠 [BDI] Agente {agente_yo.unique_id} genera plan heurístico (sin intenciones LLM).",
            categoria="sistema",
        )
        
        # Copiar lógica de entorno para BDI Heurístico
        agentes_todos = [a for a in agente_yo.modelo.agentes if a.unique_id != agente_yo.unique_id]
        amigos_lejos = []
        for a in agentes_todos:
            dist = abs(a.x - agente_yo.x) + abs(a.y - agente_yo.y)
            afinidad = agente_yo.memoria.obtener_fuerza(a.unique_id) if hasattr(agente_yo.memoria, 'obtener_fuerza') else 0
            if afinidad > 5 and dist > 4:
                amigos_lejos.append({'id': a.unique_id, 'x': a.x, 'y': a.y, 'nombre': a.display_name})
        
        miembros_faccion = []
        if agente_yo.grupo_id:
            for a in agentes_todos:
                if a.grupo_id == agente_yo.grupo_id:
                    dist = abs(a.x - agente_yo.x) + abs(a.y - agente_yo.y)
                    if dist > 4:
                        miembros_faccion.append({'id': a.unique_id, 'x': a.x, 'y': a.y})

        tiles_interesantes = []
        mapa = agente_yo.modelo.mapa
        map_size = len(mapa)
        for _ in range(40):
            rx, ry = random.randint(0, map_size-1), random.randint(0, map_size-1)
            tile = mapa[rx][ry]
            dist = abs(rx - agente_yo.x) + abs(ry - agente_yo.y)
            if dist < 2: continue
            
            interesante = False
            arq = getattr(agente_yo.alma, 'arquetipo', None)
            
            if getattr(tile, 'is_archaeological_site', False):
                interesante = True
            from core.entities.terrain import TerrainType
            from agents.personality import Arquetipo
            if arq == Arquetipo.EXPLORADOR and tile.terrain_type in [TerrainType.FOREST, TerrainType.WATER]: interesante = True
            elif arq in [Arquetipo.CONSTRUCTOR, Arquetipo.GUERRERO, Arquetipo.MERCADER] and tile.terrain_type == TerrainType.MOUNTAIN: interesante = True
            elif arq == Arquetipo.SANADOR and tile.terrain_type == TerrainType.FOREST: interesante = True
            elif tile.resource_node and tile.resource_node.get('amount', 0) > 0: interesante = True
            
            if interesante:
                tiles_interesantes.append({'x': rx, 'y': ry, 'tipo': tile.terrain_type, 'dist': dist})
        
        tiles_interesantes.sort(key=lambda t: t['dist'])

        entorno = {
            "agentes_cercanos": [a for a in agentes_todos if abs(a.x - agente_yo.x) <= 2 and abs(a.y - agente_yo.y) <= 2],
            "agentes_lejos": [{'id': a.unique_id, 'x': a.x, 'y': a.y} for a in agentes_todos if abs(a.x - agente_yo.x) > 3 or abs(a.y - agente_yo.y) > 3],
            "amigos_lejos": amigos_lejos,
            "miembros_faccion_lejos": miembros_faccion,
            "tiles_interesantes": tiles_interesantes,
            "grupos_disponibles": [
                {"id": gid, "nombre": civ.nombre, "vocero": getattr(civ, "vocero_id", None), "miembros": len([a for a in agentes_todos if getattr(a, "grupo_id", None) == gid])}
                for gid, civ in agente_yo.modelo.civilizaciones.items()
            ]
        }

        planes_heuristicos = agente_yo.intenciones.generar_planes_candidatos(agente_yo, entorno)
        mejor_plan = None
        if planes_heuristicos:
            mejor_plan = agente_yo.intenciones.seleccionar_mejor_plan(agente_yo, planes_heuristicos)
        
        if mejor_plan:
            agente_yo.intenciones.plan_actual = mejor_plan
            accion_dict = agente_yo.tick_bdi()
        else:
            accion_dict = decision.get(
                "accion", {"nombre": "HABLAR", "argumentos": {"mensaje": "..."}}
            )
```

- [ ] **Step 4: Ejecutar la prueba y verificar éxito**

Ejecutar: `pytest tests/test_langgraph_bdi_fallback.py -v`
Esperado: PASS

- [ ] **Step 5: Guardar en Git**

Ejecutar:
```bash
git add agents/cerebro_langgraph.py tests/test_langgraph_bdi_fallback.py
git commit -m "feat: fallback to heuristic BDI plan generation in LangGraph actuar node when LLM doesn't yield plans"
```

---

### Task 4: Completar métodos de SocialRecSys e integrar TO_TIMESTAMP en Postgres

**Files:**
- Modify: `core/modelo.py`
- Create: `tests/test_social_recsys.py`

- [ ] **Step 1: Crear la prueba unitaria fallida**

Escribir el archivo `tests/test_social_recsys.py` con el siguiente código:
```python
import pytest
from unittest.mock import MagicMock
from core.modelo import SocialRecSys

def test_social_recsys_missing_methods():
    db = MagicMock()
    db.execute.return_value = []
    
    recsys = SocialRecSys(db=db, user_id="test_user", load_from_db=False)
    
    # 1. Test get_siguiendo and follow
    assert recsys.get_siguiendo("ag_1") == []
    recsys.follow("ag_1", "ag_2")
    assert recsys.get_siguiendo("ag_1") == ["ag_2"]
    
    # 2. Test get_seguidores
    assert recsys.get_seguidores("ag_2") == ["ag_1"]
    
    # 3. Test comentar and get_interacciones_usuario
    post = recsys.crear_post(user_id="test_user", autor_id="ag_2", contenido="Hola mundo", tipo="texto", temas=[], timestamp=123456)
    
    recsys.comentar(post.id, "ag_1", "Qué buen post")
    recsys.likear_post(post.id, "ag_1")
    interacciones = recsys.get_interacciones_usuario("ag_2")
    
    likes = [i for i in interacciones if i["tipo"] == "like"]
    comentarios = [i for i in interacciones if i["tipo"] == "comentario"]
    
    assert len(likes) == 1
    assert len(comentarios) == 1
    assert likes[0]["autor_interaccion"] == "ag_1"
    assert comentarios[0]["autor_interaccion"] == "ag_1"
```

- [ ] **Step 2: Ejecutar la prueba y validar que falla**

Ejecutar: `pytest tests/test_social_recsys.py -v`
Esperado: FAIL with AttributeError (falta get_siguiendo).

- [ ] **Step 3: Implementar métodos y conversiones de tiempo en `SocialRecSys`**

Modificar la clase `SocialRecSys` en `core/modelo.py` añadiendo estas funciones y corrigiendo la inserción / lectura de base de datos:

Añadir al final de la clase `SocialRecSys` en `core/modelo.py`:
```python
    def comentar(self, post_id, autor_id, contenido):
        return self.agregar_comentario(post_id, autor_id, contenido)

    def get_siguiendo(self, follower_id) -> list:
        return list(self.seguidos.get(follower_id, []))

    def get_seguidores(self, followed_id) -> list:
        return [fid for fid, seg in self.seguidos.items() if followed_id in seg]

    def get_interacciones_usuario(self, user_id) -> list:
        interacciones = []
        for pid, post in self.interest_recsys.posts.items():
            if post.autor_id == user_id:
                for liker in post.likes_por:
                    interacciones.append({
                        "tipo": "like",
                        "autor_interaccion": liker,
                        "contenido_post": post.contenido[:30] + "..." if len(post.contenido) > 30 else post.contenido,
                        "timestamp": post.timestamp
                    })
                comentarios = self.interest_recsys.comentarios.get(pid, [])
                for comment in comentarios:
                    interacciones.append({
                        "tipo": "comentario",
                        "autor_interaccion": comment["autor_id"],
                        "contenido_post": post.contenido[:30] + "..." if len(post.contenido) > 30 else post.contenido,
                        "contenido_interaccion": comment["contenido"],
                        "timestamp": comment.get("timestamp", 0)
                    })
        return interacciones
```

Y en `crear_post()`, cambiar la sentencia `INSERT INTO posts_sociales` para usar `TO_TIMESTAMP(%s)` en el campo de timestamp (aprox línea 210):
```python
            result = self.db.execute("""
                INSERT INTO posts_sociales (id, user_id, autor_id, contenido, tipo, temas, timestamp, likes, likes_por, comentarios)
                VALUES (%s, %s, %s, %s, %s, %s, TO_TIMESTAMP(%s), %s, %s, %s)
                ON CONFLICT (id, user_id) DO UPDATE SET
                    contenido = EXCLUDED.contenido,
                    timestamp = EXCLUDED.timestamp
            """, (post_id, user_id, autor_id, contenido, tipo, json.dumps(temas), timestamp or 0, 0, json.dumps([]), json.dumps([])))
```

Y en `_cargar_posts_desde_db()`, convertir el datetime a float:
```python
        for row in rows:
            post_id, autor_id, contenido, tipo, temas_json, timestamp, likes, likes_por_json, comentarios_json = row
            if hasattr(timestamp, "timestamp"):
                timestamp = timestamp.timestamp()
```

- [ ] **Step 4: Ejecutar la prueba y verificar éxito**

Ejecutar: `pytest tests/test_social_recsys.py -v`
Esperado: PASS

- [ ] **Step 5: Guardar en Git**

Ejecutar:
```bash
git add core/modelo.py tests/test_social_recsys.py
git commit -m "fix: implement missing SocialRecSys methods and fix Postgres timestamp casting"
```
