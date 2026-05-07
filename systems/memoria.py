import networkx as nx
from typing import Dict, List, Optional, Any
from systems.conversaciones import gestor_conversaciones


class MemoriaGrafica:
    def __init__(self, owner_id):
        self.owner_id = owner_id
        # El grafo mental del agente
        self.grafo = nx.DiGraph()
        # Historial de mensajes recientes: [{"emisor": id, "mensaje": texto, "timestamp": ms}]
        self.historial_mensajes = []
        # Historial de acciones físicas/lógicas propias: ["ACCION", "ACCION"]
        self.historial_acciones = []
        # Añadirse a sí mismo como nodo central
        self.grafo.add_node(owner_id, tipo="yo", recursos_vistos=None)

    def registrar_interaccion(
        self,
        otro_id,
        tipo_relacion,
        fuerza_cambio,
        recursos_vistos=None,
        grupo_visto=None,
    ):
        """Actualiza el conocimiento sobre otro agente y la relación con él."""
        # --- ROBUSTEZ: Asegurar que otro_id sea el ID string y no el objeto Agente ---
        if not isinstance(otro_id, (str, int)):
            if hasattr(otro_id, "unique_id"):
                otro_id = otro_id.unique_id
            else:
                otro_id = str(otro_id)
        
        otro_id = str(otro_id) # Forzar string para consistencia con DB

        # 1. Actualizar o crear el nodo del otro agente
        if not self.grafo.has_node(otro_id):
            self.grafo.add_node(
                otro_id,
                tipo="conocido",
                recursos_vistos=recursos_vistos,
                grupo=grupo_visto,
            )
        else:
            # Actualizar información si es más reciente
            if recursos_vistos is not None:
                self.grafo.nodes[otro_id]["recursos_vistos"] = recursos_vistos
            if grupo_visto is not None:
                self.grafo.nodes[otro_id]["grupo"] = grupo_visto

        # 2. Actualizar la relación (arista)
        if not self.grafo.has_edge(self.owner_id, otro_id):
            self.grafo.add_edge(self.owner_id, otro_id, fuerza=0.0, tipo="conocido")

        # Modificar la fuerza de la relación
        self.grafo[self.owner_id][otro_id]["fuerza"] += fuerza_cambio
        
        # Determinar el tipo basado en la fuerza acumulada y el tipo sugerido
        fuerza_total = self.grafo[self.owner_id][otro_id]["fuerza"]
        
        # Si el tipo sugerido es enemigo, forzarlo si la fuerza es negativa
        if tipo_relacion == "enemigo":
            self.grafo[self.owner_id][otro_id]["tipo"] = "enemigo"
        else:
            # Lógica dinámica basada en afinidad total
            if fuerza_total > 0.5:
                self.grafo[self.owner_id][otro_id]["tipo"] = "amigo"
            elif fuerza_total < -0.5:
                self.grafo[self.owner_id][otro_id]["tipo"] = "enemigo"
            else:
                self.grafo[self.owner_id][otro_id]["tipo"] = "conocido"

        # También guardar datos de percepción en la arista para facilitar persistencia
        self.grafo[self.owner_id][otro_id]["recursos_vistos"] = recursos_vistos
        self.grafo[self.owner_id][otro_id]["grupo"] = grupo_visto

    def registrar_mensaje(self, emisor_id, contenido):
        """Guarda un mensaje en el historial reciente."""
        self.historial_mensajes.append(
            {
                "emisor": emisor_id,
                "contenido": contenido[:100] + "..."
                if len(contenido) > 100
                else contenido,
            }
        )
        # Limitar a los últimos 5 mensajes para eficiencia de tokens (antes 10)
        if len(self.historial_mensajes) > 5:
            self.historial_mensajes.pop(0)

    def registrar_accion(self, nombre_accion):
        """Guarda una acción realizada en el historial reciente para evitar repeticiones."""
        self.historial_acciones.append(nombre_accion)
        # Limitar a 3 acciones para contexto (antes 5)
        if len(self.historial_acciones) > 3:
            self.historial_acciones.pop(0)

    def obtener_contexto_acciones(self):
        """Retorna una cadena con las últimas acciones realizadas."""
        if not self.historial_acciones:
            return "No has realizado acciones físicas recientemente."
        return f"TUS ÚLTIMAS ACCIONES: {', '.join(self.historial_acciones)}"

    def obtener_contexto_mensajes(self):
        """Retorna una cadena con el historial de mensajes para el prompt."""
        if not self.historial_mensajes:
            return "No hay diálogos previos recientes."

        contexto = "HISTORIAL DE DIÁLOGOS RECIENTES:\n"
        for m in self.historial_mensajes:
            emisor = "Tú" if m["emisor"] == self.owner_id else f"Agente {m['emisor']}"
            contexto += f"- {emisor}: {m['contenido']}\n"
        return contexto

    def obtener_fuerza(self, otro_id):
        """Retorna la fuerza de la relación con un agente."""
        if self.grafo.has_edge(self.owner_id, otro_id):
            return self.grafo[self.owner_id][otro_id]["fuerza"]
        return 0.0

    def obtener_afinidad(self, otro_id: str) -> float:
        """Retorna la afinidad normalizada entre -1.0 y 1.0.
        Equivalente a la fuerza de la relación, pero con clamping."""
        if self.grafo.has_edge(self.owner_id, otro_id):
            fuerza = self.grafo[self.owner_id][otro_id]["fuerza"]
            return max(-1.0, min(1.0, fuerza))  # Clamp a [-1, 1]
        return 0.0

    def obtener_tipo(self, otro_id):
        """Retorna el tipo de relación (amigo, enemigo, conocido)."""
        if self.grafo.has_edge(self.owner_id, otro_id):
            return self.grafo[self.owner_id][otro_id]["tipo"]
        return "desconocido"

    def sugerir_interaccion(self, lista_agentes_ids):
        """
        Lógica de inferencia: Sugiere interactuar con alguien basado en el grafo.
        Prioriza amigos o 'amigos de amigos'.
        """
        # Por ahora, una lógica simple: buscar al mejor amigo en el grafo
        mejores_amigos = [
            n
            for n in self.grafo.neighbors(self.owner_id)
            if self.grafo[self.owner_id][n]["tipo"] == "amigo"
        ]

        if mejores_amigos:
            return mejores_amigos[0]  # Retorna el primero por simplicidad
        return None

    def imprimir_grafo_terminal(self):
        """Muestra una representación visual del grafo mental en la terminal."""
        print(f"\n    🧠 MAPA MENTAL DEL AGENTE {self.owner_id}")
        print("    " + "━" * 40)

        # Agrupar por tipo de relación
        relaciones = {"amigo": [], "enemigo": [], "conocido": []}
        for n in self.grafo.neighbors(self.owner_id):
            tipo = self.grafo[self.owner_id][n]["tipo"]
            fuerza = self.grafo[self.owner_id][n]["fuerza"]
            info = self.grafo.nodes[n]
            relaciones[tipo].append((n, fuerza, info))

        for tipo, lista in relaciones.items():
            if not lista:
                continue

            icono = "🟢" if tipo == "amigo" else "🔴" if tipo == "enemigo" else "⚪"
            print(f"    {icono} {tipo.upper()}S:")
            for n, f, info in lista:
                grupo = f" [Grupo: {info['grupo']}]" if info.get("grupo") else ""
                print(f"      ┗━▶ Agente {n} (Fuerza: {f:+.1f}){grupo}")

        print("    " + "━" * 40)

    def exportar_datos(self):
        """Convierte el grafo en una estructura de datos serializable."""
        return {
            "nodos": [{"id": str(n), "data": self.grafo.nodes[n]} for n in self.grafo.nodes],
            "aristas": [
                {"u": str(u), "v": str(v), "data": self.grafo[u][v]} for u, v in self.grafo.edges
            ],
            "historial_mensajes": self.historial_mensajes,
        }

    def cargar_datos(self, datos):
        """Reconstruye el grafo desde datos serializados."""
        self.grafo.clear()
        # Asegurar que el dueño está en el grafo
        self.grafo.add_node(self.owner_id, tipo="yo", recursos_vistos=None)
        
        for n in datos.get("nodos", []):
            node_id = str(n["id"])
            if not self.grafo.has_node(node_id):
                self.grafo.add_node(node_id, **n["data"])
            else:
                # Si ya existe (ej. el nodo 'yo'), actualizar data
                for k, v in n["data"].items():
                    self.grafo.nodes[node_id][k] = v
                    
        for e in datos.get("aristas", []):
            u_id = str(e["u"])
            v_id = str(e["v"])
            self.grafo.add_edge(u_id, v_id, **e["data"])
        self.historial_mensajes = datos.get("historial_mensajes", [])

    def __str__(self):
        return f"Memoria de {self.owner_id}: {self.grafo.number_of_nodes()} conocidos, {self.grafo.number_of_edges()} relaciones."

    # === MÉTODOS PARA CONVERSACIONES PERSISTENTES ===

    def iniciar_conversacion_con(self, otro_id: str):
        """Inicia o recupera una conversación activa con otro agente."""
        gestor_conversaciones.iniciar_conversacion(self.owner_id, otro_id)

    def agregar_mensaje_a_conversacion(
        self,
        otro_id: str,
        contenido: str,
        turno: int,
        tipo: str = "normal",
        metadata: Dict = None,
    ):
        """
        Agrega un mensaje a la conversación activa con otro agente.
        Se debe llamar cuando se envía o recibe un mensaje en contexto conversacional.
        """
        gestor_conversaciones.agregar_mensaje(
            self.owner_id, otro_id, contenido, turno, tipo, metadata
        )

    def obtener_contexto_conversacion_activa(
        self, otro_id: str, max_mensajes: int = 15
    ) -> str:
        """
        Obtiene el historial completo de la conversación activa con un agente específico.
        Returns: String formateado para el prompt, o cadena vacía si no hay conversación activa.
        """
        return gestor_conversaciones.obtener_contexto_conversacion_activa(
            self.owner_id, otro_id, max_mensajes
        )

    def obtener_sugerencia_conversacion(self, otro_id: str) -> Optional[str]:
        """Sugiere una pregunta para profundizar la conversación con otro agente."""
        return gestor_conversaciones.sugerir_siguiente_paso_conversacion(
            self.owner_id, otro_id
        )

    def cerrar_conversacion_con(self, otro_id: str):
        """Cierra la conversación activa con otro agente."""
        conv = gestor_conversaciones.obtener_conversacion_activa(self.owner_id, otro_id)
        if conv:
            gestor_conversaciones.cerrar_conversacion(conv.id)

    def obtener_conversaciones_activas(self) -> List[str]:
        """Retorna lista de IDs de agentes con los que hay conversación activa."""
        convs = gestor_conversaciones.obtener_conversaciones_agente(
            self.owner_id, solo_activas=True
        )
        interlocutores = []
        for conv in convs:
            otro = conv.obtener_interlocutor(self.owner_id)
            if otro:
                interlocutores.append(otro)
        return interlocutores
