"""Tests for config module."""

from codingagentim.config import load_config


def test_load_defaults():
    cfg = load_config()
    assert cfg["default_provider"] == "dingtalk"
    assert cfg["default_agent"] == "claude"
    assert "dingtalk" in cfg
