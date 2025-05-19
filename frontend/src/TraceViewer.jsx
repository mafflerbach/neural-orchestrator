import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export default function TraceViewer() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [availableIds, setAvailableIds] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [userQuery, setUserQuery] = useState("");
  const [plannedServices, setPlannedServices] = useState([]);

  const mermaidRef = useRef(null);

  const serviceColors = {
    "coordinator-agent": "bg-blue-100 text-blue-800",
    "customer-service": "bg-green-100 text-green-800",
    "insurance-service": "bg-yellow-100 text-yellow-800",
    "pricing-service": "bg-purple-100 text-purple-800",
    "rental-service": "bg-pink-100 text-pink-800",
  };

  const fetchLogs = useCallback(() => {
    fetch("/api/logs")
      .then((res) => res.text())
      .then((text) => {
        const lines = text
          .split("\n")
          .filter(Boolean)
          .map((line) => {
            try {
              return JSON.parse(line);
            } catch {
              return null;
            }
          })
          .filter(Boolean);

        const uniqueIds = [...new Set(lines.map((l) => l.correlation_id))].slice(-5).reverse();
        setAvailableIds(uniqueIds);

        if (!selectedId && uniqueIds.length > 0) {
          setSelectedId(uniqueIds[0]);
        }

        const filtered = lines
          .filter((entry) => entry.correlation_id === selectedId)
          .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        setLogs(filtered);

        const coordinatorLogs = filtered.filter((l) => l.service === "coordinator-agent");

        // Extract the first available query
        const extractedQuery = coordinatorLogs.find((l) => l.query)?.query || "";

        // Extract all distinct services mentioned as `target_service`
        const extractedServices = [
          ...new Set(coordinatorLogs.map((l) => l.target_service).filter(Boolean))
        ];

        setUserQuery(extractedQuery);
        setPlannedServices(extractedServices);

      })
      .catch((err) => setError(err.toString()));
  }, [selectedId]);

  useEffect(() => {
    fetchLogs();
    if (autoRefresh) {
      const interval = setInterval(fetchLogs, 3000);
      return () => clearInterval(interval);
    }
  }, [fetchLogs, autoRefresh]);

  const diagramContent = useMemo(() => {
    return `sequenceDiagram
      participant Coordinator
      ${logs
        .filter((log) => log.target_service)
        .map(
          (log) =>
            `Coordinator->>${log.target_service}: ${log.reason?.replace(/\n/g, " ") || "invokes"}`
        )
        .join("\n")}
    `;
  }, [logs]);

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      !mermaidRef.current ||
      logs.length === 0 ||
      !diagramContent.trim()
    )
      return;

    try {
      const mermaid = window.mermaid;
      if (!mermaid) {
        throw new Error("Mermaid not loaded");
      }

      mermaid.initialize({ startOnLoad: false });

      requestAnimationFrame(() => {
        mermaid.render("traceDiagram", diagramContent, (svgCode) => {
          if (mermaidRef.current) {
            mermaidRef.current.innerHTML = svgCode;
          }
        });
      });
    } catch (err) {
      console.error("Mermaid render failed:", err);
      setError("Diagram rendering failed: " + err.message);
    }
  }, [diagramContent, logs.length]);

  if (error) return <div className="text-red-500 p-4">Error: {error}</div>;

  return (
    <div className="space-y-6 px-6 py-8 max-w-screen-2xl mx-auto">
      <h2 className="text-3xl font-bold text-gray-900">Orchestration Trace</h2>
      {userQuery && (
        <p className="italic text-sm text-gray-600 mt-1">
          You asked: <span className="font-medium text-gray-900">"{userQuery}"</span>
        </p>
      )}

      {plannedServices.length > 0 && (
        <div className="text-sm text-gray-700">
          <p className="font-semibold mt-4 mb-1">Planned orchestration:</p>
          <ul className="list-disc list-inside">
            {plannedServices.map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-6">
        <div className="flex flex-col gap-1 text-sm">
          <label htmlFor="correlation-id" className="font-medium text-gray-700">
            Select Correlation ID
          </label>
          <select
            id="correlation-id"
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="border rounded px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
          >
            {availableIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="form-checkbox"
          />
          Auto-refresh
        </label>
      </div>
      {/* Main grid layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Log sidebar */}
        <div className="lg:col-span-4 max-h-[85vh] overflow-y-auto space-y-4 pr-1">
          {logs
            .sort((a, b) => {
              if (a.response?.skipped && !b.response?.skipped) return -1;
              if (!a.response?.skipped && b.response?.skipped) return 1;
              return new Date(a.timestamp) - new Date(b.timestamp);
            })
            .map((log, index) => {
              const colorClass =
                serviceColors[log.service] || "bg-gray-100 text-gray-800";
              return (
                <div
                  key={index}
                  className={`border p-4 rounded shadow-sm space-y-2 ${
                    log.response?.skipped
                      ? "bg-red-50 border-red-300"
                      : "bg-white border-gray-200"
                  }`}
                >
                  <div className="text-xs text-gray-500">{log.timestamp}</div>
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-bold px-2 py-1 rounded ${colorClass}`}>
                      {log.service}
                    </span>
                    {log.response?.skipped && (
                      <span className="bg-red-100 text-red-800 text-xs font-semibold px-2 py-1 rounded">
                        ⏭️ Skipped
                      </span>
                    )}
                  </div>

                  {log.target_service && (
                    <div className="text-sm text-blue-700">
                      → {log.target_service}
                    </div>
                  )}

                  {log.request && (
                    <details className="text-sm text-gray-600">
                      <summary className="cursor-pointer font-semibold">🔽 Input</summary>
                      <pre className="bg-gray-100 p-2 rounded text-xs overflow-x-auto">
                        {JSON.stringify(log.request, null, 2)}
                      </pre>
                    </details>
                  )}

                  {log.response && (
                    <details className="text-sm text-gray-600">
                      <summary className="cursor-pointer font-semibold">🔼 Output</summary>
                      <pre className="bg-gray-100 p-2 rounded text-xs overflow-x-auto">
                        {JSON.stringify(log.response, null, 2)}
                      </pre>
                    </details>
                  )}

                  {log.reason && (
                    <div className="text-sm italic text-yellow-700">
                      💭 {log.reason}
                    </div>
                  )}

                  {log.query && (
                    <div className="text-sm text-purple-700">
                      🔍 <strong>Query:</strong> {log.query}
                    </div>
                  )}
                </div>
              );
            })}
        </div>

        {/* Mermaid diagram section */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex items-center gap-2 text-sm text-gray-600 font-semibold">
            <span>🕸️</span> Sequence Diagram
          </div>
          <div
            ref={mermaidRef}
            className="bg-gray-50 border border-gray-300 rounded p-4 shadow-sm overflow-x-auto max-w-full"
          />
        </div>
      </div>
    </div>
  );
}
