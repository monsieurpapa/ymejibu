/**
 * Visual vocabulary of the app: one icon + one colour family per kind of work.
 * Colours are CSS tokens (styles.css) so light/dark themes stay consistent;
 * every icon is decorative (aria-hidden) and always paired with a text label.
 */
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  CircleAlert,
  CircleCheck,
  CircleX,
  Clock,
  ClipboardCheck,
  Container,
  FilePen,
  Gauge,
  LifeBuoy,
  PackagePlus,
  RefreshCw,
  ShieldCheck,
  SlidersHorizontal,
  Siren,
  TriangleAlert,
  Waypoints,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import type { OutboxStatus } from "../lib/types";

/** Tone = colour family defined in styles.css (--tone-*-fg / -bg / -solid). */
export type Tone = "blue" | "teal" | "violet" | "red" | "orange" | "green" | "amber" | "slate";

export interface Meta {
  icon: LucideIcon;
  tone: Tone;
  label: string;
  hint?: string;
}

/** The 7 field forms. */
export const FORM_META: Record<string, Meta & { group: "daily" | "incident" | "preventive" }> = {
  POMPAGE: { icon: Gauge, tone: "blue", label: "Pompage", hint: "Marche des pompes, énergie, qualité de l'eau", group: "daily" },
  STOCKAGE: { icon: Container, tone: "teal", label: "Stockage", hint: "Niveaux, volumes, contrôles du réservoir", group: "daily" },
  RESEAU_BF: { icon: Waypoints, tone: "violet", label: "Réseau et BF", hint: "Inspection du réseau, bornes fontaines, ventes", group: "daily" },
  PANNE: { icon: TriangleAlert, tone: "red", label: "Panne", hint: "Signaler une panne, l'intervention et les pièces", group: "incident" },
  MP_POMPE: { icon: ShieldCheck, tone: "green", label: "Préventif pompe", hint: "Contrôles mécanique, électrique, performance", group: "preventive" },
  MP_RESERVOIR: { icon: ShieldCheck, tone: "green", label: "Préventif réservoir", hint: "Contrôles structurels et sanitaires", group: "preventive" },
  MP_RESEAU: { icon: ShieldCheck, tone: "green", label: "Préventif réseau", hint: "Vannes, ventouses, bornes fontaines", group: "preventive" },
};

/** Sub-icon shown on preventive tiles so the three checklists stay distinguishable. */
export const PREVENTIVE_TARGET: Record<string, LucideIcon> = {
  MP_POMPE: Gauge,
  MP_RESERVOIR: Container,
  MP_RESEAU: Waypoints,
};

export const FORM_GROUPS: { key: "daily" | "incident" | "preventive"; title: string; icon: LucideIcon; tone: Tone }[] = [
  { key: "daily", title: "Relevés journaliers", icon: ClipboardCheck, tone: "blue" },
  { key: "incident", title: "Pannes et interventions", icon: Siren, tone: "red" },
  { key: "preventive", title: "Maintenance préventive", icon: ShieldCheck, tone: "green" },
];

/** Maintenance types (O&M KPI cost split, incident intervention type, budget lines). */
export const MAINTENANCE_META: Record<string, Meta> = {
  URGENT: { icon: Siren, tone: "red", label: "Urgente (MU)" },
  CORRECTIVE: { icon: Wrench, tone: "orange", label: "Corrective (MC)" },
  PREVENTIVE: { icon: ShieldCheck, tone: "green", label: "Préventive (MP)" },
  ROUTINE: { icon: RefreshCw, tone: "blue", label: "Exploitation de routine" },
  SUPPORT: { icon: LifeBuoy, tone: "slate", label: "Support" },
};

/** Maps a budget line label (French, from the API) back to its maintenance type. */
export function maintenanceFromLabel(label: string | undefined): Meta | undefined {
  if (!label) return undefined;
  const l = label.toLowerCase();
  if (l.includes("urgente")) return MAINTENANCE_META.URGENT;
  if (l.includes("corrective")) return MAINTENANCE_META.CORRECTIVE;
  if (l.includes("préventive")) return MAINTENANCE_META.PREVENTIVE;
  if (l.includes("routine")) return MAINTENANCE_META.ROUTINE;
  if (l.includes("support")) return MAINTENANCE_META.SUPPORT;
  return undefined;
}

/** Enum values that get a colour/icon when selected in a segmented control. */
export const ENUM_TONES: Record<string, Record<string, { tone: Tone; icon?: LucideIcon }>> = {
  bon_mauvais: { BON: { tone: "green", icon: CircleCheck }, MAUVAIS: { tone: "red", icon: CircleX } },
  gravite: { LOW: { tone: "amber" }, MEDIUM: { tone: "orange" }, CRITICAL: { tone: "red", icon: CircleAlert } },
  type_intervention: { URGENT: { tone: "red", icon: Siren }, CORRECTIVE: { tone: "orange", icon: Wrench } },
};

/** Outbox states shown on the phone. */
export const STATUS_META: Record<OutboxStatus, Meta> = {
  draft: { icon: FilePen, tone: "slate", label: "Brouillon" },
  queued: { icon: Clock, tone: "amber", label: "En attente d'envoi" },
  synced: { icon: CircleCheck, tone: "green", label: "Envoyée" },
  conflict: { icon: CircleAlert, tone: "red", label: "Conflit à résoudre" },
  invalid: { icon: CircleX, tone: "red", label: "Refusée : à corriger" },
  forbidden: { icon: CircleX, tone: "red", label: "Non autorisée" },
  error: { icon: CircleAlert, tone: "red", label: "Erreur" },
};

/** Stock movement kinds. */
export const MOVEMENT_META: Record<string, Meta> = {
  OPENING: { icon: PackagePlus, tone: "blue", label: "Stock initial" },
  IN: { icon: ArrowDownToLine, tone: "green", label: "Entrée" },
  OUT: { icon: ArrowUpFromLine, tone: "red", label: "Sortie" },
  ADJUST: { icon: SlidersHorizontal, tone: "amber", label: "Ajustement" },
};

/** Round coloured badge holding an icon. */
export function IconBadge({ icon: Icon, tone, size = "md" }: { icon: LucideIcon; tone: Tone; size?: "sm" | "md" | "lg" }) {
  const px = size === "lg" ? 26 : size === "sm" ? 16 : 20;
  return (
    <span className={`icon-badge ${size} tone-${tone}`} aria-hidden="true">
      <Icon size={px} strokeWidth={2} />
    </span>
  );
}

/** Small coloured label with icon (status, maintenance type…). */
export function Chip({ meta, className = "" }: { meta: Meta; className?: string }) {
  const Icon = meta.icon;
  return (
    <span className={`chip tone-${meta.tone} ${className}`}>
      <Icon size={14} strokeWidth={2.25} aria-hidden="true" />
      {meta.label}
    </span>
  );
}
