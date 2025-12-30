export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface Context {
  selection?: string;
  attachments?: string[];
}

export interface Response {
  message: Message;
  streaming?: boolean;
}

export interface ContextResult {
  relevantDocs: string[];
  suggestions: string[];
}

export interface CaptureResult {
  id: string;
  title: string;
  summary: string;
  timestamp: Date;
}

export interface Adapter {
  sendMessage(conversationId: string, message: string, context?: Context): Promise<Response>;
  prefetchContext(query: string): Promise<ContextResult>;
  capture(payload: { content: string; context?: Context }): Promise<CaptureResult>;
}
