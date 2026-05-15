"""Agent Dispatcher — routes IM messages to coding agent CLIs."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from codingagentim.core.models import AgentResult


AGENTS: dict[str, dict[str, Any]] = {
    "claude": {"cmd": ["claude", "-p"], "output_flag": "--output-format", "output_value": "json"},
    "codex": {"cmd": ["codex", "-q"], "output_flag": "", "output_value": ""},
    "gemini": {"cmd": ["gemini"], "output_flag": "", "output_value": ""},
}


class AgentDispatcher:
    def __init__(self, default_agent: str = "claude", work_dir: str = "."):
        self.default_agent = default_agent
        self.work_dir = work_dir

    async def dispatch(self, prompt: str, context: dict | None = None) -> AgentResult:
        agent_config = AGENTS.get(self.default_agent)
        if not agent_config:
            return AgentResult(
                exit_code=1,
                stderr=f"Unknown agent: {self.default_agent}",
                agent=self.default_agent,
            )

        cmd = [*agent_config["cmd"], prompt]
        if agent_config["output_flag"]:
            cmd.extend([agent_config["output_flag"], agent_config["output_value"]])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            result = AgentResult(
                exit_code=proc.returncode or 0,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                agent=self.default_agent,
            )
        except FileNotFoundError:
            result = AgentResult(
                exit_code=127,
                stderr=f"Agent CLI not found: {agent_config['cmd'][0]}",
                agent=self.default_agent,
            )

        result.summary = self.summarize(result)
        return result

    def summarize(self, result: AgentResult) -> str:
        if result.exit_code != 0:
            snippet = result.stderr[:500] if result.stderr else "No error output"
            return f"Execution failed (exit {result.exit_code})\n{snippet}"
        return self._extract_summary(result.stdout)

    def _extract_summary(self, output: str) -> str:
        lines = []
        pr_links = re.findall(r"https://github\.com/[^\s]+/pull/\d+", output)
        if pr_links:
            lines.append("PR: " + ", ".join(pr_links))
        diff_stat = re.search(r"(\d+ files? changed.*)", output)
        if diff_stat:
            lines.append(diff_stat.group(1))
        if not lines:
            truncated = output.strip()
            if len(truncated) > 800:
                truncated = truncated[:800] + "\n... (truncated)"
            return truncated
        return "\n".join(lines)
