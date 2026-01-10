import networkx as nx

class MemoriaGrafica:
    def __init__(self, owner_id):
        self.owner_id = owner_id
        # El grafo mental del agente
        self.grafo = nx.DiGraph()
        # Añadirse a sí mismo como nodo central
        self.grafo.add_node(owner_id, tipo="yo", recursos_vistos=None)

    def registrar_interaccion(self, otro_id, tipo_relacion, fuerza_cambio, recursos_vistos=None, grupo_visto=None):
        """Actualiza el conocimiento sobre otro agente y la relación con él."""
        
        # 1. Actualizar o crear el nodo del otro agente
        if not self.grafo.has_node(otro_id):
            self.grafo.add_node(otro_id, tipo="conocido", recursos_vistos=recursos_vistos, grupo=grupo_visto)
        else:
            # Actualizar información si es más reciente
            if recursos_vistos is not None:
                self.grafo.nodes[otro_id]['recursos_vistos'] = recursos_vistos
            if grupo_visto is not None:
                self.grafo.nodes[otro_id]['grupo'] = grupo_visto

        # 2. Actualizar la relación (arista)
        if not self.grafo.has_edge(self.owner_id, otro_id):
            self.grafo.add_edge(self.owner_id, otro_id, fuerza=0.0, tipo=tipo_relacion)
        
        # Modificar la fuerza de la relación
        self.grafo[self.owner_id][otro_id]['fuerza'] += fuerza_cambio
        self.grafo[self.owner_id][otro_id]['tipo'] = tipo_relacion

    def obtener_fuerza(self, otro_id):
        """Retorna la fuerza de la relación con un agente."""
        if self.grafo.has_edge(self.owner_id, otro_id):
            return self.grafo[self.owner_id][otro_id]['fuerza']
        return 0.0

    def obtener_tipo(self, otro_id):
        """Retorna el tipo de relación (amigo, enemigo, conocido)."""
        if self.grafo.has_edge(self.owner_id, otro_id):
            return self.grafo[self.owner_id][otro_id]['tipo']
        return "desconocido"

    def sugerir_interaccion(self, lista_agentes_ids):
        """
        Lógica de inferencia: Sugiere interactuar con alguien basado en el grafo.
        Prioriza amigos o 'amigos de amigos'.
        """
        # Por ahora, una lógica simple: buscar al mejor amigo en el grafo
        mejores_amigos = [n for n in self.grafo.neighbors(self.owner_id) 
                          if self.grafo[self.owner_id][n]['tipo'] == "amigo"]
        
        if mejores_amigos:
            return mejores_amigos[0] # Retorna el primero por simplicidad
        return None

    def imprimir_grafo_terminal(self):
        """Muestra una representación visual del grafo mental en la terminal."""
        print(f"\n    🧠 MAPA MENTAL DEL AGENTE {self.owner_id}")
        print("    " + "━" * 40)
        
        # Agrupar por tipo de relación
        relaciones = {"amigo": [], "enemigo": [], "conocido": []}
        for n in self.grafo.neighbors(self.owner_id):
            tipo = self.grafo[self.owner_id][n]['tipo']
            fuerza = self.grafo[self.owner_id][n]['fuerza']
            info = self.grafo.nodes[n]
            relaciones[tipo].append((n, fuerza, info))

        for tipo, lista in relaciones.items():
            if not lista: continue
            
            icono = "🟢" if tipo == "amigo" else "🔴" if tipo == "enemigo" else "⚪"
            print(f"    {icono} {tipo.upper()}S:")
            for n, f, info in lista:
                grupo = f" [Grupo: {info['grupo']}]" if info.get('grupo') else ""
                print(f"      ┗━▶ Agente {n} (Fuerza: {f:+.1f}){grupo}")
        
        print("    " + "━" * 40)

    def __str__(self):
        return f"Memoria de {self.owner_id}: {self.grafo.number_of_nodes()} conocidos, {self.grafo.number_of_edges()} relaciones."
