import { Check, ChevronDown, CircleCheck, CircleX, Clock, Inbox, Undo2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { FormIcon } from "../pages/Home";
import { useApp } from "../state";
import { Chip, MAINTENANCE_META, type Meta } from "../ui/meta";
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

const REVIEW_STATUS: Record<string, Meta> = {
  SUBMITTED: { icon: Clock, tone: "amber", label: "À valider" },
  VALIDATED: { icon: CircleCheck, tone: "green", label: "Validée" },
  REJECTED: { icon: CircleX, tone: "red", label: "Rejetée" },
};

export default function Review({ canWrite }: { canWrite: boolean }) {
  const [subs, setSubs] = useState<Sub[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [status, setStatus] = useState("SUBMITTED");
  const [msg, setMsg] = useState("");
  const { notify } = useApp();

  const load = () => api<Sub[]>(`/api/submissions/?status=${status}&limit=100`).then(setSubs).catch((e) => setMsg(e.message));
  useEffect(() => {
    load();
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (id: string, next: string) => {
    try {
      await api(`/api/submissions/${id}/`, { method: "PATCH", json: { status: next } });
      setMsg("");
      notify(
        next === "VALIDATED" ? "Fiche validée." : next === "REJECTED" ? "Fiche rejetée : ses données sont retirées des indicateurs." : "Fiche remise à valider.",
        next === "REJECTED" ? "red" : "green",
      );
      setOpen(null);
      load();
    } catch (e: any) {
      setMsg(e.message);
    }
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
        <span className="error small" aria-live="polite">{msg}</span>
      </div>
      {subs.length === 0 && <div className="empty"><Inbox size={32} aria-hidden="true" /><span>Aucune fiche.</span></div>}
      <ul className="list">
        {subs.map((s) => (
          <li key={s.id} className="list-item column">
            <button className="list-main as-button" onClick={() => setOpen(open === s.id ? null : s.id)} aria-expanded={open === s.id}>
              <FormIcon type={s.form_type} />
              <span className="list-text" style={{ flex: 1 }}>
                <span className="list-title">{s.form_label} · {s.asset || s.zone || ""} · {new Date(s.date).toLocaleDateString("fr-FR")}</span>
                <span className="muted small">{s.submitted_by_name} · v{s.version}{s.payload?.general?.number ? ` · ${s.payload.general.number}` : ""}</span>
                <span className="row-inline" style={{ marginTop: 0, gap: 6 }}>
                  {REVIEW_STATUS[s.status] && <Chip meta={REVIEW_STATUS[s.status]} />}
                  {MAINTENANCE_META[s.payload?.intervention?.maintenance_type] && <Chip meta={MAINTENANCE_META[s.payload.intervention.maintenance_type]} />}
                  {s.form_type.startsWith("MP_") && <Chip meta={MAINTENANCE_META.PREVENTIVE} />}
                </span>
              </span>
              <ChevronDown size={20} aria-hidden="true" style={{ transition: "transform .2s", transform: open === s.id ? "rotate(180deg)" : "none", color: "var(--muted)" }} />
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
                    {s.status !== "VALIDATED" && (
                      <button className="btn success" onClick={() => act(s.id, "VALIDATED")}><Check size={18} aria-hidden="true" />Valider</button>
                    )}
                    {s.status !== "REJECTED" && (
                      <button className="btn outline-danger" onClick={() => act(s.id, "REJECTED")}><X size={18} aria-hidden="true" />Rejeter</button>
                    )}
                    {s.status === "REJECTED" && (
                      <button className="btn secondary" onClick={() => act(s.id, "SUBMITTED")}><Undo2 size={18} aria-hidden="true" />Rétablir</button>
                    )}
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
