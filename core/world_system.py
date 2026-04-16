import random
import math
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


TerrainType.STATS = {
    "grass": {
        "yield": 1.0,
        "energy_cost": 0.04,
        "move_difficulty": 1.0,
        "health_risk": 0.0,
    },
    "forest": {
        "yield_wood": 2.0,
        "yield_food": 1.5,
        "yield": 1.2,
        "energy_cost": 0.06,
        "move_difficulty": 1.5,
        "health_risk": 0.0,
    },
    "mountain": {
        "yield_stone": 2.0,
        "yield": 0.7,
        "energy_cost": 0.12,
        "move_difficulty": 3.0,
        "health_risk": 0.05,
    },
    "water": {
        "yield_food": 0.2,
        "yield": 0.1,
        "energy_cost": 0.10,
        "move_difficulty": 5.0,
        "health_risk": 0.02,
    },
    "desert": {
        "yield": 0.5,
        "energy_cost": 0.15,
        "move_difficulty": 1.2,
        "health_risk": 0.08,
    },
    "archaeological_site": {
        "yield": 0.3,
        "energy_cost": 0.08,
        "move_difficulty": 1.0,
        "health_risk": 0.0,
    },
}


class FastNoise:
    """Implementación simple de ruido de valor para generación de terreno sin dependencias externas."""

    def __init__(self, seed: Optional[str] = None):
        self.rand = random.Random(seed)
        self.grid = {}

    def _get_value(self, x: int, y: int) -> float:
        if (x, y) not in self.grid:
            self.grid[(x, y)] = self.rand.random()
        return self.grid[(x, y)]

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + (b - a) * (3 * t**2 - 2 * t**3)  # Smoothstep

    def get_noise(self, x: float, y: float) -> float:
        xf, yf = int(math.floor(x)), int(math.floor(y))
        dx, dy = x - xf, y - yf

        v00 = self._get_value(xf, yf)
        v10 = self._get_value(xf + 1, yf)
        v01 = self._get_value(xf, yf + 1)
        v11 = self._get_value(xf + 1, yf + 1)

        ix0 = self._lerp(v00, v10, dx)
        ix1 = self._lerp(v01, v11, dx)

        return self._lerp(ix0, ix1, dy)

    def fractal_noise(self, x: float, y: float, octaves: int = 4) -> float:
        val = 0
        freq = 1.0
        amp = 1.0
        max_val = 0
        for _ in range(octaves):
            val += self.get_noise(x * freq, y * freq) * amp
            max_val += amp
            freq *= 2.0
            amp *= 0.5
        return val / max_val


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
    def terrain_type(self):
        return self.terrain

    @terrain_type.setter
    def terrain_type(self, value):
        self.terrain = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "terrain": self.terrain.value
            if isinstance(self.terrain, TerrainType)
            else self.terrain,
            "resource": self.resource_node,
            "owner": self.owner_civ_id,
            "buildings": self.buildings,
            "is_archaeological_site": self.is_archaeological_site,
            "artifact_type": self.artifact_type,
            "artifact_value": self.artifact_value,
            "discovered_by": self.discovered_by,
            "discovery_turn": self.discovery_turn,
            "yield_mult": self.yield_rate,
            "energy_cost": self.energy_cost,
            "health_risk": self.health_risk,
            "move_difficulty": self.move_difficulty,
        }


class WorldSystem:
    def __init__(self, size: int = 20, seed: Optional[str] = None):
        self.size = size
        self.seed = seed
        self.mapa: List[List[WorldTile]] = []

        # Inicializar generadores de ruido
        seed_elev = f"{seed}_elev" if seed else None
        seed_moist = f"{seed}_moist" if seed else None
        self.elev_noise = FastNoise(seed_elev)
        self.moist_noise = FastNoise(seed_moist)

    def _get_terrain_at(self, x: int, y: int) -> TerrainType:
        """Determina el tipo de terreno basado en ruido de elevación y humedad."""
        # Escalar coordenadas para obtener rasgos más grandes
        scale = 0.1
        h = self.elev_noise.fractal_noise(x * scale, y * scale, octaves=4)
        m = self.moist_noise.fractal_noise(x * scale, y * scale, octaves=3)

        if h < 0.25:
            return TerrainType.WATER
        if h > 0.75:
            return TerrainType.MOUNTAIN

        # Terreno medio dependiente de la humedad
        if m > 0.65:
            return TerrainType.FOREST
        if m < 0.25:
            return TerrainType.DESERT

        return TerrainType.GRASS

    def generar_inicial(self):
        """Genera el mapa con la nueva lógica de biomas coherentes."""
        self.mapa.clear()
        for x in range(self.size):
            row = []
            for y in range(self.size):
                terrain = self._get_terrain_at(x, y)
                tile = WorldTile(x, y, terrain)
                self._asignar_recurso_coherente(tile)
                row.append(tile)
            self.mapa.append(row)
        return self.mapa

    def expandir(self, direccion: str, cantidad: int = 5):
        if not self.mapa:
            return False
        filas, cols = len(self.mapa), len(self.mapa[0])

        def generar_nueva_tile(nx, ny):
            terrain = self._get_terrain_at(nx, ny)
            tile = WorldTile(nx, ny, terrain)
            self._asignar_recurso_coherente(tile)
            return tile

        if direccion == "east":
            for x in range(filas):
                for dy in range(cantidad):
                    self.mapa[x].append(generar_nueva_tile(x, cols + dy))
        elif direccion == "west":
            for x in range(filas):
                for t in self.mapa[x]:
                    t.y += cantidad
                nuevas = [generar_nueva_tile(x, y) for y in range(cantidad)]
                self.mapa[x] = nuevas + self.mapa[x]
        elif direccion == "south":
            for dx in range(cantidad):
                self.mapa.append(
                    [generar_nueva_tile(filas + dx, y) for y in range(cols)]
                )
        elif direccion == "north":
            for r in self.mapa:
                for t in r:
                    t.x += cantidad
            for dx in range(cantidad):
                self.mapa.insert(dx, [generar_nueva_tile(dx, y) for y in range(cols)])
        return True

    def _asignar_recurso_coherente(self, tile: WorldTile):
        """Asigna recursos basados en el bioma con probabilidades revisadas."""
        rv = random.random()
        if tile.terrain == TerrainType.MOUNTAIN:
            if rv < 0.4:  # Más frecuente en montañas
                tile.resource_node = {
                    "type": "mineral",
                    "amount": random.randint(80, 250),
                }
        elif tile.terrain == TerrainType.FOREST:
            if rv < 0.35:
                tile.resource_node = {
                    "type": "madera",
                    "amount": random.randint(60, 180),
                }
        elif tile.terrain == TerrainType.WATER:
            if rv < 0.45:  # Más abundante
                tile.resource_node = {
                    "type": "pescado",
                    "amount": random.randint(30, 120),
                }
        elif tile.terrain == TerrainType.GRASS:
            if rv < 0.40:  # Mucho más frecuente por petición del usuario
                tile.resource_node = {
                    "type": "comida",
                    "amount": random.randint(40, 140),
                }
        elif tile.terrain == TerrainType.DESERT:
            if rv < 0.1:  # Raro pero valioso
                tile.resource_node = {"type": "oro", "amount": random.randint(100, 300)}

    def get_serializable(self):
        return [[t.to_dict() for t in row] for row in self.mapa]
