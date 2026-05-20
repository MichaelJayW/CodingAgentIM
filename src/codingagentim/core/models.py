"""Unified data models shared across all IM providers."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    ACTION_CARD = "action_card"


class Message(BaseModel):
    id: str = ""
    sender_id: str = ""
    sender_name: str = ""
    conversation_id: str = ""
    content: str = ""
    msg_type: MessageType = MessageType.TEXT
    timestamp: datetime | None = None
    raw: dict = Field(default_factory=dict)
    image_paths: list[str] = Field(default_factory=list)
    file_paths: list[str] = Field(default_factory=list)
    audio_path: str = ""
    audio_recognition: str = ""


class Contact(BaseModel):
    id: str = ""
    name: str = ""
    email: str = ""
    department: str = ""
    avatar_url: str = ""
    raw: dict = Field(default_factory=dict)


class CalendarEvent(BaseModel):
    id: str = ""
    title: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str = ""
    attendees: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class TodoItem(BaseModel):
    id: str = ""
    title: str = ""
    description: str = ""
    due_date: datetime | None = None
    done: bool = False
    raw: dict = Field(default_factory=dict)


class AgentResult(BaseModel):
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    agent: str = ""
    summary: str = ""


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskRecord(BaseModel):
    id: str = ""
    prompt: str = ""
    status: TaskStatus = TaskStatus.PENDING
    agent: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    summary: str = ""
    exit_code: int = 0
    sender: str = ""
    conversation_id: str = ""
