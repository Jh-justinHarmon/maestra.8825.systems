// Context Selector - Derives minimal context slices based on intent
// Prevents sending full selections or raw board data

import type { SurfaceContext, FigmaContext, FigJamContext } from '../types';

/**
 * Minimal context slice with explicit metadata
 * Replaces raw node lists with summaries
 */
export interface ContextSlice {
  /** Surface type */
  surface: 'figma' | 'figjam';
  
  /** File name */
  file: string;
  
  /** Page or board name */
  page_or_board: string;
  
  /** 
   * Intent-relevant summary
   * Derived based on what user wants to do
   */
  relevant_summary: string;
  
  /** 
   * Explicitly labeled as partial
   * Maestra should not assume this is complete information
   */
  is_partial: true;
  
  /** 
   * Explicitly labeled as lossy
   * Design properties are not fully captured
   */
  is_lossy: true;
  
  /**
   * What was filtered out
   * Transparency about what's missing
   */
  omitted_details: string[];
}

/**
 * Select relevant context based on user intent
 * Returns minimal slice instead of full surface context
 * 
 * Intent-based filtering:
 * - observation: Include counts and types, omit IDs and detailed properties
 * - action: Include selection details, omit unselected nodes
 * - question: Include high-level summary only
 */
export function selectRelevantContext(
  intent_type: 'observation' | 'action' | 'question',
  surfaceContext: any
): any {
  const selectionCount = surfaceContext.selection?.length || 0;
  
  return {
    selection_count: selectionCount,
    page_name: surfaceContext.page?.name || 'Unknown',
    has_selection: selectionCount > 0
  };
}

/**
 * Select relevant Figma context based on intent
 */
function selectFigmaContext(
  intent_type: 'observation' | 'action' | 'question',
  context: FigmaContext
): ContextSlice {
  const selection = context.selection_summary;
  
  // OBSERVATION: User wants to understand/analyze
  if (intent_type === 'observation') {
    const typeCounts = countNodeTypes(selection.nodes);
    const summary = selection.count === 0
      ? 'No selection'
      : `${selection.count} nodes selected: ${formatTypeCounts(typeCounts)}`;
    
    return {
      surface: 'figma',
      file: context.file,
      page_or_board: context.page_or_board,
      relevant_summary: summary,
      is_partial: true,
      is_lossy: true,
      omitted_details: [
        'Node IDs',
        'Exact positions and dimensions',
        'Fill and stroke properties',
        'Typography details',
        'Layer hierarchy beyond selection'
      ]
    };
  }
  
  // ACTION: User wants to modify/create
  if (intent_type === 'action') {
    const nodeNames = selection.nodes.map(n => `"${n.name}" (${n.type})`).join(', ');
    const summary = selection.count === 0
      ? 'No selection - action will apply to page or create new'
      : `Selected: ${nodeNames}`;
    
    return {
      surface: 'figma',
      file: context.file,
      page_or_board: context.page_or_board,
      relevant_summary: summary,
      is_partial: true,
      is_lossy: true,
      omitted_details: [
        'Unselected nodes',
        'Design properties (colors, fonts, etc.)',
        'Component instances and variants',
        'Auto-layout configuration'
      ]
    };
  }
  
  // QUESTION: User is asking for help
  // Minimal context - just high-level summary
  const summary = selection.count === 0
    ? `Working in "${context.file}" on page "${context.page_or_board}"`
    : `Working in "${context.file}" with ${selection.count} nodes selected`;
  
  return {
    surface: 'figma',
    file: context.file,
    page_or_board: context.page_or_board,
    relevant_summary: summary,
    is_partial: true,
    is_lossy: true,
    omitted_details: [
      'All node details',
      'Selection specifics',
      'Design properties',
      'Layer structure'
    ]
  };
}

/**
 * Select relevant FigJam context based on intent
 */
function selectFigJamContext(
  intent_type: 'observation' | 'action' | 'question',
  context: FigJamContext
): ContextSlice {
  const summary = context.selection_summary;
  
  // OBSERVATION: User wants to understand/analyze
  if (intent_type === 'observation') {
    const boardSummary = `${summary.section_count} sections, ${summary.sticky_count} sticky notes`;
    const sectionList = summary.section_titles.length > 0
      ? `. Sections: ${summary.section_titles.slice(0, 5).join(', ')}${summary.section_titles.length > 5 ? '...' : ''}`
      : '';
    
    return {
      surface: 'figjam',
      file: context.file,
      page_or_board: context.page_or_board,
      relevant_summary: boardSummary + sectionList,
      is_partial: true,
      is_lossy: true,
      omitted_details: [
        'Sticky note content',
        'Connector relationships',
        'Shapes and drawings',
        'Exact positions',
        'Section beyond first 5'
      ]
    };
  }
  
  // ACTION: User wants to modify/create
  if (intent_type === 'action') {
    const boardSummary = `Board has ${summary.section_count} sections and ${summary.sticky_count} stickies`;
    
    return {
      surface: 'figjam',
      file: context.file,
      page_or_board: context.page_or_board,
      relevant_summary: boardSummary,
      is_partial: true,
      is_lossy: true,
      omitted_details: [
        'Individual sticky content',
        'Section details',
        'Connector paths',
        'Widget states'
      ]
    };
  }
  
  // QUESTION: User is asking for help
  const boardSummary = `Working in FigJam board "${context.file}"`;
  
  return {
    surface: 'figjam',
    file: context.file,
    page_or_board: context.page_or_board,
    relevant_summary: boardSummary,
    is_partial: true,
    is_lossy: true,
    omitted_details: [
      'All board content',
      'Section structure',
      'Sticky notes',
      'Shapes and connectors'
    ]
  };
}

/**
 * Count node types in selection
 */
function countNodeTypes(nodes: Array<{ name: string; type: string; id: string }>): Record<string, number> {
  const counts: Record<string, number> = {};
  
  for (const node of nodes) {
    counts[node.type] = (counts[node.type] || 0) + 1;
  }
  
  return counts;
}

/**
 * Format type counts as human-readable string
 */
function formatTypeCounts(counts: Record<string, number>): string {
  const entries = Object.entries(counts);
  
  if (entries.length === 0) return 'none';
  if (entries.length === 1) {
    const [type, count] = entries[0];
    return `${count} ${type}${count > 1 ? 's' : ''}`;
  }
  
  return entries
    .map(([type, count]) => `${count} ${type}${count > 1 ? 's' : ''}`)
    .join(', ');
}
