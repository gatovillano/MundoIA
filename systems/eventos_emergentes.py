"""
Sistema de Eventos Emergentes para MundoIA.

Monitoriza el estado físico del mundo (recursos hídricos, densidad poblacional,
saberes ancestrales) y dispara eventos narrativos verificables que los agentes
pueden referenciar en sus posts sin necesidad de inventarlos.
"""

import random
from typing import TYPE_CHECKING, List, Dict, Optional

if TYPE_CHECKING:
    from core.modelo import ModeloRelacional


# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE UMBRALES
# ─────────────────────────────────────────────────────────────
UMBRAL_SEQUIA_AGUA = 8          # tiles de agua necesarios por agente antes de crisis
UMBRAL_DENSIDAD_CONFLICTO = 4   # agentes en la misma región para tensión social
UMBRAL_RECURSOS_ESCASEZ = 3     # recursos promedio por agente para escasez global
INTERVALO_MIN_MISMO_EVENTO = 30 # pasos mínimos entre dos eventos del mismo tipo/región

# Tipos de saberes que pueden descubrirse en ruinas
TIPOS_SABER = [
    "Fragmento de Cartografía Antigua",
    "Recetario Medicinal Primordial",
    "Código de Leyes Tribales",
    "Mapa de Acuíferos Subterráneos",
    "Tratado de Metalurgia Olvidada",
    "Himno de las Estaciones",
    "Crónica de la Primera Migración",
    "Manual de Cultivo Perdido",
]

IMPACTO_SABER = {
    "Fragmento de Cartografía Antigua": {"exploracion": 5},
    "Recetario Medicinal Primordial":   {"medicina": 5, "salud_bonus": 1.0},
    "Código de Leyes Tribales":         {"reputacion": 0.05},
    "Mapa de Acuíferos Subterráneos":   {"agua_bonus": True},
    "Tratado de Metalurgia Olvidada":   {"ingenieria": 5},
    "Himno de las Estaciones":          {"social_bonus": 1.0},
    "Crónica de la Primera Migración":  {"exploracion": 3, "reputacion": 0.03},
    "Manual de Cultivo Perdido":        {"alimento_bonus": 2.0},
}


# ─────────────────────────────────────────────────────────────
# CLASE EVENTO EMERGENTE
# ─────────────────────────────────────────────────────────────
class EventoEmergente:
    """Representa un evento narrativo verificable dentro de la simulación."""

    def __init__(
        self,
        tipo: str,
        region: str,
        descripcion: str,
        paso_inicio: int,
        duracion: int = 10,
        coordenadas: Optional[tuple] = None,
        impacto: Optional[Dict] = None,
        agentes_afectados: Optional[List[str]] = None,
    ):
        self.tipo = tipo
        self.region = region
        self.descripcion = descripcion
        self.paso_inicio = paso_inicio
        self.duracion = duracion
        self.coordenadas = coordenadas or (0, 0)
        self.impacto = impacto or {}
        self.agentes_afectados = agentes_afectados or []
        self.activo = True
        self.resuelto = False

    @property
    def paso_fin(self) -> int:
        return self.paso_inicio + self.duracion

    def __repr__(self):
        return f"<Evento {self.tipo} en {self.region} (paso {self.paso_inicio})>"


# ─────────────────────────────────────────────────────────────
# SISTEMA PRINCIPAL
# ─────────────────────────────────────────────────────────────
class SistemaEventosEmergentes:
    """
    Motor de eventos emergentes.

    Se conecta al ModeloRelacional y en cada turno:
      1. Actualiza los atributos dinámicos del mapa (hidratación, lore).
      2. Evalúa condiciones críticas y dispara eventos.
      3. Notifica a los agentes afectados mediante registrar_evento().
      4. Registra los eventos en las Crónicas globales.
    """

    def __init__(self, modelo: "ModeloRelacional"):
        self.modelo = modelo
        self.eventos_activos: List[EventoEmergente] = []
        self.historial: List[EventoEmergente] = []
        # Registro de último paso en que ocurrió cada (tipo, region) — anti-spam
        self._ultimo_evento: Dict[str, int] = {}

    # ──────────────────────────────────────────────────────────
    # API PÚBLICA
    # ──────────────────────────────────────────────────────────
    def procesar_turno(self):
        """Punto de entrada principal. Llamar una vez por turno del modelo."""
        paso = self.modelo.paso_actual

        # 1. Actualizar atributos dinámicos del mapa
        self._actualizar_hidratacion()

        # 2. Caducar eventos viejos
        self._caducar_eventos(paso)

        # 3. Evaluar y disparar nuevos eventos
        self._evaluar_sequia(paso)
        self._evaluar_escasez_recursos(paso)
        self._evaluar_tension_poblacional(paso)
        self._evaluar_descubrimiento_saber(paso)
        self._evaluar_plaga(paso)
        self._evaluar_migracion(paso)

    def get_eventos_activos_para_contexto(self) -> str:
        """Devuelve un resumen de texto de los eventos activos para inyectar en el LLM."""
        if not self.eventos_activos:
            return ""
        lines = ["=== EVENTOS ACTIVOS EN EL MUNDO ==="]
        for ev in self.eventos_activos:
            lines.append(f"- [{ev.tipo}] {ev.descripcion} (Región: {ev.region})")
        lines.append("====================================")
        return "\n".join(lines)

    def get_eventos_en_region(self, region: str) -> List[EventoEmergente]:
        return [e for e in self.eventos_activos if e.region == region]

    # ──────────────────────────────────────────────────────────
    # ACTUALIZACIÓN DEL MAPA
    # ──────────────────────────────────────────────────────────
    def _actualizar_hidratacion(self):
        """
        Degrada la hidratación de casillas no-agua según el clima y el uso.
        Añade atributo `hidratacion` (0–100) a cada WorldTile si no existe.
        """
        modelo = self.modelo
        clima = getattr(modelo, "weather", "sunny")
        degradacion_base = {"sunny": 0.3, "heatwave": 0.8, "storm": -0.5, "rainy": -0.4, "foggy": 0.1}.get(
            str(clima), 0.2
        )

        for row in modelo.mapa:
            for tile in row:
                # Inicializar si no existe
                if not hasattr(tile, "hidratacion"):
                    tile.hidratacion = 70.0 + random.uniform(-10, 10)

                terrain_str = tile.terrain.value if hasattr(tile.terrain, "value") else str(tile.terrain)

                if terrain_str == "water":
                    tile.hidratacion = min(100.0, tile.hidratacion + 2.0)
                    continue

                # Degradar por clima
                tile.hidratacion = max(0.0, tile.hidratacion - degradacion_base)

                # Regenerar si hay agentes con agua cerca
                if tile.resource_node and tile.resource_node.get("type") in ["agua", "water"]:
                    tile.hidratacion = min(100.0, tile.hidratacion + 1.0)

                # Degradar por presión de uso (agentes en la casilla)
                agentes_aqui = sum(1 for a in modelo.agentes if a.x == tile.x and a.y == tile.y and a.esta_vivo)
                if agentes_aqui > 0:
                    tile.hidratacion = max(0.0, tile.hidratacion - agentes_aqui * 0.5)

        # Añadir hidratación inicial a los datos del tile para el to_dict si aún no está
        # (Se refleja automáticamente al ser un atributo en memoria)

    # ──────────────────────────────────────────────────────────
    # EVALUADORES DE EVENTOS
    # ──────────────────────────────────────────────────────────
    def _puede_disparar(self, tipo: str, region: str, paso: int) -> bool:
        """Evita el spam de eventos del mismo tipo en la misma región."""
        clave = f"{tipo}:{region}"
        ultimo = self._ultimo_evento.get(clave, -999)
        return (paso - ultimo) >= INTERVALO_MIN_MISMO_EVENTO

    def _registrar_disparo(self, tipo: str, region: str, paso: int):
        self._ultimo_evento[f"{tipo}:{region}"] = paso

    # ── SEQUÍA ────────────────────────────────────────────────
    def _evaluar_sequia(self, paso: int):
        modelo = self.modelo
        agentes_vivos = [a for a in modelo.agentes if a.esta_vivo]
        if not agentes_vivos:
            return

        # Agrupar por región y calcular hidratación promedio
        from core.world_system import TerrainType
        regiones_hidratacion: Dict[str, List[float]] = {}
        regiones_agentes: Dict[str, List] = {}

        for agente in agentes_vivos:
            region = modelo.world.get_region_name(agente.x, agente.y)
            tile = modelo.mapa[agente.x][agente.y]
            hid = getattr(tile, "hidratacion", 70.0)
            regiones_hidratacion.setdefault(region, []).append(hid)
            regiones_agentes.setdefault(region, []).append(agente)

        for region, hidrataciones in regiones_hidratacion.items():
            promedio = sum(hidrataciones) / len(hidrataciones)
            if promedio < 25.0 and self._puede_disparar("SEQUIA", region, paso):
                afectados = regiones_agentes[region]
                desc = (
                    f"Sequía crítica en {region}: el nivel hídrico ha caído a {promedio:.0f}%. "
                    f"Los pozos se agotan y el agua escasea para todos los que viven aquí."
                )
                evento = EventoEmergente(
                    tipo="SEQUIA",
                    region=region,
                    descripcion=desc,
                    paso_inicio=paso,
                    duracion=20,
                    impacto={"hidratacion_penalty": -5.0, "alimento_penalty": -1.0},
                    agentes_afectados=[a.unique_id for a in afectados],
                )
                self._disparar_evento(evento, afectados, paso)

    # ── ESCASEZ GLOBAL ─────────────────────────────────────────
    def _evaluar_escasez_recursos(self, paso: int):
        modelo = self.modelo
        agentes_vivos = [a for a in modelo.agentes if a.esta_vivo]
        if not agentes_vivos:
            return

        promedio_recursos = sum(a.recursos for a in agentes_vivos) / len(agentes_vivos)
        if promedio_recursos < UMBRAL_RECURSOS_ESCASEZ:
            region = "el mundo entero"
            if self._puede_disparar("ESCASEZ_GLOBAL", region, paso):
                desc = (
                    f"Escasez global de recursos: el promedio por habitante ha caído a "
                    f"{promedio_recursos:.1f} unidades. La hambruna amenaza a la población."
                )
                evento = EventoEmergente(
                    tipo="ESCASEZ_GLOBAL",
                    region=region,
                    descripcion=desc,
                    paso_inicio=paso,
                    duracion=15,
                    impacto={"alimento_penalty": -0.5},
                    agentes_afectados=[a.unique_id for a in agentes_vivos],
                )
                self._disparar_evento(evento, agentes_vivos, paso)

    # ── TENSIÓN POBLACIONAL ────────────────────────────────────
    def _evaluar_tension_poblacional(self, paso: int):
        modelo = self.modelo
        # Contar agentes por región
        from collections import defaultdict
        conteo: Dict[str, List] = defaultdict(list)
        for a in modelo.agentes:
            if a.esta_vivo:
                region = modelo.world.get_region_name(a.x, a.y)
                conteo[region].append(a)

        for region, agentes_region in conteo.items():
            if len(agentes_region) >= UMBRAL_DENSIDAD_CONFLICTO:
                if self._puede_disparar("TENSION_TERRITORIAL", region, paso):
                    # Solo disparar si hay agentes de distintas facciones
                    facciones = set(a.grupo_id for a in agentes_region if a.grupo_id)
                    if len(facciones) >= 2:
                        nombres = [a.identidad.nombre or a.unique_id for a in agentes_region[:4]]
                        desc = (
                            f"Tensión territorial en {region}: {len(agentes_region)} habitantes de "
                            f"{len(facciones)} facciones distintas compiten por los mismos recursos. "
                            f"Entre ellos: {', '.join(nombres)}."
                        )
                        evento = EventoEmergente(
                            tipo="TENSION_TERRITORIAL",
                            region=region,
                            descripcion=desc,
                            paso_inicio=paso,
                            duracion=10,
                            impacto={"tension": True},
                            agentes_afectados=[a.unique_id for a in agentes_region],
                        )
                        self._disparar_evento(evento, agentes_region, paso)

    # ── DESCUBRIMIENTO DE SABERES ──────────────────────────────
    def _evaluar_descubrimiento_saber(self, paso: int):
        """
        Cuando un agente pisa un sitio arqueológico aún no descubierto,
        genera un hallazgo narrativo real con impacto mecánico.
        """
        modelo = self.modelo
        for agente in modelo.agentes:
            if not agente.esta_vivo:
                continue
            tile = modelo.mapa[agente.x][agente.y]
            if not getattr(tile, "is_archaeological_site", False):
                continue
            if tile.discovered_by is not None:
                continue  # Ya descubierto

            # ¡Descubrimiento!
            tipo_saber = random.choice(TIPOS_SABER)
            region = modelo.world.get_region_name(agente.x, agente.y)

            if not self._puede_disparar("HALLAZGO_SABER", region, paso):
                continue

            # Marcar tile como descubierto
            tile.discovered_by = agente.unique_id
            tile.discovery_turn = paso

            nombre_agente = agente.identidad.nombre or agente.unique_id
            desc = (
                f"{nombre_agente} ha desenterrado en las ruinas de {region} "
                f"un valioso {tipo_saber}. Este conocimiento ancestral podría cambiar el rumbo de la comunidad."
            )

            # Aplicar impacto mecánico al agente descubridor
            impacto = IMPACTO_SABER.get(tipo_saber, {})
            self._aplicar_impacto_saber(agente, impacto, tipo_saber)

            evento = EventoEmergente(
                tipo="HALLAZGO_SABER",
                region=region,
                descripcion=desc,
                paso_inicio=paso,
                duracion=30,
                coordenadas=(agente.x, agente.y),
                impacto=impacto,
                agentes_afectados=[agente.unique_id],
            )
            self._disparar_evento(evento, [agente], paso)

            # El saber queda registrado en el tile para que otros agentes también lo accedan
            if not hasattr(tile, "saberes_descubiertos"):
                tile.saberes_descubiertos = []
            tile.saberes_descubiertos.append({
                "tipo": tipo_saber,
                "descubierto_por": agente.unique_id,
                "paso": paso,
            })

    def _aplicar_impacto_saber(self, agente, impacto: Dict, tipo_saber: str):
        """Aplica los efectos mecánicos del hallazgo al agente descubridor."""
        for clave, valor in impacto.items():
            try:
                if clave in agente.experiencia:
                    agente.experiencia[clave] = min(100, agente.experiencia.get(clave, 0) + valor)
                elif clave == "salud_bonus":
                    agente.necesidades["salud"] = min(10.0, agente.necesidades.get("salud", 5.0) + valor)
                elif clave == "social_bonus":
                    agente.necesidades["social"] = min(10.0, agente.necesidades.get("social", 5.0) + valor)
                elif clave == "alimento_bonus":
                    agente.necesidades["alimento"] = min(10.0, agente.necesidades.get("alimento", 5.0) + valor)
                elif clave == "reputacion":
                    agente.reputacion = min(1.0, agente.reputacion + valor)
                elif clave == "agua_bonus":
                    # Revelar fuentes de agua cercanas: mejorar hidratación de tiles adyacentes
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            nx, ny = agente.x + dx, agente.y + dy
                            if 0 <= nx < len(self.modelo.mapa) and 0 <= ny < len(self.modelo.mapa[0]):
                                adj_tile = self.modelo.mapa[nx][ny]
                                if hasattr(adj_tile, "hidratacion"):
                                    adj_tile.hidratacion = min(100.0, adj_tile.hidratacion + 20.0)
            except Exception:
                pass

    # ── PLAGA ──────────────────────────────────────────────────
    def _evaluar_plaga(self, paso: int):
        modelo = self.modelo
        # Condición: mucha densidad + baja salud promedio
        agentes_vivos = [a for a in modelo.agentes if a.esta_vivo]
        if not agentes_vivos:
            return

        salud_promedio = sum(a.necesidades.get("salud", 10) for a in agentes_vivos) / len(agentes_vivos)
        if salud_promedio < 4.0 and random.random() < 0.15:
            region = "múltiples regiones"
            if self._puede_disparar("PLAGA", region, paso):
                desc = (
                    f"Una enfermedad se extiende entre la población: la salud promedio ha caído a "
                    f"{salud_promedio:.1f}/10. Los más débiles corren peligro."
                )
                # Penalizar salud de los más débiles
                afectados = sorted(agentes_vivos, key=lambda a: a.necesidades.get("salud", 10))[:max(1, len(agentes_vivos)//3)]
                evento = EventoEmergente(
                    tipo="PLAGA",
                    region=region,
                    descripcion=desc,
                    paso_inicio=paso,
                    duracion=8,
                    impacto={"salud_penalty": -1.5},
                    agentes_afectados=[a.unique_id for a in afectados],
                )
                self._disparar_evento(evento, afectados, paso)

    # ── MIGRACIÓN MASIVA ───────────────────────────────────────
    def _evaluar_migracion(self, paso: int):
        modelo = self.modelo
        # Si una región tiene > 60% de la población, los de otra región migran
        from collections import Counter
        if not modelo.agentes:
            return

        conteo = Counter(
            modelo.world.get_region_name(a.x, a.y)
            for a in modelo.agentes if a.esta_vivo
        )
        total = sum(conteo.values())
        for region, cantidad in conteo.items():
            if cantidad / total > 0.6 and self._puede_disparar("MIGRACION", region, paso):
                desc = (
                    f"Superpoblación detectada en {region}: el {cantidad*100//total}% de la población "
                    f"se concentra aquí. Se esperan migraciones hacia zonas con más recursos."
                )
                afectados = [a for a in modelo.agentes if a.esta_vivo and
                             modelo.world.get_region_name(a.x, a.y) == region]
                evento = EventoEmergente(
                    tipo="MIGRACION",
                    region=region,
                    descripcion=desc,
                    paso_inicio=paso,
                    duracion=5,
                    agentes_afectados=[a.unique_id for a in afectados],
                )
                self._disparar_evento(evento, afectados, paso)

    # ──────────────────────────────────────────────────────────
    # INFRAESTRUCTURA INTERNA
    # ──────────────────────────────────────────────────────────
    def _disparar_evento(self, evento: EventoEmergente, agentes_afectados: list, paso: int):
        """Registra el evento, notifica a agentes y lo escribe en las Crónicas."""
        modelo = self.modelo
        self.eventos_activos.append(evento)
        self._registrar_disparo(evento.tipo, evento.region, paso)

        # Aplicar impacto físico a agentes afectados
        self._aplicar_impacto_fisico(evento, agentes_afectados)

        # Notificar a cada agente para que lo registre en su diario
        for agente in agentes_afectados:
            try:
                agente.registrar_evento(evento.descripcion)
            except Exception:
                pass

        # Log del modelo
        iconos = {
            "SEQUIA": "🏜️",
            "ESCASEZ_GLOBAL": "📉",
            "TENSION_TERRITORIAL": "⚔️",
            "HALLAZGO_SABER": "📜",
            "PLAGA": "🦠",
            "MIGRACION": "🚶",
        }
        icono = iconos.get(evento.tipo, "🌍")
        modelo.log(
            f"{icono} [EVENTO EMERGENTE] {evento.tipo} en {evento.region}: {evento.descripcion}",
            categoria="evento",
        )

        # Registrar en Crónicas globales
        try:
            from systems.cronicas import TipoCronica
            cronicas = getattr(modelo, "cronicas", None)
            if cronicas and hasattr(cronicas, "registrar"):
                cronicas.registrar(
                    tipo=TipoCronica.EVENTO,
                    titulo=f"{evento.tipo} en {evento.region}",
                    contenido=evento.descripcion,
                    turno=paso,
                    entidades_involucradas=evento.agentes_afectados[:5],
                )
        except Exception:
            pass

        # Notificar cambio de estado al frontend
        try:
            modelo.notificar_cambio_estado()
        except Exception:
            pass

    def _aplicar_impacto_fisico(self, evento: EventoEmergente, agentes: list):
        """Aplica penalizaciones/bonificaciones mecánicas a los agentes del evento."""
        impacto = evento.impacto
        for agente in agentes:
            try:
                if "alimento_penalty" in impacto:
                    agente.necesidades["alimento"] = max(
                        0.0, agente.necesidades.get("alimento", 5.0) + impacto["alimento_penalty"]
                    )
                if "salud_penalty" in impacto:
                    agente.necesidades["salud"] = max(
                        0.0, agente.necesidades.get("salud", 5.0) + impacto["salud_penalty"]
                    )
                if "hidratacion_penalty" in impacto:
                    agente.necesidades["alimento"] = max(
                        0.0, agente.necesidades.get("alimento", 5.0) + impacto["hidratacion_penalty"] * 0.1
                    )
            except Exception:
                pass

    def _caducar_eventos(self, paso: int):
        """Mueve eventos terminados al historial."""
        activos = []
        for ev in self.eventos_activos:
            if paso >= ev.paso_fin:
                ev.activo = False
                ev.resuelto = True
                self.historial.append(ev)
            else:
                activos.append(ev)
        self.eventos_activos = activos
