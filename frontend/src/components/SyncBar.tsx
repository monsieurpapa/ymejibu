import { CloudUpload, Droplets, History, LoaderCircle, TriangleAlert, Wifi, WifiOff } from "lucide-react";
import { Link } from "react-router-dom";
import { useApp } from "../state";

function ago(iso: string | null) {
  if (!iso) return "jamais";
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "à l'instant";
  if (min < 60) return `il y a ${min} min`;
  const h = Math.round(min / 60);
  return h < 24 ? `il y a ${h} h` : new Date(iso).toLocaleDateString("fr-FR");
}

/** App bar: brand + connection state + outbox counter + manual send. */
export default function SyncBar() {
  const { online, outbox, lastSync, syncing, sync, lastSummary } = useApp();
  const queued = outbox.filter((i) => i.status === "queued").length;
  const problems = outbox.filter((i) => ["conflict", "invalid", "forbidden"].includes(i.status)).length;
  return (
    <div className={`syncbar ${online ? "on" : "off"}`} role="status" aria-live="polite" data-testid="syncbar">
      <Link to="/" className="brand" viewTransition aria-label="Yme Jibu, accueil">
        <span className="brand-mark" aria-hidden="true"><Droplets size={18} strokeWidth={2.5} /></span>
        <span className="brand-name" aria-hidden="true">Yme Jibu</span>
      </Link>
      <span className={`status-pill ${online ? "on" : "off"}`}>
        {online ? <Wifi size={14} aria-hidden="true" /> : <WifiOff size={14} aria-hidden="true" />}
        <span className="state">{online ? "En ligne" : "Hors ligne"}</span>
      </span>
      <span className="meta">
        <CloudUpload size={15} aria-hidden="true" />
        <strong data-testid="queued-count">{queued} en attente</strong>
      </span>
      {problems > 0 && (
        <span className="meta warn-text">
          <TriangleAlert size={15} aria-hidden="true" />
          {problems} à corriger
        </span>
      )}
      <span className="meta hide-sm">
        <History size={15} aria-hidden="true" />
        Dernier envoi : {ago(lastSync)}
      </span>
      <button
        className={`btn small on-dark ${queued > 0 && online ? "warning" : ""}`}
        onClick={sync}
        disabled={syncing || !online || queued === 0}
        data-testid="sync-button"
      >
        {syncing ? <LoaderCircle size={16} className="spin" aria-hidden="true" /> : <CloudUpload size={16} aria-hidden="true" />}
        {syncing ? "Envoi…" : "Envoyer"}
      </button>
      {lastSummary?.error && online && <span className="meta warn-text small full">Serveur injoignable, nouvel essai automatique.</span>}
    </div>
  );
}
