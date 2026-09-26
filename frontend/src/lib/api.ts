import { kvGet, kvSet } from "./db";
import type { Me, Reference } from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

let token: string | null = null;

export async function loadToken() {
  token = (await kvGet<string>("token")) ?? null;
  return token;
}

export function setToken(t: string | null) {
  token = t;
}

export async function api<T = any>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Token ${token}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const resp = await fetch(path, { ...init, headers, body });
  if (resp.status === 304) return undefined as T;
  if (!resp.ok) {
    let data: any = null;
    try {
      data = await resp.json();
    } catch {
      /* not json */
    }
    throw new ApiError(resp.status, data?.detail || `Erreur ${resp.status}`, data);
  }
  const ct = resp.headers.get("content-type") || "";
  return (ct.includes("json") ? resp.json() : resp.text()) as Promise<T>;
}

export async function login(username: string, password: string): Promise<Me> {
  const data = await api<{ token: string; me: Me }>("/api/auth/login/", { method: "POST", json: { username, password } });
  token = data.token;
  await kvSet("token", data.token);
  await kvSet("me", data.me);
  return data.me;
}

/** Reference data is cached in IndexedDB; ETag avoids re-downloading it on slow links. */
export async function refreshReference(): Promise<Reference | undefined> {
  const etag = await kvGet<string>("reference_etag");
  const headers = new Headers();
  if (token) headers.set("Authorization", `Token ${token}`);
  if (etag) headers.set("If-None-Match", etag);
  const resp = await fetch("/api/reference/", { headers });
  if (resp.status === 304) return kvGet<Reference>("reference");
  if (!resp.ok) throw new ApiError(resp.status, `Erreur ${resp.status}`);
  const data = (await resp.json()) as Reference;
  await kvSet("reference", data);
  const newTag = resp.headers.get("ETag");
  if (newTag) await kvSet("reference_etag", newTag);
  return data;
}

export async function download(path: string, filename: string) {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Token ${token}`);
  const resp = await fetch(path, { headers });
  if (!resp.ok) throw new ApiError(resp.status, `Erreur ${resp.status}`);
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
