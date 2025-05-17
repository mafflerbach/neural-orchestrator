// TraceViewer.jsx
import { useEffect, useState } from "react";

export default function TraceViewer() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [availableIds, setAvailableIds] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchLogs = () => {
    fetch("/api/logs")
      .then((res) => res.text())
      .then((text) => {
        const lines = text
          .split("\n")
          .filter(Boolean)
          .map((line) => {
            try {
              return JSON.parse(line);
            } catch (e) {
              return null;
            }
          })
          .filter(Boolean);

        const uniqueIds = [...new Set(lines.map(l => l.correlation_id))].slice(-5).reverse();
        setAvailableIds(uniqueIds);

        if (!selectedId && uniqueIds.length > 0) {
          setSelectedId(uniqueIds[0]);
        }

        const filtered = lines
          .filter((entry) => entry.correlation_id === selectedId)
          .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        setLogs(filtered);
      })
      .catch((err) => setError(err.toString()));
  };

  useEffect(() => {
    fetchLogs();
    if (autoRefresh) {
      const interval = setInterval(fetchLogs, 3000);
      return () => clearInterval(interval);
    }
  }, [selectedId, autoRefresh]);

  if (error) return <div className="text-red-500">Error: {error}</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Orchestration Trace</h2>

      <label className="block text-sm font-medium text-gray-700 mb-1">Select Correlation ID</label>
      <select
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
        className="border rounded p-2 text-sm mb-4"
      >
        {availableIds.map((id) => (
          <option key={id} value={id}>{id}</option>
        ))}
      </select>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={autoRefresh}
          onChange={(e) => setAutoRefresh(e.target.checked)}
        />
        Auto-refresh
      </label>

      {logs.length === 0 && selectedId && (
        <div className="text-gray-500">No trace entries for selected ID</div>
      )}

      {logs.map((log, index) => (
        <div key={index} className="border p-4 rounded bg-gray-50">
          <div className="text-sm text-gray-600">{log.timestamp}</div>
          <div className="text-lg font-medium">{log.service}</div>
          {log.target_service && (
            <div className="text-sm text-blue-600">→ {log.target_service}</div>
          )}

          {log.reason && (
            <div className="text-sm italic text-yellow-700 mt-2">
              💭 {log.reason}
            </div>
          )}

          {log.query && (
            <div className="text-sm text-purple-700 mt-2">
              🔍 <strong>Query:</strong> {log.query}
            </div>
          )}

          {log.contract_input && (
            <details className="mt-2">
              <summary className="cursor-pointer text-sm font-semibold text-gray-700">📥 Contract Input</summary>
              <pre className="bg-gray-100 p-2 rounded text-xs whitespace-pre-wrap">
                {JSON.stringify(JSON.parse(log.contract_input), null, 2)}
              </pre>
            </details>
          )}

          {log.contract_output && (
            <details className="mt-2">
              <summary className="cursor-pointer text-sm font-semibold text-gray-700">📤 Contract Output</summary>
              <pre className="bg-gray-100 p-2 rounded text-xs whitespace-pre-wrap">
                {JSON.stringify(JSON.parse(log.contract_output), null, 2)}
              </pre>
            </details>
          )}

          <details className="mt-2">
            <summary className="cursor-pointer text-sm font-semibold">Request</summary>
            <pre className="bg-gray-100 p-2 rounded text-xs whitespace-pre-wrap">
              {JSON.stringify(log.request, null, 2)}
            </pre>
          </details>

          <details className="mt-2">
            <summary className="cursor-pointer text-sm font-semibold">Response</summary>
            <pre className="bg-gray-100 p-2 rounded text-xs whitespace-pre-wrap">
              {JSON.stringify(log.response, null, 2)}
            </pre>
          </details>
        </div>
      ))}
    </div>
  );
}
