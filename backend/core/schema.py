"""Serializers used only to describe the API in the OpenAPI schema (docs/reference/openapi.yaml).

They document the JSON shapes of function views (login, sync, KPI…) that are
built by hand rather than by a ModelSerializer. Keep them in sync with the views.
"""
from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class MeSerializer(serializers.Serializer):
    username = serializers.CharField()
    full_name = serializers.CharField()
    role = serializers.CharField(allow_null=True, help_text="Code du rôle (RESP_TECH, ZONE_TECH, …)")
    role_label = serializers.CharField()
    zone = serializers.CharField(allow_null=True)
    site = serializers.CharField(allow_null=True)
    is_superuser = serializers.BooleanField()


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="À envoyer ensuite dans l'en-tête `Authorization: Token <jeton>`")
    me = MeSerializer()


class SyncItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Identifiant généré par le téléphone ; renvoyer le même id ne crée jamais de doublon")
    form_type = serializers.ChoiceField(choices=["POMPAGE", "STOCKAGE", "RESEAU_BF", "PANNE", "MP_POMPE", "MP_RESERVOIR", "MP_RESEAU"])
    payload = serializers.JSONField(help_text="Contenu de la fiche, structuré selon shared/forms.fr.json")
    base_version = serializers.IntegerField(required=False, allow_null=True,
                                            help_text="Version serveur sur laquelle la modification est basée (absente pour une création)")
    client_updated_at = serializers.DateTimeField(required=False)


class SyncPushRequestSerializer(serializers.Serializer):
    items = SyncItemSerializer(many=True, help_text="100 fiches au plus par appel")


class ServerSubmissionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    form_type = serializers.CharField()
    date = serializers.DateField()
    payload = serializers.JSONField()
    version = serializers.IntegerField()
    status = serializers.CharField()
    updated_at = serializers.DateTimeField()
    submitted_by = serializers.CharField(allow_null=True)


class FieldErrorSerializer(serializers.Serializer):
    field = serializers.CharField(help_text="Chemin du champ, ex. `pumps[0].flow_m3h`")
    message = serializers.CharField()


class SyncResultSerializer(serializers.Serializer):
    id = serializers.CharField()
    status = serializers.ChoiceField(
        choices=["created", "updated", "unchanged", "conflict", "locked", "invalid", "forbidden", "error", "retry"],
        help_text="created/updated/unchanged = accepté ; conflict/locked = version serveur renvoyée dans `server` ; "
                  "invalid/forbidden/error = à corriger par l'utilisateur ; retry = erreur passagère, renvoyer plus tard")
    version = serializers.IntegerField(required=False)
    server = ServerSubmissionSerializer(required=False)
    errors = FieldErrorSerializer(many=True, required=False)


class SyncPushResponseSerializer(serializers.Serializer):
    results = SyncResultSerializer(many=True)
    server_time = serializers.DateTimeField()


class SyncPullResponseSerializer(serializers.Serializer):
    submissions = ServerSubmissionSerializer(many=True)
    server_time = serializers.DateTimeField()


class KpiMonthSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    label = serializers.CharField()
    status = serializers.ChoiceField(choices=["closed", "current", "future"])
    has_data = serializers.BooleanField()
    coverage = serializers.DictField(help_text="`pump_reading_days` / `days` du mois")
    sources = serializers.DictField(child=serializers.CharField(), help_text="indicateur → `fiches` ou `historique`")
    provisional = serializers.DictField(help_text="Valeurs Excel provisoires, affichées pour comparaison seulement")
    values = serializers.DictField(help_text="indicateur → valeur (null = pas de donnée). Voir docs/reference/kpi.md")


class KpiYearSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    site = serializers.CharField()
    today = serializers.DateField()
    months = KpiMonthSerializer(many=True)
    annual = serializers.DictField(help_text="Totaux et ratios annuels (ratio des sommes)")


class MapAssetSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    type_label = serializers.CharField()
    condition = serializers.CharField()
    lat = serializers.FloatField(allow_null=True)
    lon = serializers.FloatField(allow_null=True)
    flags = serializers.ListField(child=serializers.CharField())


class MapIncidentSerializer(serializers.Serializer):
    number = serializers.CharField()
    status = serializers.CharField()
    status_label = serializers.CharField()
    severity = serializers.CharField()
    severity_label = serializers.CharField()
    type = serializers.CharField()
    date = serializers.DateField()
    lat = serializers.FloatField(allow_null=True)
    lon = serializers.FloatField(allow_null=True)
    asset = serializers.CharField(allow_null=True)
    node = serializers.CharField(allow_null=True)


class MapDataSerializer(serializers.Serializer):
    assets = MapAssetSerializer(many=True)
    incidents = MapIncidentSerializer(many=True)


class OverviewSerializer(serializers.Serializer):
    submissions_to_review = serializers.IntegerField()
    open_incidents = serializers.IntegerField()
    critical_open = serializers.IntegerField()
    history_actual_months = serializers.IntegerField()
    history_provisional_months = serializers.IntegerField()


class StockAlertSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    unit = serializers.CharField()
    balance = serializers.FloatField(allow_null=True)
    min_threshold = serializers.FloatField()
