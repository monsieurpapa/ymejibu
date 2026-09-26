/** Outbox synchronisation: push queued sheets, keep conflicts for the user to resolve. */
import { api, ApiError } from "./api";
import { kvSet, outboxAll, outboxGet, outboxPut, notify } from "./db";
import type { OutboxItem } from "./types";

type Result = {
  id: string;
  status: "created" | "updated" | "unchanged" | "conflict" | "invalid" | "forbidden" | "locked" | "error" | "retry";
  version?: number;
  server?: OutboxItem["server"] & { payload: any };
  errors?: { field: string; message: string }[];
};

let running: Promise<SyncSummary> | null = null;

export interface SyncSummary {
  sent: number;
  conflicts: number;
  invalid: number;
  offline: boolean;
  error?: string;
}

export function isOnline() {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

export function syncNow(): Promise<SyncSummary> {
  if (!running) {
    running = doSync().finally(() => {
      running = null;
    });
  }
  return running;
}

async function doSync(): Promise<SyncSummary> {
  const summary: SyncSummary = { sent: 0, conflicts: 0, invalid: 0, offline: false };
  const queued = (await outboxAll()).filter((i) => i.status === "queued");
  if (!queued.length) return summary;
  if (!isOnline()) return { ...summary, offline: true };
  // Small batches: a lost connection only loses the current batch, which is retried.
  for (let k = 0; k < queued.length; k += 10) {
    const batch = queued.slice(k, k + 10);
    let results: Result[];
    try {
      const resp = await api<{ results: Result[] }>("/api/sync/push/", {
        method: "POST",
        json: {
          items: batch.map((i) => ({
            id: i.id,
            form_type: i.form_type,
            payload: i.payload,
            base_version: i.version,
            client_updated_at: i.updated_at,
            force: (i as any).force === true,
          })),
        },
      });
      results = resp.results;
    } catch (e) {
      const offline = !(e instanceof ApiError);
      return { ...summary, offline, error: e instanceof Error ? e.message : String(e) };
    }
    for (const r of results) {
      const item = await outboxGet(r.id);
      if (!item) continue;
      // The user may have edited the item while it was being sent: keep the newer local copy queued.
      const sentVersion = batch.find((b) => b.id === r.id)?.updated_at;
      const editedMeanwhile = sentVersion !== item.updated_at;
      const next: OutboxItem = { ...item };
      delete (next as any).force;
      if (r.status === "created" || r.status === "updated" || r.status === "unchanged") {
        next.version = r.version ?? r.server?.version ?? item.version;
        next.server = null;
        next.errors = [];
        if (!editedMeanwhile) {
          next.status = "synced";
          next.synced_at = new Date().toISOString();
          if (r.server?.payload) next.payload = r.server.payload; // server-assigned incident number, stored photos
        }
        summary.sent++;
      } else if (r.status === "conflict" || r.status === "locked") {
        next.status = "conflict";
        next.server = r.server ?? null;
        summary.conflicts++;
      } else if (r.status === "invalid") {
        next.status = "invalid";
        next.errors = r.errors ?? [];
        summary.invalid++;
      } else if (r.status === "forbidden" || r.status === "error") {
        // Kept on the phone, shown to the user, not retried in a loop; the other sheets keep flowing.
        next.status = r.status;
        next.errors = r.errors ?? [];
      }
      await outboxPut(next);
    }
  }
  await kvSet("last_sync", new Date().toISOString());
  notify();
  return summary;
}

/** Keep my version: resend on top of the server version. */
export async function keepMine(id: string) {
  const item = await outboxGet(id);
  if (!item?.server) return;
  await outboxPut({ ...item, status: "queued", version: item.server.version, server: null, updated_at: new Date().toISOString() });
}

/** Take the server version and drop my local changes. */
export async function takeServer(id: string) {
  const item = await outboxGet(id);
  if (!item?.server) return;
  await outboxPut({
    ...item,
    status: "synced",
    payload: item.server.payload,
    version: item.server.version,
    server: null,
    updated_at: new Date().toISOString(),
    synced_at: new Date().toISOString(),
  });
}

let started = false;
export function startAutoSync(onDone?: (s: SyncSummary) => void) {
  if (started) return;
  started = true;
  const run = () => syncNow().then((s) => onDone?.(s));
  window.addEventListener("online", run);
  setInterval(() => {
    if (isOnline()) run();
  }, 60_000);
  run();
}
