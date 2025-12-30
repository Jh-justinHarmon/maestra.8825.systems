# Maestra v1 Fixtures

Golden test fixtures for validating schema compliance across all Maestra surfaces.

## Schema Version
All fixtures use `schema_version: "1"`.

## Structure

```
fixtures/v1/
├── capture/           # CapturePayload and CaptureResult fixtures
│   ├── default-page-capture.json
│   ├── page-with-selection.json
│   ├── replit-code-selection.json
│   ├── ios-share-url.json
│   ├── ios-share-text.json
│   └── capture-result.json
├── messages/          # Message fixtures
│   ├── user-message.json
│   └── assistant-response.json
├── context/           # Context prefetch fixtures
│   └── prefetch-result.json
└── README.md
```

## Validation

Run `npm run validate:fixtures` to validate all fixtures against TypeScript types.

## Adding New Fixtures

1. Create a new JSON file in the appropriate directory
2. Ensure `schema_version: "1"` is present
3. Use ISO 8601 format for all timestamps
4. Run validation to confirm compliance

## Surfaces Covered

- **web**: Full card web app
- **extension**: Browser extension compact card
- **ios_share_sheet**: iOS Share Sheet integration

## Modes Covered

- **default**: Standard page capture
- **replit_collaborator**: Replit-specific code capture
