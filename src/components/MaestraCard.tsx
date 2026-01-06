import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Paperclip, Camera, Settings, X, ArrowDown, Target } from 'lucide-react';
import { MessageRenderer } from './MessageRenderer';
import { SourcesPanel } from './SourcesPanel';

// Type declaration for ImageCapture API (not in default TS lib)
declare class ImageCapture {
  constructor(track: MediaStreamTrack);
  grabFrame(): Promise<ImageBitmap>;
}
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
  const [captureButtonMode, setCaptureButtonMode] = useState(false);
  const [selection, setSelection] = useState<string | null>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [screenshotStatus, setScreenshotStatus] = useState<'idle' | 'capturing' | 'success' | 'error'>('idle');
  const [captureType, setCaptureType] = useState<'screenshot' | 'code' | null>(null);
  const clickTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Screenshot capture function
  const captureScreenshot = async () => {
    setScreenshotStatus('capturing');
    setCaptureType('screenshot');
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'browser' } as MediaTrackConstraints,
        audio: false,
      });
      const track = stream.getVideoTracks()[0];
      const imageCapture = new ImageCapture(track);
      const bitmap = await imageCapture.grabFrame();
      track.stop();
      
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      const ctx = canvas.getContext('2d');
      ctx?.drawImage(bitmap, 0, 0);
      
      canvas.toBlob(async (blob) => {
        if (blob) {
          try {
            await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
            setScreenshotStatus('success');
            setTimeout(() => { setScreenshotStatus('idle'); setCaptureType(null); }, 1500);
          } catch {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `maestra-screenshot-${Date.now()}.png`;
            a.click();
            URL.revokeObjectURL(url);
            setScreenshotStatus('success');
            setTimeout(() => { setScreenshotStatus('idle'); setCaptureType(null); }, 1500);
          }
        }
      }, 'image/png');
    } catch (err) {
      console.error('Screenshot capture failed:', err);
      setScreenshotStatus('error');
      setTimeout(() => { setScreenshotStatus('idle'); setCaptureType(null); }, 2000);
    }
  };

  // Code/context capture function
  const captureCode = async () => {
    setScreenshotStatus('capturing');
    setCaptureType('code');
    try {
      // Gather page context
      const pageContext = {
        url: window.location.href,
        title: document.title,
        timestamp: new Date().toISOString(),
        viewport: { width: window.innerWidth, height: window.innerHeight },
        // Get console errors if available
        userAgent: navigator.userAgent,
        // Capture visible text content (truncated)
        visibleText: document.body.innerText.slice(0, 5000),
        // Get any error elements
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"]'))
          .map(el => el.textContent?.trim())
          .filter(Boolean)
          .slice(0, 10),
        // Get meta tags
        meta: Array.from(document.querySelectorAll('meta'))
          .map(m => ({ name: m.getAttribute('name'), content: m.getAttribute('content') }))
          .filter(m => m.name),
      };

      const contextText = `# Page Context Capture
URL: ${pageContext.url}
Title: ${pageContext.title}
Timestamp: ${pageContext.timestamp}
Viewport: ${pageContext.viewport.width}x${pageContext.viewport.height}
User Agent: ${pageContext.userAgent}

## Errors Found (${pageContext.errors.length})
${pageContext.errors.length > 0 ? pageContext.errors.join('\n') : 'None detected'}

## Page Content (truncated)
${pageContext.visibleText.slice(0, 2000)}...
`;

      await navigator.clipboard.writeText(contextText);
      setScreenshotStatus('success');
      setTimeout(() => { setScreenshotStatus('idle'); setCaptureType(null); }, 1500);
    } catch (err) {
      console.error('Code capture failed:', err);
      setScreenshotStatus('error');
      setTimeout(() => { setScreenshotStatus('idle'); setCaptureType(null); }, 2000);
    }
  };

  // Handle click with single/double detection
  const handleCameraClick = () => {
    if (clickTimeoutRef.current) {
      // Double-click detected - cancel single click and do code capture
      clearTimeout(clickTimeoutRef.current);
      clickTimeoutRef.current = null;
      captureCode();
    } else {
      // Wait to see if it's a double-click
      clickTimeoutRef.current = setTimeout(() => {
        clickTimeoutRef.current = null;
        captureScreenshot();
      }, 250); // 250ms window for double-click
    }
  };

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
    
    // In capture mode, allow empty input (capture selection only)
    // In normal mode, require input
    if (captureButtonMode) {
      if (!inputValue.trim() && !selection) return;
    } else {
      if (!inputValue.trim()) return;
    }

    const context: Context = {};
    if (selection) {
      context.selection = selection;
    }

    if (captureButtonMode && onCapture) {
      onCapture({ content: inputValue || selection || '', context });
      // Deselect capture mode after successful capture
      setCaptureButtonMode(false);
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
        {/* Gradient fade overlay for old messages */}
        <div className="absolute top-0 left-0 right-0 h-24 bg-gradient-to-b from-zinc-800 to-transparent pointer-events-none z-10" />
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
              className={`max-w-[85%] rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-brand text-white'
                  : 'bg-zinc-700 text-zinc-100'
              }`}
            >
              {message.role === 'user' ? (
                <p className="whitespace-pre-wrap">{message.content}</p>
              ) : (
                <MessageRenderer content={message.content} />
              )}
              <span className="text-xs opacity-60 mt-2 block">
                {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              {message.role === 'assistant' && (message as any).sources && (
                <SourcesPanel sources={(message as any).sources} className="mt-2" />
              )}
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
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
          <button
            onClick={scrollToBottom}
            className="bg-zinc-700 hover:bg-zinc-600 active:bg-zinc-500 text-zinc-200 px-3 py-1.5 rounded-full text-sm flex items-center gap-1 shadow-lg transition-colors"
          >
            <ArrowDown size={14} />
            Scroll to latest
          </button>
        </div>
      )}

      <div className="p-4 border-t border-zinc-700">
        {selection && (
          <div className="mb-2 flex items-center gap-2">
            <span className="bg-brand/20 text-brand px-3 py-1 rounded-full text-sm flex items-center gap-2">
              Selection: {wordCount} word{wordCount !== 1 ? 's' : ''}
              <button
                onClick={() => setSelection(null)}
                className="hover:text-brand/80 transition-colors"
              >
                <X size={14} />
              </button>
            </span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-2" data-testid="message-form">
          <div className="flex gap-2.5">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={captureButtonMode ? "Describe what you want to capture..." : "Type a message..."}
              className="flex-1 bg-zinc-900 text-zinc-100 rounded-lg px-2.5 py-1.5 outline-none focus:ring-2 focus:ring-brand/50 placeholder-zinc-500"
              disabled={isStreaming}
              data-testid="message-input"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isStreaming}
              className="bg-brand hover:bg-brand/90 active:bg-brand/80 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg px-2.5 py-1.5 transition-colors flex items-center gap-2"
              data-testid="send-button"
            >
              <Send size={18} />
              Send
            </button>
            <button
              type="button"
              onClick={() => {
                if (!inputValue.trim() && !selection) return;
                if (onCapture) {
                  const context: Context = {};
                  if (selection) context.selection = selection;
                  onCapture({ content: inputValue || selection || '', context });
                  setInputValue('');
                  setSelection(null);
                }
              }}
              disabled={(!inputValue.trim() && !selection) || isStreaming}
              className="bg-brand hover:bg-brand/90 active:bg-brand/80 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg p-1.5 transition-colors"
              title="Pointed capture (text or container)"
              data-testid="pointed-capture-button"
            >
              <Target size={18} />
            </button>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              className="p-2 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 active:bg-zinc-600 rounded-lg transition-colors"
              title="Attach file"
              onClick={() => {
                // Trigger file input
                const input = document.createElement('input');
                input.type = 'file';
                input.onchange = (e) => {
                  const file = (e.target as HTMLInputElement).files?.[0];
                  if (file) {
                    // File attachment logic would go here
                    console.log('File selected:', file.name);
                  }
                };
                input.click();
              }}
            >
              <Paperclip size={16} />
            </button>
            <button
              type="button"
              disabled={screenshotStatus === 'capturing'}
              onClick={handleCameraClick}
              className={`p-2 rounded-lg transition-colors ${
                screenshotStatus === 'capturing' 
                  ? 'text-yellow-400 animate-pulse' 
                  : screenshotStatus === 'success'
                  ? 'text-green-400 bg-green-400/20'
                  : screenshotStatus === 'error'
                  ? 'text-red-400 bg-red-400/20'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 active:bg-zinc-600'
              }`}
              title={
                screenshotStatus === 'success' 
                  ? (captureType === 'code' ? 'Context copied!' : 'Screenshot copied!') 
                  : 'Click: Screenshot | Double-click: Code capture'
              }
              data-testid="screengrab-capture-button"
            >
              <Camera size={16} />
            </button>
            <button
              type="button"
              className="p-2 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 active:bg-zinc-600 rounded-lg transition-colors"
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
