import os
import sys
import unittest
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.api import get_ai_config, set_ai_config, AIConfig

class TestAPIConfig(unittest.TestCase):
    def test_get_ai_config_contains_kilocode(self):
        data = asyncio.run(get_ai_config())
        self.assertIn("has_kilocode_key", data)

    def test_set_ai_config_saves_kilocode(self):
        req = AIConfig(
            provider="kilocode",
            api_key="kilo-test-key-123",
            model="kilocode/stepfun/step-3.5-flash:free",
            base_url="",
            tavily_api_key=""
        )
        asyncio.run(set_ai_config(req))
        self.assertEqual(os.environ.get("KILOCODE_API_KEY"), "kilo-test-key-123")
        self.assertEqual(os.environ.get("MODEL_NAME"), "kilocode/stepfun/step-3.5-flash:free")

if __name__ == '__main__':
    unittest.main()
