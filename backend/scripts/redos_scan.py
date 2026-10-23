#!/usr/bin/env python3
"""Fail CI if a parsing / flag-derive regex exceeds the ReDoS budget.

Loads every ``re.compile`` in ``backend/core/parsing`` and
``backend/core/knowledge/ike2/flag_derive.py`` (plus other ``*derive*.py``
modules), then runs repeat-token payloads with a 0.5s budget per
(regex, payload).
"""
from __future__ import annotations

import ast
import importlib
import inspect
import multiprocessing
import pkgutil
import re
import sys
import time
from pathlib import Path
from typing import Iterable

BUDGET_S = 0.5
REPEAT_N = 40

_BACKEND = Path(__file__).resolve().parent.parent
_PARSING = _BACKEND / "core" / "parsing"
_IKE2 = _BACKEND / "core" / "knowledge" / "ike2"

_PAYLOADS: list[tuple[str, str]] = [
    ("and", "and" * REPEAT_N),
    ("and_spaces", ("and " * REPEAT_N).strip()),
    ("spaces", " " * REPEAT_N),
    ("parens", "(" * REPEAT_N),
    ("close_parens", ")" * REPEAT_N),
    ("fullwidth_parens", "（" * REPEAT_N),
    ("fullwidth_char", "ａ" * REPEAT_N),
    ("one_char", "a" * REPEAT_N),
]


def _eval_re_flags(node: ast.AST | None) -> int:
    if node is None:
        return 0
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return int(node.value)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "re":
        return int(getattr(re, node.attr, 0) or 0)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _eval_re_flags(node.left) | _eval_re_flags(node.right)
    return 0


def _literal_compiles(path: Path) -> list[re.Pattern[str]]:
    """Compile ``re.compile('literal')`` calls, including function-local ones."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return []
    out: list[re.Pattern[str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_compile = (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "re"
            and func.attr == "compile"
        )
        if not is_compile or not node.args:
            continue
        arg0 = node.args[0]
        if not isinstance(arg0, ast.Constant) or not isinstance(arg0.value, str):
            continue
        flags = 0
        if len(node.args) > 1:
            flags = _eval_re_flags(node.args[1])
        for kw in node.keywords:
            if kw.arg == "flags":
                flags |= _eval_re_flags(kw.value)
        try:
            out.append(re.compile(arg0.value, flags))
        except re.error:
            continue
    return out


def _walk_patterns(obj: object, seen: set[int], out: list[tuple[str, re.Pattern[str]]], origin: str) -> None:
    oid = id(obj)
    if oid in seen:
        return
    seen.add(oid)
    if isinstance(obj, re.Pattern):
        out.append((origin, obj))
        return
    if isinstance(obj, dict):
        for key, val in obj.items():
            _walk_patterns(val, seen, out, f"{origin}.{key}")
        return
    if isinstance(obj, (list, tuple, set, frozenset)):
        for i, val in enumerate(obj):
            _walk_patterns(val, seen, out, f"{origin}[{i}]")
        return
    if inspect.ismodule(obj):
        name = getattr(obj, "__name__", "") or origin
        if not (name.startswith("core.parsing") or name.startswith("core.knowledge.ike2")):
            return
        for attr, val in vars(obj).items():
            if attr.startswith("__"):
                continue
            _walk_patterns(val, seen, out, f"{name}.{attr}")
        return
    if inspect.isclass(obj):
        mod = getattr(obj, "__module__", "") or ""
        if not (mod.startswith("core.parsing") or mod.startswith("core.knowledge.ike2")):
            return
        for attr, val in vars(obj).items():
            if attr.startswith("__"):
                continue
            _walk_patterns(val, seen, out, f"{origin}.{attr}")


def _derive_module_paths() -> list[Path]:
    paths = [_IKE2 / "flag_derive.py"]
    paths.extend(sorted(_IKE2.glob("*derive*.py")))
    paths.extend(sorted(_IKE2.rglob("*derive*.py")))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def load_patterns() -> list[tuple[str, re.Pattern[str]]]:
    """Import parsing + derive modules and collect compiled regexes."""
    if str(_BACKEND) not in sys.path:
        sys.path.insert(0, str(_BACKEND))

    collected: list[tuple[str, re.Pattern[str]]] = []
    seen_ids: set[int] = set()

    import core.parsing as parsing_pkg

    for info in pkgutil.walk_packages(parsing_pkg.__path__, parsing_pkg.__name__ + "."):
        try:
            mod = importlib.import_module(info.name)
        except Exception:
            continue
        _walk_patterns(mod, seen_ids, collected, info.name)

    for path in _derive_module_paths():
        rel = path.relative_to(_BACKEND).with_suffix("")
        mod_name = ".".join(rel.parts)
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        _walk_patterns(mod, seen_ids, collected, mod_name)

    for path in list(_PARSING.glob("*.py")) + _derive_module_paths():
        origin = str(path.relative_to(_BACKEND))
        for pat in _literal_compiles(path):
            collected.append((origin, pat))

    unique: list[tuple[str, re.Pattern[str]]] = []
    seen_keys: set[tuple[str, int]] = set()
    for origin, pat in collected:
        key = (pat.pattern, pat.flags)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append((origin, pat))
    return unique


def _search_worker(pattern: str, flags: int, payload: str, conn) -> None:
    compiled = re.compile(pattern, flags)
    t0 = time.perf_counter()
    compiled.search(payload)
    conn.send(time.perf_counter() - t0)


def _batch_worker(
    specs: list[tuple[str, str, int]],
    payloads: list[tuple[str, str]],
    conn,
) -> None:
    for origin, pattern, flags in specs:
        compiled = re.compile(pattern, flags)
        for name, payload in payloads:
            conn.send(("start", origin, name, pattern[:160]))
            t0 = time.perf_counter()
            compiled.search(payload)
            conn.send(("done", time.perf_counter() - t0))
    conn.send(("end",))


def timed_search(
    pattern: re.Pattern[str],
    payload: str,
    budget: float = BUDGET_S,
) -> tuple[float, bool]:
    """Run ``pattern.search(payload)`` with a hard process timeout."""
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(
        target=_search_worker,
        args=(pattern.pattern, pattern.flags, payload, child),
    )
    t0 = time.perf_counter()
    proc.start()
    proc.join(budget)
    elapsed = time.perf_counter() - t0
    if proc.is_alive():
        proc.terminate()
        proc.join(1)
        if proc.is_alive():
            proc.kill()
            proc.join(1)
        return elapsed, True
    if parent.poll():
        try:
            elapsed = float(parent.recv())
        except (EOFError, TypeError, ValueError):
            pass
    parent.close()
    return elapsed, elapsed >= budget


def _scan_inprocess(
    patterns: Iterable[tuple[str, re.Pattern[str]]],
    payloads: list[tuple[str, str]],
    budget: float,
) -> list[dict]:
    slow: list[dict] = []
    for origin, pat in patterns:
        for name, payload in payloads:
            t0 = time.perf_counter()
            pat.search(payload)
            elapsed = time.perf_counter() - t0
            if elapsed >= budget:
                slow.append(
                    {
                        "origin": origin,
                        "payload": name,
                        "seconds": round(elapsed, 4),
                        "pattern": pat.pattern[:160],
                    }
                )
    return slow


def scan(
    *,
    budget: float = BUDGET_S,
    payloads: list[tuple[str, str]] | None = None,
    isolate: bool = False,
) -> list[dict]:
    patterns = load_patterns()
    used = payloads if payloads is not None else _PAYLOADS
    if isolate:
        return _scan_isolated(patterns, used, budget)
    return _scan_inprocess(patterns, used, budget)


def _scan_isolated(
    patterns: list[tuple[str, re.Pattern[str]]],
    payloads: list[tuple[str, str]],
    budget: float,
) -> list[dict]:
    specs = [(origin, pat.pattern, pat.flags) for origin, pat in patterns]
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_batch_worker, args=(specs, payloads, child))
    proc.start()
    slow: list[dict] = []
    pending: tuple | None = None
    first = True
    while True:
        wait = 30.0 if first else budget
        if not parent.poll(wait):
            if pending:
                slow.append(
                    {
                        "origin": pending[1],
                        "payload": pending[2],
                        "seconds": budget,
                        "pattern": pending[3],
                    }
                )
            proc.terminate()
            proc.join(1)
            if proc.is_alive():
                proc.kill()
                proc.join(1)
            break
        try:
            msg = parent.recv()
        except EOFError:
            break
        first = False
        if not msg:
            break
        kind = msg[0]
        if kind == "end":
            proc.join(1)
            break
        if kind == "start":
            pending = msg
            continue
        if kind == "done":
            elapsed = float(msg[1])
            if elapsed >= budget and pending:
                slow.append(
                    {
                        "origin": pending[1],
                        "payload": pending[2],
                        "seconds": round(elapsed, 4),
                        "pattern": pending[3],
                    }
                )
            pending = None
    if proc.is_alive():
        proc.terminate()
        proc.join(1)
    parent.close()
    return slow


def main() -> int:
    slow = scan(isolate=True)
    if not slow:
        n = len(load_patterns())
        print(f"redos_scan: {n} regexes, {len(_PAYLOADS)} payloads, all under {BUDGET_S}s")
        return 0
    print(f"redos_scan: {len(slow)} (regex, payload) exceeded {BUDGET_S}s", file=sys.stderr)
    for row in slow:
        print(
            f"  {row['seconds']:.3f}s {row['origin']} payload={row['payload']} {row['pattern']!r}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
