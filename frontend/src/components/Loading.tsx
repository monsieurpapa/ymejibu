import { LoaderCircle } from "lucide-react";

export default function Loading({ text = "Chargement…" }: { text?: string }) {
  return (
    <main className="page">
      <p className="muted" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <LoaderCircle size={18} className="spin" aria-hidden="true" />
        {text}
      </p>
    </main>
  );
}
