"""scripts/check_secrets_hygiene.py: exits 1 on SERVICE_ROLE/NEXT_PUBLIC_*SECRET* leaks into frontend/, 0 otherwise."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from scripts.check_secrets_hygiene import main


def _with_frontend_dir(files: dict) -> Path:
    """Write {relative_path: content} under a fresh temp 'frontend' dir; returns that dir."""
    tmp = Path(tempfile.mkdtemp())
    frontend = tmp / "frontend"
    for rel, content in files.items():
        p = frontend / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return frontend


def test_passes_on_clean_frontend_tree():
    frontend = _with_frontend_dir({
        "src/app/page.tsx": "export default function Page() { return <div>hi</div> }",
        ".env.example": "NEXT_PUBLIC_SUPABASE_URL=https://x.supabase.co\nBACKEND_URL=http://127.0.0.1:8000\n",
    })
    with patch("scripts.check_secrets_hygiene._FRONTEND_DIR", frontend):
        assert main() == 0


def test_fails_on_service_role_string_in_source_file():
    frontend = _with_frontend_dir({
        "src/lib/supabaseAdmin.ts": "const key = process.env.SUPABASE_SERVICE_ROLE_KEY",
    })
    with patch("scripts.check_secrets_hygiene._FRONTEND_DIR", frontend):
        assert main() == 1


def test_fails_on_service_role_key_lowercase_variant():
    frontend = _with_frontend_dir({
        ".env.local": "supabase_service_role_key=eyJ...\n",
    })
    with patch("scripts.check_secrets_hygiene._FRONTEND_DIR", frontend):
        assert main() == 1


def test_fails_on_next_public_service_env_var():
    frontend = _with_frontend_dir({
        ".env.example": "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=your_key_here\n",
    })
    with patch("scripts.check_secrets_hygiene._FRONTEND_DIR", frontend):
        assert main() == 1


def test_fails_on_next_public_secret_env_var():
    frontend = _with_frontend_dir({
        ".env": "NEXT_PUBLIC_APP_SECRET=shh\n",
    })
    with patch("scripts.check_secrets_hygiene._FRONTEND_DIR", frontend):
        assert main() == 1


def test_ignores_node_modules_and_next_build_dirs():
    frontend = _with_frontend_dir({
        "node_modules/some-pkg/index.js": "SUPABASE_SERVICE_ROLE_KEY",
        ".next/cache/x.js": "SUPABASE_SERVICE_ROLE_KEY",
        "src/app/page.tsx": "export default function Page() { return null }",
    })
    with patch("scripts.check_secrets_hygiene._FRONTEND_DIR", frontend):
        assert main() == 0


def test_passes_when_frontend_dir_missing():
    tmp = Path(tempfile.mkdtemp()) / "frontend"  # never created
    with patch("scripts.check_secrets_hygiene._FRONTEND_DIR", tmp):
        assert main() == 0


def test_current_repo_frontend_passes():
    """Regression guard: the real frontend/ in this repo must stay clean."""
    assert main() == 0
