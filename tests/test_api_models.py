import os
import sys
import unittest
import asyncio
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.api import get_provider_models

class TestAPIModels(unittest.TestCase):
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

        # Call the endpoint directly as a coroutine
        data = asyncio.run(get_provider_models(provider="kilocode", api_key="test-key"))
        self.assertIn("models", data)
        self.assertEqual(len(data["models"]), 1)
        self.assertEqual(data["models"][0]["id"], "stepfun/step-3.5-flash:free")

if __name__ == '__main__':
    unittest.main()
