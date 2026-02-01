"""
LocalSentinelAdapter — Session-Scoped Intelligence from Sentinel

TRACK 5B.1 Implementation

Hard Constraints:
- ❌ No persistence (disk, DB, cache)
- ❌ No cross-session memory
- ❌ No fallback if Sentinel fails
- ❌ No authority inference inside adapter

Must Do:
- Accept (query, session_id)
- Query local Sentinel MCP
- Return ContextSource(type="tool:sentinel")
- Populate: excerpt, confidence, artifact reference

If Sentinel unavailable:
- Raise SentinelUnavailable
- Let Enforcement Kernel decide refusal

Do NOT:
- Modify responses
- Decide authority
- Catch enforcement errors
"""

import os
import json
import logging
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path

from enforcement_kernel import ContextSource

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────

class SentinelUnavailable(Exception):
    """Sentinel MCP is not available or failed to respond."""
    pass


class SentinelQueryFailed(Exception):
    """Sentinel query executed but returned an error."""
    pass


# ─────────────────────────────────────────────
# Sentinel Result Model
# ─────────────────────────────────────────────

@dataclass
class SentinelResult:
    """
    Result from a Sentinel query.
    
    This is a pure data container - no authority inference.
    """
    artifact_id: str
    title: str
    excerpt: str
    confidence: float
    source_path: Optional[str] = None
    artifact_type: Optional[str] = None
    
    def to_context_source(self) -> ContextSource:
        """
        Convert to ContextSource for enforcement.
        
        Always returns type="tool:sentinel" - authority derivation
        happens in the enforcement kernel, not here.
        """
        return ContextSource(
            source="tool:sentinel",
            identifier=self.artifact_id
        )


# ─────────────────────────────────────────────
# LocalSentinelAdapter
# ─────────────────────────────────────────────

class LocalSentinelAdapter:
    """
    Session-scoped adapter for local Sentinel MCP.
    
    This adapter:
    - Queries local Sentinel for relevant artifacts
    - Returns ContextSource objects for enforcement
    - Raises SentinelUnavailable if Sentinel is not reachable
    - Does NOT persist anything
    - Does NOT infer authority
    - Does NOT catch enforcement errors
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        """
        Initialize the adapter.
        
        Args:
            workspace_root: Path to workspace root (for finding Sentinel MCP)
        """
        self.workspace_root = workspace_root or self._find_workspace_root()
        self.sentinel_mcp_path = self._find_sentinel_mcp()
        
    def _find_workspace_root(self) -> Optional[str]:
        """Find the workspace root directory."""
        # Try environment variable first
        if os.getenv("WORKSPACE_ROOT"):
            return os.getenv("WORKSPACE_ROOT")
        
        # Try common locations
        candidates = [
            Path.home() / "Hammer Consulting Dropbox" / "Justin Harmon" / "8825-Team" / "8825",
            Path.home() / "8825-Team" / "8825",
            Path("/app"),  # Fly.io
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        
        return None
    
    def _find_sentinel_mcp(self) -> Optional[str]:
        """Find the Sentinel MCP server path."""
        if not self.workspace_root:
            return None
            
        sentinel_paths = [
            Path(self.workspace_root) / "mcp-servers" / "sentinel-mcp" / "server.js",
            Path(self.workspace_root) / "mcp" / "sentinel-mcp" / "server.js",
        ]
        
        for path in sentinel_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def is_available(self) -> bool:
        """
        Check if Sentinel is available locally.
        
        Returns:
            True if Sentinel MCP is reachable
        """
        if not self.sentinel_mcp_path:
            return False
        
        try:
            # Quick health check
            result = subprocess.run(
                ["node", self.sentinel_mcp_path, "--health"],
                capture_output=True,
                timeout=2,
                cwd=self.workspace_root
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def query(
        self,
        query: str,
        session_id: str,
        max_results: int = 5
    ) -> Tuple[List[SentinelResult], List[str]]:
        """
        Query Sentinel for relevant artifacts.
        
        Args:
            query: The search query
            session_id: Session ID (for logging, not persistence)
            max_results: Maximum number of results to return
        
        Returns:
            Tuple of (results, required_but_missing)
            - results: List of SentinelResult objects
            - required_but_missing: List of required sources that weren't found
        
        Raises:
            SentinelUnavailable: If Sentinel is not reachable
            SentinelQueryFailed: If query execution failed
        """
        if not self.sentinel_mcp_path:
            logger.warning(f"Sentinel MCP not found, session={session_id}")
            raise SentinelUnavailable("Sentinel MCP path not configured")
        
        if not self.workspace_root:
            logger.warning(f"Workspace root not found, session={session_id}")
            raise SentinelUnavailable("Workspace root not configured")
        
        logger.info(f"Querying Sentinel: query='{query[:50]}...', session={session_id}")
        
        try:
            # Call Sentinel MCP via subprocess
            # This is a simplified implementation - in production would use proper MCP protocol
            result = subprocess.run(
                [
                    "node", self.sentinel_mcp_path,
                    "--query", query,
                    "--max-results", str(max_results),
                    "--format", "json"
                ],
                capture_output=True,
                timeout=10,
                cwd=self.workspace_root,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Sentinel query failed: {result.stderr}")
                raise SentinelQueryFailed(f"Sentinel returned error: {result.stderr}")
            
            # Parse results
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Sentinel response: {result.stdout[:200]}")
                raise SentinelQueryFailed("Invalid JSON response from Sentinel")
            
            results = []
            for item in data.get("results", []):
                results.append(SentinelResult(
                    artifact_id=item.get("id", "unknown"),
                    title=item.get("title", "Untitled"),
                    excerpt=item.get("excerpt", "")[:500],
                    confidence=float(item.get("confidence", 0.5)),
                    source_path=item.get("path"),
                    artifact_type=item.get("type")
                ))
            
            # Determine if any required sources are missing
            required_but_missing = []
            if not results and self._query_requires_sentinel(query):
                required_but_missing.append("sentinel")
            
            logger.info(f"Sentinel returned {len(results)} results, session={session_id}")
            return results, required_but_missing
            
        except subprocess.TimeoutExpired:
            logger.error(f"Sentinel query timed out, session={session_id}")
            raise SentinelUnavailable("Sentinel query timed out")
        except FileNotFoundError:
            logger.error(f"Node.js not found, session={session_id}")
            raise SentinelUnavailable("Node.js not available")
        except Exception as e:
            logger.error(f"Sentinel query error: {e}, session={session_id}")
            raise SentinelUnavailable(f"Sentinel error: {e}")
    
    def _query_requires_sentinel(self, query: str) -> bool:
        """
        Determine if a query requires Sentinel results.
        
        This is a simple heuristic - queries about internal systems,
        architecture, or specific projects likely need Sentinel.
        """
        sentinel_keywords = [
            "hcss", "8825", "architecture", "internal",
            "system", "project", "implementation", "code",
            "how does", "how do we", "what is our",
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in sentinel_keywords)
    
    def get_context_sources(
        self,
        query: str,
        session_id: str,
        max_results: int = 5
    ) -> Tuple[List[ContextSource], List[str], List[SentinelResult]]:
        """
        Get ContextSource objects for enforcement.
        
        This is the main entry point for the advisor.
        
        Args:
            query: The search query
            session_id: Session ID
            max_results: Maximum results
        
        Returns:
            Tuple of (context_sources, required_but_missing, raw_results)
            - context_sources: List of ContextSource for enforcement
            - required_but_missing: List of required sources not found
            - raw_results: Original SentinelResult objects for excerpts
        
        Raises:
            SentinelUnavailable: If Sentinel is not reachable
        """
        results, required_but_missing = self.query(query, session_id, max_results)
        
        context_sources = [r.to_context_source() for r in results]
        
        return context_sources, required_but_missing, results


# ─────────────────────────────────────────────
# Singleton Instance
# ─────────────────────────────────────────────

_sentinel_adapter: Optional[LocalSentinelAdapter] = None


def get_sentinel_adapter() -> LocalSentinelAdapter:
    """Get the singleton Sentinel adapter instance."""
    global _sentinel_adapter
    if _sentinel_adapter is None:
        _sentinel_adapter = LocalSentinelAdapter()
    return _sentinel_adapter
