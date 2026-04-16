import json
import functools
import logging
from datetime import datetime, date
from psycopg2.extras import Json as _Json

# Configurar logging base
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("core.utils")

class DateTimeEncoder(json.JSONEncoder):
    """Encoder JSON para soportar objetos datetime y date en la base de datos."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def Json(data):
    """Wrapper para Psycopg2 que utiliza nuestro DateTimeEncoder."""
    return _Json(data, dumps=lambda obj: json.dumps(obj, cls=DateTimeEncoder))

def synchronized(func):
    """Decorador para asegurar la exclusión mutua en métodos que acceden al estado compartido."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Intentar obtener el lock desde el modelo si existe
        lock = None
        if hasattr(self, "modelo") and self.modelo and hasattr(self.modelo, "lock"):
            lock = self.modelo.lock
        elif hasattr(self, "lock"):
            lock = self.lock
            
        if lock:
            with lock:
                return func(self, *args, **kwargs)
        return func(self, *args, **kwargs)
    return wrapper
