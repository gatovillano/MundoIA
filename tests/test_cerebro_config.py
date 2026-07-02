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
        # Evitar usar config_ai.json real si existe en el entorno de pruebas
        original_config_path = cerebro_llm.config_path
        cerebro_llm.config_path = "non_existent_config.json"
        try:
            cerebro_llm.load_config()
        finally:
            cerebro_llm.config_path = original_config_path
            
        self.assertEqual(cerebro_llm.api_key, "test-kilo-key")
        self.assertEqual(cerebro_llm.model, "kilocode/stepfun/step-3.5-flash:free")

if __name__ == '__main__':
    unittest.main()
