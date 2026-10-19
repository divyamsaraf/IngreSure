"""SourceAdapter Protocol — contract for new bulk sources only (Item 1 Prompt 3)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.knowledge.ike2.etl.license_check import license_check


@runtime_checkable
class SourceAdapter(Protocol):
    """Emit Layer-1 records for ``bulk_inject``; never write Supabase directly.

    ``name`` must be a canonical key registered in ``sources._DEFAULT_STATE`` /
    ``reconcile._SOURCE_TIER`` (or added when the adapter ships).

    Optional ``license_spdx`` attribute is read by ``emit_layer1_records`` for
    the central Item 1.3 license gate.
    """

    name: str

    def license_ok(self) -> bool:
        """True iff redistribution/use policy allows Layer-1 emission.

        Prefer delegating to ``license_check(self.name, self.license_spdx)``.
        """
        ...

    def to_layer1_records(self) -> list[dict]:
        """Layer-1 dicts compatible with ``adapt.map_record``."""
        ...


def emit_layer1_records(adapter: SourceAdapter) -> list[dict]:
    """Shared gate: central license_check + adapter.license_ok → emit or ``[]``."""
    spdx = getattr(adapter, "license_spdx", None)
    decision = license_check(adapter.name, spdx)
    if not decision.allowed:
        return []
    if not adapter.license_ok():
        return []
    return list(adapter.to_layer1_records() or [])
