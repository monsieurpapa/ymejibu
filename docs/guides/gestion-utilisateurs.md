# Gérer les utilisateurs

Chaque personne qui utilise la plateforme a **un compte** (identifiant + mot de passe) relié à **une fiche Personne** qui porte son rôle, son site et sa zone. Pas de compte partagé : les fiches sont signées par leur auteur.

La gestion se fait dans l'application : **Tableau de bord → onglet Utilisateurs**. L'onglet n'apparaît que pour les **super administrateurs**.

## Les trois niveaux d'accès

| Niveau | Réglage | Effet |
|---|---|---|
| **Super administrateur** | case « Super administrateur » | Tous les droits, y compris la gestion des utilisateurs et l'administration Django (`/admin/`) |
| **Rôle** | liste « Rôle » (+ « Zone » pour un technicien de zone) | Ce que la personne peut saisir, lire et valider : voir le tableau **Rôles et droits** en bas de l'onglet et [../reference/roles.md](../reference/roles.md) |
| **Compte actif** | case « Compte actif » | Décochée : la personne ne peut plus se connecter ; son historique est conservé |

## Premier super administrateur

Le tout premier compte se crée sur le serveur (une seule fois) :

```bash
docker compose exec backend python manage.py createsuperuser
```

Ensuite, tout se fait depuis l'onglet **Utilisateurs**, y compris la création d'autres super administrateurs.

## Créer un compte

1. **Nouvel utilisateur**.
2. Si le poste existe déjà dans le classeur Personnel importé, choisir la fiche dans **Lier à une fiche du personnel existante** : rôle, fonction et zone sont repris.
3. Renseigner l'**identifiant** (ex. `j.kambale`, sans espace), le nom complet, le **rôle** et, pour un technicien de zone, la **zone**. Sous le rôle choisi s'affiche ce qu'il permet.
4. **Mot de passe** : saisir ou cliquer **Générer**, puis **Copier**. Au moins 8 caractères, ni uniquement des chiffres, ni un mot de passe courant.
5. **Créer le compte**. Transmettre identifiant et mot de passe en main propre ; la première connexion se fait **avec du réseau**.

## Modifier le rôle, la zone ou les droits

**Modifier** sur la ligne du compte. Le changement s'applique à la requête suivante. Sur le téléphone, les formulaires et zones sont mis à jour à la prochaine ouverture de l'application avec du réseau.

## Réinitialiser un mot de passe

**Mot de passe** sur la ligne du compte. La personne est **déconnectée de tous ses appareils** ; ses fiches non envoyées restent sur le téléphone et partent après reconnexion.

## Désactiver ou supprimer

- **Désactiver** (départ, téléphone perdu) : la personne est déconnectée partout et ne peut plus se connecter. L'historique reste attribué à son nom. **Réactiver** annule l'opération. C'est l'action recommandée.
- **Supprimer** : efface le compte. La fiche du personnel est conservée, mais les fiches déjà envoyées n'affichent plus le nom de l'auteur.

## Garde-fous

- On ne peut ni supprimer, ni désactiver, ni retirer les droits de super administrateur de **son propre compte**.
- Il reste toujours **au moins un super administrateur actif**.
- Toutes ces règles sont vérifiées par le serveur (`/api/users/`), pas seulement par l'écran.

## Comptes de démonstration

`create_demo_users` (ou `DEMO_PASSWORD` dans Docker Compose) crée `resp`, `adjoint`, `tech1`, `tech2`, `pompage`, `stockage`, `sse`, `donnees`, `bailleur` avec un mot de passe commun. **À réserver aux essais et formations ; jamais en production.** Pour les retirer : onglet **Utilisateurs** → **Supprimer**.
