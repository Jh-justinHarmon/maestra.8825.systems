"""
Backend execution audit trail - tracks sources, operations, and results
"""

from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import threading


@dataclass
class AuditEntry:
    """Single audit trail entry"""
    timestamp: str
    entry_type: str  # 'source', 'operation', 'context', 'result', 'error'
    label: str
    details: Optional[dict] = None
    duration_ms: Optional[float] = None


@dataclass
class ExecutionRecord:
    """Complete execution record with all audit entries"""
    execution_id: str
    source: str
    endpoint: str
    start_time: str
    entries: list[AuditEntry]
    end_time: Optional[str] = None
    total_duration_ms: Optional[float] = None
    status: str = 'in_progress'  # 'in_progress', 'success', 'error'


class AuditTrail:
    """Thread-safe audit trail for backend execution tracking"""

    def __init__(self, log_dir: str = '/tmp/maestra_audit'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_execution: Optional[ExecutionRecord] = None
        self.history: list[ExecutionRecord] = []
        self.lock = threading.Lock()

    def start_execution(self, execution_id: str, source: str, endpoint: str):
        """Start a new execution record"""
        with self.lock:
            self.current_execution = ExecutionRecord(
                execution_id=execution_id,
                source=source,
                endpoint=endpoint,
                start_time=datetime.utcnow().isoformat(),
                entries=[],
            )

    def add_entry(
        self,
        entry_type: str,
        label: str,
        details: Optional[dict] = None,
        duration_ms: Optional[float] = None,
    ):
        """Add an entry to current execution"""
        if not self.current_execution:
            return

        with self.lock:
            entry = AuditEntry(
                timestamp=datetime.utcnow().isoformat(),
                entry_type=entry_type,
                label=label,
                details=details,
                duration_ms=duration_ms,
            )
            self.current_execution.entries.append(entry)

    def add_source(self, source: str, details: Optional[dict] = None):
        """Log source information"""
        self.add_entry('source', source, details)

    def add_operation(self, operation: str, details: Optional[dict] = None, duration_ms: Optional[float] = None):
        """Log an operation (e.g., 'advisor.ask', 'context.fetch')"""
        self.add_entry('operation', operation, details, duration_ms)

    def add_context(self, context_type: str, details: Optional[dict] = None):
        """Log context information"""
        self.add_entry('context', context_type, details)

    def add_result(self, result_label: str, details: Optional[dict] = None, duration_ms: Optional[float] = None):
        """Log result information"""
        self.add_entry('result', result_label, details, duration_ms)

    def add_error(self, error_label: str, details: Optional[dict] = None):
        """Log error information"""
        self.add_entry('error', error_label, details)

    def end_execution(self, status: str = 'success'):
        """End current execution and persist to disk"""
        if not self.current_execution:
            return

        with self.lock:
            end_time = datetime.utcnow().isoformat()
            start_ms = datetime.fromisoformat(self.current_execution.start_time).timestamp() * 1000
            end_ms = datetime.fromisoformat(end_time).timestamp() * 1000

            self.current_execution.end_time = end_time
            self.current_execution.total_duration_ms = end_ms - start_ms
            self.current_execution.status = status

            self.history.append(self.current_execution)
            self._persist_execution(self.current_execution)
            self.current_execution = None

    def _persist_execution(self, execution: ExecutionRecord):
        """Write execution record to disk"""
        try:
            log_file = self.log_dir / f"{execution.execution_id}.json"
            with open(log_file, 'w') as f:
                json.dump(asdict(execution), f, indent=2)
        except Exception as e:
            print(f"Failed to persist audit trail: {e}")

    def get_recent(self, limit: int = 10) -> list[ExecutionRecord]:
        """Get recent execution records"""
        with self.lock:
            return self.history[-limit:]

    def export_json(self) -> str:
        """Export recent history as JSON"""
        with self.lock:
            return json.dumps(
                [asdict(ex) for ex in self.history[-20:]],
                indent=2,
                default=str,
            )

    def clear(self):
        """Clear in-memory history"""
        with self.lock:
            self.history = []
            self.current_execution = None


# Global singleton
audit_trail = AuditTrail()
