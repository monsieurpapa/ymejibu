/** IndexedDB storage: survives reloads and a full day offline. */
import { openDB, type IDBPDatabase } from "idb";
import type { OutboxItem } from "./types";

let dbp: Promise<IDBPDatabase> | null = null;

function db() {
  if (!dbp) {
    dbp = openDB("ymejibu-em", 1, {
      upgrade(d) {
        d.createObjectStore("kv");
        const o = d.createObjectStore("outbox", { keyPath: "id" });
        o.createIndex("status", "status");
      },
    });
  }
  return dbp;
}

export async function kvGet<T>(key: string): Promise<T | undefined> {
  try {
    return (await (await db()).get("kv", key)) as T | undefined;
  } catch {
    return undefined;
  }
}

export async function kvSet(key: string, value: unknown) {
  await (await db()).put("kv", value, key);
}

export async function kvDel(key: string) {
  await (await db()).delete("kv", key);
}

export async function outboxAll(): Promise<OutboxItem[]> {
  const items = (await (await db()).getAll("outbox")) as OutboxItem[];
  return items.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}

export async function outboxGet(id: string): Promise<OutboxItem | undefined> {
  return (await (await db()).get("outbox", id)) as OutboxItem | undefined;
}

export async function outboxPut(item: OutboxItem) {
  await (await db()).put("outbox", item);
  notify();
}

export async function outboxDelete(id: string) {
  await (await db()).delete("outbox", id);
  notify();
}

export async function clearAll() {
  const d = await db();
  await d.clear("kv");
  await d.clear("outbox");
  notify();
}

/** Tiny event bus so screens refresh when the outbox changes. */
const listeners = new Set<() => void>();
export function onOutboxChange(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
export function notify() {
  listeners.forEach((fn) => fn());
}
