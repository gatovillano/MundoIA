#!/usr/bin/env python3
"""
MUNDO IA - Versión CLI
Simulación multiagente en consola con vista de mapa ASCII
"""

import os
import sys
import time
import json
import random
import tempfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

# Añadir el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo import ModeloRelacional, TerrainType
from identity_system import generar_identidad_inicial, NOMBRES_POR_ARQUETIPO

# Colores ANSI
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Terreno
    GRASS = '\033[92m'
    FOREST = '\033[32m'
    MOUNTAIN = '\033[33m'
    WATER = '\033[94m'
    DESERT = '\033[93m'
    ARCHAEOLOGICAL = '\033[35m'
    
    # Recursos
    FOOD = '\033[91m'
    WOOD = '\033[92m'
    STONE = '\033[90m'
    IRON = '\033[97m'
    MEDICINE = '\033[95m'
    CRYSTAL = '\033[96m'
    
    # Agentes
    AGENT = '\033[36m'
    LEADER = '\033[33m'
    
    # UI
    TITLE = '\033[94m'
    INFO = '\033[37m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    SUCCESS = '\033[92m'

class MundoCLI:
    def __init__(self, num_agentes=10, mapa_size=20):
        self.num_agentes = num_agentes
        self.mapa_size = mapa_size
        self.modelo = None
        self.running = False
        self.paused = True
        self.speed = 1.0
        self.step_count = 0
        
    def clear_screen(self):
        """Limpia la pantalla de la consola."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Muestra el encabezado del juego."""
        print(f"{Colors.TITLE}{Colors.BOLD}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║               MUNDO IA - Versión CLI v1.0                   ║")
        print("║          Simulación Multiagente con Mapa Procedural         ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(Colors.RESET)
    
    def get_terrain_symbol(self, tile):
        """Obtiene el símbolo ASCII para un tipo de terreno."""
        symbols = {
            TerrainType.GRASS: '·',
            TerrainType.FOREST: 'T',
            TerrainType.MOUNTAIN: '^',
            TerrainType.WATER: '~',
            TerrainType.DESERT: ':',
            TerrainType.ARCHAEOLOGICAL_SITE: '?',
        }
        base_symbol = symbols.get(tile.terrain_type, '?')
        
        # Si hay un agente, recurso, o sitio arqueológico, se sobrescribe en render_map
        return base_symbol
    
    def get_terrain_color(self, tile_type):
        """Obtiene el color ANSI para un tipo de terreno."""
        colors = {
            TerrainType.GRASS: Colors.GRASS,
            TerrainType.FOREST: Colors.FOREST,
            TerrainType.MOUNTAIN: Colors.MOUNTAIN,
            TerrainType.WATER: Colors.WATER,
            TerrainType.DESERT: Colors.DESERT,
            TerrainType.ARCHAEOLOGICAL_SITE: Colors.ARCHAEOLOGICAL,
        }
        return colors.get(tile_type, Colors.RESET)
    
    def get_resource_symbol(self, resource_type):
        """Obtiene símbolo ASCII para recursos (ancho fijo)."""
        symbols = {
            'food': 'F',     # Food
            'wood': 'W',     # Wood
            'stone': 'S',    # Stone
            'iron': 'I',     # Iron
            'medicine': 'M', # Medicine
            'crystal': 'C',  # Crystal
        }
        return symbols.get(resource_type, '•')
    
    def render_map(self, highlight_agent=None):
        """Renderiza el mapa del terreno en ASCII."""
        if not self.modelo or not self.modelo.mapa:
            print(f"{Colors.WARNING}Mapa no generado aún.{Colors.RESET}")
            return
        
        print(f"\n{Colors.BOLD}📊 MAPA DEL TERRENO (Tamaño: {self.mapa_size}x{self.mapa_size}){Colors.RESET}")
        # Encabezado con índices (0-9 repetidos para mapas >10)
        header = "   "
        for i in range(self.mapa_size):
            header += str(i % 10)
        print(header)
        print("   " + "─" * self.mapa_size)
        
        for x in range(self.mapa_size):
            # Usar x completo para mostrar índices correctos
            line = f"{x:{'2' if self.mapa_size >= 10 else '1'}d} │"
            for y in range(self.mapa_size):
                tile = self.modelo.mapa[x][y]
                if not tile:
                    line += ' '
                    continue
                
                # Buscar agentes en esta celda
                agentes_here = [a for a in self.modelo.agentes if a.x == x and a.y == y]
                
                # Determinar qué mostrar
                char = self.get_terrain_symbol(tile)
                color = self.get_terrain_color(tile.terrain_type)
                
                # Si hay un agente, mostrarlo
                if agentes_here:
                    agente = agentes_here[0]
                    if agente.rol == 'Líder':
                        char = '#'   # Líder
                        color = Colors.LEADER
                    else:
                        char = '@'   # Agente normal
                        color = Colors.AGENT
                # Si hay un sitio arqueológico no descubierto
                elif tile.is_archaeological_site and not tile.discovered_by:
                    char = '?'   # No descubierto
                    color = Colors.ARCHAEOLOGICAL + Colors.BOLD
                # Si hay un sitio arqueológico descubierto
                elif tile.is_archaeological_site and tile.discovered_by:
                    char = '*'   # Descubierto
                    color = Colors.SUCCESS
                # Si hay recurso, mostrarlo
                elif tile.resource_node:
                    resource_symbol = self.get_resource_symbol(tile.resource_node['type'])
                    char = resource_symbol
                    if tile.resource_node['type'] == 'food':
                        color = Colors.FOOD
                    elif tile.resource_node['type'] == 'wood':
                        color = Colors.WOOD
                    elif tile.resource_node['type'] == 'stone':
                        color = Colors.STONE
                    elif tile.resource_node['type'] == 'iron':
                        color = Colors.IRON
                    elif tile.resource_node['type'] == 'medicine':
                        color = Colors.MEDICINE
                    elif tile.resource_node['type'] == 'crystal':
                        color = Colors.CRYSTAL
                
                line += f"{color}{char}{Colors.RESET}"
            line += f"│{x%10}"
            print(line)
        
        print("   " + "─" * self.mapa_size)
        
        # Leyenda
        print(f"\n{Colors.BOLD}Leyenda:{Colors.RESET}")
        print(f"  {Colors.GRASS}·{Colors.RESET}=Pasto  {Colors.FOREST}T{Colors.RESET}=Bosque  {Colors.MOUNTAIN}^{Colors.RESET}=Montaña  {Colors.WATER}~{Colors.RESET}=Agua  {Colors.DESERT}:{Colors.RESET}=Desierto")
        print(f"  {Colors.ARCHAEOLOGICAL}?{Colors.RESET}=Sitio?  {Colors.SUCCESS}*{Colors.RESET}=Sitio✓  {Colors.AGENT}@{Colors.RESET}=Agente  {Colors.LEADER}#{Colors.RESET}=Líder")
        print(f"  {Colors.FOOD}F{Colors.RESET}=Comida  {Colors.WOOD}W{Colors.RESET}=Madera  {Colors.STONE}S{Colors.RESET}=Piedra  {Colors.IRON}I{Colors.RESET}=Hierro  {Colors.MEDICINE}M{Colors.RESET}=Medicina  {Colors.CRYSTAL}C{Colors.RESET}=Cristal")
    
    def print_stats(self):
        """Muestra estadísticas de la simulación."""
        if not self.modelo:
            return
        
        print(f"\n{Colors.BOLD}📈 ESTADÍSTICAS{Colors.RESET}")
        print(f"  Paso actual: {self.modelo.paso_actual}")
        print(f"  Agentes activos: {len(self.modelo.agentes)}")
        
        # Contar por tipo de terreno
        terrain_counts = {}
        for x in range(self.mapa_size):
            for y in range(self.mapa_size):
                tile = self.modelo.mapa[x][y]
                if tile:
                    terrain_counts[tile.terrain_type] = terrain_counts.get(tile.terrain_type, 0) + 1
        
        print(f"\n  Distribución de terrenos:")
        for terrain, count in sorted(terrain_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {terrain}: {count} celdas")
        
        # Sitios arqueológicos descubiertos
        discovered_sites = sum(1 for x in range(self.mapa_size) for y in range(self.mapa_size)
                              if self.modelo.mapa[x][y].is_archaeological_site and
                              self.modelo.mapa[x][y].discovered_by)
        total_sites = sum(1 for x in range(self.mapa_size) for y in range(self.mapa_size)
                         if self.modelo.mapa[x][y].is_archaeological_site)
        print(f"\n  Sitios arqueológicos: {discovered_sites}/{total_sites} descubiertos")
        
        # Recursos totales
        total_resources = {}
        for x in range(self.mapa_size):
            for y in range(self.mapa_size):
                tile = self.modelo.mapa[x][y]
                if tile.resource_node:
                    rtype = tile.resource_node['type']
                    total_resources[rtype] = total_resources.get(rtype, 0) + tile.resource_node['amount']
        
        print(f"\n  Recursos disponibles:")
        for rtype, amount in sorted(total_resources.items()):
            print(f"    {rtype}: {amount}")
    
    def print_agents(self):
        """Muestra información de todos los agentes."""
        if not self.modelo:
            return
        
        print(f"\n{Colors.BOLD}👥 AGENTES{Colors.RESET}")
        for agente in self.modelo.agentes:
            status = "🟢" if agente.necesidades['alimento'] > 3 else "🔴"
            print(f"  {status} {agente.unique_id}: {agente.profesion or 'Sin profesión'} | "
                  f"Pos: ({agente.x},{agente.y}) | "
                  f"Recursos: {agente.recursos:.1f} | "
                  f"Dinero: {agente.dinero:.1f} MC")
    
    def print_help(self):
        """Muestra ayuda de comandos."""
        print(f"\n{Colors.BOLD}📋 COMANDOS DISPONIBLES{Colors.RESET}")
        print("  init       - Inicializar simulación (generar mundo y agentes)")
        print("  map        - Mostrar mapa del terreno")
        print("  stats      - Mostrar estadísticas")
        print("  agents     - Listar todos los agentes")
        print("  step [n]   - Ejecutar n pasos de simulación (default: 1)")
        print("  auto [n]   - Ejecutar automáticamente n pasos por segundo")
        print("  pause      - Pausar ejecución automática")
        print("  reset      - Reiniciar el mundo")
        print("  quit/exit  - Salir")
        print()
    
    def initialize_simulation(self):
        """Inicializa la simulación."""
        print(f"{Colors.INFO}Inicializando simulación...{Colors.RESET}")
        
        # Crear modelo con start_empty=False para que cargue/ genere agentes
        self.modelo = ModeloRelacional(
            num_agentes=self.num_agentes,
            start_empty=False,
            user_id="CLI-USER"
        )
        
        # Forzar generación de mapa si no existe
        if not self.modelo.mapa or len(self.modelo.mapa) == 0:
            print("Generando mapa procedural...")
            self.modelo.mapa = self.modelo.generar_mapa()
        
        self.step_count = 0
        print(f"{Colors.SUCCESS}✓ Simulación inicializada con {len(self.modelo.agentes)} agentes{Colors.RESET}")
        print(f"  Mapa: {self.mapa_size}x{self.mapa_size}")
    
    def run_step(self, steps=1):
        """Ejecuta n pasos de simulación."""
        if not self.modelo:
            print(f"{Colors.ERROR}Simulación no inicializada. Usa 'init' primero.{Colors.RESET}")
            return
        
        for _ in range(steps):
            self.modelo.step()
            self.step_count += 1
            
            # Mostrar eventos importantes
            if self.modelo.historial_logs:
                ultimo_log = self.modelo.historial_logs[-1]
                if ultimo_log.get('categoria') in ['arqueologia', 'descubrimiento']:
                    print(f"  {Colors.SUCCESS}🏛️ {ultimo_log['mensaje']}{Colors.RESET}")
    
    def run_loop(self):
        """Bucle principal de ejecución automática."""
        self.running = True
        while self.running and not self.paused:
            self.run_step(1)
            time.sleep(1.0 / self.speed)
    
    def start_auto(self, speed=1.0):
        """Inicia ejecución automática."""
        self.speed = speed
        self.paused = False
        print(f"{Colors.INFO}Ejecución automática iniciada a {speed}x velocidad{Colors.RESET}")
        
        # Ejecutar en hilo separado
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(self.run_loop)
    
    def command_loop(self):
        """Bucle principal de comandos interactivos."""
        self.clear_screen()
        self.print_header()
        print(f"{Colors.INFO}Bienvenido a MUNDO IA CLI{Colors.RESET}")
        print(f"{Colors.INFO}Escribe 'help' para ver los comandos disponibles.{Colors.RESET}\n")
        
        while True:
            try:
                # Mostrar prompt
                prompt = f"{Colors.BOLD}[ Paso {self.step_count} ]{Colors.RESET} > "
                cmd_input = input(prompt).strip()
                
                if not cmd_input:
                    continue
                
                parts = cmd_input.split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd in ['quit', 'exit']:
                    self.running = False
                    print(f"{Colors.INFO}Saliendo...{Colors.RESET}")
                    break
                
                elif cmd == 'help':
                    self.print_help()
                
                elif cmd == 'init':
                    self.initialize_simulation()
                    self.render_map()
                    self.print_stats()
                
                elif cmd == 'map':
                    self.render_map()
                
                elif cmd == 'stats':
                    self.print_stats()
                
                elif cmd == 'agents':
                    self.print_agents()
                
                elif cmd == 'step':
                    steps = 1
                    if args and args[0].isdigit():
                        steps = int(args[0])
                    print(f"{Colors.INFO}Ejecutando {steps} paso(s)...{Colors.RESET}")
                    self.run_step(steps)
                    self.render_map()
                    self.print_stats()
                
                elif cmd == 'auto':
                    if args and args[0].isdigit():
                        speed = float(args[0])
                        self.start_auto(speed)
                    else:
                        self.start_auto(1.0)
                
                elif cmd == 'pause':
                    self.paused = True
                    print(f"{Colors.INFO}Ejecución pausada{Colors.RESET}")
                
                elif cmd == 'reset':
                    self.modelo = None
                    self.step_count = 0
                    print(f"{Colors.INFO}Simulación reiniciada. Usa 'init' para crear nuevo mundo.{Colors.RESET}")
                
                else:
                    print(f"{Colors.ERROR}Comando desconocido: {cmd}. Escribe 'help' para ayuda.{Colors.RESET}")
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}Interrumpido. Escribe 'quit' para salir.{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MUNDO IA - Versión CLI')
    parser.add_argument('--agents', type=int, default=10, help='Número de agentes (default: 10)')
    parser.add_argument('--size', type=int, default=20, help='Tamaño del mapa (default: 20)')
    parser.add_argument('--auto', action='store_true', help='Ejecutar automáticamente al iniciar')
    
    args = parser.parse_args()
    
    cli = MundoCLI(num_agentes=args.agents, mapa_size=args.size)
    cli.command_loop()

if __name__ == "__main__":
    main()
