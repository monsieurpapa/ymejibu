"""Stock as a ledger: the balance is always the sum of movements, never a typed number."""
from decimal import Decimal

from django.db import models
from django.db.models import Sum

from core.models import Site
from ops.models import Incident, Record, WorkOrder


class StockCategory(models.TextChoices):
    PERFORMANCE = "PERFORMANCE", "Équipement pour l'amélioration des performances"
    OM_TOOLS = "OM_TOOLS", "Outils, matériel et pièces de rechange E&M"
    PPE = "PPE", "Équipements de protection individuelle"
    LOGISTICS = "LOGISTICS", "Logistique et déplacement"
    CHEMICAL = "CHEMICAL", "Produits chimiques de traitement"


class StockItem(models.Model):
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="stock_items")
    code = models.CharField(max_length=30, unique=True)
    category = models.CharField(max_length=20, choices=StockCategory.choices)
    group = models.CharField(max_length=160, blank=True, help_text="Sous-rubrique Excel (ex. « 1. Distribution - Tuyaux »)")
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=30, blank=True)
    rented = models.BooleanField(null=True, blank=True)
    min_threshold = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    monthly_requirement = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    additional_need = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    source_ref = models.CharField(max_length=255, blank=True)
    flags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["category", "code"]

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def balance(self):
        total = Decimal(0)
        for m in self.movements.all():
            total += m.signed_quantity
        return total


class StockMovement(Record):
    class Kind(models.TextChoices):
        OPENING = "OPENING", "Stock initial"
        IN = "IN", "Entrée"
        OUT = "OUT", "Sortie"
        ADJUST = "ADJUST", "Ajustement d'inventaire"

    item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="movements")
    date = models.DateField()
    kind = models.CharField(max_length=10, choices=Kind.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, help_text="Toujours positive sauf pour ADJUST")
    incident = models.ForeignKey(Incident, null=True, blank=True, on_delete=models.CASCADE, related_name="stock_movements")
    work_order = models.ForeignKey(WorkOrder, null=True, blank=True, on_delete=models.CASCADE, related_name="stock_movements")
    reference = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    @property
    def signed_quantity(self):
        return -self.quantity if self.kind == self.Kind.OUT else self.quantity


def balances(site):
    """{item_id: balance} computed in the database (used by alerts and the API)."""
    out = {}
    for kind, sign in (("OPENING", 1), ("IN", 1), ("ADJUST", 1), ("OUT", -1)):
        rows = StockMovement.objects.filter(item__site=site, kind=kind).values("item_id").annotate(q=Sum("quantity"))
        for r in rows:
            out[r["item_id"]] = out.get(r["item_id"], Decimal(0)) + sign * r["q"]
    return out
