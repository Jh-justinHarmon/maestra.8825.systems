import { useState, useEffect } from 'react';
import { getOrCreateSessionId } from '../lib/session';

interface DebugSessionData {
  session_id: string;
  router_found: boolean;
  router?: {
    authenticated: boolean;
    mode: string;
    personal_scope_present: boolean;
    personal_scope_owner: string | null;
    personal_scope_expired: boolean | null;
  };
  environment?: {
    FORCE_AUTH: string;
    DISABLE_TRUST_ENFORCEMENT: string;
  };
  error?: string;
}

export function DebugPanel() {
  const [debugData, setDebugData] = useState<DebugSessionData | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const sessionId = getOrCreateSessionId();

  const fetchDebugData = async () => {
    setIsLoading(true);
    try {
      const apiBase = localStorage.getItem('maestra_api_override') || 'http://localhost:8825';
      const response = await fetch(`${apiBase}/debug/session/${sessionId}`);
      const data = await response.json();
      setDebugData(data);
    } catch (error) {
      console.error('Failed to fetch debug data:', error);
      setDebugData({
        session_id: sessionId,
        router_found: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDebugData();
      const interval = setInterval(fetchDebugData, 2000); // Refresh every 2s
      return () => clearInterval(interval);
    }
  }, [isOpen, sessionId]);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg shadow-lg text-sm font-mono z-50"
      >
        🐛 Debug
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 bg-zinc-800 border border-zinc-700 rounded-lg shadow-2xl p-4 w-96 z-50 font-mono text-xs">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-purple-400 font-bold">🐛 Session Debug</h3>
        <button
          onClick={() => setIsOpen(false)}
          className="text-zinc-400 hover:text-white"
        >
          ✕
        </button>
      </div>

      {isLoading && !debugData ? (
        <div className="text-zinc-400">Loading...</div>
      ) : debugData ? (
        <div className="space-y-2">
          <div className="border-b border-zinc-700 pb-2">
            <div className="text-zinc-400">Session ID</div>
            <div className="text-white break-all">{debugData.session_id}</div>
          </div>

          {debugData.error ? (
            <div className="text-red-400 bg-red-950/30 p-2 rounded">
              ❌ {debugData.error}
            </div>
          ) : (
            <>
              <div className="border-b border-zinc-700 pb-2">
                <div className="text-zinc-400">Router Found</div>
                <div className={debugData.router_found ? "text-green-400" : "text-red-400"}>
                  {debugData.router_found ? "✅ Yes" : "❌ No"}
                </div>
              </div>

              {debugData.router && (
                <>
                  <div className="border-b border-zinc-700 pb-2">
                    <div className="text-zinc-400">Authenticated</div>
                    <div className={debugData.router.authenticated ? "text-green-400" : "text-red-400"}>
                      {debugData.router.authenticated ? "✅ True" : "❌ False"}
                    </div>
                  </div>

                  <div className="border-b border-zinc-700 pb-2">
                    <div className="text-zinc-400">Router Mode</div>
                    <div className="text-white">{debugData.router.mode}</div>
                  </div>

                  <div className="border-b border-zinc-700 pb-2">
                    <div className="text-zinc-400">Personal Scope</div>
                    <div className={debugData.router.personal_scope_present ? "text-green-400" : "text-zinc-500"}>
                      {debugData.router.personal_scope_present ? "✅ Present" : "❌ None"}
                    </div>
                    {debugData.router.personal_scope_owner && (
                      <div className="text-zinc-400 text-xs mt-1">
                        Owner: {debugData.router.personal_scope_owner}
                      </div>
                    )}
                    {debugData.router.personal_scope_expired !== null && (
                      <div className={debugData.router.personal_scope_expired ? "text-red-400" : "text-green-400"}>
                        {debugData.router.personal_scope_expired ? "⚠️ Expired" : "✅ Valid"}
                      </div>
                    )}
                  </div>
                </>
              )}

              {debugData.environment && process.env.NODE_ENV === 'development' && (
                <div className="border-t border-zinc-700 pt-2 mt-2">
                  <div className="text-zinc-400 mb-1">Environment (DEV ONLY)</div>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-zinc-400">FORCE_AUTH</span>
                      <span className={debugData.environment.FORCE_AUTH === "true" ? "text-green-400" : "text-zinc-500"}>
                        {debugData.environment.FORCE_AUTH}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">DISABLE_TRUST</span>
                      <span className={debugData.environment.DISABLE_TRUST_ENFORCEMENT === "true" ? "text-yellow-400" : "text-zinc-500"}>
                        {debugData.environment.DISABLE_TRUST_ENFORCEMENT}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <button
            onClick={fetchDebugData}
            disabled={isLoading}
            className="w-full mt-2 bg-purple-600 hover:bg-purple-700 disabled:bg-zinc-700 text-white py-1 rounded text-xs"
          >
            {isLoading ? "Refreshing..." : "🔄 Refresh"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
