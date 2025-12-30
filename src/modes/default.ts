/**
 * Default Mode
 * Standard behavior for unknown/general websites.
 */

import type { Mode, PageContext, CaptureContext, SuggestedAction } from './types';

export const DefaultMode: Mode = {
  id: 'default',
  name: 'Default',
  description: 'Standard capture and chat for any website',

  match(_context: PageContext): number {
    // Default mode always matches with baseline confidence
    return 0.5;
  },

  composeContext(page: PageContext): CaptureContext {
    return {
      fullPage: true,
      extractedText: null, // Will be extracted by capture pipeline
      focus: page.selection
        ? {
            type: 'selection',
            text: page.selection,
            wordCount: page.selection.split(/\s+/).filter(Boolean).length,
          }
        : null,
      mode: this.id,
    };
  },

  suggestActions(): SuggestedAction[] {
    return [
      {
        id: 'ask',
        label: 'Ask about this page',
        icon: 'message-circle',
        primary: true,
      },
      {
        id: 'capture',
        label: 'Capture',
        icon: 'camera',
      },
      {
        id: 'summarize',
        label: 'Summarize',
        icon: 'file-text',
      },
    ];
  },
};
