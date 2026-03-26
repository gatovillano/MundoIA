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
        tipo_edificio = argumentos.get("tipo_edificio")
        if not tipo_edificio:
            return False, "Falta tipo_edificio para construir."
        
        # Validación básica de recursos (se repite en el modelo pero aquí evitamos el intento)
        if agente.dinero < 20 or agente.recursos < 15:
            return False, "Recursos insuficientes para construcción básica."
            
        return True, ""

    elif accion_nombre == "CURARSE":
        if agente.inventario.get("medicina", 0) <= 0:
             return False, "No tienes medicinas en el inventario."
        return True, ""

    return True, "" # Acciones genéricas como HABLAR, MOVER, RECOLECTAR, DESCANSAR son siempre válidas

def obtener_accion_fallback(agente, accion_fallida, modelo):
    """
    Retorna una acción segura si la original falló la validación.
    """
    necesidades = agente.necesidades
    
    # 1. Prioridad: Supervivencia
    if necesidades["alimento"] < 4.0:
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
