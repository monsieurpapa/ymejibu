"""Operational records.

Field forms are stored verbatim as `FormSubmission` (the audit trail, exactly
what the technician typed). Each submission is then *derived* into normalised
records (readings, incidents, work orders, quality tests…) which the KPI
engine reads. Derivation is idempotent: re-deriving a submission replaces
the records linked to it.
"""
import uuid

from django.conf import settings
from django.db import models

from core.models import Asset, Node, Person, Site, Zone


class MaintenanceType(models.TextChoices):
    ROUTINE = "ROUTINE", "Exploitation de routine"
    URGENT = "URGENT", "Maintenance Urgente (MU)"
    CORRECTIVE = "CORRECTIVE", "Maintenance Corrective (MC)"
    PREVENTIVE = "PREVENTIVE", "Maintenance Préventive (MP)"
    SUPPORT = "SUPPORT", "Autres activités de support"


class FailureCause(models.TextChoices):
    """The 11 root causes of failures used in `O&M KPI` rows 18-28 / RESEAU!A32:A42."""

    VANDALISM = "VANDALISM", "Vandalisme et vol"
    OVERPRESSURE = "OVERPRESSURE", "Surpression"
    SHALLOW_PIPE = "SHALLOW_PIPE", "Tuyau mal enfoui"
    ILLEGAL_CONNECTION = "ILLEGAL_CONNECTION", "Connexion illégale"
    MISHANDLING = "MISHANDLING", "Mauvaise manipulation des accessoires par le technicien"
    POOR_PIPE_QUALITY = "POOR_PIPE_QUALITY", "Mauvaise qualité du tuyau"
    POOR_BACKFILL = "POOR_BACKFILL", "Mauvais remblai"
    GROUND_MOVEMENT = "GROUND_MOVEMENT", "Mouvement de terrain"
    POOR_INSTALLATION = "POOR_INSTALLATION", "Mauvaise installation"
    WATER_HAMMER = "WATER_HAMMER", "Coup de bélier"
    FAULTY_CONNECTION = "FAULTY_CONNECTION", "Connexion défectueuse"
    OTHER = "OTHER", "Autre / non déterminée"


class NRWCause(models.TextChoices):
    """The 13 causes of non-revenue water used in `O&M KPI` rows 36-48."""

    PIPE_LEAK = "PIPE_LEAK", "Fuites physiques sur les conduites"
    PIPE_BURST = "PIPE_BURST", "Ruptures de conduites"
    RESERVOIR_OVERFLOW = "RESERVOIR_OVERFLOW", "Débordements de réservoirs (trop-plein)"
    NETWORK_FLUSH = "NETWORK_FLUSH", "Purges du réseau"
    DRAINING = "DRAINING", "Vidanges"
    RESERVOIR_CLEANING = "RESERVOIR_CLEANING", "Eau utilisée pour le nettoyage des réservoirs"
    FIREFIGHTING = "FIREFIGHTING", "Eau utilisée pour la lutte contre les incendies"
    ILLEGAL_BRANCH = "ILLEGAL_BRANCH", "Branchements illégaux"
    FAULTY_METER = "FAULTY_METER", "Compteurs défectueux"
    MISCALIBRATED_METER = "MISCALIBRATED_METER", "Compteurs mal calibrés"
    ILLEGAL_CONNECTION = "ILLEGAL_CONNECTION", "Connexions illégales"
    READING_ERROR = "READING_ERROR", "Erreurs de relevé"
    UNBILLED_CONSUMPTION = "UNBILLED_CONSUMPTION", "Volumes consommés mais non facturés"


class DowntimeCause(models.TextChoices):
    """Availability split used in `O&M KPI` rows 5-8."""

    PUMP_FAILURE = "PUMP_FAILURE", "Panne des pompes"
    PIPE_BURST = "PIPE_BURST", "Rupture des conduites"
    POWER_CUT = "POWER_CUT", "Coupure d'électricité"
    PLANNED_MAINTENANCE = "PLANNED_MAINTENANCE", "Maintenance programmée"
    OTHER = "OTHER", "Autre"


class FormType(models.TextChoices):
    POMPAGE = "POMPAGE", "Fiche journalière — Station de pompage"
    STOCKAGE = "STOCKAGE", "Fiche journalière — Stockage"
    RESEAU_BF = "RESEAU_BF", "Fiche journalière — Réseau et bornes fontaines"
    PANNE = "PANNE", "Rapport de panne / incident"
    MP_POMPE = "MP_POMPE", "Checklist maintenance préventive — Pompe"
    MP_RESERVOIR = "MP_RESERVOIR", "Checklist maintenance préventive — Réservoir"
    MP_RESEAU = "MP_RESEAU", "Checklist maintenance préventive — Réseau"


class RecordSource(models.TextChoices):
    APP = "APP", "Application"
    IMPORT = "IMPORT", "Import Excel"
    ADMIN = "ADMIN", "Saisie bureau"


class Record(models.Model):
    """Common columns for every operational record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="+")
    source = models.CharField(max_length=10, choices=RecordSource.choices, default=RecordSource.APP, help_text="Origine de l'enregistrement")
    source_ref = models.CharField(max_length=255, blank=True, help_text="Origine Excel : fichier!feuille!cellule (import)")
    flags = models.JSONField(default=list, blank=True, help_text="Codes du rapport qualité concernant cet enregistrement")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FormSubmission(Record):
    """A field form exactly as filled on the phone (client-generated UUID)."""

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Soumis"
        VALIDATED = "VALIDATED", "Validé"
        REJECTED = "REJECTED", "Rejeté"

    form_type = models.CharField(max_length=20, choices=FormType.choices)
    date = models.DateField()
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="submissions")
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.PROTECT, related_name="submissions")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions")
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED)
    version = models.PositiveIntegerField(default=1)
    client_updated_at = models.DateTimeField(null=True, blank=True)
    derivation_errors = models.JSONField(default=list, blank=True)
    assigned_number = models.CharField(max_length=30, blank=True, help_text="Numéro d'incident attribué par le serveur (jamais par le téléphone)")
    derived_keys = models.JSONField(default=list, blank=True, help_text="[code actif, date] des relevés alimentés par cette fiche")

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["site", "form_type", "date"])]


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(FormSubmission, null=True, blank=True, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/")
    content_type = models.CharField(max_length=60, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DailyReading(Record):
    """One row per asset per day: pumps, reservoirs, kiosks (volume sold)."""

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="readings")
    date = models.DateField()
    submission = models.ForeignKey(FormSubmission, null=True, blank=True, on_delete=models.CASCADE, related_name="readings")
    operator = models.CharField(max_length=160, blank=True)
    hours_run = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pressure_bar = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pressure_in_bar = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pressure_out_bar = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    flow_m3h = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    current_a = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    volume_m3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Pompe : volume pompé ; BF : volume vendu")
    volume_in_m3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    volume_out_m3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    level_pct = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    kwh = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_l = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    chlorine_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    observations = models.TextField(blank=True)

    class Meta:
        unique_together = [("asset", "date")]
        ordering = ["-date", "asset__code"]


class SafetyCheck(Record):
    """One checked item of a daily or preventive checklist."""

    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="safety_checks")
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="safety_checks")
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    date = models.DateField()
    item = models.CharField(max_length=120)
    ok = models.BooleanField(null=True)
    location = models.CharField(max_length=160, blank=True)
    observation = models.TextField(blank=True)


class Incident(Record):
    class Severity(models.TextChoices):
        LOW = "LOW", "Faible"
        MEDIUM = "MEDIUM", "Moyenne"
        CRITICAL = "CRITICAL", "Critique"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Ouvert"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        CLOSED = "CLOSED", "Réparé / clôturé"

    number = models.CharField(max_length=30, unique=True)
    submission = models.OneToOneField(FormSubmission, null=True, blank=True, on_delete=models.CASCADE, related_name="incident")
    detected_at = models.DateTimeField()
    reported_by = models.CharField(max_length=160, blank=True)
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="incidents")
    node = models.ForeignKey(Node, null=True, blank=True, on_delete=models.PROTECT, related_name="incidents")
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.PROTECT, related_name="incidents")
    location_detail = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    description = models.TextField(blank=True)
    incident_type = models.CharField(max_length=120, blank=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    service_interrupted = models.BooleanField(default=False)
    downtime_cause = models.CharField(max_length=25, choices=DowntimeCause.choices, blank=True)
    downtime_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    affected_zone = models.CharField(max_length=160, blank=True)
    affected_population = models.PositiveIntegerField(null=True, blank=True)
    probable_cause = models.CharField(max_length=25, choices=FailureCause.choices, blank=True)
    root_cause = models.TextField(blank=True)
    nrw_cause = models.CharField(max_length=25, choices=NRWCause.choices, blank=True)
    estimated_loss_m3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    maintenance_type = models.CharField(max_length=12, choices=MaintenanceType.choices, default=MaintenanceType.CORRECTIVE)
    intervention_start = models.DateTimeField(null=True, blank=True)
    intervention_end = models.DateTimeField(null=True, blank=True)
    team = models.TextField(blank=True)
    materials_used = models.TextField(blank=True)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    closed_at = models.DateTimeField(null=True, blank=True)
    verification = models.JSONField(default=dict, blank=True)
    lessons = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-detected_at"]


class WorkOrder(Record):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planifié"
        DONE = "DONE", "Réalisé"
        CANCELLED = "CANCELLED", "Annulé"

    class Category(models.TextChoices):
        CAPTAGE = "CAPTAGE", "Captage"
        POMPAGE = "POMPAGE", "Pompage"
        RESERVOIR = "RESERVOIR", "Réservoir"
        RESEAU = "RESEAU", "Réseau"
        BF = "BF", "Bornes-fontaines"

    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=12, choices=MaintenanceType.choices, default=MaintenanceType.PREVENTIVE)
    category = models.CharField(max_length=12, choices=Category.choices)
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="work_orders")
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.PROTECT, related_name="work_orders")
    planned_date = models.DateField()
    done_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLANNED)
    class Origin(models.TextChoices):
        PLAN = "PLAN", "Plan annuel"
        MANUAL = "MANUAL", "Saisie bureau"
        CHECKLIST = "CHECKLIST", "Créé par une checklist (non planifié)"

    origin = models.CharField(max_length=10, choices=Origin.choices, default=Origin.MANUAL)
    submission = models.ForeignKey(FormSubmission, null=True, blank=True, on_delete=models.SET_NULL, related_name="work_orders",
                                   help_text="Checklist qui a clôturé (ou créé) cet ordre de travail")
    incident = models.ForeignKey(Incident, null=True, blank=True, on_delete=models.SET_NULL, related_name="work_orders")
    plan_task = models.ForeignKey("plan.ActionPlanTask", null=True, blank=True, on_delete=models.SET_NULL, related_name="work_orders")
    downtime_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    findings = models.JSONField(default=list, blank=True, help_text="Besoins de maintenance relevés (partie, matériel, MO, coût, échéance)")

    class Meta:
        ordering = ["-planned_date"]


class QualityParameter(models.TextChoices):
    RESIDUAL_CHLORINE = "RESIDUAL_CHLORINE", "Chlore résiduel (mg/L)"
    TURBIDITY = "TURBIDITY", "Turbidité (NTU)"
    ODOUR_COLOUR = "ODOUR_COLOUR", "Odeur/couleur anormale"
    LAB = "LAB", "Test laboratoire"


class QualityThreshold(models.Model):
    """Configurable acceptable range per parameter and sampling point type (or asset)."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="quality_thresholds")
    parameter = models.CharField(max_length=20, choices=QualityParameter.choices)
    asset_type = models.CharField(max_length=30, blank=True, help_text="Vide = tous les points")
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.CASCADE)
    min_value = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    max_value = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    to_confirm = models.BooleanField(default=True, help_text="Valeur par défaut à valider par le Responsable technique")


class WaterQualityTest(Record):
    submission = models.ForeignKey(FormSubmission, null=True, blank=True, on_delete=models.CASCADE, related_name="quality_tests")
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="quality_tests")
    date = models.DateField()
    parameter = models.CharField(max_length=20, choices=QualityParameter.choices)
    value = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    compliant = models.BooleanField(null=True)
    is_lab = models.BooleanField(default=False)
    corrective_action = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]


class Complaint(Record):
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="complaints")
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    date = models.DateField()
    nature = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    action_taken = models.TextField(blank=True)


class Expense(Record):
    """Actual O&M spending — the single source for 'Dépense réelle' by maintenance type."""

    date = models.DateField()
    maintenance_type = models.CharField(max_length=12, choices=MaintenanceType.choices)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    incident = models.OneToOneField(Incident, null=True, blank=True, on_delete=models.CASCADE, related_name="expense")
    work_order = models.OneToOneField(WorkOrder, null=True, blank=True, on_delete=models.CASCADE, related_name="expense")

    class Meta:
        ordering = ["-date"]
