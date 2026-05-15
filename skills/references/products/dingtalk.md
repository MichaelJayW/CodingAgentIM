# DingTalk Product Reference

DingTalk (Ding Talk / 钉钉) is an enterprise communication and collaboration platform by Alibaba. CodingAgentIM integrates with DingTalk via its OpenAPI.

## Key Concepts

- **Conversation ID** (`openConversationId`): Unique identifier for a group chat. Found in DingTalk admin console or via API.
- **User ID** (`staffId` / `userId`): Unique identifier for a user within the organization.
- **Robot Code**: The code of the custom robot (app) that sends messages on behalf of the organization.
- **App Key / App Secret**: Credentials for the DingTalk enterprise application, used to obtain access tokens.

## API Overview

### Messages
- **Group message**: Send via robot to a group by `openConversationId`. Supports text and markdown.
- **User message**: Send via robot to individual users by `userId` list (batch send).
- Message types: `sampleText` (plain text), `sampleMarkdown` (markdown with title).

### Contacts
- Search users within the organization by keyword (name, pinyin, etc.).
- Returns: userId, userName, email, department IDs, avatar.

### Calendar
- List events for a user's primary calendar within a date range.
- Returns: event ID, summary, start/end time, location, attendees.

### Todo
- Create/query personal todo items.
- Fields: subject, description, due time, done status.

## Authentication Flow

1. Use App Key + App Secret to request an access token from `https://api.dingtalk.com/v1.0/oauth2/accessToken`.
2. Token is valid for ~7200 seconds, cached and auto-refreshed.
3. Include token in `x-acs-dingtalk-access-token` header for all API calls.

## API Endpoints Used

| Feature | Method | Endpoint |
|---------|--------|----------|
| Send group msg | POST | `/v1.0/robot/groupMessages/send` |
| Send user msg | POST | `/v1.0/robot/oToMessages/batchSend` |
| Search contacts | POST | `/v1.0/contact/users/search` |
| List calendar | POST | `/v1.0/calendar/users/{userId}/calendars/primary/events/listByTime` |
| Create todo | POST | `/v1.0/todo/users/{userId}/tasks` |
| Query todos | POST | `/v1.0/todo/users/{userId}/tasks/query` |

## Stream SDK (Reverse Link)

DingTalk provides `dingtalk-stream` SDK for receiving @robot messages in real-time via a persistent connection. CodingAgentIM uses this for the reverse link (IM -> Agent):

1. Register a chatbot callback handler on `ChatbotMessage.TOPIC`.
2. When a user @mentions the robot, the handler receives the message.
3. Only @robot messages are processed (clear intent, security boundary).

## Useful Links

- [DingTalk Open Platform](https://open.dingtalk.com/)
- [DingTalk Stream SDK (Python)](https://pypi.org/project/dingtalk-stream/)
- [DingTalk Robot API Docs](https://open.dingtalk.com/document/orgapp/robot-overview)
