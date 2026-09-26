import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import SyncBar from "./components/SyncBar";
import FormPage from "./pages/FormPage";
import Home from "./pages/Home";
import Login from "./pages/Login";
import { AppProvider, useApp } from "./state";

// The dashboard (charts, map) is only downloaded by managers.
const Dashboard = lazy(() => import("./dashboard/Dashboard"));

function Shell() {
  const { ready, me } = useApp();
  if (!ready) return <main className="page"><p>Chargement…</p></main>;
  if (!me) return <Login />;
  return (
    <>
      <SyncBar />
      <Routes>
        <Route path="/" element={me.role === "FUNDER" ? <Navigate to="/tableau-de-bord" replace /> : <Home />} />
        <Route path="/fiche/nouvelle/:type" element={<FormPage />} />
        <Route path="/fiche/:id" element={<FormPage />} />
        <Route path="/tableau-de-bord/*" element={<Suspense fallback={<main className="page"><p>Chargement…</p></main>}><Dashboard /></Suspense>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </AppProvider>
  );
}
