# Modifier un formulaire terrain

Les 7 fiches sont définies à un seul endroit : `scripts/build_forms.py`, qui génère `shared/forms.fr.json`. Le téléphone et le serveur lisent ce fichier : un changement s'applique partout.

## Règles

1. **Ne jamais renommer ni supprimer une clé** (`key`) déjà utilisée : les fiches passées la contiennent. Pour changer un libellé, modifier `label` seulement. Pour remplacer un champ, en ajouter un nouveau et cesser d'afficher l'ancien.
2. Tout champ absent de la fiche Excel d'origine et ajouté pour un indicateur porte `added(…, "raison")` : il s'affiche avec le badge « ajouté ».
3. Donner une **unité** dans le libellé et des bornes `min` / `max` réalistes (elles bloquent les fautes de frappe).
4. Si le champ doit alimenter un indicateur, mettre à jour la dérivation (`backend/ops/derive.py`) **et** ajouter un test.

## Étapes (exemple : ajouter « Niveau d'huile » au contrôle technique du pompage)

1. Dans `scripts/build_forms.py`, section `technical` du formulaire `POMPAGE`, ajouter la ligne :
   ```python
   ("oil_level", "Niveau d'huile"),
   ```
2. Régénérer :
   ```bash
   python3 scripts/build_forms.py
   cd backend && python manage.py gen_docs      # met à jour docs/reference/formulaires.md
   ```
3. Tester :
   ```bash
   python -m pytest
   cd ../frontend && npm run build
   ```
4. Commiter `scripts/build_forms.py`, `shared/forms.fr.json` et `docs/reference/formulaires.md` ensemble ; décrire le changement dans `CHANGELOG.md`.
5. Déployer ([mise-a-jour.md](mise-a-jour.md)). Les téléphones récupèrent la nouvelle définition avec le référentiel (`/api/reference/`) à la prochaine connexion.

## Types de champs

| Type | Rendu | Stocké |
|---|---|---|
| `text`, `textarea` | champ texte | chaîne |
| `number`, `integer` | clavier numérique, virgule acceptée | chaîne décimale |
| `date`, `time`, `datetime` | sélecteurs natifs | ISO 8601 |
| `enum` | boutons (≤ 3 choix) ou liste | code (`OUI`, `BON`, …) |
| `asset`, `zone`, `node`, `stock_item` | liste issue du référentiel | code (`GO-PMP-001`, `Z1`, `1.10`, `GO-ART-001`) |
| `gps` | bouton « Relever la position » | `{lat, lon, accuracy_m}` |
| `photos` | appareil photo, compression | pièces jointes (3 max) |
| `auto`, `asset_specs`, `asset_capacity`, `asset_location`, `threshold` | lecture seule | — |

Sections : `fields` (champs simples), `table` (lignes libres, `minRows`/`maxRows`), `checklist` (lignes fixes × colonnes).
