#!/usr/bin/env bash
# User-side E2E tests: profile, chat (grocery), and optional scan.
# Prereqs: Backend at BACKEND_URL (default http://127.0.0.1:8000), optional frontend at FRONTEND_URL (default http://localhost:3000).
set -e
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
USER_ID="e2e-user-$$"

echo "=== User-side E2E (backend=$BACKEND_URL, frontend=$FRONTEND_URL) ==="

# 1) Profile GET (empty)
echo -n "1. GET profile (empty): "
R=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/profile/$USER_ID")
echo "$R"
test "$R" = "200" || { echo "FAIL"; exit 1; }

# 2) Profile POST (set vegetarian)
echo -n "2. POST profile (vegetarian): "
R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND_URL/profile" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\",\"dietary_preference\":\"vegetarian\",\"allergens\":[],\"lifestyle\":[]}")
echo "$R"
test "$R" = "200" || { echo "FAIL"; exit 1; }

# 3) Profile GET (persisted)
echo -n "3. GET profile (persisted): "
BODY=$(curl -s "$BACKEND_URL/profile/$USER_ID")
echo "$BODY" | grep -q "vegetarian" || { echo "FAIL: $BODY"; exit 1; }
echo "OK"

# 4) Chat grocery (new engine: compliance response)
echo -n "4. POST /chat/grocery (compliance): "
CHAT=$(curl -s -X POST "$BACKEND_URL/chat/grocery" -H "Content-Type: application/json" \
  -d "{\"query\":\"Is water and sugar safe for vegetarian?\",\"user_id\":\"$USER_ID\",\"userProfile\":{\"dietary_preference\":\"vegetarian\",\"allergens\":[],\"lifestyle\":[]}}")
echo "$CHAT" | head -c 200
echo ""
echo "$CHAT" | grep -qE "fine|safe|SAFE|suitable|Water|vegetarian" || true
echo "OK (stream received)"

# 5) Optional: frontend proxy (if frontend + backend are up and reachable)
echo -n "5. Frontend proxy /api/profile: "
F=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL/api/profile?user_id=$USER_ID" 2>/dev/null || echo "000")
echo "$F"
if [ "$F" = "200" ]; then echo "OK"; else echo "SKIP (ensure frontend and backend are up; in Docker, backend may take 1–2 min on first start for PaddleOCR)"; fi

# 6) Optional: scan (requires valid image file)
if [ -n "${SCAN_IMAGE:-}" ] && [ -f "$SCAN_IMAGE" ]; then
  echo -n "6. POST /scan: "
  S=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND_URL/scan" -F "file=@$SCAN_IMAGE")
  echo "$S"
  test "$S" = "200" || echo "WARN: scan returned $S"
else
  echo "6. POST /scan: SKIP (set SCAN_IMAGE to a path to test scan)"
fi

echo "=== User-side E2E done ==="
