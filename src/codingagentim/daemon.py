"""macOS launchd daemon management for the DingTalk bridge."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "com.codingagentim.bridge"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = Path.home() / ".codingagentim"
STDOUT_LOG = LOG_DIR / "bridge.out.log"
STDERR_LOG = LOG_DIR / "bridge.err.log"

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"


def _find_bridge_bin() -> str:
    venv_bin = Path(__file__).resolve().parents[2] / ".venv" / "bin" / "codingagentim"
    if venv_bin.exists():
        return str(venv_bin)
    import shutil
    found = shutil.which("codingagentim")
    if found:
        return found
    return str(venv_bin)


def _read_claude_env() -> dict[str, str]:
    env = {}
    if CLAUDE_SETTINGS.exists():
        try:
            data = json.loads(CLAUDE_SETTINGS.read_text())
            settings_env = data.get("env", {})
            for key in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY",
                        "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL"):
                if key in settings_env:
                    env[key] = settings_env[key]
        except (json.JSONDecodeError, KeyError):
            pass
    for key in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY",
                "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL"):
        val = os.environ.get(key)
        if val and key not in env:
            env[key] = val
    return env


def _build_plist(mode: str = "api", model: str = "", work_dir: str = "") -> dict:
    bridge_bin = _find_bridge_bin()
    wd = work_dir or str(Path(__file__).resolve().parents[2])

    args = [bridge_bin, "dingtalk", "bridge", "--mode", mode]
    if model:
        args.extend(["--model", model])

    env = _read_claude_env()
    if model:
        env["ANTHROPIC_MODEL"] = model

    plist: dict = {
        "Label": LABEL,
        "ProgramArguments": args,
        "WorkingDirectory": wd,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "StandardOutPath": str(STDOUT_LOG),
        "StandardErrorPath": str(STDERR_LOG),
    }
    if env:
        plist["EnvironmentVariables"] = env

    return plist


def install(mode: str = "api", model: str = "", work_dir: str = "") -> str:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    if is_loaded():
        uninstall()

    plist = _build_plist(mode=mode, model=model, work_dir=work_dir)

    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist, f)

    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(PLIST_PATH)],
        check=True, capture_output=True, text=True,
    )

    return str(PLIST_PATH)


def uninstall(clean_logs: bool = False) -> dict:
    result = {"bootout": False, "plist_removed": False, "killed": [], "logs_removed": []}

    pid_before = _find_bridge_pids()

    uid = os.getuid()
    try:
        subprocess.run(
            ["launchctl", "bootout", f"gui/{uid}/{LABEL}"],
            check=True, capture_output=True, text=True,
        )
        result["bootout"] = True
    except subprocess.CalledProcessError:
        pass

    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
        result["plist_removed"] = True

    import time
    time.sleep(1)
    remaining = _find_bridge_pids()
    for pid in remaining:
        try:
            os.kill(pid, 9)
            result["killed"].append(pid)
        except OSError:
            pass

    if clean_logs:
        for log in (STDOUT_LOG, STDERR_LOG):
            if log.exists():
                log.unlink()
                result["logs_removed"].append(str(log))

    return result


def _find_bridge_pids() -> list[int]:
    ps = subprocess.run(
        ["pgrep", "-f", "codingagentim dingtalk bridge"],
        capture_output=True, text=True,
    )
    if ps.returncode != 0:
        return []
    return [int(p) for p in ps.stdout.strip().splitlines() if p.strip()]


def is_loaded() -> bool:
    result = subprocess.run(
        ["launchctl", "list", LABEL],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def get_status() -> dict:
    result = subprocess.run(
        ["launchctl", "list", LABEL],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return {"loaded": False, "pid": None, "exit_code": None}

    info: dict = {"loaded": True, "pid": None, "exit_code": None}
    for line in result.stdout.strip().splitlines():
        parts = line.split("=", 1)
        if len(parts) == 2:
            key, val = parts[0].strip().strip('"'), parts[1].strip().strip('"').rstrip(";")
            if "pid" in key.lower():
                try:
                    info["pid"] = int(val)
                except ValueError:
                    pass
            elif "exit" in key.lower() or "status" in key.lower():
                try:
                    info["exit_code"] = int(val)
                except ValueError:
                    pass

    ps = subprocess.run(
        ["pgrep", "-f", "codingagentim dingtalk bridge"],
        capture_output=True, text=True,
    )
    if ps.returncode == 0:
        pids = ps.stdout.strip().splitlines()
        if pids:
            info["pid"] = int(pids[0])

    return info


def restart() -> None:
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "kickstart", "-k", f"gui/{uid}/{LABEL}"],
        check=True, capture_output=True, text=True,
    )


def tail_logs(follow: bool = True, lines: int = 50) -> None:
    log_files = [str(p) for p in (STDOUT_LOG, STDERR_LOG) if p.exists()]
    if not log_files:
        print("No log files found")
        return
    cmd = ["tail"]
    if follow:
        cmd.append("-f")
    cmd.extend(["-n", str(lines)])
    cmd.extend(log_files)
    os.execvp("tail", cmd)
