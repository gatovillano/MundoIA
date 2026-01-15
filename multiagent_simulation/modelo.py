import random
import matplotlib
matplotlib.use('Agg') # Backend para entornos sin interfaz gráfica
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from memoria import MemoriaGrafica
from cerebro_langgraph import CerebroAvanzado
from cerebro_llm import cerebro_llm
from dotenv import load_dotenv
import os
import json
from herramientas import herramientas
import psycopg2
from psycopg2.extras import Json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.conn_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "database": os.getenv("DB_NAME", "mundoia"),
            "user": os.getenv("DB_USER", "architect"),
            "password": os.getenv("DB_PASS", "mundoia_secret_2026"),
            "port": os.getenv("DB_PORT", "5434")
        }
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = True
            logger.info("✅ Conexión a PostgreSQL establecida.")
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            return False

    def execute(self, query, params=None):
        if not self.conn: return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
            return True
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            return False

    def save_agent(self, agent, user_id):
        query = """
        INSERT INTO agentes (id, user_id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, civilizacion_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            recursos = EXCLUDED.recursos,
            dinero = EXCLUDED.dinero,
            grupo_id = EXCLUDED.grupo_id,
            rol = EXCLUDED.rol,
            profesion = EXCLUDED.profesion,
            rango = EXCLUDED.rango,
            reputacion = EXCLUDED.reputacion,
            personalidad = EXCLUDED.personalidad,
            necesidades = EXCLUDED.necesidades,
            experiencia = EXCLUDED.experiencia,
            conocimientos = EXCLUDED.conocimientos,
            inventario = EXCLUDED.inventario,
            hitos = EXCLUDED.hitos,
            historial_etico = EXCLUDED.historial_etico,
            civilizacion_id = EXCLUDED.civilizacion_id;
        """
        self.execute(query, (
            str(agent.unique_id), user_id, agent.recursos, agent.dinero, agent.grupo_id, agent.rol,
            agent.profesion, agent.rango, agent.reputacion, Json(agent.personalidad),
            Json(agent.necesidades), Json(agent.experiencia), Json(agent.conocimientos),
            Json(agent.inventario), Json(agent.hitos), Json(agent.historial_etico),
            agent.civilizacion_id
        ))

    def save_civilization(self, civ):
        query = """
        INSERT INTO civilizaciones (id, nombre, color, user_id, recursos_globales, territorio)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, user_id) DO UPDATE SET
            nombre = EXCLUDED.nombre,
            color = EXCLUDED.color,
            recursos_globales = EXCLUDED.recursos_globales,
            territorio = EXCLUDED.territorio;
        """
        self.execute(query, (civ.id, civ.nombre, civ.color, civ.user_id, civ.recursos_globales, Json(civ.territorio)))

    def get_civilizations(self):
        query = "SELECT * FROM civilizaciones;"
        return self.execute(query)

    def save_user(self, user_id, username, password_hash):
        query = "INSERT INTO usuarios (id, username, password_hash) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING;"
        self.execute(query, (user_id, username, password_hash))

    def save_memory(self, owner_id, target_id, data, user_id):
        query = """
        INSERT INTO memorias (user_id, agente_fuente, agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, agente_fuente, agente_objetivo) DO UPDATE SET
            tipo_relacion = EXCLUDED.tipo_relacion,
            fuerza = EXCLUDED.fuerza,
            recursos_percibidos = EXCLUDED.recursos_percibidos,
            grupo_percibido = EXCLUDED.grupo_percibido;
        """
        params = (
            user_id, str(owner_id), str(target_id), data.get('tipo'), data.get('fuerza', 0.0),
            data.get('recursos_vistos'), data.get('grupo')
        )
        self.execute(query, params)

    def save_world_state(self, user_id, step, lore, seed, economy, relaciones_grupos=None):
        query = """
        INSERT INTO estado_mundo (user_id, paso_actual, lore, seed, precio_recurso, indice_bursatil, total_dinero, relaciones_grupos)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            paso_actual = EXCLUDED.paso_actual,
            lore = EXCLUDED.lore,
            seed = EXCLUDED.seed,
            precio_recurso = EXCLUDED.precio_recurso,
            indice_bursatil = EXCLUDED.indice_bursatil,
            total_dinero = EXCLUDED.total_dinero,
            relaciones_grupos = EXCLUDED.relaciones_grupos;
        """
        params = (
            user_id, step, lore, seed, economy.get('precio_recurso', 2.0),
            economy.get('indice_bursatil', 1000.0), economy.get('total_dinero', 0.0),
            Json(relaciones_grupos) if relaciones_grupos else Json({})
        )
        self.execute(query, params)

    def get_world_state(self, user_id):
        query = "SELECT paso_actual, lore, seed, precio_recurso, indice_bursatil, total_dinero, relaciones_grupos FROM estado_mundo WHERE user_id = %s ORDER BY id DESC LIMIT 1;"
        result = self.execute(query, (user_id,))
        return result[0] if result else None

    def get_agents(self, user_id):
        query = "SELECT * FROM agentes WHERE user_id = %s;"
        return self.execute(query, (user_id,))

    def get_memories(self, agent_id, user_id):
        query = "SELECT agente_objetivo, tipo_relacion, fuerza, recursos_percibidos, grupo_percibido FROM memorias WHERE agente_fuente = %s AND user_id = %s;"
        return self.execute(query, (str(agent_id), user_id))

    def clear_database(self, user_id=None):
        """Limpia las tablas de la base de datos de forma selectiva por usuario."""
        if not user_id:
            logger.warning("⚠️ Intento de limpiar DB sin especificar user_id.")
            return

        # Dado que el esquema actual asocia agentes a civilizaciones y civilizaciones a usuarios...
        # Primero obtenemos las civilizaciones del usuario
        query_civs = "SELECT id FROM civilizaciones WHERE user_id = %s;"
        civs = self.execute(query_civs, (user_id,))
        civ_ids = [c[0] for c in civs] if civs else []

        if civ_ids:
            # Borrar memorias de agentes que pertenecen a estas civilizaciones
            for civ_id in civ_ids:
                query_mem = """
                DELETE FROM memorias WHERE agente_fuente IN 
                (SELECT id FROM agentes WHERE civilizacion_id = %s);
                """
                self.execute(query_mem, (civ_id,))

                # Borrar agentes
                self.execute("DELETE FROM agentes WHERE civilizacion_id = %s;", (civ_id,))

            # Borrar civilizaciones
            self.execute("DELETE FROM civilizaciones WHERE user_id = %s;", (user_id,))

        # Borrar estado del mundo y otros asociados al usuario
        self.execute("DELETE FROM estado_mundo WHERE user_id = %s;", (user_id,))
        self.execute("DELETE FROM logs_simulacion WHERE user_id = %s;", (user_id,))
        
        logger.info(f"🗑️ Base de datos limpiada para usuario {user_id}.")

# Cargar configuración
load_dotenv()

class Civilizacion:
    def __init__(self, id, nombre, color, user_id=None):
        self.id = id
        self.nombre = nombre
        self.color = color
        self.user_id = user_id
        self.recursos_globales = 0.0
        self.territorio = [] # Lista de (x, y)
        self.tecnologias = []
        self.leyes = []

class TerrainType:
    GRASS = "grass"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    WATER = "water"
    DESERT = "desert"

class WeatherType:
    SUNNY = "sunny"
    RAINY = "rainy"
    STORM = "storm"
    FOGGY = "foggy"
    HEATWAVE = "heatwave"

class Tile:
    def __init__(self, x, y, terrain_type=TerrainType.GRASS):
        self.x = x
        self.y = y
        self.terrain_type = terrain_type
        self.resource_node = None # {type: "food"|"wood"|"stone", amount: 100}
        self.owner_civ_id = None
        self.buildings = [] # List of building dicts
        self.difficulty = 1.0
        
        if terrain_type == TerrainType.MOUNTAIN: self.difficulty = 2.0
        if terrain_type == TerrainType.WATER: self.difficulty = 5.0
    
    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "terrain": self.terrain_type,
            "resource": self.resource_node,
            "owner": self.owner_civ_id,
            "buildings": self.buildings
        }

class Agente:
    def __init__(self, unique_id, modelo, recursos=100, necesidades=None, personalidad=None, civ_id=None):
        self.unique_id = unique_id
        self.modelo = modelo
        self.recursos = recursos
        self.civilizacion_id = civ_id
        
        # Posición en el mundo (Mapa de 20x20 por defecto)
        self.x = random.randint(0, 19)
        self.y = random.randint(0, 19)
        
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
            "competitividad": random.random(),
            "curiosidad": random.random(),
            "lealtad": random.random(),
            "prudencia": random.random(),
            "hostilidad": random.random()
        }
        self.necesidades = {
            "alimento": random.uniform(0, 5),
            "social": random.uniform(0, 5),
            "seguridad": random.uniform(0, 5),
            "descanso": 0.0,
            "entretenimiento": random.uniform(0, 5),
            "salud": 10.0
        }
        
        # Memoria basada en Grafos
        self.memoria = MemoriaGrafica(self.unique_id)
        
        # Cerebro Cognitivo (TODOS los agentes ahora son inteligentes)
        self.cerebro = CerebroAvanzado(self.unique_id)
        
        # Nuevos atributos: Grupo y Jerarquía
        self.grupo_id = None
        self.rol = "Ciudadano" # Rol inicial
        self.ultimo_mensaje_recibido = None # Para responder a otros
        self.dinero = 100.0 # Nueva unidad de cambio: MundoCoins (MC)
        self.rango = 1.0 # Estatus social (influye en la influencia)
        self.conocimientos = {} # Información compartida o descubierta
        self.planes = [] # Acuerdos con otros agentes
        self.gasto_turno = 0.0 # Control de gasto por turno
        self.inversiones = [] # [{monto, paso_inicio, interes_esperado}]
        self.alianzas = [] # Lista de IDs de agentes aliados (para compatibilidad)
        self.tratados = [] # Lista de dicts: {"socio_id": ID, "terminos": {...}, "pasos_restantes": N}
        self.inventario = {
            "medicina": 0,
            "ocio": 0
        }
        
        # --- SISTEMA DE PROFESIONES ---
        self.profesion = None # "Médico", "Comerciante", "Guarda", "Explorador"
        self.experiencia = {
            "medicina": 0,
            "comercio": 0,
            "combate": 0,
            "exploracion": 0
        }
        self.hitos = [] # Lista de logros alcanzados
        
        # --- SISTEMA POLÍTICO ---
        self.reputacion = 1.0 # 0.0 a 1.0 (Prestigio social)
        self.votos_recibidos = 0
        self.historial_etico = [] # Registro de crímenes o buenas acciones

    def decir(self, mensaje, pensamiento=None, privado_para=None, para_grupo=False):
        """Imprime un mensaje directo, privado o para el grupo."""
        prefijo = f"[{self.unique_id}]"
        
        if para_grupo and self.grupo_id:
            prefijo = f"👥 {prefijo} (Para Facción {self.grupo_id})"
            privado_para = f"GRUPO:{self.grupo_id}"
        elif privado_para:
            prefijo = f"🔒 {prefijo} (Privado para {privado_para})"
        elif self.personalidad["amabilidad"] > 0.7: prefijo = f"😇 {prefijo}"
        elif self.personalidad["competitividad"] > 0.7: prefijo = f"👿 {prefijo}"
        else: prefijo = f"🤖 {prefijo}"
        
        self.modelo.log(f'{prefijo}: "{mensaje}"', categoria="dialogo", tts_text=mensaje, pensamiento=pensamiento, privado_para=privado_para)

    def interactuar(self, otro_agente, tipo_interaccion="social", mensaje_enviado=None):
        """Define cómo el agente interactúa con otro basado en su decisión cognitiva."""
        
        # El otro agente guarda el mensaje para su fase de pensamiento/respuesta
        if mensaje_enviado:
            otro_agente.ultimo_mensaje_recibido = {
                "emisor": self.unique_id,
                "contenido": mensaje_enviado
            }
            
            # El otro agente responde inmediatamente si es una interacción social/competitiva
            # Para evitar bucles infinitos, solo respondemos si no estamos ya en una respuesta
            if not getattr(self, '_respondiendo', False):
                otro_agente._respondiendo = True
                # El objetivo piensa una RESPUESTA basada en el mensaje recibido
                decision_resp, mensaje_resp, pensamiento_resp, es_privado_resp, es_grupal_resp = otro_agente.cerebro.pensar(otro_agente, objetivo_id=self.unique_id)
                
                # IMPORTANTE: El otro agente DEBE decir su respuesta
                otro_agente.decir(mensaje_resp, pensamiento=pensamiento_resp, privado_para=self.unique_id if es_privado_resp else None, para_grupo=es_grupal_resp)
                
                # Si la respuesta fue SOCIALIZAR o COMPETIR, procesar efectos
                if decision_resp in ["SOCIALIZAR", "COMPETIR"]:
                    # Evitamos recursión infinita no llamando a interactuar de nuevo aquí, 
                    # pero registramos la interacción en la memoria
                    otro_agente.memoria.registrar_interaccion(self.unique_id, "amigo" if decision_resp == "SOCIALIZAR" else "enemigo", 0.1 if decision_resp == "SOCIALIZAR" else -0.2)
                
                otro_agente._respondiendo = False
                # Limpiar mensaje tras responder
                otro_agente.ultimo_mensaje_recibido = None

        if tipo_interaccion == "SOCIALIZAR" or tipo_interaccion == "social":
            self.reputacion = min(1.0, self.reputacion + 0.01) # Socializar mejora reputación
            # La hostilidad de ambos agentes reduce la probabilidad de una buena relación
            hostilidad_total = self.personalidad.get("hostilidad", 0.5) + otro_agente.personalidad.get("hostilidad", 0.5)
            afinidad_base = 0.2 * (self.personalidad["amabilidad"] + otro_agente.personalidad["amabilidad"]) - (0.15 * hostilidad_total)
            
            # Factor de Envidia: Si el otro tiene mucho más dinero, la afinidad baja
            if otro_agente.dinero > self.dinero * 1.5:
                afinidad_base -= 0.1 * self.personalidad.get("hostilidad", 0.5)

            self.memoria.registrar_interaccion(otro_agente.unique_id, "amigo" if afinidad_base > 0 else "conocido", afinidad_base, otro_agente.recursos, otro_agente.grupo_id)
            self.modelo.log(f"  🤝 [SOCIAL] Agente {self.unique_id} socializa con {otro_agente.unique_id}. Afinidad: {afinidad_base:.2f}", categoria="social")
            
        elif tipo_interaccion == "COMPETIR":
            self.ganar_experiencia("combate", 1)
            self.reputacion = max(0.0, self.reputacion - 0.05) # Atacar baja reputación
            
            # Verificar si hay leyes contra el robo en la facción
            leyes_faccion = self.modelo.facciones_leyes.get(self.grupo_id, [])
            if any("prohibido robar" in l.lower() or "ley de salud" in l.lower() for l in leyes_faccion):
                self.sancionar("Violación de la ley de propiedad", gravedad=0.15)

            # El ataque siempre destruye la relación
            self.memoria.registrar_interaccion(otro_agente.unique_id, "enemigo", -0.5, otro_agente.recursos, otro_agente.grupo_id)
            otro_agente.memoria.registrar_interaccion(self.unique_id, "enemigo", -0.5, self.recursos, self.grupo_id)
            
            exito = random.random() * self.rango > random.random() * otro_agente.rango
            if exito:
                robo = 5
                self.recursos += robo
                otro_agente.recursos -= robo
                
                # Posibilidad de robar objetos del inventario
                if random.random() < 0.3:
                    for item in ["medicina", "ocio"]:
                        if otro_agente.inventario[item] > 0:
                            otro_agente.inventario[item] -= 1
                            self.inventario[item] += 1
                            self.modelo.log(f"  🏴‍☠️ [ROBO] ¡Agente {self.unique_id} le arrebató un objeto de {item} a {otro_agente.unique_id}!", categoria="conflict")
                            break
                
                self.modelo.log(f"  ⚔️ [CONFLICTO] Agente {self.unique_id} robó recursos a {otro_agente.unique_id}.", categoria="conflict")
            else:
                self.modelo.log(f"  🛡️ [FALLO] Agente {self.unique_id} intentó atacar a {otro_agente.unique_id} pero falló.", categoria="conflict")
        
        # --- IMPACTO DIPLOMÁTICO ---
        if self.grupo_id and otro_agente.grupo_id and self.grupo_id != otro_agente.grupo_id:
            cambio_grupal = 0.05 if (tipo_interaccion == "SOCIALIZAR" or tipo_interaccion == "social") else -0.1
            self.modelo.actualizar_relacion_grupal(self.grupo_id, otro_agente.grupo_id, cambio_grupal)
        
    def fundar_grupo(self, nombre_mision):
        """El agente crea un nuevo grupo y se convierte en líder."""
        nuevo_grupo_id = f"G-{random.randint(100, 999)}"
        # Asignar un color de la paleta basado en el ID para que sea consistente
        color_idx = int(nuevo_grupo_id.split("-")[1]) % len(self.modelo.colores_paleta)
        nuevo_color = self.modelo.colores_paleta[color_idx]
        
        self.modelo.civilizaciones[nuevo_grupo_id] = Civilizacion(
            id=nuevo_grupo_id,
            nombre=f"Facción {nombre_mision}",
            color=nuevo_color,
            user_id=getattr(self.modelo, 'current_user_id', None)
        )
        self.grupo_id = nuevo_grupo_id
        self.rol = "Líder"
        self.modelo.log(f"🚩 [FUNDACION] Agente {self.unique_id} ha fundado '{nombre_mision}' con color {nuevo_color}.", categoria="consenso")
        self.modelo.grupos_creados_este_paso += 1
        return nuevo_grupo_id

    def invitar_agente(self, otro_agente):
        """Envía una invitación formal para unirse a su facción."""
        if self.grupo_id is None:
            return False
        
        # Solo invitamos si no tiene grupo o si queremos que cambie
        if otro_agente.grupo_id == self.grupo_id:
            return False

        mision = self.modelo.objetivos_grupos.get(self.grupo_id, "Prosperidad Colectiva")
        otro_agente.ultimo_mensaje_recibido = {
            "emisor": self.unique_id,
            "contenido": f"INVITACION_GRUPO:{self.grupo_id}:{mision}"
        }
        self.modelo.log(f"✉️ [INVITACION] Agente {self.unique_id} invita a {otro_agente.unique_id} a unirse a la Facción {self.grupo_id}.", categoria="social")
        return True

    def formar_alianza(self, otro_agente, terminos=None):
        """Crea un pacto de alianza mutua con términos específicos."""
        # Si no hay términos, es una alianza básica de apoyo mutuo
        if terminos is None:
            terminos = {"tipo": "apoyo_mutuo", "descripcion": "Apoyo social y suministros básicos"}

        # Evitar duplicados de tratados activos con el mismo agente
        if any(t["socio_id"] == otro_agente.unique_id for t in self.tratados):
            return False

        nuevo_tratado_yo = {
            "socio_id": otro_agente.unique_id,
            "terminos": terminos,
            "pasos_restantes": 10 # Duración estándar de 10 turnos
        }
        nuevo_tratado_otro = {
            "socio_id": self.unique_id,
            "terminos": terminos,
            "pasos_restantes": 10
        }

        self.tratados.append(nuevo_tratado_yo)
        otro_agente.tratados.append(nuevo_tratado_otro)
        
        # Mantener lista de alianzas para compatibilidad visual
        if otro_agente.unique_id not in self.alianzas: self.alianzas.append(otro_agente.unique_id)
        if self.unique_id not in otro_agente.alianzas: otro_agente.alianzas.append(self.unique_id)

        desc = terminos.get("descripcion", "Pacto formal")
        self.modelo.log(f"📜 [TRATADO] {self.unique_id} y {otro_agente.unique_id} han firmado: {desc}", categoria="social")
        return True

    def comerciar(self, otro_agente, tipo="compra"):
        """Realiza una transacción económica entre agentes."""
        # Precio base influenciado por el mercado global
        precio_mercado = float(self.modelo.precio_recurso_actual)
        
        if tipo == "compra":
            # Yo compro recursos a otro_agente
            cantidad = 3 # Reducido de 5 a 3
            costo = cantidad * precio_mercado
            if self.dinero >= costo and otro_agente.recursos >= cantidad and (self.gasto_turno + costo) <= 30:
                self.dinero -= costo
                self.gasto_turno += costo
                self.recursos += cantidad
                otro_agente.dinero += costo
                otro_agente.recursos -= cantidad
                self.modelo.log(f"💰 [COMERCIO] Agente {self.unique_id} compró {cantidad} recursos a {otro_agente.unique_id} por {costo:.1f} MC.", categoria="social")
                return True
        return False

    def mejorar_seguridad(self):
        """Invierte dinero en mejorar el rango y la protección."""
        costo = 25.0 # Reducido de 50 a 25 para que sea viable con el límite de 30
        if self.dinero >= costo and (self.gasto_turno + costo) <= 30:
            self.dinero -= costo
            self.gasto_turno += costo
            self.rango += 0.2
            self.necesidades["seguridad"] = max(0, self.necesidades["seguridad"] - 5)
            self.modelo.log(f"🛡️ [SEGURIDAD] Agente {self.unique_id} invirtió en protección. Rango aumentado a {self.rango:.1f}.", categoria="state")
            return True
        return False

    def invertir(self, monto):
        """El agente coloca dinero en el mercado para obtener retornos futuros."""
        if self.dinero >= monto and (self.gasto_turno + monto) <= 30:
            self.dinero -= monto
            self.gasto_turno += monto
            # Inversión a 5 pasos con un interés aleatorio entre -5% y +15%
            interes = random.uniform(-0.05, 0.15)
            self.inversiones.append({
                "monto": monto,
                "paso_final": self.modelo.paso_actual + 5,
                "interes": interes
            })
            self.modelo.log(f"📈 [INVERSIÓN] Agente {self.unique_id} invirtió {monto:.1f} MC en el mercado.", categoria="state")
            return True
        return False

    def actualizar_estado(self):
        """Actualiza las necesidades y recursos internos en cada paso."""
        # Producción pasiva aumentada para mayor resiliencia
        self.recursos += 0.5

        # Procesar inversiones terminadas
        for inv in list(self.inversiones):
            if self.modelo.paso_actual >= inv["paso_final"]:
                ganancia = inv["monto"] * (1 + inv["interes"])
                self.dinero += ganancia
                self.inversiones.remove(inv)
                resultado = "ganancia" if inv["interes"] > 0 else "pérdida"
                self.modelo.log(f"💰 [RETORNO] Inversión de {self.unique_id} finalizada: {ganancia:.1f} MC ({resultado}).", categoria="social")

        # El metabolismo consume menos recursos para evitar muertes rápidas
        consumo = 0.5 + (self.necesidades["alimento"] * 0.03)
        self.recursos -= consumo
        
        # Necesidades aumentan más lentamente
        self.necesidades["alimento"] += 0.10
        self.necesidades["social"] += 0.08
        self.necesidades["seguridad"] += 0.04
        self.necesidades["descanso"] += 0.15
        self.necesidades["entretenimiento"] += 0.08
        
        # --- REGENERACIÓN PASIVA ---
        # Si el agente está bien alimentado y descansado, recupera salud
        if self.necesidades["alimento"] < 3.0 and self.necesidades["descanso"] < 5.0:
            self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 0.1)
            # Log sutil de bienestar solo de vez en cuando para no saturar
            if random.random() < 0.1:
                self.modelo.log(f"✨ [BIENESTAR] Agente {self.unique_id} se está recuperando gracias a su buen estado.", categoria="state")
        
        # --- PROCESAMIENTO DE TRATADOS FORMALES ---
        for tratado in list(self.tratados):
            aliado = next((a for a in self.modelo.agentes if a.unique_id == tratado["socio_id"]), None)
            if not aliado: continue

            t = tratado["terminos"]
            # 1. Intercambio de Recursos por Dinero
            if t.get("tipo") == "intercambio":
                dar = t.get("da", {}) # {recurso: "medicina", cant: 1}
                recibe = t.get("recibe", {}) # {recurso: "dinero", cant: 10}

                # Ejecutar si ambos tienen lo necesario
                puedo_dar = False
                if dar.get("recurso") == "medicina" and self.inventario["medicina"] >= dar.get("cant", 0): puedo_dar = True
                elif dar.get("recurso") == "dinero" and self.dinero >= dar.get("cant", 0): puedo_dar = True
                elif dar.get("recurso") == "recursos" and self.recursos >= dar.get("cant", 0): puedo_dar = True

                if puedo_dar:
                    # Transferir lo que yo doy
                    if dar["recurso"] == "medicina": 
                        self.inventario["medicina"] -= dar["cant"]; aliado.inventario["medicina"] += dar["cant"]
                    elif dar["recurso"] == "dinero":
                        self.dinero -= dar["cant"]; aliado.dinero += dar["cant"]
                    elif dar["recurso"] == "recursos":
                        self.recursos -= dar["cant"]; aliado.recursos += dar["cant"]
                    
                    # Transferir lo que yo recibo (si el aliado puede)
                    # Nota: Simplificado para que el aliado siempre cumpla su parte si el otro empezó
                    if recibe["recurso"] == "dinero":
                        aliado.dinero -= recibe["cant"]; self.dinero += recibe["cant"]
                    elif recibe["recurso"] == "seguridad":
                        self.rango += recibe["cant"] # El aliado me brinda protección
                    
                    self.modelo.log(f"🤝 [EJECUCION TRATADO] Intercambio realizado entre {self.unique_id} y {aliado.unique_id}.", categoria="social")

            # Reducir duración
            tratado["pasos_restantes"] -= 1
            if tratado["pasos_restantes"] <= 0:
                self.tratados.remove(tratado)
                # También quitar del aliado
                aliado.tratados = [at for at in aliado.tratados if at["socio_id"] != self.unique_id]
                self.modelo.log(f"⌛ [SISTEMA] El tratado entre {self.unique_id} y {aliado.unique_id} ha expirado.", categoria="sistema")

        if self.necesidades["salud"] <= 0:
            self.morir("agotamiento total de constantes vitales")
            return

        # --- INSTINTO DE SUPERVIVENCIA AUTOMÁTICO ---
        tile = self.modelo.mapa[self.x][self.y]
        
        # 1. Alimentación automática si hay comida en el suelo y tiene hambre
        if tile.resource_node and tile.resource_node["type"] == "food" and self.necesidades["alimento"] > 4.0:
            comida_tomada = min(tile.resource_node["amount"], 2.0)
            tile.resource_node["amount"] -= comida_tomada
            self.necesidades["alimento"] = max(0, self.necesidades["alimento"] - (comida_tomada * 2))
            self.modelo.log(f"🍎 [INSTINTO] Agente {self.unique_id} consumió alimento del terreno automáticamente.", categoria="alimentos")
            if tile.resource_node["amount"] <= 0: tile.resource_node = None

        # 2. Uso de infraestructura (Hospitales y Centros de Recarga)
        for edif in tile.buildings:
            if edif["tipo"].lower() in ["hospital", "clinica"] and self.necesidades["salud"] < 9.0:
                self.necesidades["salud"] = min(10.0, self.necesidades["salud"] + 1.0)
                self.modelo.log(f"🏥 [SISTEMA] Agente {self.unique_id} está siendo atendido en el Hospital.", categoria="salud")
            
            if "recarga" in edif["tipo"].lower() or "eléctrica" in edif["tipo"].lower():
                self.necesidades["descanso"] = max(0, self.necesidades["descanso"] - 2.0)
                self.recursos += 1.0 # Carga de energía/recursos
                self.modelo.log(f"⚡ [SISTEMA] Agente {self.unique_id} recargando constantes en estación energética.", categoria="ambiente")

    def morir(self, motivo):
        """Finaliza la existencia del agente en la simulación."""
        if not self.esta_vivo: return
        
        self.esta_vivo = False
        self.modelo.log(f"🪦 [FUNERAL] El Agente {self.unique_id} ha MUERTO. Motivo: {motivo}.", categoria="sistema")
        
        # Eliminar de la lista activa del modelo
        if self in self.modelo.agentes:
            self.modelo.agentes.remove(self)
            
        # Limpiar tratados y alianzas
        for aliado_id in list(self.alianzas):
            aliado = self.modelo.get_agent_by_id(aliado_id)
            if aliado and self.unique_id in aliado.alianzas:
                aliado.alianzas.remove(self.unique_id)
        
        # Registrar en DB si es posible
        if self.modelo.db_active:
            try:
                self.modelo.db.execute("UPDATE agentes SET reputacion = %s WHERE id = %s", (0.0, self.unique_id))
            except: pass

    def recolectar(self):
        """El agente busca recursos en el entorno. Prioriza los nodos de recursos del mapa."""
        tile = self.modelo.mapa[self.x][self.y]
        
        # 1. Recolección de nodo específico
        if tile.resource_node and tile.resource_node["amount"] > 0:
            tipo = tile.resource_node["type"]
            cantidad = min(tile.resource_node["amount"], random.randint(5, 15))
            tile.resource_node["amount"] -= cantidad
            
            if tipo == "food":
                self.recursos += cantidad
                self.modelo.log(f"  🍎 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de ALIMENTO del terreno.", categoria="alimentos")
            elif tipo == "wood" or tipo == "stone":
                # Por ahora wood/stone se convierten en recursos genéricos o se podrían añadir al inventario
                self.recursos += cantidad * 1.5 # Más valioso
                self.modelo.log(f"  🪵 [RECOLECCION] Agente {self.unique_id} recolectó {cantidad} de MATERIALES ({tipo}).", categoria="recursos")
                
            if tile.resource_node["amount"] <= 0:
                tile.resource_node = None # Agotado
                self.modelo.log(f"  ⚠️ [RECOLECCION] El nodo de recursos en ({self.x}, {self.y}) se ha AGOTADO.", categoria="ambiente")
            return

        # 2. Recolección genérica (baja eficiencia)
        r = random.random()
        if r < 0.60: # 60% Alimento (reducido)
            cantidad = random.uniform(2, 8)
            self.recursos += cantidad
            self.modelo.log(f"  🌱 [RECOLECCION] Agente {self.unique_id} forrajeó {cantidad:.1f} unidades de alimento.", categoria="alimentos")
        elif r < 0.65: # 5% Medicina
            self.inventario["medicina"] += 1
            self.modelo.log(f"  💊 [RECOLECCION] Agente {self.unique_id} encontró una MEDICINA RARA.", categoria="recursos")
        else:
            self.modelo.log(f"  🍃 [RECOLECCION] Agente {self.unique_id} no encontró nada valioso.", categoria="recursos")
        
        self.necesidades["alimento"] = max(0, self.necesidades["alimento"] - 2)

    def ganar_experiencia(self, area, puntos=1):
        """Aumenta la experiencia en un área y verifica si puede graduarse."""
        if area in self.experiencia:
            self.experiencia[area] += puntos
            # Si llega a 5 de experiencia en un área y no tiene esa profesión, avisar
            if self.experiencia[area] == 5 and self.profesion is None:
                self.modelo.log(f"🎓 [HITOS] Agente {self.unique_id} ha ganado suficiente experiencia en {area} para profesionalizarse.", categoria="sistema")

    def graduarse(self, profesion_deseada):
        """Intenta declarar una profesión si cumple los requisitos y está en una Universidad."""
        if self.profesion:
            return False, "Ya tienes una profesión."

        # VERIFICACIÓN DE UBICACIÓN: Debe haber una Universidad en el tile actual
        tile = self.modelo.mapa[self.x][self.y]
        tiene_universidad = any(b["tipo"] == "Universidad" for b in tile.buildings)
        
        if not tiene_universidad:
            return False, "Debes estar en una Universidad para graduarte y obtener tu título oficial. 🏛️"

        costos = {
            "Médico": 150,
            "Comerciante": 200,
            "Guarda": 100,
            "Explorador": 120
        }
        
        requisitos = {
            "Médico": self.experiencia["medicina"] >= 5 and self.personalidad["amabilidad"] > 0.5,
            "Comerciante": self.experiencia["comercio"] >= 5,
            "Guarda": self.experiencia["combate"] >= 3 and self.personalidad["hostilidad"] < 0.6,
            "Explorador": self.experiencia["exploracion"] >= 5
        }

        if profesion_deseada not in costos:
            return False, "Profesión no válida."

        if not requisitos[profesion_deseada]:
            return False, f"No cumples los requisitos de experiencia o personalidad para ser {profesion_deseada}."

        if self.dinero < costos[profesion_deseada]:
            return False, f"Necesitas {costos[profesion_deseada]} MC para la licencia de {profesion_deseada}."

        # Éxito
        self.dinero -= costos[profesion_deseada]
        self.profesion = profesion_deseada
        self.hitos.append(f"Graduado como {profesion_deseada}")
        self.modelo.log(f"✨ [PROFESION] ¡El Agente {self.unique_id} se ha graduado como {profesion_deseada}! 🎓", categoria="consenso")
        return True, f"¡Felicidades! Ahora eres {profesion_deseada}."

    # --- MÉTODOS POLÍTICOS ---
    def proponer_ley(self, ley_texto):
        """Propone una nueva ley para su facción o el mundo."""
        if not self.grupo_id: return False, "Debes pertenecer a una facción para proponer leyes."
        
        ley_id = f"LEY-{random.randint(1000, 9999)}"
        propuesta = {
            "id": ley_id,
            "autor": self.unique_id,
            "texto": ley_texto,
            "votos_si": 1,
            "votos_no": 0,
            "votantes": [self.unique_id],
            "estado": "pendiente",
            "grupo_id": self.grupo_id
        }
        
        if "propuestas" not in self.modelo.facciones_leyes:
            self.modelo.facciones_leyes["propuestas"] = []
            
        self.modelo.facciones_leyes["propuestas"].append(propuesta)
        self.modelo.log(f"📜 [POLITICA] Agente {self.unique_id} propone la ley: '{ley_texto}' en la Facción {self.grupo_id}.", categoria="sistema")
        return True, ley_id

    def votar_ley(self, ley_id, a_favor=True):
        """Vota una propuesta de ley existente."""
        propuestas = self.modelo.facciones_leyes.get("propuestas", [])
        for p in propuestas:
            if p["id"] == ley_id and self.unique_id not in p["votantes"]:
                if a_favor: p["votos_si"] += 1
                else: p["votos_no"] += 1
                p["votantes"].append(self.unique_id)
                
                # Si vota más del 50% de la facción, se aprueba
                miembros = [a for a in self.modelo.agentes if a.grupo_id == p["grupo_id"]]
                if len(p["votantes"]) > len(miembros) / 2:
                    if p["votos_si"] > p["votos_no"]:
                        p["estado"] = "aprobada"
                        if p["grupo_id"] not in self.modelo.facciones_leyes:
                            self.modelo.facciones_leyes[p["grupo_id"]] = []
                        self.modelo.facciones_leyes[p["grupo_id"]].append(p["texto"])
                        self.modelo.log(f"⚖️ [LEY] ¡La ley '{p['texto']}' ha sido APROBADA en la Facción {p['grupo_id']}!", categoria="sistema")
                    else:
                        p["estado"] = "rechazada"
                        self.modelo.log(f"❌ [LEY] La propuesta '{p['texto']}' fue RECHAZADA.", categoria="sistema")
                return True
        return False

    def sancionar(self, motivo, gravedad=0.1):
        """Reduce la reputación del agente por acciones indebidas."""
        self.reputacion = max(0.0, self.reputacion - gravedad)
        self.historial_etico.append(f"Sanción: {motivo} (-{gravedad})")
        self.modelo.log(f"⚖️ [JUSTICIA] Agente {self.unique_id} sancionado por: {motivo}. Reputación: {self.reputacion:.2f}", categoria="sistema")

    def step(self):
        """Acciones que realiza el agente en un turno."""
        self.gasto_turno = 0.0 # Resetear gasto al inicio del turno
        
        # 1. Identificar posibles objetivos (Prioridad: Respondedor > Vecinos > Azar)
        otros = [a for a in self.modelo.agentes if a.unique_id != self.unique_id]
        objetivo_cercano = None
        
        # Prioridad 1: Quien me habló recientemente
        if self.ultimo_mensaje_recibido:
            emisor_id = self.ultimo_mensaje_recibido['emisor']
            objetivo_cercano = next((a for a in otros if a.unique_id == emisor_id), None)
            
        # Prioridad 2: Vecinos en mi memoria (amigos/conocidos)
        if not objetivo_cercano:
            vecinos_ids = list(self.memoria.grafo.neighbors(self.unique_id))
            if vecinos_ids:
                vecino_id = random.choice(vecinos_ids)
                objetivo_cercano = next((a for a in otros if a.unique_id == vecino_id), None)
        
        # Prioridad 3: Azar
        if not objetivo_cercano and otros:
            objetivo_cercano = random.choice(otros)
        
        # 2. Pensar (LangGraph) - Pasamos el objetivo potencial
        decision, mensaje, pensamiento, es_privado, es_grupal = self.cerebro.pensar(self, objetivo_id=objetivo_cercano.unique_id if objetivo_cercano else None)
        
        destinatario_id = objetivo_cercano.unique_id if (objetivo_cercano and es_privado) else None
        if es_grupal: destinatario_id = f"GRUPO:{self.grupo_id}"
        
        # 3. Actuar según pensamiento
        if decision == "RECOLECTAR":
            self.recolectar()
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)

        elif decision == "SOCIALIZAR" or decision == "COMPETIR":
            if objetivo_cercano:
                # Si estamos socializando y somos líderes, hay probabilidad de invitar al grupo
                if decision == "SOCIALIZAR" and self.rol == "Líder" and random.random() > 0.5:
                    self.invitar_agente(objetivo_cercano)
                
                # Decir el mensaje PRIMERO
                self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)
                # Luego interactuar (esto dispara la respuesta del otro)
                self.interactuar(objetivo_cercano, decision, mensaje_enviado=mensaje)
            else:
                self.decir(mensaje, pensamiento=pensamiento)

        elif decision == "FUNDAR_GRUPO":
            # El mensaje del LLM suele ser la propuesta de misión
            mision_propuesta = mensaje if len(mensaje) < 50 else "Prosperidad y Poder"
            self.fundar_grupo(mision_propuesta)
            self.rol = "Miembro" # El fundador empieza como miembro, el líder se elige en asamblea
            self.decir(f"📢 ¡He fundado una nueva facción! Misión: {mision_propuesta}. ¡Buscamos miembros!", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "INVITAR_A_GRUPO":
            if objetivo_cercano:
                self.invitar_agente(objetivo_cercano)
                self.decir(f"✉️ Agente {objetivo_cercano.unique_id}, te invito a unirte a nuestra causa en la Facción {self.grupo_id}.", pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("Busco nuevos talentos para nuestra facción.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "COMERCIAR":
            if objetivo_cercano:
                exito = self.comerciar(objetivo_cercano, tipo="compra")
                if exito:
                    self.ganar_experiencia("comercio", 1)
                    self.decir(f"🤝 He comprado recursos al Agente {objetivo_cercano.unique_id}. ¡Buen trato!", pensamiento=pensamiento, privado_para=destinatario_id)
                else:
                    self.decir(f"💸 Quería comerciar con el Agente {objetivo_cercano.unique_id}, pero no llegamos a un acuerdo.", pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("No encuentro a nadie con quien comerciar ahora.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "MEJORAR_SEGURIDAD":
            exito = self.mejorar_seguridad()
            if exito:
                self.decir("🛡️ He invertido en mi seguridad personal. Me siento más protegido.", pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("Necesito más MundoCoins para mejorar mi protección.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "BUSCAR_INFO":
            # La información se obtiene en el cerebro, aquí la guardamos
            temas = ["clima", "noticias", "mercado"]
            tema = random.choice(temas)
            info = f"Dato sobre {tema} en el paso {self.modelo.paso_actual}"
            self.conocimientos[tema] = info
            self.ganar_experiencia("exploracion", 1)
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "COMPARTIR_INFO":
            if objetivo_cercano and self.conocimientos:
                tema = random.choice(list(self.conocimientos.keys()))
                info = self.conocimientos[tema]
                # El otro agente aprende
                objetivo_cercano.conocimientos[tema] = info
                self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("No tengo información valiosa que compartir ahora.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "PLANIFICAR":
            if objetivo_cercano:
                plan = {"con_quien": self.unique_id, "accion": "COOPERAR", "paso": self.modelo.paso_actual + 2}
                self.planes.append(plan)
                objetivo_cercano.planes.append(plan)
                self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("Planeo mejorar mi estrategia individual.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "DEBATIR":
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)
            if objetivo_cercano:
                # El debate aumenta la afinidad o competitividad
                self.interactuar(objetivo_cercano, "social", mensaje_enviado=mensaje)

        elif decision == "INVERTIR":
            monto = min(self.dinero * 0.2, 30) # Invierte el 20% de su dinero, máximo 30 MC
            exito = self.invertir(monto)
            if exito:
                self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)
            else:
                self.decir("He decidido no arriesgar mi capital por ahora.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "FORMAR_ALIANZA":
            if objetivo_cercano:
                # Intentar extraer términos del mensaje del LLM o usar uno por defecto
                terminos = None
                if "medicina" in mensaje.lower() and "dinero" in mensaje.lower():
                    terminos = {
                        "tipo": "intercambio",
                        "descripcion": "Medicina por MundoCoins",
                        "da": {"recurso": "medicina", "cant": 1},
                        "recibe": {"recurso": "dinero", "cant": 15}
                    }
                elif "seguridad" in mensaje.lower() or "protección" in mensaje.lower():
                    terminos = {
                        "tipo": "intercambio",
                        "descripcion": "Recursos por Seguridad",
                        "da": {"recurso": "recursos", "cant": 10},
                        "recibe": {"recurso": "seguridad", "cant": 0.1}
                    }
                
                exito = self.formar_alianza(objetivo_cercano, terminos=terminos)
                if exito:
                    self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)
                else:
                    self.decir(f"Ya tenemos un pacto activo o no pudimos negociar los términos.", pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)
            else:
                self.decir("Busco aliados estratégicos para el futuro.", pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)

        elif decision == "DESCANSAR":
            self.necesidades["descanso"] = max(0, self.necesidades["descanso"] - 5)
            self.necesidades["salud"] = min(10, self.necesidades["salud"] + 0.5)
            self.modelo.log(f"  💤 [ACCION] Agente {self.unique_id} descansa para recuperar energías.", categoria="state")
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)

        elif decision == "CURARSE":
            if self.inventario["medicina"] > 0:
                self.inventario["medicina"] -= 1
                self.necesidades["salud"] = min(10, self.necesidades["salud"] + 4)
                self.ganar_experiencia("medicina", 1)
                self.modelo.log(f"  🏥 [ACCION] Agente {self.unique_id} usó medicina. Salud restaurada.", categoria="state")
            else:
                self.modelo.log(f"  ⚠️ [ACCION] Agente {self.unique_id} intentó curarse pero no tiene medicinas.", categoria="state")
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)

        elif decision == "DIVERTIRSE":
            if self.inventario["ocio"] > 0:
                self.inventario["ocio"] -= 1
                self.necesidades["entretenimiento"] = max(0, self.necesidades["entretenimiento"] - 6)
                self.modelo.log(f"  🎮 [ACCION] Agente {self.unique_id} usó objetos de ocio. ¡Se siente genial!", categoria="state")
            else:
                self.necesidades["entretenimiento"] = max(0, self.necesidades["entretenimiento"] - 2) # Ocio básico sin objetos
                self.modelo.log(f"  🎭 [ACCION] Agente {self.unique_id} buscó entretenimiento básico.", categoria="state")
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)

        elif decision == "MOVER":
            pass # El movimiento ahora es parte del ciclo obligatorio del turno

        elif decision.startswith("CONSTRUIR:"):
            tipo_edif = decision.split(":")[1]
            exito, msg = self.modelo.construir_edificio(self, tipo_edif)
            if exito:
                self.decir(f"🏗️ ¡He construido un {tipo_edif}! {mensaje}", pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)
            else:
                self.decir(f"⚠️ Intenté construir un {tipo_edif} pero: {msg}", pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)

        elif decision == "GRADUARSE":
            # El mensaje del LLM debería contener la profesión deseada o la deducimos de su experiencia
            profesion_objetivo = None
            if "Médico" in str(mensaje): profesion_objetivo = "Médico"
            elif "Comerciante" in str(mensaje): profesion_objetivo = "Comerciante"
            elif "Guarda" in str(mensaje): profesion_objetivo = "Guarda"
            elif "Explorador" in str(mensaje): profesion_objetivo = "Explorador"
            
            if profesion_objetivo:
                exito, msg = self.graduarse(profesion_objetivo)
                if exito:
                    self.decir(f"🎓 {msg}", pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)
                else:
                    self.decir(f"⚠️ Intenté graduarme como {profesion_objetivo} pero: {msg}", pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)
            else:
                self.decir("Estoy considerando profesionalizarme, pero aún no decido el camino.", pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)

        elif decision == "PROPONER_LEY":
            # Extraer el texto de la ley del mensaje o pensamiento
            ley_texto = mensaje.replace("PROPONER_LEY:", "").strip()
            if not ley_texto: ley_texto = "Ley de Convivencia Social"
            exito, ley_id = self.proponer_ley(ley_texto)
            if exito:
                self.decir(f"📜 He propuesto una nueva ley: '{ley_texto}'. ¡Espero su apoyo! (ID: {ley_id})", pensamiento=pensamiento, para_grupo=True)
            else:
                self.decir("Intenté proponer una ley, pero no tengo facción.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "VOTAR":
            # El LLM debe indicar el ID de la ley y su voto
            import re
            ley_match = re.search(r'LEY-\d+', str(mensaje) + str(pensamiento))
            if ley_match:
                ley_id = ley_match.group(0)
                a_favor = "no" not in mensaje.lower() and "contra" not in mensaje.lower()
                exito = self.votar_ley(ley_id, a_favor)
                if exito:
                    voto_str = "A FAVOR" if a_favor else "EN CONTRA"
                    self.decir(f"🗳️ He votado {voto_str} en la propuesta {ley_id}.", pensamiento=pensamiento, para_grupo=True)
            else:
                self.decir("Quería votar, pero no encontré una propuesta clara.", pensamiento=pensamiento, privado_para=destinatario_id)

        elif decision == "EJECUTAR_CODIGO":
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)
            # El resultado ya se procesó en el cerebro y se incluyó en el mensaje/pensamiento

        # Lógica de respuesta a invitaciones
        if self.ultimo_mensaje_recibido and "INVITACION_GRUPO" in str(self.ultimo_mensaje_recibido.get('contenido')):
            emisor_id = self.ultimo_mensaje_recibido['emisor']
            # Aceptamos si:
            # 1. No tenemos grupo
            # 2. Tenemos afinidad positiva con el emisor (> 0.3)
            # 3. Somos amables o extrovertidos
            afinidad = self.memoria.obtener_fuerza(emisor_id)
            amabilidad = self.personalidad.get('amabilidad', 0.5)
            
            if self.grupo_id is None and (afinidad > 0.3 or amabilidad > 0.7):
                partes = self.ultimo_mensaje_recibido['contenido'].split(":")
                self.grupo_id = partes[1]
                self.rol = "Miembro"
                self.modelo.log(f"🤝 [UNION] Agente {self.unique_id} ha aceptado unirse a la Facción {self.grupo_id}.", categoria="social")
                self.decir(f"¡He aceptado la invitación! Me uno a la Facción {self.grupo_id} con entusiasmo.")
            else:
                self.decir(f"Agradezco la invitación, Agente {emisor_id}, pero por ahora seguiré mi propio camino.")
            self.ultimo_mensaje_recibido = None

        # --- REPOSICIONAMIENTO OBLIGATORIO POR TURNO ---
        if decision not in ["DESCANSAR", "CONSTRUIR", "GRADUARSE"]:
            dx, dy = 0, 0
            
            # 1. Lógica de Cohesión Grupal (Patrullas)
            if self.grupo_id:
                aliados = [a for a in self.modelo.agentes if a.grupo_id == self.grupo_id and a.unique_id != self.unique_id]
                if aliados:
                    # Encontrar al aliado más cercano
                    mas_cercano = min(aliados, key=lambda a: abs(a.x - self.x) + abs(a.y - self.y))
                    dist = abs(mas_cercano.x - self.x) + abs(mas_cercano.y - self.y)
                    
                    if dist > 2: # Si están lejos, ir hacia ellos (cohesión)
                        dx = 1 if mas_cercano.x > self.x else (-1 if mas_cercano.x < self.x else 0)
                        dy = 1 if mas_cercano.y > self.y else (-1 if mas_cercano.y < self.y else 0)
                    else: # Si están cerca, moverse aleatoriamente pero sin alejarse mucho
                        dx = random.choice([-1, 0, 1])
                        dy = random.choice([-1, 0, 1])
                else:
                    dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
            else:
                # 2. Movimiento Errante (Agentes Literales / Sin Grupo)
                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
            
            # Aplicar movimiento con seguridad
            prob_fallo = 0.6 if self.modelo.weather == "storm" else 0.05
            
            if random.random() > prob_fallo:
                nx = max(0, min(self.modelo.mapa_size - 1, self.x + dx))
                ny = max(0, min(self.modelo.mapa_size - 1, self.y + dy))
                
                # Evitar agua y respetar fronteras si es posible
                if self.modelo.mapa[nx][ny].terrain_type != "water":
                    self.x, self.y = nx, ny

        # --- DETECCIÓN DE ENCUENTROS CON OTRAS FACCIONES ---
        if self.grupo_id:
            vecinos = [a for a in self.modelo.agentes if abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1 and a.unique_id != self.unique_id]
            for v in vecinos:
                if v.grupo_id and v.grupo_id != self.grupo_id:
                    # Probabilidad pequeña por paso para no saturar la diplomacia
                    if random.random() < 0.2:
                        self.modelo.gestionar_encuentro_facciones(self, v)

        self.actualizar_estado()

class ModeloRelacional:
    def __init__(self, num_agentes=10, log_callback=None, user_id=None):
        self.num_agentes = num_agentes
        self.log_callback = log_callback
        self.user_id = user_id
        self.paso_actual = 0
        
        # Conectar herramientas con el sistema de logs del modelo
        if self.log_callback:
            herramientas.log_callback = self.log
            
        self.objetivos_grupos = {}
        self.precio_recurso_actual = 2.0 # Precio base global
        
        # --- SISTEMA ECONÓMICO GLOBAL ---
        self.economia = {
            "indice_bursatil": 1000.0, # Base 1000
            "historial_indice": [1000.0],
            "total_dinero": 0.0,
            "inversiones_activas": 0,
            "volumen_transacciones": 0.0
        }
        self.agentes = []
        self.agentes_cargados = False

        self.historial_relaciones = []
        self.historial_grupos = []
        self.colores_paleta = [
            "#ff1744", "#d500f9", "#2979ff", "#00e5ff", "#00e676", 
            "#ffea00", "#ff9100", "#ff3d00", "#76ff03", "#f50057",
            "#651fff", "#3d5afe", "#00b0ff", "#00b8d4", "#1de9b6"
        ]
        self.datos = [] # Mantener para compatibilidad con visualizar_resultados
        self.relaciones_grupos = {} # {(id1, id2): afinidad}
        self.historial_logs = [] # [{mensaje, categoria, ...}]
        
        # --- SISTEMA POLÍTICO ---
        self.leyes_globales = [] # Lista de leyes activas en todo el mundo
        self.facciones_leyes = {} # {grupo_id: [leyes]}
        self.grupos_creados_este_paso = 0 # Límite de 2 por turno
        
        # --- PERSISTENCIA POSTGRESQL ---
        self.db = DatabaseManager()
        self.db_active = self.db.connect()
        
        # --- SISTEMA DE INFRAESTRUCTURA ---
        self.infraestructura = [] # Lista de dicts: {"tipo": T, "grupo_id": G, "pos": P, "paso_creacion": S}
        
        # --- SISTEMA DE CIVILIZACIONES Y TERRITORIOS ---
        self.civilizaciones = {} # {civ_id: Civilizacion}
        self.mapa_size = 20
        # self.mapa = [[None for _ in range(self.mapa_size)] for _ in range(self.mapa_size)] # Matriz de civ_id
        self.mapa = self.generar_mapa() # Matriz de objetos Tile
        
        # --- SISTEMA DE CLIMA ---
        self.weather = WeatherType.SUNNY
        self.weather_timer = 0
        self.weather_duration = 20
        
        # --- MUNDO ATRIBUTOS ---
        self.lore = ""
        self.seed = ""
        self.eventos_activos = []
        
        # Cargar estado previo si existe
        self.cargar_estado()

    def generar_mapa(self):
        """Genera un mapa procedural básico con diferentes terrenos."""
        nuevo_mapa = [[None for _ in range(self.mapa_size)] for _ in range(self.mapa_size)]
        
        # Generación simple basada en ruido aleatorio (se puede mejorar con Perlin Noise)
        for x in range(self.mapa_size):
            for y in range(self.mapa_size):
                r = random.random()
                tipo = TerrainType.GRASS
                
                # Clusters simples
                if 0.4 < r < 0.6: tipo = TerrainType.FOREST
                elif 0.85 < r < 0.95: tipo = TerrainType.MOUNTAIN
                elif r >= 0.95: tipo = TerrainType.WATER
                elif r < 0.05: tipo = TerrainType.DESERT
                
                tile = Tile(x, y, tipo)
                
                # Recursos iniciales según terreno
                if tipo == TerrainType.FOREST:
                    tile.resource_node = {"type": "wood", "amount": random.randint(50, 200)}
                elif tipo == TerrainType.MOUNTAIN:
                    tile.resource_node = {"type": "stone", "amount": random.randint(50, 200)}
                elif tipo == TerrainType.GRASS and random.random() < 0.2:
                    tile.resource_node = {"type": "food", "amount": random.randint(20, 100)}
                
                nuevo_mapa[x][y] = tile
        
        return nuevo_mapa

    def actualizar_clima(self):
        """Ciclo de clima dinámico."""
        self.weather_timer += 1
        if self.weather_timer >= self.weather_duration:
            self.weather_timer = 0
            # Cambiar clima
            climas = [WeatherType.SUNNY, WeatherType.RAINY, WeatherType.STORM, WeatherType.FOGGY, WeatherType.HEATWAVE]
            pesos = [0.5, 0.2, 0.1, 0.1, 0.1] # Mayor probabilidad de sol
            self.weather = random.choices(climas, weights=pesos, k=1)[0]
            self.weather_duration = random.randint(10, 30)
            
            efecto = ""
            if self.weather == WeatherType.STORM: efecto = "¡Tormenta severa! Movimiento difícil."
            elif self.weather == WeatherType.RAINY: efecto = "Lluvia. Crecimiento de cultivos."
            elif self.weather == WeatherType.HEATWAVE: efecto = "Ola de calor. Mayor consumo de agua."
            
            self.log(f"🌦️ [CLIMA] El clima ha cambiado a: {self.weather.upper()}. {efecto}", categoria="ambiente")

    def actualizar_territorios(self):
        """Actualiza la propiedad de las celdas del mapa basada en la presencia de agentes."""
        # Resetear mapa (opcional, o podemos hacerlo gradual)
        # Por ahora, la celda pertenece a la civilización con más agentes en ella
        for x in range(self.mapa_size):
            for y in range(self.mapa_size):
                agentes_en_celda = [a for a in self.agentes if a.x == x and a.y == y]
                if agentes_en_celda:
                    # Contar agentes por civilización
                    conteos = {}
                    for a in agentes_en_celda:
                        if a.civilizacion_id:
                            conteos[a.civilizacion_id] = conteos.get(a.civilizacion_id, 0) + 1
                    
                    if conteos:
                        ganador = max(conteos, key=conteos.get)
                        # self.mapa[x][y] = ganador # OLD
                        self.mapa[x][y].owner_civ_id = ganador # NEW
        
        # Actualizar la lista de territorio en cada civilización
        for civ in self.civilizaciones.values():
            civ.territorio = []
            for x in range(self.mapa_size):
                for y in range(self.mapa_size):
                    if self.mapa[x][y].owner_civ_id == civ.id:
                        civ.territorio.append((x, y))

    def step(self):
        """Avanza un paso en la simulación."""
        self.paso_actual += 1
        self.grupos_creados_este_paso = 0
        
        # Actualizar territorios
        self.actualizar_territorios()
        
        # Actualizar clima
        self.actualizar_clima()
        
        # --- PROCESAR EFECTOS DE EDIFICIOS ---
        for edif in self.infraestructura:
            tipo = edif["tipo"]
            x, y = edif["x"], edif["y"]
            
            # Granjas: Generan recursos en el tile
            if tipo == "Granja":
                tile = self.mapa[x][y]
                if not tile.resource_node:
                    tile.resource_node = {"type": "food", "amount": 20}
                else:
                    tile.resource_node["amount"] = min(200, tile.resource_node["amount"] + 10)
            
            # Hospitales / Centros: Afectan agentes cercanos
            agentes_cerca = [a for a in self.agentes if abs(a.x - x) <= 1 and abs(a.y - y) <= 1]
            for a in agentes_cerca:
                if tipo == "Hospital":
                    a.necesidades["salud"] = max(10, a.necesidades["salud"] + 0.5)
                elif tipo == "Centro de Descanso":
                    a.necesidades["descanso"] = max(0, a.necesidades["descanso"] - 1.0)
                elif tipo == "Centro de Recarga":
                    a.recursos += 5
                elif tipo == "Centro Comunitario":
                    a.necesidades["social"] = max(0, a.necesidades["social"] - 0.8)
                elif tipo == "Universidad":
                    # XP pasiva: 30% de probabilidad de ganar XP en un área aleatoria
                    if random.random() < 0.3:
                        area = random.choice(["medicina", "comercio", "combate", "exploracion", "agricultura", "ingenieria"])
                        a.ganar_experiencia(area, 1)
                        if a.unique_id == "42": # Ejemplo para un log específico de estudio
                            self.log(f"📖 Agente {a.unique_id} está estudiando {area} en la Universidad.", categoria="sistema")

        # Aplicar efectos de infraestructura (antigua lógica, se mantiene para otros tipos de edificios)
        for edif in self.infraestructura:
            beneficiarios = [a for a in self.agentes if a.grupo_id == edif["grupo_id"]]
            for b in beneficiarios:
                if edif["tipo"] == "Hospital":
                    b.necesidades["salud"] = min(10.0, b.necesidades["salud"] + 0.5)
                elif edif["tipo"] == "Comedor":
                    b.necesidades["alimento"] = max(0.0, b.necesidades["alimento"] - 0.2)
                elif edif["tipo"] == "Centro de Ocio":
                    b.necesidades["entretenimiento"] = max(0.0, b.necesidades["entretenimiento"] - 0.3)

        # Actualizar agentes
        for agente in self.agentes:
            agente.actualizar_estado()
            agente.step()
        
        # Economía global
        self.actualizar_economia()
        
        # Guardar estado si la DB está activa
        if self.db_active and self.user_id:
            # Convertir claves de tupla a string para JSON
            rel_str = {f"{k[0]}:{k[1]}": v for k, v in self.relaciones_grupos.items()}
            self.db.save_world_state(self.user_id, self.paso_actual, self.lore, self.seed, self.economia, rel_str)
            for a in self.agentes:
                self.db.save_agent(a, self.user_id)
        
        # Guardar en archivo cada 10 pasos (respaldo)
        if self.paso_actual % 10 == 0:
            self.guardar_estado()

    def construir_edificio(self, agente, tipo):
        """Permite a un agente construir una infraestructura basada en sus logros y experiencia."""
        config_edificios = {
            "Hospital": {
                "costo": {"dinero": 150, "recursos": 80},
                "requisito": lambda a: a.profesion == "Médico" or a.experiencia["medicina"] >= 10,
                "efecto": "Cura agentes cercanos cada turno."
            },
            "Granja": {
                "costo": {"dinero": 80, "recursos": 50},
                "requisito": lambda a: a.experiencia["agricultura"] >= 5,
                "efecto": "Genera recursos de alimento en el tile."
            },
            "Centro de Recarga": {
                "costo": {"dinero": 120, "recursos": 100},
                "requisito": lambda a: a.experiencia["ingenieria"] >= 8,
                "efecto": "Restaura energía/recursos rápidamente."
            },
            "Centro de Descanso": {
                "costo": {"dinero": 70, "recursos": 40},
                "requisito": lambda a: True, # Básico
                "efecto": "Reduce el estrés y la necesidad de descanso."
            },
            "Centro Comunitario": {
                "costo": {"dinero": 100, "recursos": 60},
                "requisito": lambda a: a.personalidad.get("amabilidad", 0.5) > 0.7,
                "efecto": "Mejora las relaciones sociales en el área."
            },
            "Comisaría": {
                "costo": {"dinero": 110, "recursos": 70},
                "requisito": lambda a: a.profesion == "Guarda" or a.experiencia["combate"] >= 7,
                "efecto": "Reduce la probabilidad de robos y aumenta la seguridad."
            },
            "Universidad": {
                "costo": {"dinero": 300, "recursos": 200},
                "requisito": lambda a: a.personalidad.get("curiosidad", 0.5) > 0.8 and a.experiencia["ingenieria"] >= 5,
                "efecto": "Permite graduarse a los agentes y otorga XP pasiva."
            }
        }
        
        if tipo not in config_edificios:
            # Posibilidad de "inventar" un edificio si tiene alta curiosidad e ingeniería
            if agente.experiencia["ingenieria"] >= 5 and agente.personalidad.get("curiosidad", 0.5) > 0.8:
                config_edificios[tipo] = {
                    "costo": {"dinero": 200, "recursos": 150},
                    "requisito": lambda a: True,
                    "efecto": "Edificio experimental con efectos únicos."
                }
            else:
                return False, "Tipo de edificio no válido o requisitos de invención no cumplidos."
        
        tile = self.mapa[agente.x][agente.y]
        if tile.buildings:
            return False, "Ya hay un edificio en esta ubicación."
            
        if tile.terrain_type in [TerrainType.WATER, TerrainType.MOUNTAIN] and tipo != "Puerto":
            return False, "No se puede construir en este terreno."
        
        config = config_edificios[tipo]
        if not config["requisito"](agente):
            return False, f"No cumples los requisitos (XP/Profesión) para construir {tipo}."

        costo = config["costo"]
        if agente.dinero >= costo["dinero"] and agente.recursos >= costo["recursos"]:
            agente.dinero -= costo["dinero"]
            agente.recursos -= costo["recursos"]
            
            nuevo_edif = {
                "id": f"EDIF-{len(self.infraestructura) + 1}",
                "tipo": tipo,
                "grupo_id": agente.grupo_id,
                "constructor": agente.unique_id,
                "paso_creacion": self.paso_actual,
                "x": agente.x,
                "y": agente.y
            }
            self.infraestructura.append(nuevo_edif)
            tile.buildings.append(nuevo_edif) # Add to tile
            
            self.log(f"🏗️ [CONSTRUCCION] Agente {agente.unique_id} ha construido un {tipo} en ({agente.x}, {agente.y})!", categoria="sistema")
            return True, f"¡{tipo} construido con éxito!"
        
        return False, "No tienes suficientes recursos o dinero."
        
    def set_lore_and_seed(self, lore, seed):
        self.lore = lore
        self.seed = seed
        self.log(f"🌍 [MUNDO] Lore actualizado: {lore[:50]}...", categoria="sistema")

    def get_agent_by_id(self, agent_id):
        """Busca un agente por su ID único."""
        return next((a for a in self.agentes if str(a.unique_id) == str(agent_id)), None)

    def trigger_event(self, tipo, descripcion, duracion=5, impacto=None):
        evento = {
            "tipo": tipo,
            "descripcion": descripcion,
            "paso_inicio": self.paso_actual,
            "pasos_restantes": duracion,
            "impacto": impacto or {}
        }
        self.eventos_activos.append(evento)
        self.log(f"🌪️ [EVENTO GLOBAL] ¡Ha comenzado: {tipo}! {descripcion}", categoria="sistema")
        
        # Guardar en DB si está activa
        if self.db_active:
            query = "INSERT INTO eventos_globales (tipo, descripcion, paso_inicio, duracion, impacto) VALUES (%s, %s, %s, %s, %s)"
            self.db.execute(query, (tipo, descripcion, self.paso_actual, duracion, Json(impacto or {})))

    def spawn_agent(self, config=None):
        """Spawnea un nuevo agente. Puede recibir un objeto AgentConfig o un diccionario."""
        nuevo_id = f"A{len(self.agentes)}"
        
        personalidad_final = None
        recursos_init = 0.0
        dinero_init = 100.0
        pos_init = None

        if config:
            # Manejar tanto objetos Pydantic como diccionarios
            if hasattr(config, "model_dump"):
                cfg_dict = config.model_dump()
            elif isinstance(config, dict):
                cfg_dict = config
            else:
                cfg_dict = vars(config) if hasattr(config, "__dict__") else {}

            personalidad_final = cfg_dict.get("personality")
            recursos_init = cfg_dict.get("resources", 0.0)
            dinero_init = cfg_dict.get("money", 100.0)
            pos_init = cfg_dict.get("position")

        nuevo_agente = Agente(nuevo_id, self, personalidad=personalidad_final)
        nuevo_agente.recursos = recursos_init
        nuevo_agente.dinero = dinero_init
        
        if pos_init and "x" in pos_init and "y" in pos_init:
            nuevo_agente.x = pos_init["x"]
            nuevo_agente.y = pos_init["y"]
            
        self.agentes.append(nuevo_agente)
        self.log(f"✨ [SPAWNER] Nuevo agente {nuevo_id} ha entrado al mundo.", categoria="sistema")
        
        if self.db_active:
            self.db.save_agent(nuevo_agente, self.user_id)
            
        return nuevo_agente

        # Si no se cargaron agentes (primera vez), los creamos
        if not self.agentes_cargados:
            self.agentes = [Agente(i, self) for i in range(self.num_agentes)]
            self.agentes_cargados = True
        else:
            self.log(f"💾 [SISTEMA] Continuando simulación con {len(self.agentes)} agentes.", categoria="sistema")

    def gestionar_encuentro_facciones(self, agente_a, agente_b):
        """Gestiona la interacción cuando dos agentes de distintas facciones se encuentran."""
        id_a, id_b = agente_a.grupo_id, agente_b.grupo_id
        if not id_a or not id_b or id_a == id_b: return
        
        # Clave única para la relación entre estos dos grupos
        rel_key = tuple(sorted([id_a, id_b]))
        if rel_key not in self.relaciones_grupos:
            self.relaciones_grupos[rel_key] = 0.5 # Neutral inicial
            
        afinidad = self.relaciones_grupos[rel_key]
        
        # Probabilidad de cooperación basada en afinidad y personalidades
        prob_cooperar = afinidad * (agente_a.personalidad["amabilidad"] + agente_b.personalidad["amabilidad"]) / 2
        
        if random.random() < prob_cooperar:
            # --- COOPERACIÓN: Gesto de Buena Voluntad ---
            tipo_ayuda = random.choice(["recursos", "salud", "informacion"])
            if tipo_ayuda == "recursos" and agente_a.recursos > 20:
                donado = 10
                agente_a.recursos -= donado
                agente_b.recursos += donado
                self.log(f"🤝 [DIPLOMACIA] Gesto de paz: {agente_a.unique_id} ({id_a}) donó recursos a {agente_b.unique_id} ({id_b}).", categoria="social")
                self.relaciones_grupos[rel_key] = min(1.0, afinidad + 0.05)
            elif tipo_ayuda == "salud" and agente_a.inventario["medicina"] > 0:
                agente_a.inventario["medicina"] -= 1
                agente_b.necesidades["salud"] = min(10, agente_b.necesidades["salud"] + 2)
                self.log(f"💊 [DIPLOMACIA] Auxilio médico: {agente_a.unique_id} ({id_a}) curó a un miembro de {id_b}.", categoria="social")
                self.relaciones_grupos[rel_key] = min(1.0, afinidad + 0.1)
        else:
            # --- TENSIÓN: Competencia por territorio ---
            if random.random() < 0.3:
                self.log(f"⚠️ [TENSION] Encuentro frío entre patrullas de {id_a} y {id_b} en zona fronteriza.", categoria="social")
                self.relaciones_grupos[rel_key] = max(0.0, afinidad - 0.02)

    def log(self, mensaje, categoria="info", subtitulos=None, tts_text=None, pensamiento=None, privado_para=None):
        """Envía un log al callback o a la terminal y lo guarda en el historial."""
        log_entry = {
            "paso": self.paso_actual,
            "mensaje": mensaje,
            "categoria": categoria,
            "subtitulos": subtitulos,
            "tts_text": tts_text,
            "pensamiento": pensamiento,
            "privado_para": privado_para
        }
        self.historial_logs.append(log_entry)
        if len(self.historial_logs) > 100: # Mantener solo los últimos 100
            self.historial_logs.pop(0)

        if self.log_callback:
            self.log_callback(mensaje, categoria, subtitulos, tts_text, pensamiento, privado_para)
        else:
            print(mensaje)
            if subtitulos:
                print(f"             └─ [Subtítulos: {subtitulos}]")

    def actualizar_relacion_grupal(self, g1, g2, cambio):
        """Actualiza la afinidad entre dos facciones."""
        if not g1 or not g2 or g1 == g2: return
        
        pair = tuple(sorted([str(g1), str(g2)]))
        actual = self.relaciones_grupos.get(pair, 0.0)
        nueva = max(-1.0, min(1.0, actual + cambio))
        self.relaciones_grupos[pair] = nueva
        
        if actual >= 0 and nueva < 0:
            self.log(f"⚠️ [DIPLOMACIA] Las facciones {g1} y {g2} han entrado en CONFLICTO.", categoria="sistema")
        elif actual < 0 and nueva >= 0:
            self.log(f"🕊️ [DIPLOMACIA] Las facciones {g1} y {g2} han firmado la PAZ.", categoria="sistema")

    def step(self):
        # Actualizar economía global
        total_dinero = sum(a.dinero for a in self.agentes)
        inversiones_activas = sum(len(a.inversiones) for a in self.agentes)
        
        # El índice bursátil varía según el dinero total y las inversiones
        variacion = (total_dinero - self.economia["total_dinero"]) * 0.1 if self.economia["total_dinero"] > 0 else 0
        self.economia["indice_bursatil"] += variacion + (inversiones_activas * 0.5)
        self.economia["total_dinero"] = total_dinero
        self.economia["inversiones_activas"] = inversiones_activas
        self.economia["historial_indice"].append(round(self.economia["indice_bursatil"], 2))
        if len(self.economia["historial_indice"]) > 50:
            self.economia["historial_indice"].pop(0)

        self.paso_actual += 1
        self.grupos_creados_este_paso = 0 # Resetear contador de grupos
        self.log(f"\n================ PASO {self.paso_actual} ================", categoria="paso")
        
        # Guardar estado automáticamente en cada paso
        self.guardar_estado()
        
        # Lógica de formación de grupos (cada 10 pasos)
        if self.paso_actual % 10 == 0:
            self.log("📢 [SISTEMA] Evaluando formación de grupos sociales...", categoria="sistema")
            self.formar_grupos()
            self.asignar_roles_consenso()

        # Ejecutar el paso de cada agente
        self.ejecutar_paso_agentes()

        # Registrar métricas globales
        if len(self.agentes) == 0:
            # Si no hay agentes, no calcular métricas
            return
            
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
            "num_grupos": len(set(a.grupo_id for a in self.agentes if a.grupo_id is not None)),
            "gini": self.calcular_gini(),
            "felicidad": self.calcular_felicidad_promedio(),
            "conflictos": self.track_conflictos()
        })

    def calcular_gini(self):
        """Calcula el coeficiente de Gini para la desigualdad de recursos."""
        recursos = sorted([a.recursos + a.dinero for a in self.agentes])
        n = len(recursos)
        if n == 0 or sum(recursos) == 0: return 0
        
        # Fórmula de Gini: (2 * sum(i * x_i) / (n * sum(x_i))) - (n + 1) / n
        suma_ponderada = sum((i + 1) * x for i, x in enumerate(recursos))
        suma_total = sum(recursos)
        gini = (2 * suma_ponderada / (n * suma_total)) - (n + 1) / n
        return round(max(0, min(1, gini)), 3)

    def calcular_felicidad_promedio(self):
        """Calcula la felicidad promedio basada en la satisfacción de necesidades."""
        felicidades = []
        for a in self.agentes:
            # Felicidad = 10 - promedio de necesidades (0-10)
            nec = a.necesidades
            promedio_nec = sum([nec.get(k, 0) for k in ["alimento", "social", "seguridad", "descanso", "entretenimiento"]]) / 5
            felicidad = max(0, 10 - promedio_nec)
            felicidades.append(felicidad)
        return round(sum(felicidades) / len(felicidades), 2) if felicidades else 0

    def track_conflictos(self):
        """Retorna la tasa de conflictos reciente (últimos logs)."""
        conflictos = [l for l in self.historial_logs[-20:] if l['categoria'] == 'conflict']
        return len(conflictos)

    def ejecutar_paso_agentes(self):
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
                    otro = self.get_agent_by_id(id_amigo)
                    if otro and otro.grupo_id is not None:
                        agente.grupo_id = otro.grupo_id
                        break
                else:
                    # Crear nuevo grupo si tiene al menos un amigo y hay cupo
                    if amigos and self.grupos_creados_este_paso < 2:
                        nuevo_id = f"G{agente.unique_id}"
                        agente.grupo_id = nuevo_id
                        self.grupos_creados_este_paso += 1
                        for id_amigo in amigos:
                            amigo_obj = self.get_agent_by_id(id_amigo)
                            if amigo_obj:
                                amigo_obj.grupo_id = nuevo_id

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

    def guardar_estado(self):
        """Guarda el estado actual en JSON (fallback) y PostgreSQL."""
        # 1. Guardar en JSON (Fallback)
        datos_json = {
            "paso_actual": self.paso_actual,
            "objetivos_grupos": self.objetivos_grupos,
            "datos_estadisticos": self.datos,
            "agentes": []
        }
        for a in self.agentes:
            datos_json["agentes"].append({
                "id": a.unique_id,
                "recursos": a.recursos,
                "dinero": a.dinero,
                "necesidades": a.necesidades,
                "personalidad": a.personalidad,
                "rol": a.rol,
                "grupo_id": a.grupo_id,
                "rango": a.rango,
                "conocimientos": a.conocimientos,
                "planes": a.planes,
                "inversiones": a.inversiones,
                "alianzas": a.alianzas,
                "tratados": a.tratados,
                "profesion": a.profesion,
                "experiencia": a.experiencia,
                "hitos": a.hitos,
                "memoria_grafica": a.memoria.exportar_datos()
            })
        
        datos_json["economia"] = self.economia
        datos_json["relaciones_grupos"] = {f"{k[0]}-{k[1]}": v for k, v in self.relaciones_grupos.items()}
        datos_json["historial_logs"] = self.historial_logs
        datos_json["infraestructura"] = self.infraestructura
        # Serializar mapa de objetos Tile
        datos_json["mapa"] = [[t.to_dict() for t in row] for row in self.mapa]
        datos_json["civilizaciones"] = {k: {
            "nombre": v.nombre,
            "color": v.color,
            "user_id": v.user_id,
            "recursos_globales": v.recursos_globales,
            "territorio": v.territorio
        } for k, v in self.civilizaciones.items()}
        
        with open("estado_simulacion.json", "w") as f:
            json.dump(datos_json, f, indent=4)
        
        # 2. Guardar en PostgreSQL (Si está activo)
        if self.db_active and self.user_id:
            try:
                # Convertir claves de tupla a string para JSON
                rel_str = {f"{k[0]}:{k[1]}": v for k, v in self.relaciones_grupos.items()}
                
                # Guardar estado del mundo con user_id y relaciones persistentes
                self.db.save_world_state(self.user_id, self.paso_actual, getattr(self, 'lore', ''), getattr(self, 'seed', ''), self.economia, rel_str)
                
                # Guardar civilizaciones
                for civ in self.civilizaciones.values():
                    self.db.save_civilization(civ)
                
                # Guardar agentes y sus memorias
                for a in self.agentes:
                    self.db.save_agent(a, self.user_id)
                    # Guardar relaciones de memoria
                    mem_data = a.memoria.exportar_datos()
                    for edge in mem_data.get('aristas', []):
                        # Solo guardamos relaciones que parten del agente
                        if edge['u'] == a.unique_id:
                            self.db.save_memory(a.unique_id, edge['v'], edge['data'], civ_user_id)
                
                logger.info(f"💾 [DB] Estado guardado en PostgreSQL para {civ_user_id} (Paso {self.paso_actual})")
            except Exception as e:
                logger.error(f"❌ Error guardando en DB: {e}")

    def cargar_estado(self):
        """Carga el estado desde PostgreSQL (prioridad) o JSON (fallback)."""
        # 1. Intentar cargar desde PostgreSQL
        if self.db_active:
            try:
                # Obtener el user_id (podría venir de la sesión si esto fuera asíncrono, 
                # pero aquí intentamos deducirlo o usar uno por defecto temporal)
                target_user_id = self.user_id or "USER-DEFAULT"
                world_state = self.db.get_world_state(target_user_id)
                if world_state:
                    self.paso_actual, self.lore, self.seed, precio, indice, total_dinero, rel_data = world_state
                    self.economia["indice_bursatil"] = indice
                    self.economia["total_dinero"] = total_dinero
                    self.precio_recurso_actual = precio
                    
                    # Restaurar relaciones de grupos (convertir string keys back to tuples)
                    if rel_data:
                        self.relaciones_grupos = {}
                        for k, v in rel_data.items():
                            parts = k.split(":")
                            if len(parts) == 2:
                                self.relaciones_grupos[tuple(parts)] = v
                    
                    agents_data = self.db.get_agents(target_user_id)
                    self.agentes = []
                    for row in agents_data:
                        # row mapping based on schema: id, recursos, dinero, grupo_id, rol, profesion, rango, reputacion, personalidad, necesidades, experiencia, conocimientos, inventario, hitos, historial_etico, timestamp, civilizacion_id
                        a_id, rec, din, g_id, rol, prof, ran, rep, pers, nec, exp, con, inv, hitos, etico, _, civ_id = row
                        a = Agente(a_id, self)
                        a.recursos = rec
                        a.dinero = din
                        a.grupo_id = g_id
                        a.rol = rol
                        a.profesion = prof
                        a.rango = ran
                        a.reputacion = rep
                        a.personalidad = pers
                        a.necesidades = nec
                        a.experiencia = exp
                        a.conocimientos = con
                        a.inventario = inv
                        a.hitos = hitos
                        a.historial_etico = etico
                        a.civilizacion_id = civ_id
                        
                        # Cargar memorias
                        memories = self.db.get_memories(a_id, target_user_id)
                        mem_dict = {"nodos": [{"id": a_id, "data": {"tipo": "yo"}}], "aristas": []}
                        for m_row in memories:
                            target_id, tipo, fuerza, rec_v, grp_v = m_row
                            mem_dict["nodos"].append({"id": target_id, "data": {"tipo": tipo, "recursos_vistos": rec_v, "grupo": grp_v}})
                            mem_dict["aristas"].append({"u": a_id, "v": target_id, "data": {"tipo": tipo, "fuerza": fuerza}})
                        
                        a.memoria.cargar_datos(mem_dict)
                        self.agentes.append(a)
                    
                    self.agentes_cargados = True
                    logger.info(f"💾 [DB] Estado cargado desde PostgreSQL (Paso {self.paso_actual})")
                    return
            except Exception as e:
                logger.error(f"❌ Error cargando desde DB: {e}")

        # 2. Fallback a JSON
        if os.path.exists("estado_simulacion.json"):
            try:
                with open("estado_simulacion.json", "r") as f:
                    datos_json = json.load(f) # Renamed 'datos' to 'datos_json' for clarity
                
                self.paso_actual = datos_json.get("paso_actual", 0)
                self.objetivos_grupos = datos_json.get("objetivos_grupos", {})
                self.datos = datos_json.get("datos_estadisticos", [])
                self.economia = datos_json.get("economia", self.economia)
                self.economia = datos_json.get("economia", self.economia)
                self.historial_logs = datos_json.get("historial_logs", [])
                self.infraestructura = datos_json.get("infraestructura", [])
                
                # Cargar mapa
                mapa_data = datos_json.get("mapa")
                if mapa_data and isinstance(mapa_data[0][0], dict):
                    # Cargar desde dicts
                    for x in range(self.mapa_size):
                        for y in range(self.mapa_size):
                            d = mapa_data[x][y]
                            tile = Tile(d["x"], d["y"], d["terrain"])
                            tile.resource_node = d.get("resource")
                            tile.owner_civ_id = d.get("owner")
                            tile.buildings = d.get("buildings", [])
                            self.mapa[x][y] = tile
                else:
                    # Regenerar si es formato antiguo o no existe
                    self.mapa = self.generar_mapa()
                
                civs_data = datos_json.get("civilizaciones", {})
                for civ_id, data in civs_data.items():
                    civ = Civilizacion(civ_id, data["nombre"], data["color"], data.get("user_id"))
                    civ.recursos_globales = data.get("recursos_globales", 0.0)
                    civ.territorio = data.get("territorio", [])
                    self.civilizaciones[civ_id] = civ

                self.agentes = []
                for a_data in datos_json.get("agentes", []):
                    a = Agente(a_data["id"], self)
                    a.recursos = a_data.get("recursos", 10.0)
                    a.dinero = a_data.get("dinero", 100.0)
                    
                    # Cargar necesidades con valores por defecto para evitar KeyErrors
                    necesidades_base = {
                        "alimento": 0.0, "social": 0.0, "seguridad": 0.0, 
                        "descanso": 0.0, "entretenimiento": 0.0, "salud": 10.0
                    }
                    a.necesidades = {**necesidades_base, **a_data.get("necesidades", {})}
                    
                    # Cargar personalidad con valores por defecto
                    personalidad_base = {
                        "extroversión": 0.5, "amabilidad": 0.5, "competitividad": 0.5,
                        "curiosidad": 0.5, "lealtad": 0.5, "prudencia": 0.5
                    }
                    a.personalidad = {**personalidad_base, **a_data.get("personalidad", {})}
                    
                    a.rol = a_data.get("rol", "Ciudadano")
                    a.grupo_id = a_data.get("grupo_id")
                    a.rango = a_data.get("rango", 1.0)
                    a.conocimientos = a_data.get("conocimientos", {})
                    a.planes = a_data.get("planes", [])
                    a.inversiones = a_data.get("inversiones", [])
                    a.alianzas = a_data.get("alianzas", [])
                    a.tratados = a_data.get("tratados", [])
                    a.profesion = a_data.get("profesion")
                    a.experiencia = a_data.get("experiencia", {"medicina": 0, "comercio": 0, "combate": 0, "exploracion": 0})
                    a.hitos = a_data.get("hitos", [])
                    
                    if "memoria_grafica" in a_data:
                        a.memoria.cargar_datos(a_data["memoria_grafica"])
                    self.agentes.append(a)
                
                self.economia = datos_json.get("economia", self.economia)
                self.historial_logs = datos_json.get("historial_logs", [])
                
                # Cargar relaciones grupales (convertir keys de string a tupla)
                rel_data = datos_json.get("relaciones_grupos", {})
                for k, v in rel_data.items():
                    try:
                        p1, p2 = k.split("-")
                        self.relaciones_grupos[(p1, p2)] = v
                    except: pass

                self.agentes_cargados = True
                self.log(f"💾 [SISTEMA] Estado cargado desde JSON (Paso {self.paso_actual}).", categoria="sistema")
            except Exception as e:
                self.log(f"⚠️ [ERROR] No se pudo cargar el estado desde JSON: {e}", categoria="sistema")
                self.agentes_cargados = False

    def asignar_roles_consenso(self):
        """Los grupos negocian roles internos basados en méritos y personalidad."""
        grupos = {}
        for a in self.agentes:
            if a.grupo_id is not None:
                if a.grupo_id not in grupos: grupos[a.grupo_id] = []
                grupos[a.grupo_id].append(a)
        
        for g_id, miembros in grupos.items():
            if len(miembros) < 2: continue
            
            # --- FASE DE DEBATE PÚBLICO ---
            self.log(f"🏛️ [ASAMBLEA FACCIÓN {g_id}] Se inicia el debate democrático...", categoria="consenso")
            
            ids_miembros = [m.unique_id for m in miembros]
            for m in miembros:
                # Cada agente expresa su opinión sobre el liderazgo
                argumento, pensamiento = cerebro_llm.generar_debate_consenso(m, ids_miembros, fase="liderazgo")
                m.decir(f"🗣️ [DEBATE ASAMBLEA] {argumento}", pensamiento=pensamiento, para_grupo=True)
            
            # 1. Elegir Líder (Democrática basada en Rango y Amabilidad)
            # El que tenga mayor (Rango * 0.7 + Amabilidad * 0.3) es el candidato ideal
            miembros.sort(key=lambda x: (x.rango * 0.7 + x.personalidad.get('amabilidad', 0.5) * 0.3), reverse=True)
            lider = miembros[0]
            
            for m in miembros:
                if m == lider:
                    m.rol = "Líder"
                else:
                    # Asignación de roles secundarios por personalidad
                    p = m.personalidad
                    if p.get('competitividad', 0) > 0.7:
                        m.rol = "Guardián"
                    elif p.get('extroversión', 0) > 0.7:
                        m.rol = "Explorador"
                    else:
                        m.rol = "Recolector"
            
            self.log(f"👑 [LIDERAZGO] El Agente {lider.unique_id} ha sido elegido Líder de la Facción {g_id}.", categoria="consenso")
            
            # 2. Definición de Nombre y Misión (Consenso)
            misiones_detalladas = {
                "Prosperidad Económica": ["Mercaderes del Destino", "Sindicato del Oro", "La Ruta de la Seda Digital"],
                "Seguridad Colectiva": ["La Muralla de Hierro", "Orden del Escudo", "Vigilantes del Nexo"],
                "Innovación Tecnológica": ["Vanguardia del Silicio", "Arquitectos del Futuro", "Círculo de la Chispa"],
                "Armonía Social": ["Lazos de Unidad", "Comunidad del Equilibrio", "El Gran Ágora"],
                "Preservación de la Memoria": ["Archiveros del Tiempo", "Guardianes del Saber", "El Códice Eterno"],
                "Hedonismo Colectivo": ["Buscadores del Deleite", "La Gran Fiesta", "Sinfonía de los Sentidos"],
                "Aislamiento Defensivo": ["Los Ermitaños", "Refugio de las Sombras", "La Fortaleza Oculta"]
            }
            
            import random
            mision_tipo = random.choice(list(misiones_detalladas.keys()))
            nombre_faccion = random.choice(misiones_detalladas[mision_tipo])
            
            # Guardar tanto el nombre como la misión
            self.objetivos_grupos[g_id] = f"{nombre_faccion} ({mision_tipo})"
            
            # El líder anuncia el nombre y la misión al grupo
            lider.decir(f"📢 ¡Hermanos! Desde hoy, nuestra unión se conocerá como **{nombre_faccion}**. Nuestra misión sagrada es la **{mision_tipo}**. ¡Por la gloria de nuestro grupo!", para_grupo=True)
            self.log(f"🚩 [FACCION] La Facción {g_id} se ha refundado como '{nombre_faccion}' con la misión: {mision_tipo}", categoria="consenso")

if __name__ == "__main__":
    # Configuración desde .env
    num_agentes = int(os.getenv("NUM_AGENTES", 30))
    pasos = int(os.getenv("PASOS_SIMULACION", 100))
    
    # Configuración de la simulación
    modelo = ModeloRelacional(num_agentes=num_agentes)
    modelo.ejecutar(pasos=pasos)
    modelo.imprimir_resumen_social()
    modelo.visualizar_resultados()
