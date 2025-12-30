import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Paperclip, Camera, Settings, X, ArrowDown } from 'lucide-react';
import type { Message, Context } from '../adapters/types';

interface MaestraCardProps {
  variant?: 'full' | 'compact';
  onSendMessage: (message: string, context?: Context) => void;
  onCapture?: (payload: { content: string; context?: Context }) => void;
  messages: Message[];
  isStreaming?: boolean;
}

export function MaestraCard({
  variant = 'full',
  onSendMessage,
  onCapture,
  messages,
  isStreaming = false,
}: MaestraCardProps) {
  const [inputValue, setInputValue] = useState('');
  const [captureMode, setCaptureMode] = useState(false);
  const [selection, setSelection] = useState<string | null>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const handleScroll = useCallback(() => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShowScrollButton(!isNearBottom);
    }
  }, []);

  useEffect(() => {
    if (!showScrollButton) {
      scrollToBottom();
    }
  }, [messages, showScrollButton, scrollToBottom]);

  useEffect(() => {
    const handleSelection = () => {
      const selectedText = window.getSelection()?.toString().trim();
      if (selectedText && selectedText.length > 0) {
        setSelection(selectedText);
      }
    };

    document.addEventListener('mouseup', handleSelection);
    return () => document.removeEventListener('mouseup', handleSelection);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const context: Context = {};
    if (selection) {
      context.selection = selection;
    }

    if (captureMode && onCapture) {
      onCapture({ content: inputValue, context });
    } else {
      onSendMessage(inputValue, Object.keys(context).length > 0 ? context : undefined);
    }

    setInputValue('');
    setSelection(null);
  };

  const wordCount = selection ? selection.split(/\s+/).filter(Boolean).length : 0;

  const containerClass = variant === 'full'
    ? 'flex flex-col h-full bg-zinc-800 rounded-xl shadow-xl'
    : 'flex flex-col h-80 bg-zinc-800 rounded-lg shadow-lg';

  return (
    <div className={containerClass} data-testid="maestra-card">
      <div
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-4 relative"
        data-testid="messages-container"
      >
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-zinc-500">
            <p>Start a conversation with Maestra...</p>
          </div>
        )}
        
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-zinc-700 text-zinc-100'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              <span className="text-xs opacity-60 mt-1 block">
                {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}
        
        {isStreaming && (
          <div className="flex justify-start">
            <div className="bg-zinc-700 text-zinc-100 rounded-lg px-4 py-2">
              <div className="flex space-x-1">
                <span className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {showScrollButton && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-24 left-1/2 -translate-x-1/2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 px-3 py-1.5 rounded-full text-sm flex items-center gap-1 shadow-lg transition-colors"
        >
          <ArrowDown size={14} />
          Scroll to latest
        </button>
      )}

      <div className="p-4 border-t border-zinc-700">
        {selection && (
          <div className="mb-2 flex items-center gap-2">
            <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded-full text-sm flex items-center gap-2">
              Selection: {wordCount} word{wordCount !== 1 ? 's' : ''}
              <button
                onClick={() => setSelection(null)}
                className="hover:text-blue-300 transition-colors"
              >
                <X size={14} />
              </button>
            </span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-2" data-testid="message-form">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={captureMode ? "Describe what you want to capture..." : "Type a message..."}
              className="flex-1 bg-zinc-900 text-zinc-100 rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500/50 placeholder-zinc-500"
              disabled={isStreaming}
              data-testid="message-input"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isStreaming}
              className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg px-4 py-2.5 transition-colors flex items-center gap-2"
              data-testid="send-button"
            >
              {captureMode ? (
                <>
                  <Camera size={18} />
                  Capture
                </>
              ) : (
                <>
                  <Send size={18} />
                  Send
                </>
              )}
            </button>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              className="p-2 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 rounded-lg transition-colors"
              title="Attach file"
            >
              <Paperclip size={16} />
            </button>
            <button
              type="button"
              onClick={() => setCaptureMode(!captureMode)}
              className={`p-2 rounded-lg transition-colors ${
                captureMode
                  ? 'text-blue-400 bg-blue-500/20'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700'
              }`}
              title="Toggle capture mode"
              data-testid="capture-mode-toggle"
            >
              <Camera size={16} />
            </button>
            <button
              type="button"
              className="p-2 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 rounded-lg transition-colors"
              title="Settings"
            >
              <Settings size={16} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
