from typing import Dict, List, Set, Optional, NamedTuple

# --- 1. DATA STRUCTURES ---

class IngredientProperties(NamedTuple):
    source: str  # "plant", "animal", "milk", "synthetic", "mineral", "insect", "fish", "shellfish", "egg", "alcohol"
    allergens: Set[str] # "milk", "egg", "peanut", "nut", "soy", "wheat", "fish", "shellfish"
    notes: str
    ambiguous: bool = False

# --- 2. THE COMPREHENSIVE ONTOLOGY (O(1) Lookup) ---
# All keys Must be normalized (lowercase, unique)

INGREDIENT_DB: Dict[str, IngredientProperties] = {
    # --- WATER & BASICS ---
    "water": IngredientProperties("mineral", set(), "Universal safe"),
    "carbonated water": IngredientProperties("mineral", set(), "Universal safe"),
    "sparkling water": IngredientProperties("mineral", set(), "Universal safe"),
    
    # --- SUGARS & SWEETENERS ---
    "sugar": IngredientProperties("plant", set(), "Universal safe"),
    "cane sugar": IngredientProperties("plant", set(), "Universal safe"),
    "beet sugar": IngredientProperties("plant", set(), "Universal safe"),
    "fructose": IngredientProperties("plant", set(), "Universal safe"),
    "glucose": IngredientProperties("plant", set(), "Universal safe"),
    "dextrose": IngredientProperties("plant", set(), "Universal safe"),
    "corn syrup": IngredientProperties("plant", set(), "Universal safe"),
    "high fructose corn syrup": IngredientProperties("plant", set(), "Universal safe"),
    "maltodextrin": IngredientProperties("plant", set(), "Universal safe"),
    "honey": IngredientProperties("animal", set(), "Non-vegan"), # Animal produced (bee)
    "aspartame": IngredientProperties("synthetic", set(), "Artificial sweetener"),
    "sucralose": IngredientProperties("synthetic", set(), "Artificial sweetener"),
    "acesulfame potassium": IngredientProperties("synthetic", set(), "Artificial sweetener"),
    "acesulfame k": IngredientProperties("synthetic", set(), "Artificial sweetener"),
    "saccharin": IngredientProperties("synthetic", set(), "Artificial sweetener"),
    "stevia": IngredientProperties("plant", set(), "Natural sweetener"),
    "erythritol": IngredientProperties("plant", set(), "Sugar alcohol"),
    "xylitol": IngredientProperties("plant", set(), "Sugar alcohol"),
    "sorbitol": IngredientProperties("plant", set(), "Sugar alcohol"),
    
    # --- SALTS & MINERALS ---
    "salt": IngredientProperties("mineral", set(), "Universal safe"),
    "sea salt": IngredientProperties("mineral", set(), "Universal safe"),
    "baking soda": IngredientProperties("mineral", set(), "Universal safe"),
    "sodium bicarbonate": IngredientProperties("mineral", set(), "Universal safe"),
    "calcium carbonate": IngredientProperties("mineral", set(), "Universal safe"),
    "calcium chloride": IngredientProperties("mineral", set(), "Universal safe"),
    "potassium chloride": IngredientProperties("mineral", set(), "Universal safe"),
    
    # --- OILS & FATS ---
    "vegetable oil": IngredientProperties("plant", set(), "Universal safe"),
    "canola oil": IngredientProperties("plant", set(), "Universal safe"),
    "soybean oil": IngredientProperties("plant", {"soy"}, "Universal safe"),
    "sunflower oil": IngredientProperties("plant", set(), "Universal safe"),
    "olive oil": IngredientProperties("plant", set(), "Universal safe"),
    "coconut oil": IngredientProperties("plant", {"nut"}, "Universal safe"), # FDA classifies coconut as nut
    "palm oil": IngredientProperties("plant", set(), "Universal safe"),
    "hydrogenated vegetable oil": IngredientProperties("plant", set(), "Universal safe"),
    "hydrogenated oil": IngredientProperties("plant", set(), "Universal safe"),
    "cocoa butter": IngredientProperties("plant", set(), "Universal safe"),
    "butter": IngredientProperties("milk", {"milk"}, "Dairy"),
    "ghee": IngredientProperties("milk", {"milk"}, "Dairy"),
    "cream": IngredientProperties("milk", {"milk"}, "Dairy"),
    "milk fat": IngredientProperties("milk", {"milk"}, "Dairy"),
    "lard": IngredientProperties("animal", set(), "Pork fat"),
    "tallow": IngredientProperties("animal", set(), "Beef fat"),
    "suet": IngredientProperties("animal", set(), "Beef fat"),
    "animal fat": IngredientProperties("animal", set(), "Generic animal fat"),
    "fish oil": IngredientProperties("fish", {"fish"}, "Fish derived"),
    
    # --- DAIRY ---
    "milk": IngredientProperties("milk", {"milk"}, "Dairy"),
    "skim milk": IngredientProperties("milk", {"milk"}, "Dairy"),
    "whole milk": IngredientProperties("milk", {"milk"}, "Dairy"),
    "milk powder": IngredientProperties("milk", {"milk"}, "Dairy"),
    "whey": IngredientProperties("milk", {"milk"}, "Dairy"),
    "whey protein": IngredientProperties("milk", {"milk"}, "Dairy"),
    "casein": IngredientProperties("milk", {"milk"}, "Dairy"),
    "sodium caseinate": IngredientProperties("milk", {"milk"}, "Dairy"),
    "calcium caseinate": IngredientProperties("milk", {"milk"}, "Dairy"),
    "lactose": IngredientProperties("milk", {"milk"}, "Dairy"),
    "yogurt": IngredientProperties("milk", {"milk"}, "Dairy"),
    "cheese": IngredientProperties("milk", {"milk"}, "Dairy"),
    "curd": IngredientProperties("milk", {"milk"}, "Dairy"),
    
    # --- MEAT ---
    "beef": IngredientProperties("animal", set(), "Beef"),
    "steak": IngredientProperties("animal", set(), "Beef"),
    "veal": IngredientProperties("animal", set(), "Beef"),
    "calf": IngredientProperties("animal", set(), "Beef"),
    "pork": IngredientProperties("animal", set(), "Pork"),
    "ham": IngredientProperties("animal", set(), "Pork"),
    "bacon": IngredientProperties("animal", set(), "Pork"),
    "sausage": IngredientProperties("animal", set(), "Generic meat"), # Often pork
    "chicken": IngredientProperties("animal", set(), "Poultry"),
    "turkey": IngredientProperties("animal", set(), "Poultry"),
    "duck": IngredientProperties("animal", set(), "Poultry"),
    "lamb": IngredientProperties("animal", set(), "Meat"),
    "mutton": IngredientProperties("animal", set(), "Meat"),
    "goat": IngredientProperties("animal", set(), "Meat"),
    "meat": IngredientProperties("animal", set(), "Generic meat"),
    "gelatin": IngredientProperties("animal", set(), "Animal connective tissue"),
    "rennet": IngredientProperties("animal", set(), "Enzyme from stomach"), # Assumed animal unless "microbial rennet"
    "animal rennet": IngredientProperties("animal", set(), "Enzyme from stomach"),
    "pepsin": IngredientProperties("animal", set(), "Enzyme from stomach"),
    
    # --- FISH & SEAFOOD ---
    "fish": IngredientProperties("fish", {"fish"}, "Fish"),
    "tuna": IngredientProperties("fish", {"fish"}, "Fish"),
    "salmon": IngredientProperties("fish", {"fish"}, "Fish"),
    "cod": IngredientProperties("fish", {"fish"}, "Fish"),
    "anchovy": IngredientProperties("fish", {"fish"}, "Fish"),
    "shrimp": IngredientProperties("shellfish", {"shellfish"}, "Shellfish"),
    "crab": IngredientProperties("shellfish", {"shellfish"}, "Shellfish"),
    "lobster": IngredientProperties("shellfish", {"shellfish"}, "Shellfish"),
    "clam": IngredientProperties("shellfish", {"shellfish"}, "Shellfish"),
    "oyster": IngredientProperties("shellfish", {"shellfish"}, "Shellfish"),
    "shellfish": IngredientProperties("shellfish", {"shellfish"}, "Shellfish"),
    
    # --- EGGS ---
    "egg": IngredientProperties("egg", {"egg"}, "Egg"),
    "eggs": IngredientProperties("egg", {"egg"}, "Egg"),
    "egg white": IngredientProperties("egg", {"egg"}, "Egg"),
    "egg yolk": IngredientProperties("egg", {"egg"}, "Egg"),
    "albumin": IngredientProperties("egg", {"egg"}, "Egg protein"),
    
    # --- GRAINS & FLOURS ---
    "wheat": IngredientProperties("plant", {"wheat"}, "Grain"),
    "wheat flour": IngredientProperties("plant", {"wheat"}, "Grain"),
    "flour": IngredientProperties("plant", {"wheat"}, "Grain"),
    "rice": IngredientProperties("plant", set(), "Grain"),
    "rice flour": IngredientProperties("plant", set(), "Grain"),
    "corn": IngredientProperties("plant", set(), "Grain"),
    "corn flour": IngredientProperties("plant", set(), "Grain"),
    "corn starch": IngredientProperties("plant", set(), "Grain"),
    "starch": IngredientProperties("plant", set(), "Plant starch"),
    "modified starch": IngredientProperties("plant", set(), "Plant starch"),
    "potato starch": IngredientProperties("plant", set(), "Plant starch"),
    "oats": IngredientProperties("plant", set(), "Grain"),
    "barley": IngredientProperties("plant", {"wheat"}, "Grain (Gluten)"),
    "rye": IngredientProperties("plant", {"wheat"}, "Grain (Gluten)"),
    "malt": IngredientProperties("plant", {"wheat"}, "Barley derivative"),
    
    # --- PLANT-BASED MEAT ALTERNATIVES ---
    "plant-based meat": IngredientProperties("plant", set(), "Plant-based alternative"),
    "veggie burger": IngredientProperties("plant", set(), "Plant-based alternative"),
    "veggie meat": IngredientProperties("plant", set(), "Plant-based alternative"),
    "vegan sausage": IngredientProperties("plant", set(), "Plant-based alternative"),
    "soy meat": IngredientProperties("plant", {"soy"}, "Plant-based alternative"),
    "tofu patty": IngredientProperties("plant", {"soy"}, "Plant-based alternative"),
    "seitan": IngredientProperties("plant", {"gluten", "wheat"}, "Wheat gluten (Plant-based)"),
    "textured vegetable protein": IngredientProperties("plant", {"soy"}, "Plant-based alternative"),
    "tvp": IngredientProperties("plant", {"soy"}, "Plant-based alternative"),
    "jackfruit meat": IngredientProperties("plant", set(), "Plant-based alternative"),
    "mushroom meat": IngredientProperties("plant", set(), "Plant-based alternative"),
    "bean-based meat": IngredientProperties("plant", set(), "Plant-based alternative"),
    "meatless meat": IngredientProperties("plant", set(), "Plant-based alternative"),
    "impossible meat": IngredientProperties("plant", {"soy"}, "Plant-based alternative"),
    "beyond meat": IngredientProperties("plant", set(), "Plant-based alternative"),
    "mock duck": IngredientProperties("plant", {"gluten", "wheat"}, "Plant-based alternative"),

    # --- VEGETABLES (Roots marked for Jain) ---
    "onion": IngredientProperties("plant", set(), "Root vegetable"),
    "onion powder": IngredientProperties("plant", set(), "Root vegetable"),
    "garlic": IngredientProperties("plant", set(), "Root vegetable"),
    "garlic powder": IngredientProperties("plant", set(), "Root vegetable"),
    "potato": IngredientProperties("plant", set(), "Root vegetable"),
    "carrot": IngredientProperties("plant", set(), "Root vegetable"),
    "ginger": IngredientProperties("plant", set(), "Root vegetable"),
    "tomato": IngredientProperties("plant", set(), " vegetable"),
    "spinach": IngredientProperties("plant", set(), " vegetable"),
    
    # --- ADDITIVES & PRESERVATIVES ---
    "citric acid": IngredientProperties("plant", set(), "Fermentation product"),
    "ascorbic acid": IngredientProperties("plant", set(), "Vitamin C"),
    "lecithin": IngredientProperties("plant", {"soy"}, "Soy usually"),
    "soy lecithin": IngredientProperties("plant", {"soy"}, "Soy derived"),
    "sunflower lecithin": IngredientProperties("plant", set(), "Sunflower derived"),
    "pectin": IngredientProperties("plant", set(), "Fruit derived"),
    "agar agar": IngredientProperties("plant", set(), "Seaweed derived"),
    "carrageenan": IngredientProperties("plant", set(), "Seaweed derived"),
    "guar gum": IngredientProperties("plant", set(), "Bean derived"),
    "xanthan gum": IngredientProperties("plant", set(), "Fermentation product"),
    "locust bean gum": IngredientProperties("plant", set(), "Bean derived"),
    "acacia gum": IngredientProperties("plant", set(), "Tree sap"),
    "gum arabic": IngredientProperties("plant", set(), "Tree sap"),
    "potassium sorbate": IngredientProperties("synthetic", set(), "Preservative"),
    "sodium benzoate": IngredientProperties("synthetic", set(), "Preservative"),
    "calcium propionate": IngredientProperties("synthetic", set(), "Preservative"),
    "sodium polyphosphate": IngredientProperties("synthetic", set(), "Emulsifier"),
    "polysorbate": IngredientProperties("synthetic", set(), "Emulsifier"),
    "polysorbate 60": IngredientProperties("synthetic", set(), "Emulsifier"),
    "polysorbate 80": IngredientProperties("synthetic", set(), "Emulsifier"),
    "mono- and diglycerides": IngredientProperties("plant", set(), "Usually plant oil derived"), # Can be animal but standard industry is plant. We mark plant for safety app default, or ambiguous? User said "No over hedging". Industry standard is plant. 
    "glycerin": IngredientProperties("plant", set(), "Usually plant derived"),
    "glycerol": IngredientProperties("plant", set(), "Usually plant derived"),
    
    # --- COLORS ---
    "red 40": IngredientProperties("synthetic", set(), "Artificial color"),
    "yellow 5": IngredientProperties("synthetic", set(), "Artificial color"),
    "blue 1": IngredientProperties("synthetic", set(), "Artificial color"),
    "beta carotene": IngredientProperties("plant", set(), "Natural color"),
    "carmine": IngredientProperties("insect", set(), "Insect derived"),
    "cochineal": IngredientProperties("insect", set(), "Insect derived"),
    "e120": IngredientProperties("insect", set(), "Insect derived"),
    "turmeric": IngredientProperties("plant", set(), "Natural color"),
    "annatto": IngredientProperties("plant", set(), "Natural color"),
    
    # --- FLAVORS ---
    "natural flavor": IngredientProperties("plant", set(), "Generally safe"), 
    "artificial flavor": IngredientProperties("synthetic", set(), "Safe"),
    "yeast extract": IngredientProperties("plant", set(), "Yeast"),
    "msg": IngredientProperties("plant", set(), "Fermentation"),
    "monosodium glutamate": IngredientProperties("plant", set(), "Fermentation"),
    "vanilla": IngredientProperties("plant", set(), "Plant"),
    "vanillin": IngredientProperties("synthetic", set(), "Synthetic"),
    
    # --- ALCOHOL ---
    "alcohol": IngredientProperties("alcohol", set(), "Alcohol"),
    "wine": IngredientProperties("alcohol", set(), "Alcohol"),
    "beer": IngredientProperties("alcohol", {"wheat"}, "Alcohol"),
    "rum": IngredientProperties("alcohol", set(), "Alcohol"),
    "cider": IngredientProperties("alcohol", set(), "Alcohol"),
}

# --- 3. PROFILE DEFINITIONS & RULES ---

class UserProfile(NamedTuple):
    diet: str # "hindu_veg", "hindu_non_veg", "jain", "vegan", "vegetarian", "halal", "kosher", "sikh", "general"
    dairy_allowed: bool
    allergens: Set[str]
    # religious_strictness: bool = True # Assume strict for now

def normalize_text(text: str) -> str:
    return text.lower().strip().replace("*", "").replace(".", "")

def evaluate_ingredient_risk(ingredient: str, profile: UserProfile) -> Dict:
    """
    O(1) Check.
    Returns: {"status": "SAFE"|"NOT_SAFE"|"UNCLEAR", "reason": str}
    """
    norm = normalize_text(ingredient)
    prop = INGREDIENT_DB.get(norm)
    
    # If not found, try simple substring matches for common categories
    if not prop:
        if "milk" in norm or "cream" in norm or "cheese" in norm: prop = INGREDIENT_DB["milk"]
        elif "beef" in norm: prop = INGREDIENT_DB["beef"]
        elif "pork" in norm or "bacon" in norm: prop = INGREDIENT_DB["pork"]
        elif "chicken" in norm: prop = INGREDIENT_DB["chicken"]
        elif "egg" in norm: prop = INGREDIENT_DB["egg"]
        elif "oil" in norm: prop = INGREDIENT_DB["vegetable oil"] # Assumption
        elif "flour" in norm: prop = INGREDIENT_DB["flour"]
        else:
            return {"status": "UNCLEAR", "reason": f"Unknown ingredient: {ingredient}"}

    # 1. ALLERGY CHECK
    for allergen in prop.allergens:
        if allergen in profile.allergens:
            return {"status": "NOT_SAFE", "reason": f"Contains {allergen} (allergen)"}
    
    # 2. DIET CHECK
    # Hindu Veg
    if profile.diet == "hindu_veg":
        if prop.source in ["animal", "fish", "shellfish", "egg", "insect"]:
            # Exception: Beef is bad even for non-veg, but this is veg profile so all meat bad.
            return {"status": "NOT_SAFE", "reason": f"Forbidden in Hindu Veg ({prop.notes})"}
        if prop.source == "milk" and not profile.dairy_allowed:
             return {"status": "NOT_SAFE", "reason": "Contains Dairy (Not allowed in profile)"}
             
    # Hindu Non-Veg
    elif profile.diet == "hindu_non_veg":
        if "beef" in prop.notes.lower() or "beef" in norm:
             return {"status": "NOT_SAFE", "reason": "Beef is strictly forbidden in Hindu diets"}
        if prop.source == "milk" and not profile.dairy_allowed:
             return {"status": "NOT_SAFE", "reason": "Contains Dairy (Not allowed in profile)"}

    # Jain
    elif profile.diet == "jain":
        if prop.source in ["animal", "fish", "shellfish", "egg", "insect"]:
             return {"status": "NOT_SAFE", "reason": "Animal products forbidden in Jainism"}
        if "root" in prop.notes.lower():
             return {"status": "NOT_SAFE", "reason": "Root vegetables forbidden in Jainism"}
        if prop.source == "milk" and not profile.dairy_allowed:
             return {"status": "NOT_SAFE", "reason": "Contains Dairy"}

    # Vegan
    elif profile.diet == "vegan":
        if prop.source in ["animal", "fish", "shellfish", "egg", "milk", "insect", "honey"]:
             return {"status": "NOT_SAFE", "reason": f"Animal/Dairy product ({prop.notes})"}
             
    # Vegetarian
    elif profile.diet == "vegetarian":
        if prop.source in ["animal", "fish", "shellfish", "insect"]:
             return {"status": "NOT_SAFE", "reason": "Meat/Seafood not vegetarian"}
        if prop.source == "egg": # Some vegetarians eat eggs, others don't. Assuming lacto-ovo default unless specified? 
            # Prompt doesn't specify rigid egg rule for generic 'vegetarian', but typical Western is OK. 
            # Reviewing Prompt Truth Table: "Vegetarian -> No meat/fish/egg/gelatin". 
            # Wait, standard vegetarian (Lacto-Ovo) allows egg. 
            # But Truth Table user provided earlier says: "Vegetarian: meat,fish,egg,gelatin... NO".
            # Okay, I will follow User Truth Table which implies Lacto-Vegetarian (Indian standard?).
            return {"status": "NOT_SAFE", "reason": "Egg not allowed in strict vegetarian profile"}

    # Halal
    elif profile.diet == "halal":
        if prop.source == "alcohol":
             return {"status": "NOT_SAFE", "reason": "Alcohol is Haram"}
        if "pork" in prop.notes.lower() or "pork" in norm or prop.source == "insect":
             return {"status": "NOT_SAFE", "reason": "Pork/Insect forbidden in Halal"}
        if prop.source in ["animal"] and "beef" not in norm and "pork" not in norm: 
            # Generic meat -> needs Halal cert. Safe app -> Block or Warn?
            # Prompt says "Deterministic... if ingredient is animal-derived and forbidden -> NOT SAFE".
            # For Halal, non-halal meat is forbidden. Since we can't verify cert, we mark NOT SAFE or UNCLEAR?
            # User example: "Chicken... Safe if Halal".
            return {"status": "NOT_SAFE", "reason": "Meat requires Halal certification"}
            
    # Kosher
    elif profile.diet == "kosher":
        if "pork" in prop.notes.lower() or prop.source == "shellfish" or prop.source == "insect":
             return {"status": "NOT_SAFE", "reason": "Non-Kosher"}
        if prop.source in ["animal", "meat"] and "pork" not in norm:
             return {"status": "NOT_SAFE", "reason": "Meat requires Kosher certification"}

    # Sikh
    elif profile.diet == "sikh":
        if "halal" in norm or "kutha" in norm:
             return {"status": "NOT_SAFE", "reason": "Kutha meat forbidden"}
        # Some Sikhs are veg, some non-veg. If generic Sikh -> Block Halal/Kutha.
        # User truth table says: "Sikh -> no Halal/Kutha meat".
        # If input is just "Chicken", we assume generic chicken is not Halal? Or safe?
        # Usually generic chicken in West is safe for Sikh (Jhatka or whatever). 
        # But for safety, "Meat" is usually flagged if profile is "Sikh Veg". 
        # If "Sikh Non-Veg", Chicken is SAFE.
        pass 

    # 3. UNIVERSAL ALLOWANCE Check
    # If we got here, no block triggered.
    return {"status": "SAFE", "reason": prop.notes}
