# Week 3: State Synchronization - Findings & Issues

## Issue Discovered: Hosted Backend Key Persistence

**Problem:**
- Hosted backend generates new RSA keypair on each restart
- Private key is not persisted (no BACKEND_PRIVATE_KEY env var set)
- This breaks SBT signature validation after restart
- Peer registrations are lost (in-memory only)

**Impact:**
- SBT created with old private key fails validation with new private key
- Peers must re-register after every hosted backend restart
- Not suitable for production without persistence

**Solutions:**

### Short-term (for testing):
1. Set BACKEND_PRIVATE_KEY environment variable on Fly.io
2. Use Fly.io secrets: `flyctl secrets set BACKEND_PRIVATE_KEY="..."`
3. This ensures same private key across restarts

### Long-term (for production):
1. **Database-backed peer registry** - Store peer registrations in PostgreSQL/Redis
2. **Database-backed key storage** - Store private keys in encrypted database
3. **Conversation persistence** - Store conversations in database (currently stub)

## Week 3 Progress

### ✅ Completed
- `sync.py` - ConversationSyncer with Last-Write-Wins merge logic
- `SyncPayload` - Data structure for conversation sync
- `SyncScheduler` - Automatic sync scheduler (ready to enable)
- `POST /sync` endpoint on both backends
- Security: Peer verification before accepting sync

### ⚠️ Blocked
- End-to-end sync testing blocked by key persistence issue
- Cannot test bidirectional sync without stable peer registration

### 🎯 Next Steps
1. Set BACKEND_PRIVATE_KEY on Fly.io for stable testing
2. Complete sync testing
3. Enable SyncScheduler for automatic syncing
4. Document Week 3 completion

## Architecture Notes

**Local Backend:**
- Has ConversationHub (file-based storage)
- Can persist conversations and peer registrations
- Private key stored in macOS Keychain

**Hosted Backend:**
- No ConversationHub (stub only)
- In-memory peer registry (lost on restart)
- Private key regenerated on restart (unless env var set)
- **Needs database for production**

## Test Results

### Week 2: Peer Registration ✅
- Passed when both backends had stable keys
- Mutual registration working correctly

### Week 3: Sync Endpoint ✅
- `/sync` endpoint accepts valid payloads
- `/sync` endpoint rejects unauthorized peers (403)
- Security working correctly

### Week 3: End-to-End Sync ⚠️
- Blocked by key persistence issue
- Need to set BACKEND_PRIVATE_KEY on Fly.io
