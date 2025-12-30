# Maestra iOS Share Sheet Extension

Universal capture ingress from any iOS app via Share Sheet.

## Architecture

- **MaestraShareExtension.swift**: Share extension UI and payload handling
- **ShareViewController.swift**: View controller for share UI
- **CapturePayload.swift**: Codable payload matching schema v1

## Features

- Share from Safari, Notes, Photos, Mail, etc.
- Capture URL, text, and images
- Offline queue for network failures
- Deep link back to Maestra app
- Keychain-based auth token storage

## Schema

All payloads conform to `schema_version: "1"` with ISO 8601 timestamps.

```swift
struct CapturePayloadV1: Codable {
  let schema_version: String = "1"
  let source: String = "ios_share_sheet"
  let url: String?
  let text: String?
  let timestamp: String // ISO 8601
}
```

## API Endpoint

```
POST https://api.8825.systems/capture
Authorization: Bearer <token>
Content-Type: application/json

{
  "schema_version": "1",
  "source": "ios_share_sheet",
  "url": "https://example.com",
  "text": "Selected text",
  "timestamp": "2025-01-15T14:30:00.000Z"
}
```

## Development

1. Open `Maestra.xcworkspace` in Xcode
2. Select `MaestraShareExtension` target
3. Build and run on device/simulator
4. Test via Share Sheet from any app

## Next Steps

1. Implement SwiftUI Share extension UI
2. Add Keychain auth token management
3. Implement offline queue with SQLite
4. Add deep link handling
5. TestFlight beta distribution
