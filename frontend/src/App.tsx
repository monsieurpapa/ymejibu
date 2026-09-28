import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Loading from "./components/Loading";
import SyncBar from "./components/SyncBar";
import ToastHost from "./components/Toast";
import FormPage from "./pages/FormPage";
import Home from "./pages/Home";
import Login from "./pages/Login";
import { AppProvider, useApp } from "./state";

// The dashboard (charts, map) is only downloaded by managers.
const Dashboard = lazy(() => import("./dashboard/Dashboard"));

function Shell() {
  const { ready, me } = useApp();
  if (!ready) return <Loading />;
  if (!me) return <Login />;
  return (
    <>
      <SyncBar />
      <Routes>
        <Route path="/" element={me.role === "FUNDER" ? <Navigate to="/tableau-de-bord" replace /> : <Home />} />
        <Route path="/fiche/nouvelle/:type" element={<FormPage />} />
        <Route path="/fiche/:id" element={<FormPage />} />
        <Route path="/tableau-de-bord/*" element={<Suspense fallback={<Loading />}><Dashboard /></Suspense>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <ToastHost />
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
