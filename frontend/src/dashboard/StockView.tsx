import { CircleCheck, CircleX, History, PackageOpen, Save, Search, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { useApp } from "../state";
import { IconBadge, MOVEMENT_META } from "../ui/meta";
import { api } from "../lib/api";
import { todayISO } from "../lib/forms";

interface Item { code: string; name: string; unit: string; category_label: string; group: string; balance: number | null; min_threshold: string | null;
  alert: boolean | null; flags: string[] }
interface Move { id: string; item: string; date: string; kind: string; kind_label: string; quantity: string; reference: string; incident_number: string | null }

export default function StockView({ canWrite }: { canWrite: boolean }) {
  const [items, setItems] = useState<Item[]>([]);
  const [moves, setMoves] = useState<Move[]>([]);
  const [form, setForm] = useState({ item: "", kind: "IN", quantity: "", date: todayISO(), reference: "" });
  const [msg, setMsg] = useState("");
  const [filter, setFilter] = useState("");
  const [saving, setSaving] = useState(false);
  const { notify } = useApp();

  const load = () => {
    api<Item[]>("/api/stock/items/").then(setItems);
    api<Move[]>("/api/stock/movements/").then((m) => setMoves(m.slice(0, 30)));
  };
  useEffect(load, []);

  const alerts = items.filter((i) => i.alert);
  const shown = items.filter((i) => !filter || `${i.name} ${i.code} ${i.group}`.toLowerCase().includes(filter.toLowerCase()));
  const name = (code: string) => items.find((i) => i.code === code)?.name ?? code;

  return (
    <>
      {alerts.length > 0 && (
        <section className="banner critical" role="alert">
          <TriangleAlert size={20} aria-hidden="true" />
          <span className="banner-body">
            <strong>{alerts.length} article(s) sous le seuil :</strong> {alerts.map((a) => `${a.name} (${a.balance ?? 0} ${a.unit})`).join(" ; ")}
          </span>
        </section>
      )}
      {canWrite && (
        <form
          className="card toolbar wrap"
          onSubmit={async (e) => {
            e.preventDefault();
            setSaving(true);
            try {
              await api("/api/stock/movements/", { method: "POST", json: form });
              setMsg("");
              notify(`Mouvement enregistré : ${MOVEMENT_META[form.kind]?.label ?? form.kind}`, "green");
              setForm({ ...form, quantity: "", reference: "" });
              load();
            } catch (err: any) {
              setMsg(JSON.stringify(err.body || err.message));
            } finally {
              setSaving(false);
            }
          }}
        >
          <h2 className="w100" style={{ margin: 0 }}><IconBadge icon={(MOVEMENT_META[form.kind] ?? MOVEMENT_META.IN).icon} tone={(MOVEMENT_META[form.kind] ?? MOVEMENT_META.IN).tone} size="sm" />Enregistrer un mouvement</h2>
          <select aria-label="Article" required value={form.item} onChange={(e) => setForm({ ...form, item: e.target.value })}>
            <option value="">— Article —</option>
            {items.map((i) => <option key={i.code} value={i.code}>{i.name}</option>)}
          </select>
          <select aria-label="Type de mouvement" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="OPENING">Stock initial (inventaire)</option>
            <option value="IN">Entrée</option>
            <option value="OUT">Sortie</option>
            <option value="ADJUST">Ajustement (+/−)</option>
          </select>
          <input aria-label="Quantité" required inputMode="decimal" placeholder="Quantité" value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value.replace(",", ".") })} />
          <input aria-label="Date" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          <input aria-label="Référence" placeholder="Référence (bon, fournisseur…)" value={form.reference}
            onChange={(e) => setForm({ ...form, reference: e.target.value })} />
          <button className="btn success" disabled={saving}><Save size={18} aria-hidden="true" />Enregistrer</button>
          <span className="error small" aria-live="polite">{msg}</span>
        </form>
      )}
      <section className="card">
        <div className="toolbar">
          <h2 style={{ margin: "0 auto 0 0" }}><IconBadge icon={PackageOpen} tone="teal" size="sm" />Articles</h2>
          <span style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
            <Search size={16} aria-hidden="true" style={{ position: "absolute", left: 12, color: "var(--muted)" }} />
            <input aria-label="Filtrer" placeholder="Filtrer…" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ paddingLeft: 36 }} />
          </span>
        </div>
        <p className="muted small">Solde = somme des mouvements. Les quantités d'origine du fichier Excel étaient des valeurs de test : elles n'ont pas été importées (faire un inventaire initial).</p>
        <div className="table-scroll">
          <table className="data">
            <thead><tr><th>Article</th><th>Rubrique</th><th>Solde</th><th>Seuil</th><th>État</th></tr></thead>
            <tbody>
              {shown.map((i) => (
                <tr key={i.code}>
                  <th scope="row">{i.name}<br /><span className="muted small">{i.code}</span></th>
                  <td>{i.group || i.category_label}</td>
                  <td>{i.balance === null ? "—" : `${i.balance} ${i.unit}`}</td>
                  <td>{i.min_threshold ?? "—"}</td>
                  <td>{i.alert ? <span className="tag critical"><CircleX size={13} aria-hidden="true" />sous le seuil</span> : i.alert === false ? <span className="tag good"><CircleCheck size={13} aria-hidden="true" />OK</span> : <span className="muted">seuil non défini</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card">
        <h2 style={{ marginTop: 0 }}><IconBadge icon={History} tone="slate" size="sm" />Derniers mouvements</h2>
        {moves.length === 0 && <p className="muted">Aucun mouvement.</p>}
        <ul className="list">
          {moves.map((m) => (
            <li key={m.id} className="list-item">
              <span className="list-main" style={{ minHeight: 52 }}>
                {MOVEMENT_META[m.kind] && <IconBadge icon={MOVEMENT_META[m.kind].icon} tone={MOVEMENT_META[m.kind].tone} size="sm" />}
                <span className="list-text">
                  <span className="list-title">{name(m.item)} · {m.quantity}</span>
                  <span className="muted small">{new Date(m.date).toLocaleDateString("fr-FR")} · {m.kind_label}</span>
                </span>
              </span>
              <span className="muted small">{m.incident_number || m.reference}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
