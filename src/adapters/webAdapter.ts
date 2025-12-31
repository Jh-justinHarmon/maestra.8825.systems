import { SCHEMA_VERSION } from './types';
import type { Adapter, Response, ContextResult, CaptureResult, Context } from './types';

// Maestra Backend API endpoint
// In production: https://maestra-backend-8825-systems.fly.dev
// In development: http://localhost:8000
// Can be overridden at runtime via localStorage (set by Header debug panel)
const getApiBase = () => {
  // Check for runtime override first (set by debug panel)
  if (typeof window !== 'undefined') {
    const override = localStorage.getItem('maestra_api_override');
    if (override) {
      return override;
    }
  }
  // Fall back to env var or production
  return (import.meta as any)?.env?.VITE_MAESTRA_API ||
    'https://maestra-backend-8825-systems.fly.dev';
};

const API_BASE = getApiBase();

// Local companion service (runs on user's machine)
const LOCAL_COMPANION_BASE = 'http://localhost:8826';

const generateId = () => Math.random().toString(36).substring(2, 9);

// Session state for handshake
let sessionHandshake: { jwt?: string; libraryId?: string; capabilities?: string[] } = {};

/**
 * Attempt handshake with local companion (non-blocking, 1s timeout)
 */
async function attemptHandshake(): Promise<{ jwt?: string; libraryId?: string; capabilities?: string[] } | null> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1000); // 1 second timeout
    
    const response = await fetch(`${LOCAL_COMPANION_BASE}/handshake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        version: '1',
        user_agent: 'maestra-ui/1.0'
      }),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json();
    return {
      jwt: data.jwt,
      libraryId: data.library_id,
      capabilities: data.capabilities
    };
  } catch (error) {
    // Timeout or connection error - local companion unavailable
    return null;
  }
}

/**
 * Register session capabilities with backend
 */
async function registerSessionCapabilities(
  sessionId: string,
  handshake: { jwt?: string; libraryId?: string; capabilities?: string[] }
): Promise<void> {
  if (!handshake.jwt || !handshake.libraryId) {
    return; // No handshake data to register
  }
  
  try {
    await fetch(`${API_BASE}/api/maestra/session/${sessionId}/capabilities`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        library_id: handshake.libraryId,
        jwt: handshake.jwt,
        capabilities: handshake.capabilities || []
      })
    });
  } catch (error) {
    // Silently fail - session continues without enhanced features
    console.debug('Failed to register session capabilities:', error);
  }
}

export const webAdapter: Adapter = {
  async sendMessage(conversationId: string, message: string, context?: Context, messages?: any[]): Promise<Response> {
    try {
      // Fire parallel requests: handshake + backend (non-blocking)
      const handshakePromise = attemptHandshake();

      // Best-effort local context fetch (fast timeout so we don't block UX)
      const localContextPromise = (async () => {
        try {
          const handshake = await handshakePromise;
          if (!handshake?.capabilities?.includes('context_for_query')) {
            return null;
          }

          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 500);

          const response = await fetch(
            `${LOCAL_COMPANION_BASE}/context-for-query?q=${encodeURIComponent(message)}`,
            { signal: controller.signal }
          );

          clearTimeout(timeoutId);

          if (!response.ok) {
            return null;
          }

          const data = await response.json();
          return {
            summary: data.summary,
            relevant: data.relevant_k_ids,
            selection: context?.selection,
          };
        } catch (error) {
          return null;
        }
      })();

      const localContextTimeout = new Promise<null>((resolve) => {
        setTimeout(() => resolve(null), 600);
      });

      const localContext = await Promise.race([localContextPromise, localContextTimeout]);

      // Build conversation history (last 5 messages for context)
      const conversationHistory = messages
        ? messages.slice(-5).map((msg: any) => ({
            role: msg.role || (msg.isUser ? 'user' : 'assistant'),
            content: msg.content || msg.text || msg.answer,
          }))
        : [];

      const fallbackContext = context?.selection ? { selection: context.selection } : null;
      const clientContext = localContext || fallbackContext;
      
      // Merge conversation history into client context
      const enrichedContext = clientContext ? { ...clientContext, conversation_history: conversationHistory } : { conversation_history: conversationHistory };
      
      const backendPromise = fetch(`${API_BASE}/api/maestra/advisor/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: conversationId,
          question: message,
          mode: 'quick',
          context_hints: context?.selection ? ['selection'] : [],
          client_context: enrichedContext,
        }),
      });
      
      // Wait for backend response (required)
      const response = await backendPromise;
      
      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Register handshake in background (non-blocking)
      handshakePromise.then(handshake => {
        if (handshake) {
          sessionHandshake = handshake;
          registerSessionCapabilities(conversationId, handshake);
        }
      });
      
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
      // If we have local companion capabilities, try to get context from there first
      if (sessionHandshake.capabilities?.includes('context_for_query')) {
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 500);
          
          const response = await fetch(
            `${LOCAL_COMPANION_BASE}/context-for-query?q=${encodeURIComponent(query)}`,
            { signal: controller.signal }
          );
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const data = await response.json();
            return {
              schema_version: SCHEMA_VERSION,
              relevantDocs: data.relevant_k_ids.map((id: string) => ({
                id,
                title: id,
                excerpt: data.summary
              })),
              suggestions: [],
            };
          }
        } catch (error) {
          // Fall through to empty context
        }
      }
      
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
