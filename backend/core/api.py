from rest_framework import serializers, viewsets

from .models import Asset, Fitting, Node, Person, PipeSegment, Site, StaffingNeed, Zone
from .permissions import MANAGERS, user_site  # noqa: F401


def request_site(request):
    """The site the current user works on (superusers may pass ?site=CODE)."""
    code = request.query_params.get("site") if hasattr(request, "query_params") else None
    if request.user.is_superuser:
        qs = Site.objects.all()
        if code:
            qs = qs.filter(code=code)
        return qs.order_by("id").first()
    return user_site(request.user)


class SiteScopedViewSet(viewsets.ModelViewSet):
    """Filters every queryset to the user's site and stamps the site on create."""

    site_field = "site"
    write_roles = MANAGERS

    def get_queryset(self):
        site = request_site(self.request)
        return super().get_queryset().filter(**{self.site_field: site})

    def perform_create(self, serializer):
        if self.site_field == "site":
            serializer.save(site=request_site(self.request))
        else:
            serializer.save()


class CodeRelatedField(serializers.SlugRelatedField):
    """Reference related objects by their stable code, not by database id."""

    def __init__(self, **kwargs):
        kwargs.setdefault("slug_field", "code")
        super().__init__(**kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        request = self.context.get("request")
        if request is not None and any(f.name == "site" for f in qs.model._meta.fields):
            qs = qs.filter(site=request_site(request))
        return qs


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ["id", "code", "name"]


class AssetSerializer(serializers.ModelSerializer):
    parent = CodeRelatedField(queryset=Asset.objects.all(), allow_null=True, required=False)
    zone = CodeRelatedField(queryset=Zone.objects.all(), allow_null=True, required=False)
    node = CodeRelatedField(queryset=Node.objects.all(), allow_null=True, required=False)
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    condition_label = serializers.CharField(source="get_condition_display", read_only=True)

    class Meta:
        model = Asset
        exclude = ["site", "responsible"]


class NodeSerializer(serializers.ModelSerializer):
    zone = CodeRelatedField(queryset=Zone.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Node
        exclude = ["site"]


class PipeSegmentSerializer(serializers.ModelSerializer):
    from_node = CodeRelatedField(queryset=Node.objects.all(), allow_null=True, required=False)
    to_node = CodeRelatedField(queryset=Node.objects.all())

    class Meta:
        model = PipeSegment
        exclude = ["site"]


class FittingSerializer(serializers.ModelSerializer):
    node = CodeRelatedField(queryset=Node.objects.all())

    class Meta:
        model = Fitting
        fields = "__all__"


class PersonSerializer(serializers.ModelSerializer):
    zone = CodeRelatedField(queryset=Zone.objects.all(), allow_null=True, required=False)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = Person
        exclude = ["site", "user"]


class StaffingNeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffingNeed
        exclude = ["site"]


class ZoneViewSet(SiteScopedViewSet):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer


class AssetViewSet(SiteScopedViewSet):
    queryset = Asset.objects.select_related("parent", "zone", "node")
    serializer_class = AssetSerializer
    lookup_field = "code"


class NodeViewSet(SiteScopedViewSet):
    queryset = Node.objects.select_related("zone")
    serializer_class = NodeSerializer


class PipeSegmentViewSet(SiteScopedViewSet):
    queryset = PipeSegment.objects.select_related("from_node", "to_node")
    serializer_class = PipeSegmentSerializer


class FittingViewSet(SiteScopedViewSet):
    queryset = Fitting.objects.select_related("node")
    serializer_class = FittingSerializer
    site_field = "node__site"


class PersonViewSet(SiteScopedViewSet):
    queryset = Person.objects.select_related("zone", "user")
    serializer_class = PersonSerializer
    read_roles = MANAGERS


class StaffingNeedViewSet(SiteScopedViewSet):
    queryset = StaffingNeed.objects.all()
    serializer_class = StaffingNeedSerializer
    read_roles = MANAGERS
