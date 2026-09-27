import hashlib
import json

from django.contrib.auth import authenticate
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import schema as S
from .api import request_site
from .models import Asset, Node, Zone
from .permissions import RolePermission, user_role
from ops.forms import definitions
from ops.models import QualityThreshold


def _me(user):
    person = getattr(user, "person", None)
    return {
        "username": user.get_username(),
        "full_name": (person.full_name if person else "") or user.get_full_name() or user.get_username(),
        "role": "RESP_TECH" if user.is_superuser and not person else user_role(user),
        "role_label": person.get_role_display() if person else ("Administrateur" if user.is_superuser else ""),
        "zone": person.zone.code if person and person.zone else None,
        "site": person.site.code if person else None,
        "is_superuser": user.is_superuser,
    }


@extend_schema(tags=["Authentification"], request=S.LoginRequestSerializer, responses={200: S.LoginResponseSerializer},
               summary="Se connecter et obtenir un jeton")
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    user = authenticate(username=request.data.get("username"), password=request.data.get("password"))
    if user is None or not user.is_active:
        return Response({"detail": "Identifiant ou mot de passe incorrect."}, status=400)
    if not user.is_superuser and user_role(user) is None:
        return Response({"detail": "Aucun rôle n'est attribué à ce compte."}, status=403)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "me": _me(user)})


@extend_schema(tags=["Authentification"], responses=S.MeSerializer, summary="Utilisateur connecté")
@api_view(["GET"])
@permission_classes([RolePermission])
def me(request):
    return Response(_me(request.user))


def _num(v):
    return float(v) if v is not None else None


@extend_schema(tags=["Synchronisation"], responses={200: OpenApiTypes.OBJECT, 304: None},
               summary="Données de référence pour le travail hors ligne",
               description="Site, zones, actifs, nœuds, articles, seuils de qualité et définitions des formulaires. Envoyer `If-None-Match` avec l'ETag reçu : 304 si rien n'a changé.")
@api_view(["GET"])
@permission_classes([RolePermission])
def reference(request):
    """Everything the phone needs to work offline, with an ETag to skip unchanged downloads."""
    from stock.models import StockItem

    site = request_site(request)
    data = {
        "site": {"code": site.code, "name": site.name},
        "zones": [{"code": z.code, "name": z.name} for z in Zone.objects.filter(site=site)],
        "assets": [
            {"code": a.code, "name": a.name, "type": a.type, "parent": a.parent.code if a.parent else None,
             "zone": a.zone.code if a.zone else None, "lat": _num(a.latitude), "lon": _num(a.longitude),
             "capacity": f"{a.capacity_value:g} {a.capacity_unit}".strip() if a.capacity_value is not None else "",
             "specs": a.specs}
            for a in Asset.objects.filter(site=site, active=True).select_related("parent", "zone")
        ],
        "nodes": [{"code": n.code, "kind": n.kind, "zone": n.zone.code if n.zone else None}
                  for n in Node.objects.filter(site=site).select_related("zone")],
        "stock_items": [{"code": i.code, "name": i.name, "unit": i.unit} for i in StockItem.objects.filter(site=site)],
        "thresholds": [
            {"parameter": t.parameter, "asset_type": t.asset_type, "asset": t.asset.code if t.asset else None,
             "min": _num(t.min_value), "max": _num(t.max_value)}
            for t in QualityThreshold.objects.filter(site=site).select_related("asset")
        ],
        "forms": definitions(),
    }
    body = json.dumps(data, sort_keys=True, ensure_ascii=False)
    etag = '"' + hashlib.sha1(body.encode()).hexdigest()[:16] + '"'
    if request.headers.get("If-None-Match") == etag:
        return Response(status=304, headers={"ETag": etag})
    return Response(data, headers={"ETag": etag})
