/**
 * Extension Content Script
 * Injected into every page; handles UI overlay and page context extraction.
 */

interface PageContext {
  url: string;
  title: string;
  selection?: string;
}

interface PageSnapshot extends PageContext {
  domain: string;
  timestamp: string;
  visible_text?: string;
}

let overlayOpen = false;
let snapshotTimer: number | null = null;
let sessionId: string;
let messages: { role: 'user' | 'assistant'; content: string; timestamp: string }[] = [];

function getOrCreateSessionId(): string {
  // Check for shared session_id override (e.g., from query param or localStorage)
  const sharedSessionId = sessionStorage.getItem('maestra_shared_session_id');
  if (sharedSessionId) {
    return sharedSessionId;
  }
  
  // Fall back to domain-scoped session_id
  const domain = window.location.hostname;
  const storageKey = `maestra_session_${domain}`;
  let id = sessionStorage.getItem(storageKey);
  if (!id) {
    id = `ext_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem(storageKey, id);
  }
  return id;
}

sessionId = getOrCreateSessionId();

// Poll conversation feed every 1s to sync with other surfaces
function pollConversationFeed() {
  const apiBase = 'http://localhost:8825';
  fetch(`${apiBase}/api/maestra/conversation/${sessionId}`)
    .then(r => r.json())
    .then(data => {
      if (data.turns && data.turns.length > messages.length) {
        // New turns arrived; update messages array
        messages = data.turns.map((turn: any) => ({
          role: turn.type === 'user_query' ? 'user' : 'assistant',
          content: turn.content,
          timestamp: turn.timestamp
        }));
        // Trigger UI update if overlay is open
        if (overlayOpen) {
          const container = document.getElementById('maestra-messages');
          if (container) {
            renderMessages(container);
          }
        }
      }
    })
    .catch(() => {
      // Silently fail; backend might be offline
    });
}

// Start polling if overlay is open
let pollInterval: number | null = null;

// Listen for messages from background
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'TOGGLE_OVERLAY') {
    overlayOpen ? closeOverlay() : openOverlay();
    sendResponse({ success: true });
  }
});

function getPageContext(): PageContext {
  return {
    url: window.location.href,
    title: document.title,
    selection: window.getSelection()?.toString() || undefined,
  };
}

function getVisibleTextSnapshot(maxChars: number): string {
  try {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const candidates = Array.from(document.querySelectorAll('p, li, h1, h2, h3, h4, pre, code, article, section, main')) as HTMLElement[];

    const parts: string[] = [];
    for (const el of candidates) {
      const rect = el.getBoundingClientRect();
      const intersects = rect.bottom > 0 && rect.right > 0 && rect.top < vh && rect.left < vw;
      if (!intersects) continue;
      const txt = (el.innerText || '').trim();
      if (!txt) continue;
      parts.push(txt);
      if (parts.join('\n\n').length >= maxChars) break;
    }

    const combined = parts.join('\n\n').replace(/\n{3,}/g, '\n\n');
    return combined.slice(0, maxChars);
  } catch {
    return '';
  }
}

function buildSnapshot(): PageSnapshot {
  const ctx = getPageContext();
  return {
    url: ctx.url,
    title: ctx.title,
    domain: window.location.hostname,
    selection: ctx.selection,
    timestamp: new Date().toISOString(),
    visible_text: getVisibleTextSnapshot(4000),
  };
}

function renderMessages(container: HTMLElement) {
  container.innerHTML = '';
  for (const m of messages.slice(-30)) {
    const bubble = document.createElement('div');
    bubble.style.cssText = [
      'max-width: 100%',
      'white-space: pre-wrap',
      'word-break: break-word',
      'padding: 10px 12px',
      'border-radius: 10px',
      'font-size: 13px',
      'line-height: 1.35',
      m.role === 'user' ? 'background: #115e59; margin-left: 48px; color: #fff;' : 'background: #27272a; margin-right: 48px; color: #e4e4e7;'
    ].join(' ');
    bubble.textContent = m.content;
    container.appendChild(bubble);

    const spacer = document.createElement('div');
    spacer.style.height = '10px';
    container.appendChild(spacer);
  }
  container.scrollTop = container.scrollHeight;
}

function openOverlay() {
  if (overlayOpen) return;
  overlayOpen = true;

  // Create container for React app
  const container = document.createElement('div');
  container.id = 'maestra-overlay-root';
  container.style.cssText = `
    position: fixed;
    top: 0;
    right: 0;
    width: 400px;
    height: 100vh;
    z-index: 999999;
    box-shadow: -2px 0 8px rgba(0,0,0,0.15);
  `;

  document.body.appendChild(container);

  container.innerHTML = `
    <div style="
      width: 100%;
      height: 100%;
      background: #18181b;
      color: #e4e4e7;
      display: flex;
      flex-direction: column;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #27272a;">
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="width: 28px; height: 28px; border-radius: 8px; background: #02AD9D; display:flex; align-items:center; justify-content:center;">
            <div style="width: 14px; height: 14px; border: 2px solid #fff; clip-path: polygon(50% 0%, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%);"></div>
          </div>
          <div style="font-weight: 600; font-size: 14px;">maestra</div>
        </div>
        <button id="maestra-close" style="
          background: none;
          border: none;
          color: #a1a1aa;
          cursor: pointer;
          font-size: 18px;
          padding: 0;
          line-height: 1;
        ">×</button>
      </div>

      <div style="padding: 10px 16px; border-bottom: 1px solid #27272a;">
        <div id="maestra-context" style="font-size: 11px; color: #a1a1aa; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"></div>
      </div>

      <div id="maestra-messages" style="flex: 1; overflow-y: auto; padding: 16px;">
        <div style="color:#71717a; font-size: 13px;">Ask based on what you're looking at.</div>
      </div>

      <div style="padding: 12px 16px; border-top: 1px solid #27272a; display:flex; gap: 8px;">
        <input id="maestra-input" type="text" placeholder="Type a message..." style="
          flex: 1;
          background: #09090b;
          color: #e4e4e7;
          border: 1px solid #27272a;
          border-radius: 8px;
          padding: 10px 12px;
          outline: none;
          font-size: 13px;
        " />
        <button id="maestra-send" style="
          background: #02AD9D;
          color: #fff;
          border: none;
          border-radius: 8px;
          padding: 10px 12px;
          cursor: pointer;
          font-weight: 600;
        ">Send</button>
      </div>
    </div>
  `;

  const contextEl = document.getElementById('maestra-context') as HTMLElement | null;
  const messagesEl = document.getElementById('maestra-messages') as HTMLElement | null;
  const inputEl = document.getElementById('maestra-input') as HTMLInputElement | null;
  const sendEl = document.getElementById('maestra-send') as HTMLButtonElement | null;

  const refreshSnapshot = () => {
    const snap = buildSnapshot();
    if (contextEl) {
      contextEl.textContent = `${snap.domain} — ${snap.title}`;
    }
    return snap;
  };

  const sendMessage = async () => {
    if (!inputEl || !messagesEl || !sendEl) return;
    const text = (inputEl.value || '').trim();
    if (!text) return;
    inputEl.value = '';

    const snap = refreshSnapshot();
    const userTurn = { role: 'user' as const, content: text, timestamp: new Date().toISOString() };
    messages.push(userTurn);
    renderMessages(messagesEl);

    sendEl.disabled = true;
    sendEl.style.opacity = '0.7';

    const conversationHistory = messages.slice(-10).map((m) => ({ role: m.role, content: m.content }));
    const clientContext = {
      page_snapshot: snap,
      selection: snap.selection,
      visible_text: snap.visible_text,
      conversation_history: conversationHistory,
    };

    chrome.runtime.sendMessage(
      {
        type: 'SEND_MESSAGE',
        payload: {
          session_id: sessionId,
          message: text,
          mode: 'quick',
          client_context: clientContext,
        },
      },
      (resp) => {
        const err = chrome.runtime.lastError;
        if (err) {
          messages.push({ role: 'assistant', content: `Error: ${err.message}`, timestamp: new Date().toISOString() });
          renderMessages(messagesEl);
        } else if (resp?.error) {
          messages.push({ role: 'assistant', content: `Error: ${resp.error}`, timestamp: new Date().toISOString() });
          renderMessages(messagesEl);
        } else {
          messages.push({ role: 'assistant', content: resp?.answer || '', timestamp: new Date().toISOString() });
          renderMessages(messagesEl);
        }
        sendEl.disabled = false;
        sendEl.style.opacity = '1';
      }
    );
  };

  document.getElementById('maestra-close')?.addEventListener('click', closeOverlay);
  sendEl?.addEventListener('click', () => void sendMessage());
  inputEl?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      void sendMessage();
    }
  });

  refreshSnapshot();
  snapshotTimer = window.setInterval(() => {
    if (!overlayOpen) return;
    refreshSnapshot();
  }, 1000);

  // Start polling conversation feed for real-time sync
  if (pollInterval) window.clearInterval(pollInterval);
  pollInterval = window.setInterval(() => {
    if (overlayOpen) {
      pollConversationFeed();
    }
  }, 1000);
}

function closeOverlay() {
  overlayOpen = false;
  if (snapshotTimer) {
    window.clearInterval(snapshotTimer);
    snapshotTimer = null;
  }
  if (pollInterval) {
    window.clearInterval(pollInterval);
    pollInterval = null;
  }
  const container = document.getElementById('maestra-overlay-root');
  if (container) {
    container.remove();
  }
}
