#!/usr/bin/env python3
"""
MUNDO IA - CLI conectada al servidor WebSocket
Se conecta al mismo backend que el frontend web
"""

import sys
import os
import json
import asyncio
import uuid
import select
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional

# Añadir directorio del proyecto al path (para TerrainType)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.modelo import TerrainType

# Colores ANSI
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Terreno
    GRASS = '\033[92m'
    FOREST = '\033[32m'
    MOUNTAIN = '\033[33m'
    WATER = '\033[94m'
    DESERT = '\033[93m'
    ARCHAEOLOGICAL = '\033[35m'
    
    # UI
    INFO = '\033[37m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    SUCCESS = '\033[92m'
    AGENT = '\033[36m'
    LEADER = '\033[33m'
    FOOD = '\033[91m'
    WOOD = '\033[92m'
    STONE = '\033[90m'
    IRON = '\033[97m'
    MEDICINE = '\033[95m'
    CRYSTAL = '\033[96m'

class MundoCLIClient:
    """Cliente CLI conectado via WebSocket al servidor."""
    
    def __init__(self, ws_url="wss://api-mundoia.cuerpolibre.cl/ws", user_id=None, agents=10, size=20):
        self.ws_url = ws_url.rstrip('/')
        self.user_id = user_id or f"CLI-{uuid.uuid4().hex[:8]}"
        self.num_agents = agents
        self.map_size = size
        self.websocket = None
        self.running = False
        self.state = {
            "map": None,
            "agents": [],
            "step": 0,
        }
        self.pending_command = None
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        print(f"{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗")
        print(f"║        MUNDO IA - CLI Conectado al Servidor WebSocket       ║")
        print(f"╚══════════════════════════════════════════════════════════════╝{Colors.RESET}")
        print(f"{Colors.INFO}User ID: {self.user_id}{Colors.RESET}")
    
    def get_terrain_symbol(self, terrain_type):
        symbols = {
            TerrainType.GRASS: '·',
            TerrainType.FOREST: 'T',
            TerrainType.MOUNTAIN: '^',
            TerrainType.WATER: '~',
            TerrainType.DESERT: ':',
            TerrainType.ARCHAEOLOGICAL_SITE: '?',
        }
        return symbols.get(terrain_type, '?')
    
    def get_resource_symbol(self, resource_type):
        symbols = {
            'food': 'F',
            'wood': 'W',
            'stone': 'S',
            'iron': 'I',
            'medicine': 'M',
            'crystal': 'C',
        }
        return symbols.get(resource_type, '•')
    
    def render_map(self):
        if not self.state["map"]:
            print(f"{Colors.WARNING}Mapa no disponible. Usa 'init' para generar.{Colors.RESET}")
            return
        
        mapa = self.state["map"]
        size = len(mapa)
        
        print(f"\n{Colors.BOLD}📊 MAPA (Paso: {self.state['step']}, Tamaño: {size}x{size}){Colors.RESET}")
        
        # Encabezado
        header = "   " + "".join(f"{i%10}" for i in range(size))
        print(header)
        print("   " + "─" * size)
        
        for x in range(size):
            line = f"{x%10} │"
            for y in range(size):
                tile = mapa[x][y]
                if not tile:
                    line += ' '
                    continue
                
                # Buscar agentes en esta celda
                agentes_here = [a for a in self.state["agents"] if a.get('x') == x and a.get('y') == y]
                
                char = '?'
                color = Colors.GRASS
                
                if agentes_here:
                    agente = agentes_here[0]
                    char = '#' if agente.get('rol') == 'Líder' else '@'
                    color = Colors.LEADER if agente.get('rol') == 'Líder' else Colors.AGENT
                elif tile.get('is_archaeological_site'):
                    if tile.get('discovered_by'):
                        char = '*'
                        color = Colors.SUCCESS
                    else:
                        char = '?'
                        color = Colors.ARCHAEOLOGICAL + Colors.BOLD
                elif tile.get('resource'):
                    char = self.get_resource_symbol(tile['resource']['type'])
                    color_map = {
                        'food': Colors.FOOD,
                        'wood': Colors.WOOD,
                        'stone': Colors.STONE,
                        'iron': Colors.IRON,
                        'medicine': Colors.MEDICINE,
                        'crystal': Colors.CRYSTAL,
                    }
                    color = color_map.get(tile['resource']['type'], Colors.WHITE)
                else:
                    terrain_type = tile.get('terrain')
                    symbols = {
                        TerrainType.GRASS: '·',
                        TerrainType.FOREST: 'T',
                        TerrainType.MOUNTAIN: '^',
                        TerrainType.WATER: '~',
                        TerrainType.DESERT: ':',
                    }
                    char = symbols.get(terrain_type, '?')
                    terrain_colors = {
                        TerrainType.GRASS: Colors.GRASS,
                        TerrainType.FOREST: Colors.FOREST,
                        TerrainType.MOUNTAIN: Colors.MOUNTAIN,
                        TerrainType.WATER: Colors.WATER,
                        TerrainType.DESERT: Colors.DESERT,
                    }
                    color = terrain_colors.get(terrain_type, Colors.WHITE)
                
                line += f"{color}{char}{Colors.RESET}"
            line += f"│{x%10}"
            print(line)
        
        print("   " + "─" * size)
        
        # Leyenda
        print(f"\nLeyenda:")
        print(f"  {Colors.GRASS}·{Colors.RESET}=Pasto  {Colors.FOREST}T{Colors.RESET}=Bosque  {Colors.MOUNTAIN}^{Colors.RESET}=Montaña  {Colors.WATER}~{Colors.RESET}=Agua  {Colors.DESERT}:{Colors.RESET}=Desierto")
        print(f"  {Colors.ARCHAEOLOGICAL}?{Colors.RESET}=Sitio?  {Colors.SUCCESS}*{Colors.RESET}=Sitio✓  {Colors.AGENT}@{Colors.RESET}=Agente  {Colors.LEADER}#{Colors.RESET}=Líder")
        print(f"  {Colors.FOOD}F{Colors.RESET}=Comida  {Colors.WOOD}W{Colors.RESET}=Madera  {Colors.STONE}S{Colors.RESET}=Piedra  {Colors.IRON}I{Colors.RESET}=Hierro  {Colors.MEDICINE}M{Colors.RESET}=Medicina  {Colors.CRYSTAL}C{Colors.RESET}=Cristal")
    
    def print_stats(self):
        if not self.state["agents"]:
            print(f"{Colors.WARNING}No hay agentes.{Colors.RESET}")
            return
        
        print(f"\n{Colors.BOLD}📈 ESTADÍSTICAS (Paso {self.state['step']}){Colors.RESET}")
        print(f"Agentes activos: {len(self.state['agents'])}")
        
        avg_res = sum(a.get('resources', 0) for a in self.state['agents']) / len(self.state['agents'])
        avg_money = sum(a.get('money', 0) for a in self.state['agents']) / len(self.state['agents'])
        print(f"Recursos promedio: {avg_res:.1f}")
        print(f"Dinero promedio: {avg_money:.1f} MC")
        
        if self.state["map"]:
            terrain_counts = {}
            for row in self.state["map"]:
                for tile in row:
                    if tile:
                        t = tile['terrain']
                        terrain_counts[t] = terrain_counts.get(t, 0) + 1
            
            print(f"\nTerrenos:")
            for terrain, count in sorted(terrain_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {terrain}: {count}")
            
            total_sites = sum(1 for row in self.state["map"] for tile in row if tile and tile.get('is_archaeological_site'))
            discovered = sum(1 for row in self.state["map"] for tile in row if tile and tile.get('is_archaeological_site') and tile.get('discovered_by'))
            print(f"\nSitios arqueológicos: {discovered}/{total_sites} descubiertos")
    
    def print_agents(self):
        if not self.state["agents"]:
            print(f"{Colors.WARNING}No hay agentes.{Colors.RESET}")
            return
        
        print(f"\n{Colors.BOLD}👥 AGENTES{Colors.RESET}")
        print("ID   | Nombre            | Pos   | Rec   | Dinero")
        print("─────┼──────────────────┼───────┼───────┼────────")
        
        for agente in self.state["agents"][:15]:
            aid = agente.get('id', 'N/A')[:4]
            ident = agente.get('identidad', {})
            nombre = (ident.get('nombre', 'Sin nombre') if isinstance(ident, dict) else 'Sin nombre')[:12]
            x, y = agente.get('x', 0), agente.get('y', 0)
            rec = agente.get('resources', 0)
            money = agente.get('money', 0)
            print(f"{aid:4s} | {nombre:16s} | ({x:2d},{y:2d}) | {rec:5.1f} | {money:6.1f}")
        
        if len(self.state["agents"]) > 15:
            print(f"... y {len(self.state['agents']) - 15} más")
    
    def print_help(self):
        print(f"\n{Colors.BOLD}📋 COMANDOS{Colors.RESET}")
        print("  init       - Crear nueva partida")
        print("  step [n]   - Avanzar n pasos (default: 1)")
        print("  map        - Mostrar mapa")
        print("  stats      - Mostrar estadísticas")
        print("  agents     - Listar agentes")
        print("  reset      - Reiniciar partida")
        print("  quit/exit  - Desconectar y salir")
        print("  help       - Esta ayuda")
        print(f"\n{Colors.INFO}La simulación se ejecuta en el servidor.{Colors.RESET}")
    
    async def connect(self):
        ws_url = f"{self.ws_url}?user_id={self.user_id}"
        try:
            self.websocket = await websockets.connect(ws_url)
            print(f"{Colors.SUCCESS}✓ Conectado a {ws_url}{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.ERROR}❌ Error conectando: {e}{Colors.RESET}")
            return False
    
    async def send_http_command(self, command, params=None):
        url = self.ws_url.replace("wss://", "https://").replace("ws://", "http://").replace("/ws", "/game/control")
        payload = {"command": command, "user_id": self.user_id}
        if params:
            payload.update(params)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"{Colors.SUCCESS}✓ Comando '{command}' ejecutado{Colors.RESET}")
                        return data
                    else:
                        error_text = await resp.text()
                        print(f"{Colors.ERROR}❌ Error {resp.status}: {error_text[:100]}{Colors.RESET}")
                        return None
        except Exception as e:
            print(f"{Colors.ERROR}❌ Error enviando comando: {e}{Colors.RESET}")
            return None
    
    async def listen(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    print(f"{Colors.WARNING}⚠️ Mensaje no JSON: {message[:100]}{Colors.RESET}")
        except websockets.exceptions.ConnectionClosed:
            print(f"{Colors.WARNING}⚠️ Conexión WebSocket cerrada{Colors.RESET}")
            self.running = False
    
    async def handle_message(self, data: Dict):
        msg_type = data.get('type', 'unknown')
        
        if msg_type == 'initial_state':
            self.state["map"] = data.get('map')
            self.state["agents"] = data.get('agents', [])
            self.state["step"] = data.get('step', 0)
            print(f"\n{Colors.SUCCESS}✓ Estado inicial recibido:{Colors.RESET}")
            print(f"   Mapa: {len(self.state['map'])}x{len(self.state['map'][0]) if self.state['map'] else 0}")
            print(f"   Agentes: {len(self.state['agents'])}")
            self.render_map()
            
        elif msg_type == 'log':
            log_msg = data.get('message', '')
            categoria = data.get('category', 'info')
            prefix_map = {
                'sistema': '📢',
                'arqueologia': '🏛️',
                'social': '💬',
                'economia': '💰',
                'error': '❌',
            }
            prefix = prefix_map.get(categoria, '•')
            print(f"{prefix} {log_msg}")
            
            if categoria == 'arqueologia':
                self.render_map()
                
        elif msg_type == 'stats_update':
            self.state['step'] = data.get('step', self.state['step'])
            # Podríamos actualizar sin redibujar completamente
    
    async def command_loop(self):
        while self.running:
            try:
                if self.pending_command:
                    cmd = self.pending_command
                    self.pending_command = None
                    
                    parts = cmd.split()
                    command = parts[0].lower()
                    args = parts[1:]
                    
                    if command in ['quit', 'exit']:
                        self.running = False
                        break
                    
                    elif command == 'help':
                        self.print_help()
                    
                    elif command == 'init':
                        print(f"{Colors.INFO}Creando nueva partida...{Colors.RESET}")
                        result = await self.send_http_command('init', {
                            'num_agents': self.num_agents,
                            'map_size': self.map_size
                        })
                        if result:
                            # Esperar initial_state por WebSocket
                            await asyncio.sleep(1)
                    
                    elif command == 'step':
                        steps = 1
                        if args and args[0].isdigit():
                            steps = int(args[0])
                        print(f"{Colors.INFO}Avanzando {steps} paso(s)...{Colors.RESET}")
                        result = await self.send_http_command('step', {'steps': steps})
                        if result:
                            # El servidor enviará actualización por WebSocket
                            await asyncio.sleep(0.5)
                    
                    elif command == 'reset':
                        print(f"{Colors.INFO}Reiniciando partida...{Colors.RESET}")
                        result = await self.send_http_command('reset')
                        if result:
                            self.state = {"map": None, "agents": [], "step": 0}
                            await asyncio.sleep(1)
                    
                    elif command == 'map':
                        self.render_map()
                    
                    elif command == 'stats':
                        self.print_stats()
                    
                    elif command == 'agents':
                        self.print_agents()
                    
                    else:
                        print(f"{Colors.ERROR}Comando desconocido: {command}{Colors.RESET}")
                        
                await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")
    
    def input_reader(self):
        """Lee comandos de stdin en hilo separado."""
        while self.running:
            try:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    cmd = sys.stdin.readline().strip()
                    if cmd:
                        self.pending_command = cmd
            except:
                break
    
    async def run(self):
        self.print_header()
        print(f"{Colors.INFO}Conectando a {self.ws_url}?user_id={self.user_id}...{Colors.RESET}")
        
        if not await self.connect():
            return
        
        self.running = True
        
        # Iniciar hilo para leer entrada
        import threading
        input_thread = threading.Thread(target=self.input_reader, daemon=True)
        input_thread.start()
        
        # Tareas asyncio
        listener_task = asyncio.create_task(self.listen())
        commander_task = asyncio.create_task(self.command_loop())
        
        try:
            await asyncio.gather(listener_task, commander_task)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Interrumpido. Saliendo...{Colors.RESET}")
        finally:
            self.running = False
            listener_task.cancel()
            commander_task.cancel()
            if self.websocket:
                await self.websocket.close()

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='MUNDO IA - CLI conectada a WebSocket')
    parser.add_argument('--ws', default='wss://api-mundoia.cuerpolibre.cl/ws', help='URL del WebSocket server')
    parser.add_argument('--user', default=None, help='User ID para la sesión (si no se genera aleatorio)')
    parser.add_argument('--agents', type=int, default=10, help='Número de agentes para init')
    parser.add_argument('--size', type=int, default=20, help='Tamaño del mapa para init')
    
    args = parser.parse_args()
    
    client = MundoCLIClient(
        ws_url=args.ws,
        user_id=args.user,
        agents=args.agents,
        size=args.size
    )
    await client.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.INFO}Saliendo...{Colors.RESET}")
