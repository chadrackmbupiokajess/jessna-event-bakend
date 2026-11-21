"""Modèles de l'application d'invitations de mariage à QR code.

Mariage ─┬─ ModeleAffiche (1 par mariage : textes, polices, couleurs, image de fond)
         ├─ PhotoJointe   (photos en plus envoyées avec l'invitation sur WhatsApp)
         ├─ Table         (plan de table)
         ├─ Invite        (1 invitation = 1 code QR, avec un nombre de places)
         ├─ Agent         (agents de sécurité qui scannent à l'entrée)
         └─ Scan          (journal de chaque passage devant un agent)
"""

import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q, Sum

# Alphabet sans caractères ambigus (pas de 0/O, 1/I/L) : un agent peut taper
# le code à la main si la caméra ne fonctionne pas.
ALPHABET_CODE = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LONGUEUR_CODE = 8

# Image de fond d'origine de l'affiche (mains, alliances, roses, bandeau).
FOND_ORIGINE = Path(__file__).resolve().parent / "demo" / "fond.jpg"

couleur_hex = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Couleur attendue au format #RRGGBB, par exemple #5A220C.",
)


def generer_code() -> str:
    """Code aléatoire non devinable, ex. 'K7FQ9XP2' (31^8 ≈ 850 milliards de possibilités)."""
    return "".join(secrets.choice(ALPHABET_CODE) for _ in range(LONGUEUR_CODE))


def normaliser_code(valeur: str) -> str:
    """Accepte le contenu brut d'un QR ou une saisie manuelle.

    'https://site.com/i/K7FQ9XP2' -> 'K7FQ9XP2'
    'k7fq-9xp2'                  -> 'K7FQ9XP2'
    """
    valeur = (valeur or "").strip()
    if "/" in valeur:
        valeur = valeur.rstrip("/").rsplit("/", 1)[-1]
    return valeur.replace("-", "").replace(" ", "").upper()


class Horodatage(models.Model):
    cree_le = models.DateTimeField("créé le", auto_now_add=True)
    maj_le = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Mariage
# ---------------------------------------------------------------------------
class Mariage(Horodatage):
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="mariages",
        verbose_name="organisateur",
    )
    nom = models.CharField("nom de l'événement", max_length=150)
    slug = models.SlugField(unique=True, max_length=160)
    date = models.DateField("date du mariage")
    est_actif = models.BooleanField(
        "scan ouvert",
        default=True,
        help_text="Décocher pour bloquer tous les scans (avant ou après l'événement).",
    )

    class Meta:
        ordering = ["-date"]
        verbose_name = "mariage"

    def __str__(self) -> str:
        return self.nom

    def stats(self) -> dict:
        """Chiffres du tableau de bord : invitations, places, personnes arrivées."""
        agg = self.invites.aggregate(
            places=Sum("nombre_places"),
            entrees=Sum("personnes_entrees"),
        )
        return {
            "invitations": self.invites.count(),
            "places": agg["places"] or 0,
            "arrives": agg["entrees"] or 0,
            "confirmes": self.invites.filter(statut_rsvp=Invite.Rsvp.CONFIRME).count(),
        }


# ---------------------------------------------------------------------------
# Modèle d'affiche : tout ce qui est modifiable dans l'admin
# ---------------------------------------------------------------------------
class PoliceManuscrite(models.TextChoices):
    GREAT_VIBES = "great-vibes", "Great Vibes"
    PINYON_SCRIPT = "pinyon-script", "Pinyon Script"
    ALEX_BRUSH = "alex-brush", "Alex Brush"


class PoliceTitre(models.TextChoices):
    BODONI_MODA = "bodoni-moda", "Bodoni Moda"
    PLAYFAIR = "playfair-display", "Playfair Display"
    CINZEL = "cinzel", "Cinzel"


class PoliceNoms(models.TextChoices):
    CORMORANT = "cormorant-garamond", "Cormorant Garamond"
    PLAYFAIR = "playfair-display", "Playfair Display"
    CINZEL = "cinzel", "Cinzel"


class PoliceInfos(models.TextChoices):
    MONTSERRAT = "montserrat", "Montserrat"
    RALEWAY = "raleway", "Raleway"
    LATO = "lato", "Lato"


def chemin_image_fond(instance: "ModeleAffiche", nom_fichier: str) -> str:
    return f"mariages/{instance.mariage_id}/fond/{nom_fichier}"


class TypeAffiche(models.TextChoices):
    MODELE = "modele", "Affiche à compléter (textes modifiables)"
    IMAGE = "image", "Affiche déjà prête (image complète)"


class PositionQR(models.TextChoices):
    HAUT_GAUCHE = "haut-gauche", "En haut à gauche"
    HAUT_DROITE = "haut-droite", "En haut à droite"
    BAS_GAUCHE = "bas-gauche", "En bas à gauche"
    BAS_DROITE = "bas-droite", "En bas à droite"


class ModeleAffiche(Horodatage):
    mariage = models.OneToOneField(
        Mariage, on_delete=models.CASCADE, related_name="affiche"
    )
    image_fond = models.ImageField(
        "image de fond",
        upload_to=chemin_image_fond,
        blank=True,
        help_text="Portrait, 1059 × 1486 px conseillé, sans aucun texte.",
    )

    # Deux affiches possibles : le modèle à compléter ou une image déjà prête.
    type_affiche = models.CharField(
        "affiche envoyée aux invités",
        max_length=10,
        choices=TypeAffiche.choices,
        default=TypeAffiche.MODELE,
    )
    image_complete = models.ImageField(
        "affiche déjà prête",
        upload_to=chemin_image_fond,
        blank=True,
        help_text="Affiche entière (textes compris), ajoutée par les mariés. Le QR code de l'invité est posé dessus.",
    )
    position_qr = models.CharField(
        "position du QR code",
        max_length=12,
        choices=PositionQR.choices,
        default=PositionQR.HAUT_DROITE,
        help_text="Sur l'affiche déjà prête : coin où poser la carte de l'invité.",
    )

    # En-tête
    titre_manuscrit = models.CharField(max_length=40, default="Wedding")
    titre_principal = models.CharField(max_length=40, default="Invitation")
    message = models.TextField(
        max_length=240,
        default="Kwa furaha kubwa tunakualika kushuhudia muungano wa wawili wanaopendana",
    )

    # Les mariés
    nom_marie = models.CharField("nom du marié", max_length=60)
    liaison = models.CharField(max_length=10, default="&")
    nom_mariee = models.CharField("nom de la mariée", max_length=60)

    # Bandeau
    bandeau_titre = models.CharField(max_length=40, default="Marriage")
    bandeau_sous_titre = models.CharField(
        max_length=60, default="Registration & Blessing"
    )

    # Colonne gauche : date et heure de la cérémonie
    jour = models.CharField(max_length=40, help_text="Ex. « Saturday, 12 »")
    mois_annee = models.CharField(max_length=40, help_text="Ex. « April 2026 »")
    heure_ceremonie = models.CharField(max_length=30, default="Time 4:00")
    moment_ceremonie = models.CharField(max_length=30, default="Morning")

    # Colonne droite : lieu de la cérémonie
    lieu_libelle = models.CharField(max_length=30, default="Church:")
    lieu_nom = models.CharField(max_length=80)
    heure_reception = models.CharField(max_length=30, default="Time 8:00")
    moment_reception = models.CharField(max_length=30, default="Afternoon")

    # Réception
    reception_libelle = models.CharField(max_length=30, default="Event:")
    reception_lieu = models.CharField(max_length=120)

    # Style
    couleur_titre = models.CharField(max_length=7, default="#1E1612", validators=[couleur_hex])
    couleur_texte = models.CharField(max_length=7, default="#5A220C", validators=[couleur_hex])
    couleur_bandeau = models.CharField(max_length=7, default="#F4E6D4", validators=[couleur_hex])
    police_manuscrite = models.CharField(
        max_length=30, choices=PoliceManuscrite.choices, default=PoliceManuscrite.GREAT_VIBES
    )
    police_titres = models.CharField(
        max_length=30, choices=PoliceTitre.choices, default=PoliceTitre.BODONI_MODA
    )
    police_noms = models.CharField(
        max_length=30, choices=PoliceNoms.choices, default=PoliceNoms.CORMORANT
    )
    police_infos = models.CharField(
        max_length=30, choices=PoliceInfos.choices, default=PoliceInfos.MONTSERRAT
    )

    class Meta:
        verbose_name = "modèle d'affiche"
        verbose_name_plural = "modèles d'affiche"

    def __str__(self) -> str:
        return f"Affiche – {self.mariage}"

    def remettre_fond_origine(self) -> None:
        """Remet l'image de fond d'origine (nouveau mariage, ou bouton dans l'éditeur)."""
        if not FOND_ORIGINE.exists():
            return
        with FOND_ORIGINE.open("rb") as f:
            self.image_fond.save("fond-original.jpg", File(f), save=True)


# ---------------------------------------------------------------------------
# Photos jointes : images en plus envoyées avec l'invitation sur WhatsApp
# ---------------------------------------------------------------------------
PHOTOS_MAX = 8


def chemin_photo(instance: "PhotoJointe", nom_fichier: str) -> str:
    return f"mariages/{instance.mariage_id}/photos/{nom_fichier}"


class PhotoJointe(Horodatage):
    """Photo ajoutée par les mariés (photo de couple, plan d'accès, programme…),
    proposée à l'envoi de chaque invitation, en plus des affiches."""

    mariage = models.ForeignKey(Mariage, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=chemin_photo)
    legende = models.CharField("légende", max_length=80, blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["mariage", "ordre", "id"]
        verbose_name = "photo jointe"
        verbose_name_plural = "photos jointes"

    def __str__(self) -> str:
        return self.legende or f"Photo {self.pk}"


# ---------------------------------------------------------------------------
# Plan de table
# ---------------------------------------------------------------------------
class Table(models.Model):
    mariage = models.ForeignKey(Mariage, on_delete=models.CASCADE, related_name="tables")
    numero = models.PositiveSmallIntegerField("numéro")
    nom = models.CharField(max_length=60, blank=True, help_text="Ex. « Table des parents »")
    capacite = models.PositiveSmallIntegerField("capacité", default=10)

    class Meta:
        ordering = ["mariage", "numero"]
        constraints = [
            models.UniqueConstraint(fields=["mariage", "numero"], name="table_unique_par_mariage"),
        ]

    def __str__(self) -> str:
        return f"Table {self.numero}" + (f" – {self.nom}" if self.nom else "")

    def places_attribuees(self) -> int:
        return self.invites.aggregate(total=Sum("nombre_places"))["total"] or 0


# ---------------------------------------------------------------------------
# Invité = une invitation = un code QR
# ---------------------------------------------------------------------------
def chemin_invitation(instance: "Invite", nom_fichier: str) -> str:
    return f"mariages/{instance.mariage_id}/invitations/{instance.code}.jpg"


class Invite(Horodatage):
    class Rsvp(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        CONFIRME = "confirme", "Confirmé"
        DECLINE = "decline", "Ne vient pas"

    class Categorie(models.TextChoices):
        COUPLE = "couple", "Couple"
        SEUL = "seul", "Personne seule"

    mariage = models.ForeignKey(Mariage, on_delete=models.CASCADE, related_name="invites")
    categorie = models.CharField(
        "type d'invitation", max_length=10, choices=Categorie.choices, default=Categorie.SEUL
    )
    nom = models.CharField(
        "nom sur l'invitation", max_length=80, help_text="Ex. « M. et Mme Kabasele »"
    )
    telephone = models.CharField(
        "téléphone (WhatsApp)", max_length=20, blank=True
    )
    nombre_places = models.PositiveSmallIntegerField(
        "places", default=1, validators=[MinValueValidator(1)]
    )
    table = models.ForeignKey(
        Table, on_delete=models.SET_NULL, null=True, blank=True, related_name="invites"
    )
    code = models.CharField(
        max_length=LONGUEUR_CODE, unique=True, default=generer_code, editable=False
    )
    statut_rsvp = models.CharField(
        "réponse", max_length=12, choices=Rsvp.choices, default=Rsvp.EN_ATTENTE
    )

    # Présence. On compte les personnes : un couple invité avec 2 places
    # peut arriver séparément, chacun étant validé au scan.
    personnes_entrees = models.PositiveSmallIntegerField("personnes entrées", default=0)
    arrive_le = models.DateTimeField("première arrivée", null=True, blank=True)

    # Invitation générée (image envoyée par WhatsApp ou imprimée)
    image_invitation = models.ImageField(upload_to=chemin_invitation, blank=True)
    envoyee_le = models.DateTimeField("envoyée le", null=True, blank=True)

    class Meta:
        ordering = ["mariage", "nom"]
        verbose_name = "invité"
        constraints = [
            models.CheckConstraint(
                condition=Q(personnes_entrees__lte=F("nombre_places")),
                name="entrees_inferieures_aux_places",
            ),
        ]
        indexes = [models.Index(fields=["mariage", "statut_rsvp"])]

    def __str__(self) -> str:
        return f"{self.nom} ({self.code_affiche})"

    @property
    def code_affiche(self) -> str:
        """Format lisible imprimé sous le QR : 'K7FQ-9XP2'."""
        return f"{self.code[:4]}-{self.code[4:]}"

    @property
    def places_restantes(self) -> int:
        return self.nombre_places - self.personnes_entrees

    @property
    def est_present(self) -> bool:
        return self.personnes_entrees > 0

    @property
    def url_qr(self) -> str:
        """Adresse encodée dans le QR code, hors requête (admin Django, commandes).

        L'API utilise plutôt url_invitation() (serializers.py), qui suit
        l'adresse réellement utilisée pour ouvrir le site.
        """
        return f"{settings.FRONTEND_URL or 'http://localhost:3000'}/i/{self.code}"

    def clean(self):
        if self.table_id and self.table.mariage_id != self.mariage_id:
            raise ValidationError({"table": "Cette table appartient à un autre mariage."})

    def save(self, *args, **kwargs):
        # Collision de code quasi impossible, mais on la gère quand même.
        if self._state.adding:
            while Invite.objects.filter(code=self.code).exists():
                self.code = generer_code()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Agents de sécurité
# ---------------------------------------------------------------------------
class Agent(Horodatage):
    mariage = models.ForeignKey(Mariage, on_delete=models.CASCADE, related_name="agents")
    nom = models.CharField(max_length=60, help_text="Ex. « Agent porte principale »")
    pin_hash = models.CharField(max_length=128, editable=False)
    est_actif = models.BooleanField("actif", default=True)

    class Meta:
        ordering = ["mariage", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["mariage", "nom"], name="agent_unique_par_mariage"),
        ]

    def __str__(self) -> str:
        return self.nom

    def definir_pin(self, pin: str) -> None:
        """Le PIN n'est jamais stocké en clair."""
        self.pin_hash = make_password(pin)

    def verifier_pin(self, pin: str) -> bool:
        return bool(self.pin_hash) and check_password(pin, self.pin_hash)


# ---------------------------------------------------------------------------
# Journal des scans
# ---------------------------------------------------------------------------
class Scan(models.Model):
    class Resultat(models.TextChoices):
        ACCEPTE = "accepte", "Accès autorisé"
        DEJA_UTILISE = "deja_utilise", "Déjà utilisé"
        INCONNU = "inconnu", "Code inconnu"
        AUTRE_MARIAGE = "autre_mariage", "Invitation d'un autre mariage"
        SCAN_FERME = "scan_ferme", "Scan fermé"

    mariage = models.ForeignKey(Mariage, on_delete=models.CASCADE, related_name="scans")
    invite = models.ForeignKey(
        Invite, on_delete=models.SET_NULL, null=True, blank=True, related_name="scans"
    )
    agent = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name="scans"
    )
    code_lu = models.CharField("code lu", max_length=255)
    resultat = models.CharField(max_length=16, choices=Resultat.choices)
    personnes = models.PositiveSmallIntegerField("personnes validées", default=0)
    scanne_le = models.DateTimeField("scanné le", auto_now_add=True)

    class Meta:
        ordering = ["-scanne_le"]
        indexes = [models.Index(fields=["mariage", "-scanne_le"])]

    def __str__(self) -> str:
        return f"{self.get_resultat_display()} – {self.code_lu}"
