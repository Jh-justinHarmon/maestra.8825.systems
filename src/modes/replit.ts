/**
 * Replit Collaborator Mode
 * Specialized behavior for Replit coding environment.
 */

import type { PageContext, CaptureContext, SuggestedAction } from './types';

// Helper functions (outside the Mode object)
function looksLikeCode(text: string): boolean {
  const codeIndicators = [
    /^(import|export|const|let|var|function|class|def|async|await)\s/m,
    /[{}\[\]();]/,
    /=>/,
    /\.(tsx?|jsx?|py|rb|go|rs)$/,
  ];
  return codeIndicators.some(pattern => pattern.test(text));
}

function detectLanguage(url: string): string | undefined {
  const lower = url.toLowerCase();
  if (lower.includes('.tsx') || lower.includes('.ts')) return 'typescript';
  if (lower.includes('.jsx') || lower.includes('.js')) return 'javascript';
  if (lower.includes('.py')) return 'python';
  if (lower.includes('.rb')) return 'ruby';
  if (lower.includes('.go')) return 'go';
  if (lower.includes('.rs')) return 'rust';
  return undefined;
}

function extractFilePath(url: string): string | undefined {
  const hashIndex = url.indexOf('#');
  if (hashIndex !== -1) {
    return url.slice(hashIndex + 1);
  }
  return undefined;
}

export const ReplitCollaboratorMode = {
  id: 'replit_collaborator',
  name: 'Replit Collaborator',
  description: 'Code-aware assistance for Replit projects',

  match(context: PageContext): number {
    // High confidence match for Replit domains
    if (context.domain === 'replit.com' || context.url.includes('replit.com')) {
      return 0.9;
    }
    // Also match repl.co (deployed apps)
    if (context.domain?.endsWith('.repl.co') || context.url.includes('.repl.co')) {
      return 0.7;
    }
    return 0;
  },

  composeContext(page: PageContext): CaptureContext {
    // For Replit, we want structured code capture
    const isCodeSelection = page.selection && looksLikeCode(page.selection);
    
    return {
      fullPage: false, // Don't capture full page for Replit
      extractedText: null,
      focus: page.selection
        ? {
            type: isCodeSelection ? 'code_selection' : 'selection',
            text: page.selection,
            wordCount: page.selection.split(/\s+/).filter(Boolean).length,
            language: detectLanguage(page.url),
            filePath: extractFilePath(page.url),
          }
        : null,
      mode: this.id,
    };
  },

  suggestActions(): SuggestedAction[] {
    return [
      {
        id: 'collaborate',
        label: 'Collaborate on this project',
        icon: 'users',
        primary: true,
      },
      {
        id: 'explain',
        label: 'Explain this code',
        icon: 'help-circle',
      },
      {
        id: 'refactor',
        label: 'Suggest refactoring',
        icon: 'wand-2',
      },
      {
        id: 'debug',
        label: 'Help debug',
        icon: 'bug',
      },
    ];
  },

};
