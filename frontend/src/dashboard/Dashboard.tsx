import { lazy, Suspense, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api, download } from "../lib/api";
import { MANAGER_ROLES } from "../lib/types";
import { useApp } from "../state";
import KpiView, { type KpiResult } from "./KpiView";
import { BudgetView, PlanView } from "./PlanView";
import Review from "./Review";
import StockView from "./StockView";

const MapView = lazy(() => import("./MapView"));

interface Overview { submissions_to_review: number; open_incidents: number; critical_open: number; history_actual_months: number }

export default function Dashboard() {
  const { me, online, ref } = useApp();
  const [year, setYear] = useState(new Date().getFullYear());
  const [kpi, setKpi] = useState<KpiResult | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const isManager = !!me && (me.is_superuser || MANAGER_ROLES.includes(me.role || ""));
  const canStock = !!me && (me.is_superuser || ["RESP_TECH", "ADJOINT", "DATA_OFFICER"].includes(me.role || ""));

  const load = () => {
    setLoading(true);
    Promise.all([api<KpiResult>(`/api/kpi/?year=${year}`), api<Overview>("/api/dashboard/overview/")])
      .then(([k, o]) => {
        setKpi(k);
        setOverview(o);
        setError("");
      })
      .catch((e) => setError(online ? e.message : "Hors ligne : le tableau de bord nécessite une connexion."))
      .finally(() => setLoading(false));
  };
  useEffect(load, [year]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <main className="page wide">
      <header className="page-head">
        <div>
          {me?.role !== "FUNDER" && <Link to="/" className="back">← Fiches terrain</Link>}
          <h1>Tableau de bord E&M — {ref?.site.name ?? ""}</h1>
          {overview && (
            <p className="muted small">
              {overview.open_incidents} panne(s) ouverte(s){overview.critical_open ? `, dont ${overview.critical_open} critique(s)` : ""} ·{" "}
              {overview.submissions_to_review} fiche(s) à valider
            </p>
          )}
        </div>
      </header>

      <div className="toolbar filters" aria-label="Filtres">
        <label className="label" htmlFor="year">Année</label>
        <select id="year" value={year} onChange={(e) => setYear(Number(e.target.value))}>
          {[year - 1, year, year + 1].filter((y) => y <= new Date().getFullYear()).map((y) => <option key={y}>{y}</option>)}
        </select>
        <button className="btn secondary small" onClick={load} disabled={loading}>Actualiser</button>
        <button className="btn secondary small" onClick={() => download(`/api/kpi/export.xlsx?year=${year}`, `ymejibu_KPI_${year}.xlsx`)}>Export XLSX (format O&M KPI)</button>
        <button className="btn secondary small" onClick={() => download(`/api/kpi/export.csv?year=${year}`, `ymejibu_KPI_${year}.csv`)}>Export CSV</button>
      </div>

      <nav className="tabs" aria-label="Sections du tableau de bord">
        <NavLink end to="/tableau-de-bord">Indicateurs</NavLink>
        <NavLink to="/tableau-de-bord/carte">Carte</NavLink>
        {me?.role !== "FUNDER" && <NavLink to="/tableau-de-bord/fiches">Fiches{overview?.submissions_to_review ? ` (${overview.submissions_to_review})` : ""}</NavLink>}
        {me?.role !== "FUNDER" && <NavLink to="/tableau-de-bord/stock">Stock</NavLink>}
        <NavLink to="/tableau-de-bord/budget">Budget</NavLink>
        <NavLink to="/tableau-de-bord/plan">Plan annuel</NavLink>
      </nav>

      {error && <p className="banner critical" role="alert">{error}</p>}
      <div className={loading ? "refreshing" : ""}>
        <Routes>
          <Route index element={kpi ? <KpiView data={kpi} /> : <p>Chargement…</p>} />
          <Route path="carte" element={<Suspense fallback={<p>Chargement de la carte…</p>}><MapView /></Suspense>} />
          <Route path="fiches" element={<Review canWrite={isManager} />} />
          <Route path="stock" element={<StockView canWrite={canStock} />} />
          <Route path="budget" element={<BudgetView kpi={kpi} />} />
          <Route path="plan" element={<PlanView year={year} />} />
          <Route path="*" element={<Navigate to="/tableau-de-bord" replace />} />
        </Routes>
      </div>
    </main>
  );
}
