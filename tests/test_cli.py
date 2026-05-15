"""Tests for CLI entry point."""

from typer.testing import CliRunner

from codingagentim.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "codingagentim" in result.output


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "CodingAgentIM" in result.output


def test_schema():
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    assert "dingtalk" in result.output


def test_auth_status():
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "DingTalk" in result.output


def test_dingtalk_help():
    result = runner.invoke(app, ["dingtalk", "--help"])
    assert result.exit_code == 0
    assert "chat" in result.output
    assert "listen" in result.output
