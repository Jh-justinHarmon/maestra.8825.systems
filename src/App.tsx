import { useState, useCallback, useEffect } from 'react';
import { MaestraCard, Header, PinsDrawer, ErrorBoundary, BreadcrumbPanel, DebugPanel } from './components';
import { webAdapter } from './adapters';
import { selectMode, type PageContext } from './modes';
import { trackMessageSent, trackCaptureCreated, trackModeSelected } from './lib/analytics';
import { breadcrumbTrail } from './lib/breadcrumbs';
import { getOrCreateSessionId } from './lib/session';
import type { Message, Context, CaptureResult } from './adapters/types';

const generateId = () => Math.random().toString(36).substring(2, 9);

function AppContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pins, setPins] = useState<CaptureResult[]>([]);
  const [isPinsOpen, setIsPinsOpen] = useState(false);
  const [showBreadcrumbs, setShowBreadcrumbs] = useState(false);
  const conversationId = getOrCreateSessionId();
  
  // TRACK 2: Track latest system_mode from backend responses
  const latestSystemMode = messages
    .filter(m => m.role === 'assistant' && m.system_mode)
    .slice(-1)[0]?.system_mode;

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

  // Poll conversation feed for real-time sync across surfaces
  // 
  // CRITICAL: This polling logic MUST preserve local optimistic messages.
  // Backend may legally return empty state (404, empty turns) when:
  // - DATABASE_URL is not configured
  // - Persistence layer is unavailable
  // - Session has not yet synced to database
  // 
  // Destructive replace (setMessages(serverMessages)) is FORBIDDEN.
  // Always merge server state with local state to prevent message loss.
  useEffect(() => {
    let pollInterval: NodeJS.Timeout | undefined;

    // Skip polling if backend indicates persistence unavailable
    const initPolling = async () => {
      try {
        const apiBase = localStorage.getItem('maestra_api_override') || 'http://localhost:8825';
        const healthResponse = await fetch(`${apiBase}/health`);
        if (healthResponse.ok) {
          const health = await healthResponse.json();
          if (health.persistence === false || health.database_url === false) {
            if (process.env.NODE_ENV === 'development') {
              console.warn('[Maestra] Conversation polling disabled: persistence unavailable');
            }
            return;
          }
        }
      } catch {
        // Assume persistence available if health check fails
      }

      pollInterval = setInterval(async () => {
        try {
          const apiBase = localStorage.getItem('maestra_api_override') || 'http://localhost:8825';
          const response = await fetch(`${apiBase}/api/maestra/conversation/${conversationId}`);
          if (!response.ok) return;
        
          const data = await response.json();
          if (data.turns && data.turns.length > messages.length) {
            // New turns arrived; sync them
            const newMessages = data.turns.map((turn: any) => ({
              id: turn.turn_id,
              role: turn.type === 'user_query' ? 'user' as const : 'assistant' as const,
              content: turn.content,
              timestamp: turn.timestamp,
            }));
            setMessages((prev) => {
              const serverIds = new Set(newMessages.map((m: Message) => m.id));
              const localOnly = prev.filter((m: Message) => !serverIds.has(m.id));
              return [...newMessages, ...localOnly];
            });
          }
        } catch (error) {
          // Silently fail; backend might be offline
        }
      }, 1000);
    };

    initPolling();

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [conversationId, messages.length]);

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
      setIsStreaming(false); // STEP 3: Kill typing state
    } catch (error) {
      breadcrumbTrail.addError('Message failed', { 
        error: error instanceof Error ? error.message : String(error) 
      });
      console.error('Error sending message:', error);
      setIsStreaming(false); // STEP 3: Kill typing state on error
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
      const result = await webAdapter.capture(payload, conversationId);
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
  }, [modeMatch, conversationId]);

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
        systemMode={latestSystemMode}
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

      <DebugPanel />

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
