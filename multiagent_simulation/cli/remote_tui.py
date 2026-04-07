#!/usr/bin/env python3
"""
MUNDO IA - Remote TUI (Textual)
Rich Terminal interface that connects to the simulation backend via WebSockets.
"""

import sys
import os
import json
import asyncio
import uuid
import random
import aiohttp
import websockets
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, RichLog, Button, Label, Input
from textual.reactive import reactive
from textual import events, work
from textual.binding import Binding

from modelo import TerrainType

# --- CONFIGURATION & STYLES ---

DEFAULT_WS_URL = "wss://api-mundoia.cuerpolibre.cl/ws"
DEFAULT_HTTP_URL = "https://api-mundoia.cuerpolibre.cl"

# Ultra Palette (HSL based for easy manipulation)
TERRAIN_HSL = {
    TerrainType.GRASS: (130, 60, 50),    # Green
    TerrainType.FOREST: (145, 70, 40),   # Darker Green
    TerrainType.MOUNTAIN: (45, 40, 60),   # Gold/Beige
    TerrainType.WATER: (210, 80, 50),    # Blue
    TerrainType.DESERT: (45, 70, 75),    # Sand
    TerrainType.ARCHAEOLOGICAL_SITE: (280, 70, 65), # Purple
}

# Braille patterns for textures (2x4 dots)
# Mapping: 1 4
#          2 5
#          3 6
#          7 8
BRAILLE_PATTERNS = {
    TerrainType.GRASS: "\u2840\u2880\u2801\u2808", # Sparse dots
    TerrainType.FOREST: "\u28ff\u28fe\u28f7\u28fb", # Dense patterns
    TerrainType.MOUNTAIN: "\u2803\u2818\u2806\u2830", # Slopes
    TerrainType.WATER: "\u2824\u2844\u2888\u2822",    # Ripples
    TerrainType.DESERT: "\u2824\u2812\u2848\u2884",   # Sand dunes
}

# Resource color mappings for map rendering
RESOURCE_COLORS = {
    "food":   "bold green",
    "wood":   "bold yellow4",
    "stone":  "bold grey70",
    "iron":   "bold steel_blue1",
    "gold":   "bold gold1",
    "water":  "bold dodger_blue2",
    "gem":    "bold magenta",
    "herb":   "bold green3",
    "coal":   "bold grey30",
    "oil":    "bold dark_orange3",
}

# --- WIDGETS ---

class LoginScreen(ModalScreen):
    """Universal Login/Registry modal."""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="login_dialog"):
            yield Label("[bold fuchsia]⬢ MUNDO IA: NEURAL AUTHENTICATION[/bold fuchsia]", id="login_title")
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Password", password=True, id="password")
            with Horizontal(id="login_buttons"):
                yield Button("LOGIN", variant="primary", id="btn_login")
                yield Button("REGISTER", variant="success", id="btn_register")
            yield Label("", id="status_msg")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value
        status = self.query_one("#status_msg", Label)
        
        if not username or not password:
            status.update("[bold red]ERROR: Credentials required[/bold red]")
            return

        if event.button.id == "btn_login":
            status.update("[bold fuchsia]Verifying Neural Hash...[/bold fuchsia]")
            success, user_data = await self.app.do_login(username, password)
            if success:
                self.dismiss(user_data)
            else:
                status.update(f"[bold red]DENIED: {user_data}[/bold red]")
        
        elif event.button.id == "btn_register":
            status.update("[bold green]Synthesizing identity...[/bold green]")
            success, user_id = await self.app.do_register(username, password)
            if success:
                status.update(f"[bold green]GRANTED. LOGGING IN...[/bold green]")
                # Recurse into login once registered usually works or just dismiss with info
                success2, user_data = await self.app.do_login(username, password)
                if success2: self.dismiss(user_data)
            else:
                status.update(f"[bold red]FAILED: {user_id}[/bold red]")

class ResourceBar(Static):
    """Mini bar to show resource percentage."""
    value = reactive(0.0)
    
    def render(self) -> str:
        width = 8
        filled = int(self.value * width / 100)
        empty = width - filled
        color = "green" if self.value > 50 else "yellow" if self.value > 20 else "red"
        return f"[dim][[/][{color}]{'━' * filled}[/][dim]{'─' * empty}][/]"

class UltraMapWidget(Static):
    """High-Res Terrain Map with Braille Textures."""
    
    map_data = reactive(None)
    agents_data = reactive([])
    selected_tile = reactive(None)
    is_possessed_mode = reactive(False)
    
    # Internal mappings moved to class scope to avoid NameError
    RESOURCE_COLORS = {
        "food":   "bold bright_green",
        "wood":   "bold yellow",
        "stone":  "bold grey70",
        "iron":   "bold steel_blue1",
        "gold":   "bold yellow1",
        "water":  "bold dodger_blue2",
        "gem":    "bold magenta",
        "herb":   "bold green3",
        "coal":   "bold grey30",
        "oil":    "bold dark_orange3",
    }
    
    def render(self) -> str:
        if not self.map_data:
            return "[bold yellow]Synchronizing with World...[/bold yellow]\n[dim]Ultra-Res Map Loading...[/dim]"
        
        mapa = self.map_data
        cols = len(mapa)
        rows = len(mapa[0]) if cols > 0 else 0
        lines = []
        
        # Color mapping for backgrounds (Standard Rich colors for maximum compatibility)
        TERRAIN_BG = {
            "grass": "on green",
            "forest": "on dark_green",
            "mountain": "on grey19",
            "water": "on blue",
            "desert": "on yellow4",
            "archaeological_site": "on dark_magenta",
        }
        
        for y in range(rows):
            line = ""
            for x in range(cols):
                tile = mapa[x][y]
                if not tile:
                    line += "  "
                    continue
                
                # Check for agents
                agentes_here = [a for a in self.agents_data if a.get('x') == x and a.get('y') == y]
                
                terrain = tile.get('terrain', 'grass')
                bg_style = TERRAIN_BG.get(terrain, "on black")
                
                # Symbol logic
                char = "  "
                fg_color = "white"
                
                if agentes_here:
                    agente = agentes_here[0]
                    if agente.get('is_possessed'):
                        char = "🕹 "
                        fg_color = "bold bright_white on fuchsia"
                        bg_style = "" # Possession overrides background
                    else:
                        char = "⚉ " if agente.get('rol') == 'Líder' else "@ "
                        fg_color = "bold yellow1" if agente.get('rol') == 'Líder' else "bold cyan"
                elif tile.get('is_archaeological_site'):
                    char = "🕌 " if tile.get('discovered_by') else "❓ "
                    fg_color = "bold bright_magenta"
                elif tile.get('resource'):
                    rtype = tile['resource']['type']
                    char = f"{rtype[0].upper()} "
                    fg_color = self.RESOURCE_COLORS.get(rtype, "bold white")
                else:
                    # Braille texture
                    patterns = BRAILLE_PATTERNS.get(terrain, " . ")
                    char = f"{random.choice(patterns)} "
                    fg_color = "white"
                
                # FINAL STYLE
                style = f"{fg_color} {bg_style}"
                if self.selected_tile == (x, y):
                    style = "bold reverse white"
                
                line += f"[{style}]{char}[/]"
            lines.append(line)
        
        return "\n".join(lines)

class StatsDashboard(Static):
    """HUD-style stats dashboard."""
    
    stats = reactive({})
    is_possessed_mode = reactive(False)
    
    def render(self) -> str:
        if not self.stats:
            return "[dim italic]Acquiring simulation telemetry...[/dim italic]"
        
        s = self.stats
        step = s.get('step', 0)
        economy = s.get('economy', 'CALM')
        weather = s.get('weather', 'CLEAR')
        lore = s.get('lore', '...')
        
        theme = "fuchsia" if self.is_possessed_mode else "cyan"
        header_style = f"bold {theme}"
        
        content = f"[{header_style}]STEP[/] [white]{step:04d}[/] | "
        content += f"[{header_style}]SYSTEM[/] [white]{economy}[/] | "
        content += f"[{header_style}]ENV[/] [white]{weather}[/]\n"
        
        # Mini-bars / Status
        content += f"[dim]{'━' * 40}[/]\n"
        content += f"[{header_style}]LORE EXTRAPOLATION:[/] [italic white]{lore[:80]}...[/]\n"
        
        if self.is_possessed_mode:
            content += "[bold blink red]⚠️ POSSESSION ACTIVE: NEURAL LINK ESTABLISHED[/]"
            
        return content

# --- MAIN APP ---

class MundoRemoteTUI(App):
    """The Ultra Rich TUI application for MundoIA."""
    
    # CSS glassmorphism and animations
    CSS = """
    Screen {
        layout: vertical;
        background: #05070a;
        transition: background 1s;
    }
    
    Screen.possessed {
        background: #1a0505;
        color: #ff3333;
    }

    #header_area {
        height: 3;
        border-bottom: hkey $accent;
        background: $surface;
        padding: 0 2;
        content-align: center middle;
        transition: all 500ms;
    }

    #main_layout {
        height: 1fr;
    }

    #map_container {
        width: 1fr;
        height: 1fr;
        padding: 1;
        border: solid $accent 20%;
        background: $surface;
        overflow: auto auto;
        transition: all 300ms;
    }

    #map_container:focus {
        border: double $accent;
        background: $background;
    }

    UltraMapWidget {
        width: auto;
        height: auto;
        content-align: center middle;
    }

    #side_panel {
        width: 50;
        border-left: vkey $accent;
        background: $surface;
        padding: 1;
        transition: all 400ms;
    }

    #stats_panel {
        height: 8;
        border-top: solid $accent 20%;
        background: $surface;
        padding: 1;
    }

    #log_container {
        height: 15;
        border-top: double $accent 30%;
        background: $background;
        padding: 0 1;
    }

    #controls {
        height: 4;
        layout: horizontal;
        align: center middle;
        background: $surface;
        border-top: solid $accent;
    }

    Button {
        margin: 0 1;
        min-width: 14;
        border: none;
        transition: all 100ms;
    }

    Button:hover {
        background: $accent 30%;
        color: white;
    }

    $accent: cyan;
    $secondary: magenta;
    $surface: #0d1117;
    $background: #05070a;

    #login_dialog {
        width: 60;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 2;
        align: center middle;
    }

    #login_title {
        width: 100%;
        content-align: center middle;
        margin-bottom: 2;
    }

    #login_buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    #status_msg {
        height: 1;
        margin-top: 1;
        content-align: center middle;
    }

    Input {
        margin-bottom: 1;
        border: solid $accent 20%;
    }

    Input:focus {
        border: solid $accent;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "DISCONNECT", show=True),
        Binding("s", "start", "INITIATE", show=True),
        Binding("p", "pause", "FREEZE", show=True),
        Binding("r", "reset", "WIPE", show=True),
        Binding("space", "step", "ADVANCE", show=True),
        Binding("h", "toggle_possessed", "SYNC POSSESSION", show=False),
    ]

    def __init__(self, ws_url=DEFAULT_WS_URL, http_url=DEFAULT_HTTP_URL, user_id=None):
        super().__init__()
        self.ws_url = ws_url
        self.http_url = http_url
        self.user_id = user_id or f"ULTRA-{uuid.uuid4().hex[:6]}"
        self.websocket = None
        self.is_connected = False
        self.is_possessed_mode = False
        
        self.full_state = {
            "map": None,
            "agents": {},
            "stats": {},
            "step": 0
        }

    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="header_area"):
            yield Label(f"[bold fuchsia]⬢ MUNDO IA[/bold fuchsia]  [dim]CORE VERSION v3.0[/dim]  [bold cyan]LINK: {self.user_id}[/bold cyan]")
        
        with Horizontal(id="main_layout"):
            with Vertical(id="map_container"):
                yield UltraMapWidget(id="map")
            
            with Vertical(id="side_panel"):
                yield AgentListWidget(id="agent_list")
                yield StatsDashboard(id="stats_panel")
        
        with Vertical(id="log_container"):
            yield RichLog(id="log_panel", markup=True, wrap=True, max_lines=1000, highlight=True)
        
        with Horizontal(id="controls"):
            yield Button("INITIATE", variant="success", id="btn_start")
            yield Button("FREEZE", variant="warning", id="btn_pause")
            yield Button("ADVANCE", variant="primary", id="btn_step")
            yield Button("WIPE WORLD", variant="error", id="btn_reset")
            
        yield Footer()

    async def on_mount(self) -> None:
        self.log_panel = self.query_one("#log_panel", RichLog)
        self.map_widget = self.query_one("#map", UltraMapWidget)
        self.agent_widget = self.query_one("#agent_list", AgentListWidget)
        self.stats_widget = self.query_one("#stats_panel", StatsDashboard)
        
        # Trigger Login Modal
        self.push_screen(LoginScreen(), self.handle_login_result)

    def handle_login_result(self, user_data: Optional[Dict]) -> None:
        if user_data:
            self.user_id = user_data.get("user_id", self.user_id)
            username = user_data.get("username", "Unknown")
            self.write_log(f"🧠 Neural Link Authenticated: {username} ({self.user_id})", "system")
            # Clear UI before starting
            self.full_state = {"map": None, "agents": {}, "stats": {}, "step": 0}
            self.update_ui()
            self.start_ws_client()
        else:
            self.write_log("☢️ Authentication Aborted. Limited access granted.", "warning")
            self.start_ws_client()

    async def do_login(self, username, password) -> tuple[bool, Any]:
        url = f"{self.http_url}/auth/login"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"username": username, "password": password}) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        return True, data
                    return False, data.get("detail", "Error desconocido")
        except Exception as e:
            return False, str(e)

    async def do_register(self, username, password) -> tuple[bool, Any]:
        url = f"{self.http_url}/auth/register"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"username": username, "password": password}) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        return True, data.get("user_id")
                    return False, data.get("detail", "Error desconocido")
        except Exception as e:
            return False, str(e)

    @work(exclusive=True)
    async def start_ws_client(self):
        ws_endpoint = f"{self.ws_url}/{self.user_id}"
        try:
            async with websockets.connect(ws_endpoint) as ws:
                self.websocket = ws
                self.is_connected = True
                self.write_log(f"🧠 Linked synchronized", "system")
                
                # Debug map size
                if self.full_state.get("map"):
                    m = self.full_state["map"]
                    self.write_log(f"📊 Neural Map Scale: {len(m)}x{len(m[0]) if len(m)>0 else 0}", "system")
                
                async for message in ws:
                    try:
                        data = json.loads(message)
                        await self.handle_message(data)
                    except json.JSONDecodeError:
                        self.write_log("⚠️ Receptáculo dañado: mensaje no-JSON.", "error")
        except Exception as e:
            self.write_log(f"☢️ LINK COLLAPSE: {e}", "error")
            self.is_connected = False
            await asyncio.sleep(5)
            self.start_ws_client()

    async def handle_message(self, data: Dict):
        msg_type = data.get('type')
        
        if msg_type in ['stats', 'stats_delta']:
            # Normal logic but with possession check
            if msg_type == 'stats':
                self.full_state["stats"] = data
                if 'mapa' in data: self.full_state["map"] = data['mapa']
            else:
                self.update_stats_delta(data.get('delta', {}))
            
            # Auto-detect possession for HUD change
            possessed_id = self.full_state["stats"].get('agente_poseido_id')
            was_possessed = self.is_possessed_mode
            self.is_possessed_mode = bool(possessed_id)
            
            if was_possessed != self.is_possessed_mode:
                self.apply_possession_theme()
            
            self.update_ui()
            
        elif msg_type in ['agent_update', 'agent_delta']:
            self.update_agents(data, msg_type)
            self.update_ui()
            
        elif msg_type == 'log':
            self.write_log(data.get('message', ''), data.get('category', 'info'))
            
        elif msg_type == 'world_reset':
            self.write_log("☣️ WORLD COLLAPSE & REBIRTH", "system")
            self.full_state = {"map": None, "agents": {}, "stats": {}, "step": 0}
            self.update_ui()

    def update_stats_delta(self, delta):
        new_stats = dict(self.full_state["stats"])
        for k, v in delta.items():
            if isinstance(v, dict) and k in new_stats and isinstance(new_stats[k], dict):
                new_stats[k].update(v)
            else:
                new_stats[k] = v
        self.full_state["stats"] = new_stats

    def update_agents(self, data, msg_type):
        if msg_type == 'agent_update':
            self.full_state["agents"] = {a['id']: a for a in data.get('agents', [])}
        else:
            new_agents = dict(self.full_state["agents"])
            for aid, delta in data.get('updates', {}).items():
                if aid in new_agents:
                    new_agents[aid].update(delta)
                else: new_agents[aid] = delta
            for aid in data.get('removals', []): new_agents.pop(aid, None)
            self.full_state["agents"] = new_agents

    def update_ui(self):
        self.map_widget.map_data = self.full_state["map"]
        self.map_widget.agents_data = list(self.full_state["agents"].values())
        self.map_widget.is_possessed_mode = self.is_possessed_mode
        self.agent_widget.agents = list(self.full_state["agents"].values())
        self.stats_widget.stats = self.full_state["stats"]
        self.stats_widget.is_possessed_mode = self.is_possessed_mode

    def apply_possession_theme(self):
        """Dynamic theme shift using Textual classes."""
        if self.is_possessed_mode:
            self.add_class("possessed")
            self.write_log("🚨 NEURAL OVERRIDE: Possession Active", "error")
        else:
            self.remove_class("possessed")
            self.write_log("⚪ SYSTEM RESTORED: Possession Terminated", "system")

    def write_log(self, message: str, category: str = "info"):
        colors = {
            "system": "bold cyan",
            "arqueologia": "bold magenta1",
            "social": "bold green1",
            "economia": "bold yellow3",
            "error": "bold red",
            "info": "white"
        }
        color = colors.get(category, "white")
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Add glitch effect for certain categories
        prefix = "░▒▓ " if category == "system" else "► "
        content = f"[{color}]{prefix}[dim]{timestamp}[/] {message}[/]"
        # Robust writing to avoid raw markup markers
        self.log_panel.write(content)

    # --- ACTIONS ---
    
    async def send_control(self, action: str):
        payload = {"user_id": self.user_id, "action": action}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.http_url}/game/control", json=payload) as resp:
                    if resp.status == 200:
                        self.write_log(f"📡 Protocol {action.upper()} transmitted", "system")
                    else:
                        self.write_log(f"☢️ Protocol Error {resp.status}", "error")
        except Exception:
            self.write_log(f"☢️ Hardware Link failure", "error")

    async def action_start(self): await self.send_control("start")
    async def action_pause(self): await self.send_control("pause")
    async def action_reset(self): await self.send_control("reset")
    async def action_step(self): await self.send_control("step")
    def action_toggle_possessed(self): 
        self.is_possessed_mode = not self.is_possessed_mode
        self.apply_possession_theme()
        self.update_ui()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        action_map = {"btn_start": "start", "btn_pause": "pause", "btn_reset": "reset", "btn_step": "step"}
        if event.button.id in action_map:
            await self.send_control(action_map[event.button.id])

class AgentListWidget(Static):
    """Sidebar widget for Agent list in Ultra Mode."""
    agents = reactive([])
    
    def render(self) -> str:
        if not self.agents: return ""
        content = "[bold cyan]⌬ NEURAL ENTITIES[/bold cyan]\n"
        content += "[dim]RANK | NAME             | STATUS       | FUEL[/dim]\n"
        content += "[dim]─────┼──────────────────┼──────────────┼─────[/dim]\n"
        
        sorted_agents = sorted(self.agents, key=lambda a: (not a.get('is_possessed'), a.get('rol') != 'Líder', a.get('id')))
        
        for a in sorted_agents[:20]:
            aid = str(a.get('id', '??'))[:4]
            ident = a.get('identidad', {})
            name = (ident.get('nombre', 'Unknown') if isinstance(ident, dict) else 'Unknown')[:15]
            res = a.get('resources', 0)
            
            # Resource character-based bar
            res_val = min(100, max(0, res))
            bar_color = "green" if res_val > 60 else "yellow" if res_val > 30 else "red"
            bar = f"[{bar_color}]{'█' * int(res_val/20)}{'░' * (5 - int(res_val/20))}[/]"
            
            style = "bold white"
            if a.get('is_possessed'): style = "bold white on fuchsia"
            elif a.get('rol') == 'Líder': style = "bold yellow"
            
            rol = (a.get('rol')[:12] if a.get('rol') else "Citizen")
            content += f"[{style}]{aid:4s} | {name:16s} | {rol:12s} | {bar}[/]\n"
            
            thought = a.get('pensamiento', '...')
            content += f"     [dim italic]↳ {thought[:40]}...[/dim italic]\n"
        return content

def main():
    import argparse
    parser = argparse.ArgumentParser(description='MUNDO IA - Ultra Rich TUI')
    parser.add_argument('--ws', default=DEFAULT_WS_URL, help='WebSocket URL')
    parser.add_argument('--http', default=DEFAULT_HTTP_URL, help='HTTP URL')
    parser.add_argument('--user', default=None, help='User ID')
    args = parser.parse_args()
    MundoRemoteTUI(ws_url=args.ws, http_url=args.http, user_id=args.user).run()

if __name__ == "__main__": main()
