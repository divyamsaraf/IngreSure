# Chat stream protocol (stream tags)

The backend streams plain text over `POST /chat/grocery`. Structured blocks are delimited by **stream tags**. The frontend parses these tags to extract profile updates and ingredient audit data while showing only the visible text to the user.

## Single source of tag literals

- **Backend:** `backend/core/stream_tags.py` defines the tag constants. All emission of these tags in the backend uses these constants.
- **Frontend:** `frontend/src/constants/chatProtocol.ts` exports matching constants. **These must stay identical to the backend values** (same strings). When adding or changing a tag, update both files and this doc.

## Tags

| Constant (backend / frontend) | Literal value | Meaning |
|-------------------------------|----------------|--------|
| `PROFILE_REQUIRED_TAG` | `<<<PROFILE_REQUIRED>>>` | Backend is asking the user to set a dietary profile before personalized advice. Frontend may show a prompt or modal. |
| `PROFILE_UPDATE_TAG` | `<<<PROFILE_UPDATE>>>` | Wraps a JSON object: current user profile (`user_id`, `dietary_preference`, `allergens`, `lifestyle`). Emitted at the end of every chat response so the client can sync header/state. |
| `INGREDIENT_AUDIT_TAG` | `<<<INGREDIENT_AUDIT>>>` | Wraps a JSON payload for the ingredient audit cards: `summary`, `groups` (by status: avoid / depends / safe), `explanation`. |

## Format

- Tags are sent as **plain text** in the stream. Example: `…Hello!\n\n<<<PROFILE_UPDATE>>>{"user_id":"…"}<<<PROFILE_UPDATE>>>`.
- The frontend strips these blocks from the visible message and uses the JSON for state/cards. See `frontend/src/components/chat/streamChatResponse.ts`.

## Changing a tag

1. Update `backend/core/stream_tags.py`.
2. Update `frontend/src/constants/chatProtocol.ts` with the same literal.
3. Run backend and frontend tests. Update this doc if the meaning or format changes.
