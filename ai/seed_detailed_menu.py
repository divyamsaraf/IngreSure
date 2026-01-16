import requests
import json
import time

API_URL = "http://localhost:8000/onboard-menu"

menu_data = {
    "restaurant_id": "78b31c65-3817-44da-b928-f4ff450095b3",
    "menu_items": [
        {
            "name": "Truffle Mushroom Risotto",
            "description": "Creamy Arborio rice slow-cooked with white wine and porcini mushroom broth, finished with aged Parmigiano-Reggiano, fresh herbs, and a drizzle of white truffle oil. Gluten-free and vegetarian.",
            "price": 24.00,
            "category": "Mains",
            "dietary_tags": ["Vegetarian", "Gluten-Free"],
            "ingredients": ["Arborio Rice", "Porcini Mushrooms", "White Wine", "Parmesan Cheese", "Truffle Oil", "Butter"]
        },
        {
            "name": "Spicy Szechuan Tofu",
            "description": "Crispy fried tofu cubes tossed in a fiery Szechuan peppercorn sauce with toasted peanuts, scallions, and dried red chilies. Served with steamed jasmine rice. Completely plant-based.",
            "price": 18.50,
            "category": "Mains",
            "dietary_tags": ["Vegan", "Spicy"],
            "ingredients": ["Tofu", "Peanuts", "Szechuan Peppercorns", "Chili Oil", "Scallions", "Soy Sauce"]
        },
        {
            "name": "Classic Wagyu Burger",
            "description": "8oz premium Wagyu beef patty grilled to perfection, topped with melted sharp cheddar cheese, lettuce, tomato, caramelized onions, and our signature secret sauce on a toasted brioche bun. Served with fries.",
            "price": 22.00,
            "category": "Mains",
            "ingredients": ["Wagyu Beef", "Cheddar Cheese", "Brioche Bun", "Lettuce", "Tomato", "Onion"]
        },
        {
            "name": "Grilled Atlantic Salmon",
            "description": "Fresh Atlantic salmon fillet grilled with lemon and herbs, served alongside roasted garlic asparagus and quinoa pilaf. A healthy, high-protein option.",
            "price": 28.00,
            "category": "Mains",
            "dietary_tags": ["Pescatarian", "Gluten-Free", "Dairy-Free"],
            "ingredients": ["Salmon", "Asparagus", "Quinoa", "Lemon", "Garlic", "Olive Oil"]
        },
        {
            "name": "Miso Glazed Eggplant",
            "description": "Japanese eggplant roasted until tender with a sweet and savory miso glaze, topped with sesame seeds. A delightful starter or light meal.",
            "price": 14.00,
            "category": "Appetizers",
            "dietary_tags": ["Vegan"],
            "ingredients": ["Eggplant", "Miso Paste", "Mirin", "Sugar", "Sesame Seeds"]
        },
        {
            "name": "Decadent Chocolate Lava Cake",
            "description": "Rich dark chocolate cake with a molten chocolate center, served warm with a scoop of vanilla bean ice cream and fresh berries.",
            "price": 12.00,
            "category": "Desserts",
            "dietary_tags": ["Vegetarian"],
            "ingredients": ["Dark Chocolate", "Butter", "Eggs", "Sugar", "Flour", "Vanilla Ice Cream"]
        },
        {
            "name": "Mediterranean Quinoa Salad",
            "description": "A refreshing mix of quinoa, cherry tomatoes, cucumbers, Kalamata olives, feta cheese, and red onions with a lemon-oregano vinaigrette.",
            "price": 16.00,
            "category": "Salads",
            "dietary_tags": ["Vegetarian", "Gluten-Free"],
            "ingredients": ["Quinoa", "Tomatoes", "Cucumber", "Olives", "Feta Cheese", "Red Onion"]
        },
        {
            "name": "Thai Green Curry Chicken",
            "description": "Tender chicken breast simmered in a spicy green coconut curry sauce with bamboo shoots, green beans, and Thai basil. Served with rice.",
            "price": 19.50,
            "category": "Mains",
            "ingredients": ["Chicken", "Coconut Milk", "Green Curry Paste", "Bamboo Shoots", "Green Beans", "Basil"]
        },
        {
            "name": "Shrimp Tacos",
            "description": "Three soft corn tortillas filled with grilled cajun shrimp, cabbage slaw, avocado crema, and pico de gallo.",
            "price": 17.00,
            "category": "Mains",
            "dietary_tags": ["Pescatarian", "Gluten-Free"],
            "ingredients": ["Shrimp", "Corn Tortillas", "Cabbage", "Avocado", "Sour Cream", "Lime"]
        },
         {
            "name": "Butternut Squash Soup",
            "description": "Velvety roasted butternut squash soup spiced with nutmeg and cinnamon, finished with a swirl of coconut cream. Warm and comforting.",
            "price": 10.00,
            "category": "Appetizers",
            "dietary_tags": ["Vegan", "Gluten-Free"],
            "ingredients": ["Butternut Squash", "Vegetable Broth", "Coconut Milk", "Nutmeg", "Cinnamon"]
        }
    ]
}

print(f"Seeding {len(menu_data['menu_items'])} detailed menu items...")
start_time = time.time()
try:
    response = requests.post(API_URL, json=menu_data, timeout=300)
    response.raise_for_status()
    print("Success!")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Failed: {e}")
finally:
    print(f"Time taken: {time.time() - start_time:.2f}s")
