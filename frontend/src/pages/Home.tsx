import { Link, useNavigate } from "react-router-dom";
import { outboxDelete } from "../lib/db";
import { DASHBOARD_ROLES, type OutboxItem } from "../lib/types";
import { useApp } from "../state";

const STATUS: Record<OutboxItem["status"], { label: string; cls: string }> = {
  draft: { label: "Brouillon", cls: "neutral" },
  queued: { label: "En attente d'envoi", cls: "warning" },
  synced: { label: "Envoyée", cls: "good" },
  conflict: { label: "Conflit à résoudre", cls: "critical" },
  invalid: { label: "Refusée : à corriger", cls: "critical" },
  forbidden: { label: "Non autorisée", cls: "critical" },
  error: { label: "Erreur", cls: "critical" },
};

export function StatusTag({ status }: { status: OutboxItem["status"] }) {
  const s = STATUS[status];
  return <span className={`tag ${s.cls}`}>{s.label}</span>;
}

export default function Home() {
  const { me, ref, outbox, logout } = useApp();
  const nav = useNavigate();
  if (!ref || !me) return <main className="page"><p>Chargement des données de référence…</p></main>;
  const forms = ref.forms.forms.filter((f) => me.is_superuser || (me.role && f.roles.includes(me.role)));
  const recent = outbox.slice(0, 40);
  return (
    <main className="page">
      <header className="page-head">
        <div>
          <h1>Bonjour {me.full_name.split(" ")[0]}</h1>
          <p className="muted">{me.role_label}{me.zone ? ` · ${ref.zones.find((z) => z.code === me.zone)?.name}` : ""} · {ref.site.name}</p>
        </div>
        <div className="head-actions">
          {(me.is_superuser || DASHBOARD_ROLES.includes(me.role || "")) && (
            <Link className="btn secondary" to="/tableau-de-bord">Tableau de bord</Link>
          )}
          <button className="btn link" onClick={logout}>Déconnexion</button>
        </div>
      </header>

      {forms.length > 0 && (
        <section aria-labelledby="new-sheet">
          <h2 id="new-sheet">Nouvelle fiche</h2>
          <div className="tiles">
            {forms.map((f) => (
              <button key={f.type} className="tile" onClick={() => nav(`/fiche/nouvelle/${f.type}`)}>
                {f.title}
              </button>
            ))}
          </div>
        </section>
      )}

      <section aria-labelledby="my-sheets">
        <h2 id="my-sheets">Mes fiches</h2>
        {recent.length === 0 && <p className="muted">Aucune fiche sur ce téléphone.</p>}
        <ul className="list">
          {recent.map((i) => (
            <li key={i.id} className="list-item">
              <Link to={`/fiche/${i.id}`} className="list-main">
                <span className="list-title">{i.title}</span>
                <StatusTag status={i.status} />
              </Link>
              {i.status === "draft" && (
                <button className="btn link" onClick={() => window.confirm("Supprimer ce brouillon ?") && outboxDelete(i.id)}>
                  Supprimer
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
