# Backend API Reference

Base URL: `http://localhost:8000`

## 1. Scanner API

### `POST /scan`
Uploads an image of a food label (ingredients/nutrition) and returns a safety analysis.

- **Request**: Multipart Form Data
    - `file`: Image file (JPG/PNG).
- **Response**: JSON
```json
{
  "raw_text": "extracted text...",
  "ingredients": ["sugar", "milk"],
  "dietary_scorecard": {
      "Vegan": { "status": "red", "reason": "Contains milk" }
  },
  "confidence_scores": { "overall": 0.9 }
}
```

## 2. Chat APIs

### `POST /chat/grocery`
The "SafetyAnalyst" chat. Analyzes text queries for strict dietary safety.

- **Request**:
```json
{
  "query": "Is E471 vegan?",
  "userProfile": { "diet": "vegan", "allergens": ["nuts"] }
}
```
- **Response**: Streaming Text (Server-Sent Events style usually, but here raw text stream).

### `POST /chat/restaurant`
The RAG-based search for restaurant menus.

- **Request**:
```json
{
  "query": "Do you have any vegan burgers?",
  "context_filter": { "restaurant_id": "optional-uuid" }
}
```
- **Response**: Streaming Text (Conversational answer).

## 3. Menu Verification (B2B)

### `POST /verify-menu-item`
Audits a menu item for accuracy.

- **Request**:
```json
{
  "item_name": "Vegan Burger",
  "description": "Plant based patty...",
  "ingredients": ["soy", "beef"], 
  "claimed_diet_types": ["Vegan"]
}
```
- **Response**:
```json
{
  "is_consistent": false,
  "confidence_score": 1.0,
  "issues": ["Rule Engine Violation: Claimed Vegan but found forbidden ingredients: Beef..."],
  "suggested_corrections": { ... }
}
```

## 4. Onboarding

### `POST /onboard-menu`
Ingests a full menu into the vector database.

- **Request**:
```json
{
  "restaurant_id": "uuid",
  "menu_items": [ ... ]
}
```
- **Response**: `{"status": "success", "items_processed": 50}`
