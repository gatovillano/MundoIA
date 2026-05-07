
import sys

file_path = 'core/modelo.py'

with open(file_path, 'r') as f:
    content = f.read()

old_code = """    def ejecutar_accion_final(self, accion_dict: Dict[str, Any]):
        \"\"\"
        Router maestro de acciones físicas.
        Mapea decisiones cognitivas a métodos de interacción con el mundo.
        \"\"\"
        if not accion_dict:
            return False

        tipo = accion_dict.get("tipo", "").lower()
        params = accion_dict.get("parametros", {})

        try:
            # 1. Acciones de Recolección y Supervivencia
            if tipo in ["recolectar", "buscar_recursos"]:
                return self.recolectar()
            elif tipo == "comer":
                return self.comer()
            elif tipo == "descansar":
                self.necesidades["descanso"] = min(
                    10.0, self.necesidades["descanso"] + 2.0
                )
                return True

            # 2. Acciones de Movimiento
            elif tipo == "moverse" or "ir_a" in tipo:
                dest_x = params.get("x", self.x + random.randint(-1, 1))
                dest_y = params.get("y", self.y + random.randint(-1, 1))
                return self.moverse(dest_x, dest_y)

            # 3. Acciones Sociales y de Grupo
            elif tipo == "social_create_post":
                contenido = params.get("contenido", "Hola a todos en OASIS")
                return self._ejecutar_accion_social_automatica(
                    self.modelo.paso_actual
                )  # Simplificado a pulso social
            elif tipo == "formar_grupo":
                return self.modelo.formar_grupos()

            # 4. Acciones de Construcción y Skills
            elif tipo in ["construir", "constrir"]:
                edificio = params.get("edificio") or params.get("tipo")
                if edificio:
                    exito, msg = self.modelo.construir_edificio(self, edificio)
                    return exito
            elif tipo == "skill_factory" or "crear_herramienta" in tipo:
                # Delegar al skill manager
                res = skill_manager.ejecutar_accion_evolutiva(self, accion_dict)
                return res.get("exito", False)

            # 5. Acciones de Combate y Tensión
            elif tipo == "atacar":
                target_id = params.get("target_id")
                if target_id:
                    target = self.modelo.get_agent_by_id(target_id)
                    if target:
                        return self.atacar(target)

            # Fallback: log de acción no reconocida
            # self.modelo.log(f"⚠️ Acción no reconocida: {tipo}", agente_id=self.unique_id)
            return False

        except Exception as e:
            # self.modelo.log(f"❌ Error ejecutando acción {tipo}: {e}", categoria="error")
            return False"""

new_code = """    def ejecutar_accion_final(self, accion_dict: Dict[str, Any]):
        \"\"\"
        Router maestro de acciones físicas.
        Mapea decisiones cognitivas a métodos de interacción con el mundo.
        \"\"\"
        if not accion_dict:
            return False

        tipo = accion_dict.get("tipo", "").lower()
        # Normalizar tipo si viene de botones del frontend que usan nombres directos
        if tipo == "comunicar": tipo = "decir"
        
        params = accion_dict.get("parametros", {}) or accion_dict.get("argumentos", {})

        try:
            # 1. Acciones de Recolección y Supervivencia
            if tipo in ["recolectar", "buscar_recursos"]:
                return self.recolectar()
            elif tipo == "comer":
                return self.comer()
            elif tipo == "cazar":
                # Si existe el método cazar, usarlo. Si no, fallback a recolectar.
                if hasattr(self, 'cazar'): return self.cazar()
                return self.recolectar()
            elif tipo == "curarse":
                self.necesidades["salud"] = min(10.0, self.necesidades.get("salud", 10.0) + 2.0)
                return True
            elif tipo == "descansar":
                self.necesidades["descanso"] = min(
                    10.0, self.necesidades["descanso"] + 2.0
                )
                return True

            # 2. Acciones de Movimiento
            elif tipo in ["moverse", "mover"] or "ir_a" in tipo:
                # Soporte para direcciones cardinales (norte, sur, este, oeste)
                direccion = params.get("direccion", "").lower()
                dx, dy = 0, 0
                if direccion == "norte": dy = -1
                elif direccion == "sur": dy = 1
                elif direccion == "este": dx = 1
                elif direccion == "oeste": dx = -1
                
                if dx != 0 or dy != 0:
                    return self.moverse(self.x + dx, self.y + dy)
                
                dest_x = params.get("x", self.x + random.randint(-1, 1))
                dest_y = params.get("y", self.y + random.randint(-1, 1))
                return self.moverse(dest_x, dest_y)
            elif tipo == "explorar":
                return self.explorar()

            # 3. Acciones Sociales y de Redes
            elif tipo in ["social_post", "social_create_post"]:
                return self._ejecutar_accion_social_automatica(self.modelo.paso_actual)
            elif tipo == "social_comment":
                contenido = params.get("contenido", "")
                post_id = params.get("post_id")
                if post_id and contenido:
                    return self.social_comment(post_id, contenido)
                else:
                    # No hacer fallback - si no hay post_id o contenido, fallar la acción
                    return False
            elif tipo == "social_like":
                self.necesidades["social"] = min(10.0, self.necesidades["social"] + 0.5)
                return True
            elif tipo == "socializar":
                # Buscar agente cercano para socializar
                for a in self.modelo.agentes:
                    if a.unique_id != self.unique_id and abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1:
                        self.necesidades["social"] = min(10.0, self.necesidades["social"] + 2.0)
                        return True
                return False
            elif tipo == "formar_alianza":
                # Intentar con el agente más cercano
                for a in self.modelo.agentes:
                    if a.unique_id != self.unique_id and abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1:
                        return self.formar_alianza(a)
                return False
            elif tipo == "votar":
                voto = params.get("voto", "si").lower() == "si"
                # Votar en la asamblea actual si existe
                for asamblea in self.modelo.asambleas_activas:
                    if self.unique_id in asamblea.get("participantes", []):
                        return self.votar_ley(asamblea["ley_id"], a_favor=voto)
                return False

            # 4. Acciones de Construcción y Conocimiento
            elif tipo in ["construir", "constrir"]:
                edificio = params.get("edificio") or params.get("tipo")
                if edificio:
                    exito, msg = self.modelo.construir_edificio(self, edificio)
                    return exito
            elif tipo == "investigar":
                return self.investigar()
            elif tipo in ["estudiar", "educar"]:
                return self.estudiar()
            elif tipo == "reflexionar":
                self.ganar_experiencia("espiritualidad", 5)
                return True
            elif tipo == "skill_factory" or "crear_herramienta" in tipo:
                res = skill_manager.ejecutar_accion_evolutiva(self, accion_dict)
                return res.get("exito", False)

            # 5. Acciones de Combate
            elif tipo in ["atacar", "combatir", "competir"]:
                target_id = params.get("target_id")
                if target_id:
                    target = self.modelo.get_agent_by_id(target_id)
                    if target:
                        return self.atacar(target)
                # Si no hay target, atacar al más cercano
                for a in self.modelo.agentes:
                    if a.unique_id != self.unique_id and abs(a.x - self.x) <= 1 and abs(a.y - self.y) <= 1:
                        return self.atacar(a)
                return False

            return False

        except Exception as e:
            return False"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w') as f:
        f.write(content)
    print("Successfully patched ejecutar_accion_final in modelo.py")
else:
    print("Could not find old_code in modelo.py")
