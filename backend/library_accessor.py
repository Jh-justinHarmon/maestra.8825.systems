"""
Workspace-agnostic library access layer.

Implements dual-source-of-truth architecture:
- System Library: Canonical org-wide knowledge
- Context Index: Derived fast-lookup metadata
"""

import os
import json
import glob
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class LibraryEntry:
    """A single entry in the system library."""
    entry_id: str
    title: str
    content: str
    source: str  # "conversation", "capture", "manual"
    confidence: float
    timestamp: str
    tags: List[str]
    entry_type: str  # "decision", "pattern", "runbook", "narrative"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.entry_id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "entry_type": self.entry_type
        }


@dataclass
class ContextIndexEntry:
    """A single entry in the context index (derived metadata)."""
    query: str
    sources: List[Dict[str, Any]]  # Pointers to library entries
    confidence: float
    extracted_at: str
    valid_until: str
    is_derived: bool = True
    can_regenerate: bool = True
    
    def is_fresh(self) -> bool:
        """Check if entry is within validity window."""
        valid_until = datetime.fromisoformat(self.valid_until)
        return datetime.now() < valid_until
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "sources": self.sources,
            "confidence": self.confidence,
            "extracted_at": self.extracted_at,
            "valid_until": self.valid_until,
            "is_derived": self.is_derived,
            "can_regenerate": self.can_regenerate
        }


class LibraryAccessor:
    """Workspace-agnostic access to System Library."""
    
    def __init__(self, workspace_root: str):
        """
        Initialize library accessor.
        
        Args:
            workspace_root: Root directory of workspace (from find_workspace_root())
        """
        self.workspace_root = workspace_root
        self.library_path = os.path.join(workspace_root, "shared", "8825-library")
        self._verify_accessible()
    
    def _verify_accessible(self) -> None:
        """Verify library path exists and is readable."""
        if not os.path.exists(self.library_path):
            raise RuntimeError(f"System library not found at {self.library_path}")
        
        if not os.access(self.library_path, os.R_OK):
            raise RuntimeError(f"System library not readable at {self.library_path}")
        
        logger.info(f"System library verified at {self.library_path}")
    
    def search(self, query: str, max_entries: int = 5) -> List[LibraryEntry]:
        """
        Search system library with keyword matching.
        
        Returns actual entries or empty list (never fake data).
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        relevant = []
        
        try:
            for entry_file in glob.glob(os.path.join(self.library_path, "*.json")):
                try:
                    with open(entry_file, 'r') as f:
                        data = json.load(f)
                    
                    # Extract searchable fields
                    title = data.get("title", "").lower()
                    content = data.get("content", "").lower()
                    tags = " ".join(data.get("tags", [])).lower()
                    
                    # Score by keyword matches
                    score = sum(1 for w in query_words if w in title or w in content or w in tags)
                    
                    if score > 0:
                        entry = LibraryEntry(
                            entry_id=data.get("id", os.path.basename(entry_file)),
                            title=data.get("title", ""),
                            content=data.get("content", ""),
                            source=data.get("source", "unknown"),
                            confidence=data.get("confidence", 0.7),
                            timestamp=data.get("timestamp", ""),
                            tags=data.get("tags", []),
                            entry_type=data.get("entry_type", "unknown")
                        )
                        relevant.append((entry, score, entry.confidence))
                
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {entry_file}: {e}")
                except Exception as e:
                    logger.error(f"Error reading {entry_file}: {e}")
            
            # Sort by score and confidence
            relevant.sort(key=lambda x: (x[1], x[2]), reverse=True)
            results = [entry for entry, _, _ in relevant[:max_entries]]
            
            logger.info(f"Library search found {len(results)} entries for: {query[:50]}")
            return results
        
        except Exception as e:
            logger.error(f"Library search error: {e}")
            return []
    
    def get_entry(self, entry_id: str) -> Optional[LibraryEntry]:
        """
        Get specific entry by ID.
        
        Returns entry or None (never fake data).
        """
        try:
            entry_file = os.path.join(self.library_path, f"{entry_id}.json")
            
            if not os.path.exists(entry_file):
                logger.warning(f"Entry not found: {entry_id}")
                return None
            
            with open(entry_file, 'r') as f:
                data = json.load(f)
            
            return LibraryEntry(
                entry_id=data.get("id", entry_id),
                title=data.get("title", ""),
                content=data.get("content", ""),
                source=data.get("source", "unknown"),
                confidence=data.get("confidence", 0.7),
                timestamp=data.get("timestamp", ""),
                tags=data.get("tags", []),
                entry_type=data.get("entry_type", "unknown")
            )
        
        except Exception as e:
            logger.error(f"Error retrieving entry {entry_id}: {e}")
            return None
    
    def verify_integrity(self) -> tuple[bool, List[str]]:
        """
        Verify library files are valid JSON.
        
        Returns: (all_valid, list_of_corrupted_files)
        """
        corrupted = []
        
        try:
            for entry_file in glob.glob(os.path.join(self.library_path, "*.json")):
                try:
                    with open(entry_file, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    corrupted.append(entry_file)
                except Exception as e:
                    corrupted.append(f"{entry_file} ({str(e)})")
        
        except Exception as e:
            logger.error(f"Integrity check error: {e}")
            return False, [str(e)]
        
        if corrupted:
            logger.warning(f"Found {len(corrupted)} corrupted library files")
        
        return len(corrupted) == 0, corrupted
    
    def get_entry_count(self) -> int:
        """Get total number of entries in library."""
        try:
            return len(glob.glob(os.path.join(self.library_path, "*.json")))
        except Exception as e:
            logger.error(f"Error counting entries: {e}")
            return 0


class ContextIndexAccessor:
    """Fast lookup via UCMA context index (derived metadata)."""
    
    def __init__(self, workspace_root: str):
        """
        Initialize context index accessor.
        
        Args:
            workspace_root: Root directory of workspace
        """
        self.workspace_root = workspace_root
        self.index_path = os.path.join(workspace_root, "ucma", "extracted_knowledge")
        self._ensure_exists()
    
    def _ensure_exists(self) -> None:
        """Ensure index directory exists."""
        if not os.path.exists(self.index_path):
            logger.warning(f"Context index not found at {self.index_path}, will regenerate on demand")
            return
        
        if not os.access(self.index_path, os.R_OK):
            logger.warning(f"Context index not readable at {self.index_path}")
    
    def search(self, query: str) -> List[ContextIndexEntry]:
        """
        Fast lookup in context index.
        
        Returns pointers to system library entries.
        """
        if not os.path.exists(self.index_path):
            logger.debug("Context index not available, returning empty")
            return []
        
        query_lower = query.lower()
        results = []
        
        try:
            for index_file in glob.glob(os.path.join(self.index_path, "*.json")):
                try:
                    with open(index_file, 'r') as f:
                        data = json.load(f)
                    
                    # Check if query matches
                    indexed_query = data.get("query", "").lower()
                    if query_lower in indexed_query or indexed_query in query_lower:
                        entry = ContextIndexEntry(
                            query=data.get("query", ""),
                            sources=data.get("sources", []),
                            confidence=data.get("confidence", 0.5),
                            extracted_at=data.get("extracted_at", ""),
                            valid_until=data.get("valid_until", ""),
                            is_derived=data.get("is_derived", True),
                            can_regenerate=data.get("can_regenerate", True)
                        )
                        
                        # Only return if fresh
                        if entry.is_fresh():
                            results.append(entry)
                        else:
                            logger.debug(f"Skipping stale index entry: {indexed_query}")
                
                except Exception as e:
                    logger.error(f"Error reading index file {index_file}: {e}")
        
        except Exception as e:
            logger.error(f"Context index search error: {e}")
        
        return results
    
    def mark_stale(self, query: str) -> None:
        """Mark index entries matching query as stale for regeneration."""
        if not os.path.exists(self.index_path):
            return
        
        query_lower = query.lower()
        
        try:
            for index_file in glob.glob(os.path.join(self.index_path, "*.json")):
                try:
                    with open(index_file, 'r') as f:
                        data = json.load(f)
                    
                    indexed_query = data.get("query", "").lower()
                    if query_lower in indexed_query or indexed_query in query_lower:
                        # Mark as stale by setting valid_until to past
                        data["valid_until"] = datetime.now().isoformat()
                        
                        with open(index_file, 'w') as f:
                            json.dump(data, f, indent=2)
                        
                        logger.info(f"Marked stale: {indexed_query}")
                
                except Exception as e:
                    logger.error(f"Error updating index file {index_file}: {e}")
        
        except Exception as e:
            logger.error(f"Error marking stale: {e}")


def find_workspace_root() -> str:
    """
    Find workspace root directory.
    
    Looks for 8825-Team directory or uses environment variable.
    """
    # Check environment variable first
    if "WORKSPACE_ROOT" in os.environ:
        return os.environ["WORKSPACE_ROOT"]
    
    # Look for 8825-Team in current path
    current = os.getcwd()
    while current != os.path.dirname(current):  # Until we reach root
        if os.path.basename(current) == "8825-Team":
            return current
        current = os.path.dirname(current)
    
    # Fallback to home directory + known path
    home = os.path.expanduser("~")
    default_path = os.path.join(
        home,
        "Hammer Consulting Dropbox",
        "Justin Harmon",
        "8825-Team"
    )
    
    if os.path.exists(default_path):
        return default_path
    
    raise RuntimeError("Cannot find workspace root. Set WORKSPACE_ROOT environment variable.")
