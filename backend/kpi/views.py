from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from . import catalog
from .export import csv_text, workbook_bytes
from .models import MonthlyAggregate
from .report_pdf import build_report
from .service import compute_year, to_json
from core import schema as S
from core.api import request_site
from core.models import Asset
from core.permissions import DASHBOARD_ROLES, RolePermission, set_roles
from ops.models import FormSubmission, Incident


def _year(request):
    try:
        return int(request.query_params.get("year") or timezone.localdate().year)
    except ValueError:
        return timezone.localdate().year


@extend_schema(tags=["Indicateurs"], parameters=[OpenApiParameter("year", int, description="Année (par défaut : année en cours)")], responses=S.KpiYearSerializer, summary="KPI mensuels et annuels")
@api_view(["GET"])
@permission_classes([RolePermission])
def kpis(request):
    site = request_site(request)
    return Response({**to_json(compute_year(site, _year(request))), "catalog": catalog.as_json()})


@extend_schema(tags=["Indicateurs"], parameters=[
    OpenApiParameter("year", int, description="Année (par défaut : année en cours)"),
    OpenApiParameter("month", int, description="1 à 12 : rapport du mois seul ; absent : rapport annuel complet"),
], responses={(200, "application/pdf"): OpenApiTypes.BINARY}, summary="Rapport PDF des indicateurs (graphiques inclus)")
@api_view(["GET"])
@permission_classes([RolePermission])
def report_pdf(request):
    site = request_site(request)
    year = _year(request)
    month = request.query_params.get("month")
    try:
        month = int(month) if month else None
    except ValueError:
        month = None
    if month is not None and not 1 <= month <= 12:
        return Response({"detail": "Mois invalide (1 à 12)."}, status=400)
    person = getattr(request.user, "person", None)
    who = (person.full_name if person and person.full_name else request.user.get_username())
    data = build_report(compute_year(site, year), site.name, month=month, generated_by=who)
    suffix = f"{year}-{month:02d}" if month else str(year)
    resp = HttpResponse(data, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="ymejibu_indicateurs_{site.code}_{suffix}.pdf"'
    return resp


@extend_schema(tags=["Indicateurs"], parameters=[OpenApiParameter("year", int, description="Année (par défaut : année en cours)")], responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): OpenApiTypes.BINARY},
               summary="Export XLSX au format de la feuille « O&M KPI »")
@api_view(["GET"])
@permission_classes([RolePermission])
def export_xlsx(request):
    site = request_site(request)
    year = _year(request)
    data = workbook_bytes(compute_year(site, year), site.name)
    resp = HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="ymejibu_KPI_{site.code}_{year}.xlsx"'
    return resp


@extend_schema(tags=["Indicateurs"], parameters=[OpenApiParameter("year", int, description="Année (par défaut : année en cours)")], responses={(200, "text/csv"): OpenApiTypes.STR}, summary="Export CSV (séparateur ;)")
@api_view(["GET"])
@permission_classes([RolePermission])
def export_csv(request):
    site = request_site(request)
    year = _year(request)
    resp = HttpResponse("﻿" + csv_text(compute_year(site, year)), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="ymejibu_KPI_{site.code}_{year}.csv"'
    return resp


def _f(v):
    return float(v) if v is not None else None


@extend_schema(tags=["Tableau de bord"], responses=S.MapDataSerializer, summary="Actifs géolocalisés et pannes récentes",
               parameters=[OpenApiParameter("days", int, description="Pannes des N derniers jours (défaut 90)")])
@api_view(["GET"])
@permission_classes([RolePermission])
def map_data(request):
    site = request_site(request)
    assets = [
        {"code": a.code, "name": a.name, "type": a.type, "type_label": a.get_type_display(),
         "condition": a.get_condition_display(), "lat": _f(a.latitude), "lon": _f(a.longitude),
         "flags": a.flags}
        for a in Asset.objects.filter(site=site, active=True)
    ]
    since = timezone.now() - timezone.timedelta(days=int(request.query_params.get("days", 90)))
    incidents = []
    for i in Incident.objects.filter(site=site, detected_at__gte=since).select_related("asset", "node"):
        lat, lon = i.latitude, i.longitude
        if lat is None and i.asset and i.asset.latitude is not None:
            lat, lon = i.asset.latitude, i.asset.longitude
        incidents.append({"number": i.number, "status": i.status, "status_label": i.get_status_display(),
                          "severity": i.severity, "severity_label": i.get_severity_display(),
                          "type": i.incident_type, "date": i.detected_at.date().isoformat(),
                          "lat": _f(lat), "lon": _f(lon), "asset": i.asset.code if i.asset else None,
                          "node": i.node.code if i.node else None})
    return Response({"assets": assets, "incidents": incidents})


@extend_schema(tags=["Tableau de bord"], responses=S.OverviewSerializer, summary="Compteurs d'en-tête")
@api_view(["GET"])
@permission_classes([RolePermission])
def overview(request):
    """Small counters for the dashboard header (review queue, open incidents, history status)."""
    site = request_site(request)
    return Response({
        "submissions_to_review": FormSubmission.objects.filter(site=site, status=FormSubmission.Status.SUBMITTED).count(),
        "open_incidents": Incident.objects.filter(site=site).exclude(status=Incident.Status.CLOSED).count(),
        "critical_open": Incident.objects.filter(site=site, severity=Incident.Severity.CRITICAL).exclude(
            status=Incident.Status.CLOSED).count(),
        "history_actual_months": MonthlyAggregate.objects.filter(site=site, status="ACTUAL").values("month").distinct().count(),
        "history_provisional_months": MonthlyAggregate.objects.filter(site=site, status="PROVISIONAL").values("month").distinct().count(),
    })


for _view in (kpis, report_pdf, export_xlsx, export_csv, map_data, overview):
    set_roles(_view, read=DASHBOARD_ROLES)
