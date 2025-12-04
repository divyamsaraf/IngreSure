import json
import requests
import os

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"

def verify_menu_item(item_name, description, ingredients, claimed_diet_types):
    """
    Verifies if the menu item details match the ingredients using Mistral 7B.
    """
    prompt = f"""
    You are a food safety and dietary expert. Verify the following menu item:
    
    Item Name: {item_name}
    Description: {description}
    Ingredients: {json.dumps(ingredients)}
    Claimed Diet Types: {', '.join(claimed_diet_types)}
    
    Task:
    1. Check if the ingredients match the item name and description.
    2. Verify if the claimed diet types are valid based on the ingredients.
    3. Identify any undeclared allergens or inconsistencies.
    
    Respond in JSON format with the following structure:
    {{
        "is_consistent": boolean,
        "confidence_score": float (0.0 to 1.0),
        "issues": [list of strings describing issues found],
        "suggested_corrections": {{ "diet_types": [list of correct diet types] }}
    }}
    """
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        return json.loads(result['response'])
    except Exception as e:
        return {
            "error": str(e),
            "is_consistent": False,
            "confidence_score": 0.0,
            "issues": ["AI Verification Failed"]
        }

if __name__ == "__main__":
    # Test run
    test_item = {
        "item_name": "Vegan Burger",
        "description": "Plant-based patty with lettuce and tomato.",
        "ingredients": ["soy protein", "lettuce", "tomato", "bun (wheat)"],
        "claimed_diet_types": ["Vegan", "Gluten-Free"]
    }
    print(verify_menu_item(**test_item))
