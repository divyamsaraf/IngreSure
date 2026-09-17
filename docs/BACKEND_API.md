# Backend API Reference

> **Current endpoints:** `/scan`, `/chat/grocery`, `/profile`, `/profile/{user_id}`, `/health`, API v1. Removed: `/chat/restaurant`, `/onboard-menu`, `/verify-menu-item`.

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
