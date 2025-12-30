# Maestra v1 Architecture

## Overview

Maestra is a reusable card UI with surface-specific adapters. The core contract is versioned and JSON-safe, enabling consistent behavior across web, extension, and iOS.

## Core Concepts

### Card + Adapter Pattern

```
┌─────────────────────────────────────────┐
│         MaestraCard (React)             │
│  - Chat UI, message display, input      │
│  - Capture mode toggle                  │
│  - Selection pill, pins drawer          │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
    ┌───▼────┐   ┌───▼────┐
    │ Web    │   │Extension│
    │Adapter │   │Adapter  │
    └────────┘   └────────┘
```

### Versioned Contract

All payloads use `schema_version: "1"` with ISO 8601 timestamps.

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: ISODateTimeString; // "2025-01-15T14:30:00.000Z"
}

interface Response {
  schema_version: '1';
  message: Message;
}
```

### Mode Registry

Deterministic mode selection based on page context:

```typescript
interface Mode {
  id: string;
  match(context: PageContext): number; // 0-1 confidence
  composeContext(page: PageContext): CaptureContext;
  suggestActions(): SuggestedAction[];
}
```

**v1 Modes:**
- `default`: Standard capture for any website
- `replit_collaborator`: Code-aware capture for Replit

## Directory Structure

```
maestra.8825.systems/
├── src/
│   ├── adapters/
│   │   ├── types.ts           # Versioned contract
│   │   ├── mockAdapter.ts     # Mock implementation
│   │   └── webAdapter.ts      # Real backend calls
│   ├── modes/
│   │   ├── types.ts           # Mode interface
│   │   ├── registry.ts        # Mode selection logic
│   │   ├── default.ts         # DefaultMode
│   │   └── replit.ts          # ReplitCollaboratorMode
│   ├── components/
│   │   ├── MaestraCard.tsx    # Core UI component
│   │   ├── Header.tsx         # Header with mode badge
│   │   ├── PinsDrawer.tsx     # Pins sidebar
│   │   ├── HandoffCapsule.tsx # Shareable capture
│   │   └── ErrorBoundary.tsx  # Error handling
│   ├── lib/
│   │   └── analytics.ts       # Telemetry hooks
│   └── App.tsx                # Main app with error boundary
├── extension/
│   ├── manifest.json          # Chrome MV3 config
│   ├── src/
│   │   ├── background/        # Service worker
│   │   └── content/           # Content script + overlay
│   └── README.md
├── ios/
│   └── README.md              # Share Sheet integration
├── mock-backend/
│   └── src/server.ts          # Stub API endpoints
├── e2e/
│   └── smoke.spec.ts          # Playwright tests
├── fixtures/v1/               # Golden test fixtures
├── scripts/
│   └── validate-fixtures.ts   # Schema validation
└── .github/workflows/
    └── ci.yml                 # GitHub Actions CI
```

## Data Flow

### Web App
1. User types message
2. `handleSendMessage()` calls `mockAdapter.sendMessage()`
3. Mock adapter returns `Response` with schema_version
4. UI renders message with parsed ISO timestamp

### Extension
1. User clicks extension icon
2. Content script injects overlay UI
3. User selects text and clicks "Capture"
4. Content script sends `CAPTURE` message to background
5. Background worker posts to `/api/capture`
6. Response is stored in pins

### iOS
1. User shares from Safari/Notes/Photos
2. Share extension captures URL/text
3. Payload posted to `https://api.8825.systems/capture`
4. Deep link opens Maestra app with context

## Stability Strategy

### Golden Fixtures
- 9 canonical fixtures covering all surfaces and modes
- Validation script ensures schema compliance
- CI fails if fixtures don't validate

### GitHub Actions CI
- TypeScript typecheck
- Build verification
- Fixture validation
- (Later: unit tests, E2E tests)

### Feature Flags
```typescript
export const FLAGS = {
  ENABLE_REPLIT_MODE: import.meta.env.VITE_FLAG_REPLIT === 'true',
  ENABLE_HTML_SNAPSHOT: import.meta.env.VITE_FLAG_HTML === 'true',
};
```

## Analytics

All user interactions are tracked:
- `message_sent`: User sends message
- `capture_created`: User captures content
- `mode_selected`: Mode detection on load
- `handoff_copied`: User copies handoff capsule
- `pin_shared`: User shares a pin

## Performance Budget

- Main bundle: ≤ 200 KB gzip
- Current: 52.7 KB gzip ✓

## Next Steps

1. **Phase 6**: Build React compact card for extension
2. **Phase 7**: Implement iOS Share Sheet
3. **Phase 8**: Add E2E smoke tests
4. **Phase 9**: Release train + feature flags + Storybook
