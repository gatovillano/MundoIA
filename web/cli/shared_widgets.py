"""
MUNDO IA - Shared UI Widgets
Componentes visuales comunes para las TUIs Local y Remota.
"""

import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from textual.app import ComposeResult
from textual.widgets import Static, Button, Label, RichLog, Input
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual import events

from core.modelo import TerrainType

# --- PALETA Y ESTILOS ---

BRAILLE_PATTERNS = {
    TerrainType.GRASS: "\u2840\u2880\u2801\u2808", 
    TerrainType.FOREST: "\u28ff\u28fe\u28f7\u28fb", 
    TerrainType.MOUNTAIN: "\u2803\u2818\u2806\u2830", 
    TerrainType.WATER: "\u2824\u2844\u2888\u2822",    
    TerrainType.DESERT: "\u2824\u2812\u2848\u2884",   
}

RESOURCE_COLORS = {
    "food": "bold bright_green", "wood": "bold yellow", "stone": "bold grey70",
    "iron": "bold steel_blue1", "gold": "bold yellow1", "water": "bold dodger_blue2",
    "gem": "bold magenta", "herb": "bold green3", "coal": "bold grey30", "oil": "bold dark_orange3",
}

# --- WIDGETS ---

class UltraMapWidget(Static):
    """Mapa de alta resolución con texturas Braille."""
    map_data = reactive(None)
    agents_data = reactive([])
    selected_tile = reactive(None)
    
    def render(self) -> str:
        if not self.map_data:
            return "[bold yellow]Sincronizando con el Mundo...[/bold yellow]"
        
        mapa = self.map_data
        cols = len(mapa)
        rows = len(mapa[0]) if cols > 0 else 0
        lines = []
        
        TERRAIN_BG = {
            "grass": "on green", "forest": "on dark_green", "mountain": "on grey19",
            "water": "on blue", "desert": "on yellow4", "archaeological_site": "on dark_magenta",
        }
        
        for y in range(rows):
            line = ""
            for x in range(cols):
                tile = mapa[x][y]
                if not tile:
                    line += "  "
                    continue
                
                # Obtener agentes en esta posición (soporta tanto objetos Agente como dicts JSON)
                agentes_here = []
                for a in self.agents_data:
                    ax = a.x if hasattr(a, 'x') else a.get('x')
                    ay = a.y if hasattr(a, 'y') else a.get('y')
                    if ax == x and ay == y:
                        agentes_here.append(a)
                
                # Extraer info del terreno/baldosa
                if hasattr(tile, 'terrain_type'): # Es objeto Tile
                    terrain = tile.terrain_type.value
                    has_site = bool(tile.is_archaeological_site)
                    discovered = bool(tile.discovered_by)
                    resource = tile.resource_node['type'] if tile.resource_node else None
                else: # Es dict JSON
                    terrain = tile.get('terrain', 'grass')
                    has_site = bool(tile.get('is_archaeological_site'))
                    discovered = bool(tile.get('discovered_by'))
                    resource = tile.get('resource', {}).get('type') if tile.get('resource') else None

                bg_style = TERRAIN_BG.get(terrain, "on black")
                char = "  "
                fg_color = "white"
                
                if agentes_here:
                    agente = agentes_here[0]
                    # Soporte para objeto Agente o dict
                    rol = agente.rol if hasattr(agente, 'rol') else agente.get('rol')
                    is_possessed = getattr(agente, 'is_possessed', False) if hasattr(agente, 'is_possessed') else agente.get('is_possessed')
                    
                    if is_possessed:
                        char = "🕹 "
                        fg_color = "bold bright_white on fuchsia"
                        bg_style = ""
                    else:
                        char = "⚉ " if rol == 'Líder' else "@ "
                        fg_color = "bold yellow1" if rol == 'Líder' else "bold cyan"
                elif has_site:
                    char = "🕌 " if discovered else "❓ "
                    fg_color = "bold bright_magenta"
                elif resource:
                    char = f"{resource[0].upper()} "
                    fg_color = RESOURCE_COLORS.get(resource, "bold white")
                else:
                    patterns = BRAILLE_PATTERNS.get(terrain, " . ")
                    char = f"{random.choice(patterns)} "
                    fg_color = "white"
                
                style = f"{fg_color} {bg_style}"
                if self.selected_tile == (x, y):
                    style = "bold reverse white"
                
                line += f"[{style}]{char}[/]"
            lines.append(line)
        
        return "\n".join(lines)

class StatsDashboard(Static):
    """Dashboard de estadísticas estilo HUD."""
    stats = reactive({})
    
    def render(self) -> str:
        if not self.stats:
            return "[dim italic]Adquiriendo telemetría...[/dim italic]"
        
        s = self.stats
        step = s.get('step', 0)
        economy = s.get('economy', 'ESTABLE')
        weather = s.get('weather', 'DESPEJADO')
        lore = s.get('lore', '...')
        
        header_style = "bold cyan"
        content = f"[{header_style}]PASO[/] [white]{step:04d}[/] | "
        content += f"[{header_style}]SISTEMA[/] [white]{economy}[/] | "
        content += f"[{header_style}]CLIMA[/] [white]{weather}[/]\n"
        content += f"[dim]{'━' * 40}[/]\n"
        content += f"[{header_style}]REALIDAD:[/] [italic white]{lore[:70]}...[/]\n"
        
        return content

class ArchitectPanel(Static):
    """Panel de control con herramientas divinas."""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="architect_inner"):
            yield Label("[bold yellow]⚡ PANEL DEL ARQUITECTO[/bold yellow]")
            
            with Horizontal(classes="architect_row"):
                yield Button("☀️ SOL", id="arc_sun", variant="primary")
                yield Button("🌧️ LLUVIA", id="arc_rain", variant="primary")
            with Horizontal(classes="architect_row"):
                yield Button("🌩️ TORMENTA", id="arc_storm", variant="primary")
                yield Button("☣️ PLAGA", id="arc_virus", variant="error")
            
            with Horizontal(classes="architect_row"):
                yield Button("🧬 SPAWN", id="arc_spawn", variant="success")
                yield Button("💰 DINERO", id="arc_money", variant="warning")
            
            with Horizontal(classes="architect_row"):
                yield Button("🌍 EXPANSIÓN", id="arc_expand")
                yield Button("📜 LORE", id="arc_lore")

            yield Label("[bold cyan]⏱️ CONTROL TEMPORAL[/bold cyan]")
            with Horizontal(classes="architect_row"):
                yield Button("⚡ MAX", id="speed_max", variant="primary")
                yield Button("⏩ RAPID", id="speed_rapid", variant="primary")
            with Horizontal(classes="architect_row"):
                yield Button("📊 NORM", id="speed_norm", variant="primary")
                yield Button("⏳ SLOW", id="speed_slow", variant="primary")

class SharedStyles:
    """CSS común para inyectar en las Apps de Textual."""
    MAIN = """
    #side_panel {
        width: 45;
        border-left: vkey $accent;
        background: $surface;
        padding: 1;
    }
    
    #architect_inner {
        margin-top: 1;
        border: solid yellow 20%;
        padding: 1;
        height: auto;
    }
    
    .architect_row {
        height: 3;
        margin-top: 1;
    }
    
    .architect_row Button {
        width: 1fr;
        margin: 0 1;
        min-width: 0;
    }
    
    $accent: cyan;
    $surface: #0d1117;
    """
