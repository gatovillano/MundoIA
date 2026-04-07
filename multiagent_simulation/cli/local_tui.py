#!/usr/bin/env python3
"""
MUNDO IA - Versión TUI (Textual)
Interfaz moderna de terminal con mosaicos y colores
"""

import sys
import os
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

# Añadir directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, RichLog, Button
from textual.reactive import reactive
from textual import events
from textual import work

from modelo import ModeloRelacional, TerrainType

# Colores para terrenos
TERRAIN_COLORS = {
    TerrainType.GRASS: "green",
    TerrainType.FOREST: "green4",
    TerrainType.MOUNTAIN: "yellow",
    TerrainType.WATER: "blue",
    TerrainType.DESERT: "yellow3",
    TerrainType.ARCHAEOLOGICAL_SITE: "magenta",
}

class TerrainMapWidget(Static):
    """Widget que renderiza el mapa de terreno con caracteres unicode/ascii."""
    
    def __init__(self, modelo=None, **kwargs):
        super().__init__(**kwargs)
        self.modelo = modelo
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_tile = None
    
    def set_model(self, modelo):
        self.modelo = modelo
        self.refresh()
    
    def on_click(self, event):
        """Manejar clic para seleccionar celda."""
        if not self.modelo:
            return
        
        # Calcular coordenadas desde el evento de clic
        # El ancho de cada celda es aproximadamente 2 caracteres
        # Implementación simplificada
        pass
    
    def render(self):
        if not self.modelo or not hasattr(self.modelo, 'mapa'):
            return "[yellow]Mapa no disponible. Ejecuta 'init' primero.[/yellow]"
        
        mapa = self.modelo.mapa
        size = len(mapa)
        
        # Construir representación del mapa
        lines = []
        
        # Encabezado con coordenadas
        header = "   " + "".join(f"{i%10}" for i in range(size))
        lines.append(header)
        lines.append("   " + "─" * size)
        
        for x in range(size):
            # Fila con índice
            line = f"{x:2d}│"
            for y in range(size):
                tile = mapa[x][y]
                if not tile:
                    line += " "
                    continue
                
                # Determinar carácter a mostrar
                char = self.get_tile_char(tile)
                color = self.get_tile_color(tile)
                
                # Añadir con color ANSI
                line += f"[{color}]{char}[/{color}]"
            
            # Índice al final
            line += f"│{x%10}"
            lines.append(line)
        
        lines.append("   " + "─" * size)
        
        # Información de celda seleccionada
        if self.selected_tile:
            tx, ty = self.selected_tile
            tile_info = f"[bold]Seleccionado: ({tx},{ty})[/bold] "
            tile_info += f"T: {mapa[tx][ty].terrain_type}"
            if mapa[tx][ty].resource_node:
                tile_info += f" | Recurso: {mapa[tx][ty].resource_node['type']} ({mapa[tx][ty].resource_node['amount']})"
            if mapa[tx][ty].is_archaeological_site:
                tile_info += f" | 🏛️ Sitio Archeológico"
                if mapa[tx][ty].discovered_by:
                    tile_info += f" [green]✓[/green]"
                else:
                    tile_info += f" [red]?[/red]"
            lines.append(tile_info)
        
        return "\n".join(lines)
    
    def get_tile_char(self, tile):
        """Carácter para representar la celda."""
        # Agentes tienen prioridad
        agentes = [a for a in self.modelo.agentes if a.x == tile.x and a.y == tile.y]
        if agentes:
            agente = agentes[0]
            return "#" if agente.rol == "Líder" else "@"
        
        # Sitios arqueológicos
        if tile.is_archaeological_site:
            return "*" if tile.discovered_by else "?"
        
        # Recursos
        if tile.resource_node:
            rtype = tile.resource_node['type']
            symbols = {
                'food': 'F',
                'wood': 'W',
                'stone': 'S',
                'iron': 'I',
                'medicine': 'M',
                'crystal': 'C',
            }
            return symbols.get(rtype, '?')
        
        # Terreno base
        symbols = {
            TerrainType.GRASS: ".",
            TerrainType.FOREST: "T",
            TerrainType.MOUNTAIN: "^",
            TerrainType.WATER: "~",
            TerrainType.DESERT: ":",
        }
        return symbols.get(tile.terrain_type, "?")
    
    def get_tile_color(self, tile):
        """Color para la celda."""
        if tile.is_archaeological_site:
            return "magenta" if not tile.discovered_by else "green"
        
        if tile.resource_node:
            colors = {
                'food': "red",
                'wood': "green",
                'stone': "white",
                'iron': "bright_white",
                'medicine': "cyan",
                'crystal': "blue",
            }
            return colors.get(tile.resource_node['type'], "white")
        
        return TERRAIN_COLORS.get(tile.terrain_type, "white")

class StatsPanel(Static):
    """Panel de estadísticas de la simulación."""
    
    def __init__(self, modelo=None, **kwargs):
        super().__init__(**kwargs)
        self.modelo = modelo
    
    def set_model(self, modelo):
        self.modelo = modelo
        self.refresh()
    
    def render(self):
        if not self.modelo:
            return "[yellow]Estadísticas no disponibles[/yellow]"
        
        stats = f"[bold]📊 ESTADÍSTICAS[/bold]\n"
        stats += f"Paso: {self.modelo.paso_actual}\n"
        stats += f"Agentes: {len(self.modelo.agentes)}\n"
        
        # Condiciones de agentes
        if self.modelo.agentes:
            avg_res = sum(a.recursos for a in self.modelo.agentes) / len(self.modelo.agentes)
            avg_money = sum(a.dinero for a in self.modelo.agentes) / len(self.modelo.agentes)
            stats += f"Recursos promedio: {avg_res:.1f}\n"
            stats += f"Dinero promedio: {avg_money:.1f} MC\n"
        
        # Distribución de terreno
        if hasattr(self.modelo, 'mapa') and self.modelo.mapa:
            terrain_counts = {}
            for row in self.modelo.mapa:
                for tile in row:
                    if tile:
                        terrain_counts[tile.terrain_type] = terrain_counts.get(tile.terrain_type, 0) + 1
            
            stats += f"\n[bold]Terrenos:[/bold]\n"
            for terrain, count in sorted(terrain_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                stats += f"  {terrain}: {count}\n"
        
        # Sitios arqueológicos
        if hasattr(self.modelo, 'mapa') and self.modelo.mapa:
            total_sites = sum(1 for row in self.modelo.mapa for tile in row if tile and tile.is_archaeological_site)
            discovered = sum(1 for row in self.modelo.mapa for tile in row if tile and tile.is_archaeological_site and tile.discovered_by)
            stats += f"\n[bold]Sitios Arqueológicos:[/bold]\n"
            stats += f"  Descubiertos: {discovered}/{total_sites}\n"
        
        return stats

class AgentsPanel(Static):
    """Panel que muestra la lista de agentes."""
    
    def __init__(self, modelo=None, **kwargs):
        super().__init__(**kwargs)
        self.modelo = modelo
    
    def set_model(self, modelo):
        self.modelo = modelo
        self.refresh()
    
    def render(self):
        if not self.modelo or not self.modelo.agentes:
            return "[yellow]No hay agentes[/yellow]"
        
        table = "[bold]👥 AGENTES[/bold]\n"
        table += "ID   | Nombre            | Pos   | Rec   | Dinero\n"
        table += "─────┼──────────────────┼───────┼───────┼────────\n"
        
        for agente in self.modelo.agentes[:10]:  # Mostrar solo los primeros 10
            nombre = (agente.identidad.nombre if agente.identidad else "Sin nombre")[:12]
            table += f"{agente.unique_id:4s} | {nombre:16s} | ({agente.x:2d},{agente.y:2d}) | {agente.recursos:5.1f} | {agente.dinero:6.1f}\n"
        
        if len(self.modelo.agentes) > 10:
            table += f"... y {len(self.modelo.agentes) - 10} más\n"
        
        return table

class LogPanel(RichLog):
    """Panel de logs con scroll."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_lines = 100
    
    def write_log(self, message: str, category: str = "info"):
        """Añadir un log al panel."""
        style_map = {
            "sistema": "blue",
            "arqueologia": "magenta",
            "social": "cyan",
            "economia": "yellow",
            "error": "red",
        }
        style = style_map.get(category, "white")
        self.write(f"[{style}]{message}[/{style}]")
        
        # Mantener límite de líneas
        if self.lines and len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]

class MundoTUI(App):
    """Aplicación TUI principal."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #main_container {
        height: 1fr;
    }
    
    #map_container {
        width: 1fr;
        padding: 1;
    }
    
    TerrainMapWidget {
        width: 1fr;
        height: 1fr;
        border: solid green;
        content-align: center middle;
    }
    
    #side_panel {
        width: 40;
        padding: 1;
    }
    
    StatsPanel, AgentsPanel {
        margin: 0 0 1 0;
        padding: 1;
        border: solid blue;
        height: auto;
    }
    
    #log_panel {
        height: 15;
        border: solid yellow;
    }
    
    Footer {
        height: 1;
    }
    """
    
    BINDINGS = [
        ("space", "toggle_pause", "Pausa/Reanudar"),
        ("s", "step", "Paso"),
        ("r", "reset", "Reiniciar"),
        ("q", "quit", "Salir"),
        ("i", "init", "Inicializar"),
        ("m", "refresh_map", "Actualizar mapa"),
    ]
    
    def __init__(self, agents=10, size=20):
        super().__init__()
        self.num_agents = agents
        self.map_size = size
        self.modelo = None
        self.running = False
        self.paused = False
        self.step_count = 0
    
    def compose(self) -> ComposeResult:
        """Componer la interfaz."""
        yield Header()
        
        with Horizontal(id="main_container"):
            with Vertical(id="map_container"):
                yield TerrainMapWidget(id="map_widget")
            
            with Vertical(id="side_panel"):
                yield StatsPanel(id="stats_panel")
                yield AgentsPanel(id="agents_panel")
        
        yield LogPanel(id="log_panel")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Inicialización al montar la app."""
        self.log_panel = self.query_one("#log_panel", LogPanel)
        self.map_widget = self.query_one("#map_widget", TerrainMapWidget)
        self.stats_panel = self.query_one("#stats_panel", StatsPanel)
        self.agents_panel = self.query_one("#agents_panel", AgentsPanel)
        
        self.write_log("🚀 MundoIA TUI iniciado. Presiona 'i' para inicializar.", "sistema")
    
    def write_log(self, message: str, category: str = "info"):
        """Añadir log al panel."""
        self.log_panel.write_log(message, category)
    
    def action_init(self):
        """Inicializar simulación."""
        self.write_log("🔄 Inicializando simulación...", "sistema")
        
        try:
            self.modelo = ModeloRelacional(
                num_agentes=self.num_agents,
                start_empty=False,
                user_id="TUI-USER"
            )
            
            # Forzar generación de mapa
            if not self.modelo.mapa or len(self.modelo.mapa) == 0:
                self.modelo.mapa = self.modelo.generar_mapa()
            
            # Actualizar widgets
            self.map_widget.set_model(self.modelo)
            self.stats_panel.set_model(self.modelo)
            self.agents_panel.set_model(self.modelo)
            
            size = len(self.modelo.mapa)
            self.write_log(f"✅ Simulación inicializada: {size}x{size}, {len(self.modelo.agentes)} agentes", "sistema")
            self.step_count = 0
        except Exception as e:
            self.write_log(f"❌ Error al inicializar: {e}", "error")
    
    def action_step(self):
        """Ejecutar un paso de simulación."""
        if not self.modelo:
            self.write_log("⚠️ Simulación no inicializada. Presiona 'i' primero.", "sistema")
            return
        
        try:
            self.modelo.step()
            self.step_count += 1
            
            # Actualizar UI
            self.map_widget.set_model(self.modelo)
            self.stats_panel.set_model(self.modelo)
            self.agents_panel.set_model(self.modelo)
            
            self.write_log(f"📍 Paso {self.step_count} completado", "sistema")
        except Exception as e:
            self.write_log(f"❌ Error en paso: {e}", "error")
    
    def action_toggle_pause(self):
        """Pausar/reanudar ejecución automática."""
        self.paused = not self.paused
        status = "Pausado" if self.paused else "Ejecutando"
        self.write_log(f"⏸️ {status}", "sistema")
    
    def action_reset(self):
        """Reiniciar simulación."""
        self.modelo = None
        self.step_count = 0
        self.map_widget.set_model(None)
        self.stats_panel.set_model(None)
        self.agents_panel.set_model(None)
        self.write_log("🔄 Simulación reiniciada. Presiona 'i' para nueva inicialización.", "sistema")
    
    def action_refresh_map(self):
        """Forzar actualización del mapa."""
        if self.modelo:
            self.map_widget.set_model(self.modelo)
            self.write_log("🗺️ Mapa actualizado", "sistema")

def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MUNDO IA - Versión TUI (Textual)')
    parser.add_argument('--agents', type=int, default=10, help='Número de agentes')
    parser.add_argument('--size', type=int, default=20, help='Tamaño del mapa')
    parser.add_argument('--auto', action='store_true', help='Ejecutar automáticamente al iniciar')
    
    args = parser.parse_args()
    
    app = MundoTUI(agents=args.agents, size=args.size)
    app.run()

if __name__ == "__main__":
    main()
