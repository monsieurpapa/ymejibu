from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter

from core import api as core_api
from core import views as core_views
from kpi import views as kpi_views
from ops import api as ops_api
from plan import api as plan_api
from stock import api as stock_api

router = DefaultRouter(trailing_slash=True)
router.register("zones", core_api.ZoneViewSet)
router.register("assets", core_api.AssetViewSet)
router.register("nodes", core_api.NodeViewSet)
router.register("segments", core_api.PipeSegmentViewSet)
router.register("fittings", core_api.FittingViewSet)
router.register("people", core_api.PersonViewSet)
router.register("staffing-needs", core_api.StaffingNeedViewSet)
router.register("submissions", ops_api.SubmissionViewSet)
router.register("readings", ops_api.ReadingViewSet)
router.register("incidents", ops_api.IncidentViewSet)
router.register("work-orders", ops_api.WorkOrderViewSet)
router.register("quality-tests", ops_api.QualityTestViewSet)
router.register("quality-thresholds", ops_api.QualityThresholdViewSet)
router.register("expenses", ops_api.ExpenseViewSet)
router.register("stock/items", stock_api.StockItemViewSet)
router.register("stock/movements", stock_api.StockMovementViewSet)
router.register("plan/tariffs", plan_api.TariffViewSet)
router.register("plan/budget-lines", plan_api.BudgetLineViewSet)
router.register("plan/monthly-budgets", plan_api.MonthlyBudgetViewSet)
router.register("plan/tasks", plan_api.ActionPlanTaskViewSet)


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=[AllowAny]), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema", permission_classes=[AllowAny]), name="redoc"),
    path("api/auth/login/", core_views.login),
    path("api/me/", core_views.me),
    path("api/reference/", core_views.reference),
    path("api/forms/", ops_api.forms_definitions),
    path("api/sync/push/", ops_api.sync_push),
    path("api/sync/pull/", ops_api.sync_pull),
    path("api/kpi/", kpi_views.kpis),
    path("api/kpi/export.xlsx", kpi_views.export_xlsx),
    path("api/kpi/export.csv", kpi_views.export_csv),
    path("api/dashboard/map/", kpi_views.map_data),
    path("api/dashboard/overview/", kpi_views.overview),
    path("api/stock/alerts/", stock_api.stock_alerts),
    path("api/", include(router.urls)),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
