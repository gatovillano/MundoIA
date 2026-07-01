# Especificación de Diseño: Integración de KiloCode Gateway

Este documento describe la especificación de diseño para incorporar KiloCode Gateway como proveedor de LLM en el backend y el frontend de MundoIA.

## Contexto y Requerimientos

El usuario necesita agregar KiloCode Gateway como proveedor de LLM. Esto implica:
1. Configuración de LiteLLM en el backend para poder consumir modelos de KiloCode Gateway utilizando el prefijo `kilocode/`.
2. Habilitar la persistencia de credenciales en variables de entorno (`KILOCODE_API_KEY`) y en el archivo `config_ai.json`.
3. Ofrecer la opción en el panel de configuración de la interfaz del frontend para seleccionar KiloCode como proveedor, ingresar la API key y seleccionar o escribir un modelo específico.

## Arquitectura y Componentes

### 1. Backend (`agents/cerebro_llm.py`)
- **Wrapper de `completion`:** Se interceptan las llamadas a la función `completion` de `litellm`. Si el modelo comienza con `kilocode/`, se traduce al formato de OpenAI compatible (`openai/<model_name>`), se setea `api_base = "https://api.kilo.ai/api/gateway"`, y se asocia la `api_key` correcta (por defecto `KILOCODE_API_KEY`).
- **Persistencia de Configuración:** En `load_config` y `reload_config`, si el proveedor configurado es `"kilocode"`, se asocia la API key desde `KILOCODE_API_KEY`.

### 2. API del Backend (`api/api.py`)
- **GET `/config/ai`:** Retorna `has_kilocode_key` (si existe la variable de entorno `KILOCODE_API_KEY`).
- **POST `/config/ai`:** Si el proveedor es `"kilocode"`, guarda la API key provista en `os.environ["KILOCODE_API_KEY"]`, asocia la base URL si se especificó, y persiste los datos en `config_ai.json`.
- **GET `/config/models/{provider}`:** Si el parámetro es `"kilocode"`, realiza una petición GET a `https://api.kilo.ai/api/gateway/models` utilizando la cabecera `Authorization: Bearer <api_key>` para retornar los modelos disponibles en el gateway.

### 3. Frontend (`web/frontend/src/components/ConfigPanel.tsx`)
- **Pestaña de Proveedor:** Se agrega `"KiloCode"` al selector de proveedores.
- **Autodetección:** Si el modelo cargado contiene el prefijo `kilocode/`, se selecciona automáticamente el proveedor `"KiloCode"`.
- **Guardado:** Al guardar la configuración con el proveedor `"KiloCode"`, se asegura que el modelo se envíe con el prefijo `kilocode/`.
- **Acceso rápido a Keys:** Se agrega un enlace a `https://kilo.ai/gateway` para facilitar la obtención de claves de acceso.

## Verificación y Pruebas
1. Levantar el backend de MundoIA.
2. Hacer peticiones de prueba al endpoint `/config/models/kilocode` con y sin API key.
3. Probar la actualización de la configuración del LLM enviando una configuración de KiloCode.
4. Validar en la interfaz de usuario que se puede cambiar a KiloCode, ver los modelos disponibles del gateway en la lista y guardar el cambio.
