from typing import List, Dict

class DietaryRuleEngine:
    """
    Deterministic rule engine for dietary classification.
    """

    # --- Knowledge Base ---
    FORBIDDEN = {
        "Vegan": {
            "keywords": ["milk", "whey", "casein", "butter", "ghee", "egg", "honey", "gelatin", "carmine", "shellac", "collagen", "lard", "tallow"],
            "ambiguous": ["natural flavor", "mono-glycerides", "diglycerides", "glycerin", "caramel color"]
        },
        "Jain": {
            "keywords": ["onion", "garlic", "potato", "carrot", "radish", "beet", "yam", "ginger", "egg", "meat", "fish", "gelatin", "honey", "alcohol"],
            "ambiguous": ["yeast", "natural flavor"]
        },
        "Halal": {
            "keywords": ["pork", "lard", "bacon", "ham", "alcohol", "wine", "beer", "gelatin", "carmine", "vanilla extract"],
            "ambiguous": ["natural flavor", "rennet", "enzymes", "emulsifier", "glycerin"]
        },
        "Hindu Veg": {
            "keywords": ["egg", "meat", "beef", "chicken", "fish", "pork", "gelatin", "lard"],
            "ambiguous": []
        }
    }

    @staticmethod
    def classify(ingredients: List[str]) -> Dict[str, Dict]:
        """
        Classifies a list of ingredients against all diets.
        Returns: { "Vegan": { "status": "red"|"yellow"|"green", "reason": "..." } }
        """
        scorecard = {}

        for diet, rules in DietaryRuleEngine.FORBIDDEN.items():
            status = "green"
            reasons = []
            
            # Check each ingredient
            for ingredient in ingredients:
                ing_lower = ingredient.lower()
                
                # Check Forbidden
                for forbidden in rules["keywords"]:
                    if forbidden in ing_lower:
                        status = "red"
                        reasons.append(f"Contains {forbidden} ({ingredient})")
                        break # Stop checking this ingredient if already red
                
                # Check Ambiguous (only if not already red)
                if status != "red":
                    for ambiguous in rules["ambiguous"]:
                        if ambiguous in ing_lower:
                            status = "yellow"
                            reasons.append(f"Contains ambiguous {ambiguous} ({ingredient})")
            
            scorecard[diet] = {
                "status": status,
                "reason": "; ".join(reasons) if reasons else "No forbidden ingredients detected."
            }
            
        return scorecard
