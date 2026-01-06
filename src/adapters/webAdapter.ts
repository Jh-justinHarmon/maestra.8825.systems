import { SCHEMA_VERSION } from './types';
import type { Adapter, Response, ContextResult, CaptureResult, Context } from './types';

// ============================================================================
// Tri-State Connection Hierarchy
// ============================================================================
// Priority: Quad-Core (Sidecar) → Local Backend → Hosted Backend
// This ensures Maestra always has the best available context

export type ConnectionMode = 'quad-core' | 'local' | 'cloud-only';

interface ConnectionState {
  mode: ConnectionMode;
  apiBase: string;
  sidecarAvailable: boolean;
  localBackendAvailable: boolean;
  lastHealthCheck: number;
  handshakeData?: { jwt?: string; libraryId?: string; capabilities?: string[] };
}

let connectionState: ConnectionState = {
  mode: 'cloud-only',
  apiBase: 'https://maestra-backend-8825-systems.fly.dev',
  sidecarAvailable: false,
  localBackendAvailable: false,
  lastHealthCheck: 0,
};

// Export for UI consumption
export const getConnectionMode = (): ConnectionMode => connectionState.mode;
export const getConnectionState = (): ConnectionState => ({ ...connectionState });

/**
 * Health check with timeout
 */
async function healthCheck(url: string, timeoutMs: number = 1000): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    
    const response = await fetch(`${url}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Determine optimal connection mode by checking services in priority order
 */
async function determineConnectionMode(): Promise<void> {
  const now = Date.now();
  
  // Only check every 5 seconds to avoid hammering services
  if (now - connectionState.lastHealthCheck < 5000) {
    return;
  }
  
  connectionState.lastHealthCheck = now;
  
  // Priority 1: Quad-Core (Sidecar + Handshake)
  const sidecarHealthy = await healthCheck('http://localhost:8826', 1000);
  if (sidecarHealthy) {
    const handshake = await attemptHandshake();
    if (handshake) {
      connectionState.mode = 'quad-core';
      connectionState.apiBase = 'https://maestra-backend-8825-systems.fly.dev';
      connectionState.sidecarAvailable = true;
      connectionState.localBackendAvailable = false;
      connectionState.handshakeData = handshake;
      console.log('[Maestra] Connected: Quad-Core mode');
      return;
    }
  }
  
  connectionState.sidecarAvailable = false;
  
  // Priority 2: Local Backend
  const localHealthy = await healthCheck('http://localhost:8825', 1000);
  if (localHealthy) {
    connectionState.mode = 'local';
    connectionState.apiBase = 'http://localhost:8825';
    connectionState.localBackendAvailable = true;
    connectionState.sidecarAvailable = false;
    console.log('[Maestra] Connected: Local mode');
    return;
  }
  
  connectionState.localBackendAvailable = false;
  
  // Priority 3: Hosted Backend (fallback)
  connectionState.mode = 'cloud-only';
  connectionState.apiBase = 'https://maestra-backend-8825-systems.fly.dev';
  connectionState.sidecarAvailable = false;
  connectionState.localBackendAvailable = false;
  console.log('[Maestra] Connected: Cloud-only mode (limited context)');
}

/**
 * Get API base URL - respects tri-state hierarchy
 */
const getApiBase = async (): Promise<string> => {
  // Check for runtime override first (set by debug panel)
  if (typeof window !== 'undefined') {
    const override = localStorage.getItem('maestra_api_override');
    if (override) {
      console.log('[Maestra] Using override:', override);
      return override;
    }
  }
  
  // Check env var (set at build time)
  const envApi = (import.meta as any)?.env?.VITE_MAESTRA_API;
  if (envApi) {
    console.log('[Maestra] Using VITE_MAESTRA_API:', envApi);
    return envApi;
  }
  
  // Determine optimal connection mode
  await determineConnectionMode();
  return connectionState.apiBase;
};

// Initialize API_BASE asynchronously
let API_BASE = 'https://maestra-backend-8825-systems.fly.dev';
getApiBase().then(base => {
  API_BASE = base;
});

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
      signal: controller.signal,
      mode: 'cors',
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      console.warn(`[Maestra] Handshake failed: ${response.status} ${response.statusText}`);
      return null;
    }
    
    const data = await response.json();
    console.log('[Maestra] Handshake successful:', data.session_id);
    return {
      jwt: data.jwt,
      libraryId: data.library_id,
      capabilities: data.capabilities
    };
  } catch (error) {
    // Timeout or connection error - local companion unavailable
    console.warn('[Maestra] Handshake error:', error instanceof Error ? error.message : String(error));
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
      // Determine optimal connection mode before sending
      await determineConnectionMode();
      
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
