import { X, Pin } from 'lucide-react';
import type { CaptureResult } from '../adapters/types';
import { HandoffCapsule } from './HandoffCapsule';

interface PinsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  pins: CaptureResult[];
  onShare?: (capture: CaptureResult) => void;
}

export function PinsDrawer({ isOpen, onClose, pins, onShare }: PinsDrawerProps) {
  return (
    <div
      className={`fixed top-0 right-0 h-full w-80 bg-zinc-850 border-l border-zinc-700 transform transition-transform duration-300 z-50 ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
      style={{ backgroundColor: '#1f1f23' }}
    >
      <div className="flex items-center justify-between p-4 border-b border-zinc-700">
        <div className="flex items-center gap-2 text-zinc-200">
          <Pin size={18} />
          <h2 className="font-medium">Pins</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 rounded transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      <div className="p-4 space-y-3 overflow-y-auto h-[calc(100%-60px)]">
        {pins.length === 0 ? (
          <p className="text-zinc-500 text-sm text-center py-8">
            No pins yet. Use capture mode to save snippets.
          </p>
        ) : (
          pins.map((pin) => (
            <HandoffCapsule key={pin.id} capture={pin} onShare={onShare} />
          ))
        )}
      </div>
    </div>
  );
}
