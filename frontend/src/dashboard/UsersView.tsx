import {
  Ban, BookUser, Check, CircleCheck, CircleUserRound, Copy, Eye, EyeOff, KeyRound, LoaderCircle, Pencil, Search, ShieldCheck,
  Trash2, UserCheck, UserPlus, Users, Wand2, X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useApp } from "../state";
import Modal from "../ui/Modal";
import { Chip, IconBadge, type Tone } from "../ui/meta";

interface Account {
  id: number; username: string; email: string; full_name: string; title: string; role: string | null; role_label: string;
  zone: string | null; zone_name: string | null; person_id: number | null; is_active: boolean; is_superuser: boolean;
  last_login: string | null; date_joined: string;
}
interface RoleInfo {
  value: string; label: string; forms: string[]; dashboard: boolean; validate_sheets: boolean; manage_reference: boolean;
  stock_write: boolean; read_only: boolean; zone_scoped: boolean;
}
interface Options {
  roles: RoleInfo[]; zones: { code: string; name: string }[];
  unlinked_people: { id: number; full_name: string; title: string; role: string; zone: string | null }[];
}
type Errors = Record<string, string>;

export const ROLE_TONE: Record<string, Tone> = {
  RESP_TECH: "blue", ADJOINT: "blue", DATA_OFFICER: "violet", ZONE_TECH: "teal", PUMP_FOCAL: "teal",
  STORAGE_FOCAL: "teal", SSE: "amber", FUNDER: "slate", CONTRACTOR: "orange",
};

const EMPTY = { username: "", full_name: "", email: "", title: "", role: "", zone: "", is_active: true, is_superuser: false, password: "", person_id: "" };

function errorsOf(err: unknown): Errors {
  const out: Errors = {};
  const body = err instanceof ApiError ? (err.body as any) : null;
  if (body && typeof body === "object") {
    for (const [k, v] of Object.entries(body)) out[k] = Array.isArray(v) ? v.join(" ") : String(v);
  }
  if (!Object.keys(out).length) out.detail = err instanceof Error ? err.message : "Erreur";
  return out;
}

/** Strong, readable password: 3 words-ish chunks + digits + symbol (no ambiguous characters). */
function generatePassword() {
  const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const rnd = new Uint32Array(14);
  crypto.getRandomValues(rnd);
  const s = Array.from(rnd, (n) => chars[n % chars.length]).join("");
  return `${s.slice(0, 5)}-${s.slice(5, 10)}-${s.slice(10)}!`;
}

function initials(a: Account) {
  const base = a.full_name || a.username;
  return base.split(/[\s._-]+/).filter(Boolean).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

function when(iso: string | null) {
  if (!iso) return "jamais";
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
}

export default function UsersView() {
  const { me, notify } = useApp();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [opts, setOpts] = useState<Options | null>(null);
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [editing, setEditing] = useState<Account | "new" | null>(null);
  const [pwFor, setPwFor] = useState<Account | null>(null);
  const [confirm, setConfirm] = useState<{ kind: "delete" | "deactivate"; account: Account } | null>(null);
  const [loadError, setLoadError] = useState("");

  const load = useCallback(() => {
    Promise.all([api<Account[]>("/api/users/"), api<Options>("/api/users/options/")])
      .then(([a, o]) => {
        setAccounts(a);
        setOpts(o);
        setLoadError("");
      })
      .catch((e) => setLoadError(e.message));
  }, []);
  useEffect(load, [load]);

  const roleLabel = useCallback((v: string | null) => opts?.roles.find((r) => r.value === v)?.label ?? v ?? "", [opts]);
  const shown = useMemo(() => (accounts ?? []).filter((a) => {
    const text = `${a.full_name} ${a.username} ${a.email} ${a.title} ${a.role_label}`.toLowerCase();
    if (q && !text.includes(q.toLowerCase())) return false;
    if (roleFilter === "SUPER" ? !a.is_superuser : roleFilter && a.role !== roleFilter) return false;
    if (statusFilter === "active" && !a.is_active) return false;
    if (statusFilter === "inactive" && a.is_active) return false;
    return true;
  }), [accounts, q, roleFilter, statusFilter]);

  const toggleActive = async (a: Account) => {
    try {
      await api(`/api/users/${a.id}/`, { method: "PATCH", json: { is_active: !a.is_active } });
      notify(a.is_active ? `Compte ${a.username} désactivé : il ne peut plus se connecter.` : `Compte ${a.username} réactivé.`,
        a.is_active ? "amber" : "green");
      load();
    } catch (e) {
      notify(errorsOf(e).is_active || errorsOf(e).is_superuser || errorsOf(e).detail, "red");
    }
  };

  const remove = async (a: Account) => {
    try {
      await api(`/api/users/${a.id}/`, { method: "DELETE" });
      notify(`Compte ${a.username} supprimé. Sa fiche du personnel est conservée.`, "green");
      load();
    } catch (e) {
      notify(errorsOf(e).detail, "red");
    }
  };

  if (!me?.is_superuser) {
    return <p className="banner critical" role="alert"><Ban size={20} aria-hidden="true" /><span className="banner-body">Réservé aux super administrateurs.</span></p>;
  }

  return (
    <>
      <section className="card">
        <div className="toolbar">
          <h2 style={{ margin: "0 auto 0 0" }}><IconBadge icon={Users} tone="blue" size="sm" />Utilisateurs et accès</h2>
          <button className="btn primary" onClick={() => setEditing("new")}><UserPlus size={18} aria-hidden="true" />Nouvel utilisateur</button>
        </div>
        <div className="toolbar filters-inline">
          <span className="search-field">
            <Search size={16} aria-hidden="true" />
            <input aria-label="Rechercher un utilisateur" placeholder="Nom, identifiant, e-mail…" value={q} onChange={(e) => setQ(e.target.value)} />
          </span>
          <select aria-label="Filtrer par rôle" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
            <option value="">Tous les rôles</option>
            <option value="SUPER">Super administrateurs</option>
            {opts?.roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
          <select aria-label="Filtrer par état" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">Actifs et désactivés</option>
            <option value="active">Actifs</option>
            <option value="inactive">Désactivés</option>
          </select>
        </div>
        {loadError && <p className="error" role="alert">{loadError}</p>}
        {!accounts && !loadError && <div className="skeleton" style={{ height: 180 }} aria-busy="true" />}
        {accounts && shown.length === 0 && <div className="empty"><Users size={32} aria-hidden="true" /><span>Aucun compte ne correspond.</span></div>}
        <ul className="list user-list">
          {shown.map((a) => (
            <li key={a.id} className={`list-item user-row${a.is_active ? "" : " inactive"}`}>
              <div className="user-main">
                <span className={`avatar sm tone-${a.is_superuser ? "violet" : ROLE_TONE[a.role ?? ""] ?? "slate"}`} aria-hidden="true">{initials(a)}</span>
                <span className="list-text">
                  <span className="list-title">{a.full_name || a.username}{a.username === me.username && <span className="muted small"> (vous)</span>}</span>
                  <span className="muted small">@{a.username}{a.email ? ` · ${a.email}` : ""} · dernière connexion : {when(a.last_login)}</span>
                  <span className="row-inline" style={{ marginTop: 2, gap: 6 }}>
                    {a.is_superuser && <Chip meta={{ icon: ShieldCheck, tone: "violet", label: "Super administrateur" }} />}
                    {a.role && <Chip meta={{ icon: BookUser, tone: ROLE_TONE[a.role] ?? "slate", label: roleLabel(a.role) }} />}
                    {a.zone && <Chip meta={{ icon: CircleUserRound, tone: "slate", label: a.zone_name ?? a.zone }} />}
                    <Chip meta={a.is_active ? { icon: CircleCheck, tone: "green", label: "Actif" } : { icon: Ban, tone: "slate", label: "Désactivé" }} />
                  </span>
                </span>
              </div>
              <div className="user-actions">
                <button className="btn secondary small" onClick={() => setEditing(a)}><Pencil size={15} aria-hidden="true" />Modifier</button>
                <button className="btn ghost small" onClick={() => setPwFor(a)}><KeyRound size={15} aria-hidden="true" />Mot de passe</button>
                {a.is_active ? (
                  <button className="btn outline-warning small" onClick={() => setConfirm({ kind: "deactivate", account: a })} disabled={a.username === me.username}>
                    <Ban size={15} aria-hidden="true" />Désactiver
                  </button>
                ) : (
                  <button className="btn outline-success small" onClick={() => toggleActive(a)}><UserCheck size={15} aria-hidden="true" />Réactiver</button>
                )}
                <button className="btn outline-danger small" onClick={() => setConfirm({ kind: "delete", account: a })} disabled={a.username === me.username}>
                  <Trash2 size={15} aria-hidden="true" />Supprimer
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {opts && <RightsMatrix roles={opts.roles} />}

      {editing && opts && (
        <AccountForm account={editing === "new" ? null : editing} opts={opts} self={me.username}
          onClose={() => setEditing(null)}
          onSaved={(msg) => { setEditing(null); notify(msg, "green"); load(); }} />
      )}
      {pwFor && <PasswordDialog account={pwFor} onClose={() => setPwFor(null)} onDone={(msg) => { setPwFor(null); notify(msg, "green"); }} />}
      {confirm && (
        <Modal title={confirm.kind === "delete" ? "Supprimer le compte ?" : "Désactiver le compte ?"}
          icon={<IconBadge icon={confirm.kind === "delete" ? Trash2 : Ban} tone={confirm.kind === "delete" ? "red" : "amber"} size="sm" />}
          onClose={() => setConfirm(null)}
          footer={<>
            <button className="btn secondary" onClick={() => setConfirm(null)}>Annuler</button>
            <button className={`btn ${confirm.kind === "delete" ? "danger" : "warning"}`} onClick={() => {
              const c = confirm;
              setConfirm(null);
              if (c.kind === "delete") remove(c.account); else toggleActive(c.account);
            }}>
              {confirm.kind === "delete" ? <Trash2 size={18} aria-hidden="true" /> : <Ban size={18} aria-hidden="true" />}
              {confirm.kind === "delete" ? "Supprimer définitivement" : "Désactiver"}
            </button>
          </>}>
          {confirm.kind === "delete" ? (
            <>
              <p><strong>{confirm.account.full_name || confirm.account.username}</strong> ne pourra plus se connecter et le compte sera effacé.</p>
              <p className="muted small">La fiche du personnel est conservée, mais les fiches déjà envoyées n'afficheront plus son nom.
                Pour garder l'historique, préférez <strong>Désactiver</strong>.</p>
            </>
          ) : (
            <p><strong>{confirm.account.full_name || confirm.account.username}</strong> sera déconnecté de tous ses téléphones et ne pourra plus se
              connecter. L'historique est conservé ; le compte peut être réactivé à tout moment.</p>
          )}
        </Modal>
      )}
    </>
  );
}

function AccountForm({ account, opts, self, onClose, onSaved }: {
  account: Account | null; opts: Options; self: string; onClose: () => void; onSaved: (msg: string) => void;
}) {
  const creating = account === null;
  const [f, setF] = useState(() => account
    ? { ...EMPTY, username: account.username, full_name: account.full_name, email: account.email, title: account.title,
        role: account.role ?? "", zone: account.zone ?? "", is_active: account.is_active, is_superuser: account.is_superuser }
    : { ...EMPTY });
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const isSelf = account?.username === self;
  const role = opts.roles.find((r) => r.value === f.role);
  const set = (k: keyof typeof EMPTY, v: any) => setF((x) => ({ ...x, [k]: v }));

  const pickPerson = (id: string) => {
    const p = opts.unlinked_people.find((x) => String(x.id) === id);
    setF((x) => ({ ...x, person_id: id, ...(p ? { full_name: p.full_name || x.full_name, title: p.title, role: p.role, zone: p.zone ?? "" } : {}) }));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    const body: Record<string, unknown> = {
      username: f.username.trim(), full_name: f.full_name.trim(), email: f.email.trim(), title: f.title.trim(),
      role: f.role || null, zone: f.zone || null, is_active: f.is_active, is_superuser: f.is_superuser,
    };
    if (creating) {
      body.password = f.password;
      if (f.person_id) body.person_id = Number(f.person_id);
    }
    try {
      await api(creating ? "/api/users/" : `/api/users/${account!.id}/`, { method: creating ? "POST" : "PATCH", json: body });
      onSaved(creating ? `Compte ${body.username} créé.` : `Compte ${body.username} mis à jour.`);
    } catch (err) {
      setErrors(errorsOf(err));
    } finally {
      setBusy(false);
    }
  };

  const err = (k: string) => errors[k] && <p className="error" id={`u-${k}-err`} role="alert">{errors[k]}</p>;
  return (
    <Modal wide title={creating ? "Nouvel utilisateur" : `Modifier ${account!.username}`}
      icon={<IconBadge icon={creating ? UserPlus : Pencil} tone="blue" size="sm" />} onClose={onClose}
      footer={<>
        <button type="button" className="btn secondary" onClick={onClose}>Annuler</button>
        <button type="submit" form="account-form" className="btn success" disabled={busy}>
          {busy ? <LoaderCircle size={18} className="spin" aria-hidden="true" /> : <Check size={18} aria-hidden="true" />}
          {creating ? "Créer le compte" : "Enregistrer"}
        </button>
      </>}>
      <form id="account-form" onSubmit={submit} noValidate>
        {errors.detail && <p className="banner critical" role="alert"><span className="banner-body">{errors.detail}</span></p>}
        {creating && opts.unlinked_people.length > 0 && (
          <div className="field">
            <label className="label" htmlFor="u-person">Lier à une fiche du personnel existante</label>
            <select id="u-person" value={f.person_id} onChange={(e) => pickPerson(e.target.value)}>
              <option value="">— Aucune (nouvelle personne) —</option>
              {opts.unlinked_people.map((p) => <option key={p.id} value={p.id}>{p.full_name || "(nom à compléter)"} — {p.title}</option>)}
            </select>
            <p className="hint">Les postes importés du classeur Personnel n'ont pas encore de compte : choisissez-en un pour reprendre son rôle et sa zone.</p>
            {err("person_id")}
          </div>
        )}
        <div className="grid-cols">
          <div className={`field ${errors.username ? "has-error" : ""}`}>
            <label className="label" htmlFor="u-username">Identifiant<span className="req" aria-hidden> *</span></label>
            <input id="u-username" autoCapitalize="none" autoComplete="off" required value={f.username} onChange={(e) => set("username", e.target.value)} />
            {err("username")}
          </div>
          <div className="field">
            <label className="label" htmlFor="u-fullname">Nom complet</label>
            <input id="u-fullname" value={f.full_name} onChange={(e) => set("full_name", e.target.value)} />
          </div>
          <div className={`field ${errors.email ? "has-error" : ""}`}>
            <label className="label" htmlFor="u-email">E-mail</label>
            <input id="u-email" type="email" value={f.email} onChange={(e) => set("email", e.target.value)} />
            {err("email")}
          </div>
          <div className="field">
            <label className="label" htmlFor="u-title">Fonction (intitulé du poste)</label>
            <input id="u-title" value={f.title} onChange={(e) => set("title", e.target.value)} placeholder={role?.label ?? ""} />
          </div>
        </div>

        <fieldset className="plain access-box">
          <legend className="label">Niveau d'accès</legend>
          <div className="grid-cols">
            <div className={`field ${errors.role ? "has-error" : ""}`}>
              <label className="label" htmlFor="u-role">Rôle{!f.is_superuser && <span className="req" aria-hidden> *</span>}</label>
              <select id="u-role" value={f.role} onChange={(e) => set("role", e.target.value)}>
                <option value="">{f.is_superuser ? "— Aucun rôle terrain —" : "— Choisir —"}</option>
                {opts.roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
              {err("role")}
            </div>
            <div className={`field ${errors.zone ? "has-error" : ""}`}>
              <label className="label" htmlFor="u-zone">Zone{role?.zone_scoped && " (recommandée)"}</label>
              <select id="u-zone" value={f.zone} onChange={(e) => set("zone", e.target.value)}>
                <option value="">— Toutes / aucune —</option>
                {opts.zones.map((z) => <option key={z.code} value={z.code}>{z.name}</option>)}
              </select>
              {err("zone")}
            </div>
          </div>
          {role && <RoleSummary role={role} />}
          <label className="check-line">
            <input type="checkbox" checked={f.is_superuser} disabled={isSelf} onChange={(e) => set("is_superuser", e.target.checked)} />
            <span><strong><ShieldCheck size={15} aria-hidden="true" style={{ verticalAlign: -2 }} /> Super administrateur</strong>
              <span className="muted small"> — tous les droits, y compris la gestion des utilisateurs et l'administration Django.</span></span>
          </label>
          {err("is_superuser")}
          <label className="check-line">
            <input type="checkbox" checked={f.is_active} disabled={isSelf} onChange={(e) => set("is_active", e.target.checked)} />
            <span><strong>Compte actif</strong><span className="muted small"> — décoché : la personne ne peut plus se connecter.</span></span>
          </label>
          {err("is_active")}
          {isSelf && <p className="hint">Vous ne pouvez pas retirer vos propres droits ni désactiver votre compte.</p>}
        </fieldset>

        {creating && (
          <PasswordField value={f.password} onChange={(v) => set("password", v)} show={show} setShow={setShow} error={errors.password} />
        )}
      </form>
    </Modal>
  );
}

function PasswordField({ value, onChange, show, setShow, error }: {
  value: string; onChange: (v: string) => void; show: boolean; setShow: (b: boolean) => void; error?: string;
}) {
  return (
    <div className={`field ${error ? "has-error" : ""}`}>
      <label className="label" htmlFor="u-password">Mot de passe<span className="req" aria-hidden> *</span></label>
      <div className="row-inline" style={{ marginTop: 0, flexWrap: "nowrap" }}>
        <input id="u-password" type={show ? "text" : "password"} autoComplete="new-password" value={value} onChange={(e) => onChange(e.target.value)} />
        <button type="button" className="btn ghost small" onClick={() => setShow(!show)} aria-label={show ? "Masquer" : "Afficher"}>
          {show ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
        </button>
      </div>
      <div className="row-inline" style={{ gap: 8 }}>
        <button type="button" className="btn secondary small" onClick={() => { onChange(generatePassword()); setShow(true); }}>
          <Wand2 size={15} aria-hidden="true" />Générer
        </button>
        {value && (
          <button type="button" className="btn ghost small" onClick={() => navigator.clipboard?.writeText(value)}>
            <Copy size={15} aria-hidden="true" />Copier
          </button>
        )}
      </div>
      <p className="hint">8 caractères minimum, pas uniquement des chiffres ni un mot de passe courant. Transmettez-le à la personne en main propre.</p>
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}

function PasswordDialog({ account, onClose, onDone }: { account: Account; onClose: () => void; onDone: (msg: string) => void }) {
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api(`/api/users/${account.id}/set-password/`, { method: "POST", json: { password: pw } });
      onDone(`Nouveau mot de passe enregistré pour ${account.username}. Ses téléphones devront se reconnecter.`);
    } catch (err) {
      const e2 = errorsOf(err);
      setError(e2.password || e2.detail);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title={`Mot de passe de ${account.username}`} icon={<IconBadge icon={KeyRound} tone="amber" size="sm" />} onClose={onClose}
      footer={<>
        <button type="button" className="btn secondary" onClick={onClose}><X size={18} aria-hidden="true" />Annuler</button>
        <button type="submit" form="pw-form" className="btn success" disabled={busy || !pw}>
          {busy ? <LoaderCircle size={18} className="spin" aria-hidden="true" /> : <KeyRound size={18} aria-hidden="true" />}Définir le mot de passe
        </button>
      </>}>
      <form id="pw-form" onSubmit={save}>
        <PasswordField value={pw} onChange={setPw} show={show} setShow={setShow} error={error} />
        <p className="muted small">La personne sera déconnectée de tous ses appareils. Ses fiches non envoyées restent sur le téléphone et partiront
          après reconnexion.</p>
      </form>
    </Modal>
  );
}

function RoleSummary({ role }: { role: RoleInfo }) {
  const items: [boolean, string][] = [
    [role.forms.length > 0, role.forms.length ? `Saisit : ${role.forms.join(", ")}` : "Aucune fiche terrain"],
    [role.dashboard, "Tableau de bord, indicateurs, carte"],
    [role.validate_sheets, "Valide / rejette les fiches, gère les données de référence"],
    [role.stock_write, "Enregistre les mouvements de stock"],
  ];
  return (
    <ul className="caps">
      {items.map(([ok, text]) => (
        <li key={text} className={ok ? "yes" : "no"}>{ok ? <Check size={15} aria-hidden="true" /> : <X size={15} aria-hidden="true" />}{text}</li>
      ))}
      {role.read_only && <li className="yes"><Eye size={15} aria-hidden="true" />Lecture seule</li>}
      {role.zone_scoped && <li className="yes"><CircleUserRound size={15} aria-hidden="true" />Travaille sur sa zone</li>}
    </ul>
  );
}

function RightsMatrix({ roles }: { roles: RoleInfo[] }) {
  const cols: [keyof RoleInfo | "forms_n", string][] = [
    ["forms_n", "Fiches terrain"], ["dashboard", "Tableau de bord"], ["validate_sheets", "Valider les fiches"],
    ["stock_write", "Stock"], ["read_only", "Lecture seule"],
  ];
  const cell = (ok: boolean) => ok
    ? <span className="tick-yes"><Check size={16} aria-hidden="true" /><span className="sr">oui</span></span>
    : <span className="tick-no"><X size={16} aria-hidden="true" /><span className="sr">non</span></span>;
  return (
    <section className="card">
      <h2 style={{ marginTop: 0 }}><IconBadge icon={ShieldCheck} tone="violet" size="sm" />Rôles et droits</h2>
      <p className="muted small">Droits appliqués par le serveur pour chaque rôle. Les super administrateurs ont tous les droits, dont la gestion des utilisateurs.</p>
      <div className="table-scroll">
        <table className="data text rights">
          <thead><tr><th scope="col">Rôle</th>{cols.map(([, l]) => <th key={l} scope="col">{l}</th>)}</tr></thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.value}>
                <th scope="row"><Chip meta={{ icon: BookUser, tone: ROLE_TONE[r.value] ?? "slate", label: r.label }} /></th>
                <td title={r.forms.join(", ")}>{r.forms.length ? <span className="tick-yes">{r.forms.length}</span> : cell(false)}</td>
                <td>{cell(r.dashboard)}</td>
                <td>{cell(r.validate_sheets)}</td>
                <td>{cell(r.stock_write)}</td>
                <td>{cell(r.read_only)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
