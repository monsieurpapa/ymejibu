import {
  Activity, ChartColumn, CircleCheck, CircleX, Droplet, Droplets, FlaskConical, Gauge, Info, ShieldCheck, Table2, TriangleAlert, Wallet,
  Wrench, Zap, type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { HBars, LineChart } from "../charts/LineChart";
import { IconBadge, type Tone } from "../ui/meta";
import { fmt, type FmtKey } from "./format";
import MonthDetail from "./MonthDetail";

export interface KpiMonth {
  month: number;
  label: string;
  status: "closed" | "current" | "future";
  has_data: boolean;
  coverage: { pump_reading_days: number; days: number };
  sources: Record<string, "historique" | "fiches">;
  provisional: Record<string, number>;
  values: Record<string, number | null>;
}

/** Served by /api/kpi/ (backend kpi/catalog.py): the same titles, targets and labels as the PDF report. */
export interface CatalogKpi {
  key: string;
  title: string;
  fmt: string;
  target: { value: number; label: string; better: "up" | "down" } | null;
  better: "up" | "down" | null;
  help: string;
}
export interface Catalog {
  kpis: CatalogKpi[];
  table_rows: { key: string; label: string; fmt: string }[];
  breakdowns: { key: string; title: string; fmt: string; items: { key: string; label: string }[] }[];
  figures: { title: string; items: { key: string; label: string; fmt: string }[] }[];
  pm_categories: { key: string; label: string }[];
}
export interface KpiResult {
  year: number; site: string; today: string; months: KpiMonth[]; annual: Record<string, number | null>; catalog: Catalog;
}

const LOOK: Record<string, { icon: LucideIcon; tone: Tone }> = {
  availability: { icon: Activity, tone: "blue" },
  efficiency: { icon: Droplets, tone: "teal" },
  nrw_m3: { icon: Droplet, tone: "orange" },
  repair_rate: { icon: Wrench, tone: "orange" },
  pm_rate: { icon: ShieldCheck, tone: "green" },
  quality_rate: { icon: FlaskConical, tone: "violet" },
  energy_cost_per_m3: { icon: Zap, tone: "amber" },
  kwh_per_m3: { icon: Gauge, tone: "amber" },
  budget_variance: { icon: Wallet, tone: "slate" },
  incidents_reported: { icon: TriangleAlert, tone: "red" },
};

const fmtOf = (kind: string) => fmt[(kind in fmt ? kind : "num") as FmtKey];

function latest(months: KpiMonth[], key: string) {
  for (let i = months.length - 1; i >= 0; i--) {
    const v = months[i].values[key];
    if (months[i].status !== "future" && v !== null && v !== undefined) return { m: months[i], v };
  }
  return null;
}

function Card({ def, data, selected, onSelect }: { def: CatalogKpi; data: KpiResult; selected: number; onSelect: (i: number) => void }) {
  const last = latest(data.months, def.key);
  const f = fmtOf(def.fmt);
  const look = LOOK[def.key] ?? { icon: ChartColumn, tone: "blue" as Tone };
  const ok = last && def.target ? (def.target.better === "up" ? last.v >= def.target.value : last.v <= def.target.value) : null;
  const src = last?.m.sources[def.key] ?? last?.m.sources[Object.keys(last.m.sources)[0]];
  return (
    <article className="kpi card" aria-labelledby={`kpi-${def.key}`}>
      <header>
        <IconBadge icon={look.icon} tone={look.tone} />
        <div>
          <h3 id={`kpi-${def.key}`}>{def.title}</h3>
          <p className="muted small">{def.help}</p>
        </div>
      </header>
      {last ? (
        <div className="kpi-head">
          <span className="kpi-value" data-testid={`kpi-${def.key}`}>{f(last.v)}</span>
          <span className="muted small">
            {last.m.label} {data.year}
            {src ? ` · ${src === "historique" ? "historique Excel" : "fiches terrain"}` : ""}
          </span>
          {ok !== null && (
            <span className={`tag ${ok ? "good" : "critical"}`}>
              {ok ? <CircleCheck size={14} aria-hidden="true" /> : <CircleX size={14} aria-hidden="true" />}
              {ok ? "cible atteinte" : "sous la cible"}
            </span>
          )}
        </div>
      ) : (
        <p className="kpi-empty">Pas encore de donnée pour {data.year}.</p>
      )}
      <LineChart
        title={`${def.title} par mois`}
        points={data.months.map((m) => ({
          label: m.label,
          value: m.values[def.key] ?? null,
          note: m.sources[def.key] === "historique" ? "historique Excel" : m.status === "current" ? "mois en cours" : undefined,
        }))}
        format={f}
        target={def.target ? { value: def.target.value, label: def.target.label } : undefined}
        min={def.fmt === "pct" ? 0 : undefined}
        max={def.fmt === "pct" ? 1 : undefined}
        selected={selected}
        onSelect={(i) => data.months[i].status !== "future" && onSelect(i)}
      />
    </article>
  );
}

/** Default month: the current one, else the last month with data, else January. */
function defaultMonth(data: KpiResult) {
  const cur = data.months.findIndex((m) => m.status === "current");
  if (cur >= 0) return cur;
  for (let i = data.months.length - 1; i >= 0; i--) if (data.months[i].has_data) return i;
  return 0;
}

export default function KpiView({ data }: { data: KpiResult }) {
  const [month, setMonth] = useState(() => defaultMonth(data));
  const detailRef = useRef<HTMLDivElement>(null);
  useEffect(() => setMonth(defaultMonth(data)), [data.year]); // eslint-disable-line react-hooks/exhaustive-deps

  const rca = useMemo(() => data.catalog.breakdowns.find((b) => b.key === "rca"), [data.catalog]);
  const causes = (rca?.items ?? [])
    .map((it) => ({ label: it.label, value: (data.annual[it.key] as number) || 0 }))
    .filter((c) => c.value > 0)
    .sort((a, b) => b.value - a.value);
  const current = data.months.find((m) => m.status === "current");

  const pick = (i: number, scroll = false) => {
    setMonth(i);
    if (scroll) detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <>
      {current && (
        <p className="banner neutral small">
          <Info size={18} aria-hidden="true" />
          <span className="banner-body">{current.label} : {current.coverage.pump_reading_days} jour(s) de relevés de pompage sur {current.coverage.days}. Les valeurs du mois
          en cours sont partielles.</span>
        </p>
      )}
      <p className="muted small">Astuce : cliquez sur un point d'un graphique ou sur un mois du tableau pour afficher le détail de ce mois.</p>
      <div className="kpi-grid">
        {data.catalog.kpis.map((k) => <Card key={k.key} def={k} data={data} selected={month} onSelect={(i) => pick(i, true)} />)}
      </div>
      <div ref={detailRef} style={{ scrollMarginTop: 72 }}>
        <MonthDetail data={data} index={month} onChange={(i) => pick(i)} />
      </div>
      <section className="card">
        <h2 style={{ marginTop: 0 }}><IconBadge icon={ChartColumn} tone="red" size="sm" />Causes des pannes {data.year}</h2>
        {causes.length ? <HBars items={causes} format={fmt.int} title="Nombre de pannes par cause" /> : <p className="muted">Aucune cause enregistrée.</p>}
      </section>
      <section className="card">
        <h2 style={{ marginTop: 0 }}><IconBadge icon={Table2} tone="blue" size="sm" />Tableau mensuel</h2>
        <p className="muted small">« h » = historique Excel (mois antérieurs à l'application) ; vide = pas de donnée.</p>
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">Indicateur</th>
                {data.months.map((m, i) => (
                  <th scope="col" key={m.month} className={i === month ? "col-selected" : ""}>
                    {m.status === "future" ? m.label.slice(0, 4) : (
                      <button type="button" className="th-btn" onClick={() => pick(i, true)} aria-label={`Détail de ${m.label}`}>
                        {m.label.slice(0, 4)}
                      </button>
                    )}
                  </th>
                ))}
                <th scope="col">Année</th>
              </tr>
            </thead>
            <tbody>
              {data.catalog.table_rows.map(({ key, label, fmt: kind }) => (
                <tr key={key}>
                  <th scope="row">{label}</th>
                  {data.months.map((m, i) => {
                    const v = m.values[key];
                    return (
                      <td key={m.month} className={`${m.status === "future" ? "future" : ""}${i === month ? " col-selected" : ""}`}>
                        {v === null || v === undefined ? "" : fmtOf(kind)(v)}
                        {m.sources[key] === "historique" && v !== null ? <sup title="historique Excel"> h</sup> : null}
                      </td>
                    );
                  })}
                  <td>{data.annual[key] === null || data.annual[key] === undefined ? "" : fmtOf(kind)(data.annual[key] as number)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
