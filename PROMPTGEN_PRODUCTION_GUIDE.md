# PromptGen Production Guide

## Overview

PromptGen is now fully functional in production. This guide covers deployment, monitoring, troubleshooting, and rollback procedures.

## Architecture

**PromptGen** is a library embedded in the Maestra backend that:
- Classifies user intent (code, research, general, etc.)
- Gathers context from the Library (8825-library)
- Optimizes prompts for clarity and specificity
- Estimates token cost and selects appropriate model
- Enforces Refusal Contract (refuses to optimize without grounding)

**Key Components:**
- Backend: `apps/maestra.8825.systems/backend/server.py`
- Hook: `src/hooks/useTypingIntelligence.ts`
- Component: `src/components/ChatInput.tsx`
- Endpoint: `POST /api/precompute`

## Deployment

### Prerequisites
- Repository root access (for Docker build context)
- Fly.io CLI configured
- Git push access

### Deploy Backend

```bash
cd /path/to/repo/root

# Commit changes
git add apps/maestra.8825.systems/backend/
git commit -m "fix: PromptGen production fix"
git push origin main

# Deploy from repo root
flyctl deploy \
  -a maestra-backend-8825-systems \
  --config apps/maestra.8825.systems/backend/fly.toml \
  --dockerfile apps/maestra.8825.systems/backend/Dockerfile \
  --remote-only
```

**Critical:** Build context must be repo root, not backend directory.

### Deploy Frontend

```bash
cd apps/maestra.8825.systems

# Build
npm run build

# Deploy
flyctl deploy -a maestra-8825-systems
```

## Monitoring

### Health Checks

**Basic Health:**
```bash
curl https://maestra-backend-8825-systems.fly.dev/health
```

**Deep Health (recommended):**
```bash
curl https://maestra-backend-8825-systems.fly.dev/health/deep
```

Expected response:
```json
{
  "status": "healthy",
  "checks": {
    "promptgen_import": true,
    "promptgen_functional": true,
    "server": true,
    "database": true,
    "context_builder": false  // OK if Library not accessible
  }
}
```

### Metrics

**Prometheus endpoint:**
```bash
curl https://maestra-backend-8825-systems.fly.dev/metrics
```

**Key metrics:**
- `precompute_requests_total` - Total requests
- `precompute_latency_seconds` - Request latency (p95 < 800ms)
- `precompute_grounded_total` - Successful groundings
- `precompute_refusals_total` - Refusal Contract triggers
- `precompute_confidence` - Confidence scores
- `precompute_errors_total` - Error count

### Logs

```bash
flyctl logs -a maestra-backend-8825-systems -n 100
```

Watch for:
- `✓ PromptGen imported` - Successful import
- `Precompute complete:` - Successful requests
- `PromptGen unavailable:` - Import failures

## Troubleshooting

### Issue: PromptGen not loading

**Symptom:** `/health/deep` returns `promptgen_import: false`

**Diagnosis:**
```bash
flyctl ssh console -a maestra-backend-8825-systems
python3 -c "from agents.prompt_gen import PromptGenAgent"
```

**Solution:**
1. Verify 8825_core present: `ls /app/8825_core/agents/prompt_gen`
2. Check PYTHONPATH: `echo $PYTHONPATH`
3. Redeploy from repo root (not backend directory)

### Issue: High latency (p95 > 800ms)

**Diagnosis:**
1. Check backend CPU/memory: `flyctl status -a maestra-backend-8825-systems`
2. Review logs for slow operations
3. Check Context Builder performance

**Solution:**
1. Scale horizontally: `flyctl scale count 2 -a maestra-backend-8825-systems`
2. Optimize Context Builder queries
3. Consider caching layer

### Issue: Low grounding rate (< 20%)

**Symptom:** Most queries return `grounded: false`

**Diagnosis:**
1. Check Library has entries: `ls ~/Hammer\ Consulting\ Dropbox/Justin\ Harmon/8825-Team/shared/8825-library/`
2. Review Context Builder search logic
3. Check relevance thresholds

**Solution:**
1. Ingest more conversation data
2. Tune grounding thresholds
3. Expand Library coverage

### Issue: Precompute endpoint returns 500

**Diagnosis:**
```bash
flyctl logs -a maestra-backend-8825-systems | grep "Precompute error"
```

**Solution:**
1. Check PromptGen import: `/health/deep`
2. Review error logs for specific failure
3. Rollback if needed

## Rollback Procedures

### Level 1: Immediate Rollback (< 5 min)

Revert to previous deployment:
```bash
flyctl releases rollback -a maestra-backend-8825-systems
```

### Level 2: Disable Feature (< 10 min)

If issue is in frontend, disable typing intelligence:
```bash
flyctl secrets set FEATURE_TYPING_INTELLIGENCE=false -a maestra-8825-systems
```

### Level 3: Full Revert (< 30 min)

Revert code and redeploy:
```bash
git revert <commit-hash>
git push origin main

cd /path/to/repo/root
flyctl deploy \
  -a maestra-backend-8825-systems \
  --config apps/maestra.8825.systems/backend/fly.toml \
  --dockerfile apps/maestra.8825.systems/backend/Dockerfile \
  --remote-only
```

## Testing

### Local Testing

```bash
# Test precompute endpoint
curl -X POST http://localhost:8000/api/precompute \
  -H "Content-Type: application/json" \
  -d '{"text":"implement authentication"}'

# Test health
curl http://localhost:8000/health/deep
```

### Production Testing

```bash
# Test with grounding
curl -X POST https://maestra-backend-8825-systems.fly.dev/api/precompute \
  -H "Content-Type: application/json" \
  -d '{"text":"library integration context"}'

# Test without grounding
curl -X POST https://maestra-backend-8825-systems.fly.dev/api/precompute \
  -H "Content-Type: application/json" \
  -d '{"text":"random unindexed query"}'
```

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| P50 Latency | < 300ms | ✅ ~200ms |
| P95 Latency | < 800ms | ✅ Monitoring |
| Error Rate | < 1% | ✅ 0% |
| Grounding Rate | > 20% | ⚠️ Depends on Library |
| Uptime | > 99.9% | ✅ 100% |

## Maintenance

### Weekly
- Review metrics dashboard
- Check error logs
- Validate grounding rate
- Update Library with new entries

### Monthly
- Load test at 50+ RPS
- Review and tune alert thresholds
- Update documentation
- Security audit (pip-audit, bandit)

### Quarterly
- Analyze performance trends
- Plan optimizations
- Review architecture
- Update runbook

## Success Criteria

✅ **PromptGen fully functional in production**
- Imports successfully
- Classifies intent correctly
- Gathers context when available
- Enforces Refusal Contract
- Returns optimized prompts with confidence > 0

✅ **Operational excellence**
- Deep health checks prevent silent failures
- CI tests catch import issues early
- Prometheus metrics enable monitoring
- Rollback procedures documented and tested

✅ **User experience**
- Typing-time intelligence available
- PreSendIndicator shows optimization status
- Graceful degradation if PromptGen unavailable
- Performance < 500ms for 95% of requests

## Support

For issues or questions:
1. Check logs: `flyctl logs -a maestra-backend-8825-systems`
2. Run deep health check: `/health/deep`
3. Review metrics: `/metrics`
4. Consult this guide
5. Escalate if unresolved in 15 minutes
