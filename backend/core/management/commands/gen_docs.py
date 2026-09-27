"""Generate the reference documentation that must never drift from the code.

    python manage.py gen_docs           # (re)write the files
    python manage.py gen_docs --check   # exit 1 if a file is out of date (used in CI)

Outputs (under docs/reference/):
    dictionnaire-donnees.md  from the Django models (tables, columns, types, choices, help texts)
    formulaires.md           from shared/forms.fr.json (the 7 field forms, field by field)
    openapi.yaml             from the DRF views (drf-spectacular)
"""
import io
import json
import sys
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import models

APPS = [
    ("core", "Référentiel : sites, zones, actifs, réseau, personnel"),
    ("ops", "Exploitation : fiches, relevés, pannes, ordres de travail, qualité, dépenses"),
    ("stock", "Stock : articles et grand livre des mouvements"),
    ("plan", "Planification : tarifs, budget, plan d'action"),
    ("kpi", "Historique mensuel importé d'Excel"),
]
HEADER = "<!-- Fichier généré par `python manage.py gen_docs` — ne pas modifier à la main. -->\n\n"


def esc(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def field_type(f):
    if isinstance(f, models.ForeignKey):
        return f"FK → `{f.related_model.__name__}`"
    if isinstance(f, models.OneToOneField):
        return f"1-1 → `{f.related_model.__name__}`"
    t = f.get_internal_type().replace("Field", "")
    if getattr(f, "max_length", None) and t == "Char":
        t += f"({f.max_length})"
    if t == "Decimal":
        t += f"({f.max_digits},{f.decimal_places})"
    return t


def data_dictionary():
    out = io.StringIO()
    w = out.write
    w(HEADER)
    w("# Dictionnaire de données\n\n")
    w("Toutes les tables de la plateforme, colonne par colonne. Vue d'ensemble et diagramme : [../data-model.md](../data-model.md).\n\n")
    w("Conventions : `null` = la colonne accepte l'absence de valeur ; les listes de valeurs autorisées sont données en code → libellé.\n\n")
    for label, title in APPS:
        cfg = apps.get_app_config(label)
        w(f"## `{label}` — {title}\n\n")
        for model in sorted(cfg.get_models(), key=lambda m: m.__name__):
            doc = (model.__doc__ or "").strip()
            if doc.startswith(f"{model.__name__}("):
                doc = ""
            w(f"### {model.__name__}\n\n")
            w(f"Table `{model._meta.db_table}`.")
            if doc:
                w(" " + " ".join(doc.split()))
            w("\n\n")
            uniques = [", ".join(u) for u in model._meta.unique_together]
            if uniques:
                w("Unicité : " + " ; ".join(f"({u})" for u in uniques) + "\n\n")
            w("| Colonne | Type | Null | Description |\n|---|---|---|---|\n")
            for f in model._meta.get_fields():
                if not getattr(f, "concrete", False) or f.auto_created and not f.primary_key:
                    continue
                desc = []
                if f.primary_key:
                    desc.append("clé primaire")
                if getattr(f, "unique", False) and not f.primary_key:
                    desc.append("unique")
                if f.help_text:
                    desc.append(str(f.help_text))
                if f.choices:
                    desc.append("valeurs : " + ", ".join(f"`{k}` {v}" for k, v in f.flatchoices))
                w(f"| `{f.name}` | {field_type(f)} | {'oui' if f.null else ''} | {esc(' — '.join(desc))} |\n")
            w("\n")
    return out.getvalue()


def forms_reference():
    with open(settings.FORMS_DEFINITION_FILE, encoding="utf-8") as fh:
        doc = json.load(fh)
    enums = doc["enums"]
    out = io.StringIO()
    w = out.write
    w(HEADER)
    w("# Formulaires terrain\n\n")
    w("Les 7 fiches de l'application mobile, champ par champ. Source unique : `shared/forms.fr.json`, "
      "généré par `scripts/build_forms.py` (voir [../guides/modifier-un-formulaire.md](../guides/modifier-un-formulaire.md)).\n\n")
    w("Colonne « Ajouté » : champ absent de la fiche Excel d'origine, ajouté car nécessaire au calcul d'un indicateur.\n\n")
    w("| Formulaire | Code | Rôles autorisés |\n|---|---|---|\n")
    for f in doc["forms"]:
        w(f"| [{f['title']}](#{f['type'].lower()}) | `{f['type']}` | {', '.join(f['roles'])} |\n")
    w("\n")
    for f in doc["forms"]:
        w(f"<a id=\"{f['type'].lower()}\"></a>\n\n## {f['title']} (`{f['type']}`)\n\n")
        w(f"Source Excel : `{f['source']}`.\n\n")
        if f.get("intro"):
            w(f"> {f['intro']}\n\n")
        for s in f["sections"]:
            kind = {"fields": "champs", "table": "tableau (lignes libres)", "checklist": "liste de contrôle (lignes fixes)"}[s["kind"]]
            w(f"### {s['title']} — `{s['key']}` ({kind})\n\n")
            if s["kind"] == "checklist":
                w("Lignes : " + " ; ".join(f"{r['label']}{' (' + r['unit'] + ')' if r.get('unit') else ''}" for r in s["rows"]) + "\n\n")
            if s["kind"] == "table":
                w(f"De {s.get('minRows', 0)} à {s.get('maxRows', '—')} lignes.\n\n")
            specs = s.get("fields") or s.get("columns") or []
            w("| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |\n|---|---|---|---|---|---|\n")
            for c in specs:
                ctrl = []
                if "min" in c or "max" in c:
                    ctrl.append(f"{c.get('min', '')} … {c.get('max', '')}")
                if c.get("enum"):
                    ctrl.append(" / ".join(o["label"] for o in enums[c["enum"]][:6]) + (" …" if len(enums[c["enum"]]) > 6 else ""))
                if c.get("assetTypes"):
                    ctrl.append("actif : " + ", ".join(c["assetTypes"]))
                if c.get("readonly"):
                    ctrl.append("lecture seule")
                if c.get("computed"):
                    ctrl.append("calculé")
                added = "oui — " + c.get("note", "") if c.get("added") else ""
                w(f"| `{c['key']}` | {esc(c['label'])} | {c['type']} | {'oui' if c.get('required') else ''} | {esc('; '.join(ctrl))} | {esc(added)} |\n")
            w("\n")
    w("## Listes de valeurs\n\n")
    for name, options in enums.items():
        w(f"- **`{name}`** : " + " ; ".join(f"`{o['value']}` {o['label']}" for o in options) + "\n")
    w("\n## Corrections de libellés par rapport à Excel\n\n")
    for fix, where in doc.get("typo_fixes", {}).items():
        w(f"- {fix} — `{where}`\n")
    return out.getvalue()


def openapi():
    buf = io.StringIO()
    call_command("spectacular", "--validate", "--fail-on-warn", stdout=buf, stderr=io.StringIO())
    return buf.getvalue()


class Command(BaseCommand):
    help = "Génère la documentation de référence (dictionnaire de données, formulaires, OpenAPI)."

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="Échoue si un fichier généré n'est pas à jour")

    def handle(self, *args, **opts):
        ref = settings.REPO_DIR / "docs" / "reference"
        ref.mkdir(parents=True, exist_ok=True)
        targets = {
            ref / "dictionnaire-donnees.md": data_dictionary(),
            ref / "formulaires.md": forms_reference(),
            ref / "openapi.yaml": openapi(),
        }
        stale = []
        for path, content in targets.items():
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != content:
                stale.append(path)
                if not opts["check"]:
                    path.write_text(content, encoding="utf-8")
        rel = [str(Path(p).relative_to(settings.REPO_DIR)) for p in stale]
        if opts["check"]:
            if stale:
                self.stderr.write("Documentation générée périmée : " + ", ".join(rel) + " — lancer `python manage.py gen_docs`.")
                sys.exit(1)
            self.stdout.write(self.style.SUCCESS("Documentation générée à jour."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{len(stale)} fichier(s) mis à jour : {', '.join(rel) or 'aucun'}"))
