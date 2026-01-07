# PromptGen MCP Extraction Plan

## Overview

This document outlines the architectural improvement to extract PromptGen from an embedded library into a standalone MCP (Model Context Protocol) server. This is an **optional enhancement** for improved modularity and reusability.

**Status:** Planning phase (not urgent)  
**Priority:** Low (current embedded implementation is production-ready)  
**Timeline:** Post-launch optimization

## Current Architecture

```
Maestra Backend (FastAPI)
├── PromptGen (embedded library)
│   ├── Intent classification
│   ├── Context gathering
│   ├── Prompt optimization
│   └── Refusal Contract enforcement
└── /api/precompute endpoint
```

**Pros:**
- Simple deployment (single container)
- Fast local calls (no RPC overhead)
- No additional infrastructure

**Cons:**
- Tightly coupled to backend
- Can't reuse in other services
- Scaling backend scales PromptGen unnecessarily

## Proposed MCP Architecture

```
Maestra Backend (FastAPI)
└── /api/precompute endpoint
    └── Calls PromptGen MCP via stdio

PromptGen MCP Server (Node.js)
├── Intent classification
├── Context gathering
├── Prompt optimization
└── Refusal Contract enforcement

Other Services (Future)
└── Can call PromptGen MCP directly
```

**Pros:**
- Decoupled from backend
- Reusable across services
- Independent scaling
- Easier testing and development

**Cons:**
- Additional process to manage
- RPC overhead (~50-100ms)
- More complex deployment

## Implementation Plan

### Phase 1: Create PromptGen MCP Server (2-3 days)

**Files to create:**
- `mcp_servers/promptgen-mcp/server.js` - MCP server implementation
- `mcp_servers/promptgen-mcp/package.json` - Dependencies
- `mcp_servers/promptgen-mcp/README.md` - Documentation

**Key features:**
- Expose `refine_with_context` as MCP tool
- Support intent classification
- Support context gathering
- Enforce Refusal Contract
- Return structured results

**Dependencies:**
- `@modelcontextprotocol/sdk` - MCP framework
- `axios` - HTTP client for Context Builder
- Same Python dependencies as current PromptGen

**Testing:**
- Unit tests for intent classification
- Integration tests with Context Builder
- E2E tests with Maestra backend

### Phase 2: Update Maestra Backend (1-2 days)

**Changes:**
- Replace embedded PromptGen with MCP client
- Update `/api/precompute` to call MCP server
- Add MCP server startup in Docker
- Update health checks to verify MCP connectivity

**Files to modify:**
- `apps/maestra.8825.systems/backend/server.py`
- `apps/maestra.8825.systems/backend/Dockerfile`
- `apps/maestra.8825.systems/backend/fly.toml`

**Testing:**
- Verify precompute endpoint still works
- Check latency impact (expect +50-100ms)
- Validate error handling

### Phase 3: Update Deployment (1 day)

**Changes:**
- Register PromptGen MCP in Windsurf config
- Update CI/CD to build and test MCP server
- Update monitoring to track MCP health
- Document MCP deployment procedures

**Files to create/modify:**
- `.windsurf/mcp_config.json` - Register MCP
- `.github/workflows/backend-ci.yml` - Add MCP tests
- `PROMPTGEN_PRODUCTION_GUIDE.md` - Update deployment section

### Phase 4: Migration and Rollback (1 day)

**Procedure:**
1. Deploy MCP server alongside backend
2. Update backend to call MCP
3. Monitor for issues
4. Keep embedded version as fallback
5. After 24 hours, remove embedded version

**Rollback:**
- Revert backend to embedded version
- Stop MCP server
- No data loss or downtime

## Risk Assessment

### Low Risk
- MCP server is stateless
- Backend has fallback to embedded version
- Can rollback in < 5 minutes
- No database changes

### Mitigation
- Deploy MCP in parallel with backend
- Test thoroughly before cutover
- Monitor latency and error rates
- Keep embedded version for 1 week

## Performance Impact

### Latency
- Current (embedded): ~200ms P50
- Expected (MCP): ~250-300ms P50 (+50-100ms RPC overhead)
- Acceptable: < 500ms P95

### Throughput
- Current: 50+ RPS per backend instance
- Expected: 40+ RPS per backend instance (slight decrease due to RPC)
- Mitigation: Scale to 2 instances if needed

### Resource Usage
- MCP server: ~100MB memory, minimal CPU
- Backend: Slight decrease (no PromptGen processing)
- Net: Neutral or slight improvement

## Success Criteria

✅ **MCP Server Functional**
- Implements refine_with_context tool
- Returns structured results
- Handles errors gracefully
- Passes all tests

✅ **Backend Integration**
- Precompute endpoint calls MCP
- Latency < 500ms P95
- Error rate < 1%
- Health checks pass

✅ **Deployment**
- MCP registered in Windsurf
- CI tests pass
- Monitoring active
- Rollback procedure tested

✅ **Documentation**
- MCP README complete
- Deployment guide updated
- Troubleshooting guide added
- Architecture diagram updated

## Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: MCP Server | 2-3 days | TBD | TBD |
| Phase 2: Backend Integration | 1-2 days | TBD | TBD |
| Phase 3: Deployment | 1 day | TBD | TBD |
| Phase 4: Migration | 1 day | TBD | TBD |
| **Total** | **5-7 days** | TBD | TBD |

## Decision Points

### Should we extract PromptGen as MCP?

**Factors to consider:**
1. **Reusability:** Will other services need PromptGen? (Unknown)
2. **Complexity:** Is MCP overhead worth the modularity? (Probably not yet)
3. **Maintenance:** Can we support two versions? (Yes, but extra work)
4. **Timeline:** Is this blocking other work? (No)

**Recommendation:** **Defer extraction until:**
- Another service needs PromptGen
- Latency becomes a bottleneck
- Team capacity available
- Business case clear

## Alternative: Hybrid Approach

Keep embedded version as primary, but expose MCP interface for future use:

```python
# In PromptGen library
class PromptGenMCP:
    def __init__(self):
        self.agent = PromptGenAgent()
    
    def refine_with_context(self, raw_text, gather_context=True):
        return self.agent.refine_with_context(raw_text, gather_context)
```

**Benefits:**
- No immediate changes needed
- MCP interface ready when needed
- Can extract later without rewriting
- Zero performance impact

**Drawback:**
- Still embedded in backend
- Doesn't solve reusability issue

## Conclusion

**Current Status:** PromptGen is production-ready as embedded library.

**MCP Extraction:** Valuable architectural improvement, but not urgent.

**Recommendation:** 
1. Keep embedded version for now
2. Monitor for reusability needs
3. Extract to MCP when business case clear
4. Plan extraction for Q2 2026 if needed

**Next Steps:**
1. Monitor production metrics for 24 hours
2. Establish baseline performance
3. Revisit extraction decision in 1 month
4. Document lessons learned

---

**PromptGen is production-ready. MCP extraction is future optimization, not blocking issue.**
