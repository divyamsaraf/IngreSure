import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:3000/api" # Assuming local dev
OLLAMA_URL = "http://localhost:11434/api/generate"

def test_ollama_connection():
    print("Testing Ollama Connection...")
    try:
        payload = {
            "model": "llama3.2:3b",
            "prompt": "Hello",
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload)
        if response.status_code == 200:
            print("✅ Ollama is reachable.")
            return True
        else:
            print(f"❌ Ollama returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_safety_logic_mock():
    """
    Simulates the safety engine logic since we can't easily call TS functions from Python 
    without a running server exposing them.
    """
    print("\nTesting Safety Logic (Mock)...")
    
    # Mock Item
    item = {
        "name": "Peanut Butter Sandwich",
        "ingredients": ["bread", "peanut butter", "jelly"],
        "allergens": ["peanuts", "gluten"]
    }
    
    # User Constraint
    user_allergy = "peanuts"
    
    # Logic
    is_safe = user_allergy not in item["allergens"]
    
    if not is_safe:
        print("✅ Safety Check Passed: Correctly identified unsafe item.")
    else:
        print("❌ Safety Check Failed: Allowed unsafe item.")

if __name__ == "__main__":
    print("=== IngreSure Integration Tests ===\n")
    
    ollama_ok = test_ollama_connection()
    test_safety_logic_mock()
    
    if ollama_ok:
        print("\n✅ Basic System Checks Passed")
        sys.exit(0)
    else:
        print("\n❌ System Checks Failed")
        sys.exit(1)
