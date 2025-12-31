#!/usr/bin/env python3
"""
Test script for Backend Sync Protocol - Peer Registration

Tests the full flow:
1. Get identities from both backends
2. Create Session Binding Token (SBT)
3. Register local backend with hosted backend
4. Register hosted backend with local backend
5. Verify both backends have each other registered
"""

import requests
import json
from sbt import SessionBindingToken

# Backend URLs
LOCAL_BACKEND = "http://localhost:8825"
HOSTED_BACKEND = "https://maestra-backend-8825-systems.fly.dev"

def test_peer_registration():
    print("=" * 80)
    print("Backend Sync Protocol - Peer Registration Test")
    print("=" * 80)
    
    # Step 1: Get identities from both backends
    print("\n[Step 1] Fetching backend identities...")
    
    local_identity = requests.get(f"{LOCAL_BACKEND}/identity").json()
    print(f"✓ Local backend: {local_identity['backend_id']}")
    print(f"  Capabilities: {', '.join(local_identity['capabilities'])}")
    
    hosted_identity = requests.get(f"{HOSTED_BACKEND}/identity").json()
    print(f"✓ Hosted backend: {hosted_identity['backend_id']}")
    print(f"  Capabilities: {', '.join(hosted_identity['capabilities'])}")
    
    # Step 2: Create Session Binding Token (SBT)
    print("\n[Step 2] Creating Session Binding Token...")
    
    # Note: In production, the UI would create this after user authentication
    # For testing, we'll create it directly using the local backend's private key
    
    # We need to get the private key from the local backend's identity
    # In production, this would be done securely by the local backend
    from identity import get_identity
    local_backend_identity = get_identity(backend_type="local")
    
    sbt = SessionBindingToken.create(
        user_id="test_user@8825.systems",
        session_id="test_session_001",
        local_backend_id=local_identity['backend_id'],
        hosted_backend_id=hosted_identity['backend_id'],
        local_private_key=local_backend_identity.private_key,
        expiration_hours=8
    )
    
    print(f"✓ SBT created: {sbt.sbt_id}")
    print(f"  Expires: {sbt.expires_at}")
    print(f"  Signature: {sbt.signature[:32]}...")
    
    # Step 3: Register local backend with hosted backend
    print("\n[Step 3] Registering local backend with hosted backend...")
    
    register_local_payload = {
        "sbt": sbt.to_dict(),
        "peer_backend_id": local_identity['backend_id'],
        "peer_public_key": local_identity['public_key'],
        "peer_capabilities": local_identity['capabilities']
    }
    
    try:
        response = requests.post(
            f"{HOSTED_BACKEND}/register-peer",
            json=register_local_payload
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Local backend registered with hosted backend")
            print(f"  SBT ID: {result['sbt_id']}")
        else:
            print(f"✗ Registration failed: {response.status_code}")
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Registration failed: {e}")
        return False
    
    # Step 4: Register hosted backend with local backend
    print("\n[Step 4] Registering hosted backend with local backend...")
    
    register_hosted_payload = {
        "sbt": sbt.to_dict(),
        "peer_backend_id": hosted_identity['backend_id'],
        "peer_public_key": hosted_identity['public_key'],
        "peer_capabilities": hosted_identity['capabilities']
    }
    
    try:
        response = requests.post(
            f"{LOCAL_BACKEND}/register-peer",
            json=register_hosted_payload
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Hosted backend registered with local backend")
            print(f"  SBT ID: {result['sbt_id']}")
        else:
            print(f"✗ Registration failed: {response.status_code}")
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Registration failed: {e}")
        return False
    
    # Step 5: Verify both backends have each other registered
    print("\n[Step 5] Verifying peer registration...")
    
    local_peers = requests.get(f"{LOCAL_BACKEND}/peers").json()
    print(f"✓ Local backend has {len(local_peers['peers'])} peer(s) registered")
    for peer in local_peers['peers']:
        print(f"  - {peer['backend_id']}")
    
    hosted_peers = requests.get(f"{HOSTED_BACKEND}/peers").json()
    print(f"✓ Hosted backend has {len(hosted_peers['peers'])} peer(s) registered")
    for peer in hosted_peers['peers']:
        print(f"  - {peer['backend_id']}")
    
    # Verify mutual registration
    print("\n[Verification] Checking mutual registration...")
    
    local_has_hosted = any(
        p['backend_id'] == hosted_identity['backend_id'] 
        for p in local_peers['peers']
    )
    hosted_has_local = any(
        p['backend_id'] == local_identity['backend_id'] 
        for p in hosted_peers['peers']
    )
    
    if local_has_hosted and hosted_has_local:
        print("✓ SUCCESS: Both backends have each other registered!")
        print("\n" + "=" * 80)
        print("Backend Sync Protocol - Peer Registration: PASSED ✓")
        print("=" * 80)
        return True
    else:
        print("✗ FAILED: Mutual registration incomplete")
        if not local_has_hosted:
            print("  - Local backend does not have hosted backend registered")
        if not hosted_has_local:
            print("  - Hosted backend does not have local backend registered")
        return False


if __name__ == "__main__":
    success = test_peer_registration()
    exit(0 if success else 1)
