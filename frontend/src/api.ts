// Typed client for the ShelfSignal Django REST API.
export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export interface Sku { code: string; brand: string; category: string; name: string }
export interface PackChange {
  sku: Sku; kind: "shrinkflation" | "resize" | "upsize";
  grams_before: number; grams_after: number; price_change_pct: number;
  per_gram_change_pct: number; first_seen: string; stores_changed: number;
  stores_carrying: number; confidence: number;
}
export interface Launch {
  sku: Sku; first_seen: string; days_to_25: number | null; days_to_50: number | null;
  reach_pct: number; curve: [number, number][];
}
export interface IndexPoint { city: string; month: string; pack_index: number; per_gram_index: number; shock: boolean }
export interface Run { id: number; status: string; observations_scanned: number; duration_ms: number; error: string }
export interface Brief { source: string; text: string }

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${path} returned ${res.status}`);
  return res.json() as Promise<T>;
}

export const fetchPackChanges = () => get<{ results: PackChange[] }>("/signals/pack-changes/").then(r => r.results);
export const fetchLaunches = () => get<{ results: Launch[] }>("/signals/launches/").then(r => r.results);
export const fetchIndex = () => get<{ results: IndexPoint[] }>("/signals/price-index/").then(r => r.results);
export const fetchBrief = () => get<Brief>("/signals/brief/");
export const fetchRun = (id: number) => get<Run>(`/runs/${id}/`);

export async function startRun(token: string): Promise<Run> {
  const res = await fetch(`${API}/runs/`, { method: "POST", headers: { Authorization: `Token ${token}` } });
  if (!res.ok) throw new Error(res.status === 401 ? "Invalid or missing API token" : `Run failed (${res.status})`);
  return res.json() as Promise<Run>;
}
