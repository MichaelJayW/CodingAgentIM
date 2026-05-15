"""Provider registry — discovers and manages IM providers."""

from __future__ import annotations

from codingagentim.core.provider import BaseProvider

_providers: dict[str, type[BaseProvider]] = {}


def register(name: str):
    def decorator(cls: type[BaseProvider]):
        _providers[name] = cls
        return cls
    return decorator


def get_provider(name: str, **kwargs) -> BaseProvider:
    if name not in _providers:
        available = ", ".join(_providers.keys()) or "(none)"
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")
    return _providers[name](**kwargs)


def list_providers() -> dict[str, type[BaseProvider]]:
    return dict(_providers)
