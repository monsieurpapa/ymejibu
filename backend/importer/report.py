"""Write docs/data-quality-report.md from the checks and the import log."""
import datetime as dt

from .xl import SHORT

SEVERITY_ORDER = {"Critique": 0, "Haute": 1, "Moyenne": 2, "Faible": 3, "Info": 4}


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def build(wb, findings, check_errors, log, site, today):
    lines = []
    w = lines.append
    w("# Rapport qualité des données — migration Excel → plateforme E&M")
    w("")
    w(f"Généré automatiquement par `python manage.py import_excel` le {today:%d/%m/%Y}. Ne pas modifier à la main : relancer l'import.")
    w("")
    w(f"Site : **{site.code} — {site.name}**. Les classeurs sources sont ouverts en lecture seule et ne sont jamais modifiés.")
    w("")
    w("| Clé | Fichier |")
    w("|---|---|")
    for key, name in SHORT.items():
        w(f"| {name} | `{wb.name(key)}` |")
    w("")
    w("## 1. Synthèse")
    w("")
    by_sev = {}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
    w("| Gravité | Constats |")
    w("|---|---|")
    for sev in sorted(by_sev, key=lambda s: SEVERITY_ORDER.get(s, 9)):
        w(f"| {sev} | {by_sev[sev]} |")
    w(f"| **Total** | **{len(findings)}** |")
    w("")
    w(f"{sum(1 for f in findings if f.kpi_impact)} constats faussaient directement un indicateur (colonne « KPI »). "
      "Chacun est couvert par un test de non-régression (`backend/tests/test_excel_defects.py`).")
    w("")
    if check_errors:
        w("> Contrôles en erreur (à examiner) : " + "; ".join(check_errors))
        w("")
    w("## 2. Constats (preuve lue dans le fichier à chaque import)")
    w("")
    w("| Code | Classeur | Feuille | Cellule(s) | Anomalie | Preuve | Gravité | KPI | Traitement à l'import |")
    w("|---|---|---|---|---|---|---|---|---|")
    for f in sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.code)):
        w(f"| {f.code} | {SHORT.get(f.workbook, f.workbook).split(' (')[0]} | {esc(f.sheet)} | {esc(f.cells)} | {esc(f.defect)} | "
          f"{esc(f.evidence)} | {f.severity} | {'oui' if f.kpi_impact else ''} | {esc(f.handling)} |")
    w("")
    w("## 3. Ce que l'import a fait")
    w("")
    w("| Élément | Nombre |")
    w("|---|---|")
    for k, v in sorted(log.counts.items()):
        w(f"| {k} | {v} |")
    w("")
    for n in log.notes:
        w(f"- {n}")
    w("")
    w("### 3.1 Correspondance des identifiants d'actifs")
    w("")
    w("| Libellé Excel | Source | Nouvel identifiant |")
    w("|---|---|---|")
    for raw, ref, code in log.mapping:
        w(f"| {esc(raw)} | `{esc(ref.split('!', 1)[1])}` | **{code}** |")
    w("")
    w(f"### 3.2 Lignes non importées ({len(log.skipped)})")
    w("")
    w("| Source | Raison |")
    w("|---|---|")
    for ref, reason in log.skipped:
        w(f"| `{esc(ref.split('!', 1)[1] if '!' in ref else ref)}` | {esc(reason)} |")
    w("")
    w(f"### 3.3 Lignes importées avec un signalement ({len(log.flagged)})")
    w("")
    w("| Source | Élément | Codes |")
    w("|---|---|---|")
    for ref, what, codes in log.flagged:
        w(f"| `{esc(ref.split('!', 1)[1] if '!' in ref else ref)}` | {esc(what)} | {codes} |")
    w("")
    w("## 4. À confirmer par l'équipe")
    w("")
    w("- Les totaux mensuels de janvier à juin (feuille `O&M KPI`) sont-ils des chiffres réels ? Ils sont utilisés comme historique « validé ». "
      "Plusieurs séries ont des motifs réguliers (K10, K14) ; en cas de doute, relancer avec `--history-status provisional`.")
    w("- Seuils de chlore résiduel et de turbidité (valeurs par défaut marquées « à confirmer »).")
    w("- Affectation des nœuds, bornes fontaines et personnels aux zones (absente d'Excel).")
    w("- Coordonnées GPS manquantes (A09) et position de CP1 (A16).")
    w("- Réservoir « MUDJA 200 m³ » (K22) : à ajouter au registre ou à retirer du plan.")
    w("- Unité des durées de contrat (P03).")
    w("")
    return "\n".join(lines) + "\n"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
