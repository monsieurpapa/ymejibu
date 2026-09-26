# ADR 0001 — Pile technique

**Statut :** accepté · **Date :** 2026-09-27

## Décision

- **Backend** : Django 5.1 + Django REST Framework, PostgreSQL 16 (pile par défaut demandée).
- **Frontend** : React + Vite, PWA (service worker Workbox via `vite-plugin-pwa`), stockage hors ligne IndexedDB (`idb`).
- **Exécution locale** : Docker Compose (PostgreSQL, backend gunicorn, nginx qui sert la PWA et relaie `/api`).

## Écart assumé : pas de PostGIS pour l'instant

Les positions sont stockées en latitude/longitude décimales. Aucun calcul spatial n'est nécessaire aujourd'hui (la carte affiche des points, les longueurs de conduites viennent du registre). PostGIS impose GDAL/GEOS dans l'image backend (+ ~150 Mo) et complique l'hébergement bon marché. Si des requêtes spatiales deviennent utiles (tracé des conduites, « actifs à moins de 500 m »), passer à `django.contrib.gis` : les colonnes lat/lon se convertissent en `PointField` par une migration.

## Conséquences

- Image légère, hébergement possible sur un petit VPS (1 vCPU / 1 Go).
- Carte : tuiles OpenStreetMap chargées en ligne (le tableau de bord est utilisé au bureau) ; les tuiles déjà vues sont mises en cache par le service worker.
- Les photos sont servies par Django sous des noms UUID non devinables ; en production à plus grande échelle, les servir par nginx ou un stockage objet.
