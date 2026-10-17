"""Minimal in-memory stand-in for the supabase-py query builder (tests only)."""
from __future__ import annotations

import uuid
from types import SimpleNamespace


class _Query:
    def __init__(self, db: "FakeSupabase", table: str):
        self.db = db
        self.table = table
        self.filters: list = []
        self.mode = "select"
        self.payload = None
        self._limit = None
        self._order = None

    def select(self, *_a, **_k):
        self.mode = "select"
        return self

    def insert(self, payload):
        self.mode, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.mode, self.payload = "update", payload
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def is_(self, col, val):
        self.filters.append(lambda r: r.get(col) is None if val is None else r.get(col) == val)
        return self

    def gte(self, col, val):
        self.filters.append(lambda r: (r.get(col) or 0) >= val)
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _match(self):
        rows = [r for r in self.db.tables.setdefault(self.table, []) if all(f(r) for f in self.filters)]
        if self._order:
            col, desc = self._order
            rows.sort(key=lambda r: r.get(col) or 0, reverse=desc)
        return rows[: self._limit] if self._limit is not None else rows

    def execute(self):
        self.db.calls.append((self.table, self.mode))
        if self.db.fail_tables and self.table in self.db.fail_tables:
            raise ConnectionError(f"simulated failure on {self.table}")
        if self.mode == "insert":
            row = {"id": str(uuid.uuid4()), **self.payload}
            self.db.tables.setdefault(self.table, []).append(row)
            return SimpleNamespace(data=[row])
        if self.mode == "update":
            rows = self._match()
            for r in rows:
                r.update(self.payload)
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=[dict(r) for r in self._match()])


class FakeSupabase:
    def __init__(self, tables: dict | None = None, fail_tables: set | None = None):
        self.tables: dict[str, list[dict]] = {k: [dict(r) for r in v] for k, v in (tables or {}).items()}
        self.calls: list[tuple[str, str]] = []
        self.fail_tables = fail_tables or set()

    def table(self, name):
        return _Query(self, name)

    from_ = table

    def touched(self) -> set[str]:
        return {t for t, _ in self.calls}
