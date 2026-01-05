# Maestra Chrome Extension Setup

## Build Status
✅ Extension built and ready to load

## Files
- `dist/background.js` - Background service worker (handles API calls)
- `dist/content.js` - Content script (injects UI into pages)
- `dist/manifest.json` - Extension configuration

## Load in Chrome

1. **Open Chrome Extensions**
   ```
   chrome://extensions
   ```

2. **Enable Developer Mode**
   - Toggle "Developer mode" in top-right corner

3. **Load Unpacked**
   - Click "Load unpacked"
   - Navigate to: `apps/maestra.8825.systems/extension/dist`
   - Select the `dist` folder

4. **Test**
   - Click the Maestra icon in toolbar
   - Should open overlay on any page
   - Click "Capture" to test backend connection

## Backend Configuration

Extension defaults to `http://localhost:8825`

To change backend URL:
1. Open Chrome DevTools (F12)
2. Go to Application → Local Storage
3. Add key: `maestra_backend_url`
4. Set value to your backend URL (e.g., `https://maestra-backend-8825-systems.fly.dev`)

## Current Features

✅ **Working**
- Background service worker wired to backend
- Content script injects overlay UI
- Capture button sends data to backend
- Message passing between content/background

🚧 **In Progress**
- React compact card UI (placeholder HTML for now)
- Chat message sending
- Context extraction

## Architecture

```
User clicks extension icon
    ↓
Content script opens overlay
    ↓
User clicks "Capture" or sends message
    ↓
Content script sends message to background
    ↓
Background service worker calls backend API
    ↓
Response displayed in overlay
```

## Next Steps

1. Build React compact card component
2. Wire message sending to backend
3. Test against localhost:8825 backend
4. Deploy to Chrome Web Store
