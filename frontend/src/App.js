// frontend/src/App.js
import { useState, useEffect } from 'react';
import TraceViewer from './TraceViewer';


export default function App() {
  const [query, setQuery]               = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [pickIds, setPickIds]           = useState([]);
  const [candidates, setCandidates]     = useState([]);
  const [reasons, setReasons]           = useState({});
  const [responses, setResponses]       = useState({});
  const [loading, setLoading]           = useState(false);
  const [llmRaw, setLlmRaw] = useState('');
  // 1) debounce
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => clearTimeout(t);
  }, [query]);

  // 2) fetch semantic search
useEffect(() => {
  if (!debouncedQuery) {
    setCandidates([]);
    setPickIds([]);
    setReasons({});
    setResponses({});
    return;
  }

  fetch(`/api/search?q=${encodeURIComponent(debouncedQuery)}&k=5`)
    .then(r => r.json())
    .then(data => {
      const enriched = data.map(c => {
        const m = c.metadata || {};

        // Collect all potential default-worthy values from flat metadata
        const possibleDefaults = ['location', 'start_date', 'end_date', 'days', 'vehicle_type', 'customer_tier', 'customer_id'];
        const defaults = {};

        possibleDefaults.forEach(key => {
          if (m[key] !== undefined) {
            defaults[key] = m[key];
          }
        });

        const provides = Array.isArray(m.provides) ? m.provides.join(", ") : m.provides;
        const tags = Array.isArray(m.tags) ? m.tags.join(", ") : m.tags;

        return {
          ...c,
          document: `Provides: ${provides || "unknown"} — Tags: ${tags || "none"}`,
          metadata: {
            ...m,
            defaults // inject defaults into metadata for backend compatibility
          }
        };
      });

      setCandidates(enriched);
      setPickIds([]);
      setReasons({});
      setResponses({});
    })
    .catch(err => {
      console.error('Search error:', err);
      setCandidates([]);
    });
}, [debouncedQuery]);

  // 3) single “Run Orchestration” button
  const dispatchAgents = async () => {
    setLoading(true);
    try {
      // Base payload
      const payload = { query: debouncedQuery, candidates };

      // Dynamically add each service’s inputs + defaults
      candidates.forEach(c => {
        const { inputs = [], defaults = {} } = c.metadata;
        const inputsArr = typeof inputs === "string" ? inputs.split(",") : inputs;
        inputsArr.forEach(key => {
          if (defaults[key] !== undefined) {
            payload[key] = defaults[key];
          }
        });
      });

      const res = await fetch('/api/dispatch', {
        method: 'POST',
        headers: { 'Content-Type':'application/json' },
        body: JSON.stringify(payload)
      });
      const { pickids, reasons, responses } = await res.json();
      setPickIds(pickids || []);
      setReasons(reasons);
      setResponses(responses);
      setLlmRaw(data.llm_raw || ''); 
    } catch(err) {
      console.error('Dispatch error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
   <div className="px-6 py-8 max-w-screen-2xl mx-auto w-full">
      <h1 className="text-2xl font-bold mb-4">Semantic Agent Orchestrator</h1>

      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Describe your request…"
        className="w-full p-2 border rounded mb-4"
      />

      {candidates.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-2">Top Candidates</h2>
          <ul className="space-y-2">
            {candidates.map(c => (
              <li
                key={c.id}
                className="p-3 border rounded flex justify-between items-center"
              >
                <div>
                  <div className="font-medium">{c.id}</div>
                  <div className="text-sm text-gray-600">
                    distance: {c.distance.toFixed(3)}
                  </div>
                </div>
              </li>
            ))}
          </ul>

          {/* only show this once, not per candidate */}
          <button
            onClick={dispatchAgents}
            disabled={loading}
            className="mt-4 w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Running…' : 'Run Orchestration'}
          </button>
        </div>
      )}

      {pickIds.length > 0 && (
        <div className="mt-6">
          <h2 className="text-xl font-bold mb-2">Results</h2>
          {pickIds.map(id => (
            <div key={id} className="mb-4 p-4 border rounded">
              <h3 className="text-lg font-medium">{id}</h3>
              <p className="italic text-sm mb-2">{reasons[id]}</p>
              <pre className="whitespace-pre-wrap text-sm">
                {JSON.stringify(responses[id], null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}

      {llmRaw && (
        <details className="mt-4 text-sm text-gray-600">
          <summary className="cursor-pointer underline">LLM raw response</summary>
          <pre className="whitespace-pre-wrap">{llmRaw}</pre>
        </details>
      )}


      <div className="mt-10">
        <TraceViewer/>
      </div>

    </div>
  );
}
