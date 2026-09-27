# Gérer les utilisateurs

Chaque personne qui utilise la plateforme a **un compte** (identifiant + mot de passe) relié à **une fiche Personne** qui porte son rôle, son site et sa zone. Pas de compte partagé : les fiches sont signées par leur auteur.

## Créer un compte

1. Ouvrir `https://<serveur>/admin/` avec un compte administrateur.
2. **Utilisateurs → Ajouter** : identifiant (ex. `j.kambale`), mot de passe provisoire. Enregistrer.
3. **Persons** (Personnes) : ouvrir la fiche du poste importée d'Excel (ex. « Technicien 1 — Point focal du réseau Zone 1 ») ou en créer une.
   - **User** : choisir le compte créé.
   - **Full name** (nom complet), **Role** (rôle), **Site**, **Zone** (obligatoire pour un technicien de zone).
4. Communiquer l'identifiant et le mot de passe provisoire à la personne ; elle se connecte une première fois **avec du réseau**.

Rôles disponibles et droits : [../reference/roles.md](../reference/roles.md).

## Changer le rôle ou la zone

Modifier la fiche **Person**. Le changement s'applique dès la requête suivante ; sur le téléphone, les nouvelles listes (zones, formulaires) apparaissent après la prochaine synchronisation du référentiel (au démarrage de l'application avec du réseau).

## Désactiver un compte (départ, téléphone perdu)

1. **Utilisateurs** → décocher **Actif**.
2. **Jetons** → supprimer le jeton de l'utilisateur.

Les fiches déjà envoyées restent attribuées à la personne (historique conservé).

## Réinitialiser un mot de passe

`/admin/` → Utilisateurs → *formulaire de changement de mot de passe*, ou :

```bash
docker compose exec backend python manage.py changepassword <identifiant>
```

## Comptes de démonstration

`create_demo_users` (ou `DEMO_PASSWORD` dans Docker Compose) crée `resp`, `adjoint`, `tech1`, `tech2`, `pompage`, `stockage`, `sse`, `donnees`, `bailleur` avec un mot de passe commun. **À réserver aux essais et formations ; jamais en production.** Pour les supprimer : `/admin/` → Utilisateurs → sélectionner → Supprimer.
