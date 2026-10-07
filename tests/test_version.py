"""The packaged version matches the version constant."""

from __future__ import annotations

import re
from pathlib import Path

from app import __version__
from app.metrics import render_metrics

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_version_matches_constant() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    assert match is not None
    assert match.group(1) == __version__
    assert __version__ == "0.1.0"


def test_metrics_escape_label_values() -> None:
    body = render_metrics(0, 0, version='1.2.3"beta')
    assert 'version="1.2.3\\"beta"' in body
    assert body.endswith("\n")
