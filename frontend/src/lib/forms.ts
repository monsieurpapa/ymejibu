/** Client-side validation and helpers, mirroring backend/ops/forms.py. */
import type { AssetRef, FieldDef, FormDef, Payload, Reference, SectionDef } from "./types";

export interface FieldError { field: string; message: string }

const empty = (v: unknown) => v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);

export function checkValue(ref: Reference, where: string, spec: FieldDef, value: any, errors: FieldError[]) {
  if (empty(value)) {
    if (spec.required) errors.push({ field: where, message: "Champ obligatoire" });
    return;
  }
  switch (spec.type) {
    case "number":
    case "integer": {
      const n = Number(String(value).replace(",", "."));
      if (Number.isNaN(n)) errors.push({ field: where, message: "Nombre invalide" });
      else {
        if (spec.type === "integer" && !Number.isInteger(n)) errors.push({ field: where, message: "Nombre entier attendu" });
        if (spec.min !== undefined && n < spec.min) errors.push({ field: where, message: `Minimum ${spec.min}` });
        if (spec.max !== undefined && n > spec.max) errors.push({ field: where, message: `Maximum ${spec.max}` });
      }
      break;
    }
    case "enum":
      if (!ref.forms.enums[spec.enum!]?.some((o) => o.value === value)) errors.push({ field: where, message: "Valeur non autorisée" });
      break;
    case "asset":
      if (!ref.assets.some((a) => a.code === value && (!spec.assetTypes || spec.assetTypes.includes(a.type))))
        errors.push({ field: where, message: "Actif inconnu" });
      break;
    case "zone":
      if (!ref.zones.some((z) => z.code === value)) errors.push({ field: where, message: "Zone inconnue" });
      break;
    case "node":
      if (!ref.nodes.some((n) => n.code === value)) errors.push({ field: where, message: "Nœud inconnu" });
      break;
    case "stock_item":
      if (!ref.stock_items.some((s) => s.code === value)) errors.push({ field: where, message: "Article inconnu" });
      break;
  }
}

export function validate(ref: Reference, form: FormDef, payload: Payload): FieldError[] {
  const errors: FieldError[] = [];
  for (const s of form.sections) {
    const data = payload[s.key];
    if (s.kind === "fields") {
      for (const f of s.fields!) if (!f.readonly) checkValue(ref, `${s.key}.${f.key}`, f, data?.[f.key], errors);
    } else if (s.kind === "table") {
      const rows: any[] = data || [];
      if (rows.length < (s.minRows ?? 0)) errors.push({ field: s.key, message: `Au moins ${s.minRows} ligne(s)` });
      rows.forEach((row, i) => s.columns!.forEach((c) => checkValue(ref, `${s.key}[${i}].${c.key}`, c, row?.[c.key], errors)));
    } else {
      for (const row of s.rows!) {
        for (const c of s.columns!) {
          if (c.readonly || c.computed) continue;
          const spec = c.key === "value" && row.valueEnum ? { ...c, type: "enum" as const, enum: row.valueEnum } : c;
          checkValue(ref, `${s.key}.${row.key}.${c.key}`, spec, data?.[row.key]?.[c.key], errors);
        }
      }
    }
  }
  const date = payload.general?.date;
  if (date) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    if (date > tomorrow.toISOString().slice(0, 10)) errors.push({ field: "general.date", message: "Date dans le futur" });
  }
  return errors;
}

export function getPath(payload: Payload, path?: string) {
  if (!path) return undefined;
  const [s, f] = path.split(".");
  return payload?.[s]?.[f];
}

export function assetByCode(ref: Reference, code?: string): AssetRef | undefined {
  return ref.assets.find((a) => a.code === code);
}

export function threshold(ref: Reference, parameter: string, asset?: AssetRef) {
  const t = ref.thresholds.filter((x) => x.parameter === parameter);
  return (
    (asset && t.find((x) => x.asset === asset.code)) ||
    (asset && t.find((x) => !x.asset && x.asset_type === asset.type)) ||
    t.find((x) => !x.asset && !x.asset_type)
  );
}

export function thresholdLabel(ref: Reference, parameter: string, asset?: AssetRef) {
  const t = threshold(ref, parameter, asset);
  if (!t) return "—";
  if (t.min !== null && t.max !== null) return `${t.min} – ${t.max}`;
  if (t.max !== null) return `≤ ${t.max}`;
  if (t.min !== null) return `≥ ${t.min}`;
  return "—";
}

/** "OUI" / "NON" / "" from a measured value against the configured range. */
export function compliance(ref: Reference, parameter: string, value: any, asset?: AssetRef): string {
  if (parameter === "ODOUR_COLOUR") return value === "OUI" ? "NON" : value === "NON" ? "OUI" : "";
  if (empty(value)) return "";
  const n = Number(String(value).replace(",", "."));
  const t = threshold(ref, parameter, asset);
  if (!t || Number.isNaN(n)) return "";
  if (t.min !== null && n < t.min) return "NON";
  if (t.max !== null && n > t.max) return "NON";
  return "OUI";
}

export const QUALITY_PARAM: Record<string, string> = {
  residual_chlorine: "RESIDUAL_CHLORINE",
  turbidity: "TURBIDITY",
  odour_colour: "ODOUR_COLOUR",
};

export function emptyPayload(form: FormDef, defaults: Record<string, any> = {}): Payload {
  const p: Payload = {};
  for (const s of form.sections) {
    if (s.kind === "table") p[s.key] = s.minRows ? Array.from({ length: s.minRows }, () => ({})) : [];
    else p[s.key] = {};
  }
  p.general = { ...(p.general || {}), ...defaults };
  return p;
}

export function sectionLabel(s: SectionDef) {
  return s.title;
}

export function summaryTitle(ref: Reference, form: FormDef, payload: Payload) {
  const g = payload.general || {};
  const scope = form.scope.asset_field ? assetByCode(ref, getPath(payload, form.scope.asset_field))?.name : undefined;
  const zone = form.scope.zone_field ? ref.zones.find((z) => z.code === getPath(payload, form.scope.zone_field))?.name : undefined;
  const d = g.date ? new Date(g.date + "T00:00:00").toLocaleDateString("fr-FR") : "sans date";
  return [form.title.replace(/^Fiche journalière d'exploitation – /, "").replace(/^Checklist – /, ""), scope || zone, d]
    .filter(Boolean)
    .join(" · ");
}

/** Resize to max 1280 px and JPEG q=0.6: a phone photo drops from ~4 MB to ~150 kB. */
export async function compressPhoto(file: File, maxSide = 1280, quality = 0.6): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = reject;
      i.src = url;
    });
    const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", quality);
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) =>
    (+c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))).toString(16),
  );
}

export function todayISO() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}
