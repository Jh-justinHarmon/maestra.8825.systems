import React, { useState } from 'react';
import { Globe, Home, Shield, Eye } from 'lucide-react';

export interface ProvenanceMetadata {
  source: 'local' | 'hosted' | 'hybrid';
  capability_id: string;
  tier: 0 | 1 | 2;
  executed_at: string;
  execution_time_ms: number;
  bytes_returned: number;
  drift_detected: boolean;
  receipt_id?: string;
}

export interface ProvenanceBadgeProps {
  provenance: ProvenanceMetadata;
  compact?: boolean;
  onViewAudit?: () => void;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  provenance,
  compact = false,
  onViewAudit,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  const sourceIcon = {
    local: <Home className="h-4 w-4" />,
    hosted: <Globe className="h-4 w-4" />,
    hybrid: <Shield className="h-4 w-4" />,
  }[provenance.source];

  const sourceLabel = {
    local: 'Local',
    hosted: 'Cloud',
    hybrid: 'Hybrid',
  }[provenance.source];

  const tierLabel = {
    0: 'Pointers',
    1: 'Redacted',
    2: 'Raw',
  }[provenance.tier];

  const tierColor = {
    0: 'bg-green-100 text-green-800 border-green-300',
    1: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    2: 'bg-red-100 text-red-800 border-red-300',
  }[provenance.tier];

  const sourceColor = {
    local: 'bg-blue-100 text-blue-800 border-blue-300',
    hosted: 'bg-purple-100 text-purple-800 border-purple-300',
    hybrid: 'bg-indigo-100 text-indigo-800 border-indigo-300',
  }[provenance.source];

  if (compact) {
    return (
      <div
        className="relative inline-flex items-center gap-1"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <div className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${sourceColor}`}>
          {sourceIcon}
          <span>{sourceLabel}</span>
        </div>

        <div className={`px-2 py-1 rounded text-xs font-medium border ${tierColor}`}>
          {tierLabel}
        </div>

        {showTooltip && (
          <div className="absolute bottom-full left-0 mb-2 bg-gray-900 text-white text-xs rounded p-2 whitespace-nowrap z-50">
            <p>{provenance.capability_id}</p>
            <p>{provenance.execution_time_ms}ms</p>
            {provenance.drift_detected && <p className="text-red-300">⚠️ Drift detected</p>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-gray-900">Data Provenance</h4>
        {provenance.drift_detected && (
          <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-1 rounded">
            ⚠️ Drift Detected
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-gray-600">Source</p>
          <div className={`flex items-center gap-1 mt-1 px-2 py-1 rounded border w-fit ${sourceColor}`}>
            {sourceIcon}
            <span className="font-medium">{sourceLabel}</span>
          </div>
        </div>

        <div>
          <p className="text-gray-600">Data Tier</p>
          <div className={`flex items-center gap-1 mt-1 px-2 py-1 rounded border w-fit ${tierColor}`}>
            <Shield className="h-4 w-4" />
            <span className="font-medium">{tierLabel}</span>
          </div>
        </div>

        <div>
          <p className="text-gray-600">Capability</p>
          <p className="text-gray-900 font-mono text-xs mt-1">{provenance.capability_id}</p>
        </div>

        <div>
          <p className="text-gray-600">Execution Time</p>
          <p className="text-gray-900 font-medium mt-1">{provenance.execution_time_ms}ms</p>
        </div>

        <div>
          <p className="text-gray-600">Data Size</p>
          <p className="text-gray-900 font-medium mt-1">
            {(provenance.bytes_returned / 1024).toFixed(1)} KB
          </p>
        </div>

        <div>
          <p className="text-gray-600">Timestamp</p>
          <p className="text-gray-900 text-xs mt-1">
            {new Date(provenance.executed_at).toLocaleTimeString()}
          </p>
        </div>
      </div>

      {provenance.receipt_id && (
        <div className="pt-2 border-t border-gray-200">
          <button
            onClick={onViewAudit}
            className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            <Eye className="h-4 w-4" />
            View Audit Trail
          </button>
          <p className="text-xs text-gray-500 mt-1 font-mono">{provenance.receipt_id}</p>
        </div>
      )}
    </div>
  );
};

export default ProvenanceBadge;
