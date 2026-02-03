"""
One-bit behavior guards for historical failures (PROMPT 8)

These tests encode non-negotiable invariants:
- Single-word input must NOT trigger conversation lookup
- conversation_id must remain null unless explicit "load <id>"
- Shadow backends must never respond to requests
"""

import pytest
import requests
import re


BACKEND_URL = "http://localhost:8825"


def test_single_word_input_not_conversation_lookup():
    """Single-word questions must NOT be treated as conversation IDs"""
    test_cases = [
        "bruh",
        "hello",
        "test",
        "what",
        "why",
    ]
    
    for question in test_cases:
        response = requests.post(
            f"{BACKEND_URL}/api/maestra/advisor/ask",
            json={"session_id": "test", "question": question, "mode": "quick"}
        )
        
        assert response.status_code == 200, \
            f"Request failed for question '{question}': {response.status_code}"
        
        data = response.json()
        
        # Must NOT return conversation lookup error
        assert "Conversation" not in data.get("answer", ""), \
            f"Single-word input '{question}' triggered conversation lookup"
        
        assert "not found" not in data.get("answer", "").lower(), \
            f"Single-word input '{question}' triggered 'not found' error"
        
        # conversation_id must be null
        assert data.get("conversation_id") is None, \
            f"Single-word input '{question}' set conversation_id to {data.get('conversation_id')}"


def test_conversation_id_null_unless_explicit_load():
    """conversation_id must remain null unless explicit 'load <id>' command"""
    normal_questions = [
        "what is 8825",
        "how do I use this",
        "explain the system",
    ]
    
    for question in normal_questions:
        response = requests.post(
            f"{BACKEND_URL}/api/maestra/advisor/ask",
            json={"session_id": "test", "question": question, "mode": "quick"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # conversation_id must be null for normal questions
        assert data.get("conversation_id") is None, \
            f"Normal question '{question}' set conversation_id to {data.get('conversation_id')}"


def test_explicit_load_command_triggers_lookup():
    """Explicit 'load <id>' commands should trigger conversation lookup"""
    response = requests.post(
        f"{BACKEND_URL}/api/maestra/advisor/ask",
        json={"session_id": "test", "question": "load test123", "mode": "quick"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should attempt conversation lookup
    # conversation_id should be set (even if conversation doesn't exist)
    assert data.get("conversation_id") is not None or "not found" in data.get("answer", "").lower(), \
        "Explicit 'load' command did not trigger conversation lookup"


def test_regex_requires_load_keyword():
    """Backend regex must require 'load' keyword"""
    # This is a code-level test - verify the regex in advisor.py
    import sys
    from pathlib import Path
    
    canonical_backend = Path("/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/apps/maestra.8825.systems/backend")
    advisor_file = canonical_backend / "advisor.py"
    
    assert advisor_file.exists(), "advisor.py not found at canonical location"
    
    content = advisor_file.read_text()
    
    # Find the regex pattern
    # Should be: r'^load\s+([a-zA-Z0-9_-]+)$'
    # Should NOT be: r'^(?:load\s+)?([a-zA-Z0-9_-]+)$'
    
    # Check that the BAD regex is NOT present
    bad_regex = r"r'\^(?:load\\s\+)?\("
    assert bad_regex not in content, \
        "FATAL: advisor.py contains the bad regex with optional 'load' keyword"
    
    # Check that the GOOD regex IS present
    good_regex = r"r'\^load\\s\+\("
    assert good_regex in content, \
        "FATAL: advisor.py missing the correct regex requiring 'load' keyword"


def test_health_endpoint_proves_canonical_backend():
    """Health endpoint must prove this is the canonical backend"""
    response = requests.get(f"{BACKEND_URL}/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Must include runtime identity
    assert data.get("canonical_backend") is True, \
        "Health endpoint does not confirm canonical backend"
    
    assert "server_path" in data, \
        "Health endpoint missing server_path"
    
    assert "advisor_path" in data, \
        "Health endpoint missing advisor_path"
    
    # Verify paths are canonical
    canonical_backend = "/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/apps/maestra.8825.systems/backend"
    
    assert data["server_path"].startswith(canonical_backend), \
        f"server_path is not canonical: {data['server_path']}"
    
    assert data["advisor_path"].startswith(canonical_backend), \
        f"advisor_path is not canonical: {data['advisor_path']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
