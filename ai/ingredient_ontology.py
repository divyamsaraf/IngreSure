from typing import List, Tuple, Optional, Set

# --- 1. DEFINITIONS ---

# Universal Safe Ingredients (Apps to all profiles unless typically checked)
# Note: This is an expanding list.
UNIVERSAL_SAFE = {
    "water", "sugar", "salt", "corn syrup", "dextrose", "fructose", 
    "wheat", "flour", "rice", "starch", "corn starch", "potato starch",
    "baking soda", "baking powder", "citric acid", "agar agar", 
    "soy lecithin", "sunflower lecithin", "vegetable oil", "canola oil",
    "olive oil", "coconut oil", "palm oil", "cocoa butter", "cocoa mass",
    "yeast", "pectin", "guar gum", "xanthan gum", "locust bean gum",
    "calcium chloride", "potassium sorbate", "sodium benzoate"
}

# Profile-Specific Safe Extensions
SAFE_EXTENSIONS = {
    "hindu": {"milk", "cream", "butter", "ghee", "whey", "casein", "lactose", "sodium caseinate", "milk fat"},
    "jain": {"milk", "cream", "butter", "ghee", "whey", "casein", "lactose", "sodium caseinate"}, # Dairy OK, Root Veg NO
    "vegan": set(), # Strictly Plant/Synthetic only
    "halal": {"milk", "cream", "butter", "ghee", "whey", "casein", "sodium caseinate", "fish", "egg"} # Seafood usually Halal
}

# Block Sets (Explicitly Banned)
BLOCK_SETS = {
    "hindu": {
        "meat", "beef", "pork", "pig", "chicken", "fish", "seafood", "egg", "gelatin", 
        "lard", "tallow", "suet", "animal fat", "rennet", "pepsin", "calf"
    },
    "jain": {
        "meat", "beef", "pork", "pig", "chicken", "fish", "seafood", "egg", "gelatin", 
        "lard", "honey", "onion", "garlic", "potato", "carrot", "beef extract", "root"
    },
    "vegan": {
        "meat", "beef", "pork", "pig", "chicken", "fish", "seafood", "egg", "gelatin", 
        "lard", "tallow", "suet", "honey", "milk", "cream", "butter", "ghee", 
        "whey", "casein", "caseinate", "lactose", "shellac", "carmine", "e120", "e904", "vitamin d3"
    },
    "halal": {
        "pork", "pig", "ham", "bacon", "lard", "gelatin", "alcohol", "wine", "beer", "rum", 
        "liqueur", "vanilla extract", "e120", "carmine"
    }
}

# Ambiguous / Source-Dependent (Triggers Caution/Slow Path)
AMBIGUOUS_SET = {
    "glycerin", "glycerol", "e422",
    "mono- and diglycerides", "monoglycerides", "diglycerides", "e471",
    "polysorbate", "polysorbate 60", "polysorbate 80", "e433", "e435",
    "natural flavor", "natural flavors", "flavor", "artificial flavor",
    "enzymes", "rennet", "lipase", "protease",
    "stearic acid", "magnesium stearate",
    "vitamin a", "retinol" # Can be gelatin stabilized
}

# --- 2. FAST PATH LOGIC ---

def normalize_ingredient(ing: str) -> str:
    return ing.lower().strip().replace("*", "").replace("  ", " ")

class FastPathResult:
    def __init__(self, verdict: str, logic: List[str] = None):
        self.verdict = verdict # SAFE, NOT_SUITABLE, HANDOFF
        self.logic = logic or []

def evaluate_fast_path(ingredients: List[str], profile: str = "hindu") -> FastPathResult:
    """
    Returns immediate verdict if conditions met.
    Else returns HANDOFF.
    """
    profile = profile.lower()
    
    # 1. Expand Sets
    safe_set = UNIVERSAL_SAFE.union(SAFE_EXTENSIONS.get(profile, set()))
    block_set = BLOCK_SETS.get(profile, set())
    
    normalized_inputs = [normalize_ingredient(i) for i in ingredients]
    
    # 2. Check for BLOCKED (Priority 1)
    banned_found = []
    for ing in normalized_inputs:
        # Check explicit block
        if ing in block_set:
            banned_found.append(ing)
            continue
        # Check keyword blocking (e.g. "beef" in "beef stock")
        for banned in block_set:
            if banned in ing: # Robust substr check
               banned_found.append(ing)
               break
    
    if banned_found:
        return FastPathResult("NOT SUITABLE", logic=banned_found)

    # 3. Check for AMBIGUOUS (Priority 2 -> Handoff)
    for ing in normalized_inputs:
        if ing in AMBIGUOUS_SET:
            return FastPathResult("HANDOFF", logic=[f"Ambiguous: {ing}"])
        for amb in AMBIGUOUS_SET:
            if amb in ing:
                 return FastPathResult("HANDOFF", logic=[f"Ambiguous: {ing}"])

    # 4. Check for SAFE (Priority 3)
    # MUST be all in safe set
    unknowns = []
    for ing in normalized_inputs:
        found_safe = False
        if ing in safe_set:
            found_safe = True
        else:
            # Substring check against safe set (CAREFUL here, strict rules)
            # Actually, per user rules: "If any doubt exists, SAFE is forbidden."
            # So we strictly assume if not in SAFE_SET, it is Unknown -> Handoff.
            pass
        
        if not found_safe:
           unknowns.append(ing)

    if not unknowns:
        return FastPathResult("SAFE", logic=["All ingredients recognized as safe."])

    # 5. Default Handoff (Unknown ingredients)
    return FastPathResult("HANDOFF", logic=[f"Unknown: {unknowns}"])
