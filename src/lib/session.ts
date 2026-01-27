/**
 * Session Management - Single Source of Truth
 * 
 * Ensures session_id is:
 * - Generated ONCE
 * - Stored in localStorage
 * - Reused for ALL requests (auth handshake, maestra core, etc.)
 */

const SESSION_ID_KEY = 'maestra_session_id';

/**
 * Generate a cryptographically random session ID
 */
function generateSessionId(): string {
  // Use crypto.randomUUID if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  
  // Fallback: generate random hex string
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Get or create session ID (single source of truth)
 * 
 * Priority:
 * 1. Query param ?session_id=xxx (for cross-surface sync)
 * 2. localStorage (persisted session)
 * 3. Generate new and store
 */
export function getOrCreateSessionId(): string {
  // Priority 1: Query param (for explicit session sharing)
  const params = new URLSearchParams(window.location.search);
  const querySessionId = params.get('session_id');
  if (querySessionId) {
    // Store it for future use
    localStorage.setItem(SESSION_ID_KEY, querySessionId);
    console.log('[Session] Using session_id from query param:', querySessionId);
    return querySessionId;
  }
  
  // Priority 2: localStorage (existing session)
  const storedSessionId = localStorage.getItem(SESSION_ID_KEY);
  if (storedSessionId) {
    console.log('[Session] Using stored session_id:', storedSessionId);
    return storedSessionId;
  }
  
  // Priority 3: Generate new session
  const newSessionId = generateSessionId();
  localStorage.setItem(SESSION_ID_KEY, newSessionId);
  console.log('[Session] Generated new session_id:', newSessionId);
  return newSessionId;
}

/**
 * Clear session (for logout or reset)
 */
export function clearSession(): void {
  localStorage.removeItem(SESSION_ID_KEY);
  console.log('[Session] Cleared session_id');
}

/**
 * Get current session ID (without creating new one)
 */
export function getCurrentSessionId(): string | null {
  return localStorage.getItem(SESSION_ID_KEY);
}
