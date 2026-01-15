import requests
import json
import logging

# Configuration
API_URL = "http://localhost:8000/verify-menu-item"

# Mock Data (In real scenario, fetch from Supabase)
MENU_ITEMS = [
    {
        "id": "1",
        "item_name": "Vegan Buddha Bowl",
        "description": "Quinoa, roasted chickpeas, avocado, and tahini dressing.",
        "ingredients": ["Quinoa", "Chickpeas", "Avocado", "Tahini"],
        "claimed_diet_types": ["Vegan", "Gluten-Free"]
    },
    {
        "id": "2",
        "item_name": "Classic Cheeseburger",
        "description": "Beef patty, cheddar cheese, lettuce, tomato, brioche bun.",
        "ingredients": ["Beef", "Cheddar Cheese", "Lettuce", "Tomato", "Brioche Bun"],
        "claimed_diet_types": ["Vegan"] # Intentional Error
    }
]

def process_menu():
    print("Starting Menu Processing...")
    
    for item in MENU_ITEMS:
        print(f"\nProcessing: {item['item_name']}")
        
        payload = {
            "item_name": item["item_name"],
            "description": item["description"],
            "ingredients": item["ingredients"],
            "claimed_diet_types": item["claimed_diet_types"]
        }
        
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                print("Verification Result:")
                print(json.dumps(result, indent=2))
                
                # In real app: Update Supabase here
                # supabase.table('menu_items').update({...}).eq('id', item['id'])
                
            else:
                print(f"Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Failed to connect to API: {e}")

if __name__ == "__main__":
    process_menu()
