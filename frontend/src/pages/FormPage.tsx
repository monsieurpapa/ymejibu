import { ArrowLeft, CircleAlert, CloudUpload, GitMerge, LoaderCircle, RotateCw, Save, Send, ServerCog } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FormRenderer, withComputed } from "../forms/FormRenderer";
import { outboxGet, outboxPut } from "../lib/db";
import { emptyPayload, summaryTitle, todayISO, uuid, validate } from "../lib/forms";
import { keepMine, takeServer } from "../lib/sync";
import type { OutboxItem, Payload } from "../lib/types";
import { useApp } from "../state";
import { FormIcon, StatusTag } from "./Home";
import { Chip, FORM_META, MAINTENANCE_META } from "../ui/meta";

function diffSections(a: Payload, b: Payload) {
  const out: string[] = [];
  const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
  keys.forEach((k) => {
    if (JSON.stringify(a?.[k] ?? null) !== JSON.stringify(b?.[k] ?? null)) out.push(k);
  });
  return out;
}

export default function FormPage() {
  const { id, type } = useParams();
  const { ref, me, sync, online, notify } = useApp();
  const nav = useNavigate();
  const [item, setItem] = useState<OutboxItem | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<string>("");
  const timer = useRef<number | undefined>(undefined);

  const form = useMemo(() => ref?.forms.forms.find((f) => f.type === (item?.form_type ?? type)), [ref, item, type]);

  useEffect(() => {
    (async () => {
      if (id) {
        const existing = await outboxGet(id);
        if (existing) setItem(existing);
        else nav("/", { replace: true });
      } else if (type && ref) {
        const f = ref.forms.forms.find((x) => x.type === type);
        if (!f) return nav("/", { replace: true });
        const defaults: Record<string, any> = { date: todayISO() };
        const who = me?.full_name || "";
        for (const k of ["operator", "agent", "technician", "reported_by"]) {
          if (f.sections[0].fields?.some((x) => x.key === k)) defaults[k] = who;
        }
        if (me?.zone && f.sections[0].fields?.some((x) => x.key === "zone")) defaults.zone = me.zone;
        const fresh: OutboxItem = {
          id: uuid(),
          form_type: f.type,
          payload: withComputed(ref, f, emptyPayload(f, defaults)),
          status: "draft",
          version: null,
          updated_at: new Date().toISOString(),
          title: f.title,
        };
        await outboxPut(fresh);
        nav(`/fiche/${fresh.id}`, { replace: true });
      }
    })();
  }, [id, type, ref, me, nav]);

  if (!ref || !item || !form)
    return (
      <main className="page">
        <p className="muted" style={{ display: "flex", alignItems: "center", gap: 8 }}><LoaderCircle size={18} className="spin" aria-hidden="true" />Chargement…</p>
      </main>
    );
  const locked = item.status === "conflict";

  const change = (payload: Payload) => {
    const next: OutboxItem = {
      ...item,
      payload,
      // Editing a sent sheet makes it a draft again until it is re-submitted.
      status: ["synced", "invalid", "forbidden", "error"].includes(item.status) ? "draft" : item.status,
      updated_at: new Date().toISOString(),
      title: summaryTitle(ref, form, payload),
    };
    setItem(next);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(async () => {
      // The sync may have run meanwhile: keep its server version so this edit is not a conflict with ourselves.
      const fresh = await outboxGet(next.id);
      if (fresh && fresh.version !== next.version) {
        next.version = fresh.version;
        if (fresh.status === "conflict") {
          next.status = "conflict";
          next.server = fresh.server;
        }
      }
      await outboxPut(next);
      setSaved(`Brouillon enregistré à ${new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`);
    }, 400);
  };

  const submit = async () => {
    const errs = validate(ref, form, item.payload);
    const map: Record<string, string> = {};
    errs.forEach((e) => (map[e.field] ??= e.message));
    setErrors(map);
    if (errs.length) {
      const first = document.getElementById(errs[0].field) || document.querySelector(".has-error");
      first?.scrollIntoView({ block: "center" });
      (first as HTMLElement | null)?.focus?.();
      return;
    }
    window.clearTimeout(timer.current);
    const fresh = await outboxGet(item.id);
    await outboxPut({ ...item, version: fresh?.version ?? item.version, status: "queued", errors: [], updated_at: new Date().toISOString(), title: summaryTitle(ref, form, item.payload) });
    notify(online ? "Fiche validée, transmission en cours" : "Fiche validée : elle partira au retour du réseau", online ? "blue" : "amber");
    if (online) sync();
    nav("/", { viewTransition: true });
  };

  const maintenance = MAINTENANCE_META[item.payload.intervention?.maintenance_type as string]
    ?? (form.type.startsWith("MP_") ? MAINTENANCE_META.PREVENTIVE : undefined);
  const serverErrors = ["invalid", "forbidden", "error"].includes(item.status) ? item.errors ?? [] : [];

  return (
    <main className="page form-page">
      <Link to="/" className="back" viewTransition><ArrowLeft size={18} aria-hidden="true" />Retour</Link>
      <header className={`form-hero tone-${FORM_META[form.type]?.tone ?? "slate"}`}>
        <FormIcon type={form.type} size="lg" />
        <div style={{ minWidth: 0 }}>
          <h1>{form.title}</h1>
          <div className="sub">
            <StatusTag status={item.status} />
            {maintenance && <Chip meta={maintenance} />}
            {item.payload.general?.number && <span className="muted small">{item.payload.general.number}</span>}
          </div>
        </div>
      </header>

      {locked && item.server && (
        <div className="banner critical" role="alert" data-testid="conflict-banner">
          <GitMerge size={20} aria-hidden="true" />
          <div className="banner-body">
          <strong>Conflit :</strong> cette fiche a été modifiée sur le serveur ({item.server.submitted_by || "autre utilisateur"},
          version {item.server.version}) pendant que vous travailliez hors ligne.
          <br />Parties différentes : {diffSections(item.payload, item.server.payload).join(", ") || "aucune"}.
          <div className="row-inline">
            <button className="btn primary" onClick={async () => { await keepMine(item.id); setItem((await outboxGet(item.id))!); sync(); }}>
              <CloudUpload size={18} aria-hidden="true" />Garder ma version
            </button>
            <button className="btn secondary" onClick={async () => { await takeServer(item.id); setItem((await outboxGet(item.id))!); }}>
              <ServerCog size={18} aria-hidden="true" />Prendre la version du serveur
            </button>
          </div>
          </div>
        </div>
      )}
      {serverErrors.length > 0 && (
        <div className="banner critical" role="alert">
          <CircleAlert size={20} aria-hidden="true" />
          <div className="banner-body">
            <strong>Le serveur a refusé la fiche :</strong>
            <ul>{serverErrors.map((e, i) => <li key={i}>{e.field ? `${e.field} : ` : ""}{e.message}</li>)}</ul>
          </div>
        </div>
      )}

      <fieldset disabled={locked} className="plain">
        <FormRenderer form={form} ref_={ref} payload={item.payload} onChange={change} errors={errors} />
      </fieldset>

      <div className="sticky-actions">
        <span className="muted small saved-note" aria-live="polite">{saved && <Save size={15} aria-hidden="true" />}{saved}</span>
        <button className="btn primary lg" onClick={submit} disabled={locked} data-testid="submit">
          {item.status === "synced" ? <RotateCw size={18} aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
          {item.status === "synced" ? "Renvoyer" : "Valider et envoyer"}
        </button>
      </div>
      {Object.keys(errors).length > 0 && (
        <p className="error" role="alert"><CircleAlert size={16} aria-hidden="true" />{Object.keys(errors).length} champ(s) à corriger.</p>
      )}
      <p className="muted small">Source : {form.source}</p>
    </main>
  );
}
