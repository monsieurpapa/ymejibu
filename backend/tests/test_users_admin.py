"""User administration (super administrators only): CRUD, roles, access levels, safety rules."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Person, Role

User = get_user_model()
STRONG = "Goma-Ouest-2026!"


@pytest.fixture
def admin_client(site, users):
    admin = User.objects.create_superuser("admin", "admin@example.org", STRONG)
    c = APIClient()
    c.force_authenticate(admin)
    c.admin = admin
    return c


def test_only_super_admins_can_manage_users(client_for, users):
    for name in ("resp", "adjoint", "tech", "funder"):
        assert client_for(name).get("/api/users/").status_code == 403, name


def test_list_and_options(admin_client, users):
    data = admin_client.get("/api/users/").json()
    names = {u["username"] for u in data}
    assert {"resp", "tech", "admin"} <= names
    opts = admin_client.get("/api/users/options/").json()
    roles = {r["value"]: r for r in opts["roles"]}
    assert roles["FUNDER"]["read_only"] and not roles["FUNDER"]["validate_sheets"]
    assert roles["RESP_TECH"]["validate_sheets"] and roles["RESP_TECH"]["stock_write"]
    assert any("panne" in f.lower() for f in roles["ZONE_TECH"]["forms"])
    assert [z["code"] for z in opts["zones"]] == ["Z1"]


def test_create_user_with_role_and_zone_then_login(admin_client, site):
    r = admin_client.post("/api/users/", {"username": "agent7", "full_name": "Agent Sept", "role": "ZONE_TECH",
                                          "zone": "Z1", "password": STRONG}, format="json")
    assert r.status_code == 201, r.json()
    person = Person.objects.get(user__username="agent7")
    assert person.site == site and person.role == Role.ZONE_TECH and person.zone.code == "Z1"
    login = APIClient().post("/api/auth/login/", {"username": "agent7", "password": STRONG}, format="json")
    assert login.status_code == 200 and login.json()["me"]["role"] == "ZONE_TECH"


def test_create_validations(admin_client):
    r = admin_client.post("/api/users/", {"username": "x1", "role": "ZONE_TECH"}, format="json")
    assert "password" in r.json()
    r = admin_client.post("/api/users/", {"username": "x2", "role": "ZONE_TECH", "password": "12345678"}, format="json")
    assert "password" in r.json()  # numeric / common password refused
    r = admin_client.post("/api/users/", {"username": "x3", "password": STRONG}, format="json")
    assert "role" in r.json()
    r = admin_client.post("/api/users/", {"username": "RESP", "role": "ZONE_TECH", "password": STRONG}, format="json")
    assert "username" in r.json()  # case-insensitive duplicate
    r = admin_client.post("/api/users/", {"username": "x4", "role": "ZONE_TECH", "zone": "Z9", "password": STRONG}, format="json")
    assert "zone" in r.json()


def test_link_existing_staff_record(admin_client, site):
    p = Person.objects.create(site=site, title="Point focal stockage", role=Role.STORAGE_FOCAL, full_name="Imported")
    assert p.id in [x["id"] for x in admin_client.get("/api/users/options/").json()["unlinked_people"]]
    r = admin_client.post("/api/users/", {"username": "stock1", "person_id": p.id, "password": STRONG}, format="json")
    assert r.status_code == 201, r.json()
    p.refresh_from_db()
    assert p.user.username == "stock1" and p.role == Role.STORAGE_FOCAL


def test_update_role_deactivate_and_password_revoke_tokens(admin_client, users):
    tech = users["tech"]
    Token.objects.create(user=tech)
    r = admin_client.patch(f"/api/users/{tech.id}/", {"role": "PUMP_FOCAL", "zone": None}, format="json")
    assert r.status_code == 200 and r.json()["role"] == "PUMP_FOCAL" and r.json()["zone"] is None
    r = admin_client.patch(f"/api/users/{tech.id}/", {"is_active": False}, format="json")
    tech.refresh_from_db()
    assert not tech.is_active and not tech.person.active and not Token.objects.filter(user=tech).exists()
    Token.objects.create(user=tech)
    assert admin_client.post(f"/api/users/{tech.id}/set-password/", {"password": STRONG}, format="json").status_code == 204
    tech.refresh_from_db()
    assert tech.check_password(STRONG) and not Token.objects.filter(user=tech).exists()


def test_promote_to_super_admin(admin_client, users):
    r = admin_client.patch(f"/api/users/{users['resp'].id}/", {"is_superuser": True}, format="json")
    assert r.status_code == 200
    users["resp"].refresh_from_db()
    assert users["resp"].is_superuser and users["resp"].is_staff


def test_self_protection_and_last_super_admin(admin_client):
    me = admin_client.admin
    assert admin_client.delete(f"/api/users/{me.id}/").status_code == 400
    assert admin_client.patch(f"/api/users/{me.id}/", {"is_active": False}, format="json").status_code == 400
    assert admin_client.patch(f"/api/users/{me.id}/", {"is_superuser": False}, format="json").status_code == 400


def test_delete_keeps_staff_record(admin_client, users):
    tech = users["tech"]
    pid = tech.person.id
    assert admin_client.delete(f"/api/users/{tech.id}/").status_code == 204
    assert not User.objects.filter(pk=tech.pk).exists()
    assert Person.objects.get(pk=pid).user is None
