import { Pin, Sparkles } from 'lucide-react';

interface HeaderProps {
  onTogglePins: () => void;
  pinsCount: number;
}

export function Header({ onTogglePins, pinsCount }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
          <Sparkles size={18} className="text-white" />
        </div>
        <h1 className="text-xl font-semibold text-zinc-100">Maestra</h1>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onTogglePins}
          className="flex items-center gap-2 px-3 py-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
        >
          <Pin size={16} />
          <span className="text-sm">Pins</span>
          {pinsCount > 0 && (
            <span className="bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full min-w-[1.25rem] text-center">
              {pinsCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}
