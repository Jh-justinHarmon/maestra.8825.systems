// UI Thread - Reasoning surface
// Communicates with Maestra backend and Figma plugin main thread

// 🔴 DOGFOOD MODE - Quiet but alive
const DOGFOOD_MODE = true;

import type { 
  UIToPluginMessage, 
  PluginToUIMessage 
} from '../types';

import { 
  requiresConfirmation, 
  getConfirmationMessage 
} from './guardrails';

import { 
  classifyIntent,
  type IntentClassification 
} from './intentClassifier';

// Local UI state types (not part of reasoning contract)
interface ThreadEntry {
  id: string;
  role: 'user' | 'maestra';
  content: string;
  timestamp: number;
  response_label?: 'observation' | 'hypothesis' | 'recommendation' | 'decision';
}

// Pending confirmation state
interface PendingConfirmation {
  intent: string;
  timestamp: number;
}

// Pending clarification state
interface PendingClarification {
  original_input: string;
  clarifying_question: string;
  timestamp: number;
}

// DOM elements
const threadEl = document.getElementById('messages') as HTMLElement;
const threadContainer = document.getElementById('messages-container') as HTMLElement;
const intentInput = document.getElementById('message-input') as HTMLTextAreaElement;
const sendBtn = document.getElementById('send-btn') as HTMLButtonElement;
const threadNameEl = document.getElementById('thread-name') as HTMLElement;
const debugLog = document.getElementById('debug-log') as HTMLElement;

// Confirmation dialog elements
const confirmationDialog = document.getElementById('confirmation-dialog') as HTMLElement;
const confirmationMessage = document.getElementById('confirmation-message') as HTMLElement;
const confirmCancelBtn = document.getElementById('confirm-cancel') as HTMLButtonElement;
const confirmProceedBtn = document.getElementById('confirm-proceed') as HTMLButtonElement;

// Local state (ephemeral, no persistence)
const thread: ThreadEntry[] = [];

// Current streaming thread ID
let currentStreamingThreadId: string | null = null;

// Dogfood timeout tracking
let dogfoodTimeoutId: number | null = null;
let currentThinkingId: string | null = null;

// Pending confirmation state
let pendingConfirmation: PendingConfirmation | null = null;

// Pending clarification state
let pendingClarification: PendingClarification | null = null;

// Active thread metadata
let activeThreadId: string = '';
let activeThreadTitle: string = '';

// Reasoning handler: Plugin -> UI
window.onmessage = (event) => {
  const msg = event.data.pluginMessage as PluginToUIMessage;
  
  // DOGFOOD: No debug logging
  if (!DOGFOOD_MODE) {
    logDebug('🔵 Plugin → UI received');
  }
  
  switch (msg.type) {
    case 'maestra-synthesis':
      handleMaestraSynthesis(msg.content, msg.response_label, msg.request_id);
      updateThreadDisplay(msg.thread_id, msg.thread_title);
      break;
    case 'maestra-stream-start':
      handleStreamStart(msg.threadId);
      break;
    case 'maestra-stream-chunk':
      handleStreamChunk(msg.chunk, msg.threadId);
      break;
  }
};

// UI event handlers
sendBtn.addEventListener('click', () => {
  submitIntent();
});

intentInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitIntent();
  }
});

intentInput.addEventListener('input', () => {
  autoResize();
});

// Confirmation dialog handlers
confirmCancelBtn.addEventListener('click', () => {
  console.log('Cancel button clicked');
  hideConfirmationDialog();
  pendingConfirmation = null;
});

confirmProceedBtn.addEventListener('click', () => {
  console.log('Proceed button clicked');
  if (pendingConfirmation) {
    hideConfirmationDialog();
    // Re-classify intent when user confirms
    const classification = classifyIntent(pendingConfirmation.intent);
    sendIntentToPlugin(pendingConfirmation.intent, classification);
    pendingConfirmation = null;
  }
});

// 🔴 PROMPT 5: Log to debug panel
function logDebug(message: string): void {
  const timestamp = new Date().toLocaleTimeString();
  debugLog.innerHTML += `<div>[${timestamp}] ${message}</div>`;
  debugLog.scrollTop = debugLog.scrollHeight;
}

// Functions
function submitIntent(): void {
  const content = intentInput.value.trim();
  if (!content) return;
  
  // DOGFOOD: No debug logging
  if (!DOGFOOD_MODE) {
    logDebug('🟢 UI → Plugin sent');
  }
  
  // Append user message to UI immediately
  addToThread({
    id: generateId(),
    role: 'user',
    content: content,
    timestamp: Date.now()
  });
  
  // Show thinking indicator
  const thinkingId = generateId();
  currentThinkingId = thinkingId;
  addToThread({
    id: thinkingId,
    role: 'maestra',
    content: '...',
    timestamp: Date.now()
  });
  
  // Start 8-second dogfood timeout
  if (dogfoodTimeoutId) {
    window.clearTimeout(dogfoodTimeoutId);
  }
  dogfoodTimeoutId = window.setTimeout(() => {
    // Remove thinking indicator
    const thinkingEl = threadEl.querySelector(`[data-id="${currentThinkingId}"]`);
    if (thinkingEl) {
      thinkingEl.remove();
    }
    
    // Show canonical failure message - no analysis was performed
    addToThread({
      id: generateId(),
      role: 'maestra',
      content: "Maestra wasn't reachable, so no analysis was performed.",
      timestamp: Date.now()
    });
    
    currentThinkingId = null;
    dogfoodTimeoutId = null;
  }, 8000);
  
  // 🔴 DOGFOOD MODE: Skip guardrails, send observation intent only
  if (DOGFOOD_MODE) {
    sendIntentToPlugin(content, { intent_type: 'observation', intent_label: 'Observation', intent_source: 'declared', is_clear: true, clarifying_question: '' });
    intentInput.value = '';
    autoResize();
    return;
  }
  
  // GUARD 1: Classify intent FIRST
  const classification = classifyIntent(content);
  
  // GUARD 2: If intent unclear, ask clarifying question instead of sending
  if (!classification.is_clear) {
    showClarifyingQuestion(content, classification.clarifying_question);
    intentInput.value = '';
    autoResize();
    return;
  }
  
  // GUARD 3: Check if intent requires confirmation (destructive operation)
  if (requiresConfirmation(content)) {
    pendingConfirmation = {
      intent: content,
      timestamp: Date.now()
    };
    
    showConfirmationDialog(content);
    intentInput.value = '';
    autoResize();
    return;
  }
  
  // Intent is clear and safe - send to plugin with classification
  sendIntentToPlugin(content, classification);
  
  // Clear input
  intentInput.value = '';
  autoResize();
}

function sendIntentToPlugin(content: string, classification: IntentClassification): void {
  // Send to plugin with intent classification
  // Plugin will structure the full AdapterRequest in correct order
  const intent: UIToPluginMessage = { 
    type: 'user-intent',
    content 
  };
  parent.postMessage({ pluginMessage: intent }, '*');
}

function showConfirmationDialog(intent: string): void {
  const confirmationText = getConfirmationMessage(intent);
  confirmationMessage.textContent = confirmationText;
  confirmationDialog.classList.remove('hidden');
}

function hideConfirmationDialog(): void {
  confirmationDialog.classList.add('hidden');
}

function showClarifyingQuestion(originalInput: string, question: string): void {
  // Store pending clarification
  pendingClarification = {
    original_input: originalInput,
    clarifying_question: question,
    timestamp: Date.now()
  };
  
  // Add clarifying question to thread as Maestra message
  addToThread({
    id: generateId(),
    role: 'maestra',
    content: `⚠️ ${question}`,
    timestamp: Date.now()
  });
}

function handleMaestraSynthesis(
  content: string, 
  response_label: 'observation' | 'hypothesis' | 'recommendation' | 'decision',
  request_id?: string
): void {
  // Clear dogfood timeout - response arrived
  if (dogfoodTimeoutId) {
    window.clearTimeout(dogfoodTimeoutId);
    dogfoodTimeoutId = null;
  }
  
  // Remove thinking indicator
  const thinkingEl = threadEl.querySelector(`[data-id="${currentThinkingId}"]`);
  if (thinkingEl) {
    thinkingEl.remove();
  }
  currentThinkingId = null;
  
  // DOGFOOD: Show error inline if content is empty or error message
  if (!content || content.startsWith('Error:')) {
    addToThread({
      id: generateId(),
      role: 'maestra',
      content: "Maestra wasn't reachable, so no analysis was performed.",
      timestamp: Date.now()
    });
    return;
  }
  
  // Connection proof: Log request_id match
  if (request_id) {
    console.log('✅ Round-trip confirmed:', request_id);
  }
  
  addToThread({
    id: generateId(),
    role: 'maestra',
    content,
    timestamp: Date.now()
  });
  
  // Show connection proof (dev-only)
  if (request_id) {
    const proofEl = document.createElement('div');
    proofEl.style.cssText = 'font-size: 9px; color: #10b981; padding: 4px 12px; font-family: monospace;';
    proofEl.textContent = `Connected • request_id: ${request_id}`;
    threadEl.appendChild(proofEl);
  }
}

/**
 * Update thread display with metadata from Maestra
 */
function updateThreadDisplay(threadId: string, threadTitle: string): void {
  // Update active thread metadata
  if (threadId) activeThreadId = threadId;
  if (threadTitle) activeThreadTitle = threadTitle;
  
  // Update UI display
  if (activeThreadTitle) {
    threadNameEl.textContent = activeThreadTitle;
  } else if (activeThreadId) {
    // Show truncated thread ID if no title
    const shortId = activeThreadId.substring(0, 12) + '...';
    threadNameEl.textContent = shortId;
  } else {
    threadNameEl.textContent = 'New Thread';
  }
}

function handleStreamStart(threadId: string): void {
  // Create new empty synthesis entry for streaming
  const entry: ThreadEntry = {
    id: threadId,
    role: 'maestra',
    content: '',
    timestamp: Date.now()
  };
  
  thread.push(entry);
  renderThreadEntry(entry);
  scrollToBottom();
  
  // Track current streaming synthesis
  currentStreamingThreadId = threadId;
}

function handleStreamChunk(threadId: string, chunk: string): void {
  // Find the synthesis entry being streamed
  const entry = thread.find((e: ThreadEntry) => e.id === threadId);
  if (!entry) {
    console.warn('Stream chunk for unknown thread:', threadId);
    return;
  }
  
  // Append chunk to synthesis content
  entry.content += chunk;
  
  // Update the DOM
  const entryEl = threadEl.querySelector(`[data-id="${threadId}"]`);
  if (entryEl) {
    const contentEl = entryEl.querySelector('.message-content');
    if (contentEl) {
      contentEl.textContent = entry.content;
      scrollToBottom();
    }
  }
}

function addToThread(entry: ThreadEntry): void {
  thread.push(entry);
  renderThreadEntry(entry);
  scrollToBottom();
}

function renderThreadEntry(entry: ThreadEntry): void {
  const entryEl = document.createElement('div');
  entryEl.className = `message ${entry.role}`;
  entryEl.setAttribute('data-id', entry.id);
  
  const contentEl = document.createElement('div');
  contentEl.className = 'message-content';
  contentEl.textContent = entry.content;
  
  entryEl.appendChild(contentEl);
  threadEl.appendChild(entryEl);
}

/**
 * Format response label for display
 * Capitalizes and makes human-readable
 */
function formatResponseLabel(label: 'observation' | 'hypothesis' | 'recommendation' | 'decision'): string {
  const labels = {
    observation: '🔍 Observation',
    hypothesis: '💭 Hypothesis',
    recommendation: '💡 Recommendation',
    decision: '✓ Decision'
  };
  return labels[label];
}

function scrollToBottom(): void {
  threadContainer.scrollTop = threadContainer.scrollHeight;
}

function autoResize(): void {
  intentInput.style.height = 'auto';
  intentInput.style.height = Math.min(intentInput.scrollHeight, 120) + 'px';
}

function generateId(): string {
  return `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Initialize
function init(): void {
  threadNameEl.textContent = 'New Thread';
  intentInput.focus();
}

init();
