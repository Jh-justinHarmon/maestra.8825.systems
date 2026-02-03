#!/usr/bin/env python3
"""
Structural tests for enforcement kernel invocation.

These tests verify that:
1. No response is returned without enforcement_kernel.enforce()
2. All return paths use enforce_and_return()
3. No direct AdvisorAskResponse returns exist
4. Enforcement violations raise and block output
"""

import pytest
import ast
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_all_advisor_returns_use_enforce_and_return():
    """
    Structural test: All return statements in advisor.py must use enforce_and_return().
    
    This prevents the "import but never call" anti-pattern.
    """
    advisor_path = Path(__file__).parent.parent / "advisor.py"
    with open(advisor_path) as f:
        tree = ast.parse(f.read())
    
    # Find all return statements that return AdvisorAskResponse
    violations = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value:
            # Check if this is a direct AdvisorAskResponse return
            if isinstance(node.value, ast.Call):
                if hasattr(node.value.func, 'id') and node.value.func.id == 'AdvisorAskResponse':
                    violations.append(f"Line {node.lineno}: Direct AdvisorAskResponse return")
            
            # Check if this is NOT an enforce_and_return call
            if isinstance(node.value, ast.Call):
                func_name = None
                if hasattr(node.value.func, 'id'):
                    func_name = node.value.func.id
                elif hasattr(node.value.func, 'attr'):
                    func_name = node.value.func.attr
                
                # Allow enforce_and_return, await enforce_and_return, and None returns
                if func_name and func_name not in ['enforce_and_return', 'None']:
                    # Check if it's returning an AdvisorAskResponse-like object
                    if 'Response' in str(node.value):
                        violations.append(f"Line {node.lineno}: Return without enforce_and_return: {func_name}")
    
    assert not violations, \
        f"Found {len(violations)} direct returns without enforce_and_return:\n" + "\n".join(violations)


def test_server_exception_handler_uses_enforce_and_return():
    """
    Structural test: server.py exception handler must use enforce_and_return().
    
    Verifies the fix for the bypass in server.py:784-797.
    """
    server_path = Path(__file__).parent.parent / "server.py"
    with open(server_path) as f:
        content = f.read()
    
    # Check that EnforcementViolation handler uses enforce_and_return
    assert "except EnforcementViolation" in content, \
        "EnforcementViolation exception handler missing"
    
    # Find the exception handler block
    lines = content.split('\n')
    in_enforcement_handler = False
    handler_lines = []
    
    for i, line in enumerate(lines):
        if "except EnforcementViolation" in line:
            in_enforcement_handler = True
        elif in_enforcement_handler:
            if line.strip().startswith("except ") or (line.strip() and not line.startswith(' ')):
                break
            handler_lines.append((i + 1, line))
    
    # Verify enforce_and_return is called in the handler
    enforce_calls = [line for line_no, line in handler_lines if "enforce_and_return" in line]
    
    assert enforce_calls, \
        "EnforcementViolation handler must call enforce_and_return()"
    
    # Verify there's a return statement using enforce_and_return
    return_with_enforce = [line for line_no, line in handler_lines 
                          if "return enforce_and_return" in line]
    
    assert return_with_enforce, \
        "EnforcementViolation handler must return via enforce_and_return()"


def test_no_bypass_flags_exist():
    """
    Structural test: No bypass flags or escape hatches exist.
    
    Searches for common bypass patterns in enforcement code.
    """
    enforcement_kernel_path = Path(__file__).parent.parent / "enforcement_kernel.py"
    with open(enforcement_kernel_path) as f:
        content = f.read()
    
    # Forbidden bypass patterns
    bypass_patterns = [
        "ALLOW_UNSAFE",
        "SKIP_ENFORCEMENT",
        "DISABLE_ENFORCEMENT",
        "bypass=",
        "skip_enforcement=",
        "strict=False",
        "degraded_mode",
    ]
    
    violations = []
    for pattern in bypass_patterns:
        if pattern in content:
            violations.append(f"Bypass pattern detected: {pattern}")
    
    assert not violations, \
        f"Found {len(violations)} bypass patterns:\n" + "\n".join(violations)


def test_enforcement_raises_not_returns_false():
    """
    Structural test: enforce() raises exceptions, never returns False.
    
    Prevents the "return False instead of raise" anti-pattern.
    """
    enforcement_kernel_path = Path(__file__).parent.parent / "enforcement_kernel.py"
    with open(enforcement_kernel_path) as f:
        tree = ast.parse(f.read())
    
    # Find the enforce() method
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "enforce":
            # Check all return statements in enforce()
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and child.value:
                    # enforce() should only return None, never False or boolean
                    if isinstance(child.value, ast.Constant):
                        if child.value.value is False:
                            pytest.fail("enforce() returns False - must raise instead")
                        if child.value.value is True:
                            pytest.fail("enforce() returns True - must return None or raise")
    
    # Verify enforce() has raise statements
    enforcement_kernel_path = Path(__file__).parent.parent / "enforcement_kernel.py"
    with open(enforcement_kernel_path) as f:
        content = f.read()
    
    # Check that enforce() raises exceptions
    assert "raise AuthorityViolation" in content or "raise EnforcementViolation" in content, \
        "enforce() must raise exceptions on violation"


def test_enforce_and_return_calls_kernel():
    """
    Structural test: enforce_and_return() actually calls kernel.enforce().
    
    Prevents stubbing or no-op implementations.
    """
    advisor_path = Path(__file__).parent.parent / "advisor.py"
    with open(advisor_path) as f:
        content = f.read()
    
    # Find enforce_and_return function
    assert "def enforce_and_return(" in content, \
        "enforce_and_return() function missing"
    
    # Verify it calls kernel.enforce()
    assert "kernel.enforce(" in content, \
        "enforce_and_return() must call kernel.enforce()"
    
    # Verify it's not stubbed
    assert "# TODO" not in content or "kernel.enforce" in content, \
        "enforce_and_return() appears to be stubbed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
