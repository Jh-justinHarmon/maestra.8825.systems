import React, { useState, useEffect } from 'react';
import { Download, Search, AlertCircle, CheckCircle, Clock } from 'lucide-react';

export interface AuditLogEntry {
  receipt_id: string;
  token_id: string;
  session_id: string;
  capability_id: string;
  executed_at: string;
  executed_by: string;
  status: string;
  input_hash: string;
  output_hash: string;
  bytes_returned: number;
  error_message?: string;
  drift_detected: boolean;
  drift_reason?: string;
}

export interface AuditLogViewerProps {
  sessionId: string;
  isOpen: boolean;
  onClose?: () => void;
}

export const AuditLogViewer: React.FC<AuditLogViewerProps> = ({
  sessionId,
  isOpen,
  onClose,
}) => {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [filteredEntries, setFilteredEntries] = useState<AuditLogEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const fetchAuditLog = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(
          `/api/maestra/session/${sessionId}/audit`
        );
        if (response.ok) {
          const data = await response.json();
          setEntries(data.executions || []);
        }
      } catch (error) {
        console.error('Failed to fetch audit log:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAuditLog();
  }, [isOpen, sessionId]);

  useEffect(() => {
    let filtered = entries;

    if (statusFilter !== 'all') {
      filtered = filtered.filter((e) => e.status === statusFilter);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (e) =>
          e.capability_id.toLowerCase().includes(query) ||
          e.receipt_id.toLowerCase().includes(query) ||
          e.executed_by.toLowerCase().includes(query)
      );
    }

    setFilteredEntries(filtered);
  }, [entries, statusFilter, searchQuery]);

  const handleExport = () => {
    const csv = [
      ['Receipt ID', 'Capability', 'Status', 'Executed At', 'Bytes', 'Drift'],
      ...filteredEntries.map((e) => [
        e.receipt_id,
        e.capability_id,
        e.status,
        e.executed_at,
        e.bytes_returned,
        e.drift_detected ? 'Yes' : 'No',
      ]),
    ]
      .map((row) => row.join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${sessionId}.csv`;
    a.click();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">
            Audit Log: What Left Your Device
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>

        <div className="p-6 border-b border-gray-200 space-y-4">
          <p className="text-sm text-gray-600">
            This audit log shows all data that was accessed or exported from your device during this session. Each entry includes what data was accessed, when, and by which capability.
          </p>

          <div className="flex gap-4 flex-wrap">
            <div className="flex-1 min-w-64">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by capability, receipt ID, or executor..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
              <option value="policy_violation">Policy Violation</option>
            </select>

            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <p className="text-gray-500">Loading audit log...</p>
            </div>
          ) : filteredEntries.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <p className="text-gray-500">No entries found</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredEntries.map((entry) => (
                <div key={entry.receipt_id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3 flex-1">
                      {entry.status === 'success' ? (
                        <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                      ) : (
                        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
                      )}

                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-gray-900">
                          {entry.capability_id}
                        </p>
                        <p className="text-sm text-gray-600">
                          Executed by: {entry.executed_by}
                        </p>
                      </div>
                    </div>

                    <div className="text-right ml-4">
                      <span
                        className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                          entry.status === 'success'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {entry.status}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 ml-8">
                    <div className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      <span>{new Date(entry.executed_at).toLocaleString()}</span>
                    </div>

                    <div>
                      <span className="font-medium">{entry.bytes_returned} bytes</span>
                    </div>

                    <div>
                      <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                        {entry.receipt_id.slice(0, 8)}...
                      </span>
                    </div>

                    {entry.drift_detected && (
                      <div className="text-red-600 font-medium">
                        ⚠️ Drift: {entry.drift_reason}
                      </div>
                    )}
                  </div>

                  {entry.error_message && (
                    <div className="mt-2 ml-8 text-sm text-red-600 bg-red-50 p-2 rounded">
                      Error: {entry.error_message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-200 bg-gray-50 text-sm text-gray-600">
          Showing {filteredEntries.length} of {entries.length} entries
        </div>
      </div>
    </div>
  );
};

export default AuditLogViewer;
