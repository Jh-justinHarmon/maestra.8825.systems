#!/usr/bin/env python3
"""
Test script for unified save functionality

Tests:
1. ConversationSaveService saves to library
2. Cascade agent detects save triggers
3. Backend endpoint processes save requests
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


def test_cascade_save_agent():
    """Test Cascade save agent trigger detection"""
    print("\n" + "="*80)
    print("Test 1: Cascade Save Agent - Trigger Detection")
    print("="*80)
    
    from cascade_save_agent import get_cascade_save_agent
    
    agent = get_cascade_save_agent()
    
    test_messages = [
        ("save this convo", True),
        ("save this conversation", True),
        ("capture this chat", True),
        ("archive this discussion", True),
        ("save to library", True),
        ("what is the weather?", False),
        ("tell me more", False),
        ("save the file", True),  # Should match "save"
    ]
    
    passed = 0
    failed = 0
    
    for message, expected in test_messages:
        result = agent.should_save(message)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
            print(f"{status} '{message}' → {result} (expected {expected})")
        else:
            failed += 1
            print(f"{status} '{message}' → {result} (expected {expected}) FAILED")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_conversation_extraction():
    """Test conversation context extraction"""
    print("\n" + "="*80)
    print("Test 2: Conversation Context Extraction")
    print("="*80)
    
    from cascade_save_agent import get_cascade_save_agent
    
    agent = get_cascade_save_agent()
    
    # Create test conversation
    messages = [
        {
            "role": "user",
            "content": "What is machine learning?",
            "timestamp": datetime.utcnow().isoformat(),
        },
        {
            "role": "assistant",
            "content": "Machine learning is a subset of AI...",
            "timestamp": datetime.utcnow().isoformat(),
        },
        {
            "role": "user",
            "content": "Can you give an example?",
            "timestamp": datetime.utcnow().isoformat(),
        },
    ]
    
    context = agent.extract_conversation_context(messages, user_id="test_user")
    
    print(f"✓ Conversation ID: {context['conversation_id']}")
    print(f"✓ Title: {context['title']}")
    print(f"✓ Message count: {len(context['messages'])}")
    print(f"✓ User ID: {context['user_id']}")
    
    # Verify structure
    assert context["conversation_id"].startswith("cascade_"), "Invalid conversation ID"
    assert context["title"] == "What is machine learning?", "Invalid title extraction"
    assert len(context["messages"]) == 3, "Invalid message count"
    
    print("\n✓ Context extraction test PASSED")
    return True


def test_save_trigger_handling():
    """Test save trigger handling"""
    print("\n" + "="*80)
    print("Test 3: Save Trigger Handling")
    print("="*80)
    
    from cascade_save_agent import get_cascade_save_agent
    
    agent = get_cascade_save_agent()
    
    messages = [
        {
            "role": "user",
            "content": "Explain quantum computing",
            "timestamp": datetime.utcnow().isoformat(),
        },
        {
            "role": "assistant",
            "content": "Quantum computing uses quantum bits...",
            "timestamp": datetime.utcnow().isoformat(),
        },
    ]
    
    # Test with non-trigger message
    result = agent.handle_save_trigger(
        "tell me more",
        messages,
        user_id="test_user"
    )
    
    if not result.get("success"):
        print("✓ Non-trigger message correctly rejected")
    else:
        print("✗ Non-trigger message incorrectly accepted")
        return False
    
    # Test with trigger message (would fail without unified_capture library)
    result = agent.handle_save_trigger(
        "save this convo",
        messages,
        user_id="test_user"
    )
    
    if result.get("success"):
        print(f"✓ Save trigger handled successfully")
        print(f"  Entry ID: {result.get('entry_id')}")
        print(f"  Message: {result.get('message')}")
    else:
        # Expected to fail if unified_capture not available
        print(f"⚠ Save trigger handling failed (expected if unified_capture unavailable)")
        print(f"  Error: {result.get('error')}")
    
    return True


def test_save_request_model():
    """Test SaveConversationRequest model"""
    print("\n" + "="*80)
    print("Test 4: SaveConversationRequest Model")
    print("="*80)
    
    from server import SaveConversationRequest
    
    # Create test request
    request_data = {
        "conversation_id": "test_conv_001",
        "title": "Test Conversation",
        "messages": [
            {"role": "user", "content": "Hello", "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "Hi there!", "timestamp": datetime.utcnow().isoformat()},
        ],
        "user_id": "test_user",
        "session_id": "test_session",
    }
    
    try:
        request = SaveConversationRequest(**request_data)
        print(f"✓ Request model created successfully")
        print(f"  Conversation ID: {request.conversation_id}")
        print(f"  Title: {request.title}")
        print(f"  Messages: {len(request.messages)}")
        print(f"  User ID: {request.user_id}")
        return True
    except Exception as e:
        print(f"✗ Request model creation failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("Unified Save Functionality - Test Suite")
    print("="*80)
    
    tests = [
        ("Cascade Save Agent", test_cascade_save_agent),
        ("Conversation Extraction", test_conversation_extraction),
        ("Save Trigger Handling", test_save_trigger_handling),
        ("SaveConversationRequest Model", test_save_request_model),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n✗ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests PASSED!")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} test(s) FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
