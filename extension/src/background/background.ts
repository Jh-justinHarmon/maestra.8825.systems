/**
 * Extension Background Service Worker
 * Handles communication between content script and backend API.
 */

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

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message: BackgroundMessage, sender, sendResponse) => {
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
    // TODO: Send to backend API
    // const response = await fetch('https://api.8825.systems/capture', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(payload),
    // });
    // const result = await response.json();
    
    console.log('[Background] Capture:', payload);
    sendResponse({ success: true, id: 'cap_' + Date.now() });
  } catch (error) {
    sendResponse({ error: (error as Error).message });
  }
}

async function handleSendMessage(payload: unknown, sendResponse: (response: unknown) => void) {
  try {
    // TODO: Send to backend API
    console.log('[Background] Send message:', payload);
    sendResponse({ success: true });
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
chrome.action.onClicked.addListener((tab) => {
  if (tab.id) {
    chrome.tabs.sendMessage(tab.id, { type: 'TOGGLE_OVERLAY' });
  }
});
