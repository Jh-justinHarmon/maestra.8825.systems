/**
 * useTypingIntelligence Hook
 * 
 * Triggers precompute as user types, manages precompute state,
 * and provides send integration with fallback.
 * 
 * Usage:
 * const { state, onTextChange, onSend } = useTypingIntelligence();
 */

import { useCallback, useRef, useState } from 'react';

export interface PrecomputeState {
  rawText: string;
  isPrecomputing: boolean;
  precomputeResult: PrecomputeResult | null;
  costForecast: string;
  error: string | null;
}

export interface PrecomputeResult {
  optimized_prompt: string;
  context_refs: string[];
  recommended_model: string;
  cost_estimate: string;
  confidence: number;
  intent?: string;
  entities?: string[];
}

const initialState: PrecomputeState = {
  rawText: '',
  isPrecomputing: false,
  precomputeResult: null,
  costForecast: '',
  error: null,
};

export function useTypingIntelligence() {
  const [state, setState] = useState<PrecomputeState>(initialState);
  const debounceRef = useRef<NodeJS.Timeout>();
  const abortRef = useRef<AbortController>();

  /**
   * Handle text change from input.
   * Debounces 500ms before triggering precompute.
   */
  const onTextChange = useCallback((text: string) => {
    setState((s) => ({ ...s, rawText: text, error: null }));

    // Clear previous debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Abort previous precompute if still running
    if (abortRef.current) {
      abortRef.current.abort();
    }

    // Debounce: wait 500ms after typing stops
    debounceRef.current = setTimeout(() => {
      triggerPrecompute(text);
    }, 500);
  }, []);

  /**
   * Trigger precompute for current text.
   */
  const triggerPrecompute = async (text: string) => {
    if (!text || text.length < 5) {
      // Don't precompute for very short text
      return;
    }

    // Create new abort controller for this precompute
    abortRef.current = new AbortController();

    setState((s) => ({ ...s, isPrecomputing: true }));

    try {
      const response = await fetch('/api/precompute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
        signal: abortRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`Precompute failed: ${response.statusText}`);
      }

      const result: PrecomputeResult = await response.json();

      setState((s) => ({
        ...s,
        precomputeResult: result,
        costForecast: result.cost_estimate,
        isPrecomputing: false,
      }));
    } catch (error) {
      // Ignore abort errors (user typed again)
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      console.error('Precompute error:', error);
      setState((s) => ({
        ...s,
        isPrecomputing: false,
        error: error instanceof Error ? error.message : 'Precompute failed',
      }));
    }
  };

  /**
   * Send message using precompute result if available.
   * Falls back to raw text if precompute not ready.
   */
  const onSend = useCallback(async (onSendCallback?: (prompt: string, context?: any) => Promise<void>) => {
    // Abort any pending precompute
    if (abortRef.current) {
      abortRef.current.abort();
    }

    let promptToSend = state.rawText;
    let contextToSend = undefined;

    // Use precompute if ready and confident
    if (
      state.precomputeResult &&
      state.precomputeResult.confidence > 0.7
    ) {
      promptToSend = state.precomputeResult.optimized_prompt;
      contextToSend = {
        refs: state.precomputeResult.context_refs,
        model: state.precomputeResult.recommended_model,
        cost: state.precomputeResult.cost_estimate,
        intent: state.precomputeResult.intent,
      };
    }

    // Call the send callback if provided
    if (onSendCallback) {
      try {
        await onSendCallback(promptToSend, contextToSend);
      } catch (error) {
        console.error('Send failed:', error);
        setState((s) => ({
          ...s,
          error: error instanceof Error ? error.message : 'Send failed',
        }));
        return;
      }
    }

    // Clear state after send
    setState(initialState);
  }, [state.rawText, state.precomputeResult]);

  /**
   * Reset state (e.g., when closing dialog).
   */
  const reset = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setState(initialState);
  }, []);

  return {
    state,
    onTextChange,
    onSend,
    reset,
  };
}

/**
 * Hook for displaying precompute status.
 */
export function usePrecomputeStatus(state: PrecomputeState) {
  return {
    isReady: state.precomputeResult !== null && state.precomputeResult.confidence > 0.7,
    isLoading: state.isPrecomputing,
    hasError: state.error !== null,
    costForecast: state.costForecast,
    model: state.precomputeResult?.recommended_model,
    intent: state.precomputeResult?.intent,
    contextCount: state.precomputeResult?.context_refs.length ?? 0,
  };
}
