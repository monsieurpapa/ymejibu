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
      <h1>Yme Jibu — Exploitation & Maintenance</h1>
      <p className="muted">Réseau d'eau Goma Ouest</p>
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
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn primary block" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}</button>
      </form>
      <p className="muted small">Après la première connexion, l'application fonctionne sans réseau : les fiches sont envoyées dès que la connexion revient.</p>
    </main>
  );
}
