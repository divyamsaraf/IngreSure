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

## 2. RAG Service (`rag_service.py`)

The Retrieval-Augmented Generation system allows natural language search over menus.

### Embedding Strategy
- **Model**: `all-MiniLM-L6-v2` (Local).
- **Dimensions**: 384.
- **Content**: We embed the `name`, `description`, and `dietary_tags` of a dish combined.
- **Search**: Uses Supabase `rpc` to perform `(embedding <-> query_embedding)` cosine distance sort.

### Generation Prompt
The retrieval context is injected into a "Waiter Persona" prompt.
> "You are a friendly waiter. Only recommend items from the provided list. If nothing matches, apologize."

## 3. Verification Service (`verification_service.py`)

Used for B2B auditing. It uses a **Self-Reflection** pattern.
1.  **Check**: LLM compares Name/Description vs Ingredients.
2.  **Rule Check**: Programmatic check of ingredients against claimed diets.
3.  **Merge**: If the Rule Engine finds a violation the LLM missed (e.g., "Gelatin" in a "Vegan" item), the Rule Engine overrides the LLM's "Safe" verdict.
