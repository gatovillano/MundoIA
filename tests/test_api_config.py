import os
import sys
import json
import tempfile
import unittest
import asyncio
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import api.api as api_module
from api.api import get_ai_config, set_ai_config, AIConfig
from agents.cerebro_llm import cerebro_llm

class TestAPIConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config_file = os.path.join(self.temp_dir.name, "config_ai.json")
        self.orig_api_config_file = api_module.AI_CONFIG_FILE
        self.orig_cerebro_config_path = cerebro_llm.config_path
        api_module.AI_CONFIG_FILE = self.temp_config_file
        cerebro_llm.config_path = self.temp_config_file

    def tearDown(self):
        api_module.AI_CONFIG_FILE = self.orig_api_config_file
        cerebro_llm.config_path = self.orig_cerebro_config_path
        self.temp_dir.cleanup()

    def test_get_ai_config_contains_kilocode(self):
        data = asyncio.run(get_ai_config())
        self.assertIn("has_kilocode_key", data)
        self.assertIn("api_key", data)
        self.assertIn("api_keys", data)

    def test_set_ai_config_saves_and_persists_across_restart(self):
        req = AIConfig(
            provider="kilocode",
            api_key="kilo-test-key-123",
            model="kilocode/stepfun/step-3.5-flash:free",
            base_url="https://api.kilo.ai/api/gateway",
            tavily_api_key="tvly-test-999"
        )
        asyncio.run(set_ai_config(req))
        self.assertEqual(os.environ.get("KILOCODE_API_KEY"), "kilo-test-key-123")
        self.assertEqual(os.environ.get("MODEL_NAME"), "kilocode/stepfun/step-3.5-flash:free")

        # Simular reinicio del servidor donde .env pisa las variables de entorno iniciales
        os.environ["AI_PROVIDER"] = "openrouter"
        os.environ["MODEL_NAME"] = "openrouter/default-from-env"
        os.environ["KILOCODE_API_KEY"] = "old-env-key"

        # Al recargar desde config_ai.json (en cerebro_llm y GET /config/ai), debe prevalecer lo persistido
        cerebro_llm.load_config()
        self.assertEqual(cerebro_llm.model, "kilocode/stepfun/step-3.5-flash:free")
        self.assertEqual(cerebro_llm.api_key, "kilo-test-key-123")
        self.assertEqual(os.environ.get("MODEL_NAME"), "kilocode/stepfun/step-3.5-flash:free")

        data = asyncio.run(get_ai_config())
        self.assertEqual(data["provider"], "kilocode")
        self.assertEqual(data["model"], "kilocode/stepfun/step-3.5-flash:free")
        self.assertEqual(data["api_key"], "kilo-test-key-123")
        self.assertEqual(data["tavily_api_key"], "tvly-test-999")

if __name__ == '__main__':
    unittest.main()
