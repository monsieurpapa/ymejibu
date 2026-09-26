# TASKS — Plateforme E&M Yme Jibu (Goma Ouest)

Checklist de travail. Chaque élément est coché quand il est terminé ; les découvertes sont ajoutées en bas.

## 0. Préparation
- [x] Lire les 5 classeurs Excel avant toute conception
- [x] Branche `feat/em-platform` (les `.xlsx` originaux ne sont jamais modifiés ni commités)

## 1. Audit Excel
- [x] Audit par sous-agents (un par classeur ; le classeur 5 en deux parties)
- [x] Vérification croisée des constats clés contre les fichiers (D19/N19, BW8/DX8, F8, STOCKAGE!B7, RESEAU autofill, BF07/CP1, G29, NH40)
- [ ] Tableau consolidé dans `docs/data-quality-report.md` (généré par l'importeur)

## 2. Modèle de données & backend
- [ ] Modèles Django (core, ops, stock, plan)
- [ ] `docs/data-model.md` + diagramme ER
- [ ] ADR : stack, lat/lon vs PostGIS, formulaires pilotés par définitions, historique mensuel
- [ ] API REST + rôles
- [ ] Endpoint de synchronisation (push/pull, conflits)

## 3. Import Excel
- [ ] Commande idempotente `import_excel`
- [ ] Contrôles qualité exécutables (chaque défaut = un contrôle avec preuve fichier/feuille/cellule)
- [ ] Rapport `docs/data-quality-report.md`

## 4. Moteur KPI
- [ ] Formules pures + service mensuel
- [ ] Tests unitaires calculés à la main
- [ ] Tests de non-régression pour chaque défaut Excel
- [ ] Export XLSX au format `O&M KPI`

## 5. PWA mobile (FR)
- [ ] 7 formulaires champ par champ (définitions partagées)
- [ ] File d'attente IndexedDB, synchronisation, gestion des conflits
- [ ] GPS + photo sur incident
- [ ] Fonctionne une journée hors ligne (service worker)

## 6. Tableau de bord
- [ ] KPI avec tendance et cible
- [ ] Carte actifs/BF/incidents
- [ ] Alertes stock
- [ ] Budget mensuel + plan annuel (Gantt)
- [ ] Export CSV/XLSX

## 7. Livraison
- [ ] Docker Compose
- [ ] Test E2E hors ligne (viewport mobile)
- [ ] README
- [ ] Vérification finale

## Découvertes
- Docker Hub est bloqué depuis l'environnement de build : `docker compose up` doit être vérifié sur la machine cible (la pile est testée en natif ici : PostgreSQL 16 + Django + build Vite + Playwright).
