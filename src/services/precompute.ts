/**
 * Precompute Service
 * 
 * Client-side service for calling the precompute backend endpoint.
 * Handles API communication, error handling, and response parsing.
 */

export interface PrecomputeRequest {
  text: string;
}

export interface PrecomputeResponse {
  optimized_prompt: string;
  context_refs: string[];
  recommended_model: string;
  cost_estimate: string;
  confidence: number;
  intent?: string;
  entities?: string[];
}

class PrecomputeService {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl || window.location.origin;
  }

  /**
   * Call precompute endpoint.
   * 
   * @param text - Raw user text to precompute
   * @param signal - Optional AbortSignal for cancellation
   * @returns PrecomputeResponse with optimized prompt and metadata
   */
  async run(
    text: string,
    signal?: AbortSignal
  ): Promise<PrecomputeResponse> {
    const request: PrecomputeRequest = { text };

    const response = await fetch(`${this.baseUrl}/api/precompute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(
        `Precompute failed: ${response.status} ${response.statusText}. ${error}`
      );
    }

    return response.json();
  }

  /**
   * Health check for precompute service.
   */
  async health(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/precompute/health`, {
        method: 'GET',
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const precomputeService = new PrecomputeService();
