# Frontend Developer Guide

The IngreSure frontend is built with **Next.js 14 (App Router)** and **TailwindCSS**.

## 1. Project Structure

### `src/app` (Routes)
- **`page.tsx`**: Landing page.
- **`chat/page.tsx`**: Grocery Assistant.
    - Sets `mode="grocery"` for `ChatInterface`.
- **`restaurant/chat/page.tsx`**: Restaurant Assistant.
    - Sets `mode="restaurant"` for `ChatInterface`.
- **`dashboard/page.tsx`**: B2B Dashboard. (Requires Auth).
- **`api/`**: Next.js Server Components that proxy requests to the Python backend.

### `src/components` (UI)
- **`chat/ChatInterface.tsx`**: 
    - The main chat component.
    - Handles **Streaming Response** parsing.
    - Manages `messages` state array.
- **`scan/SingleItemForm.tsx`**:
    - The image upload widget.
    - Handles Drag-and-Drop.
    - Displays the `ScanResult` JSON in a user-friendly "Scorecard".
- **`ui/`**: 
    - ShadCN reusable components (Button, Input, Card).

## 2. Key Concepts

### Streaming Text
The AI responses are streamed raw. We use `TextDecoder` to read chunks from the `fetch` response body and append them to the UI state in real-time.

```typescript
const reader = response.body?.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = new TextDecoder().decode(value);
  setMessages(prev => prev + text); // simplified
}
```

### State Management
- **Local State**: Used for Chat history and Form inputs (`useState`).
- **Server State**: We use `fetch` calls. No global store (Redux/Zustand) is currently used as the app is simple.

### Styling
- All styling is done via **Tailwind Utility Classes**.
- Theme config is in `tailwind.config.ts`.
- Global styles in `src/app/globals.css`.
