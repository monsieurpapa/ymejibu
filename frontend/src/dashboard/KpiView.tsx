import { Activity, ChartColumn, CircleCheck, CircleX, Droplet, Droplets, FlaskConical, Gauge, Info, ShieldCheck, Table2, TriangleAlert, Wallet, Wrench, Zap, type LucideIcon } from "lucide-react";
import { HBars, LineChart } from "../charts/LineChart";
import { IconBadge, type Tone } from "../ui/meta";
import { fmt, type FmtKey } from "./format";

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
export interface KpiResult { year: number; site: string; today: string; months: KpiMonth[]; annual: Record<string, number | null> }

interface KpiDef {
  key: string;
  title: string;
  f: FmtKey;
  target?: { value: number; label: string; better: "up" | "down" };
  help: string;
  icon: LucideIcon;
  tone: Tone;
}

// Default targets: to be confirmed by the Responsable technique (see README).
export const KPIS: KpiDef[] = [
  { key: "availability", icon: Activity, tone: "blue", title: "Disponibilité du réseau", f: "pct", target: { value: 0.95, label: "cible 95 %", better: "up" },
    help: "(heures du mois − heures d'arrêt) / heures du mois" },
  { key: "efficiency", icon: Droplets, tone: "teal", title: "Rendement du réseau", f: "pct", target: { value: 0.8, label: "cible 80 %", better: "up" },
    help: "eau facturée / eau introduite" },
  { key: "nrw_m3", icon: Droplet, tone: "orange", title: "Eau non facturée", f: "m3", help: "eau introduite − eau facturée" },
  { key: "repair_rate", icon: Wrench, tone: "orange", title: "Taux de réparation des pannes", f: "pct", target: { value: 0.9, label: "cible 90 %", better: "up" },
    help: "pannes clôturées / pannes signalées (registre des pannes)" },
  { key: "pm_rate", icon: ShieldCheck, tone: "green", title: "Taux de maintenance préventive", f: "pct", target: { value: 0.9, label: "cible 90 %", better: "up" },
    help: "ordres de travail préventifs réalisés / planifiés" },
  { key: "quality_rate", icon: FlaskConical, tone: "violet", title: "Conformité de la qualité de l'eau", f: "pct", target: { value: 0.95, label: "cible 95 %", better: "up" },
    help: "mesures conformes / mesures (chlore résiduel, turbidité, laboratoire)" },
  { key: "energy_cost_per_m3", icon: Zap, tone: "amber", title: "Coût énergétique par m³", f: "usd3", help: "(kWh × tarif + litres × prix) / m³ pompés" },
  { key: "kwh_per_m3", icon: Gauge, tone: "amber", title: "Intensité électrique", f: "dec3", help: "kWh / m³ pompés" },
  { key: "budget_variance", icon: Wallet, tone: "slate", title: "Écart budgétaire", f: "usd", target: { value: 0, label: "budget", better: "down" },
    help: "dépenses réelles − budget prévu (négatif = sous le budget)" },
  { key: "incidents_reported", icon: TriangleAlert, tone: "red", title: "Pannes signalées", f: "int", help: "nombre de pannes par mois" },
];

function latest(months: KpiMonth[], key: string) {
  for (let i = months.length - 1; i >= 0; i--) {
    const v = months[i].values[key];
    if (months[i].status !== "future" && v !== null && v !== undefined) return { m: months[i], v };
  }
  return null;
}

function Card({ def, data }: { def: KpiDef; data: KpiResult }) {
  const last = latest(data.months, def.key);
  const f = fmt[def.f];
  const ok = last && def.target ? (def.target.better === "up" ? last.v >= def.target.value : last.v <= def.target.value) : null;
  const src = last?.m.sources[def.key] ?? last?.m.sources[Object.keys(last.m.sources)[0]];
  return (
    <article className="kpi card" aria-labelledby={`kpi-${def.key}`}>
      <header>
        <IconBadge icon={def.icon} tone={def.tone} />
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
        min={def.f === "pct" ? 0 : undefined}
        max={def.f === "pct" ? 1 : undefined}
      />
    </article>
  );
}

const TABLE_ROWS: [string, string, FmtKey][] = [
  ["volume_introduced", "Eau introduite", "m3"],
  ["volume_billed", "Eau facturée", "m3"],
  ["nrw_m3", "Eau non facturée", "m3"],
  ["efficiency", "Rendement", "pct"],
  ["downtime_total", "Heures d'arrêt", "h"],
  ["availability", "Disponibilité", "pct"],
  ["incidents_reported", "Pannes signalées", "int"],
  ["incidents_closed", "Pannes réparées", "int"],
  ["repair_rate", "Taux de réparation", "pct"],
  ["pm_planned_total", "Maintenances préventives prévues", "int"],
  ["pm_done_total", "Maintenances préventives réalisées", "int"],
  ["pm_rate", "Taux de maintenance préventive", "pct"],
  ["kwh", "Électricité (kWh)", "int"],
  ["fuel_l", "Carburant (L)", "int"],
  ["energy_cost_per_m3", "Coût énergétique / m³", "usd3"],
  ["budget", "Budget prévu", "usd"],
  ["actual_total", "Dépense réelle", "usd"],
  ["budget_variance", "Écart budgétaire", "usd"],
  ["quality_rate", "Conformité qualité", "pct"],
];

const CAUSES: Record<string, string> = {
  VANDALISM: "Vandalisme et vol", OVERPRESSURE: "Surpression", SHALLOW_PIPE: "Tuyau mal enfoui", ILLEGAL_CONNECTION: "Connexion illégale",
  MISHANDLING: "Mauvaise manipulation", POOR_PIPE_QUALITY: "Mauvaise qualité du tuyau", POOR_BACKFILL: "Mauvais remblai",
  GROUND_MOVEMENT: "Mouvement de terrain", POOR_INSTALLATION: "Mauvaise installation", WATER_HAMMER: "Coup de bélier",
  FAULTY_CONNECTION: "Connexion défectueuse", OTHER: "Autre",
};

export default function KpiView({ data }: { data: KpiResult }) {
  const causes = Object.entries(CAUSES)
    .map(([k, label]) => ({ label, value: (data.annual[`rca_${k}`] as number) || 0 }))
    .filter((c) => c.value > 0)
    .sort((a, b) => b.value - a.value);
  const current = data.months.find((m) => m.status === "current");
  return (
    <>
      {current && (
        <p className="banner neutral small">
          <Info size={18} aria-hidden="true" />
          <span className="banner-body">{current.label} : {current.coverage.pump_reading_days} jour(s) de relevés de pompage sur {current.coverage.days}. Les valeurs du mois
          en cours sont partielles.</span>
        </p>
      )}
      <div className="kpi-grid">
        {KPIS.map((k) => <Card key={k.key} def={k} data={data} />)}
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
                {data.months.map((m) => <th scope="col" key={m.month}>{m.label.slice(0, 4)}</th>)}
                <th scope="col">Année</th>
              </tr>
            </thead>
            <tbody>
              {TABLE_ROWS.map(([key, label, f]) => (
                <tr key={key}>
                  <th scope="row">{label}</th>
                  {data.months.map((m) => {
                    const v = m.values[key];
                    return (
                      <td key={m.month} className={m.status === "future" ? "future" : ""}>
                        {v === null || v === undefined ? "" : fmt[f](v)}
                        {m.sources[key] === "historique" && v !== null ? <sup title="historique Excel"> h</sup> : null}
                      </td>
                    );
                  })}
                  <td>{data.annual[key] === null || data.annual[key] === undefined ? "" : fmt[f](data.annual[key] as number)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
