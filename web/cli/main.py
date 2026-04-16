#!/usr/bin/env python3
"""
MUNDO IA - CLI del Arquitecto
Usa ModeloRelacional directamente (sin HTTP).
Expone las mismas opciones que el panel de Arquitecto del frontend web.
"""

import os
import sys
import time
import threading
import argparse
import random

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.modelo import ModeloRelacional, TerrainType

# ─── COLORES ANSI ─────────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    GRAY    = "\033[90m"

def ok(t):   return f"{C.GREEN}✓ {t}{C.RESET}"
def err(t):  return f"{C.RED}✗ {t}{C.RESET}"
def warn(t): return f"{C.YELLOW}⚠ {t}{C.RESET}"
def info(t): return f"{C.CYAN}→ {t}{C.RESET}"
def dim(t):  return f"{C.GRAY}{t}{C.RESET}"
def sep():   return f"{C.GRAY}{'─' * 60}{C.RESET}"
def title(t):return f"{C.BOLD}{C.YELLOW}{t}{C.RESET}"

# ─── HELPERS DE INPUT ─────────────────────────────────────────────────────────

def prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{C.YELLOW}{text}{suffix}: {C.RESET}").strip()
    return val if val else default

def prompt_int(text: str, default: int = 1, lo: int = 1, hi: int = 100) -> int:
    while True:
        raw = prompt(text, str(default))
        try:
            val = int(raw)
            if lo <= val <= hi:
                return val
            print(err(f"Debe estar entre {lo} y {hi}"))
        except ValueError:
            print(err("Número inválido"))

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def header(text: str):
    print()
    print(title(f"╔══ {text} "))
    print()

# ─── RENDER DEL MAPA ASCII ────────────────────────────────────────────────────

TERRAIN_SYMBOLS = {
    TerrainType.GRASS:             ("·", C.GREEN),
    TerrainType.FOREST:            ("T", "\033[32m"),
    TerrainType.MOUNTAIN:          ("^", C.YELLOW),
    TerrainType.WATER:             ("~", C.BLUE),
    TerrainType.DESERT:            (":", "\033[93m"),
    TerrainType.ARCHAEOLOGICAL_SITE: ("?", C.MAGENTA),
}

def render_map(modelo: ModeloRelacional):
    if not modelo or not modelo.mapa:
        print(warn("Mapa no disponible."))
        return
    mapa = modelo.mapa
    size = len(mapa)
    print(f"\n{C.BOLD}Mapa {size}x{size} — Paso {modelo.paso_actual}{C.RESET}")
    print("   " + "".join(str(i % 10) for i in range(size)))
    print("   " + "─" * size)
    for x in range(size):
        line = f"{x:2d}│"
        for y in range(size):
            tile = mapa[x][y]
            if not tile:
                line += " "
                continue
            agentes_aqui = [a for a in modelo.agentes if a.x == x and a.y == y]
            if agentes_aqui:
                a = agentes_aqui[0]
                char  = "#" if a.rol == "Líder" else "@"
                color = C.YELLOW if a.rol == "Líder" else C.CYAN
            else:
                char, color = TERRAIN_SYMBOLS.get(tile.terrain_type, ("?", C.RESET))
                if tile.resource_node:
                    rmap = {"food": "F", "wood": "W", "stone": "S",
                            "iron": "I", "medicine": "M", "crystal": "C"}
                    char  = rmap.get(tile.resource_node["type"], "r")
                    color = C.RED
            line += f"{color}{char}{C.RESET}"
        print(line + f"│{x % 10}")
    print("   " + "─" * size)
    print(dim("· pasto  T bosque  ^ montaña  ~ agua  : desierto  @ agente  # líder"))

# ─── SECCIONES DEL PANEL DE ARQUITECTO ───────────────────────────────────────

def menu_voz_arquitecto(modelo: ModeloRelacional, selected_agent: list):
    """Voz del Arquitecto — replica ArchitectPanel sección 1"""
    header("VOZ DEL ARQUITECTO")
    print(f"  {C.BOLD}1{C.RESET} Decreto Global  (a toda la creación)")
    print(f"  {C.BOLD}2{C.RESET} Susurro al Ser  (a agente específico)")
    print(f"  {C.BOLD}0{C.RESET} Volver")
    op = prompt("Opción")

    if op == "1":
        msg = prompt("Dictar voluntad a la creación")
        if msg:
            for agente in modelo.agentes:
                agente.memoria.registrar_mensaje("arquitecto", f"[DECRETO] {msg}")
            modelo.log(f"📢 [ARQUITECTO] Decreto Global: '{msg}'", categoria="sistema")
            print(ok("Decreto transmitido a todos los seres"))

    elif op == "2":
        agent_id = selected_agent[0] or prompt("ID del agente receptor")
        if not agent_id:
            print(warn("Sin agente seleccionado"))
            return
        agente = next((a for a in modelo.agentes if a.unique_id == agent_id), None)
        if not agente:
            print(err(f"Agente '{agent_id}' no encontrado"))
            return
        msg = prompt("Susurro al ser")
        if msg:
            agente.memoria.registrar_mensaje("arquitecto", f"[SUSURRO] {msg}")
            modelo.log(f"🔮 [ARQUITECTO] Susurro al Ser {agent_id}: '{msg}'", categoria="sistema")
            print(ok(f"Susurro enviado a {agent_id}"))


def menu_lore(modelo: ModeloRelacional, _):
    """Realidad Narrativa — replica sección 1.5"""
    header("REALIDAD NARRATIVA (LORE)")
    actual = getattr(modelo, "lore", "Sin definir")
    print(dim(f"  Lore actual: {actual[:80]}..." if len(actual) > 80 else f"  Lore actual: {actual}"))
    lore = prompt("Define la nueva realidad narrativa")
    if lore:
        modelo.lore = lore
        modelo.log(f"📜 [NARRATIVA] Arquitecto redefine la realidad: '{lore}'", categoria="sistema")
        print(ok("Realidad narrativa actualizada"))


def menu_control_realidad(modelo: ModeloRelacional, _):
    """Control de la Realidad — replica sección 2"""
    header("CONTROL DE LA REALIDAD")
    print(f"  {C.YELLOW}── Clima ──{C.RESET}")
    print(f"  {C.BOLD}1{C.RESET} Día Radiante   (sunny)")
    print(f"  {C.BOLD}2{C.RESET} Diluvio        (rainy)")
    print(f"  {C.BOLD}3{C.RESET} Tormenta Glitch (storm)")
    print(f"  {C.BOLD}4{C.RESET} Ola de Calor   (heatwave)")
    print(f"  {C.BOLD}5{C.RESET} Niebla         (foggy)")
    print(f"  {C.YELLOW}── Eventos ──{C.RESET}")
    print(f"  {C.BOLD}6{C.RESET} Plaga Viral")
    print(f"  {C.BOLD}7{C.RESET} Terremoto")
    print(f"  {C.BOLD}0{C.RESET} Volver")

    weathers = {"1": "sunny", "2": "rainy", "3": "storm", "4": "heatwave", "5": "foggy"}
    op = prompt("Opción")

    if op in weathers:
        modelo.weather = weathers[op]
        modelo.log(f"🌩️ [DIVINO] Clima cambiado a {weathers[op]}", categoria="ambiente")
        print(ok(f"Clima: {weathers[op]}"))
    elif op == "6":
        for a in modelo.agentes:
            a.necesidades["salud"] -= 1
        modelo.log("☣️ [DIVINO] Una PLAGA se desata sobre la población.", categoria="evento")
        print(ok("Plaga activada"))
    elif op == "7":
        afectados = 0
        for a in modelo.agentes:
            if random.random() < 0.3:
                a.necesidades["salud"] -= 3
                afectados += 1
        modelo.log(f"🌍 [DIVINO] ¡TERREMOTO! {afectados} agentes heridos.", categoria="evento")
        print(ok(f"Terremoto: {afectados} heridos"))


def menu_genesis(modelo: ModeloRelacional, _):
    """Génesis Artificial — replica sección 3"""
    header("GÉNESIS ARTIFICIAL")
    count = prompt_int("Cantidad de seres a manifestar (1-10)", default=1, lo=1, hi=10)
    ids = []
    for _ in range(count):
        agente = modelo.spawn_agent()
        ids.append(agente.unique_id)
    modelo.log(f"🧬 [DIVINO] Manifestados {count} nuevos seres: {ids}", categoria="sistema")
    print(ok(f"Creados: {', '.join(ids)}"))


def menu_expansion(modelo: ModeloRelacional, _):
    """Expansión Territorial — replica sección 3.2"""
    header("EXPANSIÓN TERRITORIAL")
    print(f"  Dirección: {C.BOLD}N{C.RESET}orte / {C.BOLD}S{C.RESET}ur / {C.BOLD}E{C.RESET}ste / {C.BOLD}O{C.RESET}este / {C.BOLD}T{C.RESET}odas")
    d = prompt("Dirección", "T").upper()
    dir_map = {"N": "north", "S": "south", "E": "east", "O": "west", "T": None}
    if d not in dir_map:
        print(warn("Dirección inválida"))
        return
    cantidad = prompt_int("Casillas a expandir (1-10)", default=1, lo=1, hi=10)
    ok_flag, msg = modelo.expandir_mundo(direccion=dir_map[d], cantidad=cantidad)
    print(ok(msg) if ok_flag else err(msg))


def menu_compra_terreno(modelo: ModeloRelacional, _):
    """Compra de Terreno por Grupos — replica sección 3.3"""
    header("COMPRA DE TERRENO (GRUPOS)")
    grupos = list(modelo.civilizaciones.keys())
    if grupos:
        print("  Grupos disponibles: " + ", ".join(grupos))
    grupo_id = prompt("ID del grupo comprador")
    if not grupo_id:
        print(warn("Grupo requerido"))
        return
    cantidad = prompt_int("Casillas (1-10)", default=1, lo=1, hi=10)
    print(dim(f"  Costo estimado: {cantidad * 1000} MC"))
    d = prompt("Dirección (N/S/E/O/T)", "T").upper()
    dir_map = {"N": "north", "S": "south", "E": "east", "O": "west", "T": None}
    if d not in dir_map:
        print(warn("Dirección inválida"))
        return
    ok_flag, msg = modelo.expandir_mundo(
        direccion=dir_map[d], cantidad=cantidad,
        comprador_id=grupo_id, costo_override=cantidad * 1000
    )
    print(ok(msg) if ok_flag else err(msg))


def menu_misiones(modelo: ModeloRelacional, _):
    """Objetivos Colectivos — replica sección 3.5"""
    header("OBJETIVOS COLECTIVOS (MISIONES)")
    titulo = prompt("Título de la misión")
    if not titulo:
        print(warn("Título requerido"))
        return
    descripcion = prompt("Descripción del objetivo")
    ok_flag, msg = modelo.crear_mision(
        titulo, descripcion, "global", {"tipo": "global"}, {"puntos": 500}
    )
    print(ok(msg) if ok_flag else err(msg))


def menu_gobernanza(modelo: ModeloRelacional, _):
    """Gobernanza Divina — replica sección 4"""
    header("GOBERNANZA DIVINA")
    topic = prompt("Tema de la asamblea ciudadana")
    if not topic:
        print(warn("Tema requerido"))
        return
    if modelo.agentes:
        proponente = random.choice(modelo.agentes).unique_id
    else:
        proponente = "arquitecto"
    ok_flag, msg = modelo.crear_asamblea(proponente, topic)
    print(ok(msg) if ok_flag else err(msg))


def menu_economia(modelo: ModeloRelacional, _):
    """Arquitectura Económica — replica sección 5"""
    header("ARQUITECTURA ECONÓMICA")
    total = modelo.economia.get("total_dinero", 0)
    print(f"  {dim('Reserva Federal:')} {C.GREEN}{total:.1f} MC{C.RESET}")
    print(f"  {C.BOLD}1{C.RESET} Inyectar capital (+1000 MC, precios bajan)")
    print(f"  {C.BOLD}2{C.RESET} Colapsar mercado (índice ÷2, precios x2)")
    print(f"  {C.BOLD}0{C.RESET} Volver")
    op = prompt("Opción")
    if op == "1":
        modelo.economia["total_dinero"] += 1000
        modelo.economia["precio_recurso"] *= 0.8
        modelo.log("💸 [DIVINO] Capital divino inyectado en la economía.", categoria="economia")
        print(ok("Capital inyectado"))
    elif op == "2":
        modelo.economia["indice_bursatil"] *= 0.5
        modelo.economia["precio_recurso"] *= 2.0
        modelo.log("📉 [DIVINO] ¡El mercado ha COLAPSADO!", categoria="economia")
        print(ok("Mercado colapsado"))


def menu_decreto_individual(modelo: ModeloRelacional, selected_agent: list):
    """Decreto Individual — replica sección 6"""
    header("DECRETO INDIVIDUAL")
    agent_id = selected_agent[0] or prompt("ID del agente")
    if not agent_id:
        print(warn("Sin agente seleccionado"))
        return
    agente = next((a for a in modelo.agentes if a.unique_id == agent_id), None)
    if not agente:
        print(err(f"Agente '{agent_id}' no encontrado"))
        return
    print(f"  Agente: {C.YELLOW}{agent_id}{C.RESET}")
    print(f"  {C.BOLD}1{C.RESET} Sanar      (salud máxima)")
    print(f"  {C.BOLD}2{C.RESET} Castigar   (smite: salud=1, recursos=0)")
    print(f"  {C.BOLD}3{C.RESET} Eliminar   (kill)")
    print(f"  {C.BOLD}4{C.RESET} Enriquecer (+500 MC)")
    print(f"  {C.BOLD}0{C.RESET} Volver")
    op = prompt("Opción")
    if op == "1":
        agente.necesidades["salud"] = 10.0
        agente.necesidades["alimento"] = 0.0
        modelo.log(f"✨ [DIVINO] Agente {agent_id} SANADO.", categoria="milagro")
        print(ok("Agente sanado"))
    elif op == "2":
        agente.necesidades["salud"] = 1.0
        agente.recursos = 0
        modelo.log(f"⚡ [DIVINO] Agente {agent_id} CASTIGADO.", categoria="milagro")
        print(ok("Agente castigado"))
    elif op == "3":
        modelo.agentes = [a for a in modelo.agentes if a.unique_id != agent_id]
        modelo.log(f"💀 [DIVINO] Agente {agent_id} ELIMINADO.", categoria="milagro")
        if selected_agent[0] == agent_id:
            selected_agent[0] = None
        print(ok("Agente eliminado"))
    elif op == "4":
        agente.dinero += 500
        modelo.log(f"💰 [DIVINO] Agente {agent_id} enriquecido.", categoria="milagro")
        print(ok("Agente enriquecido"))


# ─── CONTROL DE SIMULACIÓN ────────────────────────────────────────────────────

def menu_simulacion(modelo: ModeloRelacional, running: list, _):
    """Control básico de la simulación"""
    header("CONTROL DE SIMULACIÓN")
    paso = modelo.paso_actual
    agentes_n = len(modelo.agentes)
    print(f"  {dim('Paso:')} {paso}   {dim('Agentes:')} {agentes_n}   {dim('Corriendo:')} {'Sí' if running[0] else 'No'}")
    print(f"  {C.BOLD}1{C.RESET} Ejecutar 1 paso")
    print(f"  {C.BOLD}2{C.RESET} Ejecutar N pasos")
    print(f"  {C.BOLD}3{C.RESET} Ver mapa")
    print(f"  {C.BOLD}4{C.RESET} Ver agentes")
    print(f"  {C.BOLD}5{C.RESET} Ver últimos logs")
    print(f"  {C.BOLD}0{C.RESET} Volver")
    op = prompt("Opción")

    if op == "1":
        modelo.step()
        print(ok(f"Paso {modelo.paso_actual} ejecutado"))
    elif op == "2":
        n = prompt_int("Número de pasos", default=10, lo=1, hi=1000)
        print(info(f"Ejecutando {n} pasos..."))
        for i in range(n):
            modelo.step()
            print(f"  {dim(f'{i+1}/{n}')}", end="\r")
        print()
        print(ok(f"{n} pasos completados (paso actual: {modelo.paso_actual})"))
    elif op == "3":
        render_map(modelo)
    elif op == "4":
        print()
        for a in modelo.agentes[:20]:
            nombre = (a.identidad.nombre if a.identidad else a.unique_id)[:16]
            pos_str = f"({a.x:2},{a.y:2})"
            salud_val = a.necesidades.get('salud', 0)
            print(f"  {C.CYAN}{a.unique_id:4}{C.RESET} {nombre:16} {pos_str} "
                  f"Rec:{a.recursos:5.0f}  MC:{a.dinero:6.0f}  "
                  f"Sal:{salud_val:4.1f}")
        if len(modelo.agentes) > 20:
            print(dim(f"  ... y {len(modelo.agentes)-20} más"))
    elif op == "5":
        logs = modelo.historial_logs[-15:]
        print()
        for log in logs:
            st = log.get('step', '?')
            msg = log.get('mensaje', '')
            print(f"  {dim(f'[{st}]')} {msg}")


def menu_seleccionar_agente(modelo: ModeloRelacional, selected_agent: list):
    header("SELECCIONAR AGENTE")
    if modelo.agentes:
        ids = [a.unique_id for a in modelo.agentes[:10]]
        print(f"  Agentes: {', '.join(ids)}")
    agent_id = prompt("ID del agente (vacío = deseleccionar)")
    selected_agent[0] = agent_id if agent_id else None
    print(ok(f"Agente seleccionado: {selected_agent[0]}") if selected_agent[0] else ok("Selección limpiada"))


# ─── MENÚ PRINCIPAL ───────────────────────────────────────────────────────────

MENU = [
    ("1",  "Voz del Arquitecto",            lambda m, s: menu_voz_arquitecto(m, s)),
    ("2",  "Realidad Narrativa (Lore)",     lambda m, s: menu_lore(m, s)),
    ("3",  "Control de la Realidad",        lambda m, s: menu_control_realidad(m, s)),
    ("4",  "Génesis Artificial",            lambda m, s: menu_genesis(m, s)),
    ("5",  "Expansión Territorial",         lambda m, s: menu_expansion(m, s)),
    ("6",  "Compra de Terreno (Grupos)",    lambda m, s: menu_compra_terreno(m, s)),
    ("7",  "Objetivos Colectivos",          lambda m, s: menu_misiones(m, s)),
    ("8",  "Gobernanza Divina",             lambda m, s: menu_gobernanza(m, s)),
    ("9",  "Arquitectura Económica",        lambda m, s: menu_economia(m, s)),
    ("10", "Decreto Individual",            lambda m, s: menu_decreto_individual(m, s)),
    ("s",  "Control de Simulación",         lambda m, s: menu_simulacion(m, [False], s)),
    ("a",  "Seleccionar Agente",            lambda m, s: menu_seleccionar_agente(m, s)),
]


def print_header_bar(modelo, selected_agent):
    print(title("╔══════════════════════════════════════════════════════════╗"))
    print(title("║          MUNDO IA — Panel del Arquitecto CLI            ║"))
    print(title("╚══════════════════════════════════════════════════════════╝"))
    if modelo:
        paso = modelo.paso_actual
        n    = len(modelo.agentes)
        print(f"  {dim('Paso:')} {paso}  {dim('Agentes:')} {n}  {dim('Clima:')} {getattr(modelo,'weather','-')}")
    if selected_agent[0]:
        print(f"  {dim('Agente seleccionado:')} {C.YELLOW}{selected_agent[0]}{C.RESET}")
    print(sep())


def main_loop(modelo: ModeloRelacional):
    selected_agent = [None]  # mutable ref
    while True:
        clear()
        print_header_bar(modelo, selected_agent)
        for key, label, _ in MENU:
            print(f"  {C.BOLD}{key:>2}{C.RESET}  {label}")
        print(f"  {C.BOLD} q{C.RESET}  Salir")
        print(sep())

        op = prompt("Opción").lower()

        if op == "q":
            print(info("Saliendo..."))
            break

        handler = next((fn for k, _, fn in MENU if k == op), None)
        if handler:
            try:
                handler(modelo, selected_agent)
            except KeyboardInterrupt:
                pass
            input(f"\n{dim('Presiona Enter para continuar...')}")
        else:
            print(warn(f"Opción desconocida: '{op}'"))
            time.sleep(0.7)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MUNDO IA — CLI del Arquitecto")
    parser.add_argument("--agents", type=int, default=0,
                        help="Agentes iniciales a crear (default: 0 — mundo vacío)")
    parser.add_argument("--user", default="cli-arquitecto",
                        help="User ID para persistencia (default: cli-arquitecto)")
    args = parser.parse_args()

    print(info("Inicializando mundo..."))

    def cli_log(mensaje, categoria="sistema", *a, **kw):
        pass  # Los logs se ven en el historial, no en tiempo real para no romper la TUI

    modelo = ModeloRelacional(
        num_agentes=0,
        log_callback=cli_log,
        user_id=args.user,
        start_empty=True,
    )

    # Generar mapa
    if not modelo.mapa or len(modelo.mapa) == 0:
        modelo.generar_mapa()
    print(ok("Mapa generado"))

    # Spawn inicial si se pidió
    if args.agents > 0:
        for _ in range(args.agents):
            modelo.spawn_agent()
        print(ok(f"{args.agents} agente(s) creado(s)"))

    print(ok("Mundo listo\n"))
    time.sleep(0.5)

    try:
        main_loop(modelo)
    except KeyboardInterrupt:
        print(f"\n{info('Sesión terminada.')}")


if __name__ == "__main__":
    main()
