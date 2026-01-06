 import { Pin, Hexagon, Settings } from 'lucide-react';
import { useState } from 'react';
import { ConnectionStatus } from './ConnectionStatus';

interface HeaderProps {
  onTogglePins: () => void;
  pinsCount: number;
  modeId?: string;
  modeConfidence?: number;
}

export function Header({ onTogglePins, pinsCount, modeId, modeConfidence }: HeaderProps) {
  const [showApiDebug, setShowApiDebug] = useState(false);
  const [apiEndpoint, setApiEndpoint] = useState(
    localStorage.getItem('maestra_api_override') || ''
  );

  const getModeLabel = (id: string) => {
    switch (id) {
      case 'replit_collaborator':
        return 'Replit';
      case 'default':
        return 'Default';
      default:
        return id;
    }
  };

  const handleApiOverride = (value: string) => {
    setApiEndpoint(value);
    if (value.trim()) {
      localStorage.setItem('maestra_api_override', value);
      window.location.reload();
    } else {
      localStorage.removeItem('maestra_api_override');
      window.location.reload();
    }
  };

  return (
    <header className="flex items-center justify-between px-6 lg:px-[250px] py-4 border-b border-zinc-800">
      <div className="flex items-center gap-2">
        <div className="w-10 h-10 bg-brand rounded-xl flex items-center justify-center">
          <Hexagon size={20} className="text-white" />
        </div>
        <h1 className="text-2xl font-logo font-normal text-zinc-100 tracking-tight">maestra</h1>
        {modeId && (
          <span className="ml-2 px-2 py-1 text-xs font-medium text-zinc-400 bg-zinc-800 rounded">
            {getModeLabel(modeId)}
            {modeConfidence !== undefined && (
              <span className="text-zinc-500 ml-1">
                {Math.round(modeConfidence * 100)}%
              </span>
            )}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <ConnectionStatus className="text-sm" />
        <button
          onClick={() => setShowApiDebug(!showApiDebug)}
          className="flex items-center gap-2 px-3 py-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
          title="API Debug"
        >
          <Settings size={16} />
        </button>
        <button
          onClick={onTogglePins}
          className="flex items-center gap-2 px-3 py-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
        >
          <Pin size={16} />
          <span className="text-sm">Pins</span>
          {pinsCount > 0 && (
            <span className="bg-brand text-white text-xs px-1.5 py-0.5 rounded-full min-w-[1.25rem] text-center">
              {pinsCount}
            </span>
          )}
        </button>
      </div>

      {showApiDebug && (
        <div className="absolute top-16 right-6 bg-zinc-900 border border-zinc-700 rounded-lg p-4 shadow-lg z-50 w-80">
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-zinc-400 block mb-1">
                API Endpoint Override
              </label>
              <input
                type="text"
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                placeholder="e.g., http://localhost:8000"
                className="w-full bg-zinc-800 text-zinc-100 rounded px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-brand/50"
              />
              <p className="text-xs text-zinc-500 mt-1">
                Leave empty to use production
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleApiOverride(apiEndpoint)}
                className="flex-1 bg-brand hover:bg-brand/90 text-white text-sm px-3 py-1.5 rounded transition-colors"
              >
                Apply
              </button>
              <button
                onClick={() => setShowApiDebug(false)}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm px-3 py-1.5 rounded transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
