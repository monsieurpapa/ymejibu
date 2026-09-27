import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { loadToken, refreshReference, setToken } from "./lib/api";
import { clearAll, kvGet, onOutboxChange, outboxAll } from "./lib/db";
import { isOnline, startAutoSync, syncNow, type SyncSummary } from "./lib/sync";
import type { Me, OutboxItem, Reference } from "./lib/types";

export interface Toast {
  id: number;
  text: string;
  tone: "green" | "red" | "amber" | "blue";
}

interface AppState {
  ready: boolean;
  me: Me | null;
  ref: Reference | null;
  online: boolean;
  outbox: OutboxItem[];
  lastSync: string | null;
  lastSummary: SyncSummary | null;
  syncing: boolean;
  toast: Toast | null;
  notify: (text: string, tone?: Toast["tone"]) => void;
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
  const [toast, setToast] = useState<Toast | null>(null);
  const toastTimer = useRef<number | undefined>(undefined);

  const notify = useCallback((text: string, tone: Toast["tone"] = "green") => {
    window.clearTimeout(toastTimer.current);
    setToast({ id: Date.now(), text, tone });
    toastTimer.current = window.setTimeout(() => setToast(null), 3500);
  }, []);

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
      const s = await syncNow();
      setLastSummary(s);
      // Wording avoids the status labels ("Envoyée", "En attente d'envoi") so lists stay unambiguous.
      if (s.sent > 0) notify(`${s.sent} fiche(s) transmise(s) au serveur`, "green");
      if (s.conflicts + s.invalid > 0) notify(`${s.conflicts + s.invalid} fiche(s) à corriger`, "red");
    } finally {
      setSyncing(false);
      await refreshOutbox();
    }
  }, [refreshOutbox, notify]);

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
        if (s.sent > 0) notify(`${s.sent} fiche(s) transmise(s) au serveur`, "green");
        refreshOutbox();
      });
    }
  }, [me, reloadReference, refreshOutbox, notify]);

  const logout = useCallback(async () => {
    const pending = (await outboxAll()).filter((i) => i.status !== "synced");
    if (pending.length && !window.confirm(`${pending.length} fiche(s) non envoyée(s) seront perdues. Se déconnecter quand même ?`)) return;
    await clearAll();
    setToken(null);
    setMe(null);
    setRef(null);
  }, []);

  return (
    <Ctx.Provider value={{ ready, me, ref, online, outbox, lastSync, lastSummary, syncing, toast, notify, setMe, sync, reloadReference, logout }}>
      {children}
    </Ctx.Provider>
  );
}
