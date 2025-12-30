import { useState, useCallback, useEffect } from 'react';
import { MaestraCard, Header, PinsDrawer, ErrorBoundary } from './components';
import { mockAdapter } from './adapters';
import { selectMode, type PageContext } from './modes';
import { trackMessageSent, trackCaptureCreated, trackModeSelected } from './lib/analytics';
import type { Message, Context, CaptureResult } from './adapters/types';

const generateId = () => Math.random().toString(36).substring(2, 9);

function AppContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pins, setPins] = useState<CaptureResult[]>([]);
  const [isPinsOpen, setIsPinsOpen] = useState(false);
  const conversationId = 'main';

  // Detect current page context and select mode
  const pageContext: PageContext = {
    url: window.location.href,
    title: document.title,
    domain: window.location.hostname,
    selection: window.getSelection()?.toString() || undefined,
  };
  const modeMatch = selectMode(pageContext);

  // Track mode selection on mount
  useEffect(() => {
    trackModeSelected(modeMatch.mode.id, modeMatch.confidence);
  }, [modeMatch.mode.id, modeMatch.confidence]);

  const handleSendMessage = useCallback(async (content: string, context?: Context) => {
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);
    trackMessageSent(modeMatch.mode.id, !!context);

    try {
      const response = await mockAdapter.sendMessage(conversationId, content, context);
      setMessages((prev) => [...prev, response.message]);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsStreaming(false);
    }
  }, [modeMatch]);

  const handleCapture = useCallback(async (payload: { content: string; context?: Context }) => {
    try {
      const result = await mockAdapter.capture(payload);
      setPins((prev) => [result, ...prev]);
      setIsPinsOpen(true);
      trackCaptureCreated(modeMatch.mode.id);
    } catch (error) {
      console.error('Failed to capture:', error);
    }
  }, [modeMatch]);

  const handleShare = useCallback((capture: CaptureResult) => {
    console.log('Sharing:', capture);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-zinc-900">
      <Header 
        onTogglePins={() => setIsPinsOpen(!isPinsOpen)} 
        pinsCount={pins.length}
        modeId={modeMatch.mode.id}
        modeConfidence={modeMatch.confidence}
      />

      <main className="flex-1 p-6 overflow-hidden">
        <div className="h-full max-w-4xl mx-auto">
          <MaestraCard
            variant="full"
            messages={messages}
            isStreaming={isStreaming}
            onSendMessage={handleSendMessage}
            onCapture={handleCapture}
          />
        </div>
      </main>

      <PinsDrawer
        isOpen={isPinsOpen}
        onClose={() => setIsPinsOpen(false)}
        pins={pins}
        onShare={handleShare}
      />

      {isPinsOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40"
          onClick={() => setIsPinsOpen(false)}
        />
      )}
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}

export default App;
