import { CircleAlert, Droplets, LoaderCircle, LogIn, WifiOff } from "lucide-react";
import { useState } from "react";
import { login } from "../lib/api";
import { useApp } from "../state";

export default function Login() {
  const { setMe, online } = useApp();
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <main className="login">
      <div className="login-brand">
        <span className="login-mark" aria-hidden="true"><Droplets size={34} strokeWidth={2.25} /></span>
        <h1>Yme Jibu — Exploitation & Maintenance</h1>
        <p className="muted" style={{ margin: 0 }}>Réseau d'eau Goma Ouest</p>
      </div>
      <form
        className="card"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            setMe(await login(username.trim(), password));
          } catch (err: any) {
            setError(online ? err.message || "Connexion impossible" : "Première connexion : une connexion internet est nécessaire.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="field">
          <label className="label" htmlFor="username">Identifiant</label>
          <input id="username" autoComplete="username" autoCapitalize="none" value={username} onChange={(e) => setU(e.target.value)} required />
        </div>
        <div className="field">
          <label className="label" htmlFor="password">Mot de passe</label>
          <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setP(e.target.value)} required />
        </div>
        {error && <p className="error" role="alert"><CircleAlert size={16} aria-hidden="true" />{error}</p>}
        <button className="btn primary block lg" disabled={busy}>
          {busy ? <LoaderCircle size={18} className="spin" aria-hidden="true" /> : <LogIn size={18} aria-hidden="true" />}
          {busy ? "Connexion…" : "Se connecter"}
        </button>
      </form>
      <p className="muted small" style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <WifiOff size={16} aria-hidden="true" style={{ marginTop: 2 }} />
        Après la première connexion, l'application fonctionne sans réseau : les fiches sont envoyées dès que la connexion revient.
      </p>
    </main>
  );
}
