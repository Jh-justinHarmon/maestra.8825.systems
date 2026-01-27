import { SCHEMA_VERSION } from './types';
import type { Adapter, Response, ContextResult, CaptureResult, Context } from './types';
import { getOrCreateDeviceId } from '../lib/deviceId';

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

// Track quad-core activation (persists for session)
let quadCoreActivated = false;
let responsesWithoutPersonalMemory = 0;

// Session state
let currentSessionId: string | null = null;
let deviceId: string | null = null;

// Export for UI consumption
export const getConnectionMode = (): ConnectionMode => connectionState.mode;
export const getConnectionState = (): ConnectionState => ({ ...connectionState });

/**
 * Perform session handshake to get or create session
 */
async function performSessionHandshake(): Promise<string> {
  // Return cached session if available
  if (currentSessionId) {
    return currentSessionId;
  }
  
  // Get or create device ID
  if (!deviceId) {
    deviceId = await getOrCreateDeviceId();
  }
  
  try {
    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/api/maestra/session/handshake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: deviceId,
        surface: 'web_app',
        user_id: 'anonymous'
      })
    });
    
    if (!response.ok) {
      throw new Error(`Session handshake failed: ${response.status}`);
    }
    
    const data = await response.json();
    const sessionId = data.session_id as string;
    currentSessionId = sessionId;
    
    console.log(`[SESSION] device_id=${deviceId}, session_id=${sessionId}, surface=web_app, is_new=${data.is_new_session}`);
    
    return sessionId;
  } catch (error) {
    console.error('[SESSION] Handshake failed, using fallback session ID', error);
    // Fallback to generated session ID
    currentSessionId = `fallback_${Date.now()}`;
    return currentSessionId;
  }
}

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
  if (now - connectionState.lastHealthCheck < 5000) return;
  connectionState.lastHealthCheck = now;

  const localHealthy = await healthCheck('http://localhost:8825', 1000);

  if (localHealthy) {
    // DEV-ONLY: Check /debug/session for auth state
    if (process.env.NODE_ENV === 'development') {
      try {
        const sessionId = localStorage.getItem('maestra_session_id');
        if (sessionId) {
          const res = await fetch(`http://localhost:8825/debug/session/${sessionId}`);
          if (res.ok) {
            const debug = await res.json();

            if (
              debug.router?.authenticated === true &&
              debug.router?.mode === 'system_plus_personal'
            ) {
              const wasQuadCore = connectionState.mode === 'quad-core';
              connectionState.mode = 'quad-core';
              connectionState.apiBase = 'http://localhost:8825';
              connectionState.localBackendAvailable = true;
              connectionState.sidecarAvailable = false;
              
              if (!wasQuadCore) {
                console.log('[Maestra] Quad-Core ACTIVE (authenticated + personal memory)');
              }
              return;
            }
          }
        }
      } catch {
        // fall through
      }
    }

    connectionState.mode = 'local';
    connectionState.apiBase = 'http://localhost:8825';
    connectionState.localBackendAvailable = true;
    connectionState.sidecarAvailable = false;
    console.log('[Maestra] Local backend only');
    return;
  }

  connectionState.mode = 'cloud-only';
  connectionState.apiBase = 'https://maestra-backend-8825-systems.fly.dev';
  connectionState.localBackendAvailable = false;
  connectionState.sidecarAvailable = false;
  console.log('[Maestra] Cloud only');
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
    const apiBase = await getApiBase();
    await fetch(`${apiBase}/api/maestra/session/${sessionId}/capabilities`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
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
      // Perform session handshake on first message to get session_id
      const sessionId = await performSessionHandshake();
      
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
      
      const apiBase = await getApiBase();
      const backendPromise = fetch(`${apiBase}/api/maestra/advisor/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
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
      
      // PRODUCTION: Detect quad-core from real response
      const sources = data.sources || [];
      const hasPersonalMemory = sources.some((s: string) => s.startsWith('personal:'));
      const isSystemPlusPersonal = data.mode === 'system_plus_personal';
      
      if ((hasPersonalMemory || isSystemPlusPersonal) && !quadCoreActivated) {
        quadCoreActivated = true;
        connectionState.mode = 'quad-core';
        responsesWithoutPersonalMemory = 0;
        console.log('[Maestra] Quad-Core ACTIVE (detected from response)');
      } else if (quadCoreActivated && !hasPersonalMemory) {
        responsesWithoutPersonalMemory++;
        
        // PROD-SAFE ASSERTION: Warn if quad-core active but no personal memory for >3 responses
        if (responsesWithoutPersonalMemory > 3) {
          console.warn('[Maestra] Quad-Core active but no personal memory detected in last 3+ responses');
        }
      } else if (quadCoreActivated && hasPersonalMemory) {
        responsesWithoutPersonalMemory = 0;
      }
      
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
          sources: data.sources || [],
          mode: data.mode,
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

  async capture(payload: { content: string; context?: Context }, sessionId: string): Promise<CaptureResult> {
    try {
      // Capture is handled by the backend's advisor/ask endpoint
      // The content becomes the question, and we mark it as a capture
      const response = await fetch(`${API_BASE}/api/maestra/advisor/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,  // Use same session_id as other requests
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
