"""
Stream protocol tags for chat responses.

These delimit structured blocks in the text stream. The frontend must use the
same literal values in frontend/src/constants/chatProtocol.ts. See
docs/stream-protocol.md for the full protocol.
"""
PROFILE_REQUIRED_TAG = "<<<PROFILE_REQUIRED>>>"
PROFILE_UPDATE_TAG = "<<<PROFILE_UPDATE>>>"
INGREDIENT_AUDIT_TAG = "<<<INGREDIENT_AUDIT>>>"
