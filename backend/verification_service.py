import json
import requests
import os
from caching import get_cached_verification, cache_verification

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

def verify_menu_item(item_name, description, ingredients, claimed_diet_types):
    """
    Verifies if the menu item details match the ingredients using Llama 3.2.
    """
    # Check cache first
    item_data = {
        "item_name": item_name,
        "description": description,
        "ingredients": ingredients,
        "claimed_diet_types": claimed_diet_types
    }
    cached_result = get_cached_verification(item_data)
    if cached_result:
        print("Returning cached result")
        return cached_result

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
    
    Respond ONLY with a valid JSON object. Do not include any markdown formatting or explanation outside the JSON.
    Structure:
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
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        # Handle cases where Ollama might return the JSON string inside 'response'
        response_text = result.get('response', '{}')
        try:
            parsed_result = json.loads(response_text)
        except json.JSONDecodeError:
             # Fallback: try to find JSON in the text if it's wrapped in markdown
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed_result = json.loads(json_match.group(0))
            else:
                raise ValueError("Could not parse JSON from LLM response")

        # --- Cross-Check with Deterministic Rule Engine ---
        from dietary_rules import DietaryRuleEngine
        rule_scorecard = DietaryRuleEngine.classify(ingredients)
        
        # If Rule Engine flags a violation that the LLM missed, add it to issues
        for diet in claimed_diet_types:
            if diet in rule_scorecard:
                if rule_scorecard[diet]["status"] == "red":
                    issue_msg = f"Rule Engine Violation: Claimed {diet} but found forbidden ingredients: {rule_scorecard[diet]['reason']}"
                    if issue_msg not in parsed_result.get("issues", []):
                        parsed_result.setdefault("issues", []).append(issue_msg)
                        parsed_result["is_consistent"] = False
                        parsed_result["confidence_score"] = 1.0 # High confidence in rule violation

        # Cache the result
        cache_verification(item_data, parsed_result)
        
        return parsed_result

    except requests.exceptions.ConnectionError:
        return {
            "error": "Ollama connection failed. Is Ollama running?",
            "is_consistent": False,
            "confidence_score": 0.0,
            "issues": ["AI Service Unavailable"]
        }
    except Exception as e:
        return {
            "error": str(e),
            "is_consistent": False,
            "confidence_score": 0.0,
            "issues": [f"AI Verification Failed: {str(e)}"]
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
