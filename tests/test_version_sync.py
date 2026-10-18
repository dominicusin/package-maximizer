"""Fallback version strings must not drift apart."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import package_maximizer

ROOT = Path(__file__).resolve().parent.parent


def _fallbacks() -> dict[str, str]:
    init = (ROOT / "package_maximizer" / "__init__.py").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    return {
        "__init__": set(re.findall(r'__version__ = "([^"]+)"', init)),
        "pyproject": re.search(r'fallback_version = "([^"]+)"', pyproject).group(1),
        "CITATION": re.search(r"^version: (\S+)", citation, re.M).group(1),
    }


def test_fallback_versions_match():
    found = _fallbacks()
    assert len(found["__init__"]) == 1
    assert found["__init__"] == {found["pyproject"]} == {found["CITATION"]}


def test_web_app_uses_package_version():
    web_app = importlib.import_module("package_maximizer.web.app")

    assert web_app.APP_VERSION == package_maximizer.__version__
