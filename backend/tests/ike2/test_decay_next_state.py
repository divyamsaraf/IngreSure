"""Item 4.1 Prompt 3: next_decay_state pure function."""
from core.knowledge.ike2.decay import (
    DECAY_POLICY,
    TTL_AUTO_CLASSIFIED_DAYS,
    TTL_VERIFIED_DAYS,
    next_decay_state,
)


def test_locked_never_decays():
    assert next_decay_state("LOCKED", 10_000) is None


def test_deprecated_and_unclassified_never_decay():
    assert next_decay_state("DEPRECATED", 10_000) is None
    assert next_decay_state("UNCLASSIFIED", 10_000) is None


def test_discovered_not_demoted_in_v1():
    assert next_decay_state("DISCOVERED", 10_000) is None


def test_verified_below_ttl_no_decay():
    assert next_decay_state("VERIFIED", TTL_VERIFIED_DAYS - 1) is None
    assert next_decay_state("VERIFIED", 0) is None


def test_verified_at_and_above_ttl_demotes():
    assert next_decay_state("VERIFIED", TTL_VERIFIED_DAYS) == "AUTO_CLASSIFIED"
    assert next_decay_state("VERIFIED", TTL_VERIFIED_DAYS + 1) == "AUTO_CLASSIFIED"


def test_auto_classified_demotes_to_discovered():
    assert next_decay_state("AUTO_CLASSIFIED", TTL_AUTO_CLASSIFIED_DAYS - 1) is None
    assert next_decay_state("AUTO_CLASSIFIED", TTL_AUTO_CLASSIFIED_DAYS) == "DISCOVERED"


def test_negative_age_no_decay():
    assert next_decay_state("VERIFIED", -1) is None


def test_custom_policy_override():
    assert next_decay_state("VERIFIED", 10, policy={"VERIFIED": 5}) == "AUTO_CLASSIFIED"
    assert next_decay_state("VERIFIED", 10, policy={"VERIFIED": 50}) is None


def test_decay_never_increases_rank():
    """Spot-check: every mapped transition is strictly lower in the ladder."""
    rank = {
        "UNCLASSIFIED": 0,
        "DISCOVERED": 1,
        "AUTO_CLASSIFIED": 2,
        "VERIFIED": 3,
        "LOCKED": 4,
    }
    for state, ttl in DECAY_POLICY.items():
        nxt = next_decay_state(state, ttl)
        assert nxt is not None
        assert rank[nxt] < rank[state]


def test_unknown_state_no_decay():
    assert next_decay_state("NOPE", 999) is None
