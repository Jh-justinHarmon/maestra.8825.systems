/**
 * Mock Backend Server
 * Provides stub endpoints for Maestra API contract testing.
 * Used for E2E tests and local development.
 */

import express, { Request, Response } from 'express';

const app = express();
const PORT = 3001;

app.use(express.json());

// Health check
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Chat endpoint
app.post('/api/chat', (req: Request, res: Response) => {
  const { conversationId, content, context } = req.body;

  const response = {
    schema_version: '1',
    message: {
      id: 'msg_' + Date.now(),
      role: 'assistant',
      content: `Mock response to: "${content}"`,
      timestamp: new Date().toISOString(),
    },
  };

  res.json(response);
});

// Capture endpoint
app.post('/api/capture', (req: Request, res: Response) => {
  const { url, title, selection } = req.body;

  const result = {
    schema_version: '1',
    id: 'cap_' + Date.now(),
    title: title || 'Captured page',
    summary: selection || 'Full page capture',
    timestamp: new Date().toISOString(),
    source: {
      url: url || '',
      title: title || '',
      domain: new URL(url || 'https://example.com').hostname,
    },
    content: {
      extracted_text: selection || null,
      word_count: selection ? selection.split(/\s+/).length : 0,
    },
    focus: selection
      ? {
          type: 'selection',
          text: selection,
          word_count: selection.split(/\s+/).length,
        }
      : null,
    mode: 'default',
    metadata: {
      captured_at: new Date().toISOString(),
      surface: 'web',
    },
  };

  res.json(result);
});

// Context prefetch endpoint
app.get('/api/context', (req: Request, res: Response) => {
  const query = req.query.q as string;

  const result = {
    schema_version: '1',
    relevantDocs: [
      `Documentation for "${query}"`,
      'Related patterns and examples',
    ],
    suggestions: [
      'Consider checking the official docs',
      'Look for similar patterns in the codebase',
    ],
  };

  res.json(result);
});

// Error handling
app.use((err: any, req: Request, res: Response) => {
  console.error('Error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server
app.listen(PORT, () => {
  console.log(`Mock backend running on http://localhost:${PORT}`);
  console.log(`Health check: GET http://localhost:${PORT}/health`);
});
