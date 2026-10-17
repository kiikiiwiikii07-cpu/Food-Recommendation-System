import unittest
from backend.rules import eligible, scale_nutrition

FOOD = {"diet":"vegan","minutes":20,"ingredients":["chickpeas","lemon"],"allergens":[],"calories":390,"protein":18,"carbs":55,"fat":12}

class RulesTests(unittest.TestCase):
    def test_allergy_excludes_ingredient_substring(self): self.assertFalse(eligible(FOOD, allergies=["chickpea"]))
    def test_diet_and_time_constraints(self):
        self.assertTrue(eligible(FOOD, diet="vegan", max_minutes=20))
        self.assertTrue(eligible(FOOD, diet="vegetarian", max_minutes=20))
        meat = dict(FOOD, diet="non-vegetarian")
        self.assertFalse(eligible(meat, diet="vegetarian", max_minutes=20))
        self.assertFalse(eligible(FOOD, max_minutes=19))
    def test_scaled_nutrition_and_missing_value(self):
        food = dict(FOOD, fat=None)
        self.assertEqual(scale_nutrition(food, 2), {"calories":780,"protein":36,"carbs":110})

if __name__ == "__main__": unittest.main()
