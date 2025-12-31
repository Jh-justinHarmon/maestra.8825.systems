# Maestra Backend Deployment Guide

**Status:** Production (Fly.io)  
**URL:** https://maestra-backend-8825-systems.fly.dev  
**Last Updated:** 2025-12-30

---

## Overview

The Maestra backend is deployed on Fly.io and uses team-level LLM API keys stored in Dropbox. This guide covers:
- Initial setup
- Deployment workflow
- Secret management
- Smoke testing
- Troubleshooting

---

## Prerequisites

- Fly.io account with app `maestra-backend-8825-systems` created
- `flyctl` CLI installed and authenticated
- Access to `8825-Team/config/secrets/llm.env`
- GitHub repo with CI/CD workflows configured

---

## Initial Setup (One-Time)

### 1. Create Fly.io App

```bash
cd apps/maestra.8825.systems/backend
flyctl launch --name maestra-backend-8825-systems
```

### 2. Set LLM Secrets

```bash
# Load team LLM env
source ~/Hammer\ Consulting\ Dropbox/Justin\ Harmon/8825-Team/config/secrets/llm.env

# Set Fly.io secrets
flyctl secrets set \
  OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  LLM_PROVIDER="$LLM_PROVIDER" \
  LLM_MODEL="$LLM_MODEL"
```

### 3. Deploy

```bash
flyctl deploy --remote-only
```

---

## Deployment Workflow

### Automatic (CI/CD)

Push to `main` branch:

```bash
git add backend/
git commit -m "Update backend"
git push origin main
```

GitHub Actions will:
1. Detect changes in `backend/**`
2. Build Docker image
3. Deploy to Fly.io
4. Run smoke test
5. Fail if smoke test detects stubs or LLM misconfiguration

### Manual

```bash
cd apps/maestra.8825.systems/backend
flyctl deploy --remote-only
```

---

## Secret Management

### Rotating Keys

When rotating LLM API keys:

1. **Update canonical file:**
   ```bash
   # Edit ~/Hammer Consulting Dropbox/Justin Harmon/8825-Team/config/secrets/llm.env
   # Replace old keys with new ones
   ```

2. **Update Fly.io secrets:**
   ```bash
   source ~/Hammer\ Consulting\ Dropbox/Justin\ Harmon/8825-Team/config/secrets/llm.env
   flyctl secrets set \
     OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
     OPENAI_API_KEY="$OPENAI_API_KEY" \
     ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
   ```

3. **Restart app:**
   ```bash
   flyctl restart
   ```

4. **Verify:**
   ```bash
   curl https://maestra-backend-8825-systems.fly.dev/health
   ```

See `CONFIG_LLM_KEYS.md` for full rotation workflow.

---

## Smoke Testing

### Automated (in CI/CD)

Runs after every deployment:

```bash
./backend/smoke_test_production.sh
```

### Manual

```bash
cd backend
chmod +x smoke_test_production.sh
./smoke_test_production.sh
```

**What it checks:**
- ✅ Health endpoint responds
- ✅ Advisor endpoint responds
- ✅ No stub responses detected
- ✅ No "LLM not configured" errors (503)

**Failure = deployment rollback**

---

## Monitoring

### Health Endpoint

```bash
curl https://maestra-backend-8825-systems.fly.dev/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "maestra-backend",
  "version": "1.0.0",
  "dependencies": {
    "llm": "configured:openrouter"
  }
}
```

### Logs

```bash
flyctl logs
flyctl logs --level error
```

### Metrics

```bash
flyctl status
flyctl metrics
```

---

## Troubleshooting

### "LLM not configured" (503)

**Cause:** LLM secrets not set or invalid

**Fix:**
```bash
# Check secrets
flyctl secrets list

# Re-set secrets
source ~/Hammer\ Consulting\ Dropbox/Justin\ Harmon/8825-Team/config/secrets/llm.env
flyctl secrets set OPENROUTER_API_KEY="$OPENROUTER_API_KEY" ...

# Restart
flyctl restart
```

### Deployment fails

**Check logs:**
```bash
flyctl logs --level error
```

**Common issues:**
- Docker build fails: Check `requirements.txt` has all dependencies
- App crashes on startup: Check environment variables in logs
- Health check fails: Ensure port 8825 is exposed in `fly.toml`

### Smoke test fails

**Check response:**
```bash
curl -X POST https://maestra-backend-8825-systems.fly.dev/api/maestra/advisor/ask \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","question":"test","mode":"quick","context_hints":[]}'
```

**If response contains "stub":**
- LLM keys are not configured
- LLM provider is not recognized
- See "LLM not configured" fix above

---

## Rollback

If deployment breaks production:

```bash
# View recent deployments
flyctl releases

# Rollback to previous version
flyctl releases rollback
```

---

## Performance & Scaling

### Current Configuration

- **Machine:** shared-cpu-1x (256MB RAM)
- **Min machines:** 1
- **Auto-stop:** off (always running)
- **Region:** Primary (auto-selected)

### Scaling

If hitting rate limits or timeouts:

```bash
# Scale up machine
flyctl scale vm shared-cpu-2x

# Add more machines
flyctl scale count 2
```

---

## CI/CD Integration

### GitHub Actions

Workflow: `.github/workflows/deploy.yml`

**Triggers:**
- Push to `main` branch
- Changes in `backend/**` directory

**Steps:**
1. Detect changes (path filter)
2. Build Docker image
3. Deploy to Fly.io
4. Run smoke test
5. Report status

**Secrets required:**
- `FLY_API_TOKEN` – Fly.io API token

### Setting up CI/CD

1. **Add Fly.io token to GitHub:**
   ```bash
   # In GitHub repo settings → Secrets and variables → Actions
   # Add: FLY_API_TOKEN = <your-fly-api-token>
   ```

2. **Verify workflow:**
   ```bash
   # Push a backend change and watch GitHub Actions
   git push origin main
   ```

---

## Related Documentation

- **LLM Key Management:** `CONFIG_LLM_KEYS.md`
- **Architecture:** `ARCHITECTURE.md`
- **Monorepo Layout:** `REPO_LAYOUT.md`
- **API Contract:** `HANDSHAKE_PROTOCOL.md`

---

## Support

For issues:
1. Check logs: `flyctl logs --level error`
2. Check health: `curl https://maestra-backend-8825-systems.fly.dev/health`
3. Run smoke test: `./backend/smoke_test_production.sh`
4. Check `CONFIG_LLM_KEYS.md` for LLM key issues
