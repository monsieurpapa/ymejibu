import { Camera, CircleAlert, Crosshair, LoaderCircle, MapPin, Trash2 } from "lucide-react";
import { useState } from "react";
import { ENUM_TONES } from "../ui/meta";
import { compressPhoto, assetByCode, getPath, thresholdLabel } from "../lib/forms";
import type { FieldDef, Payload, Reference } from "../lib/types";

interface Props {
  id: string;
  spec: FieldDef;
  value: any;
  onChange: (v: any) => void;
  ref_: Reference;
  payload: Payload;
  error?: string;
  rowUnit?: string;
  row?: Record<string, any>;
  hideLabel?: boolean;
  thresholdParam?: string;
}

export function Label({ spec, htmlFor, unit }: { spec: FieldDef; htmlFor: string; unit?: string }) {
  return (
    <label className="label" htmlFor={htmlFor}>
      {spec.label}
      {unit && !spec.label.includes("(") ? ` (${unit})` : ""}
      {spec.required && <span className="req" aria-hidden> *</span>}
      {spec.added && <span className="badge" title={spec.note}>ajouté</span>}
    </label>
  );
}

function Segmented({ id, enumKey, options, value, onChange }: { id: string; enumKey?: string; options: { value: string; label: string }[]; value: any; onChange: (v: any) => void }) {
  const tones = (enumKey && ENUM_TONES[enumKey]) || {};
  return (
    <div className="segmented" role="radiogroup" id={id}>
      {options.map((o) => (
        <button
          type="button"
          key={o.value}
          role="radio"
          aria-checked={value === o.value}
          className={`seg${value === o.value ? " on" : ""}${tones[o.value] ? ` tone-${tones[o.value].tone}` : ""}`}
          onClick={() => onChange(value === o.value ? "" : o.value)}
        >
          {(() => {
            const Icon = tones[o.value]?.icon;
            return Icon ? <Icon size={16} aria-hidden="true" /> : null;
          })()}
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function FieldInput({ id, spec, value, onChange, ref_, payload, error, rowUnit, row, hideLabel, thresholdParam }: Props) {
  const [busy, setBusy] = useState(false);
  const [gpsError, setGpsError] = useState("");
  const invalid = error ? { "aria-invalid": true as const, "aria-describedby": `${id}-err` } : {};
  const common = { id, name: id, ...invalid };
  let input: React.ReactNode;

  switch (spec.type) {
    case "number":
    case "integer":
      input = (
        <input
          {...common}
          type="text"
          inputMode="decimal"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value.replace(",", "."))}
          readOnly={spec.readonly}
        />
      );
      break;
    case "date":
      input = <input {...common} type="date" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
      break;
    case "time":
      input = <input {...common} type="time" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
      break;
    case "datetime":
      input = <input {...common} type="datetime-local" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
      break;
    case "textarea":
      input = <textarea {...common} rows={3} value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
      break;
    case "enum": {
      const options = ref_.forms.enums[spec.enum!] || [];
      if (spec.computed) {
        const o = options.find((x) => x.value === value);
        input = (
          <output id={id} className={`computed ${value === "NON" ? "bad" : value === "OUI" ? "good" : ""}`}>
            {o ? o.label : "—"}
            {value === "NON" && <span className="sr"> (non conforme)</span>}
          </output>
        );
      } else if (options.length <= 3) {
        input = <Segmented id={id} enumKey={spec.enum} options={options} value={value} onChange={onChange} />;
      } else {
        input = (
          <select {...common} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
            <option value="">— Choisir —</option>
            {options.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        );
      }
      break;
    }
    case "asset": {
      let assets = ref_.assets.filter((a) => !spec.assetTypes || spec.assetTypes.includes(a.type));
      const parent = getPath(payload, spec.parentFrom);
      if (spec.parentFrom && parent) assets = assets.filter((a) => a.parent === parent);
      const zone = getPath(payload, spec.zoneFrom);
      if (spec.zoneFrom && zone) {
        const inZone = assets.filter((a) => a.zone === zone || !a.zone);
        if (inZone.length) assets = inZone;
      }
      input = (
        <select {...common} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
          <option value="">— Choisir —</option>
          {assets.map((a) => (
            <option key={a.code} value={a.code}>{a.name} ({a.code})</option>
          ))}
        </select>
      );
      break;
    }
    case "zone":
      input = (
        <select {...common} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
          <option value="">— Choisir —</option>
          {ref_.zones.map((z) => (
            <option key={z.code} value={z.code}>{z.name}</option>
          ))}
        </select>
      );
      break;
    case "node":
      input = (
        <select {...common} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
          <option value="">— Nœud —</option>
          {ref_.nodes.map((n) => (
            <option key={n.code} value={n.code}>{n.code}</option>
          ))}
        </select>
      );
      break;
    case "stock_item":
      input = (
        <select {...common} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
          <option value="">— Article —</option>
          {ref_.stock_items.map((s) => (
            <option key={s.code} value={s.code}>{s.name}{s.unit ? ` (${s.unit})` : ""}</option>
          ))}
        </select>
      );
      break;
    case "gps":
      input = (
        <div className="row-inline">
          <button
            type="button"
            className="btn secondary"
            disabled={busy}
            onClick={() => {
              setGpsError("");
              if (!navigator.geolocation) return setGpsError("GPS indisponible sur cet appareil");
              setBusy(true);
              navigator.geolocation.getCurrentPosition(
                (p) => {
                  setBusy(false);
                  onChange({ lat: +p.coords.latitude.toFixed(6), lon: +p.coords.longitude.toFixed(6), accuracy_m: Math.round(p.coords.accuracy) });
                },
                (err) => {
                  setBusy(false);
                  setGpsError(err.message || "Position introuvable");
                },
                { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 },
              );
            }}
          >
            {busy ? <LoaderCircle size={18} className="spin" aria-hidden="true" /> : value ? <Crosshair size={18} aria-hidden="true" /> : <MapPin size={18} aria-hidden="true" />}
            {busy ? "Recherche…" : value ? "Relever à nouveau" : "Relever la position"}
          </button>
          <span className="muted">
            {value ? `${value.lat}, ${value.lon}${value.accuracy_m ? ` (± ${value.accuracy_m} m)` : ""}` : gpsError || "Non relevée"}
          </span>
        </div>
      );
      break;
    case "photos": {
      const photos: any[] = value || [];
      input = (
        <div>
          <div className="thumbs">
            {photos.map((p, i) => (
              <figure key={i} className="thumb">
                <img src={typeof p === "string" ? p : p.url} alt={`Photo ${i + 1}`} />
                <button type="button" className="btn link danger small" onClick={() => onChange(photos.filter((_, k) => k !== i))}>
                  <Trash2 size={15} aria-hidden="true" />Retirer
                </button>
              </figure>
            ))}
          </div>
          {photos.length < 3 && (
            <label className="btn secondary file">
              {busy ? <LoaderCircle size={18} className="spin" aria-hidden="true" /> : <Camera size={18} aria-hidden="true" />}
              {busy ? "Compression…" : "Ajouter une photo"}
              <input
                type="file"
                accept="image/*"
                capture="environment"
                hidden
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  setBusy(true);
                  try {
                    onChange([...photos, await compressPhoto(f)]);
                  } finally {
                    setBusy(false);
                    e.target.value = "";
                  }
                }}
              />
            </label>
          )}
        </div>
      );
      break;
    }
    case "auto":
      input = <output id={id} className="computed">{value || "attribué à l'envoi"}</output>;
      break;
    case "asset_specs":
    case "asset_capacity":
    case "asset_location": {
      const scopeCode = payload.general?.station ?? payload.general?.reservoir;
      const a = assetByCode(ref_, scopeCode);
      const text = !a
        ? "—"
        : spec.type === "asset_specs"
          ? ref_.assets.filter((x) => x.parent === a.code && x.type === "PUMP").map((x) => `${x.name.split(" — ")[0]}`).join(" ; ") || a.specs || "—"
          : spec.type === "asset_capacity"
            ? a.capacity || "—"
            : a.lat !== null ? `${a.lat}, ${a.lon}` : "GPS non renseigné";
      input = <output id={id} className="computed">{text}</output>;
      break;
    }
    case "threshold": {
      const scope = assetByCode(ref_, row?.kiosk ?? payload.general?.station ?? payload.general?.reservoir);
      input = <output id={id} className="computed">{thresholdParam ? thresholdLabel(ref_, thresholdParam, scope) : "—"}</output>;
      break;
    }
    default:
      input = <input {...common} type="text" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
  }

  return (
    <div className={`field ${error ? "has-error" : ""}`}>
      {!hideLabel && <Label spec={spec} htmlFor={id} unit={spec.unitFromRow ? rowUnit : undefined} />}
      {input}
      {spec.note && spec.added && <p className="hint">{spec.note}</p>}
      {error && (
        <p className="error" id={`${id}-err`} role="alert"><CircleAlert size={16} aria-hidden="true" />{error}</p>
      )}
    </div>
  );
}
