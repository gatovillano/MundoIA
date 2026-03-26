import os
import requests
from dotenv import load_dotenv

load_dotenv()

class HerramientasAgente:
    def __init__(self, log_callback=None):
        self.brave_key = os.getenv("BRAVE_API_KEY")
        self.log_callback = log_callback
    
    def _log(self, mensaje, categoria="herramienta"):
        """Envía un log si hay callback configurado."""
        if self.log_callback:
            self.log_callback(mensaje, categoria)

    def obtener_clima(self, ciudad="Madrid"):
        """Simula o consulta el clima."""
        # Podríamos usar web_search aquí si quisiéramos datos reales, 
        # pero por ahora lo dejamos como una simulación robusta o una búsqueda simple.
        return f"El clima en {ciudad} parece despejado y propicio para la actividad de los agentes."

    def consultar_mercado(self):
        """Devuelve el precio actual de los recursos en MundoCoins."""
        import random
        precio = random.uniform(1.5, 5.0)
        return f"El precio actual del recurso es de {precio:.2f} MC por unidad."

    def web_search(self, query, agente_id=None):
        """Realiza una búsqueda general en la web usando la API de Brave."""
        self._log(f"🔍 [WEB SEARCH] Agente {agente_id} busca: '{query}'", "herramienta")
        if not self.brave_key:
            self._log(f"⚠️ [WEB SEARCH] Sin API Key de Brave", "herramienta")
            return "No tengo configurada la llave de búsqueda web (Brave)."
        
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.brave_key
            }
            params = {"q": query, "count": 5}
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            
            results = data.get("web", {}).get("results", [])
            if not results:
                self._log(f"⚠️ [WEB SEARCH] Sin resultados", "herramienta")
                return "No se encontraron resultados relevantes en la web."
            
            info = "Resultados de búsqueda web: "
            for r in results:
                info += f"- {r['title']}: {r['description']} "
            
            self._log(f"✅ [WEB SEARCH] Encontrados {len(results)} resultados", "herramienta")
            return info
        except Exception as e:
            self._log(f"❌ [WEB SEARCH] Error: {str(e)}", "herramienta")
            return f"Error en la búsqueda web: {str(e)}"

    def scrapear_url(self, url, agente_id=None):
        """Extrae el texto principal de una URL."""
        self._log(f"🌐 [WEB SCRAPING] Agente {agente_id} extrayendo contenido de: {url}", "herramienta")
        try:
            from bs4 import BeautifulSoup
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Limpiar scripts y estilos
            for script in soup(["script", "style"]):
                script.extract()
            
            text = soup.get_text()
            # Limpiar espacios en blanco
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return f"Contenido extraído de {url}: {text[:500]}..."
        except Exception as e:
            return f"Error al scrapear {url}: {str(e)}"

    def ejecutar_codigo_seguro(self, codigo, agente_id=None):
        """Ejecuta código Python en un entorno restringido."""
        self._log(f"💻 [PROGRAMMABLE REALITY] Agente {agente_id} ejecutando código...", "herramienta")
        
        # Diccionario de funciones permitidas (Safe globals)
        safe_globals = {
            "abs": abs, "min": min, "max": max, "sum": sum, "round": round,
            "len": len, "list": list, "dict": dict, "set": set, "range": range,
            "int": int, "float": float, "str": str, "bool": bool, "print": print,
            "any": any, "all": all, "sorted": sorted, "type": type
        }
        
        try:
            # Capturar salida
            import sys
            from io import StringIO
            old_stdout = sys.stdout
            redirected_output = sys.stdout = StringIO()
            
            exec(codigo, {"__builtins__": safe_globals}, {})
            
            sys.stdout = old_stdout
            result = redirected_output.getvalue()
            
            # Truncar resultado para evitar saturar el contexto
            if len(result) > 1000:
                result = result[:1000] + "\n... [Resultado truncado]"
            
            self._log(f"✅ [PROGRAMMABLE REALITY] Ejecución exitosa.", "herramienta")
            return result if result else "Código ejecutado sin salida."
        except Exception as e:
            self._log(f"❌ [PROGRAMMABLE REALITY] Error: {str(e)}", "herramienta")
            return f"Error de ejecución: {str(e)}"

# Instancia global
herramientas = HerramientasAgente()
