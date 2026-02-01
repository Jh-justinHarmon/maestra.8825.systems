# Figma Surface for Maestra v2

**Status**: Migrated to Maestra v2 contracts  
**Contract Version**: 2.0.0  
**Endpoint**: `POST /api/maestra/advisor/ask`

---

## Architecture

```
Figma Plugin (UI)
    ↓
FigmaV2Adapter (Thin Translator)
    ↓
POST /api/maestra/advisor/ask
    ↓
Maestra Backend (All Intelligence)
```

---

## Directory Structure

```
surfaces/figma/
├── adapter/          # v2 adapter (thin translator)
│   ├── figmaV2Adapter.ts
│   └── config.ts
├── plugin/           # Figma plugin code (code.ts)
├── ui/               # Plugin UI (HTML/CSS/JS)
└── manifest/         # Figma manifest.json
```

---

## What This Surface Does

1. **Extract Context**: Read Figma file/page/selection data
2. **Package Request**: Build `AdvisorRequest` via adapter
3. **Send to Backend**: POST to `/api/maestra/advisor/ask`
4. **Display Response**: Render `advisor_output` in UI

---

## What This Surface Does NOT Do

- ❌ Inject system prompts (backend owns)
- ❌ Classify intent (backend owns)
- ❌ Enforce guardrails (backend owns)
- ❌ Make reasoning decisions (backend owns)
- ❌ Store conversation history (backend owns)
- ❌ Generate thread IDs (backend owns)

---

## Migration from v1

**Deleted**:
- `adapter/networkAdapter.ts` (had system prompts)
- `ui/intentClassifier.ts` (intent classification)
- `ui/guardrails.ts` (guardrails logic)
- All v1 reasoning logic

**Replaced**:
- Endpoint: `/api/reasoning` → `/api/maestra/advisor/ask`
- Adapter: v1 adapter → `figmaV2Adapter.ts`
- Contract: v1 types → Maestra v2 contracts

**Kept**:
- Figma API access (read-only)
- Context extraction logic
- UI rendering
- Plugin manifest

---

## Contract Compliance

✅ Surface is a thin client  
✅ Adapter is a pure translator  
✅ Backend owns all intelligence  
✅ No reasoning logic in surface  
✅ No prompts in surface  
✅ No guardrails in surface

---

## Development

```bash
# Install dependencies
npm install

# Build plugin
npm run build

# Watch mode
npm run watch
```

---

## Testing

See `ADAPTER_MAPPING_F_VALIDATION.md` for validation checklist.

---

**This surface is Maestra v2 compliant.**
