"""Pure recommendation and nutrition rules, kept independent of web/database libraries."""
def eligible(food, diet="any", allergies=None, avoid=None, max_minutes=60):
    allergies = [x.lower().strip() for x in (allergies or [])]
    avoid = [x.lower().strip() for x in (avoid or [])]
    if diet == "vegan" and food["diet"] != "vegan": return False
    if diet == "vegetarian" and food["diet"] == "non-vegetarian": return False
    if food["minutes"] > max_minutes: return False
    tokens = [s.lower().strip() for s in food["ingredients"] + food["allergens"]]
    if any(any(a in token for token in tokens) for a in allergies): return False
    if any(any(a in token for token in tokens) for a in avoid): return False
    return True

def scale_nutrition(food, servings):
    """Return scaled available nutrients; absent values remain absent."""
    return {key: food[key] * servings for key in ("calories", "protein", "carbs", "fat") if food.get(key) is not None}
