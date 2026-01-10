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
        self.alianzas = [] # Lista de IDs de agentes aliados
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
                otro_agente.decir(mensaje_resp, pensamiento=pensamiento_resp, privado_para=self.unique_id if es_privado_resp else None, para_grupo=es_grupal_resp)
                otro_agente._respondiendo = False
                # Limpiar mensaje tras responder
                otro_agente.ultimo_mensaje_recibido = None

        if tipo_interaccion == "SOCIALIZAR" or tipo_interaccion == "social":
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
        nuevo_id = str(len(self.modelo.objetivos_grupos) + 1)
        self.grupo_id = nuevo_id
        self.rol = "Líder"
        self.modelo.objetivos_grupos[nuevo_id] = nombre_mision
        self.modelo.log(f"🚩 [FACCION] Agente {self.unique_id} ha fundado la facción {nuevo_id}: {nombre_mision}", categoria="consenso")
        return nuevo_id

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

    def formar_alianza(self, otro_agente):
        """Crea un pacto de alianza mutua entre dos agentes."""
        if otro_agente.unique_id not in self.alianzas:
            self.alianzas.append(otro_agente.unique_id)
            if self.unique_id not in otro_agente.alianzas:
                otro_agente.alianzas.append(self.unique_id)
            self.modelo.log(f"📜 [ALIANZA] Pacto formal entre {self.unique_id} y {otro_agente.unique_id}.", categoria="social")
            return True
        return False

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
        # Producción pasiva mínima
        self.recursos += 0.2

        # Procesar inversiones terminadas
        for inv in list(self.inversiones):
            if self.modelo.paso_actual >= inv["paso_final"]:
                ganancia = inv["monto"] * (1 + inv["interes"])
                self.dinero += ganancia
                self.inversiones.remove(inv)
                resultado = "ganancia" if inv["interes"] > 0 else "pérdida"
                self.modelo.log(f"💰 [RETORNO] Inversión de {self.unique_id} finalizada: {ganancia:.1f} MC ({resultado}).", categoria="social")

        # El metabolismo consume recursos
        consumo = 1.0 + (self.necesidades["alimento"] * 0.05)
        self.recursos -= consumo
        
        # Necesidades aumentan
        self.necesidades["alimento"] += 0.15
        self.necesidades["social"] += 0.1
        self.necesidades["seguridad"] += 0.05
        self.necesidades["descanso"] += 0.2
        self.necesidades["entretenimiento"] += 0.1
        
        # --- BENEFICIOS DE ALIANZAS ---
        for aliado_id in self.alianzas:
            aliado = next((a for a in self.modelo.agentes if a.unique_id == aliado_id), None)
            if aliado:
                # 1. Apoyo Social Pasivo
                self.necesidades["social"] = max(0, self.necesidades["social"] - 0.05)
                
                # 2. Intercambio de Recursos (Solidaridad)
                if self.recursos < 10 and aliado.recursos > 50:
                    transferencia = 2
                    aliado.recursos -= transferencia
                    self.recursos += transferencia
                    self.modelo.log(f"🤝 [ALIANZA] Agente {aliado.unique_id} envió suministros de emergencia a su aliado {self.unique_id}.", categoria="social")
                
                # 3. Solidaridad Médica
                if self.necesidades["salud"] < 5 and aliado.inventario["medicina"] > 1 and self.inventario["medicina"] == 0:
                    aliado.inventario["medicina"] -= 1
                    self.inventario["medicina"] += 1
                    self.modelo.log(f"💊 [ALIANZA] Agente {aliado.unique_id} envió una medicina a su aliado herido {self.unique_id}.", categoria="social")
        
        # Impacto de la salud
        if self.necesidades["alimento"] > 9.0 or self.necesidades["descanso"] > 9.0:
            self.necesidades["salud"] -= 0.2
            self.modelo.log(f"⚠️ [SALUD] Agente {self.unique_id} se siente débil por falta de cuidados.", categoria="state")
        
        if self.necesidades["salud"] < 3.0:
            self.modelo.log(f"🚑 [CRÍTICO] Agente {self.unique_id} está en estado crítico de salud.", categoria="state")

    def recolectar(self):
        """El agente busca recursos en el entorno. Los objetos especiales son MUY raros."""
        r = random.random()
        if r < 0.80: # 80% Alimento
            cantidad = random.uniform(5, 15)
            self.recursos += cantidad
            self.modelo.log(f"  🍎 [RECOLECCION] Agente {self.unique_id} encontró {cantidad:.1f} unidades de alimento.", categoria="alimentos")
        elif r < 0.85: # 5% Medicina (Escaso)
            self.inventario["medicina"] += 1
            self.modelo.log(f"  💊 [RECOLECCION] Agente {self.unique_id} encontró una MEDICINA RARA.", categoria="recursos")
        elif r < 0.90: # 5% Ocio (Escaso)
            self.inventario["ocio"] += 1
            self.modelo.log(f"  🎮 [RECOLECCION] Agente {self.unique_id} encontró un OBJETO DE OCIO.", categoria="recursos")
        else: # 10% Nada
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
        """Intenta declarar una profesión si cumple los requisitos."""
        if self.profesion:
            return False, "Ya tienes una profesión."

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

    def step(self):
        """Acciones que realiza el agente en un turno."""
        self.gasto_turno = 0.0 # Resetear gasto al inicio del turno
        # 1. Identificar posibles objetivos cercanos para el contexto
        otros = [a for a in self.modelo.agentes if a.unique_id != self.unique_id]
        objetivo_cercano = random.choice(otros) if otros else None
        
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
                
                self.interactuar(objetivo_cercano, decision, mensaje_enviado=mensaje)
                self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)
                
        elif decision == "RECOLECTAR":
            self.recursos += 5
            self.necesidades["alimento"] = max(0, self.necesidades["alimento"] - 2)
            self.modelo.log(f"  🍎 [ACCION] Agente {self.unique_id} recolecta recursos extra.", categoria="state")
            self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id)

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
                exito = self.formar_alianza(objetivo_cercano)
                if exito:
                    self.decir(mensaje, pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)
                else:
                    self.decir(f"Ya tengo un pacto con el Agente {objetivo_cercano.unique_id}.", pensamiento=pensamiento, privado_para=destinatario_id, para_grupo=es_grupal)
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

        self.actualizar_estado()

class ModeloRelacional:
    def __init__(self, num_agentes=10, log_callback=None):
        self.num_agentes = num_agentes
        self.log_callback = log_callback
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
        self.datos = [] # Mantener para compatibilidad con visualizar_resultados
        self.relaciones_grupos = {} # {(id1, id2): afinidad}
        self.historial_logs = [] # [{mensaje, categoria, ...}]
        
        # Cargar estado previo si existe
        self.cargar_estado()

        # Si no se cargaron agentes (primera vez), los creamos
        if not self.agentes_cargados:
            self.agentes = [Agente(i, self) for i in range(self.num_agentes)]
            self.agentes_cargados = True
        else:
            self.log(f"💾 [SISTEMA] Continuando simulación con {len(self.agentes)} agentes.", categoria="sistema")

    def log(self, mensaje, categoria="info", subtitulos=None, tts_text=None, pensamiento=None, privado_para=None):
        """Envía un log al callback o a la terminal y lo guarda en el historial."""
        log_entry = {
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
        self.log(f"\n================ PASO {self.paso_actual} ================", categoria="paso")
        
        # Guardar estado automáticamente en cada paso
        self.guardar_estado()
        
        # Lógica de formación de grupos (cada 10 pasos)
        if self.paso_actual % 10 == 0:
            self.log("📢 [SISTEMA] Evaluando formación de grupos sociales...", categoria="sistema")
            self.formar_grupos()
            self.asignar_roles_consenso()

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

    def guardar_estado(self):
        """Guarda el estado actual de todos los agentes en un archivo JSON."""
        datos = {
            "paso_actual": self.paso_actual,
            "objetivos_grupos": self.objetivos_grupos,
            "datos_estadisticos": self.datos,
            "agentes": []
        }
        for a in self.agentes:
            datos["agentes"].append({
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
                "profesion": a.profesion,
                "experiencia": a.experiencia,
                "hitos": a.hitos,
                "memoria_grafica": a.memoria.exportar_datos()
            })
        
        datos["economia"] = self.economia
        datos["relaciones_grupos"] = {f"{k[0]}-{k[1]}": v for k, v in self.relaciones_grupos.items()}
        datos["historial_logs"] = self.historial_logs
        
        with open("estado_simulacion.json", "w") as f:
            json.dump(datos, f, indent=4)

    def cargar_estado(self):
        """Carga el estado desde el archivo JSON si existe."""
        if os.path.exists("estado_simulacion.json"):
            try:
                with open("estado_simulacion.json", "r") as f:
                    datos = json.load(f)
                
                self.paso_actual = datos.get("paso_actual", 0)
                self.objetivos_grupos = datos.get("objetivos_grupos", {})
                self.datos = datos.get("datos_estadisticos", [])
                self.agentes = []
                for a_data in datos.get("agentes", []):
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
                    a.profesion = a_data.get("profesion")
                    a.experiencia = a_data.get("experiencia", {"medicina": 0, "comercio": 0, "combate": 0, "exploracion": 0})
                    a.hitos = a_data.get("hitos", [])
                    
                    if "memoria_grafica" in a_data:
                        a.memoria.cargar_datos(a_data["memoria_grafica"])
                    self.agentes.append(a)
                
                self.economia = datos.get("economia", self.economia)
                self.historial_logs = datos.get("historial_logs", [])
                
                # Cargar relaciones grupales (convertir keys de string a tupla)
                rel_data = datos.get("relaciones_grupos", {})
                for k, v in rel_data.items():
                    try:
                        p1, p2 = k.split("-")
                        self.relaciones_grupos[(p1, p2)] = v
                    except: pass

                self.agentes_cargados = True
                self.log(f"💾 [SISTEMA] Estado cargado desde el paso {self.paso_actual}.", categoria="sistema")
            except Exception as e:
                self.log(f"⚠️ [ERROR] No se pudo cargar el estado: {e}", categoria="sistema")
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
