"""Create one DEMO login per role, linked to the imported staff positions.

For local testing and training only: every account gets the same password
(given with --password). Never run this on a production server.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import Person, Role, Site, Zone

DEMO = [
    ("resp", Role.RESP_TECH, None),
    ("adjoint", Role.ADJOINT, None),
    ("tech1", Role.ZONE_TECH, "Z1"),
    ("tech2", Role.ZONE_TECH, "Z2"),
    ("pompage", Role.PUMP_FOCAL, None),
    ("stockage", Role.STORAGE_FOCAL, None),
    ("sse", Role.SSE, None),
    ("donnees", Role.DATA_OFFICER, None),
    ("bailleur", Role.FUNDER, None),
]


class Command(BaseCommand):
    help = "Crée des comptes de démonstration (un par rôle). Ne pas utiliser en production."

    def add_arguments(self, parser):
        parser.add_argument("--password", required=True)
        parser.add_argument("--site", default="GO")

    def handle(self, *args, **opts):
        site = Site.objects.filter(code=opts["site"]).first()
        if site is None:
            raise CommandError("Site introuvable : lancer d'abord `import_excel`.")
        User = get_user_model()
        for username, role, zone_code in DEMO:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(opts["password"])
            user.save()
            zone = Zone.objects.filter(site=site, code=zone_code).first() if zone_code else None
            person = Person.objects.filter(site=site, role=role, user__isnull=True, **({"zone": zone} if zone else {})).first()
            if person is None:
                person = Person.objects.filter(user=user).first() or Person(site=site, role=role, title=f"Compte démo — {Role(role).label}",
                                                                            source_ref="demo")
            Person.objects.filter(user=user).exclude(pk=person.pk).update(user=None)
            person.user = user
            person.zone = zone or person.zone
            person.save()
            self.stdout.write(f"{username:10s} {Role(role).label}")
        self.stdout.write(self.style.WARNING("Comptes de démonstration créés — mot de passe commun, à ne pas utiliser en production."))
