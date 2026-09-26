from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.api import CodeRelatedField, SiteScopedViewSet, request_site
from core.permissions import DASHBOARD_ROLES, STOCK_ROLES, RolePermission, set_roles

from .models import StockItem, StockMovement, balances


class StockItemSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    alert = serializers.SerializerMethodField()
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = StockItem
        exclude = ["site"]

    def _balance(self, obj):
        cache = self.context.setdefault("_balances", {})
        if "all" not in cache:
            cache["all"] = balances(obj.site)
        return cache["all"].get(obj.id)

    def get_balance(self, obj):
        b = self._balance(obj)
        return float(b) if b is not None else None

    def get_alert(self, obj):
        b = self._balance(obj)
        if obj.min_threshold is None or b is None:
            return None
        return b < obj.min_threshold


class StockMovementSerializer(serializers.ModelSerializer):
    item = CodeRelatedField(queryset=StockItem.objects.all())
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    incident_number = serializers.CharField(source="incident.number", read_only=True, default=None)

    class Meta:
        model = StockMovement
        exclude = ["site"]
        read_only_fields = ["incident", "work_order", "source"]

    def validate(self, attrs):
        if attrs.get("kind") != StockMovement.Kind.ADJUST and attrs.get("quantity") is not None and attrs["quantity"] <= 0:
            raise serializers.ValidationError({"quantity": "La quantité doit être positive."})
        return attrs


class StockItemViewSet(SiteScopedViewSet):
    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer
    write_roles = STOCK_ROLES
    read_roles = DASHBOARD_ROLES
    lookup_field = "code"


class StockMovementViewSet(SiteScopedViewSet):
    queryset = StockMovement.objects.select_related("item", "incident")
    serializer_class = StockMovementSerializer
    write_roles = STOCK_ROLES
    read_roles = DASHBOARD_ROLES

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("item"):
            qs = qs.filter(item__code=self.request.query_params["item"])
        return qs


@api_view(["GET"])
@permission_classes([RolePermission])
def stock_alerts(request):
    site = request_site(request)
    bal = balances(site)
    out = []
    for item in StockItem.objects.filter(site=site, min_threshold__isnull=False):
        b = bal.get(item.id)
        if b is None or b < item.min_threshold:
            out.append({"code": item.code, "name": item.name, "unit": item.unit,
                        "balance": float(b) if b is not None else None, "min_threshold": float(item.min_threshold)})
    return Response(out)


set_roles(stock_alerts, read=DASHBOARD_ROLES)
