# Local Optimization Guide (8GB RAM)

Running LLMs locally on an 8GB RAM machine requires optimization. We recommend using **Ollama** with quantized models.

## Setup Ollama

1.  **Download Ollama:** [https://ollama.com/download](https://ollama.com/download)
2.  **Install Mistral 7B (Quantized):**
    - Run the following command to pull the 4-bit quantized version of Mistral, which uses ~4.1GB of VRAM/RAM.
    ```bash
    ollama pull mistral
    ```

## Configuration

1.  **Environment Variables:**
    - Ensure your application points to the local Ollama instance (usually `http://localhost:11434`).
    - In `frontend/.env.local` (for local dev):
        ```
        NEXT_PUBLIC_LLM_API_URL=http://localhost:11434/api/generate
        ```

2.  **Running the App:**
    - Start Ollama: `ollama serve`
    - Start Frontend: `npm run dev`

## Performance Tips

- **Close Background Apps:** Close browser tabs and Electron apps (Slack, Discord) to free up RAM.
- **Use "Tiny" Models:** For very fast checks, consider `ollama pull tinyllama` or `phi` (Microsoft Phi-2), which use <2GB RAM, though accuracy may be lower.
- **Batch Processing:** If verifying bulk items, process them sequentially with a small delay rather than in parallel to avoid OOM (Out of Memory) errors.
