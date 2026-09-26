"""Executable data-quality checks.

Each check reads the workbooks and returns a Finding with the evidence it
actually saw, or None if the defect is no longer present (e.g. someone fixed
the Excel). The audit table in docs/data-quality-report.md is built from these.
"""
import datetime as dt
import re
from dataclasses import dataclass, field

from openpyxl.utils import column_index_from_string as col_idx
from openpyxl.utils import get_column_letter as col_letter

from .xl import clean, is_formula


@dataclass
class Finding:
    code: str
    workbook: str
    sheet: str
    cells: str
    defect: str
    evidence: str
    severity: str  # Haute / Moyenne / Faible
    handling: str
    kpi_impact: bool = False
    extra: dict = field(default_factory=dict)


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def r(v):
    return repr(v) if not isinstance(v, str) else f"« {v[:90]}{'…' if len(v) > 90 else ''} »"


# ------------------------------------------------------------ Workbook 1

S1 = "1. Registre_Actifs_Prod&Stock"
S2 = "2. Registre_Actifs_Regul&tuy"
S3 = "3. Registre_Actifs_OrgRegu"
S4 = "4. Registre_Actifs_BF&Conn"


@check
def a01_no_asset_ids(wb):
    ws = wb.f("assets", S1)
    ids = [ws[f"B{i}"].value for i in range(4, 25) if ws[f"B{i}"].value]
    if len(ids) < 10:
        return Finding("A01", "assets", S1, "B3:B24", "« ID Actif » ne contient que des numéros de rubrique, pas d'identifiant par équipement",
                       f"Valeurs trouvées : {ids}", "Haute",
                       "Identifiants stables générés : <SITE>-<TYPE>-<NNN> (ex. GO-PMP-001), table de correspondance dans ce rapport.", True)


@check
def a02_node_110_collapsed(wb):
    ws = wb.f("assets", S2)
    c = ws["D19"]
    note = ws["N19"].value or ""
    if isinstance(c.value, float) and "1.10" in note:
        return Finding("A02", "assets", S2, "D19, C20, C21 ; aussi 3. OrgRegu!C14",
                       "Nœud « 1.10 » saisi comme nombre : la valeur stockée 1.1 se confond avec le nœud « 1.1 »",
                       f"D19 = {c.value!r} (format {c.number_format}), N19 = {r(note)}", "Haute",
                       "Identifiants de nœuds toujours en texte ; le format d'affichage (0.00 → « 1.10 ») est utilisé pour restituer le bon nœud.", True)


@check
def a03_segment_numbers(wb):
    ws = wb.f("assets", S2)
    nums = [ws[f"B{i}"].value for i in range(6, 37)]
    dup = sorted({n for n in nums if n is not None and nums.count(n) > 1})
    if dup:
        return Finding("A03", "assets", S2, "B6:B36", "Colonne « No. » des tronçons non unique",
                       f"Numéros en double : {dup}", "Moyenne", "Clé de tronçon = nœud amont > nœud aval # DN.")


@check
def a04_missing_from_nodes(wb):
    ws = wb.f("assets", S2)
    rows = [i for i in range(6, 37) if ws[f"D{i}"].value and not ws[f"C{i}"].value]
    if rows:
        return Finding("A04", "assets", S2, ", ".join(f"C{i}" for i in rows), "Nœud amont manquant pour des branchements de BF",
                       "; ".join(f"ligne {i} → {ws[f'D{i}'].value}" for i in rows), "Haute",
                       "Tronçon importé sans nœud amont et signalé ; à compléter sur le plan du réseau.")


@check
def a05_missing_lengths(wb):
    ws = wb.f("assets", S2)
    rows = [i for i in range(6, 37) if ws[f"C{i}"].value and not any(ws.cell(i, c).value for c in range(6, 13))]
    if rows:
        return Finding("A05", "assets", S2, ", ".join(f"F{i}:L{i}" for i in rows), "Tronçons sans longueur (dont la conduite de refoulement Bosco Lac)",
                       "; ".join(f"{ws[f'C{i}'].value} → {ws[f'D{i}'].value}" for i in rows), "Moyenne",
                       "Tronçon non importé (longueur obligatoire) ; nœuds créés.")


@check
def a06_dn_header_vs_comment(wb):
    ws = wb.f("assets", S2)
    if ws["H8"].value and "DN 150" in str(ws["N8"].value or ""):
        return Finding("A06", "assets", S2, "H5:I5 vs N8", "Diamètres de colonne (DN160/DN110) différents du commentaire (DN150/DN100)",
                       f"H5 = {r(ws['H5'].value)}, N8 = {r(ws['N8'].value)}", "Moyenne",
                       "DN de la colonne retenu, écart signalé sur le tronçon.")


@check
def a07_missing_material_state(wb):
    ws = wb.f("assets", S2)
    no_mat = [f"E{i}" for i in range(6, 37) if ws[f"C{i}"].value and not ws[f"E{i}"].value]
    no_state = all(not ws[f"M{i}"].value for i in range(6, 37))
    if no_mat or no_state:
        return Finding("A07", "assets", S2, ", ".join(no_mat) + ("; M6:M36" if no_state else ""),
                       "Matériau manquant sur certains tronçons ; colonne « Etat » vide pour tous",
                       f"Sans matériau : {no_mat}; état vide : {no_state}", "Moyenne", "État = « Inconnu » ; matériau vide conservé vide.")


@check
def a08_total_dn_rollup(wb):
    ws = wb.f("assets", S2)
    if ws["F37"].value is None and ws["G37"].value is None and is_formula(ws["H38"].value):
        return Finding("A08", "assets", S2, "F37:G37, H38", "Totaux par DN sans DN250/DN225",
                       f"H38 = {ws['H38'].value}", "Faible", "Longueurs totalisées par la base à partir des tronçons.")


@check
def a09_no_gps_production(wb):
    ws = wb.f("assets", S1)
    missing = [f"F{i}" for i in range(4, 22) if isinstance(ws[f"F{i}"].value, str) and "Long" in ws[f"F{i}"].value
               and not re.search(r"-?\d+\.\d+", ws[f"F{i}"].value)]
    if missing:
        return Finding("A09", "assets", S1, ", ".join(missing), "Coordonnées GPS non renseignées (modèle « Long:/Lat: » vide)",
                       f"{len(missing)} cellules", "Haute", "Actif importé sans position, signalé « GPS manquant ».")


@check
def a10_placeholder_rows(wb):
    ws = wb.f("assets", S1)
    cells = [f"D{i}" for i in range(4, 25) if isinstance(ws[f"D{i}"].value, str) and re.fullmatch(r"\d+\.\s*", ws[f"D{i}"].value)]
    if cells:
        return Finding("A10", "assets", S1, ", ".join(cells), "Lignes modèles numérotées sans actif", f"{len(cells)} lignes vides", "Faible", "Ignorées.")


@check
def a11_capacity_text(wb):
    ws = wb.f("assets", S1)
    if isinstance(ws["G4"].value, str):
        return Finding("A11", "assets", S1, "G4, G5, G9, G10, G18, G19", "Capacité et unité dans le même texte",
                       f"G4 = {r(ws['G4'].value)}", "Faible", "Découpées en valeur numérique + unité normalisée (m3/h, m3, L/h, L).")


@check
def a12_install_date_text(wb):
    ws = wb.f("assets", S1)
    if isinstance(ws["J9"].value, str):
        return Finding("A12", "assets", S1, "J9", "Date d'installation en texte (mois/année)", f"J9 = {r(ws['J9'].value)}", "Faible",
                       "Convertie au 1er du mois, signalée « précision mois ».")


@check
def a13_quantity_in_name(wb):
    ws = wb.f("assets", S1)
    if isinstance(ws["E5"].value, str) and ws["E5"].value.strip().startswith("2 "):
        return Finding("A13", "assets", S1, "E4, E5, E16, E18", "Quantité d'équipements dans le libellé (« 2 Groupe motopompe SHIMGE »)",
                       f"E5 = {r(ws['E5'].value)}", "Moyenne",
                       "Pompes et pompes doseuses : un actif par unité (2 × SHIMGE = GO-PMP-002 et GO-PMP-003). Autres équipements : quantité en attribut.", True)


@check
def a14_typo_chloration(wb):
    ws = wb.f("assets", S1)
    if "Choration" in str(ws["D14"].value):
        return Finding("A14", "assets", S1, "D14, D18", "Faute de frappe « Choration »", f"D14 = {r(ws['D14'].value)}", "Faible",
                       "Nom corrigé (« Chloration »), libellé d'origine conservé.")


@check
def a15_maintenance_fields_empty(wb):
    ws = wb.f("assets", S1)
    empty = all(not ws.cell(i, c).value for i in range(4, 25) for c in (col_idx("M"), col_idx("N"), col_idx("O")))
    if empty:
        return Finding("A15", "assets", S1, "M4:O24", "Fréquence / dernière / prochaine maintenance jamais renseignées",
                       "Toutes vides", "Moyenne", "Champs vides ; à compléter pour générer les ordres de maintenance préventive.")


@check
def a16_bf_cp_same_gps(wb):
    ws = wb.f("assets", S4)
    if ws["C14"].value == ws["C15"].value and ws["D14"].value == ws["D15"].value:
        return Finding("A16", "assets", S4, "C14:E15", "BF07 et CP1 ont exactement les mêmes coordonnées GPS",
                       f"({ws['D15'].value}, {ws['C15'].value})", "Haute", "Position de CP1 importée et signalée « à relever sur le terrain ».")


@check
def a17_bf_fields_empty(wb):
    ws = wb.f("assets", S4)
    if all(not ws[f"I{i}"].value and not ws[f"K{i}"].value for i in range(5, 16)):
        return Finding("A17", "assets", S4, "I5:I15, K5:K15, L5:L15", "Bénéficiaires, état et commentaires vides pour toutes les BF",
                       "11 lignes vides", "Moyenne", "État « Inconnu », bénéficiaires vides (jamais 0).")


@check
def a18_bf_id_format(wb):
    ws2 = wb.f("assets", S2)
    ws4 = wb.f("assets", S4)
    if ws2["D27"].value == "BF1" and ws4["B9"].value == "BF01":
        return Finding("A18", "assets", f"{S2} / {S4}", "D27:D36 vs B5:B14", "Format des identifiants BF différent (BF1 vs BF01)",
                       "BF1 … BF10 / BF01 … BF10", "Moyenne", "Normalisé en BF01 … BF10 (actif GO-BF-01 …).")


@check
def a19_orgregu_state_text(wb):
    ws = wb.f("assets", S3)
    if ws["E6"].value and "fuite" in str(ws["E6"].value):
        return Finding("A19", "assets", S3, "D6, E6", "Colonne « Etat » contient une description libre (fuite, remplacement)",
                       f"E6 = {r(ws['E6'].value)}", "Moyenne", "Nœud 1.1 marqué « Mauvais » avec la note d'origine.")


@check
def a20_node_15_missing(wb):
    ws = wb.f("assets", S3)
    codes = {str(ws[f"C{i}"].value) for i in range(6, 22)}
    if "1.5" not in codes:
        return Finding("A20", "assets", S3, "C6:C21", "Nœud 1.5 (ancienne connexion) absent du registre des organes ; nœuds 2.x absents",
                       "Séquence 1.4 → 1.6", "Faible", "Nœuds créés depuis la feuille tuyauterie, sans organes.")


# ------------------------------------------------------------ Workbook 2

F4 = "4. Fiche E&M_Rapp. Panne"


@check
def f01_free_text_assets(wb):
    ws = wb.f("forms", "1. Fiche journ_E&M_Pompage")
    if ws["B4"].value == "Nom de la station":
        return Finding("F01", "forms", "toutes les fiches", "1!B4, 2!B4, 3!B5, 4!B10/B13, 5!B4, 6!B4",
                       "Station, réservoir, zone, actif et nœud saisis en texte libre, sans code", f"B4 = {r(ws['B4'].value)}", "Haute",
                       "Dans l'application : listes déroulantes liées au registre (codes d'actif, de zone et de nœud).", True)


@check
def f02_units_missing(wb):
    ws = wb.f("forms", "1. Fiche journ_E&M_Pompage")
    if ws["B32"].value == "Qté chlore":
        return Finding("F02", "forms", "1, 2, 3", "1!B32, 2!B31, 1!F10:H10, 3!G22",
                       "Unités absentes (chlore, intensité, pression, débit, chlore résiduel)", f"B32 = {r(ws['B32'].value)}", "Haute",
                       "Unités imposées dans les formulaires : g, A, bar, m³/h, mg/L, NTU.", True)


@check
def f03_level_volume_or_pct(wb):
    ws = wb.f("forms", "2. Fiche journ_E&M_Stockage")
    if "volume ou %" in str(ws["C12"].value):
        return Finding("F03", "forms", "2. Fiche journ_E&M_Stockage", "C12", "Niveau du réservoir « volume ou % » : deux unités dans une colonne",
                       f"C12 = {r(ws['C12'].value)}", "Haute", "Deux champs : Niveau (%) et Niveau (m³).", True)


@check
def f04_no_volume_field(wb):
    ws = wb.f("forms", "1. Fiche journ_E&M_Pompage")
    headers = [ws.cell(10, c).value for c in range(2, 10)]
    if not any("Volume" in str(h) for h in headers):
        return Finding("F04", "forms", "1. Fiche journ_E&M_Pompage", "B10:I10",
                       "Pas de volume pompé ni de volume vendu sur les fiches : le rendement du réseau ne peut pas être calculé",
                       f"En-têtes : {headers}", "Haute",
                       "Champs ajoutés : Volume pompé (m³) par pompe (sinon débit × durée), Volume vendu (m³) par BF, volumes entrant/sortant par réservoir.", True)


@check
def f05_no_downtime(wb):
    ws = wb.f("forms", F4)
    labels = [ws.cell(i, 2).value for i in range(5, 30)]
    if not any("Durée" in str(v) for v in labels):
        return Finding("F05", "forms", F4, "B15, B23:B24", "Pas de durée d'arrêt ni de cause d'arrêt : la disponibilité ne peut pas être calculée",
                       "Seulement « Service interrompu ? » et heures début/fin d'intervention", "Haute",
                       "Champs ajoutés : cause de l'arrêt (4 catégories O&M KPI) et durée d'arrêt (h), calculée par défaut.", True)


@check
def f06_vocabularies(wb):
    return Finding("F06", "forms", "1-7", "1!C15:D15, 2!C18:D18, 4!C31, 6!C9",
                   "Vocabulaires différents pour la même notion (Bon/Mauvais, Oui/Non, Conforme ?)", "Constat de l'audit des en-têtes",
                   "Faible", "Deux listes contrôlées seulement (Bon/Mauvais, Oui/Non) ; conformité qualité calculée depuis les seuils.") \
        if wb.f("forms", F4)["C31"].value == "Conforme ?" else None


@check
def f07_ambiguous_heure(wb):
    ws = wb.f("forms", "1. Fiche journ_E&M_Pompage")
    if ws["F25"].value == "Heure":
        return Finding("F07", "forms", "1. Fiche journ_E&M_Pompage", "F25", "Colonne « Heure » ambiguë à côté de « Heure démarrage / arrêt »",
                       f"D25:F25 = {ws['D25'].value} / {ws['E25'].value} / {ws['F25'].value}", "Faible",
                       "Interprétée comme « Heure (relevé) » — à confirmer.")


@check
def f08_typos(wb):
    ws = wb.f("forms", F4)
    if ws["B2"].value and ws["B2"].value.startswith("Fomulaire"):
        return Finding("F08", "forms", "2, 3, 4, 7", "4!B2, 4!B43, 3!D22, 3!B3, 3!B9, 7!B10", "Fautes dans les libellés",
                       f"B2 = {r(ws['B2'].value)}", "Faible", "Libellés corrigés dans l'application (liste dans shared/forms.fr.json → typo_fixes).")


@check
def f09_no_validation(wb):
    n = sum(len(wb.f("forms", s).data_validations.dataValidation) for s in wb._load("forms", False).sheetnames)
    if n == 0:
        return Finding("F09", "forms", "toutes", "—", "Aucune liste de validation dans les 7 fiches", "0 règle de validation", "Moyenne",
                       "Validation côté téléphone et côté serveur (plages, champs obligatoires, listes).")


# ------------------------------------------------------------ Workbook 3 & 4

@check
def s01_placeholder_quantities(wb):
    ws1 = wb.f("stock", "1. Eq &outil pour amél la perf.")
    ws2 = wb.f("stock", "2. Outils & Mats pour O&M")
    rows = [(ws1["E11"].value, ws1["F11"].value, ws1["G11"].value, ws1["I11"].value),
            (ws2["G5"].value, ws2["H5"].value, ws2["I5"].value, ws2["K5"].value),
            (ws2["G10"].value, ws2["H10"].value, ws2["I10"].value, ws2["K10"].value),
            (ws2["G15"].value, ws2["H15"].value, ws2["I15"].value, ws2["K15"].value)]
    if len(set(rows)) == 1:
        return Finding("S01", "stock", "1. Eq… / 2. Outils…", "E5:I19, G5:K15, E5:I5 (chimiques)",
                       "Même motif de quantités (stock 3, sortie 1, entrée 2, besoin 2) sur des articles sans rapport : valeurs de test",
                       f"Motif répété : {rows[0]}", "Haute",
                       "Articles importés sans quantité (aucun mouvement de stock créé). Valeurs d'origine listées plus bas.", True)


@check
def s02_ledger_logic(wb):
    ws = wb.f("stock", "1. Eq &outil pour amél la perf.")
    if ws["H5"].value == "=(E5-F5)+G5":
        return Finding("S02", "stock", "1, 2, 3", "H5, H11, H19, J5…, H5 (chimiques)", "Stock restant tapé par formule, sans journal des mouvements",
                       "« Restant = (Stock − Sortie) + Entrée » ; aucune date, aucune référence d'intervention", "Moyenne",
                       "Remplacé par un grand livre de mouvements (entrée, sortie, ajustement) ; solde = somme des mouvements.", True)


@check
def s03_no_link_to_incidents(wb):
    return Finding("S03", "stock", "tous", "—", "Aucun lien entre les pièces remplacées (rapport de panne) et le stock",
                   "Pas de colonne de référence d'intervention", "Haute",
                   "Les pièces saisies dans un rapport de panne créent une sortie de stock liée à l'incident.", True)


@check
def s04_empty_categories(wb):
    ws = wb.f("stock", "2. Outils & Mats pour O&M")
    if all(ws[f"G{i}"].value is None for i in range(29, 45)):
        return Finding("S04", "stock", "2. Outils & Mats pour O&M", "D29:K44", "EPI et logistique : noms sans unité ni quantité ; colonne « Location » vide",
                       "16 lignes sans quantité", "Moyenne", "Articles créés (catalogue) sans quantité.")


@check
def s05_monthly_requirement(wb):
    ws = wb.f("stock", "3. Produit chim trait de l'eau")
    if ws["C5"].value is None:
        return Finding("S05", "stock", "3. Produit chim trait de l'eau", "C5:C7", "Besoin mensuel en chlore non renseigné", "C5 vide", "Moyenne",
                       "Champ « besoin mensuel » vide : le seuil d'alerte du chlore est à définir.")


@check
def p01_duplicate_title(wb):
    ws = wb.f("staff", "1. Pers tech perm")
    if ws["D9"].value == ws["D10"].value:
        return Finding("P01", "staff", "1. Pers tech perm", "D9, D10", "Deux postes « Technicien 4 » (stockages et pompage)",
                       f"D9 = D10 = {r(ws['D9'].value)}", "Moyenne", "Importés comme deux postes distincts (rôles différents).")


@check
def p02_missing_names(wb):
    ws = wb.f("staff", "1. Pers tech perm")
    missing = [f"C{i}" for i in range(4, 13) if not ws[f"C{i}"].value]
    if missing:
        return Finding("P02", "staff", "1. Pers tech perm", ", ".join(missing), "Noms du personnel manquants", f"{len(missing)} postes sur 9",
                       "Moyenne", "Postes importés « nom à compléter » ; aucun compte de connexion créé automatiquement.")


@check
def p03_duration_unit(wb):
    ws = wb.f("staff", "2. Pers tech non perm")
    if ws["H6"].value == "=G6+F6" and "mensuelle" in str(ws["E6"].value):
        return Finding("P03", "staff", "2 et 3", "F4:H7, G4:I8", "Unité de durée non précisée (Fin = Début + Durée en jours)",
                       f"E6 = {r(ws['E6'].value)}, durée {ws['F6'].value}", "Moyenne", "Importée en jours, signalée « unité à confirmer ».")


@check
def p04_needs_copy(wb):
    a = wb.f("staff", "2. Pers tech non perm")
    b = wb.f("staff", "3. Besoin en personnel")
    if [a[f"F{i}"].value for i in range(4, 8)] == [b[f"G{i}"].value for i in range(4, 8)]:
        return Finding("P04", "staff", "3. Besoin en personnel", "C4:I8", "Besoins en personnel identiques aux prestataires existants ; nombre et P/NP vides",
                       "Mêmes titres, durées et dates", "Moyenne", "Importés comme besoins signalés « à confirmer » ; ligne 8 sans titre ignorée.")


# ------------------------------------------------------------ Workbook 5

KPI = "O&M KPI"
SUM = "O&M Summary"


@check
def k01_e10(wb):
    ws = wb.f("kpi", KPI)
    if ws["E10"].value == "=744-D9":
        v = wb.v("kpi", KPI)
        return Finding("K01", "kpi", KPI, "E10", "Heures de fonctionnement de mars calculées avec l'arrêt de février",
                       f"E10 = {ws['E10'].value} (au lieu de =744-E9) ; C11 affiché = {v['C11'].value:.4f}", "Haute",
                       "Disponibilité recalculée par mois : (heures du mois − arrêts du mois) / heures du mois.", True)


@check
def k02_c11_fixed_range(wb):
    ws = wb.f("kpi", KPI)
    if "744+672" in str(ws["C11"].value):
        return Finding("K02", "kpi", KPI, "C11", "Disponibilité annuelle figée sur janvier–juin", f"C11 = {ws['C11'].value}", "Moyenne",
                       "Disponibilité annuelle = somme des heures de fonctionnement / somme des heures des mois disposant de données.", True)


@check
def k03_repaired_hardcoded(wb):
    ws = wb.f("kpi", KPI)
    if ws["C15"].value == "=50":
        v = wb.v("kpi", KPI)
        return Finding("K03", "kpi", KPI, "C15:C16", "Nombre de pannes réparées saisi en dur (50)",
                       f"C15 = {ws['C15'].value} ; C16 = {v['C16'].value:.4f}", "Haute",
                       "Taux de réparation = incidents clôturés / incidents signalés, depuis le registre des pannes. Non importé.", True)


@check
def k04_done_minus_five(wb):
    ws = wb.f("kpi", KPI)
    if ws["C56"].value == "=C55-5":
        return Finding("K04", "kpi", KPI, "C56:N56", "Maintenances réalisées = prévues − 5 (formule fictive)",
                       f"C56 = {ws['C56'].value}", "Haute",
                       "Réalisées = ordres de travail préventifs clôturés. Historique « réalisées » non importé.", True)


@check
def k05_fuel_175(wb):
    ws = wb.f("kpi", KPI)
    if "/175+30" in str(ws["C62"].value):
        return Finding("K05", "kpi", KPI, "C62:N62, C66:N66, C68:N68",
                       "Intensité carburant et coûts au m³ faux : « /175+30 » et « +175+30 » au lieu de diviser par le volume",
                       f"C62 = {ws['C62'].value}, C66 = {ws['C66'].value}, C68 = {ws['C68'].value}", "Haute",
                       "L/m³ = litres / m³ pompés ; USD/m³ = coût / m³ pompés.", True)


@check
def k06_july_one_day(wb):
    ws = wb.f("kpi", KPI)
    s = wb.f("kpi", SUM)
    if ws["I30"].value == "='O&M Summary'!C4" and s["C4"].value == "=POMPES!E4+POMPES!E5":
        return Finding("K06", "kpi", f"{KPI} / {SUM}", "KPI!I30, I59, I61 ; Summary!C4, H4, I4, K4",
                       "Totaux de juillet = une seule journée (9 juillet)",
                       f"Summary!C4 = {s['C4'].value}, H4 = {s['H4'].value}, I4 = {s['I4'].value}", "Haute",
                       "Totaux mensuels = somme de tous les relevés journaliers du mois.", True)


@check
def k07_b4_blocks(wb):
    s = wb.f("kpi", SUM)
    f = str(s["B4"].value)
    if f.count("POMPES!DX8") >= 2 or "POMPES!BW8" in f:
        p = wb.f("kpi", "POMPES")
        return Finding("K07", "kpi", SUM, "B4", "Somme des heures de fonctionnement : DX8 compté deux fois, BW8 (pression) au lieu de BV8",
                       f"BW3 = {r(p['BW3'].value)}, DX3 = {r(p['DX3'].value)}", "Haute", "Heures = somme des relevés par pompe et par jour.", True)


@check
def k08_august_refs(wb):
    s = wb.f("kpi", SUM)
    if s["O4"].value == "=POMPES!O4+POMPES!O5":
        p = wb.f("kpi", "POMPES")
        return Finding("K08", "kpi", SUM, "O4:X4", "Colonnes d'août pointant vers des colonnes de juillet (mauvais jour et mauvaise mesure)",
                       f"O4 = {s['O4'].value} ; POMPES!O3 = {r(p['O3'].value)}, août commence en {_first_col_for(p, dt.date(2026, 8, 1))}",
                       "Critique", "Plus aucune référence de cellule : agrégation par date.", True)


def _first_col_for(ws, day):
    for c in range(2, ws.max_column + 1):
        v = ws.cell(2, c).value
        if isinstance(v, dt.datetime) and v.date() == day:
            return col_letter(c)
    return "?"


@check
def k09_nrw_unlinked(wb):
    s = wb.f("kpi", SUM)
    if s["F4"].value is None and s["G4"].value == "=C4-F4":
        return Finding("K09", "kpi", SUM, "D4:G4", "Volume facturé non relié : eau non facturée = 100 % du volume pompé",
                       f"F4 vide, G4 = {s['G4'].value}", "Haute",
                       "Eau non facturée calculée seulement si le volume vendu est connu ; sinon « pas de donnée ».", True)


@check
def k10_future_values(wb):
    ws = wb.f("kpi", KPI)
    vals = [ws.cell(30, c).value for c in range(col_idx("L"), col_idx("N") + 1)]
    if all(isinstance(v, (int, float)) for v in vals):
        return Finding("K10", "kpi", KPI, "K:N (septembre–décembre)", "Valeurs saisies pour des mois non écoulés (données de test mêlées aux réelles)",
                       f"Eau introduite oct.–déc. = {vals}", "Haute",
                       "Mois futurs non importés ; juillet–septembre importés « provisoires » (affichés, jamais utilisés dans les KPI).", True)


@check
def k11_nrw_c33_only(wb):
    ws = wb.f("kpi", KPI)
    if ws["C33"].value == "=C30-C31" and ws["D33"].value is None:
        return Finding("K11", "kpi", KPI, "C33:N33", "Eau non facturée calculée pour janvier seulement", "D33:N33 vides", "Moyenne",
                       "Calculée pour chaque mois.", True)


@check
def k12_quality_empty(wb):
    ws = wb.f("kpi", KPI)
    if all(ws.cell(r_, c).value is None for r_ in range(82, 89) for c in range(3, 15)):
        return Finding("K12", "kpi", KPI, "B81:N88", "Section qualité de l'eau vide (aucune donnée, aucune formule)", "Toutes cellules vides",
                       "Moyenne", "Conformité = mesures conformes / mesures, depuis les fiches et tests laboratoire.", True)


@check
def k13_support_excluded(wb):
    ws = wb.f("kpi", KPI)
    if ws["C75"].value == "=SUM(C71:C73)":
        return Finding("K13", "kpi", KPI, "C75:N75", "« Total Dépense réelle » omet les autres activités de support (ligne 74)",
                       f"C75 = {ws['C75'].value}", "Faible", "Total = urgente + corrective + préventive + support.", True)


@check
def k14_arithmetic_budget(wb):
    ws = wb.f("kpi", KPI)
    vals = [ws.cell(70, c).value for c in range(3, 15)]
    diffs = {vals[i + 1] - vals[i] for i in range(5)}
    if len(diffs) == 1:
        return Finding("K14", "kpi", KPI, "C70:N70", "Budget prévu en progression arithmétique parfaite (+502 puis −403 par mois)",
                       f"{vals}", "Moyenne", "Importé comme budget mensuel « à confirmer ».")


@check
def k15_pompes_f8(wb):
    p = wb.f("kpi", "POMPES")
    if not is_formula(p["F8"].value):
        return Finding("K15", "kpi", "POMPES", "F8", "Total électricité tapé en dur au lieu d'une formule", f"F8 = {p['F8'].value}", "Faible",
                       "Totaux recalculés depuis les lignes.")


@check
def k16_stockage_total(wb):
    s = wb.f("kpi", "STOCKAGE")
    if s["B7"].value == "=SUM(B3:B6)":
        return Finding("K16", "kpi", "STOCKAGE", "B7:EI7", "Totaux incluant la ligne d'en-tête", f"B7 = {s['B7'].value}", "Faible",
                       "Totaux recalculés depuis les lignes de données.")


@check
def k17_only_one_day(wb):
    p = wb.v("kpi", "POMPES")
    filled = sorted({p.cell(2, ((c - 2) // 8) * 8 + 2).value.date().isoformat() for c in range(2, p.max_column + 1)
                     for r_ in (4, 5) if p.cell(r_, c).value not in (None, "") and isinstance(p.cell(2, ((c - 2) // 8) * 8 + 2).value, dt.datetime)})
    if len(filled) <= 1:
        return Finding("K17", "kpi", "POMPES / STOCKAGE", "J2:KC8 ; H2:EI7", "Une seule journée renseignée (9 juillet) sur 36 et 23 jours préparés",
                       f"Jours avec données : {filled}", "Info", "Seul le 9 juillet est importé en relevés journaliers.", True)


@check
def k18_pompes_row5_label(wb):
    p = wb.f("kpi", "POMPES")
    if "CAPRARI" in str(p["A5"].value) and p["D5"].value == 90:
        return Finding("K18", "kpi", "POMPES", "A5, D5", "Ligne 5 libellée « CAPRARI 183 m³/h » mais débit 90 m³/h (= pompe SHIMGE)",
                       f"A5 = {r(p['A5'].value)}, D5 = {p['D5'].value}", "Moyenne",
                       "Relevé rattaché à GO-PMP-002 (SHIMGE n°1), signalé « à confirmer ».", True)


@check
def k19_reseau_autofill(wb):
    ws = wb.v("kpi", "RESEAU")
    pressures = [ws.cell(4, c).value for c in range(2, 2 + 7 * 10, 7)]
    if pressures == list(range(pressures[0], pressures[0] + 10)) if isinstance(pressures[0], int) else False:
        return Finding("K19", "kpi", "RESEAU", "B4:NK5", "53 jours × 2 zones remplis par recopie incrémentale (pression +1/jour, pannes 1, 2, 3 …)",
                       f"Pression zone 1, 10 premiers jours : {pressures}", "Haute", "Feuille non importée (données de test).", True)


@check
def k20_reseau_cause_value(wb):
    ws = wb.v("kpi", "RESEAU")
    if ws["E4"].value == "Vole ":
        return Finding("K20", "kpi", "RESEAU", "E4, L4 …", "Cause « Vole  » hors de la liste autorisée (A32:A36)", f"E4 = {r(ws['E4'].value)}",
                       "Faible", "Liste de causes unique (11 causes) dans l'application.")


@check
def k21_ref_error(wb):
    ws = wb.f("kpi", "Plan d'Action et Calendrier")
    if "#REF!" in str(ws["NH40"].value):
        return Finding("K21", "kpi", "Plan d'Action et Calendrier", "NH40", "Référence cassée", f"NH40 = {ws['NH40'].value}", "Haute",
                       "Tâche 3.3 sans description : non importée ; avancement non repris.")


@check
def k22_mudja(wb):
    ws = wb.f("kpi", "Plan d'Action et Calendrier")
    if "MUDJA" in str(ws["C22"].value):
        return Finding("K22", "kpi", "Plan d'Action et Calendrier", "C22, C25", "Réservoir « MUDJA 200m3 » absent du registre ; tâche copiée « … de Nyabyunyu »",
                       f"C22 = {r(ws['C22'].value)}, C25 = {r(ws['C25'].value)}", "Moyenne", "Tâches importées sans actif, signalées.")


@check
def k23_plan_title(wb):
    ws = wb.f("kpi", "Plan d'Action et Calendrier")
    if "MUGUNGA" in str(ws["C4"].value):
        return Finding("K23", "kpi", "Plan d'Action et Calendrier", "C4", "Titre « MUGUNGA-LAC VERT » alors que le classeur porte sur Goma Ouest",
                       f"C4 = {r(ws['C4'].value)}", "Faible", "Considéré comme le même réseau (Mugunga–Lac Vert = Goma Ouest) — à confirmer.")


@check
def k24_plan_missing_desc(wb):
    ws = wb.f("kpi", "Plan d'Action et Calendrier")
    rows = [i for i in range(9, 54) if ws[f"B{i}"].value and not ws[f"C{i}"].value and ws[f"D{i}"].value is not None
            or (ws[f"B{i}"].value and not ws[f"C{i}"].value and any(ws.cell(i, c).value for c in range(7, 20)))]
    if rows:
        return Finding("K24", "kpi", "Plan d'Action et Calendrier", ", ".join(f"C{i}" for i in rows),
                       "Tâches sans description (et dates tapées dans la colonne du 1er janvier)", f"{len(rows)} tâches, ex. G29 = {ws['G29'].value}",
                       "Moyenne", "Non importées ; listées ci-dessous.")


@check
def k25_budget_incomplete(wb):
    ws = wb.f("kpi", "Besoins et budget E&M_mensuel")
    costed = [i for i in range(5, 30) if ws[f"G{i}"].value is not None]
    if len(costed) <= 1:
        return Finding("K25", "kpi", "Besoins et budget E&M_mensuel", "F5:M29", "Une seule ligne chiffrée sur ~20 activités ; total 250 USD",
                       f"Lignes chiffrées : {costed}", "Moyenne", "Lignes importées ; celles sans quantité/prix signalées « non chiffrées ».")


def run_all(wb):
    findings, errors = [], []
    for fn in CHECKS:
        try:
            res = fn(wb)
        except Exception as exc:  # a broken check must not stop the import
            errors.append(f"{fn.__name__}: {exc}")
            continue
        if res:
            findings.append(res)
    return findings, errors


__all__ = ["Finding", "CHECKS", "run_all", "clean"]
