import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from backend import app as api

class FoodApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        api.DB_PATH=__import__('pathlib').Path(self.tmp.name)/'test.db'
        api.init_db()
        self.client=TestClient(api.app)
        self.client.put('/api/v1/preferences',json={'diet':'any','allergies':[],'avoid':[],'cuisines':[],'meals':['breakfast','lunch','dinner'],'max_minutes':60})
    def tearDown(self): self.tmp.cleanup()
    def test_allergy_is_strict(self):
        r=self.client.put('/api/v1/preferences',json={'allergies':['peanut'],'meals':['dinner']})
        self.assertEqual(r.status_code,200)
        result=self.client.get('/api/v1/recommendations/daily').json()['items']
        self.assertTrue(all('peanut' not in f['ingredients'] for f in result))
    def test_vegan_and_prep_constraints(self):
        self.client.put('/api/v1/preferences',json={'diet':'vegan','meals':['dinner'],'max_minutes':25})
        result=self.client.get('/api/v1/recommendations/daily').json()['items']
        self.assertTrue(all(f['diet']=='vegan' and f['minutes']<=25 for f in result))
    def test_portion_scaled_log(self):
        self.client.post('/api/v1/meals/log',json={'food_id':'dal-khichdi','servings':2})
        totals=self.client.get('/api/v1/nutrition/daily').json()['totals']
        self.assertEqual(totals['calories'],840)
        self.assertEqual(totals['protein'],32)
    def test_feedback_and_history(self):
        self.assertEqual(self.client.post('/api/v1/feedback',json={'food_id':'berry-oats','action':'like'}).status_code,200)
        result=self.client.get('/api/v1/history').json()['items']
        self.assertTrue(any(x['kind']=='feedback' for x in result))
    def test_unknown_food_rejected(self):
        self.assertEqual(self.client.post('/api/v1/meals/log',json={'food_id':'nope'}).status_code,404)
    def test_health(self): self.assertEqual(self.client.get('/health').json()['status'],'ok')
    def test_ai_request_filters_after_model_interpretation(self):
        self.client.put('/api/v1/preferences',json={'diet':'any','allergies':['peanut'],'meals':['breakfast','lunch','dinner'],'max_minutes':60})
        parsed={'meal_type':'lunch','diet':'vegan','max_minutes':25,'include_ingredients':['chickpea'],'avoid_ingredients':[]}
        explanations={'items':[{'id':'chana-salad','why':'Vegan chickpeas with a 20 minute prep.'},{'id':'peanut-noodles','why':'unsafe hallucinated id'}]}
        with patch.object(api.intelligence,'chat_json',side_effect=[parsed,explanations]):
            response=self.client.post('/api/v1/recommendations/ask',json={'request':'quick vegan chickpea lunch'})
        self.assertEqual(response.status_code,200)
        result=response.json()
        self.assertTrue(result['ai_used'])
        self.assertEqual([x['id'] for x in result['items']],['chana-salad'])
        self.assertEqual(result['items'][0]['why'],'Vegan chickpeas with a 20 minute prep.')
    def test_ai_failure_uses_constrained_fallback(self):
        with patch.object(api.intelligence,'chat_json',side_effect=api.intelligence.ProviderError('offline')):
            response=self.client.post('/api/v1/recommendations/ask',json={'request':'quick vegan lunch with chickpeas'})
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['ai_used'])
        self.assertTrue(all(x['diet']=='vegan' and x['category']=='lunch' for x in response.json()['items']))

if __name__=='__main__': unittest.main()
