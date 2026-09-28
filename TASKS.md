# TASKS — Plateforme E&M Yme Jibu (Goma Ouest)

Checklist de travail. Chaque élément est coché quand il est terminé ; les découvertes sont ajoutées en bas.

## 0. Préparation
- [x] Lire les 5 classeurs Excel avant toute conception
- [x] Branche `feat/em-platform` (les `.xlsx` originaux ne sont jamais modifiés ni commités)

## 1. Audit Excel
- [x] Audit par sous-agents (un par classeur ; le classeur 5 en deux parties)
- [x] Vérification croisée des constats clés contre les fichiers (D19/N19, BW8/DX8, F8, STOCKAGE!B7, RESEAU autofill, BF07/CP1, G29, NH40)
- [x] Tableau consolidé dans `docs/data-quality-report.md` (généré par l'importeur)

## 2. Modèle de données & backend
- [x] Modèles Django (core, ops, stock, plan)
- [x] `docs/data-model.md` + diagramme ER
- [x] ADR : stack, lat/lon vs PostGIS, formulaires pilotés par définitions, historique mensuel
- [x] API REST + rôles
- [x] Endpoint de synchronisation (push/pull, conflits)

## 3. Import Excel
- [x] Commande idempotente `import_excel`
- [x] Contrôles qualité exécutables (chaque défaut = un contrôle avec preuve fichier/feuille/cellule)
- [x] Rapport `docs/data-quality-report.md`

## 4. Moteur KPI
- [x] Formules pures + service mensuel
- [x] Tests unitaires calculés à la main
- [x] Tests de non-régression pour chaque défaut Excel
- [x] Export XLSX au format `O&M KPI`

## 5. PWA mobile (FR)
- [x] 7 formulaires champ par champ (définitions partagées)
- [x] File d'attente IndexedDB, synchronisation, gestion des conflits
- [x] GPS + photo sur incident
- [x] Fonctionne une journée hors ligne (service worker)

## 6. Tableau de bord
- [x] KPI avec tendance et cible
- [x] Carte actifs/BF/incidents
- [x] Alertes stock
- [x] Budget mensuel + plan annuel (Gantt)
- [x] Export CSV/XLSX

## 7. Livraison
- [x] Docker Compose
- [x] Test E2E hors ligne (viewport mobile)
- [x] README
- [x] Vérification finale

## Revue avant fusion (sous-agent) — corrigé
- [x] Relevés périmés après modification d'une fiche (date, lignes) → `derived_keys` + recalcul
- [x] Rejet d'une équipe sans effet sur le relevé du jour → recalcul depuis les fiches actives
- [x] Renvoi après réponse perdue = faux conflit, photos dupliquées → comparaison normalisée, photos par empreinte SHA-256
- [x] Une fiche invalide bloquait tout le lot → traitement par fiche, statut `error` / `retry`
- [x] Rejet d'une checklist non planifiée faisait baisser le taux préventif → `WorkOrder.origin`
- [x] Tous les rôles lisaient les données du tableau de bord → `read_roles`
- [x] Numéros d'incident : course et réutilisation → compteur verrouillé, numéro jamais fourni par le téléphone
- [x] Réimport Excel écrasant des relevés saisis dans l'application
- [x] Changement de pompe sur une checklist → l'ordre planifié retourne au plan

## Découvertes
- `docker compose up --build` vérifié le 2026-09-27 sur Docker Desktop (Windows) : 3 conteneurs démarrés, import au premier démarrage, `/api/health/`, connexion, KPI, export XLSX, `/api/docs/`, `sw.js` en `no-cache` OK. Construction ≈ 7 min (connexion lente).
- Les lignes « Vidange et Nettoyage du stockage » (plan, lignes 20 et 21) sont en double avec les mêmes 12 dates : `plan_work_orders` crée donc deux ordres par date.
- L'historique jan.–juin et le budget mensuel montrent des motifs réguliers (K10, K14) : possibles données de test, à confirmer.
- Les tuiles OpenStreetMap ne se chargent pas dans l'environnement de build (réseau filtré) ; la carte fonctionne avec un accès internet normal.

## Documentation (2026-09-27)
- [x] Schéma OpenAPI (drf-spectacular) + Swagger `/api/docs/` + ReDoc `/api/redoc/`
- [x] Référence générée : dictionnaire de données, formulaires, OpenAPI (`manage.py gen_docs`, vérifié en CI)
- [x] Architecture arc42 / C4, ADR 0004 + index + modèle
- [x] Références : KPI, rôles, configuration, commandes
- [x] Guides : déploiement, sauvegarde, exploitation, utilisateurs, mise à jour, formulaire, nouveau site, migration Excel
- [x] Guides utilisateurs : terrain, responsables
- [x] CONTRIBUTING, CHANGELOG, SECURITY, modèle de PR, CI
- [x] Correction trouvée en documentant : codes d'articles préfixés par le site (`GO-ART-001`) pour éviter une collision au 2ᵉ site
