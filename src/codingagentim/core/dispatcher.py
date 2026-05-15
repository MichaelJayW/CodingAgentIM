"""Agent Dispatcher — routes IM messages to coding agent CLIs."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Callable, Awaitable

from codingagentim.core.models import AgentResult, TaskStatus
from codingagentim.core import task_store


_KEY_PATTERNS = re.compile(
    r"(error|fail|warn|created? |updated? |deleted? |fix|bug|test|commit|push|"
    r"pull request|PR |merge|install|compil|build|deploy|blocked|TODO|FIXME|"
    r"✓|✗|✅|❌|⚠|https?://|\.py:|\.ts:|\.js:)",
    re.IGNORECASE,
)


def _is_key_output(line: str) -> bool:
    if len(line) < 5:
        return False
    return bool(_KEY_PATTERNS.search(line))


AGENTS: dict[str, dict[str, Any]] = {
    "claude": {"cmd": ["claude", "-p"], "output_flag": "--output-format", "output_value": "json"},
    "codex": {"cmd": ["codex", "-q"], "output_flag": "--json", "output_value": ""},
    "gemini": {"cmd": ["gemini", "-p"], "output_flag": "", "output_value": ""},
    "aider": {"cmd": ["aider", "--message"], "output_flag": "", "output_value": ""},
}


class AgentDispatcher:
    def __init__(self, default_agent: str = "claude", work_dir: str = "."):
        self.default_agent = default_agent
        self.work_dir = work_dir

    async def dispatch(
        self,
        prompt: str,
        context: dict | None = None,
        on_output: Callable[[str], None] | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
        progress_interval: float = 8.0,
        sender: str = "",
        conversation_id: str = "",
    ) -> AgentResult:
        agent_config = AGENTS.get(self.default_agent)
        if not agent_config:
            return AgentResult(
                exit_code=1,
                stderr=f"Unknown agent: {self.default_agent}",
                agent=self.default_agent,
            )

        task = task_store.add_task(
            prompt=prompt,
            agent=self.default_agent,
            sender=sender,
            conversation_id=conversation_id,
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

            stdout_lines: list[str] = []
            last_progress_time = time.monotonic()

            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode()
                stdout_lines.append(text)
                stripped = text.strip()

                if on_output:
                    on_output(text)

                if on_progress and stripped and _is_key_output(stripped):
                    now = time.monotonic()
                    if now - last_progress_time >= progress_interval:
                        last_progress_time = now
                        await on_progress(stripped)

            stderr = (await proc.stderr.read()).decode()
            await proc.wait()

            result = AgentResult(
                exit_code=proc.returncode or 0,
                stdout="".join(stdout_lines),
                stderr=stderr,
                agent=self.default_agent,
            )
        except FileNotFoundError:
            result = AgentResult(
                exit_code=127,
                stderr=f"Agent CLI not found: {agent_config['cmd'][0]}",
                agent=self.default_agent,
            )

        result.summary = self.summarize(result)

        task_store.update_task(
            task.id,
            status=TaskStatus.COMPLETED if result.exit_code == 0 else TaskStatus.FAILED,
            summary=result.summary,
            exit_code=result.exit_code,
        )

        return result

    def summarize(self, result: AgentResult) -> str:
        if result.exit_code != 0:
            snippet = result.stderr[:500] if result.stderr else "No error output"
            return f"Execution failed (exit {result.exit_code})\n{snippet}"
        return self._extract_summary(result.stdout)

    def _extract_summary(self, output: str) -> str:
        import json as _json

        try:
            data = _json.loads(output.strip())
            if isinstance(data, dict) and any(k in data for k in ("result", "response", "candidates", "text")):
                return self._format_agent_result(data)
        except (ValueError, _json.JSONDecodeError):
            pass

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

    def _format_agent_result(self, data: dict) -> str:
        if "result" in data:
            return self._format_claude_result(data)
        if "response" in data:
            return self._format_codex_result(data)
        if "text" in data or "candidates" in data:
            return self._format_gemini_result(data)
        return str(data)[:800]

    def _format_claude_result(self, data: dict) -> str:
        result_text = data.get("result", "")
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_create = usage.get("cache_creation_input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = data.get("total_cost_usd")

        parts = [result_text]
        token_line = f"\n---\n📊 in: {input_tokens}"
        if cache_read:
            token_line += f" (cache read: {cache_read})"
        if cache_create:
            token_line += f" (cache create: {cache_create})"
        token_line += f" | out: {output_tokens}"
        if cost is not None:
            token_line += f" | ${cost:.4f}"
        parts.append(token_line)

        return "\n".join(parts)

    def _format_codex_result(self, data: dict) -> str:
        result_text = data.get("response", data.get("message", ""))
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        parts = [result_text]
        if input_tokens or output_tokens:
            parts.append(f"\n---\n📊 in: {input_tokens} | out: {output_tokens}")
        return "\n".join(parts)

    def _format_gemini_result(self, data: dict) -> str:
        if "candidates" in data:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            result_text = parts[0].get("text", "") if parts else ""
        else:
            result_text = data.get("text", "")

        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)

        out = [result_text]
        if input_tokens or output_tokens:
            out.append(f"\n---\n📊 in: {input_tokens} | out: {output_tokens}")
        return "\n".join(out)
