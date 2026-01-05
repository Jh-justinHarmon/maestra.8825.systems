#!/usr/bin/env python3
"""
Test script for Backend Sync Protocol - State Synchronization

Tests the full sync flow:
1. Register peers (from Week 2 test)
2. Create test conversation on local backend
3. Trigger sync from local to hosted
4. Verify hosted backend received the sync
"""

import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Add conversation_hub to path
CORE_DIR = Path(__file__).resolve().parents[4] / "users/justin_harmon/8825-Jh/8825_core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import requests
from identity import get_identity
from sbt import SessionBindingToken
from sync import ConversationSyncer, SyncPayload
from sbt import get_peer_registry

# Backend URLs
LOCAL_BACKEND = "http://localhost:8825"
HOSTED_BACKEND = "https://maestra-backend-8825-systems.fly.dev"


def setup_peer_registration():
    """Setup: Register both backends as peers (from Week 2)"""
    print("\n[Setup] Registering peers...")
    
    # Get identities
    local_identity_resp = requests.get(f"{LOCAL_BACKEND}/identity").json()
    hosted_identity_resp = requests.get(f"{HOSTED_BACKEND}/identity").json()
    
    # Create SBT
    local_backend_identity = get_identity(backend_type="local")
    sbt = SessionBindingToken.create(
        user_id="test_user@8825.systems",
        session_id="test_session_sync",
        local_backend_id=local_identity_resp['backend_id'],
        hosted_backend_id=hosted_identity_resp['backend_id'],
        local_private_key=local_backend_identity.private_key,
        expiration_hours=8
    )
    
    # Register local with hosted
    requests.post(
        f"{HOSTED_BACKEND}/register-peer",
        json={
            "sbt": sbt.to_dict(),
            "peer_backend_id": local_identity_resp['backend_id'],
            "peer_public_key": local_identity_resp['public_key'],
            "peer_capabilities": local_identity_resp['capabilities']
        }
    )
    
    # Register hosted with local
    requests.post(
        f"{LOCAL_BACKEND}/register-peer",
        json={
            "sbt": sbt.to_dict(),
            "peer_backend_id": hosted_identity_resp['backend_id'],
            "peer_public_key": hosted_identity_resp['public_key'],
            "peer_capabilities": hosted_identity_resp['capabilities']
        }
    )
    
    print("✓ Peers registered")
    return local_identity_resp, hosted_identity_resp


def test_sync():
    print("=" * 80)
    print("Backend Sync Protocol - State Synchronization Test")
    print("=" * 80)
    
    # Setup peer registration
    local_identity, hosted_identity = setup_peer_registration()
    
    # Step 1: Create test conversation on local backend
    print("\n[Step 1] Creating test conversation on local backend...")
    
    try:
        from conversation_hub import ConversationHub
        
        hub = ConversationHub()
        
        # Create a test conversation
        conv_id = hub.create_conversation(
            title="Test Sync Conversation",
            source_backend=local_identity['backend_id']
        )
        
        # Add a test message
        msg_id = hub.add_message(
            conv_id=conv_id,
            content="This is a test message for sync",
            source_backend=local_identity['backend_id'],
            role="user"
        )
        
        print(f"✓ Created conversation: {conv_id}")
        print(f"  Message: {msg_id}")
        
    except Exception as e:
        print(f"✗ Failed to create conversation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Manually trigger sync from local to hosted
    print("\n[Step 2] Syncing conversation to hosted backend...")
    
    try:
        # Get local backend identity and peer registry
        identity = get_identity(backend_type="local")
        peer_registry = get_peer_registry()
        
        # Create syncer
        syncer = ConversationSyncer(hub, identity, peer_registry)
        
        # Sync with hosted backend
        result = asyncio.run(
            syncer.sync_with_peer(hosted_identity['backend_id'])
        )
        
        print(f"✓ Sync completed")
        print(f"  Conversations sent: {result.get('conversations_received', 0)}")
        print(f"  Merged on hosted: {result.get('conversations_merged', 0)}")
        
    except Exception as e:
        print(f"✗ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Verify sync was received by hosted backend
    print("\n[Step 3] Verifying hosted backend received sync...")
    
    # Check hosted backend logs (we can't query conversations since it's a stub)
    # But we can verify the sync endpoint was called successfully
    if result.get('status') == 'synced':
        print("✓ Hosted backend acknowledged sync")
        print(f"  Sync ID: {result.get('sync_id', 'N/A')}")
    else:
        print("✗ Hosted backend did not acknowledge sync")
        return False
    
    print("\n" + "=" * 80)
    print("Backend Sync Protocol - State Synchronization: PASSED ✓")
    print("=" * 80)
    print("\nNote: Hosted backend is currently a stub (no persistence)")
    print("In production, it would store conversations in a database")
    
    return True


if __name__ == "__main__":
    success = test_sync()
    exit(0 if success else 1)
