import { ChevronRight, FileText, Inbox, LayoutDashboard, LogOut, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import Loading from "../components/Loading";
import { outboxDelete } from "../lib/db";
import { DASHBOARD_ROLES, type OutboxItem } from "../lib/types";
import { useApp } from "../state";
import { Chip, FORM_GROUPS, FORM_META, IconBadge, PREVENTIVE_TARGET, STATUS_META } from "../ui/meta";

export function StatusTag({ status }: { status: OutboxItem["status"] }) {
  return <Chip meta={STATUS_META[status]} />;
}

/** Icon of a form type, with a small sub-icon for the preventive checklists (pump / reservoir / network). */
export function FormIcon({ type, size = "md" }: { type: string; size?: "sm" | "md" | "lg" }) {
  const meta = FORM_META[type];
  if (!meta) return <IconBadge icon={FileText} tone="slate" size={size} />;
  const Sub = PREVENTIVE_TARGET[type];
  return (
    <span className="icon-stack" aria-hidden="true">
      <IconBadge icon={meta.icon} tone={meta.tone} size={size} />
      {Sub && size !== "sm" && (
        <span className="sub-icon"><Sub size={13} strokeWidth={2.5} /></span>
      )}
    </span>
  );
}

export default function Home() {
  const { me, ref, outbox, logout } = useApp();
  const nav = useNavigate();
  if (!ref || !me) return <Loading text="Chargement des données de référence…" />;
  const forms = ref.forms.forms.filter((f) => me.is_superuser || (me.role && f.roles.includes(me.role)));
  const recent = outbox.slice(0, 40);
  const initials = me.full_name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const groups = FORM_GROUPS.map((g) => ({ ...g, forms: forms.filter((f) => (FORM_META[f.type]?.group ?? "daily") === g.key) })).filter((g) => g.forms.length);

  return (
    <main className="page">
      <header className="page-head">
        <div className="hello">
          <span className="avatar" aria-hidden="true">{initials}</span>
          <div>
            <h1>Bonjour {me.full_name.split(" ")[0]}</h1>
            <p className="muted" style={{ margin: 0 }}>
              {me.role_label}{me.zone ? ` · ${ref.zones.find((z) => z.code === me.zone)?.name}` : ""} · {ref.site.name}
            </p>
          </div>
        </div>
        <div className="head-actions">
          {(me.is_superuser || DASHBOARD_ROLES.includes(me.role || "")) && (
            <Link className="btn primary" to="/tableau-de-bord" viewTransition>
              <LayoutDashboard size={18} aria-hidden="true" />Tableau de bord
            </Link>
          )}
          <button className="btn outline-danger small" onClick={logout}>
            <LogOut size={16} aria-hidden="true" />Déconnexion
          </button>
        </div>
      </header>

      {forms.length > 0 && (
        <section aria-labelledby="new-sheet">
          <h2 id="new-sheet">Nouvelle fiche</h2>
          {groups.map((g) => (
            <div key={g.key}>
              <h3 className="group-title">
                <IconBadge icon={g.icon} tone={g.tone} size="sm" />
                {g.title}
              </h3>
              <div className="tiles">
                {g.forms.map((f) => {
                  const meta = FORM_META[f.type];
                  return (
                    <button
                      key={f.type}
                      className={`tile tone-${meta?.tone ?? "slate"}`}
                      onClick={() => nav(`/fiche/nouvelle/${f.type}`, { viewTransition: true })}
                    >
                      <FormIcon type={f.type} size="lg" />
                      <span className="tile-text">
                        <span className="tile-title">{f.title}</span>
                        {meta?.hint && <span className="tile-hint">{meta.hint}</span>}
                      </span>
                      <ChevronRight size={20} className="tile-go" aria-hidden="true" />
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </section>
      )}

      <section aria-labelledby="my-sheets">
        <h2 id="my-sheets">Mes fiches</h2>
        <div className="card">
          {recent.length === 0 && (
            <div className="empty">
              <Inbox size={32} aria-hidden="true" />
              <span>Aucune fiche sur ce téléphone.</span>
            </div>
          )}
          <ul className="list">
            {recent.map((i) => (
              <li key={i.id} className="list-item">
                <Link to={`/fiche/${i.id}`} className="list-main" viewTransition>
                  <FormIcon type={i.form_type} size="md" />
                  <span className="list-text">
                    <span className="list-title">{i.title}</span>
                    <StatusTag status={i.status} />
                  </span>
                </Link>
                {i.status === "draft" && (
                  <button className="btn link danger small" onClick={() => window.confirm("Supprimer ce brouillon ?") && outboxDelete(i.id)}>
                    <Trash2 size={15} aria-hidden="true" />Supprimer
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </main>
  );
}
