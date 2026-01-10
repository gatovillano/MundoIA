from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
import random

# Definimos el estado del agente
class AgentState(TypedDict):
    agent_id: int
    recursos: float
    hambre: float
    conocidos: List[int]
    decision: str
    mensaje: str

def analizar_situacion(state: AgentState):
    """Nodo 1: El agente analiza su estado interno."""
    print(f"      [LangGraph-{state['agent_id']}] Pensando: ¿Qué necesito?")
    if state['hambre'] > 7:
        return {"decision": "buscar_comida"}
    if state['recursos'] < 50:
        return {"decision": "competir"}
    return {"decision": "socializar"}

def tomar_accion(state: AgentState):
    """Nodo 2: El agente decide qué hacer basado en el análisis."""
    decision = state['decision']
    print(f"      [LangGraph-{state['agent_id']}] Decisión tomada: {decision}")
    
    if decision == "buscar_comida":
        return {"mensaje": "Necesito energía urgentemente. ¿Quién me ayudará?"}
    elif decision == "competir":
        return {"mensaje": "El mundo es duro. Debo asegurar mi posición."}
    else:
        return {"mensaje": "Todo está en calma. Es buen momento para hacer aliados."}

# Construimos el Grafo
workflow = StateGraph(AgentState)

workflow.add_node("analizar", analizar_situacion)
workflow.add_node("decidir", tomar_accion)

workflow.set_entry_point("analizar")
workflow.add_edge("analizar", "decidir")
workflow.add_edge("decidir", END)

# Compilamos el cerebro
cerebro_compilado = workflow.compile()

class CerebroAvanzado:
    def __init__(self, agent_id):
        self.agent_id = agent_id

    def pensar(self, recursos, hambre, conocidos):
        """Ejecuta el flujo de LangGraph para obtener una decisión."""
        inputs = {
            "agent_id": self.agent_id,
            "recursos": recursos,
            "hambre": hambre,
            "conocidos": conocidos,
            "decision": "",
            "mensaje": ""
        }
        resultado = cerebro_compilado.invoke(inputs)
        return resultado['decision'], resultado['mensaje']
