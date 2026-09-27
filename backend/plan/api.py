from rest_framework import serializers

from .models import ActionPlanTask, BudgetLine, MonthlyBudget, Tariff
from core.api import CodeRelatedField, SiteScopedViewSet
from core.models import Asset
from core.permissions import DASHBOARD_ROLES


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        exclude = ["site"]


class BudgetLineSerializer(serializers.ModelSerializer):
    total_usd = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    maintenance_type_label = serializers.CharField(source="get_maintenance_type_display", read_only=True)

    class Meta:
        model = BudgetLine
        exclude = ["site"]


class MonthlyBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyBudget
        exclude = ["site"]


class ActionPlanTaskSerializer(serializers.ModelSerializer):
    asset = CodeRelatedField(queryset=Asset.objects.all(), allow_null=True, required=False)
    frequency_label = serializers.CharField(source="get_frequency_display", read_only=True)

    class Meta:
        model = ActionPlanTask
        exclude = ["site"]


class TariffViewSet(SiteScopedViewSet):
    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer
    read_roles = DASHBOARD_ROLES


class BudgetLineViewSet(SiteScopedViewSet):
    queryset = BudgetLine.objects.all()
    serializer_class = BudgetLineSerializer
    read_roles = DASHBOARD_ROLES

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("month"):  # YYYY-MM
            y, m = self.request.query_params["month"].split("-")
            qs = qs.filter(month__year=y, month__month=m)
        return qs


class MonthlyBudgetViewSet(SiteScopedViewSet):
    queryset = MonthlyBudget.objects.all()
    serializer_class = MonthlyBudgetSerializer
    read_roles = DASHBOARD_ROLES


class ActionPlanTaskViewSet(SiteScopedViewSet):
    queryset = ActionPlanTask.objects.select_related("asset")
    serializer_class = ActionPlanTaskSerializer
    read_roles = DASHBOARD_ROLES

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("year"):
            qs = qs.filter(year=self.request.query_params["year"])
        return qs
