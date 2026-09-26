import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { fmt } from "./format";
import type { KpiResult } from "./KpiView";

interface Task { id: number; code: string; section: string; title: string; frequency: string; frequency_label: string; asset: string | null;
  start: string | null; end: string | null; duration_days: number | null; scheduled_dates: string[]; progress_pct: string | null;
  status_note: string; comment: string; flags: string[] }
interface Line { id: number; month: string; category_label: string; activity: string; purpose: string; maintenance_type_label: string; unit: string;
  quantity: string | null; unit_price_usd: string | null; total_usd: string | null; responsible: string; supplier: string; flags: string[] }

const MONTHS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

function dayOfYear(iso: string, year: number) {
  const d = new Date(iso + "T00:00:00");
  return (d.getTime() - new Date(year, 0, 1).getTime()) / 86400000;
}

export function PlanView({ year }: { year: number }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  useEffect(() => {
    api<Task[]>(`/api/plan/tasks/?year=${year}`).then(setTasks);
  }, [year]);
  const days = new Date(year, 11, 31).getTime() - new Date(year, 0, 1).getTime();
  const total = days / 86400000 + 1;
  const today = dayOfYear(new Date().toISOString().slice(0, 10), year);
  const sections = useMemo(() => {
    const m = new Map<string, Task[]>();
    tasks.forEach((t) => m.set(t.section, [...(m.get(t.section) || []), t]));
    return [...m.entries()];
  }, [tasks]);

  return (
    <section className="card">
      <h3>Plan d'action annuel {year}</h3>
      <p className="muted small">Barre : période planifiée ; traits : jours programmés ; pourcentage : avancement saisi. Les tâches sans description dans Excel ne sont pas reprises (voir le rapport qualité).</p>
      {tasks.length === 0 && <p className="muted">Aucune tâche.</p>}
      <div className="gantt" role="table" aria-label="Plan d'action">
        <div className="g-row g-head" role="row">
          <div className="g-label" role="columnheader">Tâche</div>
          <div className="g-track" role="columnheader">
            {MONTHS.map((m, i) => <span key={i} className="g-month" style={{ left: `${(i / 12) * 100}%` }}>{m}</span>)}
          </div>
          <div className="g-prog" role="columnheader">Avanc.</div>
        </div>
        {sections.map(([section, list]) => (
          <div key={section} role="rowgroup">
            <div className="g-section" role="row">{section || "—"}</div>
            {list.map((t) => {
              const s = t.start ? dayOfYear(t.start, year) : null;
              const e = t.end ? dayOfYear(t.end, year) : s !== null && t.duration_days ? s + t.duration_days : null;
              return (
                <div className="g-row" role="row" key={t.id}>
                  <div className="g-label" role="cell">
                    {t.code && <span className="muted">{t.code} </span>}{t.title}
                    {t.flags.length > 0 && <span className="tag warning small" title="Voir le rapport qualité">à vérifier</span>}
                  </div>
                  <div className="g-track" role="cell">
                    {today >= 0 && today <= total && <span className="g-today" style={{ left: `${(today / total) * 100}%` }} />}
                    {s !== null && e !== null && (
                      <span className="g-bar" style={{ left: `${(s / total) * 100}%`, width: `${Math.max(((e - s + 1) / total) * 100, 0.6)}%` }} />
                    )}
                    {t.scheduled_dates.length < 60 &&
                      t.scheduled_dates.map((d) => <span key={d} className="g-tick" style={{ left: `${(dayOfYear(d, year) / total) * 100}%` }} />)}
                    {s === null && t.duration_days && <span className="muted small g-note">{t.duration_days} j — dates non planifiées</span>}
                  </div>
                  <div className="g-prog" role="cell">{t.progress_pct === null ? "—" : `${Number(t.progress_pct)} %`}</div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}

export function BudgetView({ kpi }: { kpi: KpiResult | null }) {
  const [lines, setLines] = useState<Line[]>([]);
  const [month, setMonth] = useState(() => `${kpi?.year ?? new Date().getFullYear()}-07`);
  useEffect(() => {
    api<Line[]>(`/api/plan/budget-lines/?month=${month}`).then(setLines);
  }, [month]);
  const m = kpi?.months[Number(month.slice(5)) - 1];
  const total = lines.reduce((s, l) => s + (l.total_usd ? Number(l.total_usd) : 0), 0);
  const uncosted = lines.filter((l) => l.total_usd === null).length;
  return (
    <>
      <section className="card">
        <div className="toolbar">
          <h3>Budget E&M</h3>
          <label className="label" htmlFor="bm">Mois</label>
          <input id="bm" type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
        </div>
        {m && (
          <dl className="kv inline">
            <div><dt>Budget prévu</dt><dd>{m.values.budget === null ? "—" : fmt.usd(m.values.budget!)}</dd></div>
            <div><dt>Dépense réelle</dt><dd>{m.values.actual_total === null ? "—" : fmt.usd(m.values.actual_total!)}</dd></div>
            <div><dt>Écart</dt><dd>{m.values.budget_variance === null ? "—" : fmt.usd(m.values.budget_variance!)}</dd></div>
            <div><dt>Urgente / corrective / préventive / support</dt><dd>
              {["share_urgent", "share_corrective", "share_preventive", "share_support"].map((k) => (m.values[k] === null ? "—" : fmt.pct(m.values[k]!))).join(" / ")}
            </dd></div>
          </dl>
        )}
      </section>
      <section className="card">
        <h3>Besoins budgétés ({lines.length} lignes, {fmt.usd(total)}{uncosted ? `, ${uncosted} non chiffrées` : ""})</h3>
        <div className="table-scroll">
          <table className="data">
            <thead><tr><th>Rubrique</th><th>Activité / besoin</th><th>But</th><th>Type</th><th>Qté</th><th>PU</th><th>Total</th><th>Resp.</th><th>Appro.</th></tr></thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.id}>
                  <td>{l.category_label}</td>
                  <th scope="row">{l.activity}</th>
                  <td>{l.purpose}</td>
                  <td>{l.maintenance_type_label}</td>
                  <td>{l.quantity ?? ""} {l.unit}</td>
                  <td>{l.unit_price_usd ?? ""}</td>
                  <td>{l.total_usd === null ? <span className="tag warning">non chiffré</span> : fmt.usd(Number(l.total_usd))}</td>
                  <td>{l.responsible}</td>
                  <td>{l.supplier}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
