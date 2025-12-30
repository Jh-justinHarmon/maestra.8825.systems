/**
 * Extension Content Script
 * Injected into every page; handles UI overlay and page context extraction.
 */

interface PageContext {
  url: string;
  title: string;
  selection?: string;
}

let overlayOpen = false;

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

  // TODO: Mount React compact card here
  // For now, show placeholder
  container.innerHTML = `
    <div style="
      width: 100%;
      height: 100%;
      background: #18181b;
      color: #e4e4e7;
      display: flex;
      flex-direction: column;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h2 style="margin: 0; font-size: 18px; font-weight: 600;">Maestra</h2>
        <button id="maestra-close" style="
          background: none;
          border: none;
          color: #a1a1aa;
          cursor: pointer;
          font-size: 20px;
          padding: 0;
        ">×</button>
      </div>
      <div style="flex: 1; overflow-y: auto; margin-bottom: 16px;">
        <p style="color: #71717a; font-size: 14px;">Compact card UI coming soon...</p>
      </div>
      <button id="maestra-capture" style="
        width: 100%;
        padding: 8px 12px;
        background: #2563eb;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-weight: 500;
      ">Capture</button>
    </div>
  `;

  // Close button handler
  document.getElementById('maestra-close')?.addEventListener('click', closeOverlay);

  // Capture button handler
  document.getElementById('maestra-capture')?.addEventListener('click', () => {
    const context = getPageContext();
    chrome.runtime.sendMessage({
      type: 'CAPTURE',
      payload: {
        schema_version: '1',
        url: context.url,
        title: context.title,
        selection: context.selection,
        timestamp: new Date().toISOString(),
      },
    });
  });
}

function closeOverlay() {
  overlayOpen = false;
  const container = document.getElementById('maestra-overlay-root');
  if (container) {
    container.remove();
  }
}
