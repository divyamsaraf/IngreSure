# AI Engine Internals

This document explains the inner workings of the `backend/` directory services.

## 1. The Safety Analyst (`safety_analyst.py`)

The Safety Analyst is a **Hybrid System** designed to be "Safe by Design". It does not rely solely on LLM hallucinations.

### The "Gold Standard" Logic
1.  **Normalization**: `llm_normalizer.py` converts messy OCR text into canonical ingredient names (e.g., "Mlk" -> "milk").
2.  **O(1) Lookup**: `ingredient_ontology.py` contains a hardcoded dictionary of 300+ common ingredients with their biological source and allergen flags.
3.  **Deterministic Evaluation**:
    - If `Source == Animal` AND `Diet == Vegan` -> **BLOCK**.
    - If `Source == Milk` AND `Allergy == Dairy` -> **BLOCK**.
    - This logic runs *before* any LLM inference, ensuring that obvious violations are never missed.
4.  **LLM Fallback**: Only if an ingredient is `Unclear` (not in ontology) does the system ask **Llama 3.2** to analyze it.

The platform is **grocery-only**; there is no RAG service or verification service (those were removed with the restaurant/menu schema).
