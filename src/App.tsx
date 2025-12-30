import { useState, useCallback } from 'react';
import { MaestraCard, Header, PinsDrawer } from './components';
import { mockAdapter } from './adapters';
import type { Message, Context, CaptureResult } from './adapters/types';

const generateId = () => Math.random().toString(36).substring(2, 9);

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pins, setPins] = useState<CaptureResult[]>([]);
  const [isPinsOpen, setIsPinsOpen] = useState(false);
  const conversationId = 'main';

  const handleSendMessage = useCallback(async (content: string, context?: Context) => {
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);

    try {
      const response = await mockAdapter.sendMessage(conversationId, content, context);
      setMessages((prev) => [...prev, response.message]);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  const handleCapture = useCallback(async (payload: { content: string; context?: Context }) => {
    try {
      const result = await mockAdapter.capture(payload);
      setPins((prev) => [result, ...prev]);
      setIsPinsOpen(true);
    } catch (error) {
      console.error('Failed to capture:', error);
    }
  }, []);

  const handleShare = useCallback((capture: CaptureResult) => {
    console.log('Sharing:', capture);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-zinc-900">
      <Header 
        onTogglePins={() => setIsPinsOpen(!isPinsOpen)} 
        pinsCount={pins.length} 
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

export default App;
