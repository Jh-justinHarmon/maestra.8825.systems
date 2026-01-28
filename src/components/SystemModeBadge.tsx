import React from 'react';

/**
 * TRACK 2: System Mode Badge
 * 
 * Displays the backend's system mode (FULL or MINIMAL) prominently.
 * This is truth-on-surface - users always know what mode they're in.
 * 
 * Colors:
 * - FULL: 🟢 Green - Real system active
 * - MINIMAL: 🔴 Red - Emergency mode, stubs only
 */

interface SystemModeBadgeProps {
  mode?: 'full' | 'minimal';
  className?: string;
}

export const SystemModeBadge: React.FC<SystemModeBadgeProps> = ({
  mode,
  className = '',
}) => {
  if (!mode) {
    return null; // Don't show badge until we have data
  }

  const isFull = mode === 'full';

  return (
    <div
      className={`
        flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
        ${isFull 
          ? 'bg-green-900/50 text-green-400 border border-green-700/50' 
          : 'bg-red-900/50 text-red-400 border border-red-700/50'
        }
        ${className}
      `}
      title={isFull 
        ? 'FULL MODE — Real system dependencies active' 
        : 'MINIMAL MODE — Emergency stubs only, limited functionality'
      }
    >
      <span className="text-sm">{isFull ? '🟢' : '🔴'}</span>
      <span>{isFull ? 'FULL' : 'MINIMAL'}</span>
    </div>
  );
};

export default SystemModeBadge;
