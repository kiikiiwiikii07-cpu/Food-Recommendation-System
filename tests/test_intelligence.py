import json
import unittest
from unittest.mock import patch

from backend import intelligence

class FakeResponse:
    def raise_for_status(self): pass
    def json(self):
        return {"choices":[{"message":{"content":"{\"ok\":true}"}}],"usage":{"prompt_tokens":12,"completion_tokens":3}}

class IntelligenceTests(unittest.TestCase):
    @patch.dict('os.environ', {'NVIDIA_API_KEY':'test-secret','NVIDIA_MODEL':'nvidia/nemotron-3.5-lightning-30b-a3b'})
    @patch('backend.intelligence.httpx.post', return_value=FakeResponse())
    def test_client_uses_server_key_model_and_openai_compatible_endpoint(self, post):
        result=intelligence.chat_json('json','check',80)
        self.assertEqual(result,{'ok':True})
        args,kwargs=post.call_args
        self.assertEqual(args[0],'https://integrate.api.nvidia.com/v1/chat/completions')
        self.assertEqual(kwargs['headers']['Authorization'],'Bearer test-secret')
        self.assertEqual(kwargs['json']['model'],'nvidia/nemotron-3.5-lightning-30b-a3b')
    def test_model_constraints_are_allowlisted_and_bounded(self):
        result=intelligence.safe_intent({'meal_type':'invalid','diet':'vegan','max_minutes':9999,'include_ingredients':['  Tomato! '],'avoid_ingredients':['peanut']})
        self.assertIsNone(result['meal_type'])
        self.assertEqual(result['max_minutes'],240)
        self.assertEqual(result['include_ingredients'],['tomato'])
        self.assertEqual(result['avoid_ingredients'],['peanut'])

if __name__=='__main__': unittest.main()
