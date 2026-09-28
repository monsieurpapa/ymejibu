import {
  ArrowDownRight, ArrowUpRight, CalendarDays, ChevronLeft, ChevronRight, CircleCheck, CircleX, Clock, FileDown, History, LoaderCircle,
  Minus, type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { HBars } from "../charts/LineChart";
import { download } from "../lib/api";
import { useApp } from "../state";
import { Chip, IconBadge, type Meta } from "../ui/meta";
import { fmt, type FmtKey } from "./format";
import type { CatalogKpi, KpiResult } from "./KpiView";

const SHORT = ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"];

const STATUS: Record<string, Meta> = {
  closed: { icon: CircleCheck, tone: "green", label: "Mois clôturé" },
  current: { icon: Clock, tone: "amber", label: "Mois en cours : valeurs partielles" },
  future: { icon: CalendarDays, tone: "slate", label: "À venir" },
};

const f = (kind: string) => fmt[(kind in fmt ? kind : "num") as FmtKey];

function Delta({ kpi, cur, prev }: { kpi: CatalogKpi; cur: number | null; prev: number | null }) {
  if (cur == null || prev == null) return <span className="muted">—</span>;
  const diff = cur - prev;
  if (Math.abs(diff) < 1e-12) return <span className="delta neutral"><Minus size={14} aria-hidden="true" />stable</span>;
  const good = kpi.better ? (diff > 0) === (kpi.better === "up") : null;
  const Icon: LucideIcon = diff > 0 ? ArrowUpRight : ArrowDownRight;
  const shown = kpi.fmt === "pct" ? `${fmt.num(Math.abs(diff) * 100)} pts` : f(kpi.fmt)(Math.abs(diff));
  return (
    <span className={`delta ${good === null ? "neutral" : good ? "good" : "bad"}`}>
      <Icon size={15} aria-hidden="true" />
      <span className="sr">{diff > 0 ? "hausse de" : "baisse de"} </span>{shown}
    </span>
  );
}

export default function MonthDetail({ data, index, onChange }: { data: KpiResult; index: number; onChange: (i: number) => void }) {
  const { notify } = useApp();
  const [busy, setBusy] = useState(false);
  const m = data.months[index];
  const prev = index > 0 ? data.months[index - 1] : null;
  const cat = data.catalog;
  const hasHist = Object.values(m.sources).includes("historique");
  const v = (key: string) => m.values[key] ?? null;
  const lastSelectable = data.months.reduce((acc, mm, i) => (mm.status !== "future" ? i : acc), 0);

  const pdf = async () => {
    setBusy(true);
    try {
      await download(`/api/kpi/report.pdf?year=${data.year}&month=${m.month}`, `ymejibu_indicateurs_${data.year}-${String(m.month).padStart(2, "0")}.pdf`);
    } catch (e: any) {
      notify(e.message || "Téléchargement impossible", "red");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card month-detail" aria-labelledby="month-detail-title">
      <div className="toolbar">
        <h2 id="month-detail-title" style={{ margin: "0 auto 0 0" }}>
          <IconBadge icon={CalendarDays} tone="blue" size="sm" />Détail du mois
        </h2>
        <button className="btn secondary small" onClick={pdf} disabled={busy}>
          {busy ? <LoaderCircle size={16} className="spin" aria-hidden="true" /> : <FileDown size={16} aria-hidden="true" />}PDF du mois
        </button>
      </div>

      <div className="month-nav">
        <button className="btn ghost small" onClick={() => onChange(index - 1)} disabled={index === 0} aria-label="Mois précédent">
          <ChevronLeft size={18} aria-hidden="true" />
        </button>
        <div className="month-strip" role="radiogroup" aria-label="Choisir le mois">
          {data.months.map((mm, i) => (
            <button key={mm.month} type="button" role="radio" aria-checked={i === index} aria-label={`${mm.label} ${data.year}`}
              className={`month-btn${i === index ? " on" : ""}${mm.status === "future" ? " future" : ""}`}
              disabled={mm.status === "future"} onClick={() => onChange(i)}>
              {SHORT[i]}
              {mm.has_data && <span className="has-data" aria-hidden="true" />}
            </button>
          ))}
        </div>
        <button className="btn ghost small" onClick={() => onChange(index + 1)} disabled={index >= lastSelectable} aria-label="Mois suivant">
          <ChevronRight size={18} aria-hidden="true" />
        </button>
      </div>

      <div className="month-head">
        <h3>{m.label} {data.year}</h3>
        <div className="overview">
          <Chip meta={STATUS[m.status]} />
          <Chip meta={{ icon: CalendarDays, tone: m.coverage.pump_reading_days ? "blue" : "slate",
            label: `Relevés de pompage : ${m.coverage.pump_reading_days} / ${m.coverage.days} jours` }} />
          {hasHist && <Chip meta={{ icon: History, tone: "violet", label: "Contient l'historique Excel" }} />}
        </div>
      </div>
      {!m.has_data && <p className="muted">Aucune donnée d'exploitation pour ce mois.</p>}

      <div className="table-scroll">
        <table className="data text month-kpis">
          <thead>
            <tr><th scope="col">Indicateur</th><th scope="col" className="num">Ce mois</th><th scope="col" className="num">{prev ? prev.label : "Mois précédent"}</th>
              <th scope="col" className="pad">Évolution</th><th scope="col">Cible</th></tr>
          </thead>
          <tbody>
            {cat.kpis.map((k) => {
              const cur = v(k.key);
              const pv = prev ? prev.values[k.key] ?? null : null;
              const ok = cur == null || !k.target ? null : k.target.better === "up" ? cur >= k.target.value : cur <= k.target.value;
              return (
                <tr key={k.key}>
                  <td className="strong">{k.title}</td>
                  <td className="num strong">{cur == null ? "—" : f(k.fmt)(cur)}</td>
                  <td className="num muted">{pv == null ? "—" : f(k.fmt)(pv)}</td>
                  <td className="pad"><Delta kpi={k} cur={cur} prev={pv} /></td>
                  <td>
                    {ok === null ? <span className="muted small">{k.target?.label ?? "—"}</span> : (
                      <span className={`tag ${ok ? "good" : "critical"}`}>
                        {ok ? <CircleCheck size={13} aria-hidden="true" /> : <CircleX size={13} aria-hidden="true" />}
                        {ok ? "atteinte" : "sous la cible"}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="figure-grid">
        {cat.figures.map((g) => (
          <div key={g.title} className="figure-box">
            <h4>{g.title}</h4>
            <dl>
              {g.items.map((it) => (
                <div key={it.key + it.label}><dt>{it.label}</dt><dd>{v(it.key) == null ? "—" : f(it.fmt)(v(it.key)!)}</dd></div>
              ))}
            </dl>
          </div>
        ))}
        <div className="figure-box">
          <h4>Maintenance préventive</h4>
          <dl>
            {cat.pm_categories.map((c) => {
              const planned = v(`pm_planned_${c.key}`);
              const done = v(`pm_done_${c.key}`);
              return (
                <div key={c.key}><dt>{c.label}</dt>
                  <dd>{planned == null && done == null ? "—" : `${done ?? 0} / ${planned ?? 0} réalisée(s)`}</dd></div>
              );
            })}
          </dl>
        </div>
      </div>

      <div className="breakdown-grid">
        {cat.breakdowns.map((b) => {
          const items = b.items.map((it) => ({ label: it.label, value: v(it.key) ?? 0 })).filter((it) => it.value > 0)
            .sort((a, c) => c.value - a.value);
          return (
            <div key={b.key} className="figure-box">
              <h4>{b.title}</h4>
              {items.length ? <HBars items={items} format={f(b.fmt)} title={`${b.title} — ${m.label}`} /> : <p className="muted small">Aucune donnée.</p>}
            </div>
          );
        })}
      </div>
    </section>
  );
}
