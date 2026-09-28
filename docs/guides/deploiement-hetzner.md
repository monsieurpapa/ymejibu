# Mettre en production sur Hetzner (le moins coûteux)

Recette complète pour mettre la plateforme en ligne sur un serveur **Hetzner Cloud CX23** avec HTTPS automatique. Le guide générique est [deploiement.md](deploiement.md) ; celui-ci l'automatise.

| Élément | Choix | Coût mensuel indicatif (HT, sept. 2026) |
|---|---|---|
| Serveur | Hetzner CX23 : 2 vCPU, 4 Go de RAM, 40 Go SSD, Ubuntu 24.04 | 5,49 € |
| Adresse IPv4 publique | Nécessaire (la plupart des téléphones en RDC sont en IPv4) | ≈ 0,60 € |
| Sauvegardes Hetzner | Image complète du serveur, 7 dernières conservées | +20 % du serveur, ≈ 1,10 € |
| Nom de domaine | `em.<ip>.sslip.io`, gratuit (un vrai domaine peut le remplacer plus tard) | 0 € |
| Certificat HTTPS | Let's Encrypt, obtenu et renouvelé par Caddy | 0 € |
| **Total** | | **≈ 7 à 8 € / mois** |

Vérifier les prix au moment de la commande : Hetzner les a relevés le 15 juin 2026.

## Ce qui est automatisé

Le fichier [`deploy/hetzner-cloud-init.yaml`](../../deploy/hetzner-cloud-init.yaml), collé à la création du serveur :

- met à jour le système, active les mises à jour de sécurité automatiques, `fail2ban` et le pare-feu (ports 22, 80, 443 uniquement) ;
- interdit la connexion SSH par mot de passe (clé SSH obligatoire) ;
- récupère l'application depuis GitHub et lance [`deploy/install.sh`](../../deploy/install.sh), qui :
  - installe Docker ;
  - crée un swap de 2 Go ;
  - génère `/opt/ymejibu/.env` avec des secrets aléatoires, sans comptes de démonstration ;
  - démarre la pile avec [`deploy/docker-compose.prod.yml`](../../deploy/docker-compose.prod.yml) : Caddy (HTTPS) → nginx → Django → PostgreSQL ;
  - programme une sauvegarde quotidienne à 02:30 de la base et des photos dans `/var/backups/ymejibu` (14 jours).

## 1. Créer une clé SSH (une seule fois, sur votre PC Windows)

Dans PowerShell :

```powershell
ssh-keygen -t ed25519          # Entrée pour accepter l'emplacement ; choisir une phrase de passe
type $env:USERPROFILE\.ssh\id_ed25519.pub   # copier cette ligne
```

## 2. Créer le serveur (console Hetzner)

1. Créer un compte sur <https://console.hetzner.com> et un projet « Yme Jibu ».
2. **Add Server** :
   - **Location** : Falkenstein ou Nuremberg ;
   - **Image** : Ubuntu 24.04 ;
   - **Type** : Shared vCPU, x86, **CX23** ;
   - **Networking** : IPv4 et IPv6 ;
   - **SSH keys** : coller la ligne copiée à l'étape 1 ;
   - **Backups** : activer ;
   - **Cloud config** : coller **tout** le contenu de `deploy/hetzner-cloud-init.yaml` ;
   - **Name** : `ymejibu-prod`.
3. **Create & Buy now**. Noter l'adresse IPv4, par exemple `203.0.113.10`.

L'installation dure 5 à 10 minutes. L'adresse de l'application sera `https://em.203-0-113-10.sslip.io`, c'est-à-dire l'IP avec des tirets.

Pour suivre l'installation :

```powershell
ssh root@203.0.113.10 "tail -f /var/log/cloud-init-output.log"
```

La ligne finale est `[ymejibu-install] Terminé. Adresse : https://…`. Contrôle : ouvrir `https://em.203-0-113-10.sslip.io/api/health/`, qui doit afficher `{"status": "ok"}`.

## 3. Charger les classeurs Excel

Depuis le dossier du projet sur votre PC, là où se trouvent les 5 classeurs :

```powershell
$IP = "203.0.113.10"
Get-ChildItem *.xlsx | ForEach-Object { scp $_.FullName "root@${IP}:/opt/ymejibu/" }
ssh root@$IP "cd /opt/ymejibu && docker compose exec -T backend python manage.py import_excel"
```

Le rapport qualité est écrit dans `/opt/ymejibu/docs/rapport-qualite-production.md` sur le serveur (fichier hors Git) :

```powershell
scp "root@${IP}:/opt/ymejibu/docs/rapport-qualite-production.md" .
```

## 4. Créer l'administrateur, puis le personnel

```powershell
ssh -t root@$IP "cd /opt/ymejibu && docker compose exec backend python manage.py createsuperuser"
```

Ensuite, créer les comptes du personnel dans `https://em.…sslip.io/admin/` : voir [gestion-utilisateurs.md](gestion-utilisateurs.md).

## 5. Supervision gratuite

Créer une sonde HTTPS sur `https://em.…sslip.io/api/health/`, toutes les 5 minutes, avec alerte par e-mail. UptimeRobot, en offre gratuite, convient.

## Mettre à jour vers une nouvelle version

```powershell
ssh root@$IP "cd /opt/ymejibu && ./scripts/sauvegarde.sh && git pull --ff-only && docker compose up -d --build"
```

Les migrations s'appliquent au démarrage du backend. Les téléphones reçoivent la nouvelle version à la prochaine ouverture de l'application.

## Passer plus tard à un vrai nom de domaine

1. Chez le registraire, créer un enregistrement **A** `em.ymejibu.org` vers l'IP du serveur.
2. Sur le serveur, dans `/opt/ymejibu/.env`, remplacer l'ancien nom dans `DOMAIN`, `DJANGO_ALLOWED_HOSTS` et `DJANGO_CSRF_TRUSTED_ORIGINS`. Garder `https://` dans cette dernière.
3. Lancer `docker compose up -d`. Caddy obtient le nouveau certificat tout seul.

Les téléphones devront se reconnecter une fois sur la nouvelle adresse. Leurs fiches non envoyées restent liées à l'ancienne adresse : les envoyer **avant** le changement.

## Commandes utiles sur le serveur

```bash
cd /opt/ymejibu
docker compose ps                      # état des conteneurs
docker compose logs -f --tail=100      # journaux
./scripts/sauvegarde.sh                # sauvegarde immédiate
cat /var/log/ymejibu-backup.log        # historique des sauvegardes
```

Le fichier `.env` contient les secrets (droits `600`). Ne jamais le commiter ni le partager.

## Limites connues

- Les serveurs Hetzner sont en Europe. Depuis Goma, le délai est d'environ 150 à 250 ms, ce qui ne gêne pas une application conçue pour le hors-ligne.
- `sslip.io` est un service gratuit tiers. S'il tombait, l'application deviendrait injoignable par son nom. Un vrai domaine (≈ 10 €/an) supprime cette dépendance ; le prévoir avant la généralisation.
- Les sauvegardes quotidiennes restent sur le même serveur. Les **Backups Hetzner** de l'étape 2 en gardent une copie hors du serveur. Pour une seconde copie hors Hetzner, définir `OFFSITE_CMD` : voir [sauvegarde-restauration.md](sauvegarde-restauration.md).
