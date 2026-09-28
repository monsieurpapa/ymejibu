# Guide des responsables — tableau de bord

Pour le Responsable technique, l'adjoint, le responsable des données et le responsable SSE. Les bailleurs voient les mêmes indicateurs en lecture seule.

Accès : se connecter, puis **Tableau de bord** (un ordinateur est plus confortable qu'un téléphone).

## 1. En-tête et filtres

- Compteurs : pannes ouvertes (dont critiques) et fiches à valider.
- **Année**, **Actualiser**, **Rapport PDF (graphiques)**, **Export XLSX (format O&M KPI)**, **Export CSV**. L'export XLSX a exactement la disposition de l'ancienne feuille « O&M KPI » (mêmes lignes et libellés), pour les rapports aux bailleurs.
- **Rapport PDF** : le rapport complet de l'année, prêt à imprimer ou à envoyer : synthèse des indicateurs (dernière valeur, cible), graphiques de tendance sur 12 mois avec la cible, causes des pannes, tableau mensuel complet (page paysage), puis une page de détail pour chaque mois ayant des données. Nécessite une connexion.

## 2. Indicateurs

Chaque carte montre : la dernière valeur, le mois, sa source (**fiches terrain** ou **historique Excel**), la comparaison à la **cible**, et la tendance sur 12 mois (survoler un point pour la valeur).

- Un mois **vide** = pas de donnée (jamais « 0 » ni « 100 % » par défaut).
- **Mois en cours** : l'encadré indique combien de jours ont des relevés ; les valeurs sont partielles.
- **Tableau mensuel** : toutes les valeurs par mois ; « h » = historique Excel. Cliquer sur le nom d'un mois ouvre son détail.

### Détail du mois

Choisir un mois dans la bande **Janv … Déc** (ou avec les flèches), en cliquant sur un point d'un graphique, ou sur un mois du tableau. Un point vert signale un mois qui a des données ; les mois à venir sont grisés.

- **Statut** : mois clôturé ou en cours (valeurs partielles), jours de relevés de pompage, présence d'historique Excel.
- **Indicateurs du mois** comparés au mois précédent : l'évolution est en **vert** si elle va dans le bon sens, en **rouge** sinon (en points pour les pourcentages), et la cible est marquée « atteinte » ou « sous la cible ».
- **Chiffres clés** : eau et pertes, fonctionnement (heures d'arrêt), énergie, budget, qualité de l'eau, maintenance préventive réalisée / prévue par catégorie.
- **Répartitions** : heures d'arrêt par cause, pannes par cause racine, pertes d'eau par cause, dépenses par type de maintenance.
- **PDF du mois** : le détail du mois et les tendances de l'année (mois choisi surligné), en quelques pages.

Définitions exactes : [../reference/kpi.md](../reference/kpi.md).

## 3. Fiches à valider

Onglet **Fiches** : les fiches envoyées par les agents.

- Ouvrir une fiche pour voir son contenu.
- **Valider** (bouton vert, coche) : la fiche devient non modifiable par l'agent.
- **Rejeter** (bouton rouge, croix) : ses valeurs sont **retirées immédiatement** des indicateurs, du stock et des dépenses (ex. un débit de 1 800 au lieu de 180). **Rétablir** les remet.

Bonne pratique : valider chaque semaine ; rejeter plutôt que laisser une valeur aberrante.

## 4. Carte

Bornes fontaines, réservoirs, stations et pannes des 6 derniers mois. Les actifs sans coordonnées GPS sont listés sous la carte : les relever sur le terrain et les saisir dans l'administration.

## 5. Stock

- Bandeau rouge : articles **sous le seuil**.
- **Enregistrer un mouvement** : Stock initial (inventaire), Entrée, Sortie, Ajustement.
- Les sorties liées aux pannes sont automatiques (pièces remplacées).
- Première étape : faire l'**inventaire** et saisir un « Stock initial » par article (les quantités Excel étaient des valeurs de test), puis fixer les **seuils d'alerte** dans l'administration.

## 6. Budget

Budget prévu, dépense réelle, écart et répartition urgente / corrective / préventive / support pour le mois choisi, avec les lignes de besoins budgétés (« non chiffré » = sans quantité ou prix).

## 7. Plan annuel

Diagramme de Gantt du plan d'action : période, jours programmés, avancement. Chaque début de mois, l'administrateur génère les ordres de travail préventifs du mois à partir du plan ; les checklists préventives remplies sur le terrain les clôturent, ce qui alimente le **taux de maintenance préventive**.

## 8. Paramètres à tenir à jour (administration)

| Paramètre | Où |
|---|---|
| Tarifs électricité et carburant | Tariffs |
| Seuils de qualité (chlore, turbidité) | Quality thresholds |
| Budget mensuel | Monthly budgets |
| Seuils d'alerte de stock | Stock items |
| Zones des bornes, nœuds et techniciens | Assets, Nodes, Persons |
| Comptes | [../guides/gestion-utilisateurs.md](../guides/gestion-utilisateurs.md) |
