import { useCallback, useEffect, useMemo, useState } from "react";
import { type Brief, type IndexPoint, type Launch, type PackChange, fetchBrief, fetchIndex, fetchLaunches, fetchPackChanges, fetchRun, startRun } from "./api";
import { LineChart } from "./LineChart";
import "./App.css";

const COLORS = ["#2563eb", "#d97706", "#059669", "#db2777"];

export default function App() {
  const [pack, setPack] = useState<PackChange[]>([]);
  const [launches, setLaunches] = useState<Launch[]>([]);
  const [index, setIndex] = useState<IndexPoint[]>([]);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [city, setCity] = useState("Kolkata");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, l, i, b] = await Promise.all([fetchPackChanges(), fetchLaunches(), fetchIndex(), fetchBrief()]);
      setPack(p); setLaunches(l); setIndex(i); setBrief(b); setError("");
    } catch (e) {
      setError((e as Error).message + ". Start a detector run first.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function run() {
    try {
      setStatus("Queued...");
      const r = await startRun(token);
      // Poll the background job until the Celery worker finishes it.
      for (let i = 0; i < 60; i++) {
        const cur = await fetchRun(r.id);
        setStatus(`Run #${cur.id}: ${cur.status}`);
        if (cur.status === "done") { setStatus(`Run #${cur.id} scanned ${cur.observations_scanned.toLocaleString()} observations in ${cur.duration_ms} ms`); break; }
        if (cur.status === "failed") throw new Error(cur.error);
        await new Promise(res => setTimeout(res, 1000));
      }
      await load();
    } catch (e) { setStatus(""); setError((e as Error).message); }
  }

  const cities = useMemo(() => [...new Set(index.map(p => p.city))].sort(), [index]);
  const cityPts = index.filter(p => p.city === city);
  const months = cityPts.map(p => p.month.slice(2));
  const shrink = pack.filter(p => p.kind === "shrinkflation");
  const latest = cityPts[cityPts.length - 1];

  return (
    <main>
      <header>
        <div>
          <h1>ShelfSignal</h1>
          <p className="muted">Market signals mined from shelf-audit data. Prototype on simulated data.</p>
        </div>
        <div className="run">
          <input placeholder="API token" value={token} onChange={e => setToken(e.target.value)} />
          <button onClick={run} disabled={!token}>Run detectors</button>
          <span className="muted">{status}</span>
        </div>
      </header>
      {error && <p className="error">{error}</p>}

      <section className="kpis">
        <div><b>{shrink.length}</b><span>shrinkflation events</span></div>
        <div><b>{launches.length}</b><span>new launches tracked</span></div>
        <div><b>{latest ? (latest.per_gram_index - latest.pack_index).toFixed(1) : "-"}</b><span>pts hidden inflation, {city}</span></div>
        <div><b>{index.filter(p => p.shock).length}</b><span>city price shocks</span></div>
      </section>

      {brief && <section className="card"><h2>Weekly brief</h2><p>{brief.text}</p><p className="muted small">Written by: {brief.source}</p></section>}

      <section className="card">
        <h2>Pack changes</h2>
        <table>
          <thead><tr><th>SKU</th><th>Type</th><th>Pack</th><th>Shelf price</th><th>Price per gram</th><th>First seen</th><th>Stores</th></tr></thead>
          <tbody>
            {pack.map(p => (
              <tr key={p.sku.code + p.grams_after}>
                <td>{p.sku.name}</td>
                <td><span className={`tag ${p.kind}`}>{p.kind}</span></td>
                <td>{p.grams_before}g → {p.grams_after}g</td>
                <td>{p.price_change_pct > 0 ? "+" : ""}{p.price_change_pct}%</td>
                <td><b>{p.per_gram_change_pct > 0 ? "+" : ""}{p.per_gram_change_pct}%</b></td>
                <td>{p.first_seen}</td>
                <td>{p.stores_changed}/{p.stores_carrying}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="grid2">
        <section className="card">
          <h2>Price index: pack vs per gram</h2>
          <select value={city} onChange={e => setCity(e.target.value)}>{cities.map(c => <option key={c}>{c}</option>)}</select>
          <LineChart xLabels={months} series={[
            { name: "Per gram", color: "#dc2626", points: cityPts.map((p, i) => [i, p.per_gram_index]) },
            { name: "Pack price", color: "#2563eb", dashed: true, points: cityPts.map((p, i) => [i, p.pack_index]) },
          ]} />
          <p className="legend"><span style={{ color: "#dc2626" }}>━ per gram</span> <span style={{ color: "#2563eb" }}>┅ pack price</span>
            {cityPts.filter(p => p.shock).map(p => <span key={p.month} className="shock">shock {p.month}</span>)}</p>
        </section>
        <section className="card">
          <h2>Launch velocity (share of stores stocking)</h2>
          <LineChart yMin={0} yMax={1} yFormat={v => `${Math.round(v * 100)}%`}
            series={launches.map((l, i) => ({ name: l.sku.code, color: COLORS[i % 4], points: l.curve }))} />
          <p className="legend">{launches.map((l, i) => <span key={l.sku.code} style={{ color: COLORS[i % 4] }}>━ {l.sku.code}: 50% in {l.days_to_50 ?? "–"}d</span>)}</p>
        </section>
      </div>
    </main>
  );
}
