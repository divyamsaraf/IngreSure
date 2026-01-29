import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def test_onboarding():
    restaurant_id = "78b31c65-3817-44da-b928-f4ff450095b3"
    print(f"Testing Onboarding for Restaurant ID: {restaurant_id}")
    
    menu_items = [
        {
            "name": "Spicy Tofu Ramen",
            "description": "Japanese noodle soup with spicy miso broth, tofu, corn, and green onions.",
            "price": 13.50,
            "ingredients": ["wheat noodles", "miso", "tofu", "corn", "green onion", "chili oil", "soy sauce"]
        },
        {
            "name": "Margherita Pizza",
            "description": "Classic Italian pizza with tomato sauce, mozzarella, and basil.",
            "price": 15.00,
            "ingredients": ["pizza dough", "tomato sauce", "mozzarella cheese", "fresh basil", "olive oil"]
        },
        {
            "name": "Peanut Butter Smoothie",
            "description": "Creamy smoothie with peanut butter, banana, and almond milk.",
            "price": 8.00,
            "ingredients": ["peanut butter", "banana", "almond milk", "honey"]
        }
    ]
    
    payload = {
        "restaurant_id": restaurant_id,
        "menu_items": menu_items
    }
    
    try:
        response = requests.post(f"{BASE_URL}/onboard-menu", json=payload)
        response.raise_for_status()
        result = response.json()
        print("Onboarding Response:", json.dumps(result, indent=2))
        
        if result["status"] == "success" and result["processed"] == 3:
            print("✅ Onboarding Success")
        else:
            print("❌ Onboarding Failed or Partial Success")
            
    except Exception as e:
        print(f"❌ Request Failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)

if __name__ == "__main__":
    test_onboarding()
