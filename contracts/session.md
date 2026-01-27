# Session Contract

**Status**: Authoritative  
**Created**: 2026-01-27  
**Purpose**: Define session as a first-class concept in Maestra

---

## Session Identity

A **session** is a logical container for a conversation between a user and Maestra. Sessions are surface-agnostic and persist across devices and platforms.

**Sessions are surface-agnostic.**

This means:
- A session can span multiple surfaces (web app, extension, Figma)
- Session state is managed by the backend, not the surface
- Surfaces read and write to sessions, but do not own them
- Session continuity is maintained regardless of which surface is used

---

## Required Fields

Every session MUST include the following fields:

### `session_id`
- **Type**: `string` (UUID v4)
- **Description**: Unique identifier for the session
- **Immutable**: Yes
- **Example**: `"550e8400-e29b-41d4-a716-446655440000"`

### `user_id`
- **Type**: `string`
- **Description**: Identifier for the user who owns this session
- **Immutable**: Yes
- **Example**: `"user_jh"`, `"alpha_sm"`

### `device_id`
- **Type**: `string`
- **Description**: Identifier for the device where the session was created
- **Immutable**: No (can change if session moves to different device)
- **Example**: `"macbook_pro_2023"`, `"iphone_14"`

### `surfaces`
- **Type**: `array[string]`
- **Description**: List of surfaces that have accessed this session
- **Immutable**: No (appends when new surface accesses session)
- **Example**: `["web_app", "browser_extension", "figma_v2"]`

### `started_on`
- **Type**: `string` (ISO 8601 timestamp)
- **Description**: When the session was created
- **Immutable**: Yes
- **Example**: `"2026-01-27T15:30:00Z"`

### `last_active_on`
- **Type**: `string` (ISO 8601 timestamp)
- **Description**: When the session was last accessed
- **Immutable**: No (updated on every interaction)
- **Example**: `"2026-01-27T16:45:00Z"`

---

## Optional Fields

Sessions MAY include additional fields:

- `context`: Surface-specific context (URL, file name, etc.)
- `mode`: Current mode (quick, deep, research)
- `capabilities`: Available capabilities (quad-core, local, cloud-only)
- `metadata`: Arbitrary key-value pairs

---

## Persistence Expectations

### Backend Responsibilities
- Create sessions on first interaction
- Persist session state across requests
- Update `last_active_on` on every interaction
- Append to `surfaces` when new surface accesses session
- Maintain conversation history within session

### Surface Responsibilities
- Include `session_id` in every request
- Create new session if none exists (via backend)
- Do NOT store session state locally (beyond session_id)
- Do NOT assume session ownership

---

## Session Lifecycle

1. **Creation**: Surface sends first message without `session_id`, backend creates session and returns `session_id`
2. **Active**: Surface includes `session_id` in all subsequent requests
3. **Cross-surface**: Different surface can access same session using `session_id`
4. **Dormant**: Session remains accessible but inactive (no expiration defined)
5. **Archived**: Backend may archive old sessions (policy TBD)

---

## Example Session Object

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_jh",
  "device_id": "macbook_pro_2023",
  "surfaces": ["web_app", "browser_extension"],
  "started_on": "2026-01-27T15:30:00Z",
  "last_active_on": "2026-01-27T16:45:00Z",
  "context": {
    "url": "https://example.com",
    "title": "Example Page"
  },
  "mode": "quick",
  "capabilities": ["quad-core"]
}
```

---

## Contract Enforcement

Surfaces MUST:
- Include `session_id` in all requests (after first message)
- Accept `session_id` from backend on first response
- Not modify session fields directly (only via backend API)

Backend MUST:
- Generate unique `session_id` for new sessions
- Validate `session_id` on every request
- Return session state when requested
- Update `last_active_on` automatically

---

**This contract is descriptive of current expectations. Implementation details (storage, database schema, caching) are not specified here.**
