"""
Enforcement Kernel v0.1 (LOCKED)

Speech firewall. Non-bypassable.

This module answers ONE question only:
"Is Maestra allowed to speak this response truthfully?"

MUST:
- Be invoked exactly once per response
- Run immediately before response return
- Raise on violation (never return False)
- Be non-bypassable (no flags, no degraded modes)

MUST NOT:
- Choose tools
- Route queries
- Assemble context
- Evaluate answer quality
- Retry or fallback
- Log-and-continue
- Support escape hatches

All violations result in REFUSAL.
"""

from dataclasses import dataclass
from typing import List, Literal, Optional


# ─────────────────────────────────────────────
# Context Model (Descriptive, Immutable)
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class ContextSource:
    """Immutable record of a context source used in response generation."""
    source: Literal[
        "system",
        "library",
        "memory",
        "tool:sentinel",
        "tool:deep_research",
        "tool:external",
    ]
    identifier: Optional[str] = None


@dataclass(frozen=True)
class ContextTrace:
    """
    Immutable trace of context used to generate a response.
    
    This is the input to enforcement - it describes what context
    was available and used, not what should have been.
    """
    sources: List[ContextSource]
    required_but_missing: List[str]
    system_mode: Literal["full", "minimal", "local_power"]

    def derive_required_authority(self) -> Literal["system", "memory", "tool"]:
        """
        Derive the required authority based on context sources.
        
        Rules (order matters - first match wins):
        1. Any tool:* source → authority="tool"
        2. Any library or memory source → authority="memory"
        3. Otherwise → authority="system"
        """
        for s in self.sources:
            if s.source.startswith("tool:"):
                return "tool"
        for s in self.sources:
            if s.source in ("library", "memory"):
                return "memory"
        return "system"


# ─────────────────────────────────────────────
# Violations (Blocking by Design)
# ─────────────────────────────────────────────

class EnforcementViolation(Exception):
    """Base class for all enforcement violations. Always blocking."""
    pass


class AuthorityViolation(EnforcementViolation):
    """Response claims authority it does not have."""
    pass


class ContextUnavailable(EnforcementViolation):
    """Required context was not available."""
    pass


class ModeViolation(EnforcementViolation):
    """Response claims wrong system mode."""
    pass


class RefusalAuthorityViolation(EnforcementViolation):
    """Refusal response claims authority other than 'none'."""
    pass


# ─────────────────────────────────────────────
# Enforcement Kernel (Speech Firewall)
# ─────────────────────────────────────────────

class EnforcementKernel:
    """
    Speech firewall. Non-bypassable.
    
    This class has exactly one public method: enforce()
    It raises on violation, never returns False.
    There are no config flags, no bypasses, no degraded modes.
    """

    def enforce(self, response, context: ContextTrace) -> None:
        """
        Enforce speech rules on a response.
        
        Args:
            response: The response object (must have authority, system_mode, epistemic_state)
            context: The context trace describing what was available
        
        Returns:
            None on success
        
        Raises:
            AuthorityViolation: If claimed authority doesn't match derived authority
            ContextUnavailable: If required context was missing
            ModeViolation: If claimed mode doesn't match actual mode
            RefusalAuthorityViolation: If refusal claims authority other than 'none'
        """
        # Rule 1 — Authority consistency
        # Response must claim the authority that matches its context sources
        expected_authority = context.derive_required_authority()
        
        # Special case: refusals always require authority="none"
        if response.epistemic_state == "REFUSED":
            if response.authority != "none":
                raise RefusalAuthorityViolation(
                    f"Refusals must claim authority='none', got authority='{response.authority}'"
                )
            # Refusals pass remaining checks - they're honest about having nothing
            return None
        
        if response.authority != expected_authority:
            raise AuthorityViolation(
                f"Claimed authority='{response.authority}', required='{expected_authority}' "
                f"based on sources: {[s.source for s in context.sources]}"
            )

        # Rule 2 — Required context availability
        # If context was required but missing, speech is not allowed
        if context.required_but_missing:
            raise ContextUnavailable(
                f"Missing required context: {context.required_but_missing}. "
                "Response cannot be emitted without this context."
            )

        # Rule 3 — Mode honesty
        # Response must accurately report the system mode
        if response.system_mode != context.system_mode:
            raise ModeViolation(
                f"Claimed mode='{response.system_mode}', actual='{context.system_mode}'"
            )

        # All rules passed - speech is allowed
        return None


# ─────────────────────────────────────────────
# Singleton Instance
# ─────────────────────────────────────────────

_enforcement_kernel: Optional[EnforcementKernel] = None


def get_enforcement_kernel() -> EnforcementKernel:
    """Get the singleton enforcement kernel instance."""
    global _enforcement_kernel
    if _enforcement_kernel is None:
        _enforcement_kernel = EnforcementKernel()
    return _enforcement_kernel
