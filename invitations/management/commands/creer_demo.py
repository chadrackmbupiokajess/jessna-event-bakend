"""python manage.py creer_demo <utilisateur>

Crée le mariage de démonstration de Chadrack Mbu & Merveille Nkembi, son affiche
(avec l'image de fond), deux tables et deux invitations :
  - Néhémie & Joyce Mubeya (couple, table 3, 2 places)
  - Clem's Sambu (personne seule, table 5, 1 place)
Peut être relancée sans créer de doublons.
"""

import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from invitations.models import Invite, Mariage, ModeleAffiche, Table

FOND = Path(__file__).resolve().parents[2] / "demo" / "fond.jpg"

TEXTES = {
    "titre_manuscrit": "Wedding",
    "titre_principal": "Invitation",
    "message": "Avec une immense joie, nous vous invitons à célébrer l'union de deux cœurs qui s'aiment",
    "nom_marie": "Chadrack Mbu",
    "liaison": "&",
    "nom_mariee": "Merveille Nkembi",
    "bandeau_titre": "Mariage",
    "bandeau_sous_titre": "Civil & Bénédiction nuptiale",
    "jour": "Samedi, 12",
    "mois_annee": "Décembre 2026",
    "heure_ceremonie": "Heure 10:00",
    "moment_ceremonie": "Matin",
    "lieu_libelle": "Église :",
    "lieu_nom": "Paroisse Saint-Joseph",
    "heure_reception": "Heure 18:00",
    "moment_reception": "Soir",
    "reception_libelle": "Réception :",
    "reception_lieu": "Salle Les Palmiers",
}


class Command(BaseCommand):
    help = "Crée le mariage de démonstration Chadrack & Merveille avec deux invitations."

    def add_arguments(self, parser):
        parser.add_argument("utilisateur", help="Nom d'utilisateur de l'organisateur (celui de createsuperuser).")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: options["utilisateur"]})
        except User.DoesNotExist:
            raise CommandError(
                f"Aucun utilisateur « {options['utilisateur']} ». Crée-le d'abord : python manage.py createsuperuser"
            )

        mariage, _ = Mariage.objects.get_or_create(
            slug="chadrack-merveille",
            defaults={"proprietaire": user, "nom": "Mariage de Chadrack & Merveille", "date": datetime.date(2026, 12, 12)},
        )

        # get_or_create : relancer la commande n'écrase pas les textes modifiés dans l'admin.
        affiche, _ = ModeleAffiche.objects.get_or_create(mariage=mariage, defaults=TEXTES)
        if not affiche.image_fond and FOND.exists():
            with FOND.open("rb") as f:
                affiche.image_fond.save("fond.jpg", File(f), save=True)

        tables = {
            n: Table.objects.get_or_create(mariage=mariage, numero=n, defaults={"capacite": 10})[0]
            for n in (3, 5)
        }
        invites = [
            ("Néhémie & Joyce Mubeya", "+243812345678", 2, tables[3]),
            ("Clem's Sambu", "+243897654321", 1, tables[5]),
        ]
        for nom, tel, places, table in invites:
            invite, cree = Invite.objects.get_or_create(
                mariage=mariage, nom=nom,
                defaults={
                    "telephone": tel, "nombre_places": places, "table": table,
                    "categorie": Invite.Categorie.COUPLE if places == 2 else Invite.Categorie.SEUL,
                },
            )
            etat = "créé" if cree else "existe déjà"
            self.stdout.write(f"  {nom:<26} table {table.numero}  {places} pl.  code {invite.code_affiche}  ({etat})")

        self.stdout.write(self.style.SUCCESS(
            f"Mariage « {mariage.nom} » prêt (id {mariage.id}). Connecte-toi sur /admin avec « {user.get_username()} »."
        ))
