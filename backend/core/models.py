"""Reference data: sites, zones, assets, network topology and people.

Every row that came from a workbook keeps `source_ref` ("file!sheet!cell")
so a manager can always trace a value back to the Excel it was imported from.
"""
from django.conf import settings
from django.db import models


class Site(models.Model):
    """A water network operated by Yme Jibu (Goma Ouest is the first one)."""

    code = models.CharField(max_length=10, unique=True)  # e.g. "GO"
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    timezone = models.CharField(max_length=64, default="Africa/Lubumbashi")

    def __str__(self):
        return f"{self.code} — {self.name}"


class Zone(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="zones")
    code = models.CharField(max_length=20)  # "Z1"
    name = models.CharField(max_length=120)

    class Meta:
        unique_together = [("site", "code")]
        ordering = ["site", "code"]

    def __str__(self):
        return f"{self.site.code}-{self.code} {self.name}"


class SourceTracked(models.Model):
    source_ref = models.CharField(max_length=255, blank=True, help_text="Origine Excel : fichier!feuille!cellule")
    raw_label = models.CharField(max_length=255, blank=True, help_text="Libellé d'origine tel que saisi dans Excel")
    flags = models.JSONField(default=list, blank=True, help_text="Anomalies détectées à l'import (codes du rapport qualité)")

    class Meta:
        abstract = True


class AssetType(models.TextChoices):
    INTAKE = "INTAKE", "Captage"
    PUMP = "PUMP", "Groupe motopompe"
    PUMP_STATION = "PUMP_STATION", "Station de pompage"
    CHLORINATION_UNIT = "CHLORINATION_UNIT", "Unité de chloration"
    DOSING_PUMP = "DOSING_PUMP", "Pompe doseuse"
    TANK = "TANK", "Cuve / bac"
    SOLAR_PANEL = "SOLAR_PANEL", "Panneau solaire"
    BATTERY = "BATTERY", "Batterie"
    STORAGE_SITE = "STORAGE_SITE", "Site de stockage"
    RESERVOIR = "RESERVOIR", "Réservoir"
    KIOSK = "KIOSK", "Borne fontaine (kiosque)"
    PRIVATE_CONNECTION = "PRIVATE_CONNECTION", "Connexion privée"
    GENSET = "GENSET", "Groupe électrogène"
    OTHER = "OTHER", "Autre"


# Short codes used to build stable asset IDs: <SITE>-<CODE>-<NNN>
ASSET_TYPE_CODES = {
    AssetType.INTAKE: "CAP",
    AssetType.PUMP: "PMP",
    AssetType.PUMP_STATION: "STP",
    AssetType.CHLORINATION_UNIT: "CHL",
    AssetType.DOSING_PUMP: "DOS",
    AssetType.TANK: "TNK",
    AssetType.SOLAR_PANEL: "SOL",
    AssetType.BATTERY: "BAT",
    AssetType.STORAGE_SITE: "STK",
    AssetType.RESERVOIR: "RES",
    AssetType.KIOSK: "BF",
    AssetType.PRIVATE_CONNECTION: "CP",
    AssetType.GENSET: "GEN",
    AssetType.OTHER: "OTH",
}


class Condition(models.TextChoices):
    GOOD = "GOOD", "Bon"
    FAIR = "FAIR", "Moyen"
    POOR = "POOR", "Mauvais"
    OUT_OF_SERVICE = "OUT_OF_SERVICE", "Hors service"
    UNKNOWN = "UNKNOWN", "Inconnu"


class Asset(SourceTracked):
    """Any physical equipment. Stable, human-readable ID in `code` (GO-PMP-001)."""

    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="assets")
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=30, choices=AssetType.choices)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    node = models.ForeignKey("Node", null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    altitude_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    capacity_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    capacity_unit = models.CharField(max_length=20, blank=True)  # m3/h, m3, l/h, W, kWh
    power_kw = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    head_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    specs = models.TextField(blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.UNKNOWN)
    install_date = models.DateField(null=True, blank=True)
    built_by = models.CharField(max_length=120, blank=True)
    om_documents = models.CharField(max_length=255, blank=True)
    maintenance_frequency_days = models.PositiveIntegerField(null=True, blank=True)
    last_maintenance = models.DateField(null=True, blank=True)
    next_maintenance = models.DateField(null=True, blank=True)
    responsible = models.ForeignKey("Person", null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    attributes = models.JSONField(default=dict, blank=True, help_text="Attributs spécifiques au type (robinets, bénéficiaires, DN de raccordement…)")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class NodeKind(models.TextChoices):
    JUNCTION = "JUNCTION", "Nœud / chambre de vannes"
    SOURCE = "SOURCE", "Source / lac"
    PUMP_STATION = "PUMP_STATION", "Station de pompage"
    RESERVOIR_OUTLET = "RESERVOIR_OUTLET", "Sortie réservoir"
    OUTFALL = "OUTFALL", "Exutoire (trop-plein / vidange)"
    DELIVERY = "DELIVERY", "Point de livraison (BF / CP)"


class Node(SourceTracked):
    """Network node. IDs are ALWAYS strings: "1.10" and "1.1" are different nodes."""

    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="nodes")
    code = models.CharField(max_length=40)
    kind = models.CharField(max_length=20, choices=NodeKind.choices, default=NodeKind.JUNCTION)
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.SET_NULL, related_name="nodes")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.UNKNOWN)
    note = models.TextField(blank=True)

    class Meta:
        unique_together = [("site", "code")]
        ordering = ["site", "code"]

    def __str__(self):
        return f"{self.site.code}:{self.code}"


class PipeRole(models.TextChoices):
    MAIN = "MAIN", "Conduite principale"
    OVERFLOW = "OVERFLOW", "Trop-plein / vidange"
    SERVICE = "SERVICE", "Branchement BF / CP"
    RISING = "RISING", "Refoulement"


class PipeSegment(SourceTracked):
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="pipe_segments")
    code = models.CharField(max_length=60)  # "<from>><to>#DN"
    from_node = models.ForeignKey(Node, null=True, blank=True, on_delete=models.PROTECT, related_name="segments_out")
    to_node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name="segments_in")
    dn = models.PositiveIntegerField(help_text="Diamètre nominal (mm)")
    material = models.CharField(max_length=40, blank=True)
    length_m = models.DecimalField(max_digits=10, decimal_places=2)
    role = models.CharField(max_length=20, choices=PipeRole.choices, default=PipeRole.MAIN)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.UNKNOWN)
    note = models.TextField(blank=True)

    class Meta:
        unique_together = [("site", "code")]
        ordering = ["site", "code"]

    def __str__(self):
        return self.code


class Fitting(SourceTracked):
    """Valves, tees, reducers… counted per node (register sheet 3)."""

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="fittings")
    description = models.CharField(max_length=160)
    dn = models.PositiveIntegerField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.UNKNOWN)
    note = models.TextField(blank=True)

    class Meta:
        unique_together = [("node", "description")]


class Role(models.TextChoices):
    RESP_TECH = "RESP_TECH", "Responsable technique"
    ADJOINT = "ADJOINT", "Responsable technique adjoint (opérations, stock, logistique)"
    ZONE_TECH = "ZONE_TECH", "Technicien de zone"
    PUMP_FOCAL = "PUMP_FOCAL", "Point focal pompage"
    STORAGE_FOCAL = "STORAGE_FOCAL", "Point focal stockage"
    SSE = "SSE", "Responsable SSE"
    DATA_OFFICER = "DATA_OFFICER", "Responsable base de données"
    FUNDER = "FUNDER", "Bailleur (lecture seule)"
    CONTRACTOR = "CONTRACTOR", "Prestataire (non permanent)"


class Person(SourceTracked):
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="people")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="person")
    full_name = models.CharField(max_length=160, blank=True)
    title = models.CharField(max_length=160)
    role = models.CharField(max_length=20, choices=Role.choices)
    duties = models.TextField(blank=True)
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.SET_NULL, related_name="people")
    permanent = models.BooleanField(default=True)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["site", "role", "title"]

    def __str__(self):
        return f"{self.full_name or '(nom à compléter)'} — {self.title}"


class StaffingNeed(SourceTracked):
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="staffing_needs")
    title = models.CharField(max_length=160)
    duties = models.TextField(blank=True)
    headcount = models.PositiveIntegerField(null=True, blank=True)
    permanent = models.BooleanField(null=True, blank=True)
    duration_value = models.PositiveIntegerField(null=True, blank=True)
    duration_unit = models.CharField(max_length=10, default="DAYS", help_text="Unité non précisée dans Excel : à confirmer")
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    comment = models.TextField(blank=True)


class Sequence(models.Model):
    """Gap-tolerant, never-reused counters (incident numbers). Incremented under a row lock."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="sequences")
    name = models.CharField(max_length=40)
    value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("site", "name")]

    @classmethod
    def next(cls, site, name, floor=0):
        from django.db import IntegrityError, transaction

        with transaction.atomic():
            try:
                with transaction.atomic():
                    cls.objects.get_or_create(site=site, name=name, defaults={"value": floor})
            except IntegrityError:
                pass  # created concurrently
            seq = cls.objects.select_for_update().get(site=site, name=name)
            seq.value = max(seq.value, floor) + 1
            seq.save(update_fields=["value"])
            return seq.value
