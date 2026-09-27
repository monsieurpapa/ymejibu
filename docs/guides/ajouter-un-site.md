# Ajouter un nouveau réseau (site)

La plateforme est multi-site : chaque réseau est un `Site` avec un code court (ex. `GE` pour Goma Est). Tous les identifiants sont préfixés par ce code (`GE-PMP-001`, `GE-INC-2027-0001`) et chaque utilisateur ne voit que son site.

## Cas 1 — le réseau a ses propres classeurs au même format

```bash
docker compose exec backend python manage.py import_excel \
  --dir /workbooks/goma-est --site-code GE --site-name "Goma Est" \
  --report /reports/data-quality-report-GE.md
```

Le dossier doit contenir les 5 classeurs nommés comme ceux de Goma Ouest (`1.*Registre des Actifs*.xlsx`, …) ; le monter dans le conteneur (volume `/workbooks`). Relire le rapport qualité produit.

> L'import lit les feuilles à des positions précises (voir `backend/importer/loaders.py`). Si la mise en page des classeurs diffère, utiliser le cas 2 ou adapter l'importeur avec des tests.

## Cas 2 — saisie du référentiel

Dans `/admin/` (ou via l'API, voir `/api/docs/`) :

1. **Sites** → ajouter `GE`, « Goma Est ».
2. **Zones** → `Z1`, `Z2`… du site.
3. **Assets** (actifs) : stations (`PUMP_STATION`), pompes (`PUMP`, parent = station), réservoirs, bornes fontaines (`KIOSK`)… avec des codes `GE-<TYPE>-<NNN>` et, si possible, les coordonnées GPS.
4. **Nodes** (nœuds) et **Pipe segments** (tronçons) du réseau (codes de nœuds en texte).
5. **Stock items** (articles) (`GE-ART-…`), puis un mouvement « Stock initial » par article après inventaire.
6. **Tariffs**, **Quality thresholds**, **Monthly budgets**.
7. **Persons** et comptes ([gestion-utilisateurs.md](gestion-utilisateurs.md)).

## Vérifier

- Se connecter avec un compte du nouveau site : l'accueil affiche le nom du site ; les listes ne montrent que ses actifs.
- Envoyer une fiche de test, vérifier le tableau de bord, puis rejeter la fiche de test.
