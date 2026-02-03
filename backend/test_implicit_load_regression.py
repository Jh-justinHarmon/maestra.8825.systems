"""
PROMPT H: Regression test that would have prevented the implicit load bug.

This test ensures that simple inputs like "hello" do not trigger conversation loading.
"""
import pytest
import requests
import json


def test_simple_input_does_not_trigger_conversation_load():
    """
    Test that simple inputs like "hello" return normal responses,
    not "Conversation 'hello' not found" errors.
    
    This test would have caught the implicit load bug.
    """
    # Test against local backend
    response = requests.post(
        "http://localhost:8825/api/maestra/advisor/ask",
        json={
            "session_id": "test_session",
            "question": "hello",
            "mode": "quick"
        },
        timeout=5
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # CRITICAL ASSERTIONS
    assert data["conversation_id"] is None, \
        "Simple input should not create/load a conversation"
    
    assert "Conversation" not in data["answer"], \
        f"Response should not mention 'Conversation'. Got: {data['answer'][:100]}"
    
    assert data["answer"] != "", \
        "Response should not be empty"
    
    print(f"✅ PASS: 'hello' returned normal answer: {data['answer'][:60]}...")


def test_explicit_load_still_works():
    """
    Test that explicit "load <id>" still works correctly.
    """
    response = requests.post(
        "http://localhost:8825/api/maestra/advisor/ask",
        json={
            "session_id": "test_session",
            "question": "load nonexistent_conversation",
            "mode": "quick"
        },
        timeout=5
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # This SHOULD mention conversation (because we explicitly asked to load)
    assert "Conversation" in data["answer"] or "not found" in data["answer"].lower(), \
        "Explicit load should trigger conversation lookup"
    
    print(f"✅ PASS: Explicit 'load' works correctly")


def test_various_simple_inputs():
    """
    Test multiple simple inputs to ensure none trigger implicit loading.
    """
    test_inputs = ["hi", "bruh", "test", "help", "status", "what"]
    
    for user_input in test_inputs:
        response = requests.post(
            "http://localhost:8825/api/maestra/advisor/ask",
            json={
                "session_id": "test_session",
                "question": user_input,
                "mode": "quick"
            },
            timeout=5
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["conversation_id"] is None, \
            f"Input '{user_input}' should not trigger conversation load"
        
        assert "Conversation '" not in data["answer"], \
            f"Input '{user_input}' triggered implicit load. Response: {data['answer'][:100]}"
        
        print(f"✅ PASS: '{user_input}' returned normal answer")


if __name__ == "__main__":
    print("Running implicit load regression tests...")
    print("=" * 60)
    
    try:
        test_simple_input_does_not_trigger_conversation_load()
        test_explicit_load_still_works()
        test_various_simple_inputs()
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
    except AssertionError as e:
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        exit(1)
