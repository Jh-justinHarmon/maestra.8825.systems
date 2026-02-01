// ============================================================
// FIGMA PLUGIN MAIN THREAD - SURFACE ONLY
// ============================================================
// 
// REVIEWER NOTE: This plugin is a THIN CLIENT SURFACE.
// 
// What this plugin does:
// - Displays a reasoning surface (no local intelligence)
// - Reads basic file metadata (name, page, selection)
// - Sends context to external Maestra backend
// - NO writes to design files
// - NO autonomous actions
// - NO local data storage
//
// All intelligence, memory, and decision-making happens in the
// external Maestra system. This plugin is only a communication
// surface with minimal Figma API access.
//
// Figma APIs used:
// - figma.root.name (file name - read-only)
// - figma.currentPage.name (page name - read-only)
// - figma.currentPage.selection (selected nodes - read-only)
// - figma.currentPage.findAll() (FigJam only - read-only)
// - figma.editorType (detect Figma vs FigJam - read-only)
//
// NO write operations. NO file modifications.
// ============================================================

/// <reference types="@figma/plugin-typings" />

// 🔴 DOGFOOD MODE - Quiet but alive
const DOGFOOD_MODE = true;

import type { 
  UIToPluginMessage, 
  PluginToUIMessage,
  SurfaceContext,
  FigmaContext,
  FigJamContext,
  AdapterRequest
} from '../types';

import { sendToMaestra } from '../adapter/networkAdapter';
import { selectRelevantContext } from './contextSelector';

// 🔴 INLINE HTML - Single source of truth (no external files)
const INLINE_HTML = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Maestra Surface</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; color: #f4f4f5; background: #27272a; }
    #app { display: flex; flex-direction: column; height: 100vh; }
    header { padding: 12px 16px; border-bottom: 1px solid #3f3f46; flex-shrink: 0; background: #27272a; }
    header h1 { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
    .thread-info { display: flex; align-items: center; gap: 8px; font-size: 10px; }
    .thread-name { color: #f4f4f5; font-weight: 500; padding: 2px 6px; background: #3f3f46; border-radius: 4px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .memory-indicator { color: #a1a1aa; font-size: 9px; opacity: 0.7; }
    .memory-indicator::before { content: '•'; margin-right: 4px; }
    #messages-container { flex: 1; overflow-y: auto; padding: 16px; background: #27272a; }
    #messages { display: flex; flex-direction: column; gap: 12px; }
    .message { margin-bottom: 16px; display: flex; flex-direction: column; gap: 4px; max-width: 85%; }
    .message.user { align-items: flex-end; margin-left: auto; }
    .message.maestra { align-items: flex-start; margin-right: auto; }
    .message-content { padding: 12px 16px; border-radius: 8px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; }
    .message.user .message-content { background: #3b82f6; color: #ffffff; }
    .message.maestra .message-content { background: #3f3f46; color: #f4f4f5; }
    footer { padding: 16px; border-top: 1px solid #3f3f46; flex-shrink: 0; background: #27272a; }
    .input-container { display: flex; gap: 8px; align-items: flex-end; }
    #message-input { flex: 1; padding: 10px 12px; font-size: 12px; border: 1px solid #3f3f46; border-radius: 8px; background: #3f3f46; color: #f4f4f5; resize: vertical; min-height: 36px; max-height: 120px; font-family: inherit; outline: none; transition: border-color 0.2s, box-shadow 0.2s; }
    #message-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
    #message-input::placeholder { color: #71717a; }
    #send-btn { padding: 0 16px; font-size: 11px; font-weight: 500; border: none; border-radius: 8px; background: #3b82f6; color: #ffffff; cursor: pointer; flex-shrink: 0; height: 36px; transition: background-color 0.2s; }
    #send-btn:hover { background: #2563eb; }
    #send-btn:active { background: #1d4ed8; }
    .confirmation-dialog { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
    .confirmation-dialog.hidden { display: none; }
    .confirmation-content { background: #27272a; border: 1px solid #3f3f46; border-radius: 12px; padding: 24px; max-width: 320px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4); }
    .confirmation-icon { font-size: 32px; text-align: center; margin-bottom: 12px; }
    .confirmation-content h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; text-align: center; color: #f4f4f5; }
    .confirmation-content p { font-size: 12px; line-height: 1.4; color: #a1a1aa; margin-bottom: 20px; text-align: center; }
    .confirmation-actions { display: flex; gap: 8px; }
    .confirmation-actions button { flex: 1; padding: 8px 16px; font-size: 11px; font-weight: 500; border: none; border-radius: 8px; cursor: pointer; height: 32px; transition: background-color 0.2s, opacity 0.2s; }
    .btn-secondary { background: #3f3f46; color: #f4f4f5; }
    .btn-secondary:hover { background: #52525b; }
    .btn-primary { background: #3b82f6; color: #ffffff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:active { background: #1d4ed8; }
    .btn-secondary:active { background: #71717a; }
  </style>
</head>
<body>
  <div id="app">
    <header>
      <h1>Maestra</h1>
      <div class="thread-info">
        <span class="thread-name" id="thread-name">New Thread</span>
        <span class="memory-indicator">Memory in Maestra</span>
      </div>
    </header>
    <div id="debug-log" style="display: none; background: #18181b; border-bottom: 1px solid #3f3f46; padding: 8px; font-size: 10px; font-family: monospace; color: #10b981; max-height: 80px; overflow-y: auto;"></div>
    <main id="messages-container">
      <div id="messages"></div>
    </main>
    <div id="confirmation-dialog" class="confirmation-dialog hidden">
      <div class="confirmation-content">
        <div class="confirmation-icon">⚠️</div>
        <h3>Confirm Action</h3>
        <p id="confirmation-message"></p>
        <div class="confirmation-actions">
          <button id="confirm-cancel" class="btn-secondary">Cancel</button>
          <button id="confirm-proceed" class="btn-primary">Proceed</button>
        </div>
      </div>
    </div>
    <footer>
      <div class="input-container">
        <textarea id="message-input" placeholder="Ask Maestra anything..." rows="1"></textarea>
        <button id="send-btn">Send</button>
      </div>
    </footer>
  </div>
  <script>
    // UI_SCRIPT_PLACEHOLDER
  </script>
</body>
</html>`;

figma.showUI(INLINE_HTML, {
  width: 400,
  height: 600,
  themeColors: true,
  visible: true
});

// Intent handler: UI -> Plugin
figma.ui.onmessage = (msg: UIToPluginMessage) => {
  // 🔴 DOGFOOD MODE: Skip echo, go straight to real backend
  if (DOGFOOD_MODE && msg.type === 'user-intent') {
    handleUserIntent(msg.content);
    return;
  }
  
  switch (msg.type) {
    case 'user-intent':
      handleUserIntent(msg.content);
      break;
    case 'close':
      figma.closePlugin();
      break;
  }
};

function sanitizeContextForTransport(context: any): any {
  if (!context) return { selection_count: 0, items: [], surface: 'figma' };
  
  try {
    // Return the new context structure with items array
    const sanitized = {
      selection_count: context.selection_count || 0,
      items: context.items || [],
      surface: context.surface || 'figma'
    };
    
    // Prevent oversized payloads
    const serialized = JSON.stringify(sanitized);
    if (serialized.length > 10000) {
      return { 
        selection_count: 0, 
        items: [], 
        surface: 'figma',
        note: "Context truncated - too large" 
      };
    }
    
    return sanitized;
  } catch (err) {
    console.error('Context sanitization failed:', err);
    return { selection_count: 0, items: [], surface: 'figma' };
  }
}

async function handleUserIntent(content: string): Promise<void> {
  // Generate unique request_id for connection proof
  const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  console.log('🔵 Request ID:', requestId);
  
  // Generate connection token for end-to-end verification
  const connectionToken = `token_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  console.log('🔵 Connection Token:', connectionToken);
  
  // Gather full surface context
  const surfaceContext = gatherContext();
  console.log('🔵 Full context object:', JSON.stringify(surfaceContext, null, 2));
  console.log('🔵 Selection count from context:', surfaceContext.selection_count);
  console.log('🔵 Items in context:', surfaceContext.items);
  console.log('🔵 figma.currentPage.selection length:', figma.currentPage.selection.length);
  
  // Classify intent (simple classification on plugin side)
  // UI should have already done this, but we ensure it here
  const classification = classifyIntentSimple(content);
  
  // Derive minimal context slice based on intent
  // Replaces raw node lists with summaries
  const contextSlice = selectRelevantContext(classification.intent_type, surfaceContext);
  console.log('Context sanitized');
  const sanitizedContext = sanitizeContextForTransport(contextSlice);
  
  // Generate unique thread ID for new thread (Maestra may override)
  const threadId = `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  // Create adapter request in INTENT-FIRST ORDER
  // (system_prompt will be added by adapter)
  const request: Omit<AdapterRequest, 'system_prompt'> = {
    type: 'reasoning',
    request_id: requestId,
    connection_token: connectionToken,
    
    // 1. INTENT (FIRST - REQUIRED)
    intent_type: classification.intent_type,
    intent_label: classification.intent_label,
    intent_source: classification.intent_source,
    
    // 2. THREAD METADATA (SECOND - CONTINUITY)
    thread_id: threadId,
    thread_title: '',
    
    // 3. CONTEXT SLICE (THIRD - MINIMAL)
    context_slice: sanitizedContext,
    
    // 4. RAW MESSAGE (FOURTH - LAST)
    raw_message: content,
    
    // SYSTEM
    timestamp: Date.now()
  };
  
  // Signal UI to start a new streaming synthesis
  figma.ui.postMessage({
    type: 'maestra-stream-start',
    threadId
  } as PluginToUIMessage);
  
  // Log request size before sending
  console.log('Request keys:', Object.keys(request));
  console.log('Context slice size:', JSON.stringify(request.context_slice || {}).length);
  
  // Send to adapter with streaming callback
  try {
    // DEFENSIVE: Create minimal request if original is too large
    let safeRequest = request;
    try {
      const requestStr = JSON.stringify(request);
      console.log('Request size:', requestStr.length, 'bytes');
      if (requestStr.length > 5000) {
        console.warn('Request too large, using minimal version');
        safeRequest = {
          type: 'reasoning',
          request_id: request.request_id,
          connection_token: request.connection_token,
          intent_type: request.intent_type,
          raw_message: request.raw_message,
          thread_id: request.thread_id,
          context_slice: { selection_count: 0, note: 'Context truncated' }
        } as any;
      }
    } catch (stringifyError) {
      console.error('Cannot stringify request:', stringifyError);
      safeRequest = {
        type: 'reasoning',
        request_id: request.request_id,
        connection_token: request.connection_token,
        raw_message: request.raw_message,
        context_slice: { error: 'Serialization failed' }
      } as any;
    }
    
    console.log('Calling sendToMaestra...');
    const response = await sendToMaestra(safeRequest, (chunk: string) => {
      // Stream each chunk to UI
      figma.ui.postMessage({
        type: 'maestra-stream-chunk',
        chunk,
        threadId
      } as PluginToUIMessage);
    });
    console.log('sendToMaestra returned');
    
    // Defensive response handling
    if (!response || typeof response !== 'object') {
      console.error('Invalid response type:', typeof response);
      figma.ui.postMessage({
        type: 'maestra-synthesis',
        content: 'Error: Invalid response from backend',
        response_label: 'observation',
        request_id: requestId
      } as PluginToUIMessage);
      return;
    }
    
    console.log('Response keys:', Object.keys(response));
    
    // CRITICAL: Destructure immediately, don't access response object directly
    const {
      success = false,
      request_id = '',
      connection_token = '',
      backend_identity = null,
      content = '',
      response_label = 'observation',
      thread_id = '',
      thread_title = '',
      error = null
    } = response || {};
    
    console.log('Destructured success:', success);
    console.log('Destructured content length:', String(content).length);
    
    if (error) {
      console.error('Backend error:', error);
      
      // CRITICAL: Completely flatten error to primitive string
      let errorText = 'Unknown error';
      try {
        if (typeof error === 'string') {
          errorText = error;
        } else if (error && typeof error === 'object') {
          errorText = JSON.stringify(error);
        } else {
          errorText = String(error);
        }
      } catch (e) {
        errorText = 'Error serialization failed';
      }
      
      figma.ui.postMessage({
        type: 'maestra-synthesis',
        content: `Backend error: ${errorText}`,
        response_label: 'observation',
        request_id: String(request_id || '')
      } as PluginToUIMessage);
      console.log('Error message posted to UI');
      return;
    }
    
    if (success && content) {
      console.log('🟢 Response ID:', request_id);
      console.log('🟢 Connection Token:', connection_token);
      console.log('🟢 Backend Identity:', backend_identity);
      
      // Verify connection_token matches
      if (connection_token !== connectionToken) {
        console.error('⛔ CONNECTION TOKEN MISMATCH');
        console.error('   Expected:', connectionToken);
        console.error('   Received:', connection_token);
        figma.ui.postMessage({
          type: 'maestra-synthesis',
          content: 'Connection validation failed.',
          response_label: 'observation',
          thread_id: '',
          thread_title: ''
        } as PluginToUIMessage);
        return;
      }
      
      // Verify backend_identity is present
      if (!backend_identity) {
        console.error('⛔ BACKEND IDENTITY MISSING');
        figma.ui.postMessage({
          type: 'maestra-synthesis',
          content: 'Connection validation failed.',
          response_label: 'observation',
          thread_id: '',
          thread_title: ''
        } as PluginToUIMessage);
        return;
      }
      
      console.log('✅ CONNECTION VERIFIED');
      
      // Use ONLY the destructured primitives
      figma.ui.postMessage({
        type: 'maestra-synthesis',
        content: String(content),
        response_label: String(response_label),
        thread_id: String(thread_id),
        thread_title: String(thread_title),
        request_id: String(request_id)
      } as PluginToUIMessage);
      console.log('UI postMessage sent');
    } else if (request_id && !success && !content) {
      console.log('⚠️ Minimal response received');
      figma.ui.postMessage({
        type: 'maestra-synthesis',
        content: 'Backend acknowledged request (minimal response)',
        response_label: 'observation',
        request_id: String(request_id)
      } as PluginToUIMessage);
    }
  } catch (error) {
    console.error('Adapter error:', error);
    // Send error as final synthesis with default 'observation' label
    figma.ui.postMessage({
      type: 'maestra-synthesis',
      content: 'Error: Failed to get synthesis from Maestra',
      response_label: 'observation',
      thread_id: '',
      thread_title: ''
    } as PluginToUIMessage);
  }
}

/**
 * Simple intent classification on plugin side
 * UI should have already classified, but we ensure it here
 */
function classifyIntentSimple(content: string): {
  intent_type: 'observation' | 'action' | 'question';
  intent_label: string;
  intent_source: 'inferred';
} {
  const normalized = content.toLowerCase();
  
  // Check for action patterns
  if (/\b(create|make|modify|change|delete|remove|rename|move|apply|set|add)\b/i.test(normalized)) {
    return {
      intent_type: 'action',
      intent_label: 'Action: Modify design',
      intent_source: 'inferred'
    };
  }
  
  // Check for question patterns
  if (/\b(how|can you|could you|help)\b/i.test(normalized) || /\?$/.test(content)) {
    return {
      intent_type: 'question',
      intent_label: 'Question: Request guidance',
      intent_source: 'inferred'
    };
  }
  
  // Default to observation
  return {
    intent_type: 'observation',
    intent_label: 'Observe: Analyze current selection',
    intent_source: 'inferred'
  };
}

function gatherContext() {
  const selection = figma.currentPage.selection;
  
  console.log('🔵 Selection count:', selection.length);
  
  if (selection.length === 0) {
    return {
      selection_count: 0,
      items: [],
      surface: 'figma'
    };
  }
  
  const items = selection.map(node => {
    const base = {
      id: node.id,
      name: node.name,
      type: node.type
    };
    
    if ('width' in node && 'height' in node) {
      return {
        ...base,
        width: node.width,
        height: node.height
      };
    }
    
    return base;
  });
  
  console.log('🔵 Context items:', JSON.stringify(items, null, 2));
  
  return {
    selection_count: selection.length,
    items,
    surface: 'figma'
  };
}

/**
 * Gather Figma context - READ-ONLY
 * 
 * REVIEWER NOTE: This function only READS basic metadata.
 * No design properties are accessed. No modifications are made.
 * 
 * Data collected:
 * - File name (for context)
 * - Page name (for spatial awareness)
 * - Selected node names, types, IDs (for reference only)
 * 
 * This minimal context is sent to external Maestra backend.
 */
function gatherFigmaContext(): FigmaContext {
  const selection = figma.currentPage.selection;
  
  return {
    surface: 'figma',
    file: figma.root.name,
    page_or_board: figma.currentPage.name,
    selection_summary: {
      count: selection.length,
      nodes: selection.map(node => ({
        name: node.name,
        type: node.type,
        id: node.id
      }))
    }
  };
}

/**
 * Gather FigJam context - READ-ONLY
 * 
 * REVIEWER NOTE: This function only COUNTS and LISTS board elements.
 * No content is read. No modifications are made.
 * 
 * Data collected:
 * - Board name (for context)
 * - Section count and titles (for organization awareness)
 * - Sticky note count (for density awareness)
 * 
 * This minimal context is sent to external Maestra backend.
 */
function gatherFigJamContext(): FigJamContext {
  const page = figma.currentPage;
  
  // Count section nodes
  const sections = page.findAll(node => node.type === 'SECTION');
  const sectionTitles = sections.map(node => node.name);
  
  // Count sticky notes
  const stickies = page.findAll(node => node.type === 'STICKY');
  
  return {
    surface: 'figjam',
    file: figma.root.name,
    page_or_board: page.name,
    selection_summary: {
      section_count: sections.length,
      section_titles: sectionTitles,
      sticky_count: stickies.length
    }
  };
}
