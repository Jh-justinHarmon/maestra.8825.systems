import { Copy, Share2, Check } from 'lucide-react';
import { useState } from 'react';
import type { CaptureResult } from '../adapters/types';

interface HandoffCapsuleProps {
  capture: CaptureResult;
  onShare?: (capture: CaptureResult) => void;
}

export function HandoffCapsule({ capture, onShare }: HandoffCapsuleProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(`${capture.title}\n\n${capture.summary}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShare = () => {
    onShare?.(capture);
  };

  return (
    <div className="inline-flex items-center gap-3 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 max-w-md">
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-zinc-200 truncate">{capture.title}</h4>
        <p className="text-xs text-zinc-400 line-clamp-2 mt-0.5">{capture.summary}</p>
      </div>
      
      <div className="flex items-center gap-1 flex-shrink-0">
        <button
          onClick={handleCopy}
          className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 rounded transition-colors"
          title="Copy to clipboard"
        >
          {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
        </button>
        <button
          onClick={handleShare}
          className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 rounded transition-colors"
          title="Share"
        >
          <Share2 size={14} />
        </button>
      </div>
    </div>
  );
}
