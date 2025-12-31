# Backend Sync Protocol - Implementation Plan
## Comprehensive Phased Rollout

**Status:** Implementation Roadmap  
**Version:** 1.0  
**Last Updated:** 2025-12-31  
**Estimated Duration:** 12-16 weeks

---

## Overview

This plan implements the Backend Synchronization Protocol v1 in 8 phases, addressing all critical considerations:
- Identity & key management
- Bidirectional authentication
- State synchronization
- Telemetry streaming
- Offline resilience
- Security hardening
- Privacy controls
- Multi-platform support
- Observability

---

## Phase 0: Foundation - Identity & Key Management
**Duration:** 1-2 weeks  
**Goal:** Establish cryptographic identity for both backends

### Deliverables

#### 1. Backend Identity System
**File:** `backend_8825/identity.py`
```python
class BackendIdentity:
    """Cryptographic identity for local/hosted backends"""
    
    def __init__(self):
        self.backend_id = self._generate_backend_id()
        self.backend_type = "local" | "hosted"
        self.public_key, self.private_key = self._load_or_generate_keypair()
        self.capabilities = self._detect_capabilities()
        self.created_at = datetime.utcnow()
    
    def _generate_backend_id(self):
        """SHA256 of machine_id (local) or deployment_id (hosted)"""
        pass
    
    def _load_or_generate_keypair(self):
        """Load from keychain or generate new RSA-2048 keypair"""
        pass
    
    def sign(self, data: dict) -> str:
        """Sign data with private key"""
        pass
    
    def verify(self, data: dict, signature: str, peer_public_key: str) -> bool:
        """Verify signature from peer"""
        pass
```

#### 2. Keychain Integration (Local Backend)
**File:** `backend_8825/keychain.py`
```python
import keyring

class KeychainManager:
    """Secure storage for private keys using OS keychain"""
    
    SERVICE_NAME = "com.8825.maestra.backend"
    
    def store_private_key(self, key_pem: str):
        """Store private key in macOS Keychain / Windows Credential Manager"""
        keyring.set_password(self.SERVICE_NAME, "private_key", key_pem)
    
    def load_private_key(self) -> Optional[str]:
        """Load private key from keychain"""
        return keyring.get_password(self.SERVICE_NAME, "private_key")
    
    def delete_private_key(self):
        """Revoke/delete private key"""
        keyring.delete_password(self.SERVICE_NAME, "private_key")
```

#### 3. Identity Endpoint (Both Backends)
**Endpoint:** `GET /identity`
```python
@app.get("/identity")
async def get_identity():
    """Return backend identity (public info only)"""
    return {
        "backend_id": identity.backend_id,
        "backend_type": identity.backend_type,
        "public_key": identity.public_key,
        "capabilities": identity.capabilities,
        "version": "1.0",
        "created_at": identity.created_at.isoformat()
    }
```

### Success Criteria
- [ ] Local backend generates unique `backend_id` on first run
- [ ] Private key stored in OS keychain (not plain text)
- [ ] Public key accessible via `/identity` endpoint
- [ ] Hosted backend has static `backend_id` (deployment-based)
- [ ] Sign/verify functions work with test data

### Tests
```python
def test_backend_identity_generation():
    identity = BackendIdentity()
    assert identity.backend_id.startswith("local_sha256_")
    assert identity.public_key.startswith("-----BEGIN PUBLIC KEY-----")

def test_keychain_storage():
    manager = KeychainManager()
    test_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
    manager.store_private_key(test_key)
    loaded = manager.load_private_key()
    assert loaded == test_key
```

---

## Phase 1: Handshake & Session Binding
**Duration:** 2 weeks  
**Goal:** Establish bidirectional trust via Session Binding Token (SBT)

### Deliverables

#### 1. Session Binding Token (SBT) Generator
**File:** `backend_8825/sbt.py`
```python
import hmac
import hashlib
import json
from datetime import datetime, timedelta

class SessionBindingToken:
    """Cryptographically binds local and hosted backends to same session"""
    
    def __init__(self, session_id: str, local_backend_id: str, 
                 hosted_backend_id: str, user_id: str):
        self.session_id = session_id
        self.local_backend_id = local_backend_id
        self.hosted_backend_id = hosted_backend_id
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=8)
        self.signature = None
    
    def sign(self, shared_secret: str):
        """Sign SBT with HMAC-SHA256"""
        payload = {
            "session_id": self.session_id,
            "local_backend_id": self.local_backend_id,
            "hosted_backend_id": self.hosted_backend_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat()
        }
        message = json.dumps(payload, sort_keys=True)
        self.signature = hmac.new(
            shared_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return self.signature
    
    def verify(self, shared_secret: str) -> bool:
        """Verify SBT signature"""
        if datetime.utcnow() > self.expires_at:
            return False  # Expired
        expected = self.sign(shared_secret)
        return hmac.compare_digest(expected, self.signature)
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "local_backend_id": self.local_backend_id,
            "hosted_backend_id": self.hosted_backend_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "signature": self.signature
        }
```

#### 2. Peer Registration Endpoint (Both Backends)
**Endpoint:** `POST /register-peer`
```python
@app.post("/register-peer")
async def register_peer(request: PeerRegistrationRequest):
    """Register a peer backend for sync"""
    # 1. Verify SBT signature
    sbt = SessionBindingToken(**request.sbt)
    if not sbt.verify(SHARED_SECRET):
        raise HTTPException(401, "Invalid SBT signature")
    
    # 2. Verify peer identity
    peer_identity = request.backend_identity
    if not verify_public_key(peer_identity.public_key):
        raise HTTPException(401, "Invalid public key")
    
    # 3. Store peer registration
    peer_id = f"peer_{uuid.uuid4().hex[:8]}"
    peer_registry[peer_id] = {
        "backend_id": peer_identity.backend_id,
        "backend_type": peer_identity.backend_type,
        "public_key": peer_identity.public_key,
        "capabilities": peer_identity.capabilities,
        "sbt": sbt.to_dict(),
        "registered_at": datetime.utcnow().isoformat()
    }
    
    # 4. Return sync endpoints
    return {
        "status": "registered",
        "peer_id": peer_id,
        "sync_endpoint": f"{BASE_URL}/sync/{peer_id}",
        "telemetry_endpoint": f"{BASE_URL}/telemetry/{peer_id}",
        "sync_interval_ms": 5000
    }
```

#### 3. UI Handshake Flow (Enhanced)
**File:** `src/adapters/webAdapter.ts`
```typescript
async handshake(sessionId: string): Promise<HandshakeResult> {
  // 1. Detect both backends
  const [localIdentity, hostedIdentity] = await Promise.all([
    fetch('http://localhost:8825/identity').then(r => r.json()).catch(() => null),
    fetch(`${API_BASE}/identity`).then(r => r.json())
  ]);
  
  if (!localIdentity) {
    return { mode: 'hosted-only', hostedBackend: hostedIdentity };
  }
  
  // 2. Create Session Binding Token
  const sbt = {
    session_id: sessionId,
    local_backend_id: localIdentity.backend_id,
    hosted_backend_id: hostedIdentity.backend_id,
    user_id: this.userId,
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 8*3600*1000).toISOString()
  };
  
  // 3. Sign SBT (shared secret from initial handshake)
  sbt.signature = await this.signSBT(sbt, this.sharedSecret);
  
  // 4. Local backend registers with hosted
  const localToHosted = await fetch(`${API_BASE}/register-peer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      backend_identity: localIdentity,
      sbt: sbt
    })
  }).then(r => r.json());
  
  // 5. Hosted backend registers with local
  const hostedToLocal = await fetch('http://localhost:8825/register-peer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      backend_identity: hostedIdentity,
      sbt: sbt
    })
  }).then(r => r.json());
  
  return {
    mode: 'hybrid',
    localBackend: localIdentity,
    hostedBackend: hostedIdentity,
    localPeerId: hostedToLocal.peer_id,
    hostedPeerId: localToHosted.peer_id,
    sbt: sbt
  };
}
```

### Success Criteria
- [ ] UI detects both backends and creates SBT
- [ ] Local backend successfully registers with hosted
- [ ] Hosted backend successfully registers with local
- [ ] SBT signature verification works on both ends
- [ ] Peer registry stores registration info
- [ ] SBT expiration enforced (8 hours)

### Tests
```python
def test_sbt_creation_and_verification():
    sbt = SessionBindingToken("sess_123", "local_abc", "hosted_xyz", "user_1")
    sbt.sign("shared_secret")
    assert sbt.verify("shared_secret") == True
    assert sbt.verify("wrong_secret") == False

def test_peer_registration():
    response = client.post("/register-peer", json={
        "backend_identity": {...},
        "sbt": {...}
    })
    assert response.status_code == 200
    assert "peer_id" in response.json()
```

---

## Phase 2: State Synchronization (Simple)
**Duration:** 2-3 weeks  
**Goal:** Bidirectional conversation sync with Last-Write-Wins strategy

### Deliverables

#### 1. Sync Data Model
**File:** `backend_8825/sync_models.py`
```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MessageSync(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    surface: str
    source_backend: str  # "local" or "hosted"
    version: int  # Lamport clock

class ConversationSync(BaseModel):
    conversation_id: str
    version: int  # Lamport clock for entire conversation
    messages: List[MessageSync]
    surfaces: List[str]
    last_modified: str
    source_backend: str

class SyncPayload(BaseModel):
    sync_id: str
    timestamp: str
    conversations: List[ConversationSync]
    signature: str
```

#### 2. Sync Endpoint (Both Backends)
**Endpoint:** `POST /sync/{peer_id}`
```python
@app.post("/sync/{peer_id}")
async def sync_conversations(peer_id: str, payload: SyncPayload):
    """Receive sync from peer backend"""
    # 1. Verify peer is registered
    peer = peer_registry.get(peer_id)
    if not peer:
        raise HTTPException(404, "Peer not found")
    
    # 2. Verify signature
    if not verify_signature(payload, peer["public_key"]):
        raise HTTPException(401, "Invalid signature")
    
    # 3. Merge conversations (Last-Write-Wins)
    conflicts = []
    for conv_sync in payload.conversations:
        local_conv = conversation_hub.get(conv_sync.conversation_id)
        
        if not local_conv:
            # New conversation, accept
            conversation_hub.create(conv_sync)
        elif conv_sync.version > local_conv.version:
            # Peer has newer version, accept
            conversation_hub.update(conv_sync)
        elif conv_sync.version < local_conv.version:
            # We have newer version, ignore
            pass
        else:
            # Same version, check timestamp
            if conv_sync.last_modified > local_conv.last_modified:
                conversation_hub.update(conv_sync)
    
    # 4. Acknowledge sync
    return {
        "status": "synced",
        "acked_sync_id": payload.sync_id,
        "conflicts": conflicts,
        "next_sync_in_ms": 5000
    }
```

#### 3. Sync Scheduler (Local Backend)
**File:** `backend_8825/sync_scheduler.py`
```python
import asyncio

class SyncScheduler:
    """Periodically sync conversations to hosted backend"""
    
    def __init__(self, peer_id: str, sync_endpoint: str, interval_ms: int = 5000):
        self.peer_id = peer_id
        self.sync_endpoint = sync_endpoint
        self.interval_ms = interval_ms
        self.running = False
    
    async def start(self):
        """Start sync loop"""
        self.running = True
        while self.running:
            try:
                await self.sync_once()
            except Exception as e:
                logger.error(f"Sync failed: {e}")
            await asyncio.sleep(self.interval_ms / 1000)
    
    async def sync_once(self):
        """Perform one sync cycle"""
        # 1. Get all conversations modified since last sync
        conversations = conversation_hub.get_modified_since(self.last_sync)
        
        # 2. Build sync payload
        payload = SyncPayload(
            sync_id=f"sync_{uuid.uuid4().hex}",
            timestamp=datetime.utcnow().isoformat(),
            conversations=[self._to_sync_model(c) for c in conversations],
            signature=""
        )
        
        # 3. Sign payload
        payload.signature = identity.sign(payload.dict())
        
        # 4. Send to peer
        response = await httpx.post(self.sync_endpoint, json=payload.dict())
        
        # 5. Update last sync timestamp
        if response.status_code == 200:
            self.last_sync = datetime.utcnow()
    
    def stop(self):
        """Stop sync loop"""
        self.running = False
```

### Success Criteria
- [ ] Local backend syncs conversations to hosted every 5 seconds
- [ ] Hosted backend receives and merges conversations
- [ ] Last-Write-Wins strategy prevents conflicts
- [ ] Messages marked with `source_backend` field
- [ ] Lamport clocks increment correctly
- [ ] Sync works bidirectionally (hosted → local too)

### Tests
```python
def test_conversation_sync():
    # 1. Create conversation on local
    local_conv = conversation_hub.create("test_conv")
    
    # 2. Trigger sync
    sync_scheduler.sync_once()
    
    # 3. Verify hosted backend has it
    hosted_conv = hosted_client.get("/conversations/test_conv")
    assert hosted_conv["conversation_id"] == "test_conv"
    assert hosted_conv["source_backend"] == "local"
```

---

## Phase 3: Telemetry Streaming
**Duration:** 2 weeks  
**Goal:** Real-time event streaming from local to hosted

### Deliverables

#### 1. Telemetry Event Model
**File:** `backend_8825/telemetry_models.py`
```python
class TelemetryEvent(BaseModel):
    event_id: str
    event_type: str  # "advisor_ask", "conversation_sync", "capture", etc.
    session_id: str
    timestamp: str
    source_backend: str
    metadata: dict  # Event-specific data
    
    # Performance metrics
    latency_ms: Optional[int]
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    model: Optional[str]
```

#### 2. WebSocket Telemetry Endpoint (Hosted Backend)
**Endpoint:** `WS /telemetry/{peer_id}`
```python
@app.websocket("/telemetry/{peer_id}")
async def telemetry_stream(websocket: WebSocket, peer_id: str):
    """Receive real-time telemetry from peer"""
    await websocket.accept()
    
    # Verify peer
    peer = peer_registry.get(peer_id)
    if not peer:
        await websocket.close(code=1008, reason="Peer not found")
        return
    
    try:
        while True:
            # Receive event
            data = await websocket.receive_json()
            event = TelemetryEvent(**data)
            
            # Store in telemetry database
            await telemetry_db.insert(event)
            
            # Aggregate metrics
            await metrics_aggregator.process(event)
            
            # Acknowledge
            await websocket.send_json({"status": "acked", "event_id": event.event_id})
    except WebSocketDisconnect:
        logger.info(f"Peer {peer_id} disconnected")
```

#### 3. Telemetry Client (Local Backend)
**File:** `backend_8825/telemetry_client.py`
```python
import websockets

class TelemetryClient:
    """Stream telemetry events to hosted backend"""
    
    def __init__(self, peer_id: str, endpoint: str):
        self.peer_id = peer_id
        self.endpoint = endpoint.replace("http", "ws")  # Convert to WS
        self.ws = None
        self.queue = asyncio.Queue()
    
    async def connect(self):
        """Establish WebSocket connection"""
        self.ws = await websockets.connect(self.endpoint)
        asyncio.create_task(self._send_loop())
    
    async def emit(self, event: TelemetryEvent):
        """Queue event for sending"""
        await self.queue.put(event)
    
    async def _send_loop(self):
        """Send queued events"""
        while True:
            event = await self.queue.get()
            try:
                await self.ws.send(json.dumps(event.dict()))
                ack = await self.ws.recv()
                logger.debug(f"Event {event.event_id} acknowledged")
            except Exception as e:
                logger.error(f"Failed to send event: {e}")
                # Re-queue for retry
                await self.queue.put(event)
```

#### 4. Telemetry Instrumentation
**File:** `backend_8825/server.py` (add instrumentation)
```python
@app.post("/api/maestra/advisor/ask")
async def advisor_ask(request: AdvisorAskRequest):
    start_time = time.time()
    
    # Process request
    response = await process_advisor_request(request)
    
    # Emit telemetry event
    await telemetry_client.emit(TelemetryEvent(
        event_id=f"evt_{uuid.uuid4().hex}",
        event_type="advisor_ask",
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat(),
        source_backend="local",
        metadata={
            "question": request.question[:100],  # Truncate
            "mode": request.mode
        },
        latency_ms=int((time.time() - start_time) * 1000),
        tokens_used=response.tokens_used,
        cost_usd=response.cost_usd,
        model=response.model
    ))
    
    return response
```

### Success Criteria
- [ ] Local backend establishes WebSocket to hosted
- [ ] Events stream in real-time (<100ms latency)
- [ ] Hosted backend stores events in telemetry DB
- [ ] Failed events are retried (queue-based)
- [ ] Telemetry includes performance metrics (latency, cost, tokens)

### Tests
```python
async def test_telemetry_streaming():
    # 1. Connect telemetry client
    await telemetry_client.connect()
    
    # 2. Emit test event
    event = TelemetryEvent(
        event_id="test_123",
        event_type="test",
        session_id="sess_1",
        timestamp=datetime.utcnow().isoformat(),
        source_backend="local",
        metadata={}
    )
    await telemetry_client.emit(event)
    
    # 3. Verify hosted received it
    await asyncio.sleep(0.5)
    stored = await telemetry_db.get("test_123")
    assert stored is not None
```

---

## Phase 4: Offline & Resilience
**Duration:** 2 weeks  
**Goal:** Handle network failures, offline mode, and sync recovery

### Deliverables

#### 1. Offline Queue (Local Backend)
**File:** `backend_8825/offline_queue.py`
```python
class OfflineQueue:
    """Persistent queue for sync/telemetry when offline"""
    
    def __init__(self, db_path: str = "~/.8825/offline_queue.db"):
        self.db = sqlite3.connect(db_path)
        self._init_schema()
        self.max_size_mb = 100  # Disk limit
    
    def enqueue(self, item_type: str, payload: dict):
        """Add item to queue"""
        if self._get_size_mb() > self.max_size_mb:
            # Evict oldest items
            self._evict_oldest(0.2)  # Remove 20%
        
        self.db.execute("""
            INSERT INTO queue (item_type, payload, created_at)
            VALUES (?, ?, ?)
        """, (item_type, json.dumps(payload), datetime.utcnow().isoformat()))
        self.db.commit()
    
    def dequeue_batch(self, limit: int = 100) -> List[dict]:
        """Get batch of items to process"""
        cursor = self.db.execute("""
            SELECT id, item_type, payload FROM queue
            ORDER BY created_at ASC LIMIT ?
        """, (limit,))
        return [{"id": row[0], "type": row[1], "payload": json.loads(row[2])} 
                for row in cursor.fetchall()]
    
    def mark_processed(self, item_ids: List[int]):
        """Remove processed items"""
        self.db.execute(f"""
            DELETE FROM queue WHERE id IN ({','.join('?' * len(item_ids))})
        """, item_ids)
        self.db.commit()
```

#### 2. Retry Logic with Exponential Backoff
**File:** `backend_8825/retry.py`
```python
class RetryStrategy:
    """Exponential backoff for failed sync/telemetry"""
    
    def __init__(self, max_retries: int = 5, base_delay_ms: int = 1000):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.retry_counts = {}
    
    async def execute(self, key: str, func):
        """Execute with retry"""
        retries = self.retry_counts.get(key, 0)
        
        try:
            result = await func()
            self.retry_counts[key] = 0  # Reset on success
            return result
        except Exception as e:
            if retries >= self.max_retries:
                logger.error(f"Max retries exceeded for {key}")
                raise
            
            # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            delay_ms = self.base_delay_ms * (2 ** retries)
            logger.warning(f"Retry {retries+1}/{self.max_retries} for {key} in {delay_ms}ms")
            
            self.retry_counts[key] = retries + 1
            await asyncio.sleep(delay_ms / 1000)
            return await self.execute(key, func)
```

#### 3. Network Status Monitor
**File:** `backend_8825/network_monitor.py`
```python
class NetworkMonitor:
    """Monitor network connectivity to hosted backend"""
    
    def __init__(self, hosted_url: str):
        self.hosted_url = hosted_url
        self.is_online = False
        self.last_check = None
    
    async def start(self):
        """Start monitoring loop"""
        while True:
            self.is_online = await self._check_connectivity()
            self.last_check = datetime.utcnow()
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def _check_connectivity(self) -> bool:
        """Ping hosted backend"""
        try:
            response = await httpx.get(f"{self.hosted_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
```

#### 4. Offline-Aware Sync Scheduler
**Update:** `backend_8825/sync_scheduler.py`
```python
class SyncScheduler:
    async def sync_once(self):
        """Sync with offline queue support"""
        # 1. Check network status
        if not network_monitor.is_online:
            logger.info("Offline, queueing sync")
            offline_queue.enqueue("sync", self._build_sync_payload())
            return
        
        # 2. Process offline queue first
        queued_items = offline_queue.dequeue_batch(limit=10)
        for item in queued_items:
            try:
                await self._send_sync(item["payload"])
                offline_queue.mark_processed([item["id"]])
            except Exception as e:
                logger.error(f"Failed to process queued sync: {e}")
                break  # Stop processing, will retry later
        
        # 3. Sync current state
        await self._send_sync(self._build_sync_payload())
```

### Success Criteria
- [ ] Local backend queues sync/telemetry when offline
- [ ] Queue persists to disk (survives restart)
- [ ] Queue has size limit (100MB) with eviction
- [ ] Retry logic with exponential backoff
- [ ] Network monitor detects online/offline transitions
- [ ] Queued items processed when back online

### Tests
```python
def test_offline_queue():
    queue = OfflineQueue()
    queue.enqueue("sync", {"conversation_id": "test"})
    items = queue.dequeue_batch(limit=10)
    assert len(items) == 1
    queue.mark_processed([items[0]["id"]])
    assert len(queue.dequeue_batch()) == 0

async def test_retry_strategy():
    retries = 0
    async def flaky_func():
        nonlocal retries
        retries += 1
        if retries < 3:
            raise Exception("Fail")
        return "success"
    
    strategy = RetryStrategy(max_retries=5)
    result = await strategy.execute("test", flaky_func)
    assert result == "success"
    assert retries == 3
```

---

## Phase 5: Security Hardening
**Duration:** 2 weeks  
**Goal:** Key rotation, revocation, rate limiting, and audit logging

### Deliverables

#### 1. Key Rotation System
**File:** `backend_8825/key_rotation.py`
```python
class KeyRotationManager:
    """Rotate backend keypairs without breaking SBTs"""
    
    def __init__(self):
        self.current_key = None
        self.previous_keys = []  # Keep last 2 keys for grace period
    
    async def rotate(self):
        """Generate new keypair and notify peers"""
        # 1. Generate new keypair
        new_public, new_private = generate_keypair()
        
        # 2. Store old key in grace period list
        self.previous_keys.append({
            "public_key": self.current_key.public_key,
            "private_key": self.current_key.private_key,
            "rotated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=7)
        })
        
        # 3. Update current key
        self.current_key = {"public_key": new_public, "private_key": new_private}
        keychain_manager.store_private_key(new_private)
        
        # 4. Notify all peers
        for peer_id, peer in peer_registry.items():
            await self._notify_peer_key_rotation(peer_id, new_public)
        
        # 5. Clean up expired old keys
        self.previous_keys = [k for k in self.previous_keys 
                              if k["expires_at"] > datetime.utcnow()]
```

#### 2. Peer Revocation
**Endpoint:** `DELETE /peers/{peer_id}` (Hosted Backend)
```python
@app.delete("/peers/{peer_id}")
async def revoke_peer(peer_id: str, admin_token: str):
    """Revoke a peer backend (emergency)"""
    # 1. Verify admin authorization
    if not verify_admin_token(admin_token):
        raise HTTPException(403, "Unauthorized")
    
    # 2. Remove peer from registry
    peer = peer_registry.pop(peer_id, None)
    if not peer:
        raise HTTPException(404, "Peer not found")
    
    # 3. Add to revocation list
    revocation_list.add(peer["backend_id"])
    
    # 4. Close any active connections
    await close_peer_connections(peer_id)
    
    return {"status": "revoked", "peer_id": peer_id}
```

#### 3. Rate Limiting (Hosted Backend)
**File:** `backend_8825/rate_limiter.py`
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/sync/{peer_id}")
@limiter.limit("100/minute")  # Max 100 syncs per minute per peer
async def sync_conversations(peer_id: str, payload: SyncPayload):
    # ... existing sync logic
    pass

@app.websocket("/telemetry/{peer_id}")
@limiter.limit("1000/minute")  # Max 1000 events per minute
async def telemetry_stream(websocket: WebSocket, peer_id: str):
    # ... existing telemetry logic
    pass
```

#### 4. Audit Logging
**File:** `backend_8825/audit_log.py`
```python
class AuditLogger:
    """Log security-relevant events"""
    
    def __init__(self, log_path: str = "~/.8825/audit.log"):
        self.log_path = log_path
    
    def log_event(self, event_type: str, peer_id: str, details: dict):
        """Log audit event"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "peer_id": peer_id,
            "details": details
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

# Usage
audit_logger.log_event("peer_registered", peer_id, {
    "backend_id": peer["backend_id"],
    "capabilities": peer["capabilities"]
})

audit_logger.log_event("sbt_verification_failed", peer_id, {
    "reason": "expired",
    "expires_at": sbt.expires_at
})
```

### Success Criteria
- [ ] Key rotation works without breaking active sessions
- [ ] Peer revocation immediately blocks sync/telemetry
- [ ] Rate limiting prevents abuse (100 syncs/min, 1000 events/min)
- [ ] Audit log captures all security events
- [ ] Old keys kept for 7-day grace period

### Tests
```python
async def test_key_rotation():
    old_public_key = identity.public_key
    await key_rotation_manager.rotate()
    new_public_key = identity.public_key
    assert old_public_key != new_public_key
    # Verify old key still works for 7 days
    assert key_rotation_manager.verify_with_old_key(old_public_key)

def test_rate_limiting():
    # Exceed rate limit
    for i in range(150):
        response = client.post(f"/sync/{peer_id}", json={...})
    assert response.status_code == 429  # Too Many Requests
```

---

## Phase 6: Privacy & Consent
**Duration:** 1-2 weeks  
**Goal:** User controls for sync, redaction, and data retention

### Deliverables

#### 1. Privacy Settings Model
**File:** `backend_8825/privacy_settings.py`
```python
class PrivacySettings(BaseModel):
    user_id: str
    sync_enabled: bool = True  # Master toggle
    sync_conversations: bool = True
    sync_telemetry: bool = True
    redact_pii: bool = True  # Auto-redact PII before sync
    retention_days: int = 90  # Delete synced data after N days
    allowed_surfaces: List[str] = ["web", "ios", "extension"]
```

#### 2. Privacy Controls Endpoint
**Endpoint:** `PUT /privacy-settings`
```python
@app.put("/privacy-settings")
async def update_privacy_settings(settings: PrivacySettings):
    """Update user privacy preferences"""
    # Store settings
    privacy_db.upsert(settings.user_id, settings.dict())
    
    # If sync disabled, pause sync scheduler
    if not settings.sync_enabled:
        sync_scheduler.pause()
    else:
        sync_scheduler.resume()
    
    return {"status": "updated"}
```

#### 3. PII Redaction
**File:** `backend_8825/pii_redactor.py`
```python
import re

class PIIRedactor:
    """Redact PII before syncing to hosted backend"""
    
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    }
    
    def redact(self, text: str) -> str:
        """Redact PII from text"""
        for pii_type, pattern in self.PATTERNS.items():
            text = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", text)
        return text
    
    def redact_conversation(self, conv: ConversationSync) -> ConversationSync:
        """Redact PII from entire conversation"""
        for msg in conv.messages:
            msg.content = self.redact(msg.content)
        return conv
```

#### 4. Data Retention Policy
**File:** `backend_8825/retention_policy.py`
```python
class RetentionPolicy:
    """Delete old synced data based on user settings"""
    
    async def enforce(self):
        """Run retention policy (daily cron)"""
        for user_id, settings in privacy_db.all():
            cutoff_date = datetime.utcnow() - timedelta(days=settings.retention_days)
            
            # Delete conversations older than retention period
            deleted = await conversation_hub.delete_before(user_id, cutoff_date)
            logger.info(f"Deleted {deleted} conversations for {user_id} (retention: {settings.retention_days} days)")
```

### Success Criteria
- [ ] UI toggle for "Pause Sync" (stops all sync/telemetry)
- [ ] PII redaction before sync (email, phone, SSN, credit card)
- [ ] Retention policy deletes old data (default 90 days)
- [ ] Privacy settings persist across sessions
- [ ] User can export/delete all synced data (GDPR)

### Tests
```python
def test_pii_redaction():
    redactor = PIIRedactor()
    text = "My email is john@example.com and phone is 555-123-4567"
    redacted = redactor.redact(text)
    assert "john@example.com" not in redacted
    assert "555-123-4567" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted

async def test_retention_policy():
    # Create old conversation
    old_conv = conversation_hub.create("old", created_at=datetime.utcnow() - timedelta(days=100))
    
    # Run retention policy (90 days)
    await retention_policy.enforce()
    
    # Verify deleted
    assert conversation_hub.get("old") is None
```

---

## Phase 7: Multi-Platform Parity
**Duration:** 2-3 weeks  
**Goal:** iOS/Android companions use same sync protocol

### Deliverables

#### 1. Mobile Companion SDK
**File:** `mobile_sdk/BackendSyncClient.swift` (iOS)
```swift
class BackendSyncClient {
    let localBackendURL: URL
    let hostedBackendURL: URL
    var sbt: SessionBindingToken?
    
    func handshake(sessionId: String, userId: String) async throws -> HandshakeResult {
        // 1. Detect both backends
        let localIdentity = try? await fetchIdentity(from: localBackendURL)
        let hostedIdentity = try await fetchIdentity(from: hostedBackendURL)
        
        guard let localIdentity = localIdentity else {
            return .hostedOnly(hostedIdentity)
        }
        
        // 2. Create SBT
        let sbt = SessionBindingToken(
            sessionId: sessionId,
            localBackendId: localIdentity.backendId,
            hostedBackendId: hostedIdentity.backendId,
            userId: userId
        )
        
        // 3. Sign SBT
        try sbt.sign(with: sharedSecret)
        
        // 4. Register peers
        let localPeerId = try await registerPeer(
            at: hostedBackendURL,
            identity: localIdentity,
            sbt: sbt
        )
        
        let hostedPeerId = try await registerPeer(
            at: localBackendURL,
            identity: hostedIdentity,
            sbt: sbt
        )
        
        self.sbt = sbt
        return .hybrid(localPeerId: localPeerId, hostedPeerId: hostedPeerId)
    }
    
    func syncConversations() async throws {
        // Same sync protocol as web
    }
}
```

#### 2. Platform-Agnostic Protocol Tests
**File:** `tests/test_cross_platform_sync.py`
```python
def test_ios_to_web_sync():
    """Verify iOS companion can sync with web UI"""
    # 1. iOS creates conversation
    ios_conv = ios_client.create_conversation("test")
    
    # 2. Trigger sync
    ios_client.sync()
    
    # 3. Web UI should see it
    web_conv = web_client.get_conversation("test")
    assert web_conv["conversation_id"] == "test"
    assert "ios" in web_conv["surfaces"]

def test_android_to_hosted_telemetry():
    """Verify Android companion streams telemetry"""
    # 1. Android emits event
    android_client.emit_telemetry({
        "event_type": "capture",
        "source_backend": "android_local"
    })
    
    # 2. Hosted backend should receive it
    time.sleep(1)
    events = hosted_client.get_telemetry_events(source="android_local")
    assert len(events) > 0
```

### Success Criteria
- [ ] iOS companion implements same handshake/sync protocol
- [ ] Android companion implements same handshake/sync protocol
- [ ] Cross-platform sync works (iOS ↔ Web ↔ Android)
- [ ] Mobile companions use OS keychain for private keys
- [ ] Protocol is truly platform-agnostic (no web-specific assumptions)

---

## Phase 8: Observability & Operations
**Duration:** 1-2 weeks  
**Goal:** Monitor sync health, debug issues, and optimize performance

### Deliverables

#### 1. Sync Metrics Endpoint
**Endpoint:** `GET /sync/metrics/{peer_id}`
```python
@app.get("/sync/metrics/{peer_id}")
async def get_sync_metrics(peer_id: str):
    """Get sync health metrics for peer"""
    peer = peer_registry.get(peer_id)
    if not peer:
        raise HTTPException(404, "Peer not found")
    
    return {
        "peer_id": peer_id,
        "backend_id": peer["backend_id"],
        "last_sync": peer.get("last_sync"),
        "sync_lag_seconds": (datetime.utcnow() - peer.get("last_sync", datetime.utcnow())).total_seconds(),
        "queue_depth": offline_queue.count(peer_id),
        "sync_success_rate": peer.get("sync_success_rate", 0),
        "last_error": peer.get("last_error"),
        "total_syncs": peer.get("total_syncs", 0),
        "total_events": peer.get("total_events", 0)
    }
```

#### 2. Telemetry Dashboard (Hosted Backend)
**File:** `backend_8825/telemetry_dashboard.py`
```python
@app.get("/dashboard/telemetry")
async def telemetry_dashboard():
    """Aggregate telemetry across all peers"""
    stats = {
        "total_peers": len(peer_registry),
        "online_peers": sum(1 for p in peer_registry.values() if p.get("is_online")),
        "total_events_24h": await telemetry_db.count_events(since=datetime.utcnow() - timedelta(days=1)),
        "avg_latency_ms": await telemetry_db.avg_latency(),
        "total_cost_24h": await telemetry_db.sum_cost(since=datetime.utcnow() - timedelta(days=1)),
        "top_peers_by_events": await telemetry_db.top_peers(limit=10)
    }
    return stats
```

#### 3. Sync Debugging Tools
**File:** `backend_8825/debug_tools.py`
```python
@app.get("/debug/sync/{peer_id}")
async def debug_sync(peer_id: str):
    """Debug sync issues for peer"""
    peer = peer_registry.get(peer_id)
    
    return {
        "peer_info": peer,
        "sbt_status": "valid" if sbt.verify(SHARED_SECRET) else "invalid",
        "sbt_expires_in": (sbt.expires_at - datetime.utcnow()).total_seconds(),
        "offline_queue": offline_queue.peek(peer_id, limit=10),
        "recent_errors": error_log.get_recent(peer_id, limit=10),
        "network_status": network_monitor.is_online,
        "last_successful_sync": peer.get("last_sync"),
        "sync_lag": (datetime.utcnow() - peer.get("last_sync", datetime.utcnow())).total_seconds()
    }
```

#### 4. Alerting System
**File:** `backend_8825/alerting.py`
```python
class AlertingSystem:
    """Alert on sync/telemetry issues"""
    
    async def check_health(self):
        """Run health checks and alert if needed"""
        for peer_id, peer in peer_registry.items():
            # Alert if sync lag > 5 minutes
            if peer.get("sync_lag_seconds", 0) > 300:
                await self.send_alert(f"Sync lag for {peer_id}: {peer['sync_lag_seconds']}s")
            
            # Alert if queue depth > 1000
            if offline_queue.count(peer_id) > 1000:
                await self.send_alert(f"Queue depth for {peer_id}: {offline_queue.count(peer_id)}")
            
            # Alert if success rate < 90%
            if peer.get("sync_success_rate", 1.0) < 0.9:
                await self.send_alert(f"Low sync success rate for {peer_id}: {peer['sync_success_rate']}")
```

### Success Criteria
- [ ] `/sync/metrics` shows real-time sync health
- [ ] Telemetry dashboard aggregates across all peers
- [ ] Debug tools help diagnose sync issues
- [ ] Alerting system catches problems (lag, queue depth, errors)
- [ ] Logs are structured and searchable

---

## Implementation Timeline

| Phase | Duration | Dependencies | Risk |
|-------|----------|--------------|------|
| Phase 0: Identity & Keys | 1-2 weeks | None | Low |
| Phase 1: Handshake & SBT | 2 weeks | Phase 0 | Medium |
| Phase 2: State Sync | 2-3 weeks | Phase 1 | High |
| Phase 3: Telemetry | 2 weeks | Phase 1 | Medium |
| Phase 4: Offline | 2 weeks | Phase 2, 3 | Medium |
| Phase 5: Security | 2 weeks | Phase 1, 2 | High |
| Phase 6: Privacy | 1-2 weeks | Phase 2 | Low |
| Phase 7: Multi-Platform | 2-3 weeks | Phase 1-3 | Medium |
| Phase 8: Observability | 1-2 weeks | Phase 2-4 | Low |

**Total: 12-16 weeks**

---

## Success Metrics

- **Sync Reliability:** >99% success rate
- **Sync Latency:** <5 seconds for typical conversation
- **Offline Queue:** <100MB disk usage, <1000 items
- **Telemetry Latency:** <100ms event delivery
- **Security:** 0 unauthorized peer registrations
- **Privacy:** 100% PII redaction before sync
- **Cross-Platform:** iOS/Android/Web all use same protocol
- **Observability:** <5 minute MTTR for sync issues

---

## Risk Mitigation

1. **CRDT Complexity:** Start with Last-Write-Wins, upgrade to CRDT later
2. **Clock Skew:** Use Lamport clocks, not wall-clock timestamps
3. **Key Management:** Use OS keychain, never plain text
4. **Network Failures:** Offline queue + exponential backoff
5. **Rate Limiting:** Prevent abuse, protect hosted backend
6. **Privacy:** PII redaction + user consent controls
7. **Multi-Platform:** Protocol tests ensure compatibility

---

## Next Steps

1. **Week 1-2:** Implement Phase 0 (Identity & Keys)
2. **Week 3-4:** Implement Phase 1 (Handshake & SBT)
3. **Week 5-7:** Implement Phase 2 (State Sync)
4. **Week 8-9:** Implement Phase 3 (Telemetry)
5. **Week 10-11:** Implement Phase 4 (Offline)
6. **Week 12-13:** Implement Phase 5 (Security)
7. **Week 14:** Implement Phase 6 (Privacy)
8. **Week 15-16:** Implement Phase 7 (Multi-Platform)
9. **Week 17:** Implement Phase 8 (Observability)

**Start with Phase 0 to establish foundation.**
