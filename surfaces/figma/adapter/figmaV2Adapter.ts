/**
 * Figma v2 Adapter - Thin translator for Maestra v2 Advisor API
 * 
 * OWNERSHIP:
 * - Surface: Extract context, package request
 * - Adapter: Translate to AdvisorRequest format
 * - Backend: All reasoning, prompts, tools, guardrails
 * 
 * WHAT THIS ADAPTER DOES:
 * - Accept surface inputs (user intent, Figma context)
 * - Package into AdvisorRequest
 * - Send to /api/maestra/advisor/ask
 * - Return AdvisorResponse unchanged
 * 
 * WHAT THIS ADAPTER MUST NOT DO:
 * - Inject system prompts (backend owns)
 * - Classify intent (backend owns)
 * - Enforce guardrails (backend owns)
 * - Make reasoning decisions (backend owns)
 * - Store conversation history (backend owns)
 * - Generate thread IDs (backend owns)
 * - Modify advisor_output (backend owns)
 */

import type { AdvisorRequest, AdvisorResponse, AdvisorError } from '../../../contracts/advisor';
import type { FigmaSurfaceContext } from '../../../contracts/surface';

// ============================================================
// ADAPTER INPUT (Surface-Provided)
// ============================================================

export interface FigmaAdapterInput {
  user_intent: string;
  figma_context: {
    file_name: string;
    page_name: string;
    editor_type: 'figma' | 'figjam';
    selection_count?: number;
    selection_summary?: string;
    selected_nodes?: Array<{
      name: string;
      type: string;
      id: string;
    }>;
    is_complete?: boolean;
    omitted_details?: string[];
  };
  thread_id?: string;
  client_metadata?: {
    client_version?: string;
    platform?: string;
  };
}

// ============================================================
// ADAPTER CONFIGURATION
// ============================================================

export interface AdapterConfig {
  endpoint: string;
  timeout: number;
  contract_version: string;
}

// ============================================================
// ADAPTER INTERFACE
// ============================================================

export interface FigmaV2Adapter {
  sendRequest(input: FigmaAdapterInput): Promise<AdvisorResponse | AdvisorError>;
  getConfig(): AdapterConfig;
}

// ============================================================
// ADAPTER IMPLEMENTATION
// ============================================================

export function createFigmaV2Adapter(config: AdapterConfig): FigmaV2Adapter {
  return {
    sendRequest: async (input: FigmaAdapterInput): Promise<AdvisorResponse | AdvisorError> => {
      // Generate request_id for idempotency
      const request_id = generateRequestId();

      // Build AdvisorRequest (NO MODIFICATIONS)
      const request: AdvisorRequest = {
        contract_version: config.contract_version,
        request_id: request_id,
        user_intent: input.user_intent,
        surface_context: {
          surface_id: "figma_plugin_v2",
          surface_type: "figma",
          figma: {
            file_name: input.figma_context.file_name,
            page_name: input.figma_context.page_name,
            editor_type: input.figma_context.editor_type,
            selection_count: input.figma_context.selection_count,
            selection_summary: input.figma_context.selection_summary,
            selected_nodes: input.figma_context.selected_nodes,
            is_complete: input.figma_context.is_complete ?? false,
            omitted_details: input.figma_context.omitted_details
          }
        } as FigmaSurfaceContext,
        thread_id: input.thread_id,
        client_metadata: input.client_metadata
      };

      // Send to backend (NO MODIFICATIONS)
      try {
        const response = await fetch(config.endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            // Auth header added by transport layer
          },
          body: JSON.stringify(request)
        });

        // Check HTTP status
        if (!response.ok) {
          // Parse error response
          const errorData = await response.json();
          return errorData.error as AdvisorError;
        }

        // Parse success response
        const data = await response.json();
        return data as AdvisorResponse;

      } catch (error) {
        // Network error - return AdvisorError
        return {
          code: 'backend_error',
          message: `Network error: ${(error as Error).message}`,
          retryable: true,
          trace_id: `client_${Date.now()}`
        };
      }
    },

    getConfig: () => config
  };
}

// ============================================================
// HELPER FUNCTIONS
// ============================================================

function generateRequestId(): string {
  return `req_${crypto.randomUUID()}`;
}
