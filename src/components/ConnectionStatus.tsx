import React, { useEffect, useState } from 'react';
import { getConnectionMode, getConnectionState } from '../adapters/webAdapter';
import type { ConnectionMode } from '../adapters/webAdapter';

/**
 * ConnectionStatus Component
 * 
 * Displays the current connection mode and available capabilities
 * Updates in real-time as connection state changes
 * 
 * Modes:
 * - 🟢 Quad-Core: Full capabilities (Sidecar + Local Brain + Hosted)
 * - 🟡 Local: Full context but local compute only
 * - ⚪ Cloud Only: Limited context (hosted backend only)
 */

interface ConnectionStatusProps {
  className?: string;
  showDetails?: boolean;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  className = '',
  showDetails = false,
}) => {
  const [mode, setMode] = useState<ConnectionMode>('cloud-only');
  const [state, setState] = useState(getConnectionState());
  const [showTooltip, setShowTooltip] = useState(false);

  // Poll connection state every 2 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const currentMode = getConnectionMode();
      const currentState = getConnectionState();
      
      if (currentMode !== mode) {
        setMode(currentMode);
        // Show brief notification on mode change
        console.log(`[Maestra] Connection mode changed: ${mode} → ${currentMode}`);
      }
      
      setState(currentState);
    }, 2000);

    return () => clearInterval(interval);
  }, [mode]);

  const getModeIcon = () => {
    switch (mode) {
      case 'quad-core':
        return '🟢';
      case 'local':
        return '🟡';
      case 'cloud-only':
        return '⚪';
      default:
        return '⚪';
    }
  };

  const getModeLabel = () => {
    switch (mode) {
      case 'quad-core':
        return 'Quad-Core Active';
      case 'local':
        return 'Local Mode';
      case 'cloud-only':
        return 'Cloud Only';
      default:
        return 'Connecting...';
    }
  };

  const getModeDescription = () => {
    switch (mode) {
      case 'quad-core':
        return 'Connected to Sidecar + Local Brain + Hosted Backend. Full capabilities available.';
      case 'local':
        return 'Connected to Local Backend. Full library context available, local compute only.';
      case 'cloud-only':
        return 'Connected to Hosted Backend only. Library context unavailable. Limited capabilities.';
      default:
        return 'Determining connection mode...';
    }
  };

  const getCapabilities = () => {
    const caps = [];
    
    if (state.sidecarAvailable) {
      caps.push('Sidecar');
    }
    if (state.localBackendAvailable) {
      caps.push('Local Backend');
    }
    caps.push('Hosted Backend');
    
    return caps;
  };

  const getContextAvailability = () => {
    switch (mode) {
      case 'quad-core':
        return 'Full (K/D/P + Sidecar)';
      case 'local':
        return 'Full (K/D/P + Local)';
      case 'cloud-only':
        return 'Limited (Manifesto only)';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className={`relative ${className}`}>
      {/* Status Badge */}
      <button
        onClick={() => setShowTooltip(!showTooltip)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`
          flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium
          transition-all duration-200 cursor-help
          ${
            mode === 'quad-core'
              ? 'bg-green-100 text-green-800 hover:bg-green-200'
              : mode === 'local'
              ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }
        `}
        title={getModeDescription()}
      >
        <span className="text-lg">{getModeIcon()}</span>
        <span>{getModeLabel()}</span>
      </button>

      {/* Tooltip */}
      {showTooltip && (
        <div
          className={`
            absolute top-full mt-2 left-0 z-50
            bg-white border rounded-lg shadow-lg p-3 min-w-max
            ${mode === 'cloud-only' ? 'border-gray-300' : 'border-gray-200'}
          `}
        >
          {/* Mode Description */}
          <div className="mb-3 pb-3 border-b border-gray-200">
            <p className="text-xs font-semibold text-gray-700 mb-1">
              {getModeLabel()}
            </p>
            <p className="text-xs text-gray-600">
              {getModeDescription()}
            </p>
          </div>

          {/* Active Services */}
          <div className="mb-3 pb-3 border-b border-gray-200">
            <p className="text-xs font-semibold text-gray-700 mb-1.5">
              Active Services
            </p>
            <div className="flex flex-wrap gap-1">
              {getCapabilities().map((cap) => (
                <span
                  key={cap}
                  className="inline-block px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded"
                >
                  {cap}
                </span>
              ))}
            </div>
          </div>

          {/* Context Availability */}
          <div className="mb-3 pb-3 border-b border-gray-200">
            <p className="text-xs font-semibold text-gray-700 mb-1">
              Context Available
            </p>
            <p className="text-xs text-gray-600">
              {getContextAvailability()}
            </p>
          </div>

          {/* Last Health Check */}
          <div>
            <p className="text-xs text-gray-500">
              Last check: {new Date(state.lastHealthCheck).toLocaleTimeString()}
            </p>
          </div>

          {/* Warning for Cloud Only */}
          {mode === 'cloud-only' && (
            <div className="mt-3 pt-3 border-t border-yellow-200 bg-yellow-50 rounded p-2">
              <p className="text-xs text-yellow-800 font-medium">
                ⚠️ Limited Context
              </p>
              <p className="text-xs text-yellow-700 mt-1">
                Library access unavailable. Start local services for full capabilities.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Inline Details (optional) */}
      {showDetails && (
        <div className="mt-2 text-xs text-gray-600 space-y-1">
          <div>Mode: <span className="font-mono font-semibold">{mode}</span></div>
          <div>Context: <span className="font-mono font-semibold">{getContextAvailability()}</span></div>
          <div>Services: <span className="font-mono font-semibold">{getCapabilities().join(', ')}</span></div>
        </div>
      )}
    </div>
  );
};

export default ConnectionStatus;
