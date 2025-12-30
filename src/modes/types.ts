/**
 * Mode Registry Types
 * Defines the interface for Maestra modes that tailor behavior per surface/app.
 */

export interface PageContext {
  url: string;
  title: string;
  domain: string;
  selection?: string;
  metadata?: Record<string, unknown>;
}

export interface CaptureContext {
  fullPage: boolean;
  extractedText: string | null;
  focus: FocusAnchor | null;
  mode: string;
}

export interface FocusAnchor {
  type: 'selection' | 'code_selection' | 'element';
  text: string;
  wordCount: number;
  // Code-specific fields
  language?: string;
  filePath?: string;
  lineRange?: [number, number];
}

export interface SuggestedAction {
  id: string;
  label: string;
  icon?: string;
  primary?: boolean;
}

export interface Mode {
  /** Unique identifier for this mode */
  id: string;
  
  /** Human-readable name */
  name: string;
  
  /** Short description */
  description: string;
  
  /**
   * Determine how well this mode matches the given page context.
   * @returns Confidence score 0-1 (0 = no match, 1 = perfect match)
   */
  match(context: PageContext): number;
  
  /**
   * Compose the capture context based on page context.
   * Determines what gets captured and how.
   */
  composeContext(page: PageContext): CaptureContext;
  
  /**
   * Get suggested actions for this mode.
   * Displayed as quick action buttons in the UI.
   */
  suggestActions(): SuggestedAction[];
}

export interface ModeMatch {
  mode: Mode;
  confidence: number;
}
