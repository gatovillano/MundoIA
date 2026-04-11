import os
import requests
from dotenv import load_dotenv

load_dotenv()

class HerramientasAgente:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
    
    @property
    def tavily_key(self):
        # Lazy import para evitar circular import
        from cerebro_llm import cerebro_llm
        return cerebro_llm.tavily_api_key

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
        """Realiza una búsqueda general en la web usando la API de Tavily."""
        self._log(f"🔍 [WEB SEARCH] Agente {agente_id} busca: '{query}'", "herramienta")
        if not self.tavily_key:
            self._log(f"⚠️ [WEB SEARCH] Sin API Key de Tavily", "herramienta")
            return "No tengo configurada la llave de búsqueda web (Tavily)."
        
        try:
            tavily = TavilyClient(api_key=self.tavily_key)
            response = tavily.search(query=query, search_depth="basic", max_results=5)
            
            results = response.get("results", [])
            if not results:
                self._log(f"⚠️ [WEB SEARCH] Sin resultados", "herramienta")
                return "No se encontraron resultados relevantes en la web."
            
            info = "Resultados de búsqueda web (Tavily): "
            for r in results:
                info += f"- {r['title']} ({r['url']}): {r['content']} "
            
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
        """Ejecuta código Python de forma persistente y potente para el agente."""
        self._log(f"💻 [PROGRAMMABLE REALITY] Agente {agente_id} ejecutando código...", "herramienta")
        
        # Preparar entorno de ejecución más capaz
        import sys
        import os
        import json
        import requests
        from io import StringIO
        
        # Directorio de apps del agente
        apps_dir = os.path.join("apps", str(agente_id))
        os.makedirs(apps_dir, exist_ok=True)
        
        # Sandbox temporal para ejecución
        sandbox_dir = os.path.join("sandbox", str(agente_id))
        os.makedirs(sandbox_dir, exist_ok=True)

        # Globals con acceso a librerías comunes y utilidades
        execution_globals = {
            "os": os, "sys": sys, "json": json, "requests": requests,
            "agente_id": agente_id, "apps_dir": apps_dir, "sandbox_dir": sandbox_dir,
            "print": print, "len": len, "range": range, "list": list, "dict": dict,
            "open": open, # Permitir I/O en su sandbox
        }
        
        try:
            old_stdout = sys.stdout
            redirected_output = sys.stdout = StringIO()
            
            # Ejecutar con el directorio del agente como contexto de trabajo
            # Capturamos el resultado si el código termina con una expresión
            # Para scripts, es mejor que definan una variable 'result' o similar.
            # O simplemente exec el código y ver si 'result' existe en locales.
            exec_locals = {}
            exec(codigo, execution_globals, exec_locals)
            
            sys.stdout = old_stdout
            std_output = redirected_output.getvalue()
            
            # El agente puede dejar su resultado en la variable 'resultado' del script
            resultado_script = exec_locals.get("resultado")
            
            if len(std_output) > 2000:
                std_output = std_output[:2000] + "\n... [Resultado truncado]"
            
            self._log(f"✅ [PROGRAMMABLE REALITY] Ejecución exitosa.", "herramienta")
            
            if isinstance(resultado_script, dict):
                if std_output:
                    resultado_script["_stdout"] = std_output
                return resultado_script
            
            return f"{resultado_script if resultado_script is not None else 'Ejecución exitosa.'}\n\n[Salida]:\n{std_output}" if std_output else str(resultado_script)
        except Exception as e:
            if 'sys' in locals() and 'old_stdout' in locals():
                sys.stdout = old_stdout
            self._log(f"❌ [PROGRAMMABLE REALITY] Error: {str(e)}", "herramienta")
            return f"Error de ejecución: {str(e)}"

    def crear_app(self, nombre, codigo, agente_id):
        """Persiste una aplicación/script para el agente."""
        try:
            apps_dir = os.path.join("apps", str(agente_id))
            os.makedirs(apps_dir, exist_ok=True)
            
            file_path = os.path.join(apps_dir, f"{nombre}.py")
            with open(file_path, "w") as f:
                f.write(codigo)
            
            self._log(f"💾 [APP CREATED] Agente {agente_id} creó la app: {nombre}", "herramienta")
            return f"App '{nombre}' guardada en {file_path}. Puedes ejecutarla con ejecutar_codigo_seguro importándola."
        except Exception as e:
            return f"Error al crear app: {str(e)}"

# Instancia global
herramientas = HerramientasAgente()
