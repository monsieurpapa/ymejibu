# Guide terrain — techniciens et points focaux

Ce guide explique comment remplir les fiches sur le téléphone, avec ou sans réseau.

## 1. Installer l'application (une seule fois, avec du réseau)

1. Ouvrir Chrome sur le téléphone et aller à l'adresse donnée par le responsable (ex. `https://em.ymejibu.org`).
2. Se connecter avec son **identifiant** et son **mot de passe**.
3. Menu de Chrome (⋮) → **Ajouter à l'écran d'accueil**. L'application s'ouvre ensuite comme une application normale.

Après cette première connexion, l'application **fonctionne sans réseau**.

## 2. L'écran d'accueil

- **Barre du haut** : « En ligne » ou « Hors ligne », nombre de fiches **en attente**, dernier envoi, bouton **Envoyer**.
- **Nouvelle fiche** : seulement les fiches autorisées pour votre poste, rangées en trois groupes, chacun avec sa couleur et son icône :
  - **Relevés journaliers** (bleu) : pompage (jauge), stockage (réservoir), réseau et bornes fontaines (réseau) ;
  - **Pannes et interventions** (rouge, triangle d'alerte) ;
  - **Maintenance préventive** (vert, bouclier) : la petite icône en bas à droite indique pompe, réservoir ou réseau.
- **Mes fiches** : toutes les fiches du téléphone et leur état (étiquette colorée avec icône).

Couleurs des boutons : **bleu** = action principale (envoyer, se connecter) ; **vert** = valider, enregistrer ; **rouge** = supprimer, rejeter, se déconnecter ; **orange** = fiches en attente d'être envoyées. Dans le rapport de panne, le type d'intervention choisi s'affiche en rouge (Maintenance Urgente, sirène) ou en orange (Maintenance Corrective, clé).

| État | Signification | Que faire |
|---|---|---|
| Brouillon | Commencée, pas encore validée | La terminer puis « Valider et envoyer » |
| En attente d'envoi | Validée, sera envoyée au retour du réseau | Rien : l'envoi est automatique |
| Envoyée | Reçue par le serveur | Rien |
| Refusée : à corriger | Le serveur a trouvé une erreur | Ouvrir la fiche, lire le message en rouge, corriger, renvoyer |
| Conflit à résoudre | La fiche a été modifiée ailleurs | Choisir « Garder ma version » ou « Prendre la version du serveur » |
| Erreur | Problème du serveur | Prévenir le responsable ; la fiche reste sur le téléphone |

## 3. Remplir une fiche

1. **Nouvelle fiche** → choisir la fiche. La date du jour et votre nom sont déjà remplis.
2. Choisir la **station**, le **réservoir**, la **zone** ou la **borne fontaine** dans la liste.
3. Remplir les champs. Les champs avec **\*** sont obligatoires. Les unités sont indiquées (m³/h, bar, mg/L…).
4. Les champs marqués **AJOUTÉ** n'existaient pas sur la fiche papier : ils servent au calcul des indicateurs (volume pompé, volume vendu, durée d'arrêt…). Merci de les remplir.
5. **Valider et envoyer**. Si un champ est faux, il est entouré de rouge avec l'explication.

La fiche est **enregistrée sur le téléphone à chaque saisie** : on peut fermer l'application et reprendre plus tard.

### Conseils par fiche

| Fiche | Points d'attention |
|---|---|
| **Station de pompage** | Une ligne par pompe et par période de marche (heure de démarrage et d'arrêt). Si le volume n'est pas connu, laisser vide : il est calculé avec le débit × la durée. Indiquer les kWh (SNEL) et les litres (groupe). |
| **Stockage** | Niveau en % **ou** en m³ (deux champs séparés). Remplir les volumes entrant et sortant de la journée. |
| **Réseau et bornes fontaines** | Une ligne par borne visitée, avec le **volume vendu** et le **chlore résiduel**. La case « Qualité conforme » se calcule seule. Signaler les fuites avec le nœud. |
| **Rapport de panne** | Remplir dès la détection. Si le service est coupé, indiquer la **cause de l'arrêt** et sa **durée**. Relever la **position GPS** et prendre jusqu'à **3 photos**. Ajouter les **pièces remplacées** : elles sont retirées du stock automatiquement. Le numéro de panne (ex. GO-INC-2026-0012) est donné à l'envoi. |
| **Checklists préventives** | Cocher Bon/Mauvais ou Oui/Non pour chaque ligne ; noter les besoins de maintenance avec l'échéance. |

## 4. Sans réseau

- Tout fonctionne : remplir, valider, consulter ses fiches.
- Les fiches validées attendent dans **En attente d'envoi**.
- Dès que le réseau revient, elles partent **toutes seules** (on peut aussi appuyer sur **Envoyer**).
- **Ne pas se déconnecter** tant que des fiches sont en attente : elles seraient perdues. L'application prévient.

## 5. Questions fréquentes

**Je me suis trompé après l'envoi.** Ouvrir la fiche dans « Mes fiches », corriger, **Renvoyer**. Si le responsable l'a déjà validée, lui demander de la corriger.

**La liste des bornes est vide.** Choisir d'abord la zone. Si elle reste vide, se reconnecter avec du réseau pour mettre à jour les listes, puis prévenir le responsable.

**Le GPS ne trouve pas la position.** Sortir à découvert, attendre 20 secondes, réessayer. Sinon, indiquer le nœud et une référence (ex. « devant le marché »).

**J'ai changé de téléphone.** Envoyer toutes les fiches depuis l'ancien avant de s'y déconnecter.
