import React, { useState } from 'react';
import { Save, CheckCircle, AlertCircle, Loader } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

interface SaveButtonProps {
  conversationId: string;
  conversationTitle: string;
  messages: Message[];
  userId?: string;
  sessionId?: string;
  onSaveComplete?: (result: SaveResult) => void;
}

interface SaveResult {
  success: boolean;
  entry_id?: string;
  verification_query?: string;
  error?: string;
}

export const SaveButton: React.FC<SaveButtonProps> = ({
  conversationId,
  conversationTitle,
  messages,
  userId,
  sessionId,
  onSaveComplete,
}) => {
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [savedEntryId, setSavedEntryId] = useState<string | null>(null);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus('saving');
    setErrorMessage(null);

    try {
      // Call backend save endpoint
      const response = await fetch('/api/maestra/save-conversation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          title: conversationTitle,
          messages: messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
          })),
          user_id: userId,
          session_id: sessionId,
        }),
      });

      const result: SaveResult = await response.json();

      if (result.success) {
        setSaveStatus('success');
        setSavedEntryId(result.entry_id || null);
        
        // Call callback if provided
        if (onSaveComplete) {
          onSaveComplete(result);
        }

        // Reset status after 3 seconds
        setTimeout(() => {
          setSaveStatus('idle');
        }, 3000);
      } else {
        setSaveStatus('error');
        setErrorMessage(result.error || 'Failed to save conversation');
      }
    } catch (error) {
      setSaveStatus('error');
      setErrorMessage(
        error instanceof Error ? error.message : 'An error occurred while saving'
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleSave}
        disabled={isSaving || saveStatus === 'success'}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg font-medium
          transition-all duration-200
          ${
            saveStatus === 'success'
              ? 'bg-green-100 text-green-700 cursor-default'
              : saveStatus === 'error'
              ? 'bg-red-100 text-red-700'
              : isSaving
              ? 'bg-blue-100 text-blue-700 cursor-wait'
              : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95'
          }
        `}
        title={
          saveStatus === 'success'
            ? `Saved to library (${savedEntryId})`
            : saveStatus === 'error'
            ? errorMessage || 'Save failed'
            : 'Save this conversation to 8825 Library'
        }
      >
        {isSaving ? (
          <>
            <Loader className="w-4 h-4 animate-spin" />
            <span>Saving...</span>
          </>
        ) : saveStatus === 'success' ? (
          <>
            <CheckCircle className="w-4 h-4" />
            <span>Saved</span>
          </>
        ) : saveStatus === 'error' ? (
          <>
            <AlertCircle className="w-4 h-4" />
            <span>Error</span>
          </>
        ) : (
          <>
            <Save className="w-4 h-4" />
            <span>Save</span>
          </>
        )}
      </button>

      {saveStatus === 'success' && savedEntryId && (
        <div className="text-sm text-gray-600">
          Entry: <code className="bg-gray-100 px-2 py-1 rounded">{savedEntryId}</code>
        </div>
      )}

      {saveStatus === 'error' && errorMessage && (
        <div className="text-sm text-red-600">{errorMessage}</div>
      )}
    </div>
  );
};

export default SaveButton;
