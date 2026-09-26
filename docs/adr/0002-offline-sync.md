# ADR 0002 — Formulaires pilotés par définitions et synchronisation hors ligne

**Statut :** accepté · **Date :** 2026-09-27

## Contexte

Les techniciens travaillent sur des téléphones Android avec une connexion intermittente et lente. Une journée entière sans réseau doit être possible. Les 7 fiches Excel doivent être reprises champ par champ.

## Décisions

1. **Une seule définition des formulaires** : `shared/forms.fr.json`, générée par `scripts/build_forms.py`. Le téléphone s'en sert pour afficher et valider, le serveur pour valider (`backend/ops/forms.py`). Les champs ajoutés (absents des fiches papier mais indispensables aux KPI) portent `added: true` et une note visible (« ajouté »).
2. **La fiche brute est la source** : le serveur stocke le `payload` tel que saisi (audit), puis en dérive les enregistrements normalisés (`backend/ops/derive.py`), de façon idempotente.
3. **Identifiant créé sur le téléphone** (UUID) : renvoyer la même fiche deux fois (réponse perdue) ne crée jamais de doublon.
4. **Conflits par version** : chaque fiche a une `version`. Le téléphone envoie `base_version` ; si le serveur a une version plus récente avec un contenu différent → `conflict`, le téléphone garde les deux copies et l'utilisateur choisit « garder ma version » (renvoi sur la version serveur) ou « prendre celle du serveur ». Contenu identique → `unchanged` (pas de faux conflit).
5. **Relevés journaliers = somme des fiches du jour** : deux fiches de pompage le même jour (deux équipes) s'additionnent au lieu de s'écraser.
6. **Photos** compressées sur le téléphone (1280 px, JPEG 0,6 ≈ 150 ko), envoyées dans la fiche puis extraites en pièces jointes par le serveur.
7. **Données de référence** (actifs, nœuds, zones, articles, seuils, définitions) téléchargées en un seul appel `/api/reference/` avec ETag : rien n'est retéléchargé si rien n'a changé.
8. **Envoi automatique** au retour du réseau (événement `online`) et toutes les 60 s, par lots de 10.

## Règles métier choisies (à confirmer, voir README « Bloqué sur vous »)

- Une panne a **une seule cause d'arrêt** (panne pompe, rupture, coupure électrique, maintenance programmée, autre). Si un arrêt a deux causes, saisir deux rapports. Les heures d'arrêt de plusieurs pannes s'additionnent (même convention que la feuille Excel).
- Durée d'arrêt non saisie = de l'heure de détection à la fin d'intervention, si le service a été interrompu.
- Une checklist préventive clôt l'ordre de travail planifié du même mois (même actif ou même zone) ; sans ordre planifié, elle crée un ordre « réalisé » (compté prévu et réalisé).
