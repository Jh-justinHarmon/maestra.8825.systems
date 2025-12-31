# Maestra 8825

**Status:** Production  
**Live:** https://maestra.8825.systems  
**Backend:** https://maestra-backend-8825-systems.fly.dev

Maestra is an intelligent advisor system that combines local context with real-time LLM synthesis to provide actionable guidance across the 8825 ecosystem.

---

## Quick Start

### For Users
Open https://maestra.8825.systems and start asking questions.

### For Developers

**Prerequisites:**
- Node.js 18+
- Python 3.9+
- Fly.io account (for backend deployment)

**Local Development:**

```bash
# Install UI dependencies
npm install

# Start UI dev server
npm run dev

# In another terminal, start backend
cd backend
python3 -m uvicorn server:app --reload
```

UI will be at `http://localhost:5173`  
Backend will be at `http://localhost:8825`

---

## Architecture

### Frontend (React + Vite)
- **Location:** `src/`
- **Build:** `npm run build`
- **Deploy:** Cloudflare Pages (automatic on push to main)

### Backend (FastAPI + Python)
- **Location:** `backend/`
- **Build:** Docker (Fly.io)
- **Deploy:** `flyctl deploy --remote-only`

### Shared Documentation
- **Architecture:** `docs/ARCHITECTURE.md`
- **Monorepo Layout:** `docs/REPO_LAYOUT.md`
- **API Contract:** `backend/HANDSHAKE_PROTOCOL.md`

---

## LLM Configuration

Maestra uses team-level LLM API keys for all surfaces (web, extension, iOS).

**For local development:**
- Keys are loaded from `8825-Team/config/secrets/llm.env`
- See [`CONFIG_LLM_KEYS.md`](../../CONFIG_LLM_KEYS.md) for setup and rotation

**For production:**
- Keys are stored in Fly.io secrets
- Managed via `flyctl secrets set` (sourced from canonical env file)

---

## Deployment

### UI Deployment
Automatic on push to `main`:
```bash
git add src/
git commit -m "Update UI"
git push origin main
```

GitHub Actions will build and deploy to Cloudflare Pages.

### Backend Deployment
Automatic on push to `main` (if `backend/**` changed):
```bash
git add backend/
git commit -m "Update backend"
git push origin main
```

GitHub Actions will build, deploy to Fly.io, and run smoke tests.

**Manual deployment:**
```bash
cd backend
flyctl deploy --remote-only
```

See [`docs/DEPLOY_BACKEND.md`](docs/DEPLOY_BACKEND.md) for full deployment guide.

---

## Testing

### E2E Tests
```bash
npm run test:e2e
```

### Backend Smoke Test
```bash
cd backend
./smoke_test_production.sh
```

---

## Monitoring

### Backend Health
```bash
curl https://maestra-backend-8825-systems.fly.dev/health
```

### Logs
```bash
# UI (Cloudflare Pages)
# View in Cloudflare dashboard

# Backend (Fly.io)
flyctl logs
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/` | React UI components |
| `backend/` | FastAPI backend |
| `docs/ARCHITECTURE.md` | System design |
| `docs/DEPLOY_BACKEND.md` | Deployment guide |
| `backend/smoke_test_production.sh` | Production verification |
| `CONFIG_LLM_KEYS.md` | LLM key management |

---

## Troubleshooting

### Backend returns "LLM not configured"
- Check `CONFIG_LLM_KEYS.md` for key setup
- Verify Fly.io secrets: `flyctl secrets list`
- Restart backend: `flyctl restart`

### UI can't reach backend
- Check backend is running: `curl https://maestra-backend-8825-systems.fly.dev/health`
- Verify UI is pointing to correct backend URL (see `src/adapters/webAdapter.ts`)

### Deployment fails
- Check GitHub Actions logs
- Check Fly.io logs: `flyctl logs --level error`
- Verify secrets are set: `flyctl secrets list`

---

## Related Documentation

- **Team LLM Keys:** [`8825-Team/CONFIG_LLM_KEYS.md`](../../CONFIG_LLM_KEYS.md)
- **Monorepo Layout:** `docs/REPO_LAYOUT.md`
- **Backend API:** `backend/HANDSHAKE_PROTOCOL.md`
- **System Architecture:** `docs/ARCHITECTURE.md`

---

## Support

For issues or questions:
1. Check relevant documentation above
2. Review GitHub Actions logs for CI/CD issues
3. Check Fly.io logs for backend issues
4. See `CONFIG_LLM_KEYS.md` for LLM configuration issues
