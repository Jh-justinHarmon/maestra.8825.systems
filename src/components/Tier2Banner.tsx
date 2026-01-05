import React, { useEffect, useState } from 'react';
import { AlertCircle, Clock, Zap, X } from 'lucide-react';

export interface Tier2BannerProps {
  sessionId: string;
  isVisible: boolean;
  onDismiss?: () => void;
  onDisableTier2?: () => void;
  ttlSeconds?: number;
  bytesBudget?: number;
  bytesUsed?: number;
}

export const Tier2Banner: React.FC<Tier2BannerProps> = ({
  sessionId,
  isVisible,
  onDismiss,
  onDisableTier2,
  ttlSeconds = 900,
  bytesBudget = 5242880,
  bytesUsed = 0,
}) => {
  const [timeRemaining, setTimeRemaining] = useState(ttlSeconds);
  const [bytesPercentage, setBytesPercentage] = useState(0);

  useEffect(() => {
    if (!isVisible) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [isVisible]);

  useEffect(() => {
    setBytesPercentage(Math.round((bytesUsed / bytesBudget) * 100));
  }, [bytesUsed, bytesBudget]);

  if (!isVisible) return null;

  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;
  const bytesMB = (bytesBudget / 1024 / 1024).toFixed(1);
  const usedMB = (bytesUsed / 1024 / 1024).toFixed(1);

  return (
    <div className="fixed bottom-4 right-4 max-w-sm bg-red-50 border-2 border-red-200 rounded-lg shadow-lg p-4 z-50">
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
        
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-red-900 mb-2">
            Raw Data Access Active (Tier 2)
          </h3>
          
          <p className="text-sm text-red-800 mb-3">
            Your conversation has access to unredacted raw data. This data will automatically delete after the time limit expires.
          </p>

          <div className="space-y-2 mb-3">
            <div className="flex items-center gap-2 text-sm text-red-700">
              <Clock className="h-4 w-4" />
              <span>
                Time remaining: <strong>{minutes}m {seconds}s</strong>
              </span>
            </div>

            <div className="flex items-center gap-2 text-sm text-red-700">
              <Zap className="h-4 w-4" />
              <span>
                Data used: <strong>{usedMB} MB / {bytesMB} MB</strong>
              </span>
            </div>

            <div className="w-full bg-red-200 rounded-full h-2">
              <div
                className="bg-red-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${bytesPercentage}%` }}
              />
            </div>
          </div>

          <div className="bg-red-100 border border-red-300 rounded p-2 mb-3">
            <p className="text-xs text-red-900">
              <strong>What this means:</strong> Your raw data will be automatically deleted when the time expires or the session ends. No permanent storage.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={onDisableTier2}
              className="flex-1 px-3 py-2 text-sm font-medium text-red-700 bg-red-100 hover:bg-red-200 rounded transition-colors"
            >
              Disable Raw Data
            </button>
            <button
              onClick={onDismiss}
              className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="text-xs text-gray-500 mt-3 pt-3 border-t border-red-200">
        Session: {sessionId.slice(0, 8)}...
      </div>
    </div>
  );
};

export default Tier2Banner;
