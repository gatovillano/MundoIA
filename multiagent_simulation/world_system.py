import random
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

class TerrainType(str, Enum):
    GRASS = "grass"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    WATER = "water"
    DESERT = "desert"
    ARCHAEOLOGICAL_SITE = "archaeological_site"
    PATH = "path"
    VOID = "void"

    STATS = {
        "grass": {"yield": 1.0, "energy_cost": 0.04, "move_difficulty": 1.0, "health_risk": 0.0},
        "forest": {"yield_wood": 2.0, "yield_food": 1.5, "yield": 1.2, "energy_cost": 0.06, "move_difficulty": 1.5, "health_risk": 0.0},
        "mountain": {"yield_stone": 2.0, "yield": 0.7, "energy_cost": 0.12, "move_difficulty": 3.0, "health_risk": 0.05},
        "water": {"yield_food": 0.2, "yield": 0.1, "energy_cost": 0.10, "move_difficulty": 5.0, "health_risk": 0.02},
        "desert": {"yield": 0.5, "energy_cost": 0.15, "move_difficulty": 1.2, "health_risk": 0.08},
        "archaeological_site": {"yield": 0.3, "energy_cost": 0.08, "move_difficulty": 1.0, "health_risk": 0.0},
    }

class WorldTile:
    def __init__(self, x: int, y: int, terrain: TerrainType = TerrainType.GRASS):
        self.x = x
        self.y = y
        self.terrain = terrain
        self.resource_node = None
        self.owner_civ_id = None
        self.buildings = []
        self.is_archaeological_site = False
        self.artifact_type = None
        self.artifact_value = 0
        self.discovered_by = None
        self.discovery_turn = None
        self.data = {}

        terrain_str = terrain.value if isinstance(terrain, TerrainType) else terrain
        stats = TerrainType.STATS.get(terrain_str, TerrainType.STATS["grass"])
        self.yield_rate = stats.get("yield", 1.0)
        self.energy_cost = stats.get("energy_cost", 0.05)
        self.move_difficulty = stats.get("move_difficulty", 1.0)
        self.health_risk = stats.get("health_risk", 0.0)

    @property
    def terrain_type(self): return self.terrain
    @terrain_type.setter
    def terrain_type(self, value): self.terrain = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x, "y": self.y,
            "terrain": self.terrain.value if isinstance(self.terrain, TerrainType) else self.terrain,
            "resource": self.resource_node, "owner": self.owner_civ_id,
            "buildings": self.buildings, "is_archaeological_site": self.is_archaeological_site,
            "artifact_type": self.artifact_type, "artifact_value": self.artifact_value,
            "discovered_by": self.discovered_by, "discovery_turn": self.discovery_turn
        }

class WorldSystem:
    def __init__(self, size: int = 20, seed: Optional[str] = None):
        self.size = size
        self.seed = seed
        self.mapa: List[List[WorldTile]] = []
        if seed: random.seed(seed)

    def generar_inicial(self):
        """Genera el mapa con la lógica de distribución original de producción."""
        self.mapa.clear()
        for x in range(self.size):
            row = []
            for y in range(self.size):
                rv = random.random()
                if rv < 0.15: # 15% Montañas
                    terrain = TerrainType.MOUNTAIN
                    tile = WorldTile(x, y, terrain)
                    if random.random() < 0.3: tile.resource_node = {"type": "mineral", "amount": random.randint(50, 200)}
                elif rv < 0.35: # 20% Bosques
                    terrain = TerrainType.FOREST
                    tile = WorldTile(x, y, terrain)
                    if random.random() < 0.25: tile.resource_node = {"type": "madera", "amount": random.randint(40, 150)}
                elif rv < 0.50: # 15% Agua
                    terrain = TerrainType.WATER
                    tile = WorldTile(x, y, terrain)
                    if random.random() < 0.2: tile.resource_node = {"type": "pescado", "amount": random.randint(20, 100)}
                else: # 50% Pasto
                    terrain = TerrainType.GRASS
                    tile = WorldTile(x, y, terrain)
                    if random.random() < 0.1: tile.resource_node = {"type": "comida", "amount": random.randint(30, 120)}
                row.append(tile)
            self.mapa.append(row)
        return self.mapa

    def expandir(self, direccion, cantidad=5):
        if not self.mapa: return False
        filas, cols = len(self.mapa), len(self.mapa[0])
        # Re-utilizamos la misma lógica de distribución para la expansión
        def generar_tile_random(nx, ny):
            rv = random.random()
            if rv < 0.15: t = TerrainType.MOUNTAIN
            elif rv < 0.35: t = TerrainType.FOREST
            elif rv < 0.50: t = TerrainType.WATER
            else: t = TerrainType.GRASS
            tile = WorldTile(nx, ny, t)
            self._asignar_recurso_original(tile)
            return tile

        if direccion == "east":
            for x in range(filas):
                for dy in range(cantidad): self.mapa[x].append(generar_tile_random(x, cols + dy))
        elif direccion == "west":
            for x in range(filas):
                for t in self.mapa[x]: t.y += cantidad
                nuevas = [generar_tile_random(x, y) for y in range(cantidad)]
                self.mapa[x] = nuevas + self.mapa[x]
        elif direccion == "south":
            for dx in range(cantidad):
                self.mapa.append([generar_tile_random(filas + dx, y) for y in range(cols)])
        elif direccion == "north":
            for r in self.mapa:
                for t in r: t.x += cantidad
            for dx in range(cantidad):
                self.mapa.insert(dx, [generar_tile_random(dx, y) for y in range(cols)])
        return True

    def _asignar_recurso_original(self, tile):
        if tile.terrain == TerrainType.MOUNTAIN and random.random() < 0.3: tile.resource_node = {"type": "mineral", "amount": 100}
        elif tile.terrain == TerrainType.FOREST and random.random() < 0.25: tile.resource_node = {"type": "madera", "amount": 100}
        elif tile.terrain == TerrainType.WATER and random.random() < 0.2: tile.resource_node = {"type": "pescado", "amount": 100}
        elif tile.terrain == TerrainType.GRASS and random.random() < 0.1: tile.resource_node = {"type": "comida", "amount": 100}

    def get_serializable(self):
        return [[t.to_dict() for t in row] for row in self.mapa]
