"""Pending restrictions tighten immediately; persist and relax wait for confirm."""
from fastapi.testclient import TestClient

from app import app
from core.parsing.restriction_statement import parse_restriction_statement
from core.pending_restrictions import (
    abandon,
    effective_restriction_ids,
    get_pending,
)
from core.stream_tags import INGREDIENT_AUDIT_TAG

client = TestClient(app, raise_server_exceptions=False)


def test_lactose_intolerant_is_tighten_not_dead_end():
    stmt = parse_restriction_statement("lactose intolerant, not dairy allergy. Milk, sugar.")
    assert stmt.needs_confirm
    assert stmt.action in {"confirm", "tighten"}
    assert "dairy_free" in stmt.restriction_ids or stmt.tighten_ids


def test_pending_tightens_without_persisting():
    uid = "pending-tighten-user"
    abandon(uid)
    r1 = client.post(
        "/chat/grocery",
        json={
            "query": "I'm lactose intolerant. Milk, sugar.",
            "user_id": uid,
            "userProfile": {"dietary_preference": "No rules", "allergens": [], "lifestyle": []},
        },
    )
    assert r1.status_code == 200, r1.text[:400]
    low = r1.text.lower()
    assert "dairy" in low or "lactose" in low or "confirm" in low or "save" in low
    pending = get_pending(uid)
    assert pending is not None
    assert pending.persist is False
    rids = effective_restriction_ids(uid, [])
    assert "dairy_free" in rids
    # Milk must not be SAFE under the tightened session.
    if INGREDIENT_AUDIT_TAG in r1.text:
        assert "NOT_SAFE" in r1.text or "avoid" in r1.text.lower()
        assert '"status":"SAFE"' not in r1.text.replace(" ", "") or "avoid" in r1.text.lower()
    # Saved profile still empty
    prof = client.get(f"/profile/{uid}")
    assert prof.json().get("dietary_preference") in (None, "No rules")


def test_confirm_no_drops_pending():
    uid = "pending-no-user"
    abandon(uid)
    client.post(
        "/chat/grocery",
        json={"query": "I'm lactose intolerant. Milk, sugar.", "user_id": uid},
    )
    r = client.post("/chat/grocery", json={"query": "no", "user_id": uid})
    assert r.status_code == 200
    assert get_pending(uid) is None


def test_confirm_yes_persists():
    uid = "pending-yes-user"
    abandon(uid)
    client.post(
        "/chat/grocery",
        json={"query": "I'm lactose intolerant.", "user_id": uid},
    )
    r = client.post("/chat/grocery", json={"query": "yes", "user_id": uid})
    assert r.status_code == 200
    assert get_pending(uid) is None
    prof = client.get(f"/profile/{uid}").json()
    assert "dairy" in (prof.get("dietary_preference") or "").lower() or "milk" in str(
        prof.get("allergens")
    ).lower()


def test_only_today_does_not_persist():
    uid = "pending-today-user"
    abandon(uid)
    client.post(
        "/chat/grocery",
        json={"query": "I'm lactose intolerant.", "user_id": uid},
    )
    r = client.post("/chat/grocery", json={"query": "only today", "user_id": uid})
    assert r.status_code == 200
    pending = get_pending(uid)
    assert pending is not None
    assert pending.persist is False
    prof = client.get(f"/profile/{uid}").json()
    assert prof.get("dietary_preference") in (None, "No rules")


def test_relax_allergy_gone_does_not_tighten_or_persist():
    stmt = parse_restriction_statement("I think my peanut allergy is gone. PEANUTS (49.5%).")
    assert stmt.needs_confirm
    assert stmt.action != "apply"
    assert not stmt.tighten_ids
