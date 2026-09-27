## Quoi et pourquoi

<!-- Ce que change cette PR et le problème qu'elle résout. Lien vers l'issue ou l'ADR. -->

## Comment vérifier

<!-- Étapes pour tester à la main, données utilisées. -->

## Liste de contrôle

- [ ] Tests ajoutés ou mis à jour (bogue : un test qui échouait avant)
- [ ] `python -m pytest` et `npm run build` passent
- [ ] Documentation générée à jour (`python manage.py gen_docs`)
- [ ] Migrations commitées si les modèles changent
- [ ] Nouvelle vue d'API : `read_roles` / `write_roles` + test de refus
- [ ] Formulaire modifié : aucune clé renommée ni supprimée
- [ ] `CHANGELOG.md` mis à jour
- [ ] Documentation concernée mise à jour (guides, références, ADR)
