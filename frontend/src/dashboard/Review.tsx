import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface Sub {
  id: string; form_type: string; form_label: string; date: string; status: string; version: number;
  submitted_by_name: string; asset: string | null; zone: string | null; payload: Record<string, any>; derivation_errors: unknown[];
}

function flatten(p: Record<string, any>) {
  const out: [string, string][] = [];
  for (const [sec, val] of Object.entries(p || {})) {
    if (Array.isArray(val)) {
      val.forEach((row, i) => out.push([`${sec} ${i + 1}`, Object.entries(row || {}).filter(([, v]) => v !== "" && v !== null).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ")]));
    } else if (val && typeof val === "object") {
      for (const [k, v] of Object.entries(val)) {
        if (v === "" || v === null || v === undefined) continue;
        if (typeof v === "object" && !Array.isArray(v)) {
          const s = Object.entries(v as object).filter(([, x]) => x !== "" && x !== null).map(([a, b]) => `${a}: ${b}`).join(" · ");
          if (s) out.push([`${sec}.${k}`, s]);
        } else out.push([`${sec}.${k}`, Array.isArray(v) ? `${v.length} élément(s)` : String(v)]);
      }
    }
  }
  return out;
}

export default function Review({ canWrite }: { canWrite: boolean }) {
  const [subs, setSubs] = useState<Sub[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [status, setStatus] = useState("SUBMITTED");
  const [msg, setMsg] = useState("");

  const load = () => api<Sub[]>(`/api/submissions/?status=${status}&limit=100`).then(setSubs).catch((e) => setMsg(e.message));
  useEffect(() => {
    load();
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (id: string, next: string) => {
    await api(`/api/submissions/${id}/`, { method: "PATCH", json: { status: next } });
    setMsg(next === "VALIDATED" ? "Fiche validée." : "Fiche rejetée : ses données sont retirées des indicateurs.");
    load();
  };

  return (
    <section className="card">
      <div className="toolbar">
        <label className="label" htmlFor="st">Statut</label>
        <select id="st" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="SUBMITTED">À valider</option>
          <option value="VALIDATED">Validées</option>
          <option value="REJECTED">Rejetées</option>
        </select>
        <span className="muted small" aria-live="polite">{msg}</span>
      </div>
      {subs.length === 0 && <p className="muted">Aucune fiche.</p>}
      <ul className="list">
        {subs.map((s) => (
          <li key={s.id} className="list-item column">
            <button className="list-main as-button" onClick={() => setOpen(open === s.id ? null : s.id)} aria-expanded={open === s.id}>
              <span className="list-title">{s.form_label} · {s.asset || s.zone || ""} · {new Date(s.date).toLocaleDateString("fr-FR")}</span>
              <span className="muted small">{s.submitted_by_name} · v{s.version}{s.payload?.general?.number ? ` · ${s.payload.general.number}` : ""}</span>
            </button>
            {open === s.id && (
              <div className="detail">
                <dl className="kv">
                  {flatten(s.payload).map(([k, v]) => (
                    <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
                  ))}
                </dl>
                {canWrite && (
                  <div className="row-inline">
                    {s.status !== "VALIDATED" && <button className="btn primary" onClick={() => act(s.id, "VALIDATED")}>Valider</button>}
                    {s.status !== "REJECTED" && <button className="btn secondary danger" onClick={() => act(s.id, "REJECTED")}>Rejeter</button>}
                    {s.status === "REJECTED" && <button className="btn secondary" onClick={() => act(s.id, "SUBMITTED")}>Rétablir</button>}
                  </div>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
