# Integración de KiloCode Gateway - Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incorporar KiloCode Gateway como proveedor de LLM en el backend y el frontend, permitiendo seleccionar y configurar sus modelos en caliente desde la interfaz web.

**Architecture:** Interceptar las peticiones de modelos prefijados con `kilocode/` a través de un wrapper personalizado de la función `completion` de LiteLLM. Esto mapea de forma transparente el modelo a OpenAI compatible, redirige la base URL del API de KiloCode, asocia su API key (`KILOCODE_API_KEY`) y expone los endpoints necesarios en la API FastAPI del backend y el panel de configuración de Next.js en el frontend.

**Tech Stack:** Python (FastAPI, LiteLLM, requests), TypeScript (React, Next.js, TailwindCSS).

---

### Task 1: Soporte de Variables de Entorno y Configuración en el Cerebro LLM

**Files:**
- Modify: `agents/cerebro_llm.py:395-407` (en `load_config`)
- Modify: `agents/cerebro_llm.py:446-458` (en `reload_config`)
- Test: `tests/test_cerebro_config.py` (Crear para validar carga de configuración)

- [ ] **Step 1: Crear test de prueba para validación de carga de configuración de KiloCode**

Crear el archivo `tests/test_cerebro_config.py`:
```python
import os
import unittest
from unittest.mock import patch, MagicMock

# Ajustar PYTHONPATH para poder importar
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.cerebro_llm import cerebro_llm

class TestCerebroConfig(unittest.TestCase):
    @patch.dict(os.environ, {
        "AI_PROVIDER": "kilocode",
        "KILOCODE_API_KEY": "test-kilo-key",
        "MODEL_NAME": "kilocode/stepfun/step-3.5-flash:free"
    })
    def test_load_config_kilocode(self):
        cerebro_llm.load_config()
        self.assertEqual(cerebro_llm.api_key, "test-kilo-key")
        self.assertEqual(cerebro_llm.model, "kilocode/stepfun/step-3.5-flash:free")

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Ejecutar:
```bash
python3 tests/test_cerebro_config.py
```
Expected: FAIL porque la carga de configuración aún no soporta el proveedor "kilocode" y no mapea la key `KILOCODE_API_KEY`.

- [ ] **Step 3: Implementar la carga y recarga de configuración para kilocode**

Modificar `agents/cerebro_llm.py` en `load_config` (líneas ~395-407):
```python
        provider = os.getenv("AI_PROVIDER", "openrouter")
        if provider == "openrouter":
            self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        elif provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        elif provider == "ollama":
            self.api_key = os.getenv("OLLAMA_API_KEY", "")
        elif provider == "kilocode":
            self.api_key = os.getenv("KILOCODE_API_KEY", "")
        else:
            self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
```

Modificar `agents/cerebro_llm.py` en `reload_config` (líneas ~446-458):
```python
        provider = os.getenv("AI_PROVIDER", "openrouter")
        if provider == "openrouter":
            self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        elif provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        elif provider == "ollama":
            self.api_key = os.getenv("OLLAMA_API_KEY", "")
        elif provider == "kilocode":
            self.api_key = os.getenv("KILOCODE_API_KEY", "")
        else:
            self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Ejecutar:
```bash
python3 tests/test_cerebro_config.py
```
Expected: PASS

- [ ] **Step 5: Commit de Task 1**

Ejecutar:
```bash
git add agents/cerebro_llm.py tests/test_cerebro_config.py
git commit -m "feat(backend): add support for kilocode provider in cerebro config"
```

---

### Task 2: Implementación de la Interceptación Dinámica (Wrapper de completion)

**Files:**
- Modify: `agents/cerebro_llm.py:3-10` (al inicio del archivo, redefiniendo `completion`)
- Test: `tests/test_cerebro_completion_wrapper.py` (Crear)

- [ ] **Step 1: Escribir el test de integración/simulación del wrapper**

Crear el archivo `tests/test_cerebro_completion_wrapper.py`:
```python
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import agents.cerebro_llm

class TestCerebroCompletionWrapper(unittest.TestCase):
    @patch('agents.cerebro_llm._original_completion')
    def test_completion_wrapper_routes_kilocode(self, mock_original):
        mock_original.return_value = "fake_response"
        
        # Simular llamada a completion con modelo kilocode
        from agents.cerebro_llm import completion
        res = completion(model="kilocode/stepfun/step-3.5-flash:free", messages=[{"role": "user", "content": "hi"}], api_key="some-key")
        
        # Verificar argumentos de llamada al original
        mock_original.assert_called_once()
        called_kwargs = mock_original.call_args[1]
        self.assertEqual(called_kwargs["model"], "openai/stepfun/step-3.5-flash:free")
        self.assertEqual(called_kwargs["api_base"], "https://api.kilo.ai/api/gateway")
        self.assertEqual(called_kwargs["api_key"], "some-key")
        self.assertEqual(res, "fake_response")

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Ejecutar:
```bash
python3 tests/test_cerebro_completion_wrapper.py
```
Expected: FAIL porque no hay redefinición o wrapper que traduzca el modelo.

- [ ] **Step 3: Agregar la redefinición de completion en cerebro_llm.py**

Modificar `agents/cerebro_llm.py` arriba para definir el wrapper (líneas ~3-10):
```python
import os
import json
from litellm import completion as _original_completion
import litellm
import logging
from litellm._logging import verbose_logger

# Wrapper para interceptar modelos de KiloCode Gateway
def completion(*args, **kwargs):
    if "model" in kwargs and isinstance(kwargs["model"], str) and kwargs["model"].startswith("kilocode/"):
        model_name = kwargs["model"]
        # Mapear kilocode/ a openai/ compatible con custom api_base
        kwargs["model"] = "openai/" + model_name[len("kilocode/"):]
        # Endpoint de KiloCode Gateway
        if not kwargs.get("api_base"):
            kwargs["api_base"] = "https://api.kilo.ai/api/gateway"
        # Resolver API key si no está presente
        if not kwargs.get("api_key"):
            kwargs["api_key"] = os.getenv("KILOCODE_API_KEY", "")
    return _original_completion(*args, **kwargs)
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Ejecutar:
```bash
python3 tests/test_cerebro_completion_wrapper.py
```
Expected: PASS

- [ ] **Step 5: Commit de Task 2**

Ejecutar:
```bash
git add agents/cerebro_llm.py tests/test_cerebro_completion_wrapper.py
git commit -m "feat(backend): add transparent completion wrapper for kilocode gateway"
```

---

### Task 3: API Config endpoints en api/api.py

**Files:**
- Modify: `api/api.py:1330-1376` (endpoints `/config/ai` GET y POST)
- Test: `tests/test_api_config.py` (Crear)

- [ ] **Step 1: Escribir test de integración para endpoints de configuración en api.py**

Crear el archivo `tests/test_api_config.py`:
```python
import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.api import app

class TestAPIConfig(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_ai_config_contains_kilocode(self):
        resp = self.client.get("/config/ai")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("has_kilocode_key", data)

    def test_set_ai_config_saves_kilocode(self):
        payload = {
            "provider": "kilocode",
            "api_key": "kilo-test-key-123",
            "model": "kilocode/stepfun/step-3.5-flash:free",
            "base_url": "",
            "tavily_api_key": ""
        }
        resp = self.client.post("/config/ai", json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os.environ.get("KILOCODE_API_KEY"), "kilo-test-key-123")
        self.assertEqual(os.environ.get("MODEL_NAME"), "kilocode/stepfun/step-3.5-flash:free")

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Ejecutar:
```bash
python3 tests/test_api_config.py
```
Expected: FAIL porque `/config/ai` no tiene la llave `has_kilocode_key` y el POST no asocia `KILOCODE_API_KEY`.

- [ ] **Step 3: Actualizar los endpoints en api/api.py**

Modificar el endpoint GET `/config/ai` en `api/api.py` (líneas ~1330-1341):
```python
@app.get("/config/ai")
async def get_ai_config():
    """Retorna la configuración actual del LLM."""
    return {
        "provider": os.getenv("AI_PROVIDER", "openrouter"),
        "model": os.getenv("MODEL_NAME", "google/gemini-2.0-flash-exp:free"),
        "base_url": os.getenv("AI_BASE_URL", ""),
        "has_openrouter_key": bool(os.getenv("OPENROUTER_API_KEY")),
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "has_ollama_key": bool(os.getenv("OLLAMA_API_KEY") or os.getenv("OLLAMA_API_BASE")),
        "has_kilocode_key": bool(os.getenv("KILOCODE_API_KEY")),
        "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
    }
```

Modificar el endpoint POST `/config/ai` en `api/api.py` (líneas ~1342-1376):
```python
@app.post("/config/ai")
async def set_ai_config(req: AIConfig):
    """Actualiza la configuración del LLM en caliente."""
    os.environ["MODEL_NAME"] = req.model
    os.environ["AI_PROVIDER"] = req.provider
    # Guardar API key por proveedor
    if req.provider == "openrouter" and req.api_key:
        os.environ["OPENROUTER_API_KEY"] = req.api_key
    elif req.provider == "openai" and req.api_key:
        os.environ["OPENAI_API_KEY"] = req.api_key
    elif req.provider == "ollama" and req.api_key:
        os.environ["OLLAMA_API_KEY"] = req.api_key
    elif req.provider == "kilocode" and req.api_key:
        os.environ["KILOCODE_API_KEY"] = req.api_key
        
    if req.base_url and req.provider in ("ollama", "kilocode"):
        os.environ["AI_BASE_URL"] = req.base_url
    elif req.provider not in ("ollama", "kilocode"):
        # Limpiar AI_BASE_URL al cambiar a otros proveedores para evitar conflictos
        os.environ.pop("AI_BASE_URL", None)
        os.environ.pop("OLLAMA_API_BASE", None)
        
    if req.tavily_api_key:
        os.environ["TAVILY_API_KEY"] = req.tavily_api_key
    # Persistir en config_ai.json para que sobreviva a reinicios
    try:
        import json
        config_data = {
            "model": req.model,
            "provider": req.provider,
            "api_key": req.api_key,
            "base_url": req.base_url if req.provider in ("ollama", "kilocode") else "",
            "tavily_api_key": req.tavily_api_key or ""
        }
        with open("config_ai.json", "w") as f:
            json.dump(config_data, f, indent=2)
        print(f"✅ Configuración guardada en config_ai.json: {req.provider}/{req.model}")
    except Exception as e:
        print(f"⚠️ Error guardando config_ai.json: {e}")
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Ejecutar:
```bash
python3 tests/test_api_config.py
```
Expected: PASS

- [ ] **Step 5: Commit de Task 3**

Ejecutar:
```bash
git add api/api.py tests/test_api_config.py
git commit -m "feat(api): implement kilocode endpoints for config/ai"
```

---

### Task 4: Endpoint de consulta de modelos /config/models/kilocode

**Files:**
- Modify: `api/api.py:1384-1460` (endpoint `/config/models/{provider}`)
- Test: `tests/test_api_models.py` (Crear)

- [ ] **Step 1: Escribir el test para obtener modelos de kilocode**

Crear el archivo `tests/test_api_models.py`:
```python
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.api import app

class TestAPIModels(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('requests.get')
    def test_get_models_kilocode(self, mock_get):
        # Configurar mock de respuesta de Kilo Gateway
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"id": "stepfun/step-3.5-flash:free", "name": "Step 3.5 Flash Free"}
            ]
        }
        mock_get.return_value = mock_resp

        resp = self.client.get("/config/models/kilocode?api_key=test-key")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("models", data)
        self.assertEqual(len(data["models"]), 1)
        self.assertEqual(data["models"][0]["id"], "stepfun/step-3.5-flash:free")

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Ejecutar:
```bash
python3 tests/test_api_models.py
```
Expected: FAIL porque no hay soporte para el proveedor "kilocode" en `/config/models/{provider}`.

- [ ] **Step 3: Agregar la lógica para kilocode en el endpoint de modelos**

Modificar `api/api.py` en `get_provider_models` (líneas ~1426-1456):
```python
        elif prov == "openrouter":
            # Usar base_url si se entregó (posible proxy), sino el endpoint público
            base = base_url or os.getenv("AI_BASE_URL") or "https://openrouter.ai/api"
            if base.endswith("/v1"):
                url = base.rstrip("/") + "/models"
            else:
                url = base.rstrip("/") + "/v1/models"
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = requests.get(url, timeout=6, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                raw = []
                if isinstance(data, dict):
                    raw = data.get("models") or data.get("data") or data.get("results") or []
                elif isinstance(data, list):
                    raw = data

                for m in raw:
                    if isinstance(m, dict):
                        mid = m.get("id") or m.get("name") or str(m)
                        name = m.get("name") or m.get("id") or str(m)
                        models.append({"id": mid, "name": name, **{k: v for k, v in m.items() if k not in ("id", "name")}})
                    else:
                        models.append({"id": str(m), "name": str(m)})

        elif prov == "kilocode":
            # Usar base_url si se entregó (posible proxy), sino el endpoint público de KiloCode
            base = base_url or os.getenv("AI_BASE_URL") or "https://api.kilo.ai/api/gateway"
            url = base.rstrip("/") + "/models"
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = requests.get(url, timeout=6, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                raw = []
                if isinstance(data, dict):
                    raw = data.get("models") or data.get("data") or data.get("results") or []
                elif isinstance(data, list):
                    raw = data

                for m in raw:
                    if isinstance(m, dict):
                        mid = m.get("id") or m.get("name") or str(m)
                        name = m.get("name") or m.get("id") or str(m)
                        models.append({"id": mid, "name": name, **{k: v for k, v in m.items() if k not in ("id", "name")}})
                    else:
                        models.append({"id": str(m), "name": str(m)})
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Ejecutar:
```bash
python3 tests/test_api_models.py
```
Expected: PASS

- [ ] **Step 5: Commit de Task 4**

Ejecutar:
```bash
git add api/api.py tests/test_api_models.py
git commit -m "feat(api): implement model fetching for kilocode provider"
```

---

### Task 5: Integración del Frontend (Panel de Configuración)

**Files:**
- Modify: `web/frontend/src/components/ConfigPanel.tsx` (Agregar opción KiloCode, autodetección y link)

- [ ] **Step 1: Modificar ConfigPanel.tsx para incluir el proveedor KiloCode**

Abrir `web/frontend/src/components/ConfigPanel.tsx` y realizar las siguientes modificaciones:

1. Modificar el bloque de autodetección en `fetchCurrentConfig` (líneas ~76-84):
```typescript
                let loadedProv = "OpenRouter";
                if (data.model?.includes("openrouter/")) {
                    loadedProv = "OpenRouter";
                } else if (data.model?.includes("ollama/")) {
                    loadedProv = "Ollama";
                } else if (data.model?.includes("kilocode/")) {
                    loadedProv = "KiloCode";
                } else if (data.model?.includes("gpt-")) {
                    loadedProv = "OpenAI";
                }
                setProvider(loadedProv);

                if (loadedProv === "OpenRouter" || loadedProv === "Ollama" || loadedProv === "KiloCode") {
                    loadModels(loadedProv, data.api_key || "", data.base_url || "");
```

2. Modificar `handleManualReload` (líneas ~101-105):
```typescript
    const handleManualReload = () => {
        if (provider === "OpenRouter" || provider === "Ollama" || provider === "KiloCode") {
            loadModels(provider, apiKey, baseUrl);
        }
    };
```

3. Modificar `handleSave` para añadir el prefijo `kilocode/` y soportar `base_url` si se configura (líneas ~107-127):
```typescript
            let finalModel = selectedModel || searchTerm; // Try searchTerm as custom input if selected is missing
            if (provider === "OpenRouter" && !finalModel.startsWith("openrouter/")) {
                finalModel = `openrouter/${finalModel}`;
            } else if (provider === "Ollama" && !finalModel.startsWith("ollama/")) {
                finalModel = `ollama/${finalModel}`;
            } else if (provider === "KiloCode" && !finalModel.startsWith("kilocode/")) {
                finalModel = `kilocode/${finalModel}`;
            }

            const res = await fetch(getHttpUrl("/config/ai"), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: provider.toLowerCase(), // Enviar en minúscula al backend: "kilocode", "openrouter", "openai", "ollama"
                    api_key: apiKey,
                    model: finalModel,
                    base_url: (provider === "Ollama" || provider === "KiloCode") ? baseUrl : "",
                    tavily_api_key: tavilyApiKey
                })
            });
```

4. Modificar el render del Proveedor de Inteligencia para incluir la opción "KiloCode" (líneas ~150-160):
```typescript
            {/* Proveedor */}
            <Section title="Proveedor de Inteligencia">
                <div className="grid grid-cols-4 gap-2 p-1 bg-black/40 rounded-2xl border border-white/5 shadow-inner">
                    {["OpenRouter", "OpenAI", "Ollama", "KiloCode"].map((p) => (
                        <button
                            key={p}
                            onClick={() => setProvider(p)}
                            className={`py-2.5 text-[10px] font-bold uppercase rounded-xl transition-all ${provider === p ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.1)]' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </Section>
```

5. Modificar el campo de endpoint para mostrarlo si es Ollama o KiloCode (líneas ~180-190):
```typescript
                    {(provider === "Ollama" || provider === "KiloCode") && (
                        <div className="relative group">
                            <input
                                type="text"
                                value={baseUrl}
                                onChange={(e) => setBaseUrl(e.target.value)}
                                placeholder={provider === "Ollama" 
                                    ? "Endpoint (ej: http://localhost:11434)" 
                                    : "Endpoint Kilo (opcional, ej: https://api.kilo.ai/api/gateway)"}
                                className="w-full bg-black/60 border border-white/10 rounded-2xl p-4 text-xs text-white placeholder:text-gray-700 focus:border-indigo-500/40 focus:outline-none transition-all font-mono"
                            />
                        </div>
                    )}
```

6. Modificar el enlace de ayuda para obtener API Keys para incluir KiloCode (líneas ~192-204):
```typescript
                    {(provider !== "Ollama") && (
                        <div className="flex items-center justify-between px-1">
                            <a
                                href={
                                    provider === "OpenRouter" 
                                        ? "https://openrouter.ai/keys" 
                                        : provider === "KiloCode" 
                                            ? "https://kilo.ai/gateway" 
                                            : "https://platform.openai.com/api-keys"
                                }
                                target="_blank"
                                rel="noreferrer"
                                className="text-[9px] text-indigo-400/60 hover:text-indigo-400 flex items-center gap-1.5 transition-colors uppercase font-bold tracking-widest"
                            >
                                Obtener Llave <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                            <span className="text-[8px] text-gray-600 font-mono italic">Seguro: AES-256 Encrypted</span>
                        </div>
                    )}
```

- [ ] **Step 2: Verificar sintaxis y formatear ConfigPanel.tsx**

Revisar el archivo `web/frontend/src/components/ConfigPanel.tsx` para asegurarse de que no haya errores de TypeScript ni tags HTML mal cerrados.

- [ ] **Step 3: Commit de Task 5**

Ejecutar:
```bash
git add web/frontend/src/components/ConfigPanel.tsx
git commit -m "feat(frontend): add KiloCode provider options to ConfigPanel UI"
```

---

### Task 6: Verificación de Integridad y Pruebas Manuales de Producción

- [ ] **Step 1: Ejecutar la suite completa de pruebas del backend**

Ejecutar:
```bash
python3 -m unittest discover tests/
```
Expected: Todos los tests deben pasar exitosamente.

- [ ] **Step 2: Verificar la recarga en caliente del backend con KiloCode**

Correr un script de simulación rápida en python para comprobar que el reload funciona:
```python
import os
from agents.cerebro_llm import cerebro_llm

os.environ["AI_PROVIDER"] = "kilocode"
os.environ["KILOCODE_API_KEY"] = "dummy_kilo_key"
os.environ["MODEL_NAME"] = "kilocode/stepfun/step-3.5-flash:free"

cerebro_llm.reload_config()
assert cerebro_llm.api_key == "dummy_kilo_key"
assert cerebro_llm.model == "kilocode/stepfun/step-3.5-flash:free"
print("SUCCESS: Reload test ok!")
```

- [ ] **Step 3: Commit final**

Ejecutar:
```bash
git commit --allow-empty -m "chore: complete KiloCode Gateway provider integration"
```
