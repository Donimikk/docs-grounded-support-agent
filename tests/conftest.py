"""Shared fixtures for the tests.

The history is written to disk on every /ask call. Without this, each test run
would add dozens of invented tickets to the real history - and afterwards there
would be no telling a genuine customer from a test.
"""

import pytest

from fyndit_helper import api


@pytest.fixture(autouse=True)
def history_aside(tmp_path, monkeypatch):
    """Redirect the history into a temporary directory for every test."""
    monkeypatch.setattr(api, "HISTORY_PATH", tmp_path / "tickets.json")
