import os
import requests
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

class HerramientasAgente:
    def __init__(self, log_callback=None):
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.brave_key = os.getenv("BRAVE_API_KEY")
        self.log_callback = log_callback
        if self.tavily_key:
            self.tavily = TavilyClient(api_key=self.tavily_key)
        else:
            self.tavily = None
    
    def _log(self, mensaje, categoria="herramienta"):
        """Envía un log si hay callback configurado."""
        if self.log_callback:
            self.log_callback(mensaje, categoria)

    def buscar_noticias(self, query="noticias del mundo", agente_id=None):
        """Busca noticias reales usando Tavily."""
        self._log(f"🔍 [HERRAMIENTA] Agente {agente_id} está buscando: '{query}' usando Tavily", "herramienta")
        if not self.tavily:
            return "No tengo acceso a internet en este momento."
        try:
            # Buscamos noticias recientes
            response = self.tavily.search(query=query, search_depth="advanced")
            # Tomamos los primeros 2 resultados para no saturar el contexto
            resultados = response.get('results', [])[:2]
            if not resultados:
                self._log(f"⚠️ [HERRAMIENTA] Agente {agente_id}: No se encontraron resultados", "herramienta")
                return "No encontré noticias relevantes."
            
            info = "Noticias encontradas: "
            for r in resultados:
                info += f"- {r['title']}: {r['content'][:200]}... "
            self._log(f"✅ [HERRAMIENTA] Agente {agente_id}: Encontró {len(resultados)} resultados", "herramienta")
            return info
        except Exception as e:
            self._log(f"❌ [HERRAMIENTA] Agente {agente_id}: Error - {str(e)}", "herramienta")
            return f"Error al buscar noticias: {str(e)}"

    def obtener_clima(self, ciudad="Madrid"):
        """Simula o consulta el clima (podría extenderse con una API real)."""
        # Por ahora simulamos para no depender de más keys, pero Tavily también puede buscar esto
        if self.tavily:
            return self.buscar_noticias(f"clima actual en {ciudad}")
        return f"El clima en {ciudad} parece despejado y propicio para la recolección."

    def consultar_mercado(self):
        """Devuelve el precio actual de los recursos en MundoCoins."""
        import random
        precio = random.uniform(1.5, 5.0)
        return f"El precio actual del recurso es de {precio:.2f} MC por unidad."

    def brave_search(self, query, agente_id=None):
        """Realiza una búsqueda usando la API de Brave."""
        self._log(f"🔍 [BRAVE SEARCH] Agente {agente_id} busca: '{query}'", "herramienta")
        if not self.brave_key:
            return "No tengo configurada la llave de Brave Search."
        
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.brave_key
            }
            params = {"q": query, "count": 3}
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            
            results = data.get("web", {}).get("results", [])
            if not results:
                return "No se encontraron resultados en Brave."
            
            info = "Resultados de Brave: "
            for r in results:
                info += f"- {r['title']}: {r['description']} (URL: {r['url']}) "
            return info
        except Exception as e:
            return f"Error en Brave Search: {str(e)}"

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
        
        # Añadir acceso limitado al modelo si se pasa el contexto (opcional)
        # Por ahora lo mantenemos puramente matemático/lógico para seguridad
        
        try:
            # Capturar salida
            import sys
            from io import StringIO
            old_stdout = sys.stdout
            redirected_output = sys.stdout = StringIO()
            
            exec(codigo, {"__builtins__": safe_globals}, {})
            
            sys.stdout = old_stdout
            result = redirected_output.getvalue()
            
            # Truncar resultado para evitar saturar el frontend/LLM
            if len(result) > 1000:
                result = result[:1000] + "\n... [Resultado truncado por longitud]"
            
            self._log(f"✅ [PROGRAMMABLE REALITY] Ejecución exitosa.", "herramienta")
            return result if result else "Código ejecutado sin salida."
        except Exception as e:
            self._log(f"❌ [PROGRAMMABLE REALITY] Error: {str(e)}", "herramienta")
            return f"Error de ejecución: {str(e)}"

# Instancia global
herramientas = HerramientasAgente()
