#!/usr/bin/env python3
"""
MUNDO IA - CLI HTTP (sin WebSocket)
Se conecta a la API REST para controlar la simulación
"""

import sys
import os
import uuid
import time
import json
import requests
from typing import Dict, List

# Añadir directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo import TerrainType

# Colores ANSI
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    GRASS = '\033[92m'
    FOREST = '\033[32m'
    MOUNTAIN = '\033[33m'
    WATER = '\033[94m'
    DESERT = '\033[93m'
    ARCHAEOLOGICAL = '\033[35m'
    
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

class MundoCLIHTTP:
    """Cliente CLI que usa solo HTTP (no WebSocket)."""
    
    def __init__(self, base_url="https://api-mundoia.cuerpolibre.cl", user_id=None, agents=10, size=20):
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id or f"CLI-{uuid.uuid4().hex[:8]}"
        self.num_agents = agents
        self.map_size = size
        self.session = requests.Session()
        self.state = {
            "map": None,
            "agents": [],
            "step": 0,
        }
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        print(f"{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗")
        print(f"║        MUNDO IA - CLI (HTTP)                                 ║")
        print(f"╚══════════════════════════════════════════════════════════════╝{Colors.RESET}")
        print(f"{Colors.INFO}User ID: {self.user_id}{Colors.RESET}")
        print(f"{Colors.INFO}Servidor: {self.base_url}{Colors.RESET}")
    
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
        print("  quit/exit  - Salir")
        print("  help       - Esta ayuda")
        print(f"\n{Colors.INFO}Ejemplos:{Colors.RESET}")
        print("  init              # Crear partida con 10 agentes, mapa 20x20")
        print("  step 5            # Avanzar 5 pasos")
        print("  map               # Ver mapa")
    
    def send_command(self, command, params=None):
        """Enviar comando al servidor via HTTP."""
        payload = {"command": command, "user_id": self.user_id}
        if params:
            payload.update(params)
        
        try:
            resp = self.session.post(
                f"{self.base_url}/game/control",
                json=payload,
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"{Colors.ERROR}❌ Error {resp.status_code}: {resp.text[:200]}{Colors.RESET}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"{Colors.ERROR}❌ Error de conexión: {e}{Colors.RESET}")
            return None
    
    def fetch_state(self):
        """Obtener estado actual desde el servidor."""
        try:
            # Obtener agentes
            agents_resp = self.session.get(f"{self.base_url}/chat/{self.user_id}/agents", timeout=5)
            if agents_resp.ok:
                self.state["agents"] = agents_resp.json().get("agents", [])
            
            # Obtener mapa
            map_resp = self.session.get(f"{self.base_url}/chat/{self.user_id}/map", timeout=5)
            if map_resp.ok:
                map_data = map_resp.json()
                self.state["map"] = map_data.get("map", [])
                self.state["size"] = map_data.get("size", 0)
            
            # Obtener stats
            stats_resp = self.session.get(f"{self.base_url}/chat/{self.user_id}/stats", timeout=5)
            if stats_resp.ok:
                self.state["step"] = stats_resp.json().get("step", 0)
            
        except requests.exceptions.RequestException as e:
            print(f"{Colors.WARNING}⚠️ Error obteniendo estado: {e}{Colors.RESET}")
    
    def run(self):
        self.print_header()
        print(f"{Colors.INFO}Comandos: init, step, map, stats, agents, reset, quit, help{Colors.RESET}\n")
        
        while True:
            try:
                # Mostrar prompt con paso actual
                prompt = f"{Colors.BOLD}[ Paso {self.state['step']} ]{Colors.RESET} > "
                cmd = input(prompt).strip()
                
                if not cmd:
                    continue
                
                parts = cmd.split()
                command = parts[0].lower()
                args = parts[1:]
                
                if command in ['quit', 'exit']:
                    print(f"{Colors.INFO}Saliendo...{Colors.RESET}")
                    break
                
                elif command == 'help':
                    self.print_help()
                
                elif command == 'init':
                    print(f"{Colors.INFO}Creando nueva partida...{Colors.RESET}")
                    result = self.send_command('init', {
                        'num_agents': self.num_agents,
                        'map_size': self.map_size
                    })
                    if result:
                        # Esperar un momento y obtener estado
                        time.sleep(1)
                        self.fetch_state()
                        print(f"{Colors.SUCCESS}✓ Partida creada con {self.state['size']}x{self.state['size']} y {len(self.state['agents'])} agentes{Colors.RESET}")
                        self.render_map()
                
                elif command == 'step':
                    steps = 1
                    if args and args[0].isdigit():
                        steps = int(args[0])
                    print(f"{Colors.INFO}Avanzando {steps} paso(s)...{Colors.RESET}")
                    result = self.send_command('step', {'steps': steps})
                    if result:
                        time.sleep(0.5)
                        self.fetch_state()
                        print(f"{Colors.SUCCESS}✓ Paso {self.state['step']} completado{Colors.RESET}")
                        self.render_map()
                
                elif command == 'reset':
                    print(f"{Colors.INFO}Reiniciando partida...{Colors.RESET}")
                    result = self.send_command('reset')
                    if result:
                        self.state = {"map": None, "agents": [], "step": 0}
                        time.sleep(1)
                        print(f"{Colors.SUCCESS}✓ Partida reiniciada{Colors.RESET}")
                
                elif command == 'map':
                    self.fetch_state()
                    self.render_map()
                
                elif command == 'stats':
                    self.fetch_state()
                    self.print_stats()
                
                elif command == 'agents':
                    self.fetch_state()
                    self.print_agents()
                
                else:
                    print(f"{Colors.ERROR}Comando desconocido: {command}{Colors.RESET}")
                    print(f"{Colors.INFO}Escribe 'help' para ver comandos disponibles.{Colors.RESET}")
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}Interrumpido. Escribe 'quit' para salir.{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='MUNDO IA - CLI HTTP')
    parser.add_argument('--host', default='api-mundoia.cuerpolibre.cl', help='Host del servidor')
    parser.add_argument('--port', type=int, default=443, help='Puerto del servidor')
    parser.add_argument('--user', default=None, help='User ID para la sesión')
    parser.add_argument('--agents', type=int, default=10, help='Número de agentes para init')
    parser.add_argument('--size', type=int, default=20, help='Tamaño del mapa para init')
    
    args = parser.parse_args()
    
    base_url = f"https://{args.host}" if args.port == 443 else f"http://{args.host}:{args.port}"
    client = MundoCLIHTTP(
        base_url=base_url,
        user_id=args.user,
        agents=args.agents,
        size=args.size
    )
    
    try:
        client.run()
    except KeyboardInterrupt:
        print(f"\n{Colors.INFO}Saliendo...{Colors.RESET}")

if __name__ == "__main__":
    main()
