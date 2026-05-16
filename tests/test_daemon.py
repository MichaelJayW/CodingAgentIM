"""Tests for daemon module (launchd management)."""

import plistlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codingagentim.daemon import (
    LABEL,
    PLIST_PATH,
    _build_plist,
    _find_bridge_pids,
    _read_claude_env,
    get_status,
    install,
    is_loaded,
    uninstall,
)


@pytest.fixture
def tmp_plist(tmp_path, monkeypatch):
    plist = tmp_path / "com.codingagentim.bridge.plist"
    monkeypatch.setattr("codingagentim.daemon.PLIST_PATH", plist)
    monkeypatch.setattr("codingagentim.daemon.LOG_DIR", tmp_path)
    monkeypatch.setattr("codingagentim.daemon.STDOUT_LOG", tmp_path / "out.log")
    monkeypatch.setattr("codingagentim.daemon.STDERR_LOG", tmp_path / "err.log")
    return plist


class TestBuildPlist:
    def test_default_api_mode(self):
        plist = _build_plist(mode="api")
        assert plist["Label"] == LABEL
        assert "dingtalk" in plist["ProgramArguments"]
        assert "bridge" in plist["ProgramArguments"]
        assert "--mode" in plist["ProgramArguments"]
        assert "api" in plist["ProgramArguments"]
        assert plist["RunAtLoad"] is True
        assert plist["KeepAlive"] is True
        assert plist["ThrottleInterval"] == 10

    def test_cli_mode(self):
        plist = _build_plist(mode="cli")
        assert "cli" in plist["ProgramArguments"]

    def test_custom_model(self):
        plist = _build_plist(model="claude-haiku-4-5-20251001")
        args = plist["ProgramArguments"]
        assert "--model" in args
        assert "claude-haiku-4-5-20251001" in args
        assert plist.get("EnvironmentVariables", {}).get("ANTHROPIC_MODEL") == "claude-haiku-4-5-20251001"

    def test_custom_work_dir(self):
        plist = _build_plist(work_dir="/tmp/myproject")
        assert plist["WorkingDirectory"] == "/tmp/myproject"


class TestReadClaudeEnv:
    def test_reads_from_settings(self, tmp_path, monkeypatch):
        settings = tmp_path / "settings.json"
        settings.write_text('{"env": {"ANTHROPIC_AUTH_TOKEN": "tok123", "ANTHROPIC_BASE_URL": "http://x"}}')
        monkeypatch.setattr("codingagentim.daemon.CLAUDE_SETTINGS", settings)

        env = _read_claude_env()
        assert env["ANTHROPIC_AUTH_TOKEN"] == "tok123"
        assert env["ANTHROPIC_BASE_URL"] == "http://x"

    def test_missing_settings(self, tmp_path, monkeypatch):
        monkeypatch.setattr("codingagentim.daemon.CLAUDE_SETTINGS", tmp_path / "nope.json")
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        env = _read_claude_env()
        assert env == {}

    def test_env_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr("codingagentim.daemon.CLAUDE_SETTINGS", tmp_path / "nope.json")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env_key")
        env = _read_claude_env()
        assert env["ANTHROPIC_API_KEY"] == "env_key"


class TestIsLoaded:
    def test_loaded(self):
        with patch("codingagentim.daemon.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert is_loaded() is True

    def test_not_loaded(self):
        with patch("codingagentim.daemon.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=113)
            assert is_loaded() is False


class TestInstall:
    def test_creates_plist_and_loads(self, tmp_plist):
        with patch("codingagentim.daemon.is_loaded", return_value=False):
            with patch("codingagentim.daemon.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = install(mode="api")

        assert tmp_plist.exists()
        plist_data = plistlib.loads(tmp_plist.read_bytes())
        assert plist_data["Label"] == LABEL
        assert result == str(tmp_plist)

    def test_uninstalls_first_if_loaded(self, tmp_plist):
        with patch("codingagentim.daemon.is_loaded", return_value=True):
            with patch("codingagentim.daemon.uninstall") as mock_uninstall:
                with patch("codingagentim.daemon.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    install()
                    mock_uninstall.assert_called_once()


class TestUninstall:
    def test_bootout_and_delete(self, tmp_plist):
        tmp_plist.write_bytes(plistlib.dumps({"Label": LABEL}))
        with patch("codingagentim.daemon.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("codingagentim.daemon._find_bridge_pids", return_value=[]):
                result = uninstall()

        assert result["bootout"] is True
        assert result["plist_removed"] is True
        assert not tmp_plist.exists()

    def test_kills_remaining_processes(self, tmp_plist):
        tmp_plist.write_bytes(plistlib.dumps({"Label": LABEL}))
        with patch("codingagentim.daemon.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("codingagentim.daemon._find_bridge_pids", return_value=[12345]):
                with patch("os.kill") as mock_kill:
                    result = uninstall()
                    mock_kill.assert_called_once_with(12345, 9)
                    assert 12345 in result["killed"]


class TestGetStatus:
    def test_not_loaded(self):
        with patch("codingagentim.daemon.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=113, stdout="", stderr="")
            status = get_status()
            assert status["loaded"] is False

    def test_running_with_pid(self):
        launchctl_output = '"PID" = 42;\n"LastExitStatus" = 0;\n'
        pgrep_result = MagicMock(returncode=0, stdout="42\n")
        launchctl_result = MagicMock(returncode=0, stdout=launchctl_output)

        with patch("codingagentim.daemon.subprocess.run") as mock_run:
            mock_run.side_effect = [launchctl_result, pgrep_result]
            status = get_status()
            assert status["loaded"] is True
            assert status["pid"] == 42
