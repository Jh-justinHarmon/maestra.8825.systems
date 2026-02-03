# Maestra Backend - Canonical Startup

**This is the ONLY valid way to start the Maestra backend locally.**

## Prerequisites

- Python 3.9+
- System modules at: `/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/system`

## Startup Command

**Use the blessed startup script:**

```bash
./apps/maestra.8825.systems/backend/start.sh
```

**That's it. No other method is supported.**

## Why PYTHONPATH is Required

The backend imports system modules:
- `routing.context_router` - Memory routing and access control
- `memory_gate` - Authentication and authorization
- `maestra_memory` - Library access

These modules live in `system/` and must be on PYTHONPATH.

## Verification

After startup, check:
```bash
curl http://localhost:8825/health
```

Expected: `{"status": "healthy", ...}`

## Common Issues

**"No module named 'routing'"**
- PYTHONPATH not set correctly
- Must include absolute path to `system/` directory

**Port 8825 already in use**
- Another backend instance is running
- Kill it: `lsof -ti:8825 | xargs kill -9`

## DO NOT

- ❌ Start from a different directory
- ❌ Omit PYTHONPATH
- ❌ Use a different port without updating frontend
- ❌ Edit files in `system/tools/maestra_backend/` (shadow copy)
