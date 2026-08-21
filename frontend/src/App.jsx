import React, { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8100";

const RAILS = [
  { key: "fedwire", label: "FedWire (RTGS)" },
  { key: "chips", label: "CHIPS (net settlement)" },
  { key: "ach", label: "ACH (batch)" },
];

function Panel({ title, subtitle, children, accent }) {
  return (
    <div
      style={{
        border: `1px solid ${accent}`,
        borderRadius: 10,
        padding: 16,
        background: "#0d1117",
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: 2, color: accent }}>{title}</h3>
      <p style={{ marginTop: 0, color: "#9aa4af", fontSize: 13 }}>{subtitle}</p>
      {children}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #21262d" }}>
      <span style={{ color: "#9aa4af" }}>{label}</span>
      <span style={{ fontWeight: 600 }}>{value}</span>
    </div>
  );
}

function SizeBar({ label, classicalBytes, pqcBytes }) {
  const max = Math.max(classicalBytes, pqcBytes, 1);
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#9aa4af" }}>
        <span>{label}</span>
        <span>
          {classicalBytes}B → {pqcBytes}B ({(pqcBytes / Math.max(classicalBytes, 1)).toFixed(1)}x)
        </span>
      </div>
      <div style={{ background: "#21262d", borderRadius: 4, height: 8, marginBottom: 3 }}>
        <div style={{ width: `${(classicalBytes / max) * 100}%`, background: "#58a6ff", height: 8, borderRadius: 4 }} />
      </div>
      <div style={{ background: "#21262d", borderRadius: 4, height: 8 }}>
        <div style={{ width: `${(pqcBytes / max) * 100}%`, background: "#f0883e", height: 8, borderRadius: 4 }} />
      </div>
    </div>
  );
}

export default function App() {
  const [form, setForm] = useState({
    rail: "fedwire",
    originator: "Bank of Example NA",
    beneficiary: "Second National Bank",
    amount_usd: 1000000,
    reference: "INV-2026-0819",
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runCompare() {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/payments/compare`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!resp.ok) throw new Error(`API error ${resp.status}`);
      setResult(await resp.json());
    } catch (e) {
      setError(e.message + " — is the backend running at " + API_BASE + "?");
    } finally {
      setLoading(false);
    }
  }

  const classical = result?.classical;
  const hybrid = result?.hybrid_pqc;

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginBottom: 4 }}>PQC Payment Migration Dashboard</h1>
      <p style={{ color: "#9aa4af", marginTop: 0 }}>
        Classical (RSA/ECDSA + ECDH) vs. Hybrid PQC (ML-KEM-768 + X25519, ML-DSA-65 + ECDSA) on a simulated payment message
      </p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, margin: "20px 0", alignItems: "flex-end" }}>
        <div>
          <label style={{ display: "block", fontSize: 12, color: "#9aa4af" }}>Rail</label>
          <select
            value={form.rail}
            onChange={(e) => setForm({ ...form, rail: e.target.value })}
            style={{ padding: 8, borderRadius: 6, background: "#161b22", color: "#e6e6e6", border: "1px solid #30363d" }}
          >
            {RAILS.map((r) => (
              <option key={r.key} value={r.key}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 12, color: "#9aa4af" }}>Originator</label>
          <input
            value={form.originator}
            onChange={(e) => setForm({ ...form, originator: e.target.value })}
            style={{ padding: 8, borderRadius: 6, background: "#161b22", color: "#e6e6e6", border: "1px solid #30363d" }}
          />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 12, color: "#9aa4af" }}>Beneficiary</label>
          <input
            value={form.beneficiary}
            onChange={(e) => setForm({ ...form, beneficiary: e.target.value })}
            style={{ padding: 8, borderRadius: 6, background: "#161b22", color: "#e6e6e6", border: "1px solid #30363d" }}
          />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 12, color: "#9aa4af" }}>Amount (USD)</label>
          <input
            type="number"
            value={form.amount_usd}
            onChange={(e) => setForm({ ...form, amount_usd: parseFloat(e.target.value) })}
            style={{ padding: 8, borderRadius: 6, background: "#161b22", color: "#e6e6e6", border: "1px solid #30363d", width: 140 }}
          />
        </div>
        <button
          onClick={runCompare}
          disabled={loading}
          style={{
            padding: "10px 18px",
            borderRadius: 8,
            border: "1px solid #30363d",
            background: "#238636",
            color: "white",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          {loading ? "Running…" : "Compare Classical vs Hybrid PQC"}
        </button>
      </div>

      {error && <p style={{ color: "#f85149" }}>{error}</p>}

      {result && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
            <Panel title="Classical (RSA/ECDSA + ECDH)" subtitle="HNDL-exposed" accent="#58a6ff">
              <Row label="Handshake" value={classical.handshake.ok ? "OK" : "FAILED"} />
              <Row label="Handshake latency" value={`${classical.handshake.elapsed_ms} ms`} />
              <Row label="Signing" value={classical.signing.ok ? "OK" : "FAILED"} />
              <Row label="Signing latency" value={`${classical.signing.elapsed_ms} ms`} />
              <p style={{ fontSize: 13, color: "#9aa4af", marginTop: 12 }}>{classical.hndl_exposure.explanation}</p>
            </Panel>

            <Panel title="Hybrid PQC (ML-KEM-768 + X25519, ML-DSA-65)" subtitle="HNDL-resistant" accent="#f0883e">
              <Row label="Handshake" value={hybrid.handshake.ok ? "OK" : hybrid.handshake.error || "FAILED"} />
              <Row label="Handshake latency" value={`${hybrid.handshake.elapsed_ms} ms`} />
              <Row label="Signing" value={hybrid.signing.ok ? "OK" : hybrid.signing.error || "FAILED"} />
              <Row label="Signing latency" value={`${hybrid.signing.elapsed_ms} ms`} />
              <p style={{ fontSize: 13, color: "#9aa4af", marginTop: 12 }}>{hybrid.hndl_exposure.explanation}</p>
            </Panel>
          </div>

          {hybrid.handshake.sizes_bytes && hybrid.signing.sizes_bytes && (
            <Panel title="Wire-size overhead" subtitle="Blue = classical, orange = hybrid PQC — matches the paper's data-bloat analysis" accent="#3fb950">
              <SizeBar label="Public key (X25519 vs ML-KEM-768)" classicalBytes={32} pqcBytes={hybrid.handshake.sizes_bytes.mlkem_public_key} />
              <SizeBar label="Handshake ciphertext" classicalBytes={32} pqcBytes={hybrid.handshake.sizes_bytes.mlkem_ciphertext} />
              <SizeBar
                label="Signature (ECDSA vs ML-DSA-65)"
                classicalBytes={hybrid.signing.sizes_bytes.ecdsa_signature || 64}
                pqcBytes={hybrid.signing.sizes_bytes.mldsa_signature}
              />
            </Panel>
          )}

          {!hybrid.handshake.ok && (
            <p style={{ color: "#d29922", fontSize: 13, marginTop: 12 }}>
              Hybrid PQC self-test did not pass — this usually means <code>pqcrypto</code> isn't installed/built correctly in
              the backend container yet. Check <code>{API_BASE}/pqc/selftest</code> directly for the raw error.
            </p>
          )}
        </>
      )}
    </div>
  );
}
