"""
Stub agent registry for MAESTRA_MINIMAL_MODE.

Provides minimal agent info without requiring full system/agents/ infrastructure.
"""
from typing import Optional, Dict, Any


class StubAgent:
    """Minimal agent representation."""
    def __init__(self, agent_id: str, display_name: str):
        self.agent_id = agent_id
        self.display_name = display_name


def get_agent(agent_id: str) -> Optional[StubAgent]:
    """
    Return stub agent info.
    
    In minimal mode, we only need basic agent identity for response attribution.
    """
    agents = {
        "analyst": StubAgent("analyst", "Analyst"),
        "researcher": StubAgent("researcher", "Researcher"),
        "advisor": StubAgent("advisor", "Advisor"),
    }
    return agents.get(agent_id)
