import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import App from '../App';

// Mock fetch globally
global.fetch = jest.fn();

describe('Conversation Polling - Message Persistence', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('preserves optimistic assistant message when /conversation returns 404', async () => {
    // Mock health check - persistence unavailable
    (global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ persistence: false, database_url: false })
        });
      }
      if (url.includes('/conversation/')) {
        return Promise.resolve({ ok: false, status: 404 });
      }
      if (url.includes('/advisor/ask')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            answer: 'Test assistant response',
            trace_id: 'test-trace',
            authority: 'system',
            system_mode: 'full',
            sources: []
          })
        });
      }
      return Promise.reject(new Error('Unexpected fetch'));
    });

    render(<App />);

    // Wait for initial render
    await waitFor(() => {
      expect(screen.queryByText('Start a conversation with Maestra...')).toBeInTheDocument();
    });

    // Simulate sending a message
    const input = screen.getByTestId('message-input');
    const sendButton = screen.getByTestId('send-button');

    act(() => {
      input.value = 'Test question';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });

    act(() => {
      sendButton.click();
    });

    // Wait for assistant message to appear
    await waitFor(() => {
      expect(screen.getByText('Test assistant response')).toBeInTheDocument();
    }, { timeout: 2000 });

    // Wait 3+ seconds to ensure polling has run multiple times
    await new Promise(resolve => setTimeout(resolve, 3500));

    // Message should still be visible
    expect(screen.getByText('Test assistant response')).toBeInTheDocument();
  });

  it('preserves optimistic assistant message when /conversation returns empty turns', async () => {
    (global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ persistence: true })
        });
      }
      if (url.includes('/conversation/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ turns: [] })
        });
      }
      if (url.includes('/advisor/ask')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            answer: 'Test response',
            trace_id: 'test-trace-2',
            authority: 'system',
            system_mode: 'full',
            sources: []
          })
        });
      }
      return Promise.reject(new Error('Unexpected fetch'));
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Start a conversation with Maestra...')).toBeInTheDocument();
    });

    const input = screen.getByTestId('message-input');
    const sendButton = screen.getByTestId('send-button');

    act(() => {
      input.value = 'Another test';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });

    act(() => {
      sendButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText('Test response')).toBeInTheDocument();
    }, { timeout: 2000 });

    // Wait for polling cycles
    await new Promise(resolve => setTimeout(resolve, 3500));

    // Message must persist
    expect(screen.getByText('Test response')).toBeInTheDocument();
  });

  it('disables polling when persistence unavailable', async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock;

    fetchMock.mockImplementation((url: string) => {
      if (url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ persistence: false })
        });
      }
      return Promise.reject(new Error('Should not poll'));
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Start a conversation with Maestra...')).toBeInTheDocument();
    });

    // Wait to ensure polling doesn't start
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Should only have called health check, not conversation endpoint
    const conversationCalls = fetchMock.mock.calls.filter(call => 
      call[0].includes('/conversation/')
    );
    expect(conversationCalls.length).toBe(0);
  });
});
