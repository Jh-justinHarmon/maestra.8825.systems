import React, { useState, useEffect } from 'react';
import { AlertCircle, X, RefreshCw } from 'lucide-react';

/**
 * ErrorBanner Component
 * 
 * Displays error messages with actionable guidance and retry logic
 * Auto-dismisses after 8 seconds or on user action
 */

export type ErrorType = 'connection' | 'library' | 'auth' | 'validation' | 'server' | 'unknown';

export interface ErrorBannerProps {
  message: string;
  type?: ErrorType;
  onDismiss?: () => void;
  onRetry?: () => void;
  autoClose?: boolean;
  autoDismissMs?: number;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  message,
  type = 'unknown',
  onDismiss,
  onRetry,
  autoClose = true,
  autoDismissMs = 8000,
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    if (!autoClose) return;

    const timer = setTimeout(() => {
      setIsVisible(false);
      onDismiss?.();
    }, autoDismissMs);

    return () => clearTimeout(timer);
  }, [autoClose, autoDismissMs, onDismiss]);

  if (!isVisible) return null;

  const getIcon = () => {
    switch (type) {
      case 'connection':
        return <AlertCircle className="h-5 w-5" />;
      case 'library':
        return <AlertCircle className="h-5 w-5" />;
      case 'auth':
        return <AlertCircle className="h-5 w-5" />;
      case 'validation':
        return <AlertCircle className="h-5 w-5" />;
      case 'server':
        return <AlertCircle className="h-5 w-5" />;
      default:
        return <AlertCircle className="h-5 w-5" />;
    }
  };

  const getColors = () => {
    switch (type) {
      case 'connection':
        return 'bg-yellow-50 border-yellow-200 text-yellow-900';
      case 'library':
        return 'bg-orange-50 border-orange-200 text-orange-900';
      case 'auth':
        return 'bg-red-50 border-red-200 text-red-900';
      case 'validation':
        return 'bg-blue-50 border-blue-200 text-blue-900';
      case 'server':
        return 'bg-red-50 border-red-200 text-red-900';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-900';
    }
  };

  const getActionText = () => {
    switch (type) {
      case 'connection':
        return 'Trying Local Backend...';
      case 'library':
        return 'Check Entry ID or permissions';
      case 'auth':
        return 'Please re-authenticate';
      case 'validation':
        return 'Check your input';
      case 'server':
        return 'Server error - try again';
      default:
        return 'An error occurred';
    }
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await onRetry?.();
    } finally {
      setIsRetrying(false);
    }
  };

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.();
  };

  return (
    <div
      className={`
        fixed top-4 left-4 right-4 max-w-md
        border rounded-lg p-4 shadow-lg
        flex items-start gap-3
        ${getColors()}
        z-50 animate-in fade-in slide-in-from-top-2
      `}
    >
      <div className="flex-shrink-0 mt-0.5">
        {getIcon()}
      </div>

      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm mb-1">
          {getActionText()}
        </p>
        <p className="text-xs opacity-90 break-words">
          {message}
        </p>
      </div>

      <div className="flex-shrink-0 flex gap-2">
        {onRetry && (
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            className="p-1 hover:opacity-70 transition-opacity disabled:opacity-50"
            title="Retry"
          >
            <RefreshCw
              className={`h-4 w-4 ${isRetrying ? 'animate-spin' : ''}`}
            />
          </button>
        )}
        <button
          onClick={handleDismiss}
          className="p-1 hover:opacity-70 transition-opacity"
          title="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

export default ErrorBanner;
