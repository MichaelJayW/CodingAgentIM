"""DingTalk calendar service."""

from __future__ import annotations

from datetime import datetime, timedelta

from codingagentim.core.models import CalendarEvent
from codingagentim.providers.dingtalk.api import DingTalkAPI


class CalendarService:
    def __init__(self, api: DingTalkAPI, user_id: str = "me"):
        self._api = api
        self._user_id = user_id

    async def list_events(self, date: str | None = None) -> list[CalendarEvent]:
        if date:
            start = datetime.fromisoformat(date)
        else:
            start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        time_min = start.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        time_max = end.strftime("%Y-%m-%dT%H:%M:%S+08:00")

        result = await self._api.post(
            f"/v1.0/calendar/users/{self._user_id}/calendars/primary/events/listByTime",
            json={"timeMin": time_min, "timeMax": time_max, "maxResults": 50},
        )

        events = []
        for item in result.get("events", []):
            events.append(
                CalendarEvent(
                    id=item.get("id", ""),
                    title=item.get("summary", ""),
                    start_time=item.get("start", {}).get("dateTime"),
                    end_time=item.get("end", {}).get("dateTime"),
                    location=item.get("location", {}).get("displayName", ""),
                    attendees=[
                        a.get("displayName", "") for a in item.get("attendees", [])
                    ],
                    raw=item,
                )
            )
        return events
