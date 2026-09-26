import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { loadToken, refreshReference, setToken } from "./lib/api";
import { clearAll, kvGet, onOutboxChange, outboxAll } from "./lib/db";
import { isOnline, startAutoSync, syncNow, type SyncSummary } from "./lib/sync";
import type { Me, OutboxItem, Reference } from "./lib/types";

interface AppState {
  ready: boolean;
  me: Me | null;
  ref: Reference | null;
  online: boolean;
  outbox: OutboxItem[];
  lastSync: string | null;
  lastSummary: SyncSummary | null;
  syncing: boolean;
  setMe: (m: Me | null) => void;
  sync: () => Promise<void>;
  reloadReference: () => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AppState>(null as unknown as AppState);
export const useApp = () => useContext(Ctx);

export function AppProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [ref, setRef] = useState<Reference | null>(null);
  const [online, setOnline] = useState(isOnline());
  const [outbox, setOutbox] = useState<OutboxItem[]>([]);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [lastSummary, setLastSummary] = useState<SyncSummary | null>(null);
  const [syncing, setSyncing] = useState(false);

  const refreshOutbox = useCallback(async () => {
    setOutbox(await outboxAll());
    setLastSync((await kvGet<string>("last_sync")) ?? null);
  }, []);

  const reloadReference = useCallback(async () => {
    const cached = await kvGet<Reference>("reference");
    if (cached) setRef(cached);
    if (isOnline()) {
      try {
        const fresh = await refreshReference();
        if (fresh) setRef(fresh);
      } catch {
        /* offline or server down: keep the cached copy */
      }
    }
  }, []);

  const sync = useCallback(async () => {
    setSyncing(true);
    try {
      setLastSummary(await syncNow());
    } finally {
      setSyncing(false);
      await refreshOutbox();
    }
  }, [refreshOutbox]);

  useEffect(() => {
    (async () => {
      const t = await loadToken();
      const cachedMe = await kvGet<Me>("me");
      if (t && cachedMe) {
        setMe(cachedMe);
        await reloadReference();
      }
      await refreshOutbox();
      setReady(true);
    })();
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    const off = onOutboxChange(refreshOutbox);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
      off();
    };
  }, [refreshOutbox, reloadReference]);

  useEffect(() => {
    if (me) {
      reloadReference();
      startAutoSync((s) => {
        setLastSummary(s);
        refreshOutbox();
      });
    }
  }, [me, reloadReference, refreshOutbox]);

  const logout = useCallback(async () => {
    const pending = (await outboxAll()).filter((i) => i.status !== "synced");
    if (pending.length && !window.confirm(`${pending.length} fiche(s) non envoyée(s) seront perdues. Se déconnecter quand même ?`)) return;
    await clearAll();
    setToken(null);
    setMe(null);
    setRef(null);
  }, []);

  return (
    <Ctx.Provider value={{ ready, me, ref, online, outbox, lastSync, lastSummary, syncing, setMe, sync, reloadReference, logout }}>
      {children}
    </Ctx.Provider>
  );
}
