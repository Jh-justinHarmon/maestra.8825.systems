/**
 * Mode Registry
 * Selects the best mode for a given page context.
 */

import type { Mode, PageContext, ModeMatch } from './types';
import { DefaultMode } from './default';
import { ReplitCollaboratorMode } from './replit';

// All registered modes
const MODES: Mode[] = [
  ReplitCollaboratorMode,
  DefaultMode, // Default should be last (fallback)
];

// Minimum confidence threshold for mode selection
const MIN_CONFIDENCE = 0.3;

/**
 * Select the best mode for the given page context.
 * Returns the mode with highest confidence above threshold.
 * Falls back to DefaultMode if no mode matches.
 */
export function selectMode(context: PageContext): ModeMatch {
  let bestMatch: ModeMatch = {
    mode: DefaultMode,
    confidence: DefaultMode.match(context),
  };

  for (const mode of MODES) {
    const confidence = mode.match(context);
    
    if (confidence >= MIN_CONFIDENCE && confidence > bestMatch.confidence) {
      bestMatch = { mode, confidence };
    }
  }

  return bestMatch;
}

/**
 * Get all modes with their match confidence for a given context.
 * Useful for debugging or showing mode options to user.
 */
export function getAllModeMatches(context: PageContext): ModeMatch[] {
  return MODES.map(mode => ({
    mode,
    confidence: mode.match(context),
  })).sort((a, b) => b.confidence - a.confidence);
}

/**
 * Get a mode by ID.
 */
export function getModeById(id: string): Mode | undefined {
  return MODES.find(mode => mode.id === id);
}

/**
 * List all available modes.
 */
export function listModes(): Mode[] {
  return [...MODES];
}
