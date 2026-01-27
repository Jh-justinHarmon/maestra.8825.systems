export const SCHEMA_VERSION = '1' as const;

export type SchemaVersion = typeof SCHEMA_VERSION;
export type ISODateTimeString = string;

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: ISODateTimeString;
  sources?: string[];
  mode?: string;
}

export interface Context {
  selection?: string;
  attachments?: string[];
}

export interface Response {
  schema_version: SchemaVersion;
  message: Message;
  streaming?: boolean;
}

export interface ContextResult {
  schema_version: SchemaVersion;
  relevantDocs: string[];
  suggestions: string[];
}

export interface CaptureResult {
  schema_version: SchemaVersion;
  id: string;
  title: string;
  summary: string;
  timestamp: ISODateTimeString;
}

export interface Adapter {
  sendMessage(conversationId: string, message: string, context?: Context, messages?: Message[]): Promise<Response>;
  prefetchContext(query: string): Promise<ContextResult>;
  capture(payload: { content: string; context?: Context }, sessionId: string): Promise<CaptureResult>;
}
