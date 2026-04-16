import random
import math
import logging
from typing import List, Dict, Any, Optional
from core.utils import synchronized, logger, Json
from systems.memoria import MemoriaGrafica
from agents.cerebro_langgraph import CerebroAvanzado
from agents.alma import generar_alma_inicial
from agents.identity_system import generar_identidad_inicial
from agents.bdi_components import (
    SistemaCreencias,
    SistemaDeseos,
    SistemaIntenciones,
    TipoDeseo,
    TipoAccion
)

class Agente:
    """
    Entidad central de la simulación MundoIA. 
    Representa un ciudadano autónomo con profundidad psicológica, social y cognitiva.
    """
    
    def __init__(
        self,
        unique_id,
        modelo,
        recursos=100,
        necesidades=None,
        personalidad=None,
        civ_id=None,
        x=None,
        y=None,
    ):
        self.unique_id = unique_id
        self.modelo = modelo
        self.recursos = recursos
        self.civilizacion_id = civ_id
        self.objetivo_movimiento = None

        # Posicionamiento inicial robusto
        if x is not None and y is not None:
            self.x, self.y = x, y
        else:
            self._spawn_en_posicion_valida()

        # Atributos Psicológicos (OCEAN-like)
        self.personalidad = personalidad or {
            "extroversión": random.random(),
            "amabilidad": random.random(),
            "competitividad": random.random(),
            "curiosidad": random.random(),
            "lealtad": random.random(),
            "prudencia": random.random(),
            "hostilidad": random.random(),
        }

        # Estado Vital (10.0 = Óptimo, 0.0 = Crítico)
        self.necesidades = necesidades or {
            "alimento": 10.0,
            "social": 10.0,
            "seguridad": 10.0,
            "descanso": 10.0,
            "entretenimiento": 10.0,
            "salud": 10.0,
        }

        self.necesidades_intelectuales = {
            "curiosidad": random.uniform(6, 9),
            "expresion": random.uniform(6, 9),
            "debate": random.uniform(5, 8),
            "aprendizaje": random.uniform(6, 9),
        }

        # Capital Social y Redes Sociales (OASIS Integration)
        self.capital_social = 10.0
        self.seguidores = 0
        self.siguiendo = 0
        self.posts_publicados = 0
        self.comentarios_realizados = 0
        self.likes_recibidos = 0
        self.likes_dados = 0
        self.debates_ganados = 0
        self.debates_perdidos = 0
        self.intereses = []
        self.opiniones_fuertes = {}

        # Sistema de Habilidades
        self.skill_factor = random.uniform(0.1, 0.5)
        self.experiencia = {
            "medicina": 0, "comercio": 0, "combate": 0, "exploracion": 0,
            "social": 0, "ingenieria": 0, "agricultura": 0, "investigacion": 0, "ciencia": 0
        }
        self.skills = {}

        # Subsistemas de Inteligencia y Memoria
        self.memoria = MemoriaGrafica(self.unique_id)
        self.cerebro = CerebroAvanzado(self.unique_id)
        self.creencias = SistemaCreencias()
        self.deseos = SistemaDeseos()
        self.intenciones = SistemaIntenciones()
        
        # Identidad y Alma
        self.alma = generar_alma_inicial(self.personalidad, 0)
        self.identidad = generar_identidad_inicial(self.alma.arquetipo.value, 0)
        if self.alma.nombre_propio:
            self.identidad.nombre = self.alma.nombre_propio

        # Economía y Estatus
        self.grupo_id = civ_id
        self.rol = "Ciudadano"
        self.dinero = 100.0
        self.rango = 1.0
        self.reputacion = 1.0
        self.inventario = {
            "comida": int(self.recursos), "madera": 0, "piedra": 0,
            "hierro": 0, "medicina": 0, "ocio": 0
        }
        self.alianzas = []
        self.tratados = []
        self.hitos = []
        self.historial_etico = []
        self.esta_vivo = True
        self.apps = {}
        self.pensamiento_actual = "Iniciando existencia..."
        self.ultimo_mensaje_recibido = None
        self.gasto_turno = 0.0
        self.inversiones = []

    @property
    def display_name(self):
        if hasattr(self, "identidad") and self.identidad:
            nombre = getattr(self.identidad, "nombre", None)
            emoji = getattr(self.identidad, "emoji", "")
            if nombre:
                return f"{emoji} {nombre}".strip()
        return str(self.unique_id)

    def _spawn_en_posicion_valida(self):
        mapa_size = getattr(self.modelo, "mapa_size", 20)
        for _ in range(100):
            nx, ny = random.randint(0, mapa_size-1), random.randint(0, mapa_size-1)
            if not any(a.x == nx and a.y == ny for a in self.modelo.agentes):
                self.x, self.y = nx, ny
                return
        self.x, self.y = random.randint(0, mapa_size-1), random.randint(0, mapa_size-1)

    @synchronized
    def decir(self, mensaje, pensamiento=None, privado_para=None, para_grupo=False, global_broadcast=False):
        """Comunicación multicanal con registro histórico."""
        prefijo_emisor = f"[{self.unique_id}]"
        prefix_tags = ""
        if global_broadcast:
            prefix_tags = " 📢 (GLOBAL)"
        elif para_grupo and self.grupo_id:
            prefix_tags = f" 👥 (Facción {self.grupo_id})"
            privado_para = f"GRUPO:{self.grupo_id}"
        elif privado_para:
            prefix_tags = " 🔒 (Privado)"

        prefijo = f"{prefijo_emisor}{prefix_tags}"

        if pensamiento: self.pensamiento_actual = pensamiento

        self.modelo.log(
            f'{prefijo}: "{mensaje}"',
            categoria="dialogo",
            tts_text=mensaje,
            pensamiento=pensamiento,
            privado_para=privado_para,
            agente_id=self.unique_id,
        )

        self.memoria.registrar_mensaje(self.unique_id, mensaje)
        self._difundir(mensaje, privado_para, para_grupo, global_broadcast)

    def _difundir(self, mensaje, privado_para, para_grupo, global_broadcast):
        packet = {"emisor": self.unique_id, "contenido": mensaje, "tipo": "DIRECTO"}
        if global_broadcast:
            packet["tipo"] = "GLOBAL"
            for agent in self.modelo.agentes:
                if agent != self: self._entregar(agent, packet)
        elif para_grupo:
            for agent in self.modelo.agentes:
                if agent.grupo_id == self.grupo_id and agent != self:
                    self._entregar(agent, packet)
        elif privado_para:
            dest = self.modelo.get_agent_by_id(privado_para)
            if dest: self._entregar(dest, packet)
        else: # Proximidad (Asamblea local)
            for agent in self.modelo.agentes:
                if agent != self and (abs(self.x - agent.x) + abs(self.y - agent.y)) <= 3:
                    self._entregar(agent, packet)

    def _entregar(self, receptor, packet):
        receptor.ultimo_mensaje_recibido = packet
        receptor.memoria.registrar_mensaje(self.unique_id, packet["contenido"])

    @synchronized
    def interactuar(self, otro, tipo="social", mensaje=None):
        """Interacción profesional: Basada en afinidad, ética y estatus."""
        if mensaje: self._entregar(otro, {"emisor": self.unique_id, "contenido": mensaje})

        if tipo in ["social", "SOCIALIZAR"]:
            self._ejecutar_socializacion(otro)
        elif tipo == "COMPETIR":
            self._ejecutar_competencia(otro)
        elif tipo == "COMERCIAR":
            self._ejecutar_comercio(otro)
        elif tipo == "ATACAR":
            self._ejecutar_ataque(otro)

    def _ejecutar_socializacion(self, otro):
        self.necesidades["social"] = min(10.0, self.necesidades["social"] + 2.0)
        self.ganar_experiencia("social", 1)
        
        # Inteligencia Social: La afinidad no es azar, es compatibilidad de personalidades
        compatibilidad = 1.0 - abs(self.personalidad["amabilidad"] - otro.personalidad["amabilidad"])
        hostilidad_mutua = (self.personalidad["hostilidad"] + otro.personalidad["hostilidad"]) / 2
        afinidad = (compatibilidad * 0.7) - (hostilidad_mutua * 0.4)
        
        self.memoria.registrar_interaccion(otro.unique_id, "amigo" if afinidad > 0.3 else "conocido", afinidad, otro.recursos, otro.grupo_id)
        self.modelo.log(
            f"🤝 [SOCIAL] {self.display_name} y {otro.display_name} interactúan. Afinidad: {afinidad:.2f}",
            categoria="social",
        )

    def _ejecutar_ataque(self, otro):
        self.ganar_experiencia("combate", 2)
        self.reputacion = max(0.0, self.reputacion - 0.15)
        
        fuerza_ataque = (self.experiencia["combate"] * 0.5) + (self.personalidad["competitividad"] * 2)
        defensa_otro = (otro.experiencia["combate"] * 0.3) + (otro.personalidad["prudencia"] * 2)
        
        daño = max(0.5, fuerza_ataque - defensa_otro)
        if random.random() < 0.8: # 80% Precisión base
            self.modelo.log(
                f"⚔️ [ATAQUE] {self.display_name} inflige {daño:.1f} de daño a {otro.display_name}",
                categoria="conflict",
            )
            otro.recibir_daño(daño, f"violencia de {self.display_name}")
        else:
            self.modelo.log(
                f"🛡️ [DEFENSA] {otro.display_name} bloqueó el ataque de {self.display_name}",
                categoria="conflict",
            )

    @synchronized
    def explorar(self):
        """Producción: Búsqueda heurística de recursos basada en biomas y habilidad."""
        if self.necesidades["descanso"] < 3.0: return False, "Demasiado cansado"
        
        self.necesidades["descanso"] -= 1.5
        self.ganar_experiencia("exploracion", 2)
        
        tile = self.modelo.mapa[self.x][self.y]
        habilidad_exploracion = self.experiencia["exploracion"] / 10.0
        
        # Lógica de hallazgo basada en el nodo real del terreno
        if tile.resource_node and tile.resource_node["amount"] > 0:
            encontrado = tile.resource_node["type"]
            cantidad = min(tile.resource_node["amount"], random.randint(2, 6) + int(habilidad_exploracion * 10))
            self.inventario[encontrado if encontrado in self.inventario else "comida"] += cantidad
            tile.resource_node["amount"] -= cantidad
            self.modelo.log(
                f"🔍 [EXPLORACION] {self.display_name} extrajo {cantidad} de {encontrado} en {tile.terrain_type}",
                categoria="recursos",
            )
            return True, f"Encontraste {cantidad} {encontrado}"
        
        return True, "Zona sin recursos explotables"

    @synchronized
    def step(self):
        """Ciclo de vida principal del agente."""
        if not self.esta_vivo: return
        
        self._actualizar_metabolismo()
        self._procesar_necesidades_criticas()
        
        # BDI System integrado
        if hasattr(self, "tick_bdi"):
            self.tick_bdi()
            
        # OASIS Social Pulse — publicar cada turno del agente
        self._ejecutar_accion_social_automatica(self.modelo.paso_actual)

    def _actualizar_metabolismo(self):
        # Degradación balanceada
        self.necesidades["alimento"] = max(0, self.necesidades["alimento"] - 0.12)
        self.necesidades["descanso"] = max(0, self.necesidades["descanso"] - 0.08)
        self.necesidades["social"] = max(0, self.necesidades["social"] - 0.05)
        
        # El metabolismo consume comida si tiene hambre
        if self.necesidades["alimento"] < 5.0 and self.inventario["comida"] > 0:
            self.necesidades["alimento"] = min(10.0, self.necesidades["alimento"] + 4.0)
            self.inventario["comida"] -= 1

    def _procesar_necesidades_criticas(self):
        if self.necesidades["alimento"] <= 0:
            self.recibir_daño(0.8, "inanición prolongada")
        if self.necesidades["salud"] <= 0:
            self.morir("insuficiencia vital")

    @synchronized
    def recibir_daño(self, cantidad, motivo):
        self.necesidades["salud"] = max(0, self.necesidades["salud"] - cantidad)
        self.modelo.log(
            f"🩸 [DAÑO] {self.display_name} recibió {cantidad:.1f} por {motivo}. Salud: {self.necesidades['salud']:.1f}",
            categoria="salud",
        )
        if self.necesidades["salud"] <= 0: self.morir(motivo)

    def morir(self, motivo):
        if not self.esta_vivo: return
        self.esta_vivo = False
        self.modelo.log(
            f"🪦 [FUNERAL] El agente {self.display_name} ha fallecido. Causa: {motivo}",
            categoria="sistema",
        )
        if self in self.modelo.agentes: self.modelo.agentes.remove(self)
        self.modelo.notificar_cambio_estado()

    def ganar_experiencia(self, area, puntos=1):
        if area in self.experiencia:
            self.experiencia[area] += puntos
            if self.experiencia[area] >= 100: self.experiencia[area] = 100

    def to_dict(self):
        """Serialización de producción."""
        return {
            "unique_id": self.unique_id,
            "x": self.x, "y": self.y,
            "recursos": self.recursos,
            "necesidades": self.necesidades,
            "personalidad": self.personalidad,
            "dinero": self.dinero,
            "inventario": self.inventario,
            "experiencia": self.experiencia,
            "esta_vivo": self.esta_vivo,
            "rango": self.rango,
            "grupo_id": self.grupo_id,
            "capital_social": self.capital_social
        }

    @classmethod
    def from_dict(cls, data, modelo):
        obj = cls(unique_id=data["unique_id"], modelo=modelo)
        for k, v in data.items(): setattr(obj, k, v)
        return obj

    # --- Integración OASIS Social (Producción) ---
    def _ejecutar_accion_social_automatica(self, paso):
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys: return
        
        # Generar post basado en estado actual
        tipo = "observacion"
        if self.necesidades["alimento"] < 4: tipo = "hungry"
        
        from agents.cerebro_llm import cerebro_llm
        contenido = cerebro_llm.generar_post_social(self, f"Tipo de post: {tipo}. Paso: {paso}")
        
        if contenido:
            self.social_create_post(contenido, tipo, ["realidad", "supervivencia"])

    def social_create_post(
        self, contenido: str, tipo: str = "opinion", temas: List[str] = None
    ) -> bool:
        """El agente crea un post en la red social."""
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return False

        post = recsys.crear_post(self.modelo.user_id, self.unique_id, contenido, tipo, temas)
        # Sincronizar timestamp con el paso actual del modelo
        post.timestamp = getattr(self.modelo, "paso_actual", 0)

        self.posts_publicados += 1
        # Publicar satisface la necesidad de expresión (baja el hambre de expresión)
        if "expresion" in self.necesidades_intelectuales:
            self.necesidades_intelectuales["expresion"] = max(
                0.0, self.necesidades_intelectuales["expresion"] - 2.0
            )

        self.capital_social = self.calcular_capital_social()

        # Notificar cambio de estado para actualizar UI
        if hasattr(self.modelo, "notificar_cambio_estado"):
            self.modelo.notificar_cambio_estado()

        return True

    def _evaluar_tipo_accion_necesidades(self):
        """Heurística ligera para decidir tipo de acción prioritaria según necesidades."""
        try:
            if self.necesidades.get("alimento", 10.0) < 4.0 or self.necesidades.get("salud", 10.0) < 4.0:
                return "SURVIVAL"
            if self.necesidades.get("social", 10.0) < 4.0:
                return "SOCIAL_REQUIRED"
            # Priorizar curiosidad / aprendizaje cuando estén muy altos
            cur = self.necesidades_intelectuales.get("curiosidad", 0)
            apr = self.necesidades_intelectuales.get("aprendizaje", 0)
            if max(cur, apr) >= 7.0:
                return "INTELLECTUAL"
        except Exception:
            pass
        return "FREE_CHOICE"

    def social_force_action(self, paso):
        """Forzar al menos una acción social por turno: post / like / comment / follow.

        Intenta en este orden razonable: crear post (si hay necesidad de expresión o pocos posts),
        likear un post aleatorio, comentar, o seguir a alguien. Si falla, cae al comportamiento
        automático existente.
        """
        recsys = getattr(self.modelo, "social_recsys", None)
        if not recsys:
            return self._ejecutar_accion_social_automatica(paso)

        try:
            # Preferir crear post si tiene alto hambre de expresión o aún no ha posteado
            expr_hunger = self.necesidades_intelectuales.get("expresion", 0)
            if expr_hunger > 6 or self.posts_publicados < 1:
                try:
                    from agents.cerebro_llm import cerebro_llm
                    contenido = cerebro_llm.generar_post_social(self, f"Post forzado. Paso: {paso}")
                except Exception:
                    contenido = None
                if contenido:
                    return self.social_create_post(contenido, "forzado", ["expresion"]) 

            # Obtener feed y elegir una interacción simple
            feed = recsys.get_feed_hibrido(self, paso, limite=20)
            posts = []
            if isinstance(feed, dict):
                posts = feed.get("all_posts", []) or []
            elif isinstance(feed, list):
                posts = feed

            if posts:
                # Intentar like en un post aleatorio
                target = random.choice(posts)
                post_id = getattr(target, "id", None)
                if post_id:
                    exito = recsys.likear_post(post_id, self.unique_id)
                    if exito:
                        self.likes_dados = getattr(self, "likes_dados", 0) + 1
                        return True

            # Intentar comentar el primer post
            if posts:
                first = posts[0]
                post_id = getattr(first, "id", None)
                if post_id:
                    comentario = recsys.agregar_comentario(post_id, self.unique_id, "Interesante.")
                    if comentario:
                        self.comentarios_realizados = getattr(self, "comentarios_realizados", 0) + 1
                        return True

            # Intentar seguir a un autor aleatorio
            authors = [getattr(p, "autor_id", None) for p in posts if getattr(p, "autor_id", None) != self.unique_id]
            authors = [a for a in authors if a]
            if authors:
                objetivo = random.choice(authors)
                recsys.follow(self.unique_id, objetivo)
                self.siguiendo = getattr(self, "siguiendo", 0) + 1
                return True

        except Exception as e:
            try:
                self.modelo.log(f"⚠️ Error en social_force_action de {self.unique_id}: {e}", categoria="sistema")
            except Exception:
                pass

        # Fallback al comportamiento automático existente si todo lo demás falla
        return self._ejecutar_accion_social_automatica(paso)
