import datetime as dt
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from importer.checks import run_all
from importer.loaders import import_all
from importer.report import build, write
from importer.xl import Workbooks
from kpi.models import MonthlyAggregate


class Command(BaseCommand):
    help = "Importe les 5 classeurs Excel (idempotent) et écrit docs/data-quality-report.md."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=str(settings.WORKBOOK_DIR), help="Dossier contenant les classeurs")
        parser.add_argument("--year", type=int, default=2026)
        parser.add_argument("--today", help="Date de référence AAAA-MM-JJ (par défaut aujourd'hui)")
        parser.add_argument("--report", default=str(settings.DATA_QUALITY_REPORT))
        parser.add_argument("--site-code", default="GO")
        parser.add_argument("--site-name", default="Goma Ouest")
        parser.add_argument("--history-status", choices=["actual", "provisional"], default="actual",
                            help="Statut de l'historique mensuel antérieur aux relevés journaliers")

    def handle(self, *args, **opts):
        today = dt.date.fromisoformat(opts["today"]) if opts["today"] else timezone.localdate()
        wb = Workbooks(opts["dir"])
        findings, errors = run_all(wb)
        with transaction.atomic():
            site, log = import_all(wb, opts["year"], today, opts["site_code"], opts["site_name"])
            if opts["history_status"] == "provisional":
                n = MonthlyAggregate.objects.filter(site=site, status="ACTUAL").update(status="PROVISIONAL")
                log.notes.append(f"Option --history-status provisional : {n} valeurs historiques passées en provisoire.")
        text = build(wb, findings, errors, log, site, today)
        write(Path(opts["report"]), text)
        self.stdout.write(self.style.SUCCESS(
            f"Import terminé : {dict(log.counts)} — {len(findings)} constats, {len(log.skipped)} lignes ignorées, "
            f"{len(log.flagged)} signalements. Rapport : {opts['report']}"))
