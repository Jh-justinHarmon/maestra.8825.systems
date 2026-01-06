# Maestra Quad-Core Sidecar

The Quad-Core Sidecar enables **Quad-Core Mode** for Maestra by providing local service capabilities without requiring a cloud connection.

## What is Quad-Core Mode?

Quad-Core is the highest-fidelity connection mode for Maestra:

```
🟢 Quad-Core (Full Capabilities)
  ├─ Local Sidecar (port 8826) - Capability negotiation & library bridge
  ├─ Local Backend (port 8825) - Chat processing & context
  ├─ Local Brain (port 5000) - Knowledge routing & personalization
  └─ Hosted Backend (Fly.io) - Cloud tools & scaling
```

When the sidecar is running, Maestra automatically detects it and enters Quad-Core mode, providing:
- ✅ Full library access (local 8825 Library)
- ✅ Learning profile injection
- ✅ Deep context aggregation
- ✅ Offline-capable operation
- ✅ Capability routing to local services

## Quick Start

### Start the Sidecar

```bash
./sidecar/start.sh
```

The sidecar will:
1. Create a Python virtual environment (first run only)
2. Install dependencies (Flask, Werkzeug)
3. Start listening on `http://localhost:8826`

### Verify It's Running

```bash
curl http://localhost:8826/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "maestra-sidecar",
  "mode": "quad-core",
  "library_available": true
}
```

### Test Handshake

```bash
curl -X POST http://localhost:8826/handshake \
  -H "Content-Type: application/json" \
  -d '{"version":"1","user_agent":"maestra-ui/1.0"}'
```

Expected response:
```json
{
  "success": true,
  "mode": "quad-core",
  "capabilities": [
    "library-access",
    "learning-profiles",
    "deep-context",
    "offline-mode",
    "capability-routing",
    "brain-routing"
  ]
}
```

## Connection Detection

Maestra automatically detects the sidecar with a **5-second health check interval**:

1. **Check Sidecar (port 8826)** - If healthy + handshake succeeds → **Quad-Core Mode** 🟢
2. **Check Local Backend (port 8825)** - If healthy → **Local Mode** 🟡
3. **Fallback to Hosted (Fly.io)** - Always available → **Cloud-Only Mode** ⚪

## API Endpoints

### `/health` (GET)
Health check endpoint. Used by Maestra UI to detect sidecar availability.

```bash
curl http://localhost:8826/health
```

### `/handshake` (POST)
Capability negotiation endpoint. Called by Maestra UI to establish Quad-Core connection.

```bash
curl -X POST http://localhost:8826/handshake \
  -H "Content-Type: application/json" \
  -d '{"version":"1","user_agent":"maestra-ui/1.0"}'
```

Returns: `session_id`, `jwt`, `capabilities`, `library_id`

### `/library/{entry_id}` (GET)
Bridge to local 8825 Library. Retrieves knowledge entries by ID.

```bash
curl http://localhost:8826/library/5ce9e4d4f0f23d90
```

### `/capabilities` (GET)
Get available Quad-Core capabilities.

```bash
curl http://localhost:8826/capabilities?session_id=<session_id>
```

### `/context/aggregate` (POST)
Aggregate deep context from local services.

```bash
curl -X POST http://localhost:8826/context/aggregate \
  -H "Content-Type: application/json" \
  -d '{"query":"example query","session_id":"<session_id>"}'
```

### `/status` (GET)
Get sidecar status and configuration.

```bash
curl http://localhost:8826/status
```

## Configuration

The sidecar reads configuration from environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `LIBRARY_PATH` | `/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/shared/8825-library` | Path to local 8825 Library |
| `FLASK_ENV` | `production` | Flask environment |
| `FLASK_APP` | `server.py` | Flask app entry point |

## Architecture

```
Maestra UI (Browser)
    ↓ (health check every 5s)
Sidecar (port 8826)
    ├─ /health → Detect availability
    ├─ /handshake → Negotiate capabilities
    ├─ /library/* → Bridge to 8825 Library
    ├─ /context/aggregate → Assemble deep context
    └─ /capabilities → Feature discovery
    ↓
Local Services
    ├─ 8825 Library (JSON files)
    ├─ Jh-Brain (port 5000, if available)
    └─ Local Backend (port 8825)
```

## Troubleshooting

### Sidecar not detected (shows 🟡 Local Mode instead of 🟢 Quad-Core)

1. **Check if sidecar is running:**
   ```bash
   curl http://localhost:8826/health
   ```

2. **Check if library path exists:**
   ```bash
   ls -la "/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/shared/8825-library"
   ```

3. **Check browser console** for connection logs:
   - Open DevTools (F12)
   - Look for `[Maestra] Connected: Quad-Core mode` or `[Maestra] Connected: Local mode`

4. **Restart sidecar:**
   ```bash
   pkill -f "python.*sidecar"
   ./sidecar/start.sh
   ```

### Library entries not accessible

1. Verify library path is correct
2. Check file permissions: `ls -la shared/8825-library/`
3. Verify entry ID format (16 hex characters)

### Handshake failing

1. Check sidecar logs for errors
2. Verify JSON payload format
3. Ensure `Content-Type: application/json` header is set

## Development

### Run with Debug Logging

```bash
FLASK_ENV=development ./sidecar/start.sh
```

### Install Dependencies Manually

```bash
cd sidecar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 server.py
```

### Test Library Access

```bash
# List available entries
ls shared/8825-library/*.json

# Retrieve an entry
curl http://localhost:8826/library/<entry_id>
```

## Integration with Maestra

The sidecar is automatically integrated into Maestra's connection hierarchy. No additional configuration needed—just run `./sidecar/start.sh` and Maestra will detect it within 5 seconds.

The UI will display:
- 🟢 **Quad-Core Active** - Sidecar detected and handshake successful
- 🟡 **Local Mode** - Sidecar unavailable, using local backend
- ⚪ **Cloud Only** - Both sidecar and local backend unavailable

## Next Steps

1. **Start the sidecar:** `./sidecar/start.sh`
2. **Open Maestra:** https://maestra.8825.systems/
3. **Check connection status:** Look for 🟢 badge in top-right
4. **Test library access:** Reference an Entry ID in a message (e.g., "5ce9e4d4f0f23d90")

## References

- Maestra Gold Standard: `OPTIMAL_EXECUTION_PLAN.md`
- Connection Hierarchy: `src/adapters/webAdapter.ts`
- 8825 Library: `shared/8825-library/`
