import base64
import binascii
import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from core.api import CodeRelatedField, SiteScopedViewSet, request_site
from core.models import Asset, Node, Zone
from core.permissions import ALL_ROLES, FIELD_ROLES, MANAGERS, RolePermission, user_role

from .derive import derive
from .forms import definitions, form_def, to_date, validate_payload
from .models import (
    Attachment,
    Complaint,
    DailyReading,
    Expense,
    FormSubmission,
    Incident,
    QualityThreshold,
    SafetyCheck,
    WaterQualityTest,
    WorkOrder,
)

MAX_PHOTOS = 3
MAX_PHOTO_BYTES = 1_500_000


class FormSubmissionSerializer(serializers.ModelSerializer):
    asset = CodeRelatedField(queryset=Asset.objects.all(), allow_null=True, required=False)
    zone = CodeRelatedField(queryset=Zone.objects.all(), allow_null=True, required=False)
    submitted_by_name = serializers.SerializerMethodField()
    form_label = serializers.CharField(source="get_form_type_display", read_only=True)

    class Meta:
        model = FormSubmission
        exclude = ["site"]
        read_only_fields = ["version", "source", "submitted_by", "derivation_errors", "form_type", "date", "payload"]

    def get_submitted_by_name(self, obj):
        u = obj.submitted_by
        if not u:
            return ""
        person = getattr(u, "person", None)
        return (person.full_name if person and person.full_name else u.get_username())


class DailyReadingSerializer(serializers.ModelSerializer):
    asset = CodeRelatedField(queryset=Asset.objects.all())

    class Meta:
        model = DailyReading
        exclude = ["site"]


class IncidentSerializer(serializers.ModelSerializer):
    asset = CodeRelatedField(queryset=Asset.objects.all(), allow_null=True, required=False)
    node = CodeRelatedField(queryset=Node.objects.all(), allow_null=True, required=False)
    zone = CodeRelatedField(queryset=Zone.objects.all(), allow_null=True, required=False)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    cause_label = serializers.CharField(source="get_probable_cause_display", read_only=True)
    photos = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        exclude = ["site"]

    def get_photos(self, obj):
        if not obj.submission_id:
            return []
        return [a.file.url for a in obj.submission.attachments.all()]


class WorkOrderSerializer(serializers.ModelSerializer):
    asset = CodeRelatedField(queryset=Asset.objects.all(), allow_null=True, required=False)
    zone = CodeRelatedField(queryset=Zone.objects.all(), allow_null=True, required=False)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = WorkOrder
        exclude = ["site"]
        read_only_fields = ["submission"]


class WaterQualityTestSerializer(serializers.ModelSerializer):
    asset = CodeRelatedField(queryset=Asset.objects.all(), allow_null=True, required=False)

    class Meta:
        model = WaterQualityTest
        exclude = ["site"]


class QualityThresholdSerializer(serializers.ModelSerializer):
    asset = CodeRelatedField(queryset=Asset.objects.all(), allow_null=True, required=False)

    class Meta:
        model = QualityThreshold
        exclude = ["site"]


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        exclude = ["site"]


class SafetyCheckSerializer(serializers.ModelSerializer):
    asset = CodeRelatedField(queryset=Asset.objects.all(), allow_null=True, required=False)

    class Meta:
        model = SafetyCheck
        exclude = ["site"]


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        exclude = ["site"]


class SubmissionViewSet(SiteScopedViewSet):
    """Managers review submissions; status changes trigger re-derivation."""

    queryset = FormSubmission.objects.select_related("asset", "zone", "submitted_by")
    serializer_class = FormSubmissionSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("form_type"):
            qs = qs.filter(form_type=p["form_type"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if user_role(self.request.user) not in MANAGERS and not self.request.user.is_superuser:
            qs = qs.filter(submitted_by=self.request.user)
        return qs[: int(p.get("limit", 200))] if self.action == "list" else qs

    def perform_update(self, serializer):
        sub = serializer.save()
        derive(sub)


class ReadingViewSet(SiteScopedViewSet):
    queryset = DailyReading.objects.select_related("asset")
    serializer_class = DailyReadingSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("month"):  # YYYY-MM
            y, m = p["month"].split("-")
            qs = qs.filter(date__year=y, date__month=m)
        if p.get("asset"):
            qs = qs.filter(asset__code=p["asset"])
        return qs


class IncidentViewSet(SiteScopedViewSet):
    queryset = Incident.objects.select_related("asset", "node", "zone", "submission").prefetch_related("submission__attachments")
    serializer_class = IncidentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("year"):
            qs = qs.filter(detected_at__year=p["year"])
        return qs


class WorkOrderViewSet(SiteScopedViewSet):
    queryset = WorkOrder.objects.select_related("asset", "zone")
    serializer_class = WorkOrderSerializer


class QualityTestViewSet(SiteScopedViewSet):
    queryset = WaterQualityTest.objects.select_related("asset")
    serializer_class = WaterQualityTestSerializer


class QualityThresholdViewSet(SiteScopedViewSet):
    queryset = QualityThreshold.objects.select_related("asset")
    serializer_class = QualityThresholdSerializer


class ExpenseViewSet(SiteScopedViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


# ------------------------------------------------------------------ sync

def _store_photos(submission, payload):
    """Replace base64 photos in the payload with stored attachment references."""
    desc = payload.get("description") or {}
    photos = desc.get("photos") or []
    stored = []
    for photo in photos[:MAX_PHOTOS]:
        if isinstance(photo, dict) and photo.get("attachment"):
            stored.append(photo)
            continue
        if not isinstance(photo, str) or not photo.startswith("data:image/"):
            continue
        header, _, data = photo.partition(",")
        ext = "png" if "png" in header else "jpg"
        try:
            raw = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError):
            continue
        if len(raw) > MAX_PHOTO_BYTES:
            continue
        att = Attachment(submission=submission, content_type=header[5:].split(";")[0])
        att.file.save(f"{uuid.uuid4()}.{ext}", ContentFile(raw), save=True)
        stored.append({"attachment": str(att.id), "url": att.file.url})
    if photos:
        desc["photos"] = stored
        payload["description"] = desc
    return payload


def _serialize_sub(sub):
    return {
        "id": str(sub.id),
        "form_type": sub.form_type,
        "date": sub.date.isoformat(),
        "payload": sub.payload,
        "version": sub.version,
        "status": sub.status,
        "updated_at": sub.updated_at.isoformat(),
        "submitted_by": sub.submitted_by.get_username() if sub.submitted_by else None,
    }


def _scope(site, form, payload):
    asset = zone = None
    scope = form.get("scope") or {}
    if scope.get("asset_field"):
        sec, _, key = scope["asset_field"].partition(".")
        code = (payload.get(sec) or {}).get(key)
        asset = Asset.objects.filter(site=site, code=code).first() if code else None
    if scope.get("zone_field"):
        sec, _, key = scope["zone_field"].partition(".")
        code = (payload.get(sec) or {}).get(key)
        zone = Zone.objects.filter(site=site, code=code).first() if code else None
    if zone is None and asset is not None:
        zone = asset.zone
    return asset, zone


def push_one(request, site, item):
    role = user_role(request.user)
    is_manager = request.user.is_superuser or role in MANAGERS
    try:
        sub_id = uuid.UUID(str(item.get("id")))
        form = form_def(item.get("form_type"))
    except (ValueError, KeyError, TypeError):
        return {"id": item.get("id"), "status": "invalid", "errors": [{"field": "", "message": "Identifiant ou type de formulaire invalide"}]}
    if not request.user.is_superuser and role not in form["roles"]:
        return {"id": str(sub_id), "status": "forbidden", "errors": [{"field": "", "message": "Votre rôle ne permet pas ce formulaire"}]}
    payload = item.get("payload") or {}
    errors = validate_payload(site, form["type"], payload)
    if errors:
        return {"id": str(sub_id), "status": "invalid", "errors": errors}
    date = to_date((payload.get("general") or {}).get("date"))
    asset, zone = _scope(site, form, payload)
    client_ts = parse_datetime(item["client_updated_at"]) if item.get("client_updated_at") else None

    with transaction.atomic():
        existing = FormSubmission.objects.select_for_update().filter(pk=sub_id).first()
        if existing is None:
            sub = FormSubmission(id=sub_id, site=site, form_type=form["type"], submitted_by=request.user, version=1)
            result = "created"
        else:
            if existing.site_id != site.id or existing.form_type != form["type"]:
                return {"id": str(sub_id), "status": "invalid", "errors": [{"field": "", "message": "Identifiant déjà utilisé"}]}
            if not is_manager and existing.submitted_by_id != request.user.id:
                return {"id": str(sub_id), "status": "forbidden", "errors": [{"field": "", "message": "Fiche d'un autre agent"}]}
            if existing.status == FormSubmission.Status.VALIDATED and not is_manager:
                return {"id": str(sub_id), "status": "locked", "server": _serialize_sub(existing)}
            base = item.get("base_version")
            if base != existing.version and not item.get("force"):
                if existing.payload == payload:
                    return {"id": str(sub_id), "status": "unchanged", "version": existing.version, "server": _serialize_sub(existing)}
                return {"id": str(sub_id), "status": "conflict", "server": _serialize_sub(existing)}
            sub = existing
            sub.version = existing.version + 1
            result = "updated"
        sub.date = date
        sub.asset = asset
        sub.zone = zone
        sub.client_updated_at = client_ts
        sub.payload = payload
        sub.save()
        sub.payload = _store_photos(sub, sub.payload)
        sub.save(update_fields=["payload"])
        derive(sub)
        sub.refresh_from_db()
    return {"id": str(sub.id), "status": result, "version": sub.version, "server": _serialize_sub(sub)}


@api_view(["POST"])
@permission_classes([RolePermission])
def sync_push(request):
    """Upload queued submissions. Each item is processed independently."""
    site = request_site(request)
    items = request.data.get("items") or []
    return Response({"results": [push_one(request, site, it) for it in items[:100]], "server_time": timezone.now().isoformat()})


sync_push.cls.write_roles = FIELD_ROLES
sync_push.cls.read_roles = ALL_ROLES


@api_view(["GET"])
@permission_classes([RolePermission])
def sync_pull(request):
    """Submissions of this user changed since `since` (managers may review them on the server)."""
    site = request_site(request)
    qs = FormSubmission.objects.filter(site=site, submitted_by=request.user)
    since = request.query_params.get("since")
    if since:
        ts = parse_datetime(since)
        if ts:
            qs = qs.filter(updated_at__gt=ts)
    else:
        qs = qs.filter(date__gte=timezone.localdate() - timezone.timedelta(days=30))
    return Response({"submissions": [_serialize_sub(s) for s in qs.order_by("updated_at")[:500]],
                     "server_time": timezone.now().isoformat()})


@api_view(["GET"])
@permission_classes([RolePermission])
def forms_definitions(request):
    return Response(definitions())
