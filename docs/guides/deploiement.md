# Déployer en production

Objectif : faire tourner la plateforme sur un serveur accessible en HTTPS par les téléphones et le bureau.

> Pour un serveur Hetzner, tout ce guide est automatisé par `deploy/` : voir [deploiement-hetzner.md](deploiement-hetzner.md).

## Prérequis

| Élément | Minimum conseillé |
|---|---|
| Serveur | VPS Linux (Ubuntu 22.04+), 1 vCPU, 2 Go de RAM, 20 Go de disque |
| Logiciels | Docker Engine 24+ et le plugin Docker Compose |
| Réseau | Un nom de domaine (ex. `em.ymejibu.org`) pointant vers le serveur ; ports 80 et 443 ouverts |
| Accès | Compte avec `sudo` ; clé SSH |

> **HTTPS est obligatoire** : sans lui, les navigateurs désactivent le service worker (mode hors ligne), le GPS et l'appareil photo.

## 1. Récupérer le code et les classeurs

```bash
git clone https://github.com/monsieurpapa/ymejibu.git /opt/ymejibu
cd /opt/ymejibu
git checkout <version>          # une étiquette de version, ex. v0.1.0
# Copier les 5 classeurs Excel à la racine de /opt/ymejibu (ils ne sont pas dans Git)
```

## 2. Configurer

Créer `/opt/ymejibu/.env` (droits `600`) — liste complète dans [../reference/configuration.md](../reference/configuration.md) :

```dotenv
DJANGO_SECRET_KEY=<64 caractères aléatoires>
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=em.ymejibu.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://em.ymejibu.org
POSTGRES_PASSWORD=<mot de passe fort>
DEMO_PASSWORD=
```

`DEMO_PASSWORD` **vide** : aucun compte de démonstration en production.

## 3. Exposer uniquement en local, derrière un reverse proxy HTTPS

Dans `docker-compose.yml`, le service `web` publie `8080:80`. En production, limiter à l'interface locale en ajoutant un fichier `docker-compose.override.yml` :

```yaml
services:
  web:
    ports: !override
      - "127.0.0.1:8080:80"
```

Puis installer un reverse proxy qui gère le certificat. Exemple avec **Caddy** (certificat Let's Encrypt automatique), `/etc/caddy/Caddyfile` :

```caddy
em.ymejibu.org {
    encode gzip
    reverse_proxy 127.0.0.1:8080
    request_body {
        max_size 12MB
    }
}
```

## 4. Démarrer

```bash
cd /opt/ymejibu
docker compose up --build -d
docker compose logs -f backend      # attendre « Import terminé » puis Ctrl+C
curl -s https://em.ymejibu.org/api/health/     # {"status": "ok"}
```

Au premier démarrage, le backend applique les migrations, importe les classeurs et écrit `docs/data-quality-report.md`.

## 5. Créer l'administrateur et les comptes

```bash
docker compose exec backend python manage.py createsuperuser
```

Puis créer les comptes du personnel : [gestion-utilisateurs.md](gestion-utilisateurs.md).

## 6. Mettre en place les sauvegardes et la supervision

- Sauvegardes quotidiennes : [sauvegarde-restauration.md](sauvegarde-restauration.md).
- Supervision de `/api/health/` : [exploitation.md](exploitation.md).

## Liste de vérification avant ouverture

- [ ] `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` et `POSTGRES_PASSWORD` uniques et forts
- [ ] `DEMO_PASSWORD` vide ; aucun compte `resp`, `tech1`… sur le serveur
- [ ] HTTPS valide ; le port 8080 n'est pas accessible depuis Internet
- [ ] Sauvegarde automatique testée par une restauration
- [ ] Supervision de `/api/health/` active
- [ ] Rapport qualité relu ; historique janvier–juin confirmé ou passé en provisoire
- [ ] Seuils de qualité, tarifs, cibles et zones validés par le Responsable technique
- [ ] Un téléphone de test : connexion, mode avion, saisie, retour du réseau, fiche reçue

## Mise à jour vers une nouvelle version

Voir [mise-a-jour.md](mise-a-jour.md).
