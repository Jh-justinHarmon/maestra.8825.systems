# Maestra Browser Extension

Compact, lightweight browser extension for capturing web content and chatting with Maestra.

## Architecture

- **manifest.json**: Extension configuration (MV3)
- **src/background/background.ts**: Service worker handling API communication
- **src/content/content.ts**: Content script injected into pages; manages overlay UI
- **src/shared/**: Shared types and utilities (symlinked from main project)

## Features

- One-click page capture with selection support
- Compact card UI (400px width, right sidebar)
- Mode detection (Replit, default)
- Handoff capsule for sharing
- Graceful error handling

## Development

```bash
# Build extension
npm run build:extension

# Watch for changes
npm run dev:extension

# Load in Chrome: chrome://extensions/ → Load unpacked → extension/dist/
```

## API Contract

All payloads conform to `schema_version: "1"` with ISO timestamps.

### Capture Payload
```json
{
  "schema_version": "1",
  "url": "https://example.com",
  "title": "Page Title",
  "selection": "Optional selected text",
  "timestamp": "2025-01-15T14:30:00.000Z"
}
```

## Next Steps

1. Build React compact card component
2. Integrate with main app's mode registry
3. Add E2E tests for extension overlay
4. Deploy to Chrome Web Store
