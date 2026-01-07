import React from 'react';
import { useTypingIntelligence } from '../hooks/useTypingIntelligence';
import { PreSendIndicator } from './PreSendIndicator';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const { state, onTextChange, reset } = useTypingIntelligence();
  
  const handleSend = async () => {
    if (!state.rawText.trim()) return;
    
    // Use optimized prompt if available, otherwise raw text
    const finalText = state.precomputeResult?.optimized_prompt || state.rawText;
    onSend(finalText);
    reset();
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSend();
    }
  };
  
  return (
    <div className="chat-input-container">
      <div className="chat-input-wrapper">
        <textarea 
          value={state.rawText}
          onChange={(e) => onTextChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Ctrl+Enter to send)"
          rows={3}
          disabled={disabled}
          className="chat-input"
        />
        
        {state.precomputeResult && (
          <PreSendIndicator 
            state={state}
          />
        )}
        
        {state.error && (
          <div className="error-message">
            Precompute unavailable: {state.error}
          </div>
        )}
      </div>
      
      <button 
        onClick={handleSend} 
        disabled={!state.rawText.trim() || disabled}
        className="send-button"
      >
        Send
      </button>
    </div>
  );
}
