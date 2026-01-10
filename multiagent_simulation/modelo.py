import random
import matplotlib
matplotlib.use('Agg') # Backend para entornos sin interfaz gráfica
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from memoria import MemoriaGrafica
from traductor import traductor
from cerebro_langgraph import CerebroAvanzado
from cerebro_llm import cerebro_llm
from dotenv import load_dotenv
import os

# Cargar configuración
load_dotenv()

class Agente:
    def __init__(self, unique_id, modelo, recursos=100, necesidades=None, personalidad=None):
        self.unique_id = unique_id
        self.modelo = modelo
        self.recursos = recursos
        
        # Necesidades: alimento, seguridad, socialización
        self.necesidades = necesidades if necesidades else {
            "alimento": random.randint(1, 5),
            "seguridad": random.randint(1, 5),
            "social": random.randint(1, 5)
        }
        
        # Personalidad (0.0 a 1.0): extroversión, amabilidad, competitividad
        self.personalidad = personalidad if personalidad else {
            "extroversión": random.random(),
            "amabilidad": random.random(),
            "competitividad": random.random()
        }
        
        # Memoria basada en Grafos
        self.memoria = MemoriaGrafica(self.unique_id)
        
        # Cerebro LangGraph (Solo para agentes de élite 0 y 1)
        self.cerebro_lg = CerebroAvanzado(self.unique_id) if self.unique_id in [0, 1] else None
        
        # Nuevos atributos: Grupo y Jerarquía
        self.grupo_id = None
        self.rango = 1.0 # Estatus social (influye en la influencia)

    def decir(self, mensaje):
        """Imprime un mensaje en el idioma emergente con subtítulos en español."""
        prefijo = f"[{self.unique_id}]"
        if self.personalidad["amabilidad"] > 0.7: prefijo = f"😇 {prefijo}"
        elif self.personalidad["competitividad"] > 0.7: prefijo = f"👿 {prefijo}"
        else: prefijo = f"🤖 {prefijo}"
        
        # Traducir al idioma emergente
        mensaje_alien = traductor.traducir_frase(mensaje)
        
        self.modelo.log(f"{prefijo}: \"{mensaje_alien}\"", categoria="dialogo", subtitulos=mensaje, tts_text=mensaje)

    def generar_dialogo(self, otro, contexto):
        """Genera un pensamiento espontáneo usando LLM (LiteLLM) o lógica interna."""
        
        # Intentamos usar el LLM para una interacción más real
        return cerebro_llm.generar_interaccion(self, otro, contexto)

    def interactuar(self, otro_agente):
        """Define cómo el agente interactúa con otro basado en su personalidad y necesidades."""
        # Lógica de Intercambio de Recursos (Cooperación vs Competencia)
        if self.recursos > 40 and otro_agente.necesidades["alimento"] > 7:
            prob_ayuda = self.personalidad["amabilidad"]
            if random.random() < prob_ayuda:
                cantidad = min(15, self.recursos - 40)
                self.recursos -= cantidad
                otro_agente.recursos += cantidad
                incremento = 0.5 * (1 + self.personalidad["amabilidad"])
                
                # Registrar en memoria
                self.memoria.registrar_interaccion(otro_agente.unique_id, "amigo", incremento, otro_agente.recursos, otro_agente.grupo_id)
                otro_agente.memoria.registrar_interaccion(self.unique_id, "amigo", incremento, self.recursos, self.grupo_id)
                
                self.modelo.log(f"  🤝 [COOPERACIÓN] Agente {self.unique_id} ayudó a {otro_agente.unique_id} con {cantidad:.1f} recursos.", categoria="social")
                self.decir(self.generar_dialogo(otro_agente, "ayuda_dar"))
                otro_agente.decir(otro_agente.generar_dialogo(self, "ayuda_recibir"))

        # Lógica de Conflicto (Competencia)
        elif self.personalidad["competitividad"] > 0.8 and otro_agente.recursos > self.recursos:
            exito_ataque = (self.rango / (self.rango + otro_agente.rango)) * random.random()
            if exito_ataque > 0.4:
                daño = random.randint(2, 8)
                otro_agente.recursos -= daño
                self.recursos += daño
                self.rango += 0.1
                otro_agente.rango = max(0.5, otro_agente.rango - 0.05)
                
                # Registrar en memoria (impacto negativo)
                self.memoria.registrar_interaccion(otro_agente.unique_id, "enemigo", -1.5, otro_agente.recursos, otro_agente.grupo_id)
                otro_agente.memoria.registrar_interaccion(self.unique_id, "enemigo", -1.5, self.recursos, self.grupo_id)
                
                self.modelo.log(f"  ⚔️ [CONFLICTO] Agente {self.unique_id} atacó a {otro_agente.unique_id}.", categoria="conflict")
                self.decir(self.generar_dialogo(otro_agente, "attack" if "attack" in self.generar_dialogo(otro_agente, "ataque") else "ataque"))
                otro_agente.decir(otro_agente.generar_dialogo(self, "defensa"))
            else:
                self.modelo.log(f"  🛡️ [CONFLICTO FALLIDO] Agente {self.unique_id} intentó intimidar a {otro_agente.unique_id} pero falló.", categoria="conflict")
                self.decir("¡Tsk! La próxima vez no tendrás tanta suerte...")
        
        else:
            afinidad_base = 0.2 * (self.personalidad["amabilidad"] + otro_agente.personalidad["amabilidad"])
            
            # Registrar en memoria (interacción neutral/social)
            tipo = "amigo" if self.memoria.obtener_fuerza(otro_agente.unique_id) + afinidad_base > 2.5 else "conocido"
            self.memoria.registrar_interaccion(otro_agente.unique_id, tipo, afinidad_base, otro_agente.recursos, otro_agente.grupo_id)
            otro_agente.memoria.registrar_interaccion(self.unique_id, tipo, afinidad_base, self.recursos, self.grupo_id)
            
            self.modelo.log(f"  💬 [SOCIAL] Charla entre {self.unique_id} y {otro_agente.unique_id}.", categoria="social")
            self.decir(self.generar_dialogo(otro_agente, "social"))
            otro_agente.decir(otro_agente.generar_dialogo(self, "respuesta_social"))

        # Actualizar tipo de relación según fuerza (esto ya se hace dentro de memoria.registrar_interaccion, 
        # pero mantenemos la lógica de umbrales aquí para claridad si es necesario)
        pass

    def actualizar_estado(self):
        """Actualiza las necesidades y recursos internos en cada paso."""
        # Producción aleatoria (recolección)
        recoleccion = random.randint(1, 5)
        self.recursos += recoleccion

        # El metabolismo consume recursos
        consumo = 1.5 + (self.necesidades["alimento"] * 0.05)
        self.recursos -= consumo
        
        self.modelo.log(f"  🍎 [ESTADO] Agente {self.unique_id}: Recolectó {recoleccion}, Consumió {consumo:.1f}. Recursos actuales: {self.recursos:.1f}", categoria="state")

        # Si los recursos son bajos, el hambre aumenta
        if self.recursos < 30:
            self.necesidades["alimento"] += 1
            self.modelo.log(f"  ⚠️ [ALERTA] Agente {self.unique_id} tiene hambre acumulada ({self.necesidades['alimento']}).", categoria="sistema")
        else:
            self.necesidades["alimento"] = max(1, self.necesidades["alimento"] - 0.5)
            
        # La soledad aumenta si no interactúa
        self.necesidades["social"] += 0.5

    def step(self):
        """Acciones que realiza el agente en un turno."""
        self.modelo.log(f"\n--- Turno del Agente {self.unique_id} ---", categoria="turno")
        
        # Si es un agente de élite, usa LangGraph para pensar
        if self.cerebro_lg:
            conocidos = list(self.memoria.grafo.neighbors(self.unique_id))
            decision_lg, mensaje_lg = self.cerebro_lg.pensar(self.recursos, self.necesidades["alimento"], conocidos)
            self.modelo.log(f"🧠 [LANGGRAPH] Pensamiento interno: {mensaje_lg}", categoria="sistema")
            
        self.actualizar_estado()
        
        # Decidir con quién interactuar basado en extroversión
        num_interacciones = 1 if self.personalidad["extroversión"] < 0.5 else 2
        
        for _ in range(num_interacciones):
            otros = [a for a in self.modelo.agentes if a.unique_id != self.unique_id]
            if otros:
                objetivo = random.choice(otros)
                self.interactuar(objetivo)
                self.necesidades["social"] = max(0, self.necesidades["social"] - 2)

class ModeloRelacional:
    def __init__(self, num_agentes=10, log_callback=None):
        self.num_agentes = num_agentes
        self.log_callback = log_callback
        self.agentes = [Agente(i, self) for i in range(self.num_agentes)]
        self.paso_actual = 0
        self.historial_recursos = []
        self.historial_relaciones = []
        self.historial_grupos = []
        self.datos = [] # Mantener para compatibilidad con visualizar_resultados

    def log(self, mensaje, categoria="info", subtitulos=None, tts_text=None):
        """Envía un log al callback o a la terminal."""
        if self.log_callback:
            self.log_callback(mensaje, categoria, subtitulos, tts_text)
        else:
            print(mensaje)
            if subtitulos:
                print(f"             └─ [Subtítulos: {subtitulos}]")

    def step(self):
        self.paso_actual += 1
        self.log(f"\n================ PASO {self.paso_actual} ================", categoria="paso")
        
        # Lógica de formación de grupos (cada 10 pasos)
        if self.paso_actual % 10 == 0:
            self.log("📢 [SISTEMA] Evaluando formación de grupos sociales...", categoria="sistema")
            self.formar_grupos()

        # Registrar métricas globales
        recursos_totales = sum(a.recursos for a in self.agentes)
        promedio_recursos = recursos_totales / len(self.agentes)
        
        # Contar tipos de relaciones desde la memoria de cada agente
        num_amigos = 0
        num_enemigos = 0
        for a in self.agentes:
            for n in a.memoria.grafo.neighbors(a.unique_id):
                tipo = a.memoria.obtener_tipo(n)
                if tipo == "amigo": num_amigos += 1
                if tipo == "enemigo": num_enemigos += 1
        
        self.datos.append({
            "paso": self.paso_actual,
            "recursos_promedio": promedio_recursos,
            "amigos_total": num_amigos // 2,
            "enemigos_total": num_enemigos // 2,
            "num_grupos": len(set(a.grupo_id for a in self.agentes if a.grupo_id is not None))
        })

        # Ejecutar el paso de cada agente
        # Mezclamos el orden para evitar sesgos de prioridad
        agentes_shuffled = list(self.agentes)
        random.shuffle(agentes_shuffled)
        for agente in agentes_shuffled:
            agente.step()

    def formar_grupos(self):
        """Los agentes con fuertes lazos de amistad forman grupos."""
        for agente in self.agentes:
            if agente.grupo_id is None:
                # Buscar amigos en su memoria
                amigos = [n for n in agente.memoria.grafo.neighbors(agente.unique_id) 
                          if agente.memoria.obtener_tipo(n) == "amigo"]
                for id_amigo in amigos:
                    otro = self.agentes[id_amigo]
                    if otro.grupo_id is not None:
                        agente.grupo_id = otro.grupo_id
                        break
                else:
                    # Crear nuevo grupo si tiene al menos un amigo
                    if amigos:
                        nuevo_id = f"G{agente.unique_id}"
                        agente.grupo_id = nuevo_id
                        for id_amigo in amigos:
                            self.agentes[id_amigo].grupo_id = nuevo_id

    def ejecutar(self, pasos=50):
        print("\n" + "═"*60)
        print("🚀 MISIÓN INICIAL: CREACIÓN DE IDIOMA EMERGENTE")
        print("Los agentes han decidido establecer un protocolo de comunicación")
        print("basado en glifos y símbolos para coordinar su sociedad.")
        print("═"*60 + "\n")
        
        self.log(f"Iniciando simulación con {len(self.agentes)} agentes por {pasos} pasos...", categoria="sistema")
        for _ in range(pasos):
            self.step()
        self.log("Simulación finalizada. ✨", categoria="sistema")

    def visualizar_resultados(self):
        if not self.datos:
            print("No hay datos para visualizar. ❌")
            return

        df = pd.DataFrame(self.datos)
        
        plt.figure(figsize=(10, 6))
        
        # Eje principal: Recursos
        ax1 = plt.gca()
        color = 'tab:blue'
        ax1.set_xlabel('Paso')
        ax1.set_ylabel('Recursos Promedio', color=color)
        ax1.plot(df['paso'], df['recursos_promedio'], color=color, label='Recursos', linewidth=2)
        ax1.tick_params(axis='y', labelcolor=color)

        # Eje secundario: Relaciones
        ax2 = ax1.twinx()
        color_amigos = 'tab:green'
        color_enemigos = 'tab:red'
        ax2.set_ylabel('Cantidad de Relaciones / Grupos', color='black')
        ax2.plot(df['paso'], df['amigos_total'], color=color_amigos, linestyle='--', label='Amigos')
        ax2.plot(df['paso'], df['enemigos_total'], color=color_enemigos, linestyle=':', label='Enemigos')
        ax2.plot(df['paso'], df['num_groups'] if 'num_groups' in df else df['num_grupos'], color='purple', label='Grupos', alpha=0.5)
        ax2.tick_params(axis='y', labelcolor='black')

        plt.title('Evolución de la Sociedad de Agentes')
        
        # Combinar leyendas de ambos ejes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        
        # Forzar el renderizado antes de guardar
        plt.savefig('resultado_simulacion.png', dpi=100, bbox_inches='tight')
        plt.close() # Limpiar memoria
        print("Gráfico guardado exitosamente como 'resultado_simulacion.png' 📊")

    def imprimir_resumen_social(self):
        print("\n--- RESUMEN SOCIAL FINAL ---")
        # Líderes por rango
        lideres = sorted(self.agentes, key=lambda a: a.rango, reverse=True)[:3]
        print("\nTop 3 Agentes con mayor Rango (Estatus):")
        for l in lideres:
            print(f"  - Agente {l.unique_id}: Rango {l.rango:.2f}, Recursos {l.recursos:.2f}, Grupo: {l.grupo_id}")
            l.memoria.imprimir_grafo_terminal()
        
        # Grupos
        grupos = {}
        for a in self.agentes:
            if a.grupo_id:
                grupos[a.grupo_id] = grupos.get(a.grupo_id, 0) + 1
        print(f"\nTotal de grupos formados: {len(grupos)}")
        for gid, count in grupos.items():
            print(f"  - Grupo {gid}: {count} miembros")
        print("----------------------------\n")

if __name__ == "__main__":
    # Configuración desde .env
    num_agentes = int(os.getenv("NUM_AGENTES", 30))
    pasos = int(os.getenv("PASOS_SIMULACION", 100))
    
    # Configuración de la simulación
    modelo = ModeloRelacional(num_agentes=num_agentes)
    modelo.ejecutar(pasos=pasos)
    modelo.imprimir_resumen_social()
    modelo.visualizar_resultados()
