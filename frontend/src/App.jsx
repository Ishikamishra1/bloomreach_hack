import { useState } from "react";

// Build order note: this is intentionally the LAST piece to build.
// Get the pipeline working headlessly (via `aws stepfunctions start-execution`
// or the FastAPI backend directly) before wiring up this UI.

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [therapeuticArea, setTherapeuticArea] = useState("Colorectal Cancer");
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [executionId, setExecutionId] = useState(null);

  async function startScan() {
    setStatus("STARTING");
    setResult(null);

    const res = await fetch(`${API_BASE}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ therapeutic_area: therapeuticArea }),
    });
    const data = await res.json();
    const id = data.execution_arn.split(":").pop();
    setExecutionId(id);
    setStatus("RUNNING");
    poll(id);
  }

  async function poll(id) {
    const res = await fetch(`${API_BASE}/scan/${id}`);
    const data = await res.json();
    setStatus(data.status);

    if (data.status === "RUNNING") {
      setTimeout(() => poll(id), 3000);
    } else if (data.status === "SUCCEEDED") {
      setResult(data.output);
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: "40px auto", fontFamily: "Arial, sans-serif" }}>
      <h1>TheraScout</h1>
      <p style={{ color: "#555" }}>AI-Powered Therapeutic Opportunity Intelligence</p>

      <div style={{ marginTop: 24 }}>
        <label>
          Therapeutic area:{" "}
          <input
            value={therapeuticArea}
            onChange={(e) => setTherapeuticArea(e.target.value)}
          />
        </label>
        <button onClick={startScan} style={{ marginLeft: 12 }}>
          Discover Therapeutic Opportunities
        </button>
      </div>

      {status && <p style={{ marginTop: 16 }}>Status: {status}</p>}

      {result && (
        <div style={{ marginTop: 24 }}>
          <h2>Top opportunities</h2>
          <pre style={{ background: "#f6f9fa", padding: 16, borderRadius: 8 }}>
            {JSON.stringify(result, null, 2)}
          </pre>
          <p style={{ fontStyle: "italic", color: "#666" }}>
            This is a decision-support prioritization draft, not a
            guarantee of drug success, a clinical prediction, or a
            regulatory prediction.
          </p>
        </div>
      )}
    </div>
  );
}
