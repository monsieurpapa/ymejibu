import { ArrowLeft, CalendarRange, ChartLine, ClipboardList, FileSpreadsheet, FileText, LoaderCircle, Map as MapIcon, Package, RefreshCw, Siren, TriangleAlert, Users, Wallet } from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api, download } from "../lib/api";
import { MANAGER_ROLES } from "../lib/types";
import { useApp } from "../state";
import { Chip } from "../ui/meta";
import KpiView, { type KpiResult } from "./KpiView";
import { BudgetView, PlanView } from "./PlanView";
import Review from "./Review";
import StockView from "./StockView";
import UsersView from "./UsersView";

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
          {me?.role !== "FUNDER" && <Link to="/" className="back" viewTransition><ArrowLeft size={18} aria-hidden="true" />Retour aux fiches terrain</Link>}
          <h1>Tableau de bord E&M — {ref?.site.name ?? ""}</h1>
          {overview && (
            <div className="overview">
              <Chip meta={{ icon: Siren, tone: overview.open_incidents ? "orange" : "green", label: `${overview.open_incidents} panne(s) ouverte(s)` }} />
              {overview.critical_open > 0 && <Chip meta={{ icon: TriangleAlert, tone: "red", label: `${overview.critical_open} critique(s)` }} />}
              <Chip meta={{ icon: ClipboardList, tone: overview.submissions_to_review ? "amber" : "green", label: `${overview.submissions_to_review} fiche(s) à valider` }} />
            </div>
          )}
        </div>
      </header>

      <div className="toolbar filters" aria-label="Filtres">
        <label className="label" htmlFor="year">Année</label>
        <select id="year" value={year} onChange={(e) => setYear(Number(e.target.value))}>
          {[year - 1, year, year + 1].filter((y) => y <= new Date().getFullYear()).map((y) => <option key={y}>{y}</option>)}
        </select>
        <button className="btn secondary small" onClick={load} disabled={loading}>
          <RefreshCw size={16} className={loading ? "spin" : ""} aria-hidden="true" />Actualiser
        </button>
        <button className="btn outline-success small" onClick={() => download(`/api/kpi/export.xlsx?year=${year}`, `ymejibu_KPI_${year}.xlsx`)}>
          <FileSpreadsheet size={16} aria-hidden="true" />Export XLSX (format O&M KPI)
        </button>
        <button className="btn secondary small" onClick={() => download(`/api/kpi/export.csv?year=${year}`, `ymejibu_KPI_${year}.csv`)}>
          <FileText size={16} aria-hidden="true" />Export CSV
        </button>
      </div>

      <nav className="tabs" aria-label="Sections du tableau de bord">
        <NavLink end to="/tableau-de-bord" viewTransition><ChartLine size={18} aria-hidden="true" />Indicateurs</NavLink>
        <NavLink to="/tableau-de-bord/carte" viewTransition><MapIcon size={18} aria-hidden="true" />Carte</NavLink>
        {me?.role !== "FUNDER" && (
          <NavLink to="/tableau-de-bord/fiches" viewTransition>
            <ClipboardList size={18} aria-hidden="true" />Fiches
            {overview?.submissions_to_review ? <span className="count"><span className="sr">, à valider : </span>{overview.submissions_to_review}</span> : null}
          </NavLink>
        )}
        {me?.role !== "FUNDER" && <NavLink to="/tableau-de-bord/stock" viewTransition><Package size={18} aria-hidden="true" />Stock</NavLink>}
        <NavLink to="/tableau-de-bord/budget" viewTransition><Wallet size={18} aria-hidden="true" />Budget</NavLink>
        <NavLink to="/tableau-de-bord/plan" viewTransition><CalendarRange size={18} aria-hidden="true" />Plan annuel</NavLink>
        {me?.is_superuser && <NavLink to="/tableau-de-bord/utilisateurs" viewTransition><Users size={18} aria-hidden="true" />Utilisateurs</NavLink>}
      </nav>

      {error && <p className="banner critical" role="alert"><TriangleAlert size={20} aria-hidden="true" /><span className="banner-body">{error}</span></p>}
      <div className={loading ? "refreshing" : ""}>
        <Routes>
          <Route index element={kpi ? <KpiView data={kpi} /> : <KpiSkeleton />} />
          <Route path="carte" element={<Suspense fallback={<Spinner text="Chargement de la carte…" />}><MapView /></Suspense>} />
          <Route path="fiches" element={<Review canWrite={isManager} />} />
          <Route path="stock" element={<StockView canWrite={canStock} />} />
          <Route path="budget" element={<BudgetView kpi={kpi} />} />
          <Route path="plan" element={<PlanView year={year} />} />
          <Route path="utilisateurs" element={<UsersView />} />
          <Route path="*" element={<Navigate to="/tableau-de-bord" replace />} />
        </Routes>
      </div>
    </main>
  );
}

function Spinner({ text }: { text: string }) {
  return (
    <p className="muted" style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <LoaderCircle size={18} className="spin" aria-hidden="true" />{text}
    </p>
  );
}

/** Placeholder cards while the indicators load (keeps the layout from jumping). */
function KpiSkeleton() {
  return (
    <div className="kpi-grid" aria-busy="true" aria-label="Chargement des indicateurs">
      {Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton skeleton-card" />)}
    </div>
  );
}
