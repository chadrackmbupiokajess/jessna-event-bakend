from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.utils.text import slugify
from rest_framework import serializers

from .images import optimiser_image
from .models import PHOTOS_MAX, Agent, Invite, Mariage, ModeleAffiche, PhotoJointe, Table

User = get_user_model()
# Les images sont converties et compressées à l'arrivée (images.py) :
# on accepte donc de grosses photos de téléphone.
TAILLE_MAX_IMAGE = 25 * 1024 * 1024  # 25 Mo

# Tous les textes de l'affiche peuvent être vidés pendant la saisie
# (l'enregistrement automatique envoie chaque frappe).
CHAMPS_TEXTE = [
    f.name
    for f in ModeleAffiche._meta.fields
    if isinstance(f, (models.CharField, models.TextField))
    and not f.choices
    and not f.name.startswith("couleur_")
]


def url_invitation(request, invite) -> str:
    """Adresse du QR code : FRONTEND_URL si elle est fixée, sinon l'adresse
    par laquelle le site a été ouvert (ex. http://192.168.1.20:3000/i/K7FQ9XP2)."""
    if settings.FRONTEND_URL or request is None:
        return invite.url_qr
    return request.build_absolute_uri(f"/i/{invite.code}")


def url_image_invitation(request, invite) -> str | None:
    """Image de l'affiche personnalisée (aperçu WhatsApp). « ?v=… » force WhatsApp
    à reprendre la nouvelle image quand l'affiche a été refaite."""
    if not invite.image_invitation:
        return None
    url = f"{invite.image_invitation.url}?v={int(invite.maj_le.timestamp())}"
    return request.build_absolute_uri(url) if request is not None else url


def verifier_mot_de_passe(mot_de_passe: str, utilisateur) -> None:
    """Règles de Django (8 caractères, pas trop simple…), messages en français."""
    try:
        validate_password(mot_de_passe, user=utilisateur)
    except DjangoValidationError as e:
        raise serializers.ValidationError({"password": list(e.messages)})


# ---------------------------------------------------------------- affiche
class ModeleAfficheSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeleAffiche
        exclude = ["id", "mariage", "cree_le"]
        read_only_fields = ["maj_le"]
        extra_kwargs = {
            "image_fond": {"required": False, "allow_null": True},
            "image_complete": {"required": False, "allow_null": True},
            **{nom: {"required": False, "allow_blank": True} for nom in CHAMPS_TEXTE},
        }

    def _verifier_taille(self, image):
        if image and image.size > TAILLE_MAX_IMAGE:
            raise serializers.ValidationError("L'image dépasse 25 Mo. Choisis une image plus légère.")

    def validate_image_fond(self, image):
        self._verifier_taille(image)
        return optimiser_image(image) if image else image

    def validate_image_complete(self, image):
        # La deuxième affiche (image déjà prête) est ajoutée uniquement par les mariés,
        # depuis leur propre compte : l'administrateur peut la voir, pas la remplacer.
        mariage = self.context.get("mariage")
        request = self.context.get("request")
        if mariage is not None and request is not None and request.user != mariage.proprietaire:
            raise serializers.ValidationError("Seuls les mariés peuvent ajouter ou retirer leur affiche déjà prête.")
        self._verifier_taille(image)
        return optimiser_image(image, fond_transparent=(18, 12, 10)) if image else image

    def validate(self, attrs):
        # Choisir l'affiche déjà prête n'a de sens que si une image est présente.
        type_affiche = attrs.get("type_affiche", getattr(self.instance, "type_affiche", "modele"))
        image = attrs.get("image_complete", getattr(self.instance, "image_complete", None))
        if type_affiche == "image" and not image:
            if "image_complete" in attrs:
                attrs["type_affiche"] = "modele"  # affiche prête retirée → on revient à l'invitation
            else:
                raise serializers.ValidationError(
                    {"type_affiche": "Les mariés doivent d'abord ajouter leur affiche déjà prête."}
                )
        return attrs


# ---------------------------------------------------------------- photos jointes
class PhotoJointeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoJointe
        fields = ["id", "image", "legende", "ordre"]
        extra_kwargs = {"legende": {"required": False, "allow_blank": True}, "ordre": {"required": False}}

    def validate_image(self, image):
        if image.size > TAILLE_MAX_IMAGE:
            raise serializers.ValidationError("L'image dépasse 25 Mo. Choisis une image plus légère.")
        return optimiser_image(image)

    def validate(self, attrs):
        mariage = self.context["mariage"]
        if self.instance is None and mariage.photos.count() >= PHOTOS_MAX:
            raise serializers.ValidationError(
                {"image": f"{PHOTOS_MAX} photos au maximum : retire une photo avant d'en ajouter une autre."}
            )
        return attrs

    def create(self, vd):
        mariage = self.context["mariage"]
        if "ordre" not in vd:
            dernier = mariage.photos.aggregate(m=models.Max("ordre"))["m"]
            vd["ordre"] = 0 if dernier is None else dernier + 1
        return PhotoJointe.objects.create(mariage=mariage, **vd)


# ---------------------------------------------------------------- mariages
class MariageSerializer(serializers.ModelSerializer):
    stats = serializers.SerializerMethodField()
    proprietaire = serializers.CharField(source="proprietaire.get_username", read_only=True)
    nom_marie = serializers.SerializerMethodField()
    nom_mariee = serializers.SerializerMethodField()

    class Meta:
        model = Mariage
        fields = ["id", "nom", "slug", "date", "est_actif", "proprietaire", "nom_marie", "nom_mariee", "stats"]

    def _affiche(self, obj):
        try:
            return obj.affiche
        except ModeleAffiche.DoesNotExist:
            return None

    def get_nom_marie(self, obj):
        a = self._affiche(obj)
        return a.nom_marie if a else ""

    def get_nom_mariee(self, obj):
        a = self._affiche(obj)
        return a.nom_mariee if a else ""

    def get_stats(self, obj):
        return obj.stats()


class NouveauMariageSerializer(serializers.Serializer):
    """Création par l'administrateur : le mariage, son affiche et le compte des mariés."""

    nom = serializers.CharField(max_length=150)
    date = serializers.DateField()
    nom_marie = serializers.CharField(max_length=60)
    nom_mariee = serializers.CharField(max_length=60)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, valeur):
        valeur = valeur.strip()
        try:
            User.username_validator(valeur)
        except DjangoValidationError:
            raise serializers.ValidationError(
                "Utilise seulement des lettres, des chiffres et les signes @ . + - _ (sans espace)."
            )
        if User.objects.filter(username__iexact=valeur).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return valeur

    def validate(self, attrs):
        verifier_mot_de_passe(attrs["password"], User(username=attrs["username"], email=attrs.get("email", "")))
        return attrs

    @transaction.atomic
    def create(self, vd):
        maries = User.objects.create_user(
            username=vd["username"], email=vd.get("email", ""), password=vd["password"],
            first_name=vd["nom_marie"].split(" ")[0][:150],
        )
        base = slugify(vd["nom"])[:150] or "mariage"
        slug, n = base, 2
        while Mariage.objects.filter(slug=slug).exists():
            slug, n = f"{base}-{n}", n + 1
        mariage = Mariage.objects.create(proprietaire=maries, nom=vd["nom"], slug=slug, date=vd["date"])
        affiche = ModeleAffiche.objects.create(mariage=mariage, nom_marie=vd["nom_marie"], nom_mariee=vd["nom_mariee"])
        affiche.remettre_fond_origine()  # chaque nouveau mariage part de l'affiche d'origine
        return mariage


class MotDePasseSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        verifier_mot_de_passe(attrs["password"], self.context["utilisateur"])
        return attrs


# ---------------------------------------------------------------- invités
class InviteSerializer(serializers.ModelSerializer):
    code_affiche = serializers.CharField(read_only=True)
    url_qr = serializers.SerializerMethodField()
    image_invitation = serializers.SerializerMethodField()
    table_numero = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=999, write_only=True
    )

    class Meta:
        model = Invite
        fields = [
            "id", "categorie", "nom", "telephone", "nombre_places", "table_numero",
            "code", "code_affiche", "url_qr", "image_invitation", "statut_rsvp",
            "personnes_entrees", "arrive_le", "envoyee_le",
        ]
        read_only_fields = ["code", "statut_rsvp", "personnes_entrees", "arrive_le", "envoyee_le"]
        extra_kwargs = {
            "nombre_places": {"required": False, "min_value": 1, "max_value": 20},
            "telephone": {"required": False, "allow_blank": True},
        }

    def get_url_qr(self, invite):
        return url_invitation(self.context.get("request"), invite)

    def get_image_invitation(self, invite):
        return url_image_invitation(self.context.get("request"), invite)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["table_numero"] = instance.table.numero if instance.table_id else None
        return data

    def validate_nom(self, valeur):
        valeur = valeur.strip()
        if not valeur:
            raise serializers.ValidationError("Indique le nom imprimé sur l'invitation.")
        return valeur

    def validate(self, attrs):
        if self.instance is None and "nombre_places" not in attrs:
            attrs["nombre_places"] = 2 if attrs.get("categorie") == Invite.Categorie.COUPLE else 1
        places = attrs.get("nombre_places", getattr(self.instance, "nombre_places", 1))
        entrees = getattr(self.instance, "personnes_entrees", 0)
        if places < entrees:
            raise serializers.ValidationError(
                {"nombre_places": f"{entrees} personne(s) sont déjà entrées avec cette invitation."}
            )
        return attrs

    def _table(self, numero):
        if numero is None:
            return None
        return Table.objects.get_or_create(mariage=self.context["mariage"], numero=numero)[0]

    def create(self, vd):
        table = self._table(vd.pop("table_numero", None))
        return Invite.objects.create(mariage=self.context["mariage"], table=table, **vd)

    def update(self, instance, vd):
        if "table_numero" in vd:
            instance.table = self._table(vd.pop("table_numero"))
        return super().update(instance, vd)


class InvitePubliqueSerializer(serializers.ModelSerializer):
    """Ce qu'un invité voit de sa propre invitation (rien sur sa table ni les autres invités)."""

    code_affiche = serializers.CharField(read_only=True)
    url_qr = serializers.SerializerMethodField()
    image_invitation = serializers.SerializerMethodField()

    class Meta:
        model = Invite
        fields = ["nom", "nombre_places", "code_affiche", "url_qr", "image_invitation", "statut_rsvp"]

    def get_url_qr(self, invite):
        return url_invitation(self.context.get("request"), invite)

    def get_image_invitation(self, invite):
        return url_image_invitation(self.context.get("request"), invite)


class ImageInvitationSerializer(serializers.Serializer):
    """Image de l'affiche personnalisée, dessinée par le navigateur des mariés."""

    image = serializers.ImageField()

    def validate_image(self, image):
        if image.size > 3 * 1024 * 1024:
            raise serializers.ValidationError("L'image de l'affiche dépasse 3 Mo.")
        return image


# ---------------------------------------------------------------- agents
class AgentSerializer(serializers.ModelSerializer):
    pin = serializers.RegexField(
        r"^\d{4,8}$", write_only=True, required=False,
        error_messages={"invalid": "Le code PIN doit contenir 4 à 8 chiffres."},
    )

    class Meta:
        model = Agent
        fields = ["id", "nom", "est_actif", "pin", "cree_le"]
        read_only_fields = ["cree_le"]

    def validate_nom(self, valeur):
        valeur = valeur.strip()
        autres = Agent.objects.filter(mariage=self.context["mariage"], nom__iexact=valeur)
        if self.instance:
            autres = autres.exclude(pk=self.instance.pk)
        if autres.exists():
            raise serializers.ValidationError("Un agent porte déjà ce nom pour ce mariage.")
        return valeur

    def validate(self, attrs):
        if self.instance is None and not attrs.get("pin"):
            raise serializers.ValidationError({"pin": "Choisis un code PIN de 4 à 8 chiffres."})
        return attrs

    def create(self, vd):
        pin = vd.pop("pin")
        agent = Agent(mariage=self.context["mariage"], **vd)
        agent.definir_pin(pin)
        agent.save()
        return agent

    def update(self, instance, vd):
        pin = vd.pop("pin", None)
        if pin:
            instance.definir_pin(pin)
        return super().update(instance, vd)
