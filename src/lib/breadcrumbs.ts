/**
 * Breadcrumb trail for tracking execution sources and tools used
 */

export interface BreadcrumbEntry {
  id: string;
  timestamp: string;
  type: 'source' | 'tool' | 'context' | 'result' | 'error';
  label: string;
  details?: Record<string, any>;
  duration?: number; // milliseconds
}

export interface ExecutionBreadcrumb {
  messageId: string;
  userInput: string;
  entries: BreadcrumbEntry[];
  startTime: string;
  endTime?: string;
  totalDuration?: number;
}

class BreadcrumbTrail {
  private trail: ExecutionBreadcrumb[] = [];
  private currentExecution: ExecutionBreadcrumb | null = null;

  startExecution(messageId: string, userInput: string) {
    this.currentExecution = {
      messageId,
      userInput,
      entries: [],
      startTime: new Date().toISOString(),
    };
  }

  addEntry(
    type: BreadcrumbEntry['type'],
    label: string,
    details?: Record<string, any>,
    duration?: number
  ) {
    if (!this.currentExecution) return;

    this.currentExecution.entries.push({
      id: `${this.currentExecution.messageId}_${this.currentExecution.entries.length}`,
      timestamp: new Date().toISOString(),
      type,
      label,
      details,
      duration,
    });
  }

  addSource(source: string, details?: Record<string, any>, duration?: number) {
    this.addEntry('source', source, details, duration);
  }

  addTool(toolName: string, details?: Record<string, any>, duration?: number) {
    this.addEntry('tool', toolName, details, duration);
  }

  addContext(contextType: string, details?: Record<string, any>, duration?: number) {
    this.addEntry('context', contextType, details, duration);
  }

  addResult(resultLabel: string, details?: Record<string, any>, duration?: number) {
    this.addEntry('result', resultLabel, details, duration);
  }

  addError(errorLabel: string, details?: Record<string, any>, duration?: number) {
    this.addEntry('error', errorLabel, details, duration);
  }

  endExecution() {
    if (!this.currentExecution) return;

    const endTime = new Date().toISOString();
    const startMs = new Date(this.currentExecution.startTime).getTime();
    const endMs = new Date(endTime).getTime();

    this.currentExecution.endTime = endTime;
    this.currentExecution.totalDuration = endMs - startMs;

    this.trail.push(this.currentExecution);
    this.currentExecution = null;
  }

  getCurrentExecution(): ExecutionBreadcrumb | null {
    return this.currentExecution;
  }

  getTrail(): ExecutionBreadcrumb[] {
    return this.trail;
  }

  getLastN(n: number): ExecutionBreadcrumb[] {
    return this.trail.slice(-n);
  }

  clear() {
    this.trail = [];
    this.currentExecution = null;
  }

  exportAsJSON(): string {
    return JSON.stringify(this.trail, null, 2);
  }
}

export const breadcrumbTrail = new BreadcrumbTrail();
