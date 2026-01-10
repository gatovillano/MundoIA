import os
import requests
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

class HerramientasAgente:
    def __init__(self):
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.brave_key = os.getenv("BRAVE_API_KEY")
        if self.tavily_key:
            self.tavily = TavilyClient(api_key=self.tavily_key)
        else:
            self.tavily = None

    def buscar_noticias(self, query="noticias del mundo"):
        """Busca noticias reales usando Tavily."""
        if not self.tavily:
            return "No tengo acceso a internet en este momento."
        try:
            # Buscamos noticias recientes
            response = self.tavily.search(query=query, search_depth="advanced")
            # Tomamos los primeros 2 resultados para no saturar el contexto
            resultados = response.get('results', [])[:2]
            if not resultados:
                return "No encontré noticias relevantes."
            
            info = "Noticias encontradas: "
            for r in resultados:
                info += f"- {r['title']}: {r['content'][:200]}... "
            return info
        except Exception as e:
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

    def brave_search(self, query):
        """Realiza una búsqueda usando la API de Brave."""
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

    def scrapear_url(self, url):
        """Extrae el texto principal de una URL."""
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

# Instancia global
herramientas = HerramientasAgente()
