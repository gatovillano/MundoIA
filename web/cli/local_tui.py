#!/usr/bin/env python3
"""
MUNDO IA - Local TUI (Premium Edition)
Interfaz visual rica que corre el modelo directamente en memoria.
"""

import sys
import os
import time
import threading
from typing import Dict, List, Any

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.modelo import ModeloRelacional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, Label, RichLog
from textual.reactive import reactive
from textual.binding import Binding

# Importar widgets compartidos
from web.cli.shared_widgets import UltraMapWidget, StatsDashboard, ArchitectPanel, SharedStyles

# --- ESTILOS ADICIONALES ---

CSS = SharedStyles.MAIN + """
Screen {
    background: #05070a;
}

#map_container {
    width: 1fr;
    height: 1fr;
    border: solid cyan 20%;
    padding: 1;
    overflow: auto auto;
}

#log_panel {
    height: 10;
    border-top: double cyan 30%;
    background: $background;
}

AgentsPanel {
    height: 1fr;
    border-bottom: solid cyan 10%;
    padding: 1;
}

.agent_item {
    padding: 0 1;
}
"""

class AgentsPanel(Static):
    """Listado de agentes en la TUI local."""
    agents = reactive([])
    
    def render(self) -> str:
        if not self.agents:
            return "[dim]Esperando vida...[/dim]"
        
        content = "[bold cyan]⌬ ENTIDADES NEURALES[/bold cyan]\n"
        for a in self.agents[:15]:
            nombre = (a.identidad.nombre if a.identidad else a.unique_id)[:15]
            char = "⚉" if a.rol == "Líder" else "@"
            color = "yellow" if a.rol == "Líder" else "cyan"
            content += f"[{color}]{char}[/] {nombre:16} | {a.rol:10} | {a.recursos:5.0f} rec\n"
        
        if len(self.agents) > 15:
            content += f"[dim]... y {len(self.agents)-15} más[/dim]"
        return content

class MundoTUI(App):
    """Aplicación principal de la TUI Local."""
    
    CSS = CSS
    
    BINDINGS = [
        Binding("space", "step", "AVANCE", show=True),
        Binding("i", "init", "INICIAR MUNDO", show=True),
        Binding("r", "reset", "REINICIAR", show=True),
        Binding("q", "quit", "SALIR", show=True),
    ]
    
    def __init__(self, agents=0, size=20):
        super().__init__()
        self.initial_agents = agents
        self.modelo = None
        self.step_count = 0
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal(id="main_layout"):
            with Vertical(id="map_container"):
                yield UltraMapWidget(id="map_widget")
            
            with Vertical(id="side_panel"):
                yield AgentsPanel(id="agents_panel")
                yield StatsDashboard(id="stats_panel")
                yield ArchitectPanel(id="architect_panel")
        
        yield RichLog(id="log_panel", markup=True, max_lines=500)
        yield Footer()
    
    def on_mount(self) -> None:
        self.log_panel = self.query_one("#log_panel", RichLog)
        self.map_widget = self.query_one("#map_widget", UltraMapWidget)
        self.stats_panel = self.query_one("#stats_panel", StatsDashboard)
        self.agents_panel = self.query_one("#agents_panel", AgentsPanel)
        
        self.write_log("🚀 [SISTEMA] MundoIA TUI Iniciado. Presiona 'i' para manifestar el universo.", "system")

    def write_log(self, message: str, category: str = "info"):
        colors = {"system": "cyan", "milagro": "yellow", "error": "red", "info": "white"}
        color = colors.get(category, "white")
        timestamp = time.strftime("%H:%M:%S")
        self.log_panel.write(f"[[dim]{timestamp}[/]] [{color}]► {message}[/]")

    # --- ACCIONES DEL MUNDO ---

    def action_init(self):
        if self.modelo: return
        self.write_log("🔄 Generando tejido de la realidad...", "system")
        
        self.modelo = ModeloRelacional(
            num_agentes=self.initial_agents,
            user_id="LOCAL-ARCHITECT",
            start_empty=True if self.initial_agents == 0 else False
        )
        if not self.modelo.mapa:
            self.modelo.generar_mapa()
            
        self.update_ui()
        self.write_log(f"✅ Realidad manifestada ({len(self.modelo.mapa)}x{len(self.modelo.mapa[0])})", "system")

    def action_step(self):
        if not self.modelo:
            self.action_init()
        
        self.modelo.step()
        self.step_count += 1
        self.update_ui()
        self.write_log(f"📍 Paso {self.step_count} completado", "info")

    def action_reset(self):
        self.modelo = None
        self.step_count = 0
        self.update_ui()
        self.write_log("⚠ Realidad colapsada. Presiona 'i' para nuevo Big Bang.", "error")

    def update_ui(self):
        if not self.modelo:
            self.map_widget.map_data = None
            self.agents_panel.agents = []
            self.stats_panel.stats = {}
            return
            
        self.map_widget.map_data = self.modelo.mapa
        self.map_widget.agents_data = self.modelo.agentes
        self.agents_panel.agents = self.modelo.agentes
        
        # Telemetría para el HUD
        self.stats_panel.stats = {
            "step": self.modelo.paso_actual,
            "economy": "COLAPSO" if self.modelo.economia.get("indice_bursatil", 1) < 0.6 else "ESTABLE",
            "weather": self.modelo.weather.upper(),
            "lore": getattr(self.modelo, "lore", "Realidad estándar")
        }

    # --- ACCIONES DEL ARQUITECTO ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.modelo:
            self.write_log("☢ Error: Debes iniciar el mundo ('i') antes de actuar.", "error")
            return
            
        btn_id = event.button.id
        
        if btn_id == "arc_sun":
            self.modelo.weather = "sunny"
            self.write_log("☀️ Has decretado un día radiante.", "milagro")
        elif btn_id == "arc_rain":
            self.modelo.weather = "rainy"
            self.write_log("🌧️ Has decretado lluvia purificadora.", "milagro")
        elif btn_id == "arc_storm":
            self.modelo.weather = "storm"
            self.write_log("🌩️ Una tormenta divina sacude la tierra.", "milagro")
        elif btn_id == "arc_spawn":
            a = self.modelo.spawn_agent()
            self.write_log(f"🧬 Vida manifestada: {a.unique_id}", "milagro")
        elif btn_id == "arc_money":
            self.modelo.economia["total_dinero"] += 1000
            self.write_log("💰 Inyección de capital divino: +1000 MC", "milagro")
        elif btn_id == "arc_virus":
            for a in self.modelo.agentes: a.necesidades["salud"] -= 1.5
            self.write_log("☣️ Una plaga viral se extiende por el mundo.", "error")
        elif btn_id == "arc_expand":
            ok, msg = self.modelo.expandir_mundo(cantidad=5)
            self.write_log(f"🌍 {msg}", "milagro")
        
        self.update_ui()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='MUNDO IA - Local TUI Premium')
    parser.add_argument('--agents', type=int, default=0, help='Agentes iniciales')
    args = parser.parse_args()
    
    app = MundoTUI(agents=args.agents)
    app.run()

if __name__ == "__main__":
    main()
