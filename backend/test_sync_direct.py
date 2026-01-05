#!/usr/bin/env python3
"""
Test script for Backend Sync Protocol - Direct Endpoint Test

Tests the sync endpoint without requiring peer registry:
1. Create test conversation locally
2. POST sync payload directly to /sync endpoint
3. Verify response
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from conversation_hub import ConversationHub
from sync import SyncPayload

# Backend URLs
LOCAL_BACKEND = "http://localhost:8825"
HOSTED_BACKEND = "https://maestra-backend-8825-systems.fly.dev"


def test_sync_endpoint():
    print("=" * 80)
    print("Backend Sync Protocol - Direct Endpoint Test (Week 3)")
    print("=" * 80)
    
    # Step 1: Create test conversation locally
    print("\n[Step 1] Creating test conversation locally...")
    try:
        hub = ConversationHub()
        
        conv_id = hub.create_conversation(
            title="Week 3 Sync Test",
            source_backend="local_test"
        )
        
        # Add test messages
        hub.add_message(
            conv_id=conv_id,
            content="First message from local backend",
            source_backend="local_test",
            role="user"
        )
        
        hub.add_message(
            conv_id=conv_id,
            content="Response from assistant",
            source_backend="local_test",
            role="assistant"
        )
        
        print(f"✓ Created conversation: {conv_id}")
        print(f"  Messages: {len(hub.get_conversation(conv_id).messages)}")
        
    except Exception as e:
        print(f"✗ Failed to create conversation: {e}")
        return False
    
    # Step 2: Create sync payload
    print("\n[Step 2] Creating sync payload...")
    try:
        sync_payload = SyncPayload(
            sync_id=f"sync_{uuid.uuid4().hex[:16]}",
            source_backend_id="local_test",
            target_backend_id="hosted_test",
            timestamp=datetime.utcnow().isoformat(),
            conversations=hub.get_all_conversations()
        )
        
        print(f"✓ Created sync payload")
        print(f"  Sync ID: {sync_payload.sync_id}")
        print(f"  Conversations: {len(sync_payload.conversations)}")
        
    except Exception as e:
        print(f"✗ Failed to create sync payload: {e}")
        return False
    
    # Step 3: POST to local backend /sync endpoint
    print("\n[Step 3] Testing local backend /sync endpoint...")
    try:
        response = requests.post(
            f"{LOCAL_BACKEND}/sync",
            json=sync_payload.to_dict(),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Local backend /sync endpoint works")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Conversations merged: {result.get('conversations_merged', 0)}")
        else:
            print(f"✗ Local backend returned {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"⚠ Local backend not running (expected for CI)")
        print(f"  Skipping local backend test")
    except Exception as e:
        print(f"✗ Local backend test failed: {e}")
        return False
    
    # Step 4: POST to hosted backend /sync endpoint
    print("\n[Step 4] Testing hosted backend /sync endpoint...")
    try:
        response = requests.post(
            f"{HOSTED_BACKEND}/sync",
            json=sync_payload.to_dict(),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Hosted backend /sync endpoint works")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Conversations merged: {result.get('conversations_merged', 0)}")
        else:
            print(f"✗ Hosted backend returned {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"✗ Hosted backend test failed: {e}")
        return False
    
    # Step 5: Verify sync payload structure
    print("\n[Step 5] Verifying sync payload structure...")
    try:
        payload_dict = sync_payload.to_dict()
        
        required_fields = ['sync_id', 'source_backend_id', 'target_backend_id', 'timestamp', 'conversations']
        missing = [f for f in required_fields if f not in payload_dict]
        
        if missing:
            print(f"✗ Missing fields: {missing}")
            return False
        
        print(f"✓ Sync payload structure valid")
        print(f"  Fields: {', '.join(required_fields)}")
        
    except Exception as e:
        print(f"✗ Payload validation failed: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("Backend Sync Protocol - Week 3: PASSED ✓")
    print("=" * 80)
    print("\nSummary:")
    print("✓ Conversation creation works")
    print("✓ Sync payload generation works")
    print("✓ /sync endpoint accepts payloads")
    print("✓ Payload structure is valid")
    print("\nNext: Week 4 - Telemetry streaming")
    
    return True


if __name__ == "__main__":
    success = test_sync_endpoint()
    exit(0 if success else 1)
