import random

def validar_accion(agente, accion_nombre, accion_data, modelo):
    """
    Valida si una acción es realizable según el estado del agente y el mundo.
    Retorna (es_valido, mensaje_error).
    """
    argumentos = accion_data.get("argumentos", {})
    
    if accion_nombre == "ATACAR":
        objetivo_id = argumentos.get("objetivo_id") or argumentos.get("agente_id")
        if not objetivo_id:
            return False, "Falta objetivo_id para atacar."
        
        objetivo = modelo.get_agent_by_id(objetivo_id)
        if not objetivo:
            return False, f"El objetivo {objetivo_id} no existe."
        if not objetivo.esta_vivo:
            return False, f"El objetivo {objetivo_id} ya no está vivo."
        
        distancia = abs(objetivo.x - agente.x) + abs(objetivo.y - agente.y)
        if distancia > 2:
            return False, f"Objetivo a {distancia} casillas (máx 2 para atacar)."
        
        return True, ""

    elif accion_nombre == "COMERCIAR":
        objetivo_id = argumentos.get("objetivo_id") or argumentos.get("agente_id")
        if not objetivo_id:
            return False, "Falta objetivo_id para comerciar."
        
        objetivo = modelo.get_agent_by_id(objetivo_id)
        if not objetivo:
            return False, f"El objetivo {objetivo_id} no existe."
        
        distancia = abs(objetivo.x - agente.x) + abs(objetivo.y - agente.y)
        if distancia > 3:
            return False, f"Objetivo a {distancia} casillas (máx 3 para comerciar)."
        
        if agente.dinero < 15:
            return False, f"Dinero insuficiente: {agente.dinero:.1f} < 15 MC."
        
        if objetivo.recursos <= 0:
            return False, "El objetivo no tiene recursos para vender."
        
        return True, ""

    elif accion_nombre == "INVERTIR":
        monto = argumentos.get("monto")
        if monto is None:
            return True, "" # El motor calcula el monto si no viene
        
        try:
            monto = float(monto)
        except:
            return False, "Monto de inversión inválido."
            
        if monto <= 0:
            return False, "El monto de inversión debe ser positivo."
        if monto > agente.dinero * 0.8:
            return False, "No puedes invertir más del 80% de tu capital."
        
        return True, ""

    elif accion_nombre == "ALIANZA" or accion_nombre == "FORMAR_ALIANZA":
        objetivo_id = argumentos.get("interlocutor_id") or argumentos.get("objetivo_id") or argumentos.get("agente_id")
        if not objetivo_id:
            return False, "Falta destinatario para la alianza."
        
        objetivo = modelo.get_agent_by_id(objetivo_id)
        if not objetivo:
            return False, f"El agente {objetivo_id} no existe."
            
        distancia = abs(objetivo.x - agente.x) + abs(objetivo.y - agente.y)
        if distancia > 3:
            return False, f"Agente a {distancia} casillas (máx 3 para diplomacia directa)."
            
        return True, ""

    elif accion_nombre == "CONSTRUIR":
        tipo_edificio = argumentos.get("tipo") or argumentos.get("tipo_edificio")
        if not tipo_edificio:
            return False, "Falta el tipo de edificio para construir (ej: Granja, Hospital)."

        # El edificio más barato es el Centro de Descanso (20 MC, 15 rec)
        if agente.dinero < 20 or agente.recursos < 15:
            return False, f"Recursos insuficientes para construcción básica (mínimo 20 MC y 15 rec). Tienes: {agente.dinero:.1f} MC, {agente.recursos:.1f} rec."

        # Comprobaciones a nivel de modelo (ej: límites globales / proximidad)
        try:
            if hasattr(modelo, "puede_construir"):
                ok, msg = modelo.puede_construir(agente, tipo_edificio)
                if not ok:
                    return False, msg
        except Exception:
            # Si falla la comprobación del modelo, no bloquear por seguridad (se validará al ejecutar)
            pass

        return True, ""

    elif accion_nombre == "CURARSE":
        if agente.inventario.get("medicina", 0) <= 0:
             return False, "No tienes medicinas en el inventario."
        return True, ""

    elif accion_nombre == "COMER":
        if agente.inventario.get("comida", 0) <= 0:
            return False, "No tienes comida en el inventario."
        return True, ""

    elif accion_nombre == "ESTUDIAR":
        # Validar ubicación: Universidad
        tile = modelo.mapa[agente.x][agente.y]
        tiene_uni = any(b.get("tipo") == "Universidad" for b in tile.buildings)
        if not tiene_uni:
            return False, "Debes estar en una Universidad (edificio) para usar la acción ESTUDIAR."
        return True, ""

    elif accion_nombre == "UNIRSE_INSTITUCION":
        inst_id = argumentos.get("institucion_id") or argumentos.get("institucion") or argumentos.get("id") or argumentos.get("nombre")
        # Buscar por id o nombre o por ubicación
        if inst_id:
            if hasattr(modelo, "instituciones"):
                # Buscar por id exacto
                if str(inst_id) in modelo.instituciones:
                    return True, ""
                # Buscar por nombre
                for iid, inst in modelo.instituciones.items():
                    if getattr(inst, "nombre", "").lower() == str(inst_id).lower():
                        return True, ""
                return False, f"Institución '{inst_id}' no encontrada."
            return False, "No hay instituciones en el modelo."
        else:
            # Si no se especifica, validar que exista una institución en tu casilla
            if hasattr(modelo, "instituciones"):
                for iid, inst in modelo.instituciones.items():
                    if getattr(inst, "x", None) == agente.x and getattr(inst, "y", None) == agente.y:
                        return True, ""
            return False, "No especificaste institución y no hay ninguna en tu ubicación."

    elif accion_nombre == "USAR_INSTITUCION":
        inst_id = argumentos.get("institucion_id") or argumentos.get("institucion") or argumentos.get("id") or argumentos.get("nombre")
        if inst_id:
            if hasattr(modelo, "instituciones"):
                if str(inst_id) in modelo.instituciones:
                    return True, ""
                for iid, inst in modelo.instituciones.items():
                    if getattr(inst, "nombre", "").lower() == str(inst_id).lower():
                        return True, ""
                return False, f"Institución '{inst_id}' no encontrada."
            return False, "No hay instituciones en el modelo."
        else:
            # Debes estar en la misma casilla que una institución para usarla sin especificar id
            if hasattr(modelo, "instituciones"):
                for iid, inst in modelo.instituciones.items():
                    if getattr(inst, "x", None) == agente.x and getattr(inst, "y", None) == agente.y:
                        return True, ""
            return False, "No hay una institución aquí para usar."

    elif accion_nombre == "EXPLORAR":
        if agente.necesidades["descanso"] < 2.0:
            return False, "Estás demasiado agotado para explorar."
        return True, ""

    elif accion_nombre == "INVESTIGAR":
        if agente.necesidades["alimento"] < 3.0:
            return False, "Tienes demasiado hambre para concentrarte en investigar."
        return True, ""

    elif accion_nombre in ["COMMENT", "social_comment", "SOCIAL_COMMENT"]:
        post_id = argumentos.get("post_id")
        contenido = argumentos.get("contenido")
        if not post_id or not contenido:
            return False, "Faltan argumentos: post_id y contenido son requeridos para comentar."
        # Opcional: validar que el post existe (si el modelo tiene social_recsys)
        if hasattr(modelo, "social_recsys") and modelo.social_recsys:
            try:
                if hasattr(modelo.social_recsys, "interest_recsys"):
                    posts = modelo.social_recsys.interest_recsys.posts
                    if post_id not in posts:
                        return False, f"El post {post_id} no existe."
            except AttributeError:
                pass  # Si no se puede validar, continuar
        return True, ""

    return True, "" # Acciones genéricas como HABLAR, MOVER, RECOLECTAR, DESCANSAR son siempre válidas

def obtener_accion_fallback(agente, accion_fallida, modelo):
    """
    Retorna una acción segura si la original falló la validación.
    """
    necesidades = agente.necesidades
    
    # 1. Prioridad: Supervivencia
    if necesidades["alimento"] < 4.0:
        # Si tiene comida, comer es mejor que recolectar
        if agente.inventario.get("comida", 0) > 0:
            return {"nombre": "COMER", "argumentos": {}}
        else:
            return {"nombre": "RECOLECTAR", "argumentos": {}}
    if necesidades["salud"] < 3.0:
        return {"nombre": "DESCANSAR", "argumentos": {}}
    if necesidades["descanso"] < 2.0:
        return {"nombre": "DESCANSAR", "argumentos": {}}
        
    # 2. Si falló por distancia, intentar MOVER hacia el objetivo
    if isinstance(accion_fallida, dict):
        argumentos = accion_fallida.get("argumentos", {})
    else:
        argumentos = {}
        
    objetivo_id = argumentos.get("objetivo_id") or argumentos.get("agente_id") or argumentos.get("interlocutor_id")
    
    if objetivo_id:
        objetivo = modelo.get_agent_by_id(objetivo_id)
        if objetivo:
            # Aproximarse (simplificado: una dirección aleatoria que reduzca distancia si es posible, o solo aleatoria)
            dx = 1 if objetivo.x > agente.x else -1 if objetivo.x < agente.x else 0
            dy = 1 if objetivo.y > agente.y else -1 if objetivo.y < agente.y else 0
            
            # Moverse en una de las direcciones de desplazamiento
            if dx != 0 and random.random() > 0.5:
                dir_str = "E" if dx > 0 else "O"
            elif dy != 0:
                dir_str = "S" if dy > 0 else "N"
            else:
                dir_str = random.choice(["N", "S", "E", "O"])
                
            return {"nombre": "MOVER", "argumentos": {"direccion": dir_str}}

    # 3. Fallback genérico: Saludar o Esperar
    return {"nombre": "HABLAR", "argumentos": {"mensaje": "Analizando mi próximo movimiento..."}}
