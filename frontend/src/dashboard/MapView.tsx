import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../lib/api";

interface MapData {
  assets: { code: string; name: string; type: string; type_label: string; condition: string; lat: number | null; lon: number | null; flags: string[] }[];
  incidents: { number: string; status: string; status_label: string; severity: string; severity_label: string; type: string; date: string;
    lat: number | null; lon: number | null; asset: string | null; node: string | null }[];
}

const TYPE_STYLE: Record<string, { color: string; radius: number }> = {
  KIOSK: { color: "#2a78d6", radius: 7 },
  PRIVATE_CONNECTION: { color: "#4a3aa7", radius: 6 },
  RESERVOIR: { color: "#1baf7a", radius: 9 },
  STORAGE_SITE: { color: "#1baf7a", radius: 9 },
  PUMP_STATION: { color: "#eb6834", radius: 9 },
};
const SEVERITY: Record<string, string> = { CRITICAL: "#d03b3b", MEDIUM: "#ec835a", LOW: "#fab219" };

export default function MapView() {
  const el = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<MapData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<MapData>("/api/dashboard/map/?days=180").then(setData).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!data || !el.current) return;
    const map = L.map(el.current, { zoomControl: true, attributionControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap",
    }).addTo(map);
    const pts: L.LatLngExpression[] = [];
    const text = (s: string) => {
      const d = document.createElement("div");
      d.textContent = s;
      return d.innerHTML;
    };
    data.assets.filter((a) => a.lat !== null && TYPE_STYLE[a.type]).forEach((a) => {
      const st = TYPE_STYLE[a.type];
      pts.push([a.lat!, a.lon!]);
      L.circleMarker([a.lat!, a.lon!], { radius: st.radius, color: "#fcfcfb", weight: 2, fillColor: st.color, fillOpacity: 1 })
        .bindPopup(`<strong>${text(a.name)}</strong><br>${text(a.code)} · ${text(a.type_label)}<br>État : ${text(a.condition)}${
          a.flags.includes("A16") ? "<br><em>Position à vérifier sur le terrain</em>" : ""}`)
        .addTo(map);
    });
    data.incidents.filter((i) => i.lat !== null).forEach((i) => {
      pts.push([i.lat!, i.lon!]);
      L.marker([i.lat!, i.lon!], {
        icon: L.divIcon({ className: "", html: `<span class="inc-pin" style="background:${SEVERITY[i.severity] || "#d03b3b"}">!</span>`, iconSize: [22, 22] }),
      })
        .bindPopup(`<strong>${text(i.number)}</strong><br>${text(i.date)} · ${text(i.severity_label)}<br>${text(i.status_label)}`)
        .addTo(map);
    });
    if (pts.length) map.fitBounds(L.latLngBounds(pts), { padding: [30, 30], maxZoom: 16 });
    else map.setView([-1.64, 29.17], 14);
    return () => {
      map.remove();
    };
  }, [data]);

  if (error) return <p className="error">{error}</p>;
  const noGps = data ? data.assets.filter((a) => a.lat === null && TYPE_STYLE[a.type]).map((a) => a.name) : [];
  const incNoGps = data ? data.incidents.filter((i) => i.lat === null).length : 0;
  return (
    <section className="card">
      <div className="legend">
        <span><i style={{ background: TYPE_STYLE.KIOSK.color }} /> Borne fontaine</span>
        <span><i style={{ background: TYPE_STYLE.PRIVATE_CONNECTION.color }} /> Connexion privée</span>
        <span><i style={{ background: TYPE_STYLE.RESERVOIR.color }} /> Réservoir</span>
        <span><i style={{ background: TYPE_STYLE.PUMP_STATION.color }} /> Station de pompage</span>
        <span><i className="sq" style={{ background: SEVERITY.CRITICAL }} /> Panne (6 derniers mois)</span>
      </div>
      <div ref={el} className="map" aria-label="Carte des actifs et des pannes" />
      {noGps.length > 0 && <p className="muted small">Sans coordonnées GPS (non affichés) : {noGps.join(", ")}.</p>}
      {incNoGps > 0 && <p className="muted small">{incNoGps} panne(s) sans position.</p>}
    </section>
  );
}
