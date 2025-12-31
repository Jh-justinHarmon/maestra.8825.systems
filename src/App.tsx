import { useState, useCallback, useEffect } from 'react';
import { MaestraCard, Header, PinsDrawer, ErrorBoundary, BreadcrumbPanel } from './components';
import { webAdapter } from './adapters';
import { selectMode, type PageContext } from './modes';
import { trackMessageSent, trackCaptureCreated, trackModeSelected } from './lib/analytics';
import { breadcrumbTrail } from './lib/breadcrumbs';
import type { Message, Context, CaptureResult } from './adapters/types';

const generateId = () => Math.random().toString(36).substring(2, 9);

function AppContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pins, setPins] = useState<CaptureResult[]>([]);
  const [isPinsOpen, setIsPinsOpen] = useState(false);
  const [showBreadcrumbs, setShowBreadcrumbs] = useState(false);
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

    // Start breadcrumb trail
    breadcrumbTrail.startExecution(userMessage.id, content);
    breadcrumbTrail.addSource('Maestra UI', { mode: modeMatch.mode.id, confidence: modeMatch.confidence });
    
    if (context?.selection) {
      breadcrumbTrail.addContext('selection', { length: context.selection.length });
    }

    try {
      const startTime = performance.now();
      breadcrumbTrail.addTool('webAdapter.sendMessage', { endpoint: 'api/maestra/advisor/ask' });
      
      const response = await webAdapter.sendMessage(conversationId, content, context, messages);
      
      const duration = performance.now() - startTime;
      breadcrumbTrail.addResult('Message received', { 
        traceId: response.message.id,
        contentLength: response.message.content.length 
      }, duration);
      
      setMessages((prev) => [...prev, response.message]);
    } catch (error) {
      breadcrumbTrail.addError('Message failed', { 
        error: error instanceof Error ? error.message : String(error) 
      });
      console.error('Failed to send message:', error);
    } finally {
      breadcrumbTrail.endExecution();
      setIsStreaming(false);
    }
  }, [modeMatch, messages]);

  const handleCapture = useCallback(async (payload: { content: string; context?: Context }) => {
    const captureId = generateId();
    breadcrumbTrail.startExecution(captureId, `Capture: ${payload.content.substring(0, 30)}`);
    breadcrumbTrail.addSource('Maestra UI - Capture', { mode: modeMatch.mode.id });
    breadcrumbTrail.addTool('webAdapter.capture', { endpoint: 'api/maestra/advisor/ask' });

    try {
      const startTime = performance.now();
      const result = await webAdapter.capture(payload);
      const duration = performance.now() - startTime;
      
      breadcrumbTrail.addResult('Capture created', { 
        captureId: result.id,
        title: result.title 
      }, duration);
      
      setPins((prev) => [result, ...prev]);
      setIsPinsOpen(true);
      trackCaptureCreated(modeMatch.mode.id);
    } catch (error) {
      breadcrumbTrail.addError('Capture failed', { 
        error: error instanceof Error ? error.message : String(error) 
      });
      console.error('Failed to capture:', error);
    } finally {
      breadcrumbTrail.endExecution();
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

      <main className={`flex-1 p-6 lg:px-[250px] overflow-hidden ${showBreadcrumbs ? 'pb-80' : ''}`}>
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

      <BreadcrumbPanel 
        isOpen={showBreadcrumbs}
        onToggle={() => setShowBreadcrumbs(!showBreadcrumbs)}
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
