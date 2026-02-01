# TRACK 5 REQUIREMENTS

**Derived from:** Track 5B Dogfooding  
**Date:** 2026-01-28  
**Status:** 🔒 LOCKED — Input to Track 5 Implementation

---

## Executive Summary

Track 5B proved the Enforcement Kernel works locally. Track 5 deploys MCP servers to cloud so Maestra can access real intelligence while maintaining enforcement.

---

## Hard Requirements

### 1. MCP Servers Must Be Cloud-Accessible

**Current State:** MCP servers run locally, unreachable from Fly.io  
**Required State:** MCP servers deployed or proxied to cloud

| MCP Server | Priority | Reason |
|------------|----------|--------|
| sentinel-mcp | P0 | Core intelligence source |
| context-builder | P1 | Context aggregation |
| deep-research-mcp | P2 | External research |
| library-bridge | P1 | Library access |

### 2. Workspace Root Must Be Available

**Current State:** `WORKSPACE_ROOT` not set on Fly.io  
**Required State:** Environment variable or mounted volume

Options:
- **A.** Deploy MCP servers as separate Fly.io apps
- **B.** Use Cloudflare Tunnel to expose local MCPs
- **C.** Mount Dropbox volume to Fly.io (complex)

### 3. Tool Authority Path Must Work End-to-End

**Current State:** All responses use memory/system authority  
**Required State:** Sentinel queries return tool authority

Flow:
```
Query → LocalSentinelAdapter → ContextSource(tool:sentinel) → 
EnforcementKernel → authority="tool" → Response
```

### 4. Local Power Mode Toggle

**Current State:** Mode is always "full"  
**Required State:** User can enable "local_power" mode

UI Requirements:
- Toggle in settings or per-session
- Clear indicator when local_power is active
- Tooltip explaining what it means

---

## Enforcement Rules (Unchanged)

These rules from Track 5B remain in effect:

| Rule | Behavior |
|------|----------|
| Tool context → tool authority | Sentinel sources require authority="tool" |
| Missing required context → block | ContextUnavailable raised |
| Mode mismatch → block | ModeViolation raised |
| Refusal → authority="none" | RefusalAuthorityViolation if violated |

---

## Deployment Options Analysis

### Option A: Deploy MCPs to Fly.io (Recommended)

**Pros:**
- Full cloud deployment
- No local dependencies
- Scales independently

**Cons:**
- Requires MCP server modifications
- Need to handle artifact storage

**Implementation:**
1. Create `sentinel-mcp` Fly.io app
2. Mount artifact index as volume
3. Update Maestra to call cloud Sentinel

### Option B: Cloudflare Tunnel

**Pros:**
- MCPs stay local
- No code changes to MCPs
- Quick to set up

**Cons:**
- Requires local machine running
- Latency concerns
- Single point of failure

**Implementation:**
1. Install cloudflared on local machine
2. Create tunnel to MCP ports
3. Update Maestra to use tunnel URLs

### Option C: Hybrid (Recommended for Phase 1)

**Pros:**
- Fast to implement
- Proves the path works
- Can migrate to Option A later

**Implementation:**
1. Use Cloudflare Tunnel for Sentinel
2. Deploy context-builder to Fly.io
3. Keep deep-research local (optional)

---

## Success Criteria

Track 5 is complete when:

- [ ] Sentinel queries return tool authority
- [ ] Enforcement fires on tool context
- [ ] Local power mode is toggleable
- [ ] UI shows current mode clearly
- [ ] No enforcement regressions (51+ tests pass)

---

## Non-Goals for Track 5

- Cross-session persistence (Track 6)
- Multi-user support (Track 7)
- Cloud-native artifact storage (Track 8)

---

## Timeline Estimate

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 5.1 | 2 hours | Cloudflare Tunnel setup |
| 5.2 | 4 hours | Sentinel integration wired |
| 5.3 | 2 hours | Local power mode toggle |
| 5.4 | 2 hours | UI indicators |
| 5.5 | 2 hours | End-to-end testing |

**Total:** ~12 hours

---

## Dependencies

- Cloudflare account (for tunnel)
- Local machine running MCPs
- Fly.io secrets for tunnel credentials

---

## Risks

| Risk | Mitigation |
|------|------------|
| Tunnel latency | Monitor response times, fall back to library |
| Local machine offline | Clear error message, refuse gracefully |
| Sentinel index stale | Periodic re-index, show last-updated |

---

## Approval

This document is the **only input** to Track 5 implementation.

**Approved by:** Enforcement Kernel (automatically via 51 passing tests)
