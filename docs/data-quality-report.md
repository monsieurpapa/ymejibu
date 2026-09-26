# Rapport qualité des données — migration Excel → plateforme E&M

Généré automatiquement par `python manage.py import_excel` le 27/09/2026. Ne pas modifier à la main : relancer l'import.

Site : **GO — Goma Ouest**. Les classeurs sources sont ouverts en lecture seule et ne sont jamais modifiés.

| Clé | Fichier |
|---|---|
| Classeur 1 (Registre des actifs) | `1. ymejibu_E&M_Registre des Actifs_Goma Ouest_2026.xlsx` |
| Classeur 2 (Activités d'exploitation) | `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx` |
| Classeur 3 (Stock) | `3. ymejibu_E&M_Stock_Outils&Equip_Goma Ouest_2026.xlsx` |
| Classeur 4 (Personnel) | `4. ymejibu_E&M_Personnel_Goma Ouest_2026.xlsx` |
| Classeur 5 (Base KPI) | `5. ymejibu_E&M_Base de donnees KPI_2026.xlsx` |

## 1. Synthèse

| Gravité | Constats |
|---|---|
| Critique | 1 |
| Haute | 22 |
| Moyenne | 25 |
| Faible | 14 |
| Info | 1 |
| **Total** | **63** |

27 constats faussaient directement un indicateur (colonne « KPI »). Chacun est couvert par un test de non-régression (`backend/tests/test_excel_defects.py`).

## 2. Constats (preuve lue dans le fichier à chaque import)

| Code | Classeur | Feuille | Cellule(s) | Anomalie | Preuve | Gravité | KPI | Traitement à l'import |
|---|---|---|---|---|---|---|---|---|
| K08 | Classeur 5 | O&M Summary | O4:X4 | Colonnes d'août pointant vers des colonnes de juillet (mauvais jour et mauvaise mesure) | O4 = =POMPES!O4+POMPES!O5 ; POMPES!O3 = « Carburant (litre) », août commence en GD | Critique | oui | Plus aucune référence de cellule : agrégation par date. |
| A01 | Classeur 1 | 1. Registre_Actifs_Prod&Stock | B3:B24 | « ID Actif » ne contient que des numéros de rubrique, pas d'identifiant par équipement | Valeurs trouvées : ['I', 'II', 'III'] | Haute | oui | Identifiants stables générés : <SITE>-<TYPE>-<NNN> (ex. GO-PMP-001), table de correspondance dans ce rapport. |
| A02 | Classeur 1 | 2. Registre_Actifs_Regul&tuy | D19, C20, C21 ; aussi 3. OrgRegu!C14 | Nœud « 1.10 » saisi comme nombre : la valeur stockée 1.1 se confond avec le nœud « 1.1 » | D19 = 1.1 (format 0.00), N19 = « -Traversée sur route principale asphatée de 23.8m au Noeud 1.10 » | Haute | oui | Identifiants de nœuds toujours en texte ; le format d'affichage (0.00 → « 1.10 ») est utilisé pour restituer le bon nœud. |
| A04 | Classeur 1 | 2. Registre_Actifs_Regul&tuy | C35, C36 | Nœud amont manquant pour des branchements de BF | ligne 35 → BF7; ligne 36 → BF10 | Haute |  | Tronçon importé sans nœud amont et signalé ; à compléter sur le plan du réseau. |
| A09 | Classeur 1 | 1. Registre_Actifs_Prod&Stock | F4, F5, F10, F11, F14, F18 | Coordonnées GPS non renseignées (modèle « Long:/Lat: » vide) | 6 cellules | Haute |  | Actif importé sans position, signalé « GPS manquant ». |
| A16 | Classeur 1 | 4. Registre_Actifs_BF&Conn | C14:E15 | BF07 et CP1 ont exactement les mêmes coordonnées GPS | (-1.64192247493039, 29.1756970266623) | Haute |  | Position de CP1 importée et signalée « à relever sur le terrain ». |
| F01 | Classeur 2 | toutes les fiches | 1!B4, 2!B4, 3!B5, 4!B10/B13, 5!B4, 6!B4 | Station, réservoir, zone, actif et nœud saisis en texte libre, sans code | B4 = « Nom de la station » | Haute | oui | Dans l'application : listes déroulantes liées au registre (codes d'actif, de zone et de nœud). |
| F02 | Classeur 2 | 1, 2, 3 | 1!B32, 2!B31, 1!F10:H10, 3!G22 | Unités absentes (chlore, intensité, pression, débit, chlore résiduel) | B32 = « Qté chlore » | Haute | oui | Unités imposées dans les formulaires : g, A, bar, m³/h, mg/L, NTU. |
| F03 | Classeur 2 | 2. Fiche journ_E&M_Stockage | C12 | Niveau du réservoir « volume ou % » : deux unités dans une colonne | C12 = « Niveau du réservoir (volume ou %) » | Haute | oui | Deux champs : Niveau (%) et Niveau (m³). |
| F04 | Classeur 2 | 1. Fiche journ_E&M_Pompage | B10:I10 | Pas de volume pompé ni de volume vendu sur les fiches : le rendement du réseau ne peut pas être calculé | En-têtes : ['Heure', 'Pompe N°', 'Heure démarrage', 'Heure arrêt', 'Intensité', 'Pression', 'Débit', 'Observations'] | Haute | oui | Champs ajoutés : Volume pompé (m³) par pompe (sinon débit × durée), Volume vendu (m³) par BF, volumes entrant/sortant par réservoir. |
| F05 | Classeur 2 | 4. Fiche E&M_Rapp. Panne | B15, B23:B24 | Pas de durée d'arrêt ni de cause d'arrêt : la disponibilité ne peut pas être calculée | Seulement « Service interrompu ? » et heures début/fin d'intervention | Haute | oui | Champs ajoutés : cause de l'arrêt (4 catégories O&M KPI) et durée d'arrêt (h), calculée par défaut. |
| K01 | Classeur 5 | O&M KPI | E10 | Heures de fonctionnement de mars calculées avec l'arrêt de février | E10 = =744-D9 (au lieu de =744-E9) ; C11 affiché = 0.9705 | Haute | oui | Disponibilité recalculée par mois : (heures du mois − arrêts du mois) / heures du mois. |
| K03 | Classeur 5 | O&M KPI | C15:C16 | Nombre de pannes réparées saisi en dur (50) | C15 = =50 ; C16 = 0.3597 | Haute | oui | Taux de réparation = incidents clôturés / incidents signalés, depuis le registre des pannes. Non importé. |
| K04 | Classeur 5 | O&M KPI | C56:N56 | Maintenances réalisées = prévues − 5 (formule fictive) | C56 = =C55-5 | Haute | oui | Réalisées = ordres de travail préventifs clôturés. Historique « réalisées » non importé. |
| K05 | Classeur 5 | O&M KPI | C62:N62, C66:N66, C68:N68 | Intensité carburant et coûts au m³ faux : « /175+30 » et « +175+30 » au lieu de diviser par le volume | C62 = =C61/175+30, C66 = =C64/175+30, C68 = =C67/(C30+175+30) | Haute | oui | L/m³ = litres / m³ pompés ; USD/m³ = coût / m³ pompés. |
| K06 | Classeur 5 | O&M KPI / O&M Summary | KPI!I30, I59, I61 ; Summary!C4, H4, I4, K4 | Totaux de juillet = une seule journée (9 juillet) | Summary!C4 = =POMPES!E4+POMPES!E5, H4 = =POMPES!F4+POMPES!F5, I4 = =POMPES!G8 | Haute | oui | Totaux mensuels = somme de tous les relevés journaliers du mois. |
| K07 | Classeur 5 | O&M Summary | B4 | Somme des heures de fonctionnement : DX8 compté deux fois, BW8 (pression) au lieu de BV8 | BW3 = « Pression (bar) », DX3 = « chore résiduel (mg/l ou ppm) » | Haute | oui | Heures = somme des relevés par pompe et par jour. |
| K09 | Classeur 5 | O&M Summary | D4:G4 | Volume facturé non relié : eau non facturée = 100 % du volume pompé | F4 vide, G4 = =C4-F4 | Haute | oui | Eau non facturée calculée seulement si le volume vendu est connu ; sinon « pas de donnée ». |
| K10 | Classeur 5 | O&M KPI | K:N (septembre–décembre) | Valeurs saisies pour des mois non écoulés (données de test mêlées aux réelles) | Eau introduite oct.–déc. = [720, 740, 750] | Haute | oui | Mois futurs non importés ; juillet–septembre importés « provisoires » (affichés, jamais utilisés dans les KPI). |
| K19 | Classeur 5 | RESEAU | B4:NK5 | 53 jours × 2 zones remplis par recopie incrémentale (pression +1/jour, pannes 1, 2, 3 …) | Pression zone 1, 10 premiers jours : [3, 4, 5, 6, 7, 8, 9, 10, 11, 12] | Haute | oui | Feuille non importée (données de test). |
| K21 | Classeur 5 | Plan d'Action et Calendrier | NH40 | Référence cassée | NH40 = =#REF!*100 | Haute |  | Avancement de la tâche 3.3 laissé vide. |
| S01 | Classeur 3 | 1. Eq… / 2. Outils… | E5:I19, G5:K15, E5:I5 (chimiques) | Même motif de quantités (stock 3, sortie 1, entrée 2, besoin 2) sur des articles sans rapport : valeurs de test | Motif répété : (3, 1, 2, 2) | Haute | oui | Articles importés sans quantité (aucun mouvement de stock créé). Valeurs d'origine listées plus bas. |
| S03 | Classeur 3 | tous | — | Aucun lien entre les pièces remplacées (rapport de panne) et le stock | Pas de colonne de référence d'intervention | Haute | oui | Les pièces saisies dans un rapport de panne créent une sortie de stock liée à l'incident. |
| A03 | Classeur 1 | 2. Registre_Actifs_Regul&tuy | B6:B36 | Colonne « No. » des tronçons non unique | Numéros en double : [1, 2, 3] | Moyenne |  | Clé de tronçon = nœud amont > nœud aval # DN. |
| A05 | Classeur 1 | 2. Registre_Actifs_Regul&tuy | F6:L6, F7:L7 | Tronçons sans longueur (dont la conduite de refoulement Bosco Lac) | Bosco Lac → CV1 Pompage; Bosco Lac → SR | Moyenne |  | Tronçon non importé (longueur obligatoire) ; nœuds créés. |
| A06 | Classeur 1 | 2. Registre_Actifs_Regul&tuy | H5:I5 vs N8 | Diamètres de colonne (DN160/DN110) différents du commentaire (DN150/DN100) | H5 = « DN160 », N8 = « DN 150 SR(Sortie réservoir-nouvelle CV), DN 100 trop plein vidange, 1.1-ancienne CV » | Moyenne |  | DN de la colonne retenu, écart signalé sur le tronçon. |
| A07 | Classeur 1 | 2. Registre_Actifs_Regul&tuy | E6, E7, E20; M6:M36 | Matériau manquant sur certains tronçons ; colonne « Etat » vide pour tous | Sans matériau : ['E6', 'E7', 'E20']; état vide : True | Moyenne |  | État = « Inconnu » ; matériau vide conservé vide. |
| A13 | Classeur 1 | 1. Registre_Actifs_Prod&Stock | E4, E5, E16, E18 | Quantité d'équipements dans le libellé (« 2 Groupe motopompe SHIMGE ») | E5 = « 2 Groupe motopompe SHIMGE BLT 90 » | Moyenne | oui | Pompes et pompes doseuses : un actif par unité (2 × SHIMGE = GO-PMP-002 et GO-PMP-003). Autres équipements : quantité en attribut. |
| A15 | Classeur 1 | 1. Registre_Actifs_Prod&Stock | M4:O24 | Fréquence / dernière / prochaine maintenance jamais renseignées | Toutes vides | Moyenne |  | Champs vides ; à compléter pour générer les ordres de maintenance préventive. |
| A17 | Classeur 1 | 4. Registre_Actifs_BF&Conn | I5:I15, K5:K15, L5:L15 | Bénéficiaires, état et commentaires vides pour toutes les BF | 11 lignes vides | Moyenne |  | État « Inconnu », bénéficiaires vides (jamais 0). |
| A18 | Classeur 1 | 2. Registre_Actifs_Regul&tuy / 4. Registre_Actifs_BF&Conn | D27:D36 vs B5:B14 | Format des identifiants BF différent (BF1 vs BF01) | BF1 … BF10 / BF01 … BF10 | Moyenne |  | Normalisé en BF01 … BF10 (actif GO-BF-01 …). |
| A19 | Classeur 1 | 3. Registre_Actifs_OrgRegu | D6, E6 | Colonne « Etat » contient une description libre (fuite, remplacement) | E6 = « Vanne bridée en fonte ductile DN50 fuite - besoin de remplacement » | Moyenne |  | Nœud 1.1 marqué « Mauvais » avec la note d'origine. |
| F09 | Classeur 2 | toutes | — | Aucune liste de validation dans les 7 fiches | 0 règle de validation | Moyenne |  | Validation côté téléphone et côté serveur (plages, champs obligatoires, listes). |
| K02 | Classeur 5 | O&M KPI | C11 | Disponibilité annuelle figée sur janvier–juin | C11 = =SUM(C10:H10)/(744+672+744+720+744+720) | Moyenne | oui | Disponibilité annuelle = somme des heures de fonctionnement / somme des heures des mois disposant de données. |
| K11 | Classeur 5 | O&M KPI | C33:N33 | Eau non facturée calculée pour janvier seulement | D33:N33 vides | Moyenne | oui | Calculée pour chaque mois. |
| K12 | Classeur 5 | O&M KPI | B81:N88 | Section qualité de l'eau vide (aucune donnée, aucune formule) | Toutes cellules vides | Moyenne | oui | Conformité = mesures conformes / mesures, depuis les fiches et tests laboratoire. |
| K14 | Classeur 5 | O&M KPI | C70:N70 | Budget prévu en progression arithmétique parfaite (+502 puis −403 par mois) | [5580, 6082, 6584, 7086, 7588, 8090, 7687, 7284, 6881, 6478, 6075, 5672] | Moyenne |  | Importé comme budget mensuel « à confirmer ». |
| K18 | Classeur 5 | POMPES | A5, D5 | Ligne 5 libellée « CAPRARI 183 m³/h » mais débit 90 m³/h (= pompe SHIMGE) | A5 = « 2. Bosco Lac 183m3/hr Groupe motopompe CAPRARI », D5 = 90 | Moyenne | oui | Relevé rattaché à GO-PMP-002 (SHIMGE n°1), signalé « à confirmer ». |
| K22 | Classeur 5 | Plan d'Action et Calendrier | C22, C25 | Réservoir « MUDJA 200m3 » absent du registre ; tâche copiée « … de Nyabyunyu » | C22 = « MUDJA 200m3 », C25 = « Vidange et Nettoyage du stockage de Nyabyunyu » | Moyenne |  | Tâches importées sans actif, signalées. |
| K24 | Classeur 5 | Plan d'Action et Calendrier | C12, C13, C14, C29, C30, C31, C32, C33, C34, C35, C36, C38, C39, C40, C41, C42, C43, C44, C45, C48, C49, C50, C51, C52, C53 | Tâches sans description (et dates tapées dans la colonne du 1er janvier) | 25 tâches, ex. G29 = 2026-03-02 00:00:00 | Moyenne |  | Non importées ; listées ci-dessous. |
| K25 | Classeur 5 | Besoins et budget E&M_mensuel | F5:M29 | Une seule ligne chiffrée sur ~20 activités ; total 250 USD | Lignes chiffrées : [5] | Moyenne |  | Lignes importées ; celles sans quantité/prix signalées « non chiffrées ». |
| P01 | Classeur 4 | 1. Pers tech perm | D9, D10 | Deux postes « Technicien 4 » (stockages et pompage) | D9 = D10 = « Technicien 4 » | Moyenne |  | Importés comme deux postes distincts (rôles différents). |
| P02 | Classeur 4 | 1. Pers tech perm | C5, C6, C7, C8, C9, C10, C11, C12 | Noms du personnel manquants | 8 postes sur 9 | Moyenne |  | Postes importés « nom à compléter » ; aucun compte de connexion créé automatiquement. |
| P03 | Classeur 4 | 2 et 3 | F4:H7, G4:I8 | Unité de durée non précisée (Fin = Début + Durée en jours) | E6 = « Inspection mensuelle des pompes », durée 6 | Moyenne |  | Importée en jours, signalée « unité à confirmer ». |
| P04 | Classeur 4 | 3. Besoin en personnel | C4:I8 | Besoins en personnel identiques aux prestataires existants ; nombre et P/NP vides | Mêmes titres, durées et dates | Moyenne |  | Importés comme besoins signalés « à confirmer » ; ligne 8 sans titre ignorée. |
| S02 | Classeur 3 | 1, 2, 3 | H5, H11, H19, J5…, H5 (chimiques) | Stock restant tapé par formule, sans journal des mouvements | « Restant = (Stock − Sortie) + Entrée » ; aucune date, aucune référence d'intervention | Moyenne | oui | Remplacé par un grand livre de mouvements (entrée, sortie, ajustement) ; solde = somme des mouvements. |
| S04 | Classeur 3 | 2. Outils & Mats pour O&M | D29:K44 | EPI et logistique : noms sans unité ni quantité ; colonne « Location » vide | 16 lignes sans quantité | Moyenne |  | Articles créés (catalogue) sans quantité. |
| S05 | Classeur 3 | 3. Produit chim trait de l'eau | C5:C7 | Besoin mensuel en chlore non renseigné | C5 vide | Moyenne |  | Champ « besoin mensuel » vide : le seuil d'alerte du chlore est à définir. |
| A08 | Classeur 1 | 2. Registre_Actifs_Regul&tuy | F37:G37, H38 | Totaux par DN sans DN250/DN225 | H38 = =SUM(H37,I37,J37,K37,L37) | Faible |  | Longueurs totalisées par la base à partir des tronçons. |
| A10 | Classeur 1 | 1. Registre_Actifs_Prod&Stock | D7, D8, D12, D13, D22, D23, D24 | Lignes modèles numérotées sans actif | 7 lignes vides | Faible |  | Ignorées. |
| A11 | Classeur 1 | 1. Registre_Actifs_Prod&Stock | G4, G5, G9, G10, G18, G19 | Capacité et unité dans le même texte | G4 = « 183m3/hr » | Faible |  | Découpées en valeur numérique + unité normalisée (m3/h, m3, L/h, L). |
| A12 | Classeur 1 | 1. Registre_Actifs_Prod&Stock | J9 | Date d'installation en texte (mois/année) | J9 = « Septembre 2026 » | Faible |  | Convertie au 1er du mois, signalée « précision mois ». |
| A14 | Classeur 1 | 1. Registre_Actifs_Prod&Stock | D14, D18 | Faute de frappe « Choration » | D14 = « 1. Unité de Choration du pompage Bosco Lac » | Faible |  | Nom corrigé (« Chloration »), libellé d'origine conservé. |
| A20 | Classeur 1 | 3. Registre_Actifs_OrgRegu | C6:C21 | Nœud 1.5 (ancienne connexion) absent du registre des organes ; nœuds 2.x absents | Séquence 1.4 → 1.6 | Faible |  | Nœuds créés depuis la feuille tuyauterie, sans organes. |
| F06 | Classeur 2 | 1-7 | 1!C15:D15, 2!C18:D18, 4!C31, 6!C9 | Vocabulaires différents pour la même notion (Bon/Mauvais, Oui/Non, Conforme ?) | Constat de l'audit des en-têtes | Faible |  | Deux listes contrôlées seulement (Bon/Mauvais, Oui/Non) ; conformité qualité calculée depuis les seuils. |
| F07 | Classeur 2 | 1. Fiche journ_E&M_Pompage | F25 | Colonne « Heure » ambiguë à côté de « Heure démarrage / arrêt » | D25:F25 = Heure démarrage / Heure arrêt / Heure | Faible |  | Interprétée comme « Heure (relevé) » — à confirmer. |
| F08 | Classeur 2 | 2, 3, 4, 7 | 4!B2, 4!B43, 3!D22, 3!B3, 3!B9, 7!B10 | Fautes dans les libellés | B2 = « Fomulaire de rapport de panne » | Faible |  | Libellés corrigés dans l'application (liste dans shared/forms.fr.json → typo_fixes). |
| K13 | Classeur 5 | O&M KPI | C75:N75 | « Total Dépense réelle » omet les autres activités de support (ligne 74) | C75 = =SUM(C71:C73) | Faible | oui | Total = urgente + corrective + préventive + support. |
| K15 | Classeur 5 | POMPES | F8 | Total électricité tapé en dur au lieu d'une formule | F8 = 218 | Faible |  | Totaux recalculés depuis les lignes. |
| K16 | Classeur 5 | STOCKAGE | B7:EI7 | Totaux incluant la ligne d'en-tête | B7 = =SUM(B3:B6) | Faible |  | Totaux recalculés depuis les lignes de données. |
| K20 | Classeur 5 | RESEAU | E4, L4 … | Cause « Vole  » hors de la liste autorisée (A32:A36) | E4 = « Vole  » | Faible |  | Liste de causes unique (11 causes) dans l'application. |
| K23 | Classeur 5 | Plan d'Action et Calendrier | C4 | Titre « MUGUNGA-LAC VERT » alors que le classeur porte sur Goma Ouest | C4 = « PLANNING  ET PLAN D'ACTION ANNUELLE O&M MUGUNGA-LAC VERT » | Faible |  | Considéré comme le même réseau (Mugunga–Lac Vert = Goma Ouest) — à confirmer. |
| K17 | Classeur 5 | POMPES / STOCKAGE | J2:KC8 ; H2:EI7 | Une seule journée renseignée (9 juillet) sur 36 et 23 jours préparés | Jours avec données : ['2026-07-09'] | Info | oui | Seul le 9 juillet est importé en relevés journaliers. |

## 3. Ce que l'import a fait

| Élément | Nombre |
|---|---|
| assets | 32 |
| budget_lines | 16 |
| daily_readings | 4 |
| fittings | 71 |
| history_actual | 165 |
| history_provisional | 60 |
| monthly_budgets | 12 |
| nodes | 38 |
| people | 13 |
| pipe_segments | 31 |
| plan_tasks | 12 |
| quality_thresholds | 4 |
| staffing_needs | 4 |
| stock_items | 36 |
| tariffs | 2 |
| zones | 3 |

- Zones créées depuis le registre du personnel (« Point focal du réseau Zone N »). L'affectation des nœuds et des BF aux zones n'existe pas dans Excel : à compléter.
- Seuils de qualité : valeurs par défaut marquées « à confirmer » (la colonne « Valeur acceptable » des fiches est vide).
- Historique mensuel : mois avant 07/2026 = « validé » (à confirmer), de 07/2026 à aujourd'hui = « provisoire », mois futurs non importés.

### 3.1 Correspondance des identifiants d'actifs

| Libellé Excel | Source | Nouvel identifiant |
|---|---|---|
| 1. BOSCO LAC | `1. Registre_Actifs_Prod&Stock!D4` | **GO-STP-001** |
| 1 Groupe motopompe CAPRARI | `1. Registre_Actifs_Prod&Stock!E4` | **GO-PMP-001** |
| 2 Groupe motopompe SHIMGE BLT 90 | `1. Registre_Actifs_Prod&Stock!E5` | **GO-PMP-002** |
| 2 Groupe motopompe SHIMGE BLT 90 | `1. Registre_Actifs_Prod&Stock!E5` | **GO-PMP-003** |
| 2. BUHIMBA | `1. Registre_Actifs_Prod&Stock!D6` | **GO-STP-002** |
| 1. NYABYUNYU | `1. Registre_Actifs_Prod&Stock!D9` | **GO-STK-001** |
| Réservoir 1 nouveau | `1. Registre_Actifs_Prod&Stock!E9` | **GO-RES-001** |
| Réservoir 2 | `1. Registre_Actifs_Prod&Stock!E10` | **GO-RES-002** |
| 2. CAJED | `1. Registre_Actifs_Prod&Stock!D11` | **GO-STK-002** |
| Réservoir 2 | `1. Registre_Actifs_Prod&Stock!E11` | **GO-RES-003** |
| 1. Unité de Choration du pompage Bosco Lac | `1. Registre_Actifs_Prod&Stock!D14` | **GO-CHL-001** |
| pompe doeseuse | `1. Registre_Actifs_Prod&Stock!E14` | **GO-DOS-001** |
| Tank | `1. Registre_Actifs_Prod&Stock!E15` | **GO-TNK-001** |
| 4 Panneaux solaires | `1. Registre_Actifs_Prod&Stock!E16` | **GO-SOL-001** |
| Batterie | `1. Registre_Actifs_Prod&Stock!E17` | **GO-BAT-001** |
| 2. Unité de Choration du réservoir Nyabyunyu | `1. Registre_Actifs_Prod&Stock!D18` | **GO-CHL-002** |
| 2 pompes doeseuses | `1. Registre_Actifs_Prod&Stock!E18` | **GO-DOS-002** |
| 2 pompes doeseuses | `1. Registre_Actifs_Prod&Stock!E18` | **GO-DOS-003** |
| Tank | `1. Registre_Actifs_Prod&Stock!E19` | **GO-TNK-002** |
| Panneau solaire | `1. Registre_Actifs_Prod&Stock!E20` | **GO-SOL-002** |
| Batterie | `1. Registre_Actifs_Prod&Stock!E21` | **GO-BAT-002** |
| BF09 | `4. Registre_Actifs_BF&Conn!B5` | **GO-BF-09** |
| BF02 | `4. Registre_Actifs_BF&Conn!B6` | **GO-BF-02** |
| BF03 | `4. Registre_Actifs_BF&Conn!B7` | **GO-BF-03** |
| BF05 | `4. Registre_Actifs_BF&Conn!B8` | **GO-BF-05** |
| BF01 | `4. Registre_Actifs_BF&Conn!B9` | **GO-BF-01** |
| BF04 | `4. Registre_Actifs_BF&Conn!B10` | **GO-BF-04** |
| BF08 | `4. Registre_Actifs_BF&Conn!B11` | **GO-BF-08** |
| BF10 | `4. Registre_Actifs_BF&Conn!B12` | **GO-BF-10** |
| BF06 | `4. Registre_Actifs_BF&Conn!B13` | **GO-BF-06** |
| BF07 | `4. Registre_Actifs_BF&Conn!B14` | **GO-BF-07** |
| CP1 | `4. Registre_Actifs_BF&Conn!B15` | **GO-CP-001** |

### 3.2 Lignes non importées (103)

| Source | Raison |
|---|---|
| `1. Registre_Actifs_Prod&Stock!D7` | Ligne modèle « 3. » sans actif |
| `1. Registre_Actifs_Prod&Stock!D8` | Ligne modèle « 4. » sans actif |
| `1. Registre_Actifs_Prod&Stock!D12` | Ligne modèle « 3. » sans actif |
| `1. Registre_Actifs_Prod&Stock!D13` | Ligne modèle « 4. » sans actif |
| `1. Registre_Actifs_Prod&Stock!D22` | Ligne modèle « 3. » sans actif |
| `1. Registre_Actifs_Prod&Stock!D23` | Ligne modèle « 4. » sans actif |
| `1. Registre_Actifs_Prod&Stock!D24` | Ligne modèle « 5. » sans actif |
| `2. Registre_Actifs_Regul&tuy!B6` | Tronçon Bosco Lac → CV1 Pompage sans longueur |
| `2. Registre_Actifs_Regul&tuy!B7` | Tronçon Bosco Lac → SR sans longueur |
| `3. Besoin en personnel!B8` | Besoin sans titre (durée/date seules) |
| `O&M KPI!L13` | Mois futur (10/2026) — valeur 12 non importée |
| `O&M KPI!M13` | Mois futur (11/2026) — valeur 12 non importée |
| `O&M KPI!N13` | Mois futur (12/2026) — valeur 12 non importée |
| `O&M KPI!L18` | Mois futur (10/2026) — valeur 4 non importée |
| `O&M KPI!M18` | Mois futur (11/2026) — valeur 4 non importée |
| `O&M KPI!N18` | Mois futur (12/2026) — valeur 4 non importée |
| `O&M KPI!L19` | Mois futur (10/2026) — valeur 4 non importée |
| `O&M KPI!M19` | Mois futur (11/2026) — valeur 4 non importée |
| `O&M KPI!N19` | Mois futur (12/2026) — valeur 4 non importée |
| `O&M KPI!L20` | Mois futur (10/2026) — valeur 2 non importée |
| `O&M KPI!M20` | Mois futur (11/2026) — valeur 2 non importée |
| `O&M KPI!N20` | Mois futur (12/2026) — valeur 2 non importée |
| `O&M KPI!L21` | Mois futur (10/2026) — valeur 2 non importée |
| `O&M KPI!M21` | Mois futur (11/2026) — valeur 2 non importée |
| `O&M KPI!N21` | Mois futur (12/2026) — valeur 2 non importée |
| `O&M KPI!I30` | Formule ='O&M Summary'!C4 (valeur dérivée, non importée) |
| `O&M KPI!L30` | Mois futur (10/2026) — valeur 720 non importée |
| `O&M KPI!M30` | Mois futur (11/2026) — valeur 740 non importée |
| `O&M KPI!N30` | Mois futur (12/2026) — valeur 750 non importée |
| `O&M KPI!L31` | Mois futur (10/2026) — valeur 615 non importée |
| `O&M KPI!M31` | Mois futur (11/2026) — valeur 635 non importée |
| `O&M KPI!N31` | Mois futur (12/2026) — valeur 645 non importée |
| `O&M KPI!L36` | Mois futur (10/2026) — valeur 4 non importée |
| `O&M KPI!M36` | Mois futur (11/2026) — valeur 4 non importée |
| `O&M KPI!N36` | Mois futur (12/2026) — valeur 4 non importée |
| `O&M KPI!L37` | Mois futur (10/2026) — valeur 4 non importée |
| `O&M KPI!M37` | Mois futur (11/2026) — valeur 4 non importée |
| `O&M KPI!N37` | Mois futur (12/2026) — valeur 4 non importée |
| `O&M KPI!L38` | Mois futur (10/2026) — valeur 2 non importée |
| `O&M KPI!M38` | Mois futur (11/2026) — valeur 2 non importée |
| `O&M KPI!N38` | Mois futur (12/2026) — valeur 2 non importée |
| `O&M KPI!L39` | Mois futur (10/2026) — valeur 2 non importée |
| `O&M KPI!M39` | Mois futur (11/2026) — valeur 2 non importée |
| `O&M KPI!N39` | Mois futur (12/2026) — valeur 2 non importée |
| `O&M KPI!L50` | Mois futur (10/2026) — valeur 4 non importée |
| `O&M KPI!M50` | Mois futur (11/2026) — valeur 4 non importée |
| `O&M KPI!N50` | Mois futur (12/2026) — valeur 4 non importée |
| `O&M KPI!L51` | Mois futur (10/2026) — valeur 4 non importée |
| `O&M KPI!M51` | Mois futur (11/2026) — valeur 4 non importée |
| `O&M KPI!N51` | Mois futur (12/2026) — valeur 4 non importée |
| `O&M KPI!L52` | Mois futur (10/2026) — valeur 2 non importée |
| `O&M KPI!M52` | Mois futur (11/2026) — valeur 2 non importée |
| `O&M KPI!N52` | Mois futur (12/2026) — valeur 2 non importée |
| `O&M KPI!L53` | Mois futur (10/2026) — valeur 2 non importée |
| `O&M KPI!M53` | Mois futur (11/2026) — valeur 2 non importée |
| `O&M KPI!N53` | Mois futur (12/2026) — valeur 2 non importée |
| `O&M KPI!L54` | Mois futur (10/2026) — valeur 2 non importée |
| `O&M KPI!M54` | Mois futur (11/2026) — valeur 2 non importée |
| `O&M KPI!N54` | Mois futur (12/2026) — valeur 2 non importée |
| `O&M KPI!I59` | Formule =POMPES!F8 (valeur dérivée, non importée) |
| `O&M KPI!L59` | Mois futur (10/2026) — valeur 240 non importée |
| `O&M KPI!M59` | Mois futur (11/2026) — valeur 265 non importée |
| `O&M KPI!N59` | Mois futur (12/2026) — valeur 280 non importée |
| `O&M KPI!I61` | Formule =POMPES!G8 (valeur dérivée, non importée) |
| `O&M KPI!L61` | Mois futur (10/2026) — valeur 265 non importée |
| `O&M KPI!M61` | Mois futur (11/2026) — valeur 273 non importée |
| `O&M KPI!N61` | Mois futur (12/2026) — valeur 234 non importée |
| `O&M KPI!L71` | Mois futur (10/2026) — valeur 4087 non importée |
| `O&M KPI!M71` | Mois futur (11/2026) — valeur 3684 non importée |
| `O&M KPI!N71` | Mois futur (12/2026) — valeur 3281 non importée |
| `O&M KPI!L72` | Mois futur (10/2026) — valeur 3474 non importée |
| `O&M KPI!M72` | Mois futur (11/2026) — valeur 3071 non importée |
| `O&M KPI!N72` | Mois futur (12/2026) — valeur 2668 non importée |
| `O&M KPI!L73` | Mois futur (10/2026) — valeur 2455 non importée |
| `O&M KPI!M73` | Mois futur (11/2026) — valeur 2052 non importée |
| `O&M KPI!N73` | Mois futur (12/2026) — valeur 1649 non importée |
| `RESEAU!B4:NK5` | Feuille RESEAU : 106 lignes générées par recopie incrémentale (K19), non importées |
| `Plan d'Action et Calendrier!C12` | Tâche 1.4 sans description (durée None, date 1) |
| `Plan d'Action et Calendrier!C13` | Tâche 1.5 sans description (durée None, date 1) |
| `Plan d'Action et Calendrier!C14` | Tâche 1.6 sans description (durée None, date 1) |
| `Plan d'Action et Calendrier!C16` | En-tête de section « RESERVOIR » avec 1 jour(s) coché(s) par erreur |
| `Plan d'Action et Calendrier!C29` | Tâche 2.4 sans description (durée 24, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C30` | Tâche 2.5 sans description (durée 24, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C31` | Tâche 2.7 sans description (durée 24, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C32` | Tâche 2.8 sans description (durée 10, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C33` | Tâche 2.9 sans description (durée 7, date 2026-03-12 00:00:00) |
| `Plan d'Action et Calendrier!C34` | Tâche 2.11 sans description (durée 2, date 2026-05-24 00:00:00) |
| `Plan d'Action et Calendrier!C35` | Tâche 2.12 sans description (durée 22, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C36` | Tâche 2.13 sans description (durée 7, date 2026-03-12 00:00:00) |
| `Plan d'Action et Calendrier!C38` | Tâche 3.1 sans description (durée 64, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C39` | Tâche 3.2 sans description (durée 52, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C40` | Tâche 3.3 sans description (durée 40, date 2026-03-04 00:00:00) |
| `Plan d'Action et Calendrier!C41` | Tâche 3.4 sans description (durée 40, date 2026-03-11 00:00:00) |
| `Plan d'Action et Calendrier!C42` | Tâche 3.5 sans description (durée 40, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C43` | Tâche 3.6 sans description (durée 40, date 2026-03-04 00:00:00) |
| `Plan d'Action et Calendrier!C44` | Tâche 3.7 sans description (durée 40, date 2026-03-11 00:00:00) |
| `Plan d'Action et Calendrier!C45` | Tâche 3.8 sans description (durée 40, date 2026-03-02 00:00:00) |
| `Plan d'Action et Calendrier!C48` | Tâche 4.2 sans description (durée 30, date None) |
| `Plan d'Action et Calendrier!C49` | Tâche 4.3 sans description (durée 30, date None) |
| `Plan d'Action et Calendrier!C50` | Tâche 4.4 sans description (durée 30, date None) |
| `Plan d'Action et Calendrier!C51` | Tâche 4.5 sans description (durée 30, date None) |
| `Plan d'Action et Calendrier!C52` | Tâche 4.6 sans description (durée 14, date None) |
| `Plan d'Action et Calendrier!C53` | Tâche 5.1 sans description (durée 42, date None) |

### 3.3 Lignes importées avec un signalement (49)

| Source | Élément | Codes |
|---|---|---|
| `1. Registre_Actifs_Prod&Stock!E4` | GO-PMP-001 | A09 |
| `1. Registre_Actifs_Prod&Stock!E5` | GO-PMP-002 | A09, A13 |
| `1. Registre_Actifs_Prod&Stock!E5` | GO-PMP-003 | A09, A13 |
| `1. Registre_Actifs_Prod&Stock!D6` | GO-STP-002 | incomplet |
| `1. Registre_Actifs_Prod&Stock!E9` | GO-RES-001 | A12 |
| `1. Registre_Actifs_Prod&Stock!E10` | GO-RES-002 | A09 |
| `1. Registre_Actifs_Prod&Stock!E11` | GO-RES-003 | A09 |
| `1. Registre_Actifs_Prod&Stock!D14` | GO-CHL-001 | A14 |
| `1. Registre_Actifs_Prod&Stock!E14` | GO-DOS-001 | A09 |
| `1. Registre_Actifs_Prod&Stock!E15` | GO-TNK-001 | A09 |
| `1. Registre_Actifs_Prod&Stock!E16` | GO-SOL-001 | A09, A13 |
| `1. Registre_Actifs_Prod&Stock!E17` | GO-BAT-001 | A09 |
| `1. Registre_Actifs_Prod&Stock!D18` | GO-CHL-002 | A14 |
| `1. Registre_Actifs_Prod&Stock!E18` | GO-DOS-002 | A09, A13 |
| `1. Registre_Actifs_Prod&Stock!E18` | GO-DOS-003 | A09, A13 |
| `1. Registre_Actifs_Prod&Stock!E19` | GO-TNK-002 | A09 |
| `1. Registre_Actifs_Prod&Stock!E20` | GO-SOL-002 | A09 |
| `1. Registre_Actifs_Prod&Stock!E21` | GO-BAT-002 | A09 |
| `4. Registre_Actifs_BF&Conn!B5` | GO-BF-09 | A17 |
| `4. Registre_Actifs_BF&Conn!B6` | GO-BF-02 | A17 |
| `4. Registre_Actifs_BF&Conn!B7` | GO-BF-03 | A17 |
| `4. Registre_Actifs_BF&Conn!B8` | GO-BF-05 | A17 |
| `4. Registre_Actifs_BF&Conn!B9` | GO-BF-01 | A17 |
| `4. Registre_Actifs_BF&Conn!B10` | GO-BF-04 | A17 |
| `4. Registre_Actifs_BF&Conn!B11` | GO-BF-08 | A17 |
| `4. Registre_Actifs_BF&Conn!B12` | GO-BF-10 | A17 |
| `4. Registre_Actifs_BF&Conn!B13` | GO-BF-06 | A17 |
| `4. Registre_Actifs_BF&Conn!B14` | GO-BF-07 | A17 |
| `4. Registre_Actifs_BF&Conn!B15` | GO-CP-001 | A16, A17 |
| `2. Registre_Actifs_Regul&tuy!B8` | SR>1.1#DN160 | A06 |
| `2. Registre_Actifs_Regul&tuy!B8` | SR>1.1#DN110 | A06 |
| `2. Registre_Actifs_Regul&tuy!B9` | 1.1>1.2#DN160 | A06 |
| `2. Registre_Actifs_Regul&tuy!B9` | 1.1>1.2#DN110 | A06 |
| `2. Registre_Actifs_Regul&tuy!B14` | 1.4>1.5#DN160 | A06 |
| `2. Registre_Actifs_Regul&tuy!B20` | 1.10>1.16#DN160 | A07 |
| `2. Registre_Actifs_Regul&tuy!B35` | ?>BF07#DN50 | A04 |
| `2. Registre_Actifs_Regul&tuy!B36` | ?>BF10#DN50 | A04 |
| `1. Eq &outil pour amél la perf.!C5` | ART-001 Tuyaux PEHD DN 110 — quantités d'origine non importées : {'stock': 3000, 'sortie': 1000, 'entree': 2000, 'restant': '=(E5-F5)+G5', 'besoin': 2000} | S01 |
| `1. Eq &outil pour amél la perf.!C11` | ART-003 Compteur bridé DN110 en fonte ductile PN10 — quantités d'origine non importées : {'stock': 3, 'sortie': 1, 'entree': 2, 'restant': '=(E11-F11)+G11', 'besoin': 2} | S01 |
| `1. Eq &outil pour amél la perf.!C19` | ART-008 Compteur d'eau volumétrique à jet multiple DN 1' — quantités d'origine non importées : {'stock': 2, 'sortie': 1, 'entree': 2, 'restant': '=(E19-F19)+G19', 'besoin': 2} | S01 |
| `2. Outils & Mats pour O&M!D5` | ART-011 Kit de filletage — quantités d'origine non importées : {'stock': 3, 'sortie': 1, 'entree': 2, 'restant': '=(G5-H5)+I5', 'besoin': 2} | S01 |
| `2. Outils & Mats pour O&M!D10` | ART-013 Machine à fusion digitale DN 63 à 300 — quantités d'origine non importées : {'stock': 3, 'sortie': 1, 'entree': 2, 'restant': '=(G10-H10)+I10', 'besoin': 2} | S01 |
| `2. Outils & Mats pour O&M!D15` | ART-014 Marteau piqueur sans compresseur — quantités d'origine non importées : {'stock': 3, 'sortie': 1, 'entree': 2, 'restant': '=(G15-H15)+I15', 'besoin': 2} | S01 |
| `3. Produit chim trait de l'eau!B5` | ART-034 Chlore — quantités d'origine non importées : {'stock': 30, 'sortie': 10, 'entree': 20, 'restant': '=(E5-F5)+G5', 'besoin': 30} | S01 |
| `POMPES!B5` | Relevé 2026-07-09 → GO-PMP-002 | K18 |
| `Plan d'Action et Calendrier!C23` | Control structurel | K22 |
| `Plan d'Action et Calendrier!C24` | Control sanitaire | K22 |
| `Plan d'Action et Calendrier!C25` | Vidange et Nettoyage du stockage de Nyabyunyu | K22 |
| `Plan d'Action et Calendrier!C26` | Vidange et Nettoyage du stockage | K22 |

## 4. À confirmer par l'équipe

- Les totaux mensuels de janvier à juin (feuille `O&M KPI`) sont-ils des chiffres réels ? Ils sont utilisés comme historique « validé ». Plusieurs séries ont des motifs réguliers (K10, K14) ; en cas de doute, relancer avec `--history-status provisional`.
- Seuils de chlore résiduel et de turbidité (valeurs par défaut marquées « à confirmer »).
- Affectation des nœuds, bornes fontaines et personnels aux zones (absente d'Excel).
- Coordonnées GPS manquantes (A09) et position de CP1 (A16).
- Réservoir « MUDJA 200 m³ » (K22) : à ajouter au registre ou à retirer du plan.
- Unité des durées de contrat (P03).

