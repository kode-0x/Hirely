"""Layering and deliverables-sanity tests.

The presentation layer (``pages/``) must not import httpx, the concrete
provider adapters, or requests. Deliverables must be well-formed:
``.env.example`` carries no filled-in secrets and every dependency declared in
``pyproject.toml`` is pinned to an exact version.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PAGES_DIR = _REPO_ROOT / "pages"

_FORBIDDEN_IN_PAGES = (
    re.compile(r"^\s*import\s+httpx\b", re.MULTILINE),
    re.compile(r"^\s*import\s+requests\b", re.MULTILINE),
    re.compile(r"from\s+hirely\.providers\.ollama\b"),
    re.compile(r"from\s+hirely\.providers\.openrouter\b"),
    re.compile(r"import\s+hirely\.providers\.ollama\b"),
    re.compile(r"import\s+hirely\.providers\.openrouter\b"),
)


def test_pages_have_no_provider_or_web_http_imports() -> None:
    offenders: list[str] = []
    for page in _PAGES_DIR.glob("*.py"):
        text = page.read_text(encoding="utf-8")
        for pattern in _FORBIDDEN_IN_PAGES:
            if pattern.search(text):
                offenders.append(f"{page.name}: {pattern.pattern}")
    assert offenders == [], offenders


def test_env_example_has_empty_secret_values() -> None:
    env = (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    secret_keys = ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "OLLAMA_MODEL")
    for line in env.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if key.strip() in secret_keys:
            assert value.strip() == "", f"{key} must be empty in .env.example"


def _collect_requirement_strings(text: str) -> list[str]:
    requirements: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        token = line.rstrip(",").strip().strip('"').strip("'")
        if token and (token[0].isalpha() or token[0] == "_"):
            requirements.append(token)
    return requirements


def test_pyproject_dependencies_are_fully_pinned() -> None:
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    runtime = pyproject.partition("dependencies = [")[2].partition("]")[0]
    dev = pyproject.partition("dev = [")[2].partition("]")[0]

    runtime_reqs = _collect_requirement_strings(runtime)
    dev_reqs = _collect_requirement_strings(dev)

    assert runtime_reqs, "pyproject.toml should list runtime dependencies"
    assert dev_reqs, "pyproject.toml should list dev dependencies"
    for req in runtime_reqs + dev_reqs:
        assert "==" in req, f"dependency not pinned: {req}"


def test_lockfile_is_present() -> None:
    assert (_REPO_ROOT / "uv.lock").is_file(), "uv.lock must be committed for reproducible installs"
