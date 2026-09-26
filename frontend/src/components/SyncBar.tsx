import { useApp } from "../state";

function ago(iso: string | null) {
  if (!iso) return "jamais";
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "à l'instant";
  if (min < 60) return `il y a ${min} min`;
  const h = Math.round(min / 60);
  return h < 24 ? `il y a ${h} h` : new Date(iso).toLocaleDateString("fr-FR");
}

export default function SyncBar() {
  const { online, outbox, lastSync, syncing, sync, lastSummary } = useApp();
  const queued = outbox.filter((i) => i.status === "queued").length;
  const problems = outbox.filter((i) => ["conflict", "invalid", "forbidden"].includes(i.status)).length;
  return (
    <div className={`syncbar ${online ? "on" : "off"}`} role="status" aria-live="polite" data-testid="syncbar">
      <span className="dot" aria-hidden />
      <span className="state">{online ? "En ligne" : "Hors ligne"}</span>
      <span className="sep" aria-hidden>·</span>
      <span data-testid="queued-count">{queued} en attente</span>
      {problems > 0 && (
        <>
          <span className="sep" aria-hidden>·</span>
          <span className="warn-text">{problems} à corriger</span>
        </>
      )}
      <span className="sep hide-sm" aria-hidden>·</span>
      <span className="hide-sm">Dernier envoi : {ago(lastSync)}</span>
      <button className="btn small secondary" onClick={sync} disabled={syncing || !online || queued === 0} data-testid="sync-button">
        {syncing ? "Envoi…" : "Envoyer"}
      </button>
      {lastSummary?.error && online && <span className="warn-text small">Serveur injoignable, nouvel essai automatique.</span>}
    </div>
  );
}
