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
