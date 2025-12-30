import { SCHEMA_VERSION } from './types';
import type { Adapter, Response, ContextResult, CaptureResult, Context } from './types';

// Maestra Backend API endpoint
// In production: https://maestra-backend-8825-systems.fly.dev
// In development: http://localhost:8000
const API_BASE = process.env.REACT_APP_MAESTRA_API || 'https://maestra-backend-8825-systems.fly.dev';

const generateId = () => Math.random().toString(36).substring(2, 9);

export const webAdapter: Adapter = {
  async sendMessage(conversationId: string, message: string, context?: Context): Promise<Response> {
    try {
      const response = await fetch(`${API_BASE}/api/maestra/advisor/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: conversationId,
          question: message,
          mode: 'quick',
          context_hints: context?.selection ? ['selection'] : [],
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      return {
        schema_version: SCHEMA_VERSION,
        message: {
          id: data.trace_id || generateId(),
          role: 'assistant',
          content: data.answer,
          timestamp: new Date().toISOString(),
        },
      };
    } catch (error) {
      throw new Error(`Failed to send message: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  async prefetchContext(query: string): Promise<ContextResult> {
    try {
      // For now, return empty context as the backend doesn't have a prefetch endpoint
      // This could be enhanced to call /api/maestra/context/{session_id} if needed
      return {
        schema_version: SCHEMA_VERSION,
        relevantDocs: [],
        suggestions: [],
      };
    } catch (error) {
      throw new Error(`Failed to prefetch context: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  async capture(payload: { content: string; context?: Context }): Promise<CaptureResult> {
    try {
      // Capture is handled by the backend's advisor/ask endpoint
      // The content becomes the question, and we mark it as a capture
      const response = await fetch(`${API_BASE}/api/maestra/advisor/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: `capture_${generateId()}`,
          question: payload.content || (payload.context?.selection || 'Capture'),
          mode: 'quick',
          context_hints: ['capture'],
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }
      
      const data = await response.json();
      const words = payload.content.split(' ').slice(0, 5).join(' ');
      
      return {
        schema_version: SCHEMA_VERSION,
        id: data.trace_id || generateId(),
        title: `Capture: ${words || 'Selection'}`,
        summary: payload.content.substring(0, 100) || payload.context?.selection?.substring(0, 100) || '',
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      throw new Error(`Failed to capture: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },
};
