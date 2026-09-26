export type FieldType =
  | "text" | "textarea" | "number" | "integer" | "date" | "time" | "datetime" | "enum"
  | "asset" | "zone" | "node" | "stock_item" | "gps" | "photos" | "auto"
  | "asset_specs" | "asset_capacity" | "asset_location" | "threshold";

export interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  required?: boolean;
  readonly?: boolean;
  computed?: boolean;
  unit?: string;
  min?: number;
  max?: number;
  enum?: string;
  assetTypes?: string[];
  parentFrom?: string;
  zoneFrom?: string;
  unitFromRow?: boolean;
  added?: boolean;
  note?: string;
}

export interface RowDef { key: string; label: string; unit?: string; valueEnum?: string }

export interface SectionDef {
  key: string;
  title: string;
  kind: "fields" | "table" | "checklist";
  fields?: FieldDef[];
  columns?: FieldDef[];
  rows?: RowDef[];
  minRows?: number;
  maxRows?: number;
  note?: string;
}

export interface FormDef {
  type: string;
  title: string;
  source: string;
  intro?: string;
  roles: string[];
  scope: { asset_field?: string; zone_field?: string };
  sections: SectionDef[];
}

export interface FormsDoc {
  version: number;
  enums: Record<string, { value: string; label: string }[]>;
  forms: FormDef[];
}

export interface AssetRef {
  code: string; name: string; type: string; parent: string | null; zone: string | null;
  lat: number | null; lon: number | null; capacity: string; specs: string;
}

export interface Reference {
  site: { code: string; name: string };
  zones: { code: string; name: string }[];
  assets: AssetRef[];
  nodes: { code: string; kind: string; zone: string | null }[];
  stock_items: { code: string; name: string; unit: string }[];
  thresholds: { parameter: string; asset_type: string; asset: string | null; min: number | null; max: number | null }[];
  forms: FormsDoc;
}

export interface Me {
  username: string; full_name: string; role: string | null; role_label: string;
  zone: string | null; site: string | null; is_superuser: boolean;
}

export type Payload = Record<string, any>;

export type OutboxStatus = "draft" | "queued" | "synced" | "conflict" | "invalid" | "forbidden" | "error";

export interface OutboxItem {
  id: string;
  form_type: string;
  payload: Payload;
  status: OutboxStatus;
  version: number | null; // server version this copy is based on
  server?: { payload: Payload; version: number; updated_at: string; submitted_by: string | null } | null;
  errors?: { field: string; message: string }[];
  updated_at: string;
  synced_at?: string;
  title: string;
}

export const MANAGER_ROLES = ["RESP_TECH", "ADJOINT", "DATA_OFFICER"];
export const DASHBOARD_ROLES = [...MANAGER_ROLES, "FUNDER", "SSE"];
