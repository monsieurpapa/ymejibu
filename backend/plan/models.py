from django.db import models

from core.models import Asset, Site
from ops.models import MaintenanceType


class Tariff(models.Model):
    """Dated unit prices. The KPI engine uses the tariff valid on the 1st of each month."""

    class Kind(models.TextChoices):
        ELECTRICITY = "ELECTRICITY", "Électricité (USD/kWh)"
        FUEL = "FUEL", "Carburant (USD/L)"

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="tariffs")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    price_usd = models.DecimalField(max_digits=8, decimal_places=4)
    valid_from = models.DateField()
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("site", "kind", "valid_from")]
        ordering = ["site", "kind", "-valid_from"]


class BudgetLine(models.Model):
    class Category(models.TextChoices):
        STAFF = "STAFF", "Besoin en personnel"
        LOGISTICS = "LOGISTICS", "Besoin logistique"
        TOOLS = "TOOLS", "Besoin en outils et équipements"
        MATERIALS = "MATERIALS", "Besoin en matériels et matériaux"
        ENERGY = "ENERGY", "Besoin énergie"
        COMMUNICATION = "COMMUNICATION", "Besoin en communication"
        OTHER = "OTHER", "Autre"

    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="budget_lines")
    month = models.DateField(help_text="1er jour du mois budgété")
    category = models.CharField(max_length=20, choices=Category.choices)
    activity = models.CharField(max_length=200)
    purpose = models.TextField(blank=True)
    maintenance_type = models.CharField(max_length=12, choices=MaintenanceType.choices, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_price_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    responsible = models.CharField(max_length=160, blank=True)
    supplier = models.CharField(max_length=160, blank=True)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)
    flags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["month", "category", "id"]

    @property
    def total_usd(self):
        if self.quantity is None or self.unit_price_usd is None:
            return None
        return self.quantity * self.unit_price_usd


class MonthlyBudget(models.Model):
    """Monthly O&M envelope ('Budget prévu (USD)', O&M KPI row 70)."""

    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="monthly_budgets")
    month = models.DateField()
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("site", "month")]


class ActionPlanTask(models.Model):
    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Journalière"
        WEEKLY = "WEEKLY", "Hebdomadaire"
        MONTHLY = "MONTHLY", "Mensuelle"
        PERIODIC = "PERIODIC", "Trimestrielle / semestrielle / annuelle"

    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="plan_tasks")
    year = models.PositiveIntegerField()
    code = models.CharField(max_length=20, blank=True)
    section = models.CharField(max_length=160, blank=True)
    title = models.CharField(max_length=200)
    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.SET_NULL, related_name="plan_tasks")
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    scheduled_dates = models.JSONField(default=list, blank=True, help_text="Jours cochés dans le calendrier (ISO)")
    progress_pct = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    status_note = models.CharField(max_length=200, blank=True)
    comment = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    source_ref = models.CharField(max_length=255, blank=True)
    flags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["site", "year", "order"]
