"""Tests for Agent Dispatcher."""

import pytest

from codingagentim.core.dispatcher import AgentDispatcher


@pytest.mark.asyncio
async def test_dispatch_unknown_agent():
    dispatcher = AgentDispatcher(default_agent="nonexistent")
    result = await dispatcher.dispatch("test prompt")
    assert result.exit_code == 1
    assert "Unknown agent" in result.stderr


def test_summarize_failure():
    dispatcher = AgentDispatcher()
    from codingagentim.core.models import AgentResult

    result = AgentResult(exit_code=1, stderr="some error", agent="claude")
    summary = dispatcher.summarize(result)
    assert "failed" in summary.lower()
    assert "some error" in summary


def test_summarize_with_pr_link():
    dispatcher = AgentDispatcher()
    from codingagentim.core.models import AgentResult

    result = AgentResult(
        exit_code=0,
        stdout="Created https://github.com/user/repo/pull/42\n3 files changed, 10 insertions(+)",
        agent="claude",
    )
    summary = dispatcher.summarize(result)
    assert "pull/42" in summary
    assert "files changed" in summary


def test_summarize_truncation():
    dispatcher = AgentDispatcher()
    from codingagentim.core.models import AgentResult

    result = AgentResult(exit_code=0, stdout="x" * 2000, agent="claude")
    summary = dispatcher.summarize(result)
    assert "truncated" in summary
    assert len(summary) < 1000
