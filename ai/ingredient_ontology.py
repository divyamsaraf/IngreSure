from typing import List, Optional, Set, Dict

# --- INGREDIENT CATEGORIES ---
DAIRY = {"milk", "cream", "butter", "ghee", "whey", "casein", "lactose", "sodium caseinate", "milk fat", "yogurt", "cheese", "curd"}
MEAT = {"meat", "beef", "pork", "pig", "chicken", "lamb", "mutton", "goat", "turkey", "duck", "bacon", "ham", "sausage", "pepperoni", "salami", "animal fat", "lard", "tallow", "suet", "gelatin", "rennet", "pepsin", "calf"}
BEEF = {"beef", "calf", "veal", "beef extract"}
PORK = {"pork", "pig", "ham", "bacon", "lard", "pork fat", "gelatin"} # Gelatin usually pork/beef
EGG = {"egg", "eggs", "egg white", "egg yolk", "albumin"}
SEAFOOD = {"fish", "tuna", "salmon", "cod", "anchovy", "shellfish", "shrimp", "crab", "lobster", "oyster", "clam", "prawn", "squid", "calamari"}
ROOT_VEG = {"onion", "garlic", "potato", "carrot", "ginger", "radish", "turnip", "beetroot", "sweet potato", "scallion", "shallot", "leek"}
ALCOHOL = {"alcohol", "wine", "beer", "rum", "whiskey", "vodka", "liqueur", "cider", "spirit"}

# --- UNIVERSAL SAFE INGREDIENTS ---
# Always safe unless specific constraint (like sugar/starch is generally fine everywhere)
UNIVERSAL_SAFE = {
    "water", "sugar", "salt", "corn syrup", "dextrose", "fructose", "glucose",
    "wheat", "flour", "rice", "starch", "corn starch", "potato starch", "modified starch",
    "baking soda", "baking powder", "citric acid", "agar agar",
    "soy lecithin", "sunflower lecithin", "vegetable oil", "canola oil",
    "olive oil", "coconut oil", "palm oil", "cocoa butter", "cocoa mass",
    "hydrogenated vegetable oil", "hydrogenated oil", "beta carotene",
    "yeast", "pectin", "guar gum", "xanthan gum", "locust bean gum",
    "carrageenan", "calcium chloride", "potassium sorbate", "sodium benzoate",
    "aspartame", "sucralose", "acesulfame k", "saccharin", "stevia", "erythritol",
    "natural flavor", "natural flavors", "artificial flavor", "artificial flavors", "flavor" 
    # Flavors are considered safe by default in this ontology unless animal-derived is explicitly flagged
    # but we will handle ambiguity if needed. User requested "Safe unless explicitly labeled".
}

# --- AMBIGUOUS / CAUTION ---
AMBIGUOUS_SET = {
    "glycerin", "glycerol", "e422", "mono- and diglycerides", "e471", "polysorbate", 
    "enzymes", "rennet", "lipase", "protease", "stearic acid", "magnesium stearate", "vitamin a", "retinol"
}

def normalize_ingredient(ing: str) -> str:
    return ing.lower().strip().replace("*", "").replace("  ", " ")

class FastPathResult:
    def __init__(self, verdict: str, logic: Optional[List[str]] = None):
        self.verdict = verdict  # SAFE, NOT_SUITABLE, HANDOFF
        self.logic = logic or []

def evaluate_fast_path(ingredients: List[str], profile_str: str = "general") -> FastPathResult:
    """
    Evaluates ingredients based on a granular profile string (e.g. "hindu vegan").
    """
    profile_str = profile_str.lower()
    
    # 1. Determine constraints based on profile keywords
    blocked_sets: List[Set[str]] = []
    allowed_sets: List[Set[str]] = []
    
    # Base Rules
    if "jain" in profile_str:
        blocked_sets.extend([MEAT, SEAFOOD, EGG, ROOT_VEG])
        # Jain Vegan vs Jain (Dairy OK)
        if "vegan" in profile_str:
            blocked_sets.append(DAIRY)
        else:
            allowed_sets.append(DAIRY) # Explicitly allow dairy
            
    elif "vegan" in profile_str:
        blocked_sets.extend([MEAT, SEAFOOD, EGG, DAIRY])
        # Block honey/gelatin logic handled by keywords/MEAT set inclusion
        blocked_sets.append({"honey", "shellac", "carmine", "e120", "vitamin d3"})
        
    elif "hindu" in profile_str:
        # Hindu Non-Veg vs Veg
        if "non-veg" in profile_str or "non veg" in profile_str:
             blocked_sets.append(BEEF)
             # Allowed: Meat (Generic), Seafood, Egg, Dairy
             allowed_sets.extend([MEAT, SEAFOOD, EGG, DAIRY])
        else:
             # Hindu Veg (Default)
             blocked_sets.extend([MEAT, SEAFOOD, EGG])
             # Check if vegan specified
             if "vegan" in profile_str:
                 blocked_sets.append(DAIRY)
             else:
                 allowed_sets.append(DAIRY)

    elif "halal" in profile_str:
        blocked_sets.extend([PORK, ALCOHOL])
        # Note: Non-halal meat is blocked, but we can't detect "Non-Halal Chicken" by string.
        # We assume "Chicken" is safe unless user says "Halal Chicken Only" - strictness varies.
        # For safety app: Block Pork/Alcohol strictly. Flag Meat as Ambiguous?
        # User said: "Halal -> Pork, alcohol... NO; plant-based OK".
        # We will assume generic meat is suspect? Or Safe?
        # Let's block definite Haram.
        
    elif "vegetarian" in profile_str:
        blocked_sets.extend([MEAT, SEAFOOD, EGG])
        allowed_sets.append(DAIRY)

    elif "kosher" in profile_str:
        blocked_sets.extend([PORK, SEAFOOD]) # Shellfish in SEAFOOD need separation?
        # Kosher rules are complex. Block Pork/Shellfish.
        blocked_sets.append({"shrimp", "crab", "lobster", "oyster", "clam", "shellfish"})
        
    elif "sikh" in profile_str:
        blocked_sets.append({"halal", "kutha"}) # Mainly method of slaughter.
        if "vegetarian" in profile_str:
            blocked_sets.extend([MEAT, SEAFOOD, EGG])
            
    # Combine sets
    combined_block = set().union(*blocked_sets) if blocked_sets else set()
    combined_allow = set().union(*allowed_sets) if allowed_sets else set()
    
    # Universal Safe is always valid base
    # But if profile is "No Sugar" (not implemented), we would remove it.
    # For now, UNIVERSAL_SAFE is truly universal for these religious/ethical profiles.
    
    normalized_inputs = [normalize_ingredient(i) for i in ingredients]
    
    # --- CHECK LOGIC ---
    
    blocked_found = []
    
    for ing in normalized_inputs:
        # Check Explicit Block
        for b in combined_block:
            if b in ing:
                blocked_found.append(ing)
                break
        if blocked_found and ing == blocked_found[-1]: continue
        
    if blocked_found:
        return FastPathResult("NOT_SUITABLE", blocked_found)
        
    # Check Safe / Ambiguous
    ambiguous_found = []
    unknowns = []
    valid_ingredients = []

    for ing in normalized_inputs:
        # 1. Is it safe? (Universal or Explicitly Allowed)
        is_safe = False
        if ing in UNIVERSAL_SAFE: is_safe = True
        if not is_safe:
             for s in combined_allow:
                 if s in ing: 
                     is_safe = True
                     break
        
        if is_safe:
            valid_ingredients.append(ing)
            continue

        # 2. Is it ambiguous?
        is_ambiguous = False
        for a in AMBIGUOUS_SET:
            if a in ing:
                ambiguous_found.append(ing)
                is_ambiguous = True
                break
        if is_ambiguous:
            continue
            
        unknowns.append(ing)

    if not ambiguous and not unknowns:
        return FastPathResult("SAFE", valid_ingredients)

    if ambiguous or unknowns:
        return FastPathResult("HANDOFF", ambiguous + unknowns)

    return FastPathResult("HANDOFF", normalized_inputs)
