# Backend Sync Protocol - Optimal Execution Plan
## Risk-Adjusted, Parallelized, MVP-First Approach

**Status:** Execution Roadmap  
**Version:** 1.0  
**Last Updated:** 2025-12-31  
**Optimized Duration:** 8-10 weeks (vs 12-16 weeks original)

---

## Optimization Strategy

### Key Insights

1. **Critical Path:** Identity → Handshake → Sync → Everything else
2. **Parallelization:** Telemetry, Privacy, and Observability can run in parallel
3. **MVP First:** Get basic sync working in 4 weeks, then harden
4. **Risk Front-Loading:** Tackle hardest problems (sync, security) early
5. **Existing Assets:** Leverage existing ConversationHub, LLM env loader, LaunchAgent

---

## Execution Tracks

```
Week 1-2:  [FOUNDATION]     Identity + Handshake (Critical Path)
Week 3-4:  [CORE]           State Sync + Basic Telemetry (Critical Path)
           ─────────────────── MVP CHECKPOINT ───────────────────
Week 5-6:  [PARALLEL TRACK A] Security Hardening
           [PARALLEL TRACK B] Privacy & Consent
Week 7-8:  [PARALLEL TRACK A] Offline & Resilience
           [PARALLEL TRACK B] Observability
Week 9-10: [INTEGRATION]    Multi-Platform + Polish
```

---

## Week 1-2: Foundation (Critical Path)

### Goal: Establish cryptographic identity and bidirectional handshake

### Week 1: Identity System

| Day | Deliverable | Owner | Risk |
|-----|-------------|-------|------|
| 1 | `BackendIdentity` class with `backend_id` generation | Backend | Low |
| 2 | `KeychainManager` for macOS keychain integration | Backend | Medium |
| 3 | `/identity` endpoint on local backend (port 8825) | Backend | Low |
| 4 | `/identity` endpoint on hosted backend (Fly.io) | Backend | Low |
| 5 | Integration test: both backends return valid identity | QA | Low |

**Deliverables:**
- `backend_8825/identity.py`
- `backend_8825/keychain.py`
- `/identity` endpoint live on both backends

### Week 2: Handshake & Session Binding

| Day | Deliverable | Owner | Risk |
|-----|-------------|-------|------|
| 1 | `SessionBindingToken` class with HMAC signing | Backend | Medium |
| 2 | `/register-peer` endpoint on local backend | Backend | Medium |
| 3 | `/register-peer` endpoint on hosted backend | Backend | Medium |
| 4 | UI handshake flow: detect both, create SBT, register | Frontend | High |
| 5 | End-to-end test: UI → Local → Hosted registration | QA | Medium |

**Deliverables:**
- `backend_8825/sbt.py`
- `/register-peer` endpoint live on both backends
- UI `handshake()` function updated in `webAdapter.ts`

**Success Gate:** UI successfully registers local backend with hosted backend, SBT verified on both ends.

---

## Week 3-4: Core Sync (Critical Path)

### Goal: Bidirectional conversation sync with basic telemetry

### Week 3: State Synchronization

| Day | Deliverable | Owner | Risk |
|-----|-------------|-------|------|
| 1 | `SyncPayload` and `ConversationSync` models | Backend | Low |
| 2 | `/sync/{peer_id}` endpoint on hosted backend | Backend | High |
| 3 | `/sync/{peer_id}` endpoint on local backend | Backend | High |
| 4 | `SyncScheduler` with 5-second interval | Backend | Medium |
| 5 | Integration test: conversation syncs local → hosted | QA | High |

**Key Decision:** Use Last-Write-Wins (not CRDT) for v1. Simpler, lower risk.

### Week 4: Basic Telemetry

| Day | Deliverable | Owner | Risk |
|-----|-------------|-------|------|
| 1 | `TelemetryEvent` model | Backend | Low |
| 2 | WebSocket `/telemetry/{peer_id}` on hosted backend | Backend | Medium |
| 3 | `TelemetryClient` on local backend | Backend | Medium |
| 4 | Instrument `/api/maestra/advisor/ask` with telemetry | Backend | Low |
| 5 | Verify events stream from local to hosted | QA | Medium |

**Deliverables:**
- Conversations sync bidirectionally every 5 seconds
- Telemetry events stream in real-time
- Messages marked with `source_backend` field

---

## ─────────────── MVP CHECKPOINT (End of Week 4) ───────────────

### What Works:
- ✅ Both backends have cryptographic identity
- ✅ UI creates Session Binding Token linking them
- ✅ Conversations sync local ↔ hosted every 5 seconds
- ✅ Telemetry streams from local to hosted
- ✅ User can start on local, continue on hosted (or vice versa)

### What Doesn't Work Yet:
- ❌ Offline mode (queues, retry)
- ❌ Key rotation, revocation
- ❌ PII redaction, privacy controls
- ❌ Mobile companions
- ❌ Observability dashboard

### Decision Point:
- **If MVP works:** Continue to hardening phases
- **If MVP fails:** Debug sync/handshake before proceeding

---

## Week 5-6: Parallel Hardening

### Track A: Security Hardening (Week 5-6)

| Week | Day | Deliverable | Risk |
|------|-----|-------------|------|
| 5 | 1-2 | `KeyRotationManager` with 7-day grace period | Medium |
| 5 | 3-4 | `DELETE /peers/{peer_id}` revocation endpoint | Medium |
| 5 | 5 | Rate limiting on `/sync` and `/telemetry` | Low |
| 6 | 1-2 | `AuditLogger` for security events | Low |
| 6 | 3-5 | Security tests: rotation, revocation, rate limits | Medium |

### Track B: Privacy & Consent (Week 5-6)

| Week | Day | Deliverable | Risk |
|------|-----|-------------|------|
| 5 | 1-2 | `PrivacySettings` model and storage | Low |
| 5 | 3-4 | `PUT /privacy-settings` endpoint | Low |
| 5 | 5 | UI toggle for "Pause Sync" | Low |
| 6 | 1-2 | `PIIRedactor` for email, phone, SSN, credit card | Medium |
| 6 | 3-4 | `RetentionPolicy` with 90-day default | Low |
| 6 | 5 | Privacy tests: redaction, retention, consent | Low |

**Parallelization:** These tracks have no dependencies on each other. Run simultaneously with 2 engineers or time-slice with 1.

---

## Week 7-8: Parallel Resilience

### Track A: Offline & Resilience (Week 7-8)

| Week | Day | Deliverable | Risk |
|------|-----|-------------|------|
| 7 | 1-2 | `OfflineQueue` with SQLite persistence | Medium |
| 7 | 3-4 | `RetryStrategy` with exponential backoff | Low |
| 7 | 5 | `NetworkMonitor` for online/offline detection | Low |
| 8 | 1-2 | Integrate offline queue into `SyncScheduler` | Medium |
| 8 | 3-4 | Integrate offline queue into `TelemetryClient` | Medium |
| 8 | 5 | Offline tests: queue, retry, recovery | High |

### Track B: Observability (Week 7-8)

| Week | Day | Deliverable | Risk |
|------|-----|-------------|------|
| 7 | 1-2 | `GET /sync/metrics/{peer_id}` endpoint | Low |
| 7 | 3-4 | `GET /dashboard/telemetry` aggregate endpoint | Low |
| 7 | 5 | `GET /debug/sync/{peer_id}` debug endpoint | Low |
| 8 | 1-2 | `AlertingSystem` for lag, queue depth, errors | Medium |
| 8 | 3-5 | Observability tests and documentation | Low |

---

## Week 9-10: Integration & Polish

### Week 9: Multi-Platform Parity

| Day | Deliverable | Risk |
|-----|-------------|------|
| 1-2 | iOS `BackendSyncClient` Swift SDK | Medium |
| 3-4 | Android `BackendSyncClient` Kotlin SDK | Medium |
| 5 | Cross-platform sync tests (iOS ↔ Web ↔ Android) | High |

### Week 10: Polish & Documentation

| Day | Deliverable | Risk |
|-----|-------------|------|
| 1-2 | End-to-end integration tests | Medium |
| 3 | Performance benchmarks (sync latency, queue depth) | Low |
| 4 | Documentation update (all protocols, APIs) | Low |
| 5 | Release prep, deployment to production | Medium |

---

## Resource Allocation

### Minimum Viable Team: 1 Engineer

```
Week 1-4:  Foundation + Core (sequential, 1 engineer)
Week 5-6:  Security → Privacy (sequential, 1 engineer)
Week 7-8:  Offline → Observability (sequential, 1 engineer)
Week 9-10: Multi-Platform + Polish (1 engineer)
```

**Duration:** 10 weeks

### Optimal Team: 2 Engineers

```
Week 1-4:  Engineer A: Backend (Identity, Handshake, Sync)
           Engineer B: Frontend (UI handshake, testing)
Week 5-6:  Engineer A: Security Hardening
           Engineer B: Privacy & Consent
Week 7-8:  Engineer A: Offline & Resilience
           Engineer B: Observability
Week 9-10: Both: Multi-Platform + Polish
```

**Duration:** 8 weeks

---

## Risk Mitigation

### High-Risk Items (Front-Load)

1. **State Sync (Week 3):** Most complex, highest risk of bugs
   - Mitigation: Start with Last-Write-Wins, upgrade to CRDT later
   - Fallback: If sync fails, local-only mode still works

2. **UI Handshake (Week 2):** Orchestrates both backends
   - Mitigation: Graceful degradation to hosted-only if local unavailable
   - Fallback: Manual `.env` override for testing

3. **Offline Recovery (Week 8):** Edge cases with queue replay
   - Mitigation: Extensive testing with network simulation
   - Fallback: Manual "force sync" button in UI

### Medium-Risk Items (Monitor)

4. **Key Rotation:** Breaking active sessions
5. **WebSocket Telemetry:** Connection stability
6. **Mobile SDKs:** Platform-specific quirks

### Low-Risk Items (Defer if Needed)

7. **PII Redaction:** Regex-based, well-understood
8. **Observability Endpoints:** Read-only, low complexity
9. **Documentation:** Can be done incrementally

---

## Success Metrics by Milestone

### MVP (Week 4)
- [ ] Handshake success rate: >95%
- [ ] Sync latency: <5 seconds
- [ ] Telemetry delivery: >99%

### Hardened (Week 8)
- [ ] Sync reliability: >99%
- [ ] Offline queue: <100MB, <1000 items
- [ ] Security: 0 unauthorized registrations
- [ ] Privacy: 100% PII redaction

### Production (Week 10)
- [ ] Cross-platform: iOS/Android/Web all working
- [ ] MTTR for sync issues: <5 minutes
- [ ] Documentation: Complete API reference

---

## Quick Start: Week 1, Day 1

```bash
# 1. Create identity module
touch backend_8825/identity.py

# 2. Implement BackendIdentity class
# - Generate backend_id from machine_id
# - Generate RSA-2048 keypair
# - Store private key in keychain

# 3. Add /identity endpoint to server.py
@app.get("/identity")
async def get_identity():
    return {
        "backend_id": identity.backend_id,
        "backend_type": "local",
        "public_key": identity.public_key,
        "capabilities": ["offline", "fast_context", "local_capture"],
        "version": "1.0"
    }

# 4. Test
curl http://localhost:8825/identity | jq .
```

---

## Decision Log

| Decision | Rationale | Reversible? |
|----------|-----------|-------------|
| Last-Write-Wins over CRDT | Simpler, lower risk for v1 | Yes |
| 5-second sync interval | Balance between freshness and load | Yes |
| 8-hour SBT expiration | Security vs UX tradeoff | Yes |
| OS Keychain for keys | Security best practice | No |
| SQLite for offline queue | Simple, reliable, portable | Yes |
| WebSocket for telemetry | Real-time, bidirectional | Yes |

---

## Files to Create (Ordered)

### Week 1-2
1. `backend_8825/identity.py`
2. `backend_8825/keychain.py`
3. `backend_8825/sbt.py`
4. `src/adapters/webAdapter.ts` (update handshake)

### Week 3-4
5. `backend_8825/sync_models.py`
6. `backend_8825/sync_scheduler.py`
7. `backend_8825/telemetry_models.py`
8. `backend_8825/telemetry_client.py`

### Week 5-6
9. `backend_8825/key_rotation.py`
10. `backend_8825/rate_limiter.py`
11. `backend_8825/audit_log.py`
12. `backend_8825/privacy_settings.py`
13. `backend_8825/pii_redactor.py`
14. `backend_8825/retention_policy.py`

### Week 7-8
15. `backend_8825/offline_queue.py`
16. `backend_8825/retry.py`
17. `backend_8825/network_monitor.py`
18. `backend_8825/alerting.py`

### Week 9-10
19. `mobile_sdk/BackendSyncClient.swift`
20. `mobile_sdk/BackendSyncClient.kt`

---

## Next Action

**Start Week 1, Day 1:** Create `backend_8825/identity.py` with `BackendIdentity` class.
