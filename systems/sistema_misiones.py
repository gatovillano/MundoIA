"""
Sistema de Misiones Mejorado para MundoIA
Misiones preestablecidas con objetivos medibles y sistema de puntaje
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import random

@dataclass
class Mision:
    """Representa una misión con objetivos medibles"""
    id: str
    titulo: str
    descripcion: str
    tipo: str  # "construccion", "social", "economico", "exploracion", "combate"
    dificultad: str  # "facil", "media", "dificil", "epica"
    objetivo: Dict[str, Any]  # {"tipo": "construir", "cantidad": 5, "actual": 0, "meta": "Hospital"}
    recompensa_puntos: int
    estado: str = "activa"  # "activa", "completada", "fallida"
    turno_inicio: int = 0
    turno_limite: Optional[int] = None
    completada_por: Optional[str] = None  # user_id
    turno_completada: Optional[int] = None
    
    def to_dict(self):
        # Asegurar que objetivo sea al menos un dict vacío para evitar errores de .get()
        obj = self.objetivo or {}
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "tipo": self.tipo,
            "dificultad": self.dificultad,
            "objetivo": obj,
            "recompensa_puntos": self.recompensa_puntos,
            "estado": self.estado,
            "turno_inicio": self.turno_inicio,
            "turno_limite": self.turno_limite,
            "completada_por": self.completada_por,
            "turno_completada": self.turno_completada,
            "progreso": f"{obj.get('actual', 0)}/{obj.get('cantidad', 1)}"
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Mision':
        """Crea una misión a partir de un diccionario filtrando claves extra"""
        valid_fields = {
            "id", "titulo", "descripcion", "tipo", "dificultad", "objetivo",
            "recompensa_puntos", "estado", "turno_inicio", "turno_limite",
            "completada_por", "turno_completada"
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return Mision(**filtered_data)

    def verificar_completada(self, modelo) -> bool:
        """Verifica si la misión se ha completado"""
        if self.estado != "activa" or not self.objetivo:
            return False
            
        tipo_obj = self.objetivo.get("tipo")
        cantidad_requerida = self.objetivo.get("cantidad", 1)
        
        if tipo_obj == "construir":
            # Contar edificios del tipo especificado o cualquiera
            meta = self.objetivo.get("meta")
            count = sum(
                1 for row in modelo.mapa for tile in row 
                for building in (tile.buildings or [])
                if meta == "cualquiera" or building.get("tipo") == meta
            )
            self.objetivo["actual"] = count
            return count >= cantidad_requerida
            
        elif tipo_obj == "poblacion":
            # Alcanzar cierta población
            self.objetivo["actual"] = len(modelo.agentes)
            return len(modelo.agentes) >= cantidad_requerida
            
        elif tipo_obj == "facciones":
            # Crear cierto número de facciones
            total_facciones = len(modelo.civilizaciones) + len(modelo.objetivos_grupos)
            self.objetivo["actual"] = total_facciones
            return total_facciones >= cantidad_requerida
            
        elif tipo_obj == "economia":
            # Alcanzar cierto nivel económico total
            dinero_total = sum(a.dinero for a in modelo.agentes)
            self.objetivo["actual"] = int(dinero_total)
            return dinero_total >= cantidad_requerida
            
        elif tipo_obj == "leyes":
            # Aprobar cierto número de leyes
            leyes_aprobadas = sum(
                len([l for l in leyes if l.get("estado") == "aprobada"])
                for leyes in modelo.facciones_leyes.values()
            )
            self.objetivo["actual"] = leyes_aprobadas
            return leyes_aprobadas >= cantidad_requerida
            
        elif tipo_obj == "asambleas":
            # Completar cierto número de asambleas
            asambleas_completadas = len([
                a for a in modelo.asambleas_globales 
                if a.get("estado") == "FINALIZADA"
            ])
            self.objetivo["actual"] = asambleas_completadas
            return asambleas_completadas >= cantidad_requerida
            
        return False


class SistemaMisiones:
    """Gestiona las misiones del juego"""
    
    # Catálogo de misiones preestablecidas
    MISIONES_CATALOGO = [
        {
            "id": "PRIMEROS_PASOS",
            "titulo": "Primeros Pasos",
            "descripcion": "Construye tu primer edificio para comenzar la civilización",
            "tipo": "construccion",
            "dificultad": "facil",
            "objetivo": {"tipo": "construir", "cantidad": 1, "actual": 0, "meta": "cualquiera"},
            "recompensa_puntos": 100
        },
        {
            "id": "CIUDAD_SALUD",
            "titulo": "Ciudad Saludable",
            "descripcion": "Construye 3 Hospitales para cuidar la salud de tus agentes",
            "tipo": "construccion",
            "dificultad": "media",
            "objetivo": {"tipo": "construir", "cantidad": 3, "actual": 0, "meta": "Hospital"},
            "recompensa_puntos": 500
        },
        {
            "id": "GRANERO_MUNDIAL",
            "titulo": "Granero Mundial",
            "descripcion": "Construye 5 Granjas para asegurar el alimento",
            "tipo": "construccion",
            "dificultad": "media",
            "objetivo": {"tipo": "construir", "cantidad": 5, "actual": 0, "meta": "Granja"},
            "recompensa_puntos": 500
        },
        {
            "id": "METROPOLIS",
            "titulo": "Metrópolis",
            "descripcion": "Alcanza una población de 50 agentes",
            "tipo": "social",
            "dificultad": "media",
            "objetivo": {"tipo": "poblacion", "cantidad": 50, "actual": 0},
            "recompensa_puntos": 750
        },
        {
            "id": "NACIONES_UNIDAS",
            "titulo": "Naciones Unidas",
            "descripcion": "Forma 5 facciones diferentes en el mundo",
            "tipo": "social",
            "dificultad": "dificil",
            "objetivo": {"tipo": "facciones", "cantidad": 5, "actual": 0},
            "recompensa_puntos": 1000
        },
        {
            "id": "PROSPERIDAD",
            "titulo": "Era de Prosperidad",
            "descripcion": "Acumula 10,000 MundoCoins en total entre todos los agentes",
            "tipo": "economico",
            "dificultad": "dificil",
            "objetivo": {"tipo": "economia", "cantidad": 10000, "actual": 0},
            "recompensa_puntos": 1500
        },
        {
            "id": "DEMOCRACIA",
            "titulo": "Democracia Plena",
            "descripcion": "Aprueba 10 leyes mediante votación",
            "tipo": "social",
            "dificultad": "dificil",
            "objetivo": {"tipo": "leyes", "cantidad": 10, "actual": 0},
            "recompensa_puntos": 1200
        },
        {
            "id": "DIALOGO_GLOBAL",
            "titulo": "Diálogo Global",
            "descripcion": "Completa 5 asambleas globales",
            "tipo": "social",
            "dificultad": "media",
            "objetivo": {"tipo": "asambleas", "cantidad": 5, "actual": 0},
            "recompensa_puntos": 800
        },
        {
            "id": "IMPERIO",
            "titulo": "Imperio Eterno",
            "descripcion": "Alcanza una población de 100 agentes",
            "tipo": "social",
            "dificultad": "epica",
            "objetivo": {"tipo": "poblacion", "cantidad": 100, "actual": 0},
            "recompensa_puntos": 3000
        },
        {
            "id": "UTOPIA",
            "titulo": "Utopía Tecnológica",
            "descripcion": "Construye 10 edificios de cada tipo",
            "tipo": "construccion",
            "dificultad": "epica",
            "objetivo": {"tipo": "construir", "cantidad": 30, "actual": 0, "meta": "cualquiera"},
            "recompensa_puntos": 5000
        }
    ]
    
    def __init__(self):
        self.misiones_activas: List[Mision] = []
        self.misiones_completadas: List[Mision] = []
        self.puntajes_usuarios: Dict[str, int] = {}  # {user_id: puntos}

    def __getstate__(self):
        state = self.__dict__.copy()
        state['misiones_activas'] = [m.to_dict() for m in self.misiones_activas]
        state['misiones_completadas'] = [m.to_dict() for m in self.misiones_completadas]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.misiones_activas = [Mision.from_dict(d) for d in state['misiones_activas']]
        self.misiones_completadas = [Mision.from_dict(d) for d in state['misiones_completadas']]
        
    def inicializar_misiones_iniciales(self, turno_actual: int):
        """Crea las misiones iniciales del juego"""
        # Empezar con 3 misiones fáciles/medias
        misiones_iniciales = [
            "PRIMEROS_PASOS",
            "CIUDAD_SALUD",
            "GRANERO_MUNDIAL"
        ]
        
        for mision_id in misiones_iniciales:
            template = next((m for m in self.MISIONES_CATALOGO if m["id"] == mision_id), None)
            if template:
                mision = Mision(
                    id=template["id"],
                    titulo=template["titulo"],
                    descripcion=template["descripcion"],
                    tipo=template["tipo"],
                    dificultad=template["dificultad"],
                    objetivo=template["objetivo"].copy(),
                    recompensa_puntos=template["recompensa_puntos"],
                    turno_inicio=turno_actual
                )
                self.misiones_activas.append(mision)
    
    def verificar_misiones(self, modelo, user_id: str) -> List[Dict]:
        """Verifica el estado de todas las misiones activas"""
        misiones_completadas_ahora = []
        
        for mision in self.misiones_activas[:]:  # Copiar lista para poder modificar
            if mision.verificar_completada(modelo):
                mision.estado = "completada"
                mision.completada_por = user_id
                mision.turno_completada = modelo.paso_actual
                
                # Otorgar puntos
                self.otorgar_puntos(user_id, mision.recompensa_puntos)
                
                # Mover a completadas
                self.misiones_activas.remove(mision)
                self.misiones_completadas.append(mision)
                
                misiones_completadas_ahora.append(mision.to_dict())
                
                # Desbloquear nuevas misiones
                self.desbloquear_nuevas_misiones(mision, modelo.paso_actual)
        
        return misiones_completadas_ahora
    
    def desbloquear_nuevas_misiones(self, mision_completada: Mision, turno_actual: int):
        """Desbloquea nuevas misiones basadas en las completadas"""
        # Lógica de progresión
        if mision_completada.id == "PRIMEROS_PASOS":
            # Desbloquear misiones de población
            self.agregar_mision("METROPOLIS", turno_actual)
        elif mision_completada.id == "CIUDAD_SALUD":
            # Desbloquear misiones económicas
            self.agregar_mision("PROSPERIDAD", turno_actual)
        elif mision_completada.id == "METROPOLIS":
            # Desbloquear misiones sociales avanzadas
            self.agregar_mision("NACIONES_UNIDAS", turno_actual)
            self.agregar_mision("DEMOCRACIA", turno_actual)
        elif mision_completada.id == "NACIONES_UNIDAS":
            # Desbloquear misiones épicas
            self.agregar_mision("IMPERIO", turno_actual)
    
    def agregar_mision(self, mision_id: str, turno_actual: int):
        """Agrega una nueva misión si no está ya activa o completada"""
        # Verificar que no esté ya activa
        if any(m.id == mision_id for m in self.misiones_activas):
            return
        if any(m.id == mision_id for m in self.misiones_completadas):
            return
            
        template = next((m for m in self.MISIONES_CATALOGO if m["id"] == mision_id), None)
        if template:
            mision = Mision(
                id=template["id"],
                titulo=template["titulo"],
                descripcion=template["descripcion"],
                tipo=template["tipo"],
                dificultad=template["dificultad"],
                objetivo=template["objetivo"].copy(),
                recompensa_puntos=template["recompensa_puntos"],
                turno_inicio=turno_actual
            )
            self.misiones_activas.append(mision)
    
    def otorgar_puntos(self, user_id: str, puntos: int):
        """Otorga puntos a un usuario"""
        if user_id not in self.puntajes_usuarios:
            self.puntajes_usuarios[user_id] = 0
        self.puntajes_usuarios[user_id] += puntos
    
    def obtener_puntaje(self, user_id: str) -> int:
        """Obtiene el puntaje de un usuario"""
        return self.puntajes_usuarios.get(user_id, 0)
    
    def obtener_ranking(self) -> List[Dict]:
        """Obtiene el ranking de usuarios por puntaje"""
        ranking = [
            {"user_id": user_id, "puntos": puntos}
            for user_id, puntos in self.puntajes_usuarios.items()
        ]
        return sorted(ranking, key=lambda x: x["puntos"], reverse=True)
    
    def to_dict(self):
        """Serializa el estado del sistema de misiones"""
        return {
            "misiones_activas": [m.to_dict() for m in self.misiones_activas],
            "misiones_completadas": [m.to_dict() for m in self.misiones_completadas],
            "puntajes": self.puntajes_usuarios,
            "ranking": self.obtener_ranking()
        }
