from django.db import models

from core.models import Site


class MonthlyAggregate(models.Model):
    """Monthly totals recorded before the app existed (imported from `O&M KPI`).

    Only rows with status ACTUAL override the values computed from records.
    PROVISIONAL rows are shown for comparison but never used in KPIs.
    Placeholder values (future months) are not imported at all.
    """

    class Status(models.TextChoices):
        ACTUAL = "ACTUAL", "Historique validé (mois clos)"
        PROVISIONAL = "PROVISIONAL", "Provisoire — non utilisé dans les KPI"

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="monthly_aggregates")
    month = models.DateField()
    metric = models.CharField(max_length=60)
    value = models.DecimalField(max_digits=14, decimal_places=4)
    status = models.CharField(max_length=12, choices=Status.choices)
    source_ref = models.CharField(max_length=255, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("site", "month", "metric")]
        ordering = ["site", "month", "metric"]
