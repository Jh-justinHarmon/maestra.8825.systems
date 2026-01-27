/// <reference types="chrome" />
/**
 * Extension Background Service Worker
 * Handles communication between content script and backend API.
 */

import { getOrCreateDeviceId } from '../lib/deviceId';

// Session state
let currentSessionId: string | null = null;
let deviceId: string | null = null;

interface CapturePayload {
  schema_version: string;
  url: string;
  title: string;
  selection?: string;
  timestamp: string;
}

interface BackgroundMessage {
  type: 'CAPTURE' | 'SEND_MESSAGE' | 'GET_CONTEXT';
  payload?: unknown;
}

interface MessageSender {
  url?: string;
  tab?: { id?: number };
}

interface AdvisorAskPayload {
  session_id: string;
  message: string;
  mode?: 'quick' | 'deep';
  client_context?: Record<string, unknown>;
}

const BACKEND_URL = 'http://localhost:8825';

async function getBackendUrl(): Promise<string> {
  const stored = await chrome.storage.local.get('maestra_backend_url');
  return stored.maestra_backend_url || BACKEND_URL;
}

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
    const backendUrl = await getBackendUrl();
    const response = await fetch(`${backendUrl}/api/maestra/session/handshake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: deviceId,
        surface: 'browser_extension',
        user_id: 'anonymous'
      })
    });
    
    if (!response.ok) {
      throw new Error(`Session handshake failed: ${response.status}`);
    }
    
    const data = await response.json();
    const sessionId = data.session_id as string;
    currentSessionId = sessionId;
    
    console.log(`[SESSION] device_id=${deviceId}, session_id=${sessionId}, surface=browser_extension, is_new=${data.is_new_session}`);
    
    return sessionId;
  } catch (error) {
    console.error('[SESSION] Handshake failed, using fallback session ID', error);
    // Fallback to generated session ID
    currentSessionId = `fallback_${Date.now()}`;
    return currentSessionId;
  }
}

// Perform handshake on extension startup
performSessionHandshake().catch(err => {
  console.error('[SESSION] Startup handshake failed:', err);
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message: BackgroundMessage, sender: MessageSender, sendResponse: (response: unknown) => void) => {
  switch (message.type) {
    case 'CAPTURE':
      handleCapture(message.payload as CapturePayload, sendResponse);
      break;
    case 'SEND_MESSAGE':
      handleSendMessage(message.payload, sendResponse);
      break;
    case 'GET_CONTEXT':
      handleGetContext(sender.url, sendResponse);
      break;
    default:
      sendResponse({ error: 'Unknown message type' });
  }
  return true; // Keep channel open for async response
});

async function handleCapture(payload: CapturePayload, sendResponse: (response: unknown) => void) {
  try {
    const backendUrl = await getBackendUrl();
    const response = await fetch(`${backendUrl}/api/maestra/capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('[Background] Capture success:', result);
    sendResponse({ success: true, ...result });
  } catch (error) {
    console.error('[Background] Capture error:', error);
    sendResponse({ error: (error as Error).message });
  }
}

async function handleSendMessage(payload: any, sendResponse: (response: any) => void) {
  try {
    // Get session ID from handshake
    const sessionId = await performSessionHandshake();
    
    const { message, mode, client_context } = payload;
    
    const apiBase = 'http://localhost:8825';
    console.log('[Maestra Extension] Using backend:', apiBase);
    console.log(`[ADVISOR_CALL] session_id=${sessionId}, device_id=${deviceId}, surface=browser_extension`);

    const response = await fetch(`${apiBase}/api/maestra/advisor/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        mode,
        client_context,
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    sendResponse({
      success: true,
      answer: data.answer,
      trace_id: data.trace_id,
      sources: data.sources || [],
    });
  } catch (error) {
    sendResponse({ error: (error as Error).message });
  }
}

async function handleGetContext(url: string | undefined, sendResponse: (response: unknown) => void) {
  try {
    sendResponse({
      url: url || '',
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    sendResponse({ error: (error as Error).message });
  }
}

// Handle extension icon click
function isSupportedTabUrl(url: string | undefined): boolean {
  if (!url) return false;
  return url.startsWith('http://') || url.startsWith('https://');
}

function injectContentScript(tabId: number): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      chrome.scripting.executeScript(
        {
          target: { tabId },
          files: ['content/content.js'],
        },
        () => {
          const err = chrome.runtime.lastError;
          if (err) {
            reject(new Error(err.message));
            return;
          }
          resolve();
        }
      );
    } catch (e) {
      reject(e);
    }
  });
}

function sendToTab(tabId: number, message: unknown): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      chrome.tabs.sendMessage(tabId, message, () => {
        const err = chrome.runtime.lastError;
        if (err) {
          reject(new Error(err.message));
          return;
        }
        resolve();
      });
    } catch (e) {
      reject(e);
    }
  });
}

async function toggleOverlay(tab: chrome.tabs.Tab) {
  if (!tab.id) return;
  if (!isSupportedTabUrl(tab.url)) {
    console.warn('[Background] Tab URL not supported for overlay:', tab.url);
    return;
  }

  try {
    await sendToTab(tab.id, { type: 'TOGGLE_OVERLAY' });
  } catch (e) {
    // Most common case: content script not present yet.
    console.info('[Background] No content receiver, injecting content script and retrying...');
    try {
      await injectContentScript(tab.id);
      await sendToTab(tab.id, { type: 'TOGGLE_OVERLAY' });
    } catch (inner) {
      console.error('[Background] Failed to inject/toggle overlay:', inner);
    }
  }
}

chrome.action.onClicked.addListener((tab: chrome.tabs.Tab) => {
  void toggleOverlay(tab);
});
