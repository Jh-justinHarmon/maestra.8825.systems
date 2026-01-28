import React from 'react';

/**
 * TRACK 2: Message Metadata
 * 
 * Displays agent identity and authority source under each assistant message.
 * This is truth-on-surface - users always know who answered and on what authority.
 * 
 * Format: "Answered by: Analyst · Authority: System"
 */

interface MessageMetadataProps {
  agent?: {
    id: string;
    display_name: string;
  };
  authority?: 'system' | 'memory' | 'none';
  className?: string;
}

export const MessageMetadata: React.FC<MessageMetadataProps> = ({
  agent,
  authority,
  className = '',
}) => {
  // Don't render if we have no metadata
  if (!agent && !authority) {
    return null;
  }

  const getAuthorityLabel = () => {
    switch (authority) {
      case 'system':
        return 'System';
      case 'memory':
        return 'Memory';
      case 'none':
        return 'None';
      default:
        return '—';
    }
  };

  const getAuthorityColor = () => {
    switch (authority) {
      case 'system':
        return 'text-blue-400';
      case 'memory':
        return 'text-green-400';
      case 'none':
        return 'text-zinc-500';
      default:
        return 'text-zinc-500';
    }
  };

  return (
    <div className={`flex items-center gap-2 text-xs text-zinc-500 mt-1 ${className}`}>
      <span>
        Answered by:{' '}
        <span className="text-zinc-400 font-medium">
          {agent?.display_name || '—'}
        </span>
      </span>
      <span className="text-zinc-600">·</span>
      <span>
        Authority:{' '}
        <span className={`font-medium ${getAuthorityColor()}`}>
          {getAuthorityLabel()}
        </span>
      </span>
    </div>
  );
};

export default MessageMetadata;
