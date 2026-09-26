"""Create PLANNED preventive work orders for one month from the annual action plan.

A task becomes work orders when it has scheduled dates in that month and its
section/title maps to a maintenance category. Idempotent: one work order per
task and date. Preventive checklists filled on the phone then close them,
which is what the 'Taux de maintenance préventive' KPI measures.
"""
import datetime as dt
import re

from django.core.management.base import BaseCommand

from core.models import Site
from ops.models import WorkOrder
from plan.models import ActionPlanTask

RULES = [
    (r"r[ée]servoir|stockage|nyabyunyu|mudja|cajed", WorkOrder.Category.RESERVOIR),
    (r"pompage|pompe|bosco", WorkOrder.Category.POMPAGE),
    (r"captage|source|prise", WorkOrder.Category.CAPTAGE),
    (r"borne|\bbf\b|kiosque", WorkOrder.Category.BF),
    (r"r[ée]seau|conduite|vanne", WorkOrder.Category.RESEAU),
]
EXCLUDE = re.compile(r"exploitation journali|tests? laboratoire", re.I)


def category_for(task):
    text = f"{task.section} {task.title}"
    if EXCLUDE.search(text):
        return None
    for pat, cat in RULES:
        if re.search(pat, text, re.I):
            return cat
    return None


class Command(BaseCommand):
    help = "Génère les ordres de travail préventifs planifiés d'un mois à partir du plan d'action."

    def add_arguments(self, parser):
        parser.add_argument("--month", required=True, help="AAAA-MM")
        parser.add_argument("--site", default="GO")

    def handle(self, *args, **opts):
        y, m = map(int, opts["month"].split("-"))
        site = Site.objects.get(code=opts["site"])
        created = 0
        for task in ActionPlanTask.objects.filter(site=site, year=y):
            cat = category_for(task)
            if cat is None:
                continue
            for iso in task.scheduled_dates:
                day = dt.date.fromisoformat(iso)
                if day.month != m:
                    continue
                title = f"{task.title} [{task.code or task.pk}] {day:%d/%m}"
                _, was_created = WorkOrder.objects.get_or_create(
                    site=site, plan_task=task, planned_date=day, category=cat,
                    defaults={"title": title[:200], "kind": "PREVENTIVE", "asset": task.asset, "status": WorkOrder.Status.PLANNED})
                created += was_created
        self.stdout.write(self.style.SUCCESS(f"{created} ordre(s) de travail planifié(s) créé(s) pour {opts['month']}."))
