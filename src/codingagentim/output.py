"""Output formatting — json/table/raw."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def print_json(data: Any) -> None:
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
        data = [d.model_dump(mode="json") for d in data]
    console.print_json(json.dumps(data, ensure_ascii=False, default=str))


def print_table(rows: list[dict], columns: list[str] | None = None) -> None:
    if not rows:
        console.print("[dim]No results[/dim]")
        return
    if columns is None:
        columns = list(rows[0].keys())
    table = Table()
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(row.get(c, "")) for c in columns])
    console.print(table)


def print_raw(text: str) -> None:
    console.print(text)


def output(data: Any, fmt: str = "table") -> None:
    if fmt == "json":
        print_json(data)
    elif fmt == "raw":
        if isinstance(data, str):
            print_raw(data)
        else:
            print_json(data)
    else:
        if isinstance(data, list):
            rows = [d.model_dump(mode="json") if hasattr(d, "model_dump") else d for d in data]
            print_table(rows)
        elif hasattr(data, "model_dump"):
            print_table([data.model_dump(mode="json")])
        elif isinstance(data, dict):
            print_table([data])
        else:
            print_raw(str(data))
