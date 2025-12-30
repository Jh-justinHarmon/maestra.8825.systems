import type { Adapter, Response, ContextResult, CaptureResult, Context } from './types';

const mockResponses = [
  "I understand. Let me help you with that.",
  "That's a great question! Here's what I think...",
  "Based on what you've shared, I'd suggest the following approach.",
  "I can definitely help with that. Here are some options to consider.",
  "Interesting point! Let me elaborate on that.",
];

const generateId = () => Math.random().toString(36).substring(2, 9);

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const mockAdapter: Adapter = {
  async sendMessage(_conversationId: string, message: string, context?: Context): Promise<Response> {
    await delay(800 + Math.random() * 400);
    
    let responseContent = mockResponses[Math.floor(Math.random() * mockResponses.length)];
    
    if (context?.selection) {
      responseContent = `Regarding your selection: "${context.selection.substring(0, 50)}..."\n\n${responseContent}`;
    }
    
    if (message.toLowerCase().includes('hello') || message.toLowerCase().includes('hi')) {
      responseContent = "Hello! I'm Maestra, your AI assistant. How can I help you today?";
    }
    
    return {
      message: {
        id: generateId(),
        role: 'assistant',
        content: responseContent,
        timestamp: new Date(),
      },
    };
  },

  async prefetchContext(query: string): Promise<ContextResult> {
    await delay(200);
    return {
      relevantDocs: [`Document related to: ${query}`],
      suggestions: ['Try asking about...', 'You might also want to...'],
    };
  },

  async capture(payload: { content: string; context?: Context }): Promise<CaptureResult> {
    await delay(300);
    const words = payload.content.split(' ').slice(0, 5).join(' ');
    return {
      id: generateId(),
      title: `Capture: ${words}...`,
      summary: payload.content.substring(0, 100),
      timestamp: new Date(),
    };
  },
};
