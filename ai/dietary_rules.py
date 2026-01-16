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

    # --- Cuisine Knowledge Base ---
    CUISINE_KEYWORDS = {
        "Italian": ["pasta", "pizza", "risotto", "spaghetti", "lasagna", "mozzarella", "parmesan", "basil", "oregano", "tomato sauce"],
        "Mexican": ["taco", "burrito", "quesadilla", "salsa", "guacamole", "tortilla", "jalapeno", "cilantro", "bean", "corn"],
        "Indian": ["curry", "masala", "tikka", "naan", "paneer", "biryani", "tandoori", "samosa", "chutney", "dal"],
        "Chinese": ["noodle", "fried rice", "dim sum", "soy sauce", "tofu", "wok", "sichuan", "dumpling", "spring roll"],
        "American": ["burger", "fries", "steak", "bbq", "sandwich", "hot dog", "wings", "ranch", "apple pie"],
        "Japanese": ["sushi", "ramen", "tempura", "miso", "teriyaki", "sashimi", "udon", "wasabi", "matcha"],
        "Mediterranean": ["hummus", "falafel", "pita", "olive", "feta", "gyro", "tzatziki", "kebab", "couscous"],
        "Thai": ["pad thai", "curry", "lemongrass", "coconut milk", "basil", "peanut", "satay", "tom yum"]
    }

    # --- Allergen Knowledge Base ---
    ALLERGEN_KEYWORDS = {
        "Peanuts": ["peanut", "groundnut"],
        "Tree Nuts": ["almond", "cashew", "walnut", "pecan", "pistachio", "macadamia", "hazelnut"],
        "Dairy": ["milk", "cheese", "cream", "butter", "yogurt", "whey", "casein", "lactose", "ghee"],
        "Eggs": ["egg", "mayonnaise", "meringue", "albumin"],
        "Wheat/Gluten": ["wheat", "barley", "rye", "flour", "bread", "pasta", "seitan", "couscous", "bulgur", "semolina"],
        "Soy": ["soy", "tofu", "edamame", "miso", "tempeh", "lecithin"],
        "Fish": ["fish", "salmon", "tuna", "cod", "tilapia", "anchovy"],
        "Shellfish": ["shrimp", "crab", "lobster", "prawn", "clam", "mussel", "oyster", "scallop"]
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

    @staticmethod
    def detect_cuisine(text: str) -> str:
        """
        Detects cuisine based on keywords in the text (name + description).
        Returns the most likely cuisine or "Global".
        """
        text_lower = text.lower()
        scores = {cuisine: 0 for cuisine in DietaryRuleEngine.CUISINE_KEYWORDS}
        
        for cuisine, keywords in DietaryRuleEngine.CUISINE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[cuisine] += 1
        
        # Find max score
        best_cuisine = max(scores, key=scores.get)
        if scores[best_cuisine] > 0:
            return best_cuisine
        return "Global"

    @staticmethod
    def detect_allergens(ingredients: List[str]) -> List[str]:
        """
        Detects allergens present in the ingredients list.
        Returns a list of detected allergens (e.g., ["Peanuts", "Dairy"]).
        """
        detected = set()
        for ingredient in ingredients:
            ing_lower = ingredient.lower()
            for allergen, keywords in DietaryRuleEngine.ALLERGEN_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in ing_lower:
                        detected.add(allergen)
                        break
        return list(detected)

    @staticmethod
    def extract_filters(query: str) -> Dict[str, List[str]]:
        """
        Parses a natural language query to extract dietary and allergen filters.
        Example: "What vegan options do you have without nuts?"
        Returns: { 
            "dietary": ["Vegan"], 
            "allergens": ["Peanuts", "Tree Nuts"] 
        }
        """
        query_lower = query.lower()
        filters = {"dietary": [], "allergens": []}
        
        # 1. Extract Dietary Filters
        # Simple keyword matching
        if "vegan" in query_lower:
            filters["dietary"].append("Vegan")
        if "vegetarian" in query_lower:
            filters["dietary"].append("Vegetarian")
        if "jain" in query_lower:
            filters["dietary"].append("Jain")
        if "halal" in query_lower:
            filters["dietary"].append("Halal")
        if "gluten-free" in query_lower or "gluten free" in query_lower:
            filters["allergens"].append("Wheat/Gluten") # Treat as allergen exclusion
            
        # 2. Extract Allergen Exclusions
        # Look for "no [allergen]", "free of [allergen]", "without [allergen]" queries
        # Or simplistic: if allergen keyword is mentioned with a negation context?
        # For now, let's look for explicit "nut-free", "no peanuts", etc. OR just allergen keywords if context implies exclusion?
        # Actually, "I am allergic to X" implies exclusion. "Does this have X?" implies checking for X.
        # This is hard for regex. 
        # Strategy: Match common "exclusion phrases" + allergen keyword.
        # But for V1, let's match explicit "allergy" mentions. e.g. "I have a peanut allergy" -> exclude Peanuts.
        
        # Simple map of user terms to keys
        term_map = {
            "nut": ["Peanuts", "Tree Nuts"],
            "peanut": ["Peanuts"],
            "dairy": ["Dairy"],
            "milk": ["Dairy"],
            "egg": ["Eggs"],
            "corn": [], # Not in our DB yet
            "soy": ["Soy"],
            "wheat": ["Wheat/Gluten"],
            "gluten": ["Wheat/Gluten"],
            "fish": ["Fish"],
            "shellfish": ["Shellfish"]
        }
        
        for term, allergens in term_map.items():
            # Check if term exists in query
            if term in query_lower:
                # Naive: assume if mentioned, it's an unwanted allergen? 
                # "I want peanut butter" vs "I am allergic to peanuts". 
                # Context is needed. 
                # Safety First: If "allergy", "allergic", "no ", "without ", "free" is nearby?
                # Let's check for trigger words.
                trigger_words = ["no ", "without ", "free", "allerg", "intolera"]
                if any(t in query_lower for t in trigger_words):
                    filters["allergens"].extend(allergens)
                    
        # Deduplicate
        filters["allergens"] = list(set(filters["allergens"]))
        
        return filters
