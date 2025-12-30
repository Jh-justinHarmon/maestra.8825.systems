import type { Adapter, Response, ContextResult, CaptureResult, Context } from './types';

const API_BASE = '/api';

export const webAdapter: Adapter = {
  async sendMessage(conversationId: string, message: string, context?: Context): Promise<Response> {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversationId, message, context }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    
    return response.json();
  },

  async prefetchContext(query: string): Promise<ContextResult> {
    const response = await fetch(`${API_BASE}/context?q=${encodeURIComponent(query)}`);
    
    if (!response.ok) {
      throw new Error('Failed to prefetch context');
    }
    
    return response.json();
  },

  async capture(payload: { content: string; context?: Context }): Promise<CaptureResult> {
    const response = await fetch(`${API_BASE}/capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) {
      throw new Error('Failed to capture');
    }
    
    return response.json();
  },
};
