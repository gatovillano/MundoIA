#!/usr/bin/env python3
"""
MUNDO IA - Remote TUI (Premium Edition)
Interfaz que conecta con el servidor remoto garantizando paridad visual con la local.
"""

import sys
import os
import json
import asyncio
import uuid
import aiohttp
import websockets
from datetime import datetime
from typing import Dict, List, Optional, Any

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Label, RichLog, Input
from textual.reactive import reactive
from textual import work
from textual.binding import Binding

# Widgets compartidos
from web.cli.shared_widgets import UltraMapWidget, StatsDashboard, ArchitectPanel, SharedStyles

# --- CONFIGURACIÓN ---
DEFAULT_WS_URL = "wss://api-mundoia.cuerpolibre.cl/ws"
DEFAULT_HTTP_URL = "https://api-mundoia.cuerpolibre.cl"

CSS = SharedStyles.MAIN + """
Screen {
    background: #05070a;
}
#map_container {
    width: 1fr;
    height: 1fr;
    border: solid magenta 20%;
    padding: 1;
    overflow: auto auto;
}
#log_panel {
    height: 10;
    border-top: double magenta 30%;
    background: $background;
}
#agent_list {
    height: 1fr;
    border-bottom: solid magenta 10%;
    padding: 1;
}
#login_dialog {
    width: 60;
    height: auto;
    border: thick cyan;
    background: #0d1117;
    padding: 2;
    align: center middle;
}
"""

class LoginScreen(ModalScreen):
    """Pantalla de autenticación neural."""
    def compose(self) -> ComposeResult:
        with Vertical(id="login_dialog"):
            yield Label("[bold cyan]⬢ MUNDO IA: AUTENTICACIÓN NEURAL[/bold cyan]")
            yield Input(placeholder="Usuario", id="username")
            yield Input(placeholder="Password", password=True, id="password")
            with Horizontal():
                yield Button("ENTRAR", variant="primary", id="btn_login")
                yield Button("REGISTRAR", variant="success", id="btn_register")
            yield Label("", id="status_msg")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value
        if not username or not password: return
        
        if event.button.id == "btn_login":
            success, user_data = await self.app.do_login(username, password)
            if success: self.dismiss(user_data)
            else: self.query_one("#status_msg").update(f"[red]{user_data}[/]")
        elif event.button.id == "btn_register":
            success, res = await self.app.do_register(username, password)
            if success: self.query_one("#status_msg").update("[green]Registrado con éxito![/]")

class AgentListWidget(Static):
    """Listado de agentes remoto."""
    agents = reactive([])
    def render(self) -> str:
        if not self.agents: return "[dim]Esperando vida...[/dim]"
        content = "[bold magenta]⌬ ENTIDADES NEURALES[/bold magenta]\n"
        for a in self.agents[:15]:
            nombre = a.get('identidad', {}).get('nombre', a.get('id', '??'))[:15]
            rol = a.get('rol', 'Citizen')
            char = "⚉" if rol == "Líder" else "@"
            color = "yellow" if rol == "Líder" else "magenta"
            content += f"[{color}]{char}[/] {nombre:16} | {rol:10}\n"
        return content

class MundoRemoteTUI(App):
    """Aplicación principal de la TUI Remota."""
    CSS = CSS
    
    BINDINGS = [
        Binding("space", "step", "AVANCE", show=True),
        Binding("q", "quit", "DESCONECTAR", show=True),
    ]

    def __init__(self, ws_url=DEFAULT_WS_URL, http_url=DEFAULT_HTTP_URL, user_id=None):
        super().__init__()
        self.ws_url = ws_url
        self.http_url = http_url
        self.user_id = user_id or f"EXT-{uuid.uuid4().hex[:4]}"
        self.full_state = {"map": None, "agents": {}, "stats": {}}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main_layout"):
            with Vertical(id="map_container"):
                yield UltraMapWidget(id="map")
            with Vertical(id="side_panel"):
                yield AgentListWidget(id="agent_list")
                yield StatsDashboard(id="stats_panel")
                yield ArchitectPanel(id="architect_panel")
        yield RichLog(id="log_panel", markup=True, max_lines=500)
        yield Footer()

    async def on_mount(self) -> None:
        self.push_screen(LoginScreen(), self.handle_login_result)

    def handle_login_result(self, user_data: Optional[Dict]) -> None:
        if user_data:
            self.user_id = user_data.get("user_id", self.user_id)
            self.write_log(f"🧠 Enlace Neural Establecido: {user_data.get('username')}", "system")
            self.start_ws_client()

    @work(exclusive=True)
    async def start_ws_client(self):
        ws_endpoint = f"{self.ws_url}/{self.user_id}"
        try:
            async with websockets.connect(ws_endpoint) as ws:
                self.write_log("📡 Sincronización completa con el servidor.", "system")
                async for message in ws:
                    data = json.loads(message)
                    self.handle_message(data)
        except Exception as e:
            self.write_log(f"☢ ERROR DE ENLACE: {e}", "error")
            await asyncio.sleep(5)
            self.start_ws_client()

    def handle_message(self, data: Dict):
        mtype = data.get('type')
        if mtype == 'stats':
            self.full_state["stats"] = data
            if 'mapa' in data: self.full_state["map"] = data['mapa']
        elif mtype == 'agent_update':
            self.full_state["agents"] = {a['id']: a for a in data.get('agents', [])}
        elif mtype == 'log':
            self.write_log(data.get('message', ''), data.get('category', 'info'))
        self.update_ui()

    def update_ui(self):
        m = self.query_one("#map", UltraMapWidget)
        s = self.query_one("#stats_panel", StatsDashboard)
        a = self.query_one("#agent_list", AgentListWidget)
        
        m.map_data = self.full_state["map"]
        m.agents_data = list(self.full_state["agents"].values())
        a.agents = list(self.full_state["agents"].values())
        
        st = self.full_state["stats"]
        s.stats = {
            "step": st.get('step', 0),
            "weather": st.get('weather', 'CLEAR').upper(),
            "economy": st.get('economy', 'CALM'),
            "lore": st.get('lore', '...')
        }

    # --- COMUNICACIÓN API ---

    async def do_login(self, username, password):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.http_url}/auth/login", json={"username": username, "password": password}) as r:
                    if r.status == 200: return True, await r.json()
                    return False, (await r.json()).get("detail", "Error")
        except Exception as e: return False, str(e)

    async def do_register(self, username, password):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.http_url}/auth/register", json={"username": username, "password": password}) as r:
                    return r.status == 200, await r.json()
        except Exception: return False, "Error"

    async def send_god_action(self, action: str):
        payload = {"action": action, "params": {}}
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"{self.http_url}/game/god-mode/{self.user_id}", json=payload)
        except Exception as e: self.write_log(f"☢ Error de envío: {e}", "error")

    # --- HANDLERS ---

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {
            "arc_sun": "set_weather:sunny", "arc_rain": "set_weather:rainy",
            "arc_storm": "set_weather:storm", "arc_spawn": "spawn_agent",
            "arc_money": "economy_boost", "arc_virus": "trigger_plague"
        }
        if event.button.id in mapping:
            await self.send_god_action(mapping[event.button.id])

    async def action_step(self):
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"{self.http_url}/game/control", json={"user_id": self.user_id, "action": "step"})
        except Exception: pass

    def write_log(self, message: str, category: str = "info"):
        self.query_one("#log_panel", RichLog).write(f"► {message}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='MUNDO IA - Remote TUI Premium')
    parser.add_argument('--http', default=DEFAULT_HTTP_URL, help='HTTP URL')
    parser.add_argument('--ws', default=DEFAULT_WS_URL, help='WS URL')
    args = parser.parse_args()
    MundoRemoteTUI(http_url=args.http, ws_url=args.ws).run()

if __name__ == "__main__": main()
