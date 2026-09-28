"""User administration for super administrators (CRUD, roles, access levels, passwords).

An *account* is a Django user plus its Person record (site, role, zone). Three
levels of access exist:

* **Super administrateur** (`is_superuser`): everything, including this API;
* **Rôle** (Person.role): what the person may read and change (see ROLE_CAPABILITIES);
* **Compte actif** (`is_active`): an inactive account cannot sign in; its history is kept.

Safety rules: a super administrator cannot delete, deactivate or demote
themselves, and the last active super administrator can never be removed.
Changing a password or deactivating an account revokes its API token, which
signs the person out of every phone.
"""
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .api import request_site
from .models import Person, Role, Zone
from .permissions import DASHBOARD_ROLES, MANAGERS, STOCK_ROLES
from ops.forms import definitions

User = get_user_model()


class IsSuperAdmin(BasePermission):
    message = "Réservé aux super administrateurs."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


def role_capabilities():
    """What each role may do, derived from the same rules the API enforces (no second source of truth)."""
    forms = definitions()["forms"]
    out = []
    for value, label in Role.choices:
        out.append({
            "value": value,
            "label": label,
            "forms": [f["title"] for f in forms if value in f["roles"]],
            "dashboard": value in DASHBOARD_ROLES,
            "validate_sheets": value in MANAGERS,
            "manage_reference": value in MANAGERS,
            "stock_write": value in STOCK_ROLES,
            "read_only": value == Role.FUNDER,
            "zone_scoped": value == Role.ZONE_TECH,
        })
    return out


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.RegexField(r"^[\w.@+-]+$", max_length=150,
                                      error_messages={"invalid": "Lettres, chiffres et . @ + - _ uniquement, sans espace."})
    email = serializers.EmailField(required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    title = serializers.CharField(max_length=160, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=Role.choices, required=False, allow_null=True)
    role_label = serializers.CharField(read_only=True)
    zone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(default=True)
    is_superuser = serializers.BooleanField(default=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    person_id = serializers.IntegerField(required=False, allow_null=True,
                                         help_text="Lier le compte à une fiche du personnel existante (import Excel)")
    last_login = serializers.DateTimeField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    # --- representation -------------------------------------------------------------------
    def to_representation(self, user):
        person = getattr(user, "person", None)
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": (person.full_name if person else "") or user.get_full_name(),
            "title": person.title if person else "",
            "role": person.role if person else None,
            "role_label": person.get_role_display() if person else ("Super administrateur" if user.is_superuser else ""),
            "zone": person.zone.code if person and person.zone else None,
            "zone_name": person.zone.name if person and person.zone else None,
            "person_id": person.id if person else None,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "last_login": user.last_login,
            "date_joined": user.date_joined,
        }

    # --- validation ------------------------------------------------------------------------
    def validate_username(self, value):
        qs = User.objects.filter(username__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Cet identifiant est déjà utilisé.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        site = self.context["site"]
        creating = self.instance is None
        is_superuser = attrs.get("is_superuser", self.instance.is_superuser if self.instance else False)
        person = getattr(self.instance, "person", None) if self.instance else None

        zone_code = attrs.get("zone")
        if zone_code:
            zone = Zone.objects.filter(site=site, code=zone_code).first()
            if not zone:
                raise serializers.ValidationError({"zone": "Zone inconnue pour ce site."})
            attrs["zone"] = zone
        elif "zone" in attrs:
            attrs["zone"] = None

        pid = attrs.get("person_id")
        if pid:
            linked = Person.objects.filter(pk=pid, site=site).first()
            if not linked:
                raise serializers.ValidationError({"person_id": "Fiche du personnel introuvable."})
            if linked.user_id and (creating or linked.user_id != self.instance.pk):
                raise serializers.ValidationError({"person_id": "Cette fiche est déjà liée à un autre compte."})
            attrs["person"] = linked
            person = linked

        role = attrs.get("role") or (person.role if person else None)
        if not role and not is_superuser:
            raise serializers.ValidationError({"role": "Choisir un rôle (ou cocher « Super administrateur »)."})

        password = attrs.get("password") or ""
        if creating and not password:
            raise serializers.ValidationError({"password": "Mot de passe obligatoire pour un nouveau compte."})
        if password:
            probe = self.instance or User(username=attrs.get("username", ""), email=attrs.get("email", ""))
            try:
                password_validation.validate_password(password, probe)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)})

        if self.instance is not None and self.instance.pk == request.user.pk:
            if attrs.get("is_active") is False:
                raise serializers.ValidationError({"is_active": "Vous ne pouvez pas désactiver votre propre compte."})
            if attrs.get("is_superuser") is False:
                raise serializers.ValidationError({"is_superuser": "Vous ne pouvez pas retirer vos propres droits de super administrateur."})
        if self.instance is not None and self.instance.is_superuser and (
            attrs.get("is_superuser") is False or attrs.get("is_active") is False
        ) and last_active_superuser(self.instance):
            raise serializers.ValidationError({"is_superuser": "Il doit rester au moins un super administrateur actif."})
        return attrs

    # --- persistence -----------------------------------------------------------------------
    @transaction.atomic
    def create(self, data):
        user = User(username=data["username"], email=data.get("email", ""),
                    is_active=data.get("is_active", True), is_superuser=data.get("is_superuser", False))
        user.is_staff = user.is_superuser  # Django /admin/ is reserved to super administrators
        user.set_password(data["password"])
        user.save()
        self._save_person(user, data)
        return user

    @transaction.atomic
    def update(self, user, data):
        was_active = user.is_active
        for field in ("username", "email", "is_active", "is_superuser"):
            if field in data:
                setattr(user, field, data[field])
        user.is_staff = user.is_superuser
        password_changed = bool(data.get("password"))
        if password_changed:
            user.set_password(data["password"])
        user.save()
        self._save_person(user, data)
        if password_changed or (was_active and not user.is_active):
            Token.objects.filter(user=user).delete()  # sign out everywhere
        return user

    def _save_person(self, user, data):
        site = self.context["site"]
        person = data.get("person") or getattr(user, "person", None)
        if person is None:
            if not data.get("role"):
                return  # super administrator without an operational role
            person = Person(site=site, user=user, role=data["role"], title=data.get("title") or Role(data["role"]).label)
        elif person.user_id is None:
            person.user = user
        if "full_name" in data:
            person.full_name = data["full_name"]
        if data.get("title"):
            person.title = data["title"]
        if data.get("role"):
            person.role = data["role"]
        if "zone" in data:
            person.zone = data["zone"]
        if "is_active" in data:
            person.active = data["is_active"]
        if not person.title:
            person.title = person.get_role_display()
        person.save()


def last_active_superuser(user):
    return not User.objects.filter(is_superuser=True, is_active=True).exclude(pk=user.pk).exists()


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False)


@extend_schema(tags=["Utilisateurs"])
class AccountViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                     mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Comptes utilisateurs du site (super administrateurs uniquement)."""

    permission_classes = [IsSuperAdmin]
    serializer_class = AccountSerializer

    def get_queryset(self):
        site = request_site(self.request)
        # Accounts of this site, plus super administrators without a staff record.
        return (User.objects.filter(person__site=site) | User.objects.filter(is_superuser=True, person__isnull=True)) \
            .select_related("person__zone").distinct().order_by("-is_active", "username")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "site": request_site(self.request)}

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({"detail": "Vous ne pouvez pas supprimer votre propre compte."}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser and user.is_active and last_active_superuser(user):
            return Response({"detail": "Il doit rester au moins un super administrateur actif."}, status=status.HTTP_400_BAD_REQUEST)
        # The staff record (Person) is kept, unlinked: it still documents the position and history.
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=PasswordSerializer, responses={204: None}, summary="Définir un nouveau mot de passe")
    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        user = self.get_object()
        ser = PasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            password_validation.validate_password(ser.validated_data["password"], user)
        except DjangoValidationError as exc:
            return Response({"password": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(ser.validated_data["password"])
        user.save(update_fields=["password"])
        Token.objects.filter(user=user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="Rôles, droits associés, zones et fiches du personnel sans compte")
    @action(detail=False, methods=["get"])
    def options(self, request):
        site = request_site(request)
        return Response({
            "roles": role_capabilities(),
            "zones": [{"code": z.code, "name": z.name} for z in Zone.objects.filter(site=site).order_by("code")],
            "unlinked_people": [
                {"id": p.id, "full_name": p.full_name, "title": p.title, "role": p.role, "zone": p.zone.code if p.zone else None}
                for p in Person.objects.filter(site=site, user__isnull=True).select_related("zone").order_by("role", "title")
            ],
        })
