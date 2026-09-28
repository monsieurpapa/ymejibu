import { CircleAlert, Info, Plus, Trash2 } from "lucide-react";
import { assetByCode, compliance, QUALITY_PARAM } from "../lib/forms";
import type { FormDef, Payload, Reference, SectionDef } from "../lib/types";
import { FieldInput } from "./Field";

/** Fill the computed "Conforme ?" columns from the configured quality thresholds. */
export function withComputed(ref: Reference, form: FormDef, payload: Payload): Payload {
  const p = { ...payload };
  const scope = assetByCode(ref, p.general?.station ?? p.general?.reservoir);
  if (p.quality && form.sections.some((s) => s.key === "quality")) {
    const q = { ...p.quality };
    for (const [row, param] of Object.entries(QUALITY_PARAM)) {
      if (q[row]) q[row] = { ...q[row], conforme: compliance(ref, param, q[row].value, scope) };
    }
    p.quality = q;
  }
  if (Array.isArray(p.kiosks) && form.type === "RESEAU_BF") {
    p.kiosks = p.kiosks.map((r: any) => ({
      ...r,
      conforme: compliance(ref, "RESIDUAL_CHLORINE", r.residual_chlorine, assetByCode(ref, r.kiosk)),
    }));
  }
  return p;
}

interface Props {
  form: FormDef;
  ref_: Reference;
  payload: Payload;
  onChange: (p: Payload) => void;
  errors: Record<string, string>;
}

export function FormRenderer({ form, ref_, payload, onChange, errors }: Props) {
  const set = (next: Payload) => onChange(withComputed(ref_, form, next));
  return (
    <div className="form">
      {form.intro && <p className="intro"><Info size={18} aria-hidden="true" style={{ marginTop: 2 }} /><span>{form.intro}</span></p>}
      {form.sections.map((s) => (
        <Section key={s.key} s={s} ref_={ref_} payload={payload} set={set} errors={errors} />
      ))}
    </div>
  );
}

function Section({ s, ref_, payload, set, errors }: { s: SectionDef; ref_: Reference; payload: Payload; set: (p: Payload) => void; errors: Record<string, string> }) {
  const data = payload[s.key];
  const sectionError = errors[s.key];
  if (s.kind === "fields") {
    return (
      <fieldset className="card">
        <legend>{s.title}</legend>
        {s.fields!.map((f) => (
          <FieldInput
            key={f.key}
            id={`${s.key}.${f.key}`}
            spec={f}
            value={data?.[f.key]}
            ref_={ref_}
            payload={payload}
            error={errors[`${s.key}.${f.key}`]}
            onChange={(v) => set({ ...payload, [s.key]: { ...(data || {}), [f.key]: v } })}
          />
        ))}
      </fieldset>
    );
  }
  if (s.kind === "checklist") {
    return (
      <fieldset className="card">
        <legend>{s.title}</legend>
        {s.rows!.map((row) => {
          const values = data?.[row.key] || {};
          return (
            <div className="check-row" key={row.key}>
              <div className="check-title">{row.label}{row.unit ? ` (${row.unit})` : ""}</div>
              <div className="check-cols">
                {s.columns!.map((c) => {
                  const spec = c.key === "value" && row.valueEnum ? { ...c, type: "enum" as const, enum: row.valueEnum } : c;
                  const id = `${s.key}.${row.key}.${c.key}`;
                  if (c.type === "threshold" && !QUALITY_PARAM[row.key]) return null;
                  if (c.computed && !QUALITY_PARAM[row.key]) return null;
                  return (
                    <FieldInput
                      key={c.key}
                      id={id}
                      spec={spec}
                      value={values[c.key]}
                      ref_={ref_}
                      payload={payload}
                      rowUnit={row.unit}
                      thresholdParam={QUALITY_PARAM[row.key]}
                      error={errors[id]}
                      onChange={(v) => set({ ...payload, [s.key]: { ...(data || {}), [row.key]: { ...values, [c.key]: v } } })}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </fieldset>
    );
  }
  const rows: any[] = data || [];
  const setRows = (next: any[]) => set({ ...payload, [s.key]: next });
  return (
    <fieldset className="card">
      <legend>{s.title}</legend>
      {s.note && <p className="hint">{s.note}</p>}
      {rows.length === 0 && <p className="muted">Aucune ligne.</p>}
      {rows.map((row, i) => (
        <div className="table-row" key={i}>
          <div className="table-row-head">
            <strong>Ligne {i + 1}</strong>
            {rows.length > (s.minRows ?? 0) && (
              <button type="button" className="btn link danger small" onClick={() => setRows(rows.filter((_, k) => k !== i))}>
                <Trash2 size={15} aria-hidden="true" />Supprimer
              </button>
            )}
          </div>
          <div className="grid-cols">
            {s.columns!.map((c) => {
              const id = `${s.key}[${i}].${c.key}`;
              return (
                <FieldInput
                  key={c.key}
                  id={id}
                  spec={c}
                  value={row[c.key]}
                  ref_={ref_}
                  payload={payload}
                  row={row}
                  error={errors[id]}
                  onChange={(v) => setRows(rows.map((r, k) => (k === i ? { ...r, [c.key]: v } : r)))}
                />
              );
            })}
          </div>
        </div>
      ))}
      {sectionError && <p className="error" role="alert"><CircleAlert size={16} aria-hidden="true" />{sectionError}</p>}
      {rows.length < (s.maxRows ?? 50) && (
        <button type="button" className="btn secondary" onClick={() => setRows([...rows, {}])}>
          <Plus size={18} aria-hidden="true" />Ajouter une ligne
        </button>
      )}
    </fieldset>
  );
}
