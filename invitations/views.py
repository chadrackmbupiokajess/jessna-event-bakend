"""API de Jessna Event.

Deux rôles :
- l'administrateur (is_staff) crée les mariages et les comptes des mariés, et voit tout ;
- les mariés n'accèdent qu'à leur(s) mariage(s) : affiche, invités, agents.
"""

from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Expertise, Invite, Mariage, ModeleAffiche, ParametresEcosystem, Scan, Table, normaliser_code
from .serializers import (
    AgentSerializer, ImageInvitationSerializer, InvitePubliqueSerializer, InviteSerializer, MariageSerializer,
    ModeleAfficheSerializer, MotDePasseSerializer, NouveauMariageSerializer, PhotoJointeSerializer,
    ExpertiseSerializer, ParametresEcosystemSerializer,
    TableSerializer,
)


def profil(user) -> dict:
    return {
        "id": user.id,
        "username": user.get_username(),
        "nom": user.get_full_name() or user.get_username(),
        "est_admin": user.is_staff,
    }


def mariage_pour(request, mariage_id) -> Mariage:
    """Le mariage demandé, si l'utilisateur y a droit (sinon 404)."""
    qs = Mariage.objects.select_related("proprietaire")
    if not request.user.is_staff:
        qs = qs.filter(proprietaire=request.user)
    return get_object_or_404(qs, pk=mariage_id)


class DansMonMariage:
    """Vues sous /mariages/<mariage_id>/… : vérifie l'accès et passe le mariage au serializer."""

    def get_mariage(self) -> Mariage:
        if not hasattr(self, "_mariage"):
            self._mariage = mariage_pour(self.request, self.kwargs["mariage_id"])
        return self._mariage

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["mariage"] = self.get_mariage()
        return ctx


# ---------------------------------------------------------------- connexion
class CsrfView(APIView):
    """Dépose le cookie csrftoken que Next.js renvoie ensuite dans l'en-tête X-CSRFToken."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"ok": True})


class ConnexionView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "connexion"

    def post(self, request):
        user = authenticate(
            request,
            username=request.data.get("username", ""),
            password=request.data.get("password", ""),
        )
        if user is None:
            return Response(
                {"detail": "Nom d'utilisateur ou mot de passe incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(profil(user))


class DeconnexionView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MoiView(APIView):
    def get(self, request):
        return Response(profil(request.user))


# ---------------------------------------------------------------- administrateur
class AdminMariagesView(APIView):
    """GET : tous les mariages. POST : crée un mariage + le compte des mariés."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Mariage.objects.select_related("proprietaire", "affiche").order_by("-date")
        return Response(MariageSerializer(qs, many=True).data)

    def post(self, request):
        s = NouveauMariageSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        mariage = s.save()
        return Response(MariageSerializer(mariage).data, status=status.HTTP_201_CREATED)


class AdminEcosystemView(APIView):
    """Page publicitaire globale affichée aux invités."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(ParametresEcosystemSerializer(ParametresEcosystem.charger()).data)

    def put(self, request):
        serializer = ParametresEcosystemSerializer(ParametresEcosystem.charger(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminExpertisesView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        expertises = ParametresEcosystem.charger().expertises.all()
        return Response(ExpertiseSerializer(expertises, many=True, context={"request": request}).data)

    def post(self, request):
        parametres = ParametresEcosystem.charger()
        serializer = ExpertiseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(parametres=parametres)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminExpertiseDetailView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def patch(self, request, expertise_id):
        expertise = get_object_or_404(Expertise, pk=expertise_id)
        serializer = ExpertiseSerializer(
            expertise,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, expertise_id):
        expertise = get_object_or_404(Expertise, pk=expertise_id)
        if expertise.image:
            expertise.image.delete(save=False)
        expertise.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMotDePasseView(APIView):
    """Donne un nouveau mot de passe au compte des mariés (oubli, première remise…)."""

    permission_classes = [IsAdminUser]

    def post(self, request, mariage_id):
        mariage = get_object_or_404(Mariage.objects.select_related("proprietaire"), pk=mariage_id)
        maries = mariage.proprietaire
        if maries.is_staff:
            return Response(
                {"detail": "Ce mariage appartient à un administrateur : change son mot de passe dans l'admin Django."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        s = MotDePasseSerializer(data=request.data, context={"utilisateur": maries})
        s.is_valid(raise_exception=True)
        maries.set_password(s.validated_data["password"])
        maries.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- espace des mariés
class MesMariagesView(generics.ListAPIView):
    serializer_class = MariageSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Mariage.objects.select_related("proprietaire", "affiche")
        return qs if self.request.user.is_staff else qs.filter(proprietaire=self.request.user)


class MariageDetailView(generics.RetrieveAPIView):
    serializer_class = MariageSerializer

    def get_object(self):
        return mariage_pour(self.request, self.kwargs["mariage_id"])


class TablesView(DansMonMariage, generics.ListCreateAPIView):
    serializer_class = TableSerializer
    pagination_class = None

    def get_queryset(self):
        return self.get_mariage().tables.all()

    def perform_create(self, serializer):
        serializer.save(mariage=self.get_mariage())


class TableDetailView(DansMonMariage, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TableSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return self.get_mariage().tables.all()


class AfficheView(DansMonMariage, generics.RetrieveUpdateAPIView):
    """GET : l'affiche. PATCH : un ou plusieurs champs (JSON), ou une image
    (multipart « image_fond » ou « image_complete », convertie et compressée à l'arrivée)."""

    serializer_class = ModeleAfficheSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        affiche, _ = ModeleAffiche.objects.get_or_create(mariage=self.get_mariage())
        return affiche


class AfficheImageOrigineView(DansMonMariage, APIView):
    """Remet l'image de fond d'origine de l'affiche (bouton dans l'éditeur)."""

    def post(self, request, mariage_id):
        affiche, _ = ModeleAffiche.objects.get_or_create(mariage=self.get_mariage())
        affiche.remettre_fond_origine()
        return Response(ModeleAfficheSerializer(affiche, context={"request": request}).data)


class PhotosView(DansMonMariage, generics.ListCreateAPIView):
    """Photos en plus envoyées avec l'invitation (multipart « image », convertie et compressée)."""

    serializer_class = PhotoJointeSerializer
    pagination_class = None
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return self.get_mariage().photos.all()


class PhotoDetailView(DansMonMariage, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PhotoJointeSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return self.get_mariage().photos.all()

    def perform_destroy(self, instance):
        instance.image.delete(save=False)  # le fichier part avec la photo
        instance.delete()


class DirectView(DansMonMariage, APIView):
    """Temps réel en AJAX : la page des mariés interroge cette adresse toutes
    les quelques secondes. Réponse très légère : les compteurs et une « version »
    qui change dès qu'un agent scanne ou qu'un invité est ajouté, modifié ou
    supprimé. La page ne recharge ses listes que si la version a changé.
    """

    def get(self, request, mariage_id):
        mariage = self.get_mariage()
        invites = mariage.invites.aggregate(n=Count("id"), maj=Max("maj_le"))
        dernier_scan = mariage.scans.aggregate(dernier=Max("id"))["dernier"] or 0
        maj = invites["maj"]
        version = f"{dernier_scan}-{invites['n']}-{int(maj.timestamp() * 1000) if maj else 0}"
        return Response({"version": version, "stats": mariage.stats()})


class InvitesView(DansMonMariage, generics.ListCreateAPIView):
    serializer_class = InviteSerializer
    pagination_class = None

    def get_queryset(self):
        return self.get_mariage().invites.select_related("table").order_by("-cree_le")


class InviteDetailView(DansMonMariage, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InviteSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return self.get_mariage().invites.select_related("table")

    def destroy(self, request, *args, **kwargs):
        invite = self.get_object()
        if invite.personnes_entrees:
            return Response(
                {"detail": "Cet invité est déjà entré : son invitation reste dans l'historique de la soirée."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InviteEnvoyeeView(DansMonMariage, APIView):
    """Note que l'invitation a été envoyée (bouton WhatsApp)."""

    def post(self, request, mariage_id, pk):
        invite = get_object_or_404(self.get_mariage().invites, pk=pk)
        invite.envoyee_le = timezone.now()
        invite.save(update_fields=["envoyee_le", "maj_le"])
        return Response(InviteSerializer(invite, context={"mariage": self.get_mariage(), "request": request}).data)


class InviteImageView(DansMonMariage, APIView):
    """Enregistre l'image de l'affiche personnalisée de l'invité.

    Elle sert d'aperçu (og:image) à la page /i/<code> : WhatsApp l'affiche en haut
    du message, au-dessus du texte, quand on envoie le lien de l'invitation.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, mariage_id, pk):
        invite = get_object_or_404(self.get_mariage().invites, pk=pk)
        s = ImageInvitationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if invite.image_invitation:
            invite.image_invitation.delete(save=False)  # une seule image par invité
        invite.image_invitation.save(f"{invite.code}.jpg", s.validated_data["image"], save=False)
        invite.save(update_fields=["image_invitation", "maj_le"])
        return Response(InviteSerializer(invite, context={"mariage": self.get_mariage(), "request": request}).data)


class PresenceView(DansMonMariage, APIView):
    """Liste de présence du jour J : qui est entré (heure, table, agent), qui est
    attendu, et les tentatives refusées (invitation déjà utilisée, code inconnu…)."""

    def get(self, request, mariage_id):
        mariage = self.get_mariage()
        invites = list(mariage.invites.select_related("table").order_by("nom"))

        # Agents qui ont validé chaque invitation (un couple peut entrer en deux fois).
        agents: dict[int, list[str]] = {}
        acceptes = mariage.scans.filter(resultat=Scan.Resultat.ACCEPTE).select_related("agent").order_by("scanne_le")
        for s in acceptes:
            if s.invite_id:
                noms = agents.setdefault(s.invite_id, [])
                nom = s.agent.nom if s.agent_id else "Agent supprimé"
                if nom not in noms:
                    noms.append(nom)

        def ligne(i: Invite) -> dict:
            return {
                "id": i.id,
                "nom": i.nom,
                "categorie": i.categorie,
                "telephone": i.telephone,
                "table_numero": i.table.numero if i.table_id else None,
                "table_nom": i.table.nom if i.table_id else "",
                "nombre_places": i.nombre_places,
                "personnes_entrees": i.personnes_entrees,
                "arrive_le": i.arrive_le,
                "statut_rsvp": i.statut_rsvp,
                "agents": agents.get(i.id, []),
            }

        entres = sorted((ligne(i) for i in invites if i.personnes_entrees), key=lambda l: l["arrive_le"], reverse=True)
        attendus = [ligne(i) for i in invites if not i.personnes_entrees]
        refus = [
            {
                "id": s.id,
                "scanne_le": s.scanne_le,
                "resultat": s.resultat,
                "libelle": s.get_resultat_display(),
                "invite": s.invite.nom if s.invite_id else None,
                "code_lu": s.code_lu,
                "agent": s.agent.nom if s.agent_id else None,
            }
            for s in mariage.scans.exclude(resultat=Scan.Resultat.ACCEPTE)
            .select_related("invite", "agent").order_by("-scanne_le")[:50]
        ]
        return Response({
            "stats": mariage.stats(),
            "entres": entres,
            "attendus": attendus,
            "refus": refus,
            "maintenant": timezone.now(),
        })


class AgentsView(DansMonMariage, generics.ListCreateAPIView):
    serializer_class = AgentSerializer
    pagination_class = None

    def get_queryset(self):
        return self.get_mariage().agents.order_by("nom")


class AgentDetailView(DansMonMariage, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AgentSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return self.get_mariage().agents.all()


# ---------------------------------------------------------------- public (invité)
class InvitationPubliqueView(APIView):
    """L'affiche personnalisée d'un invité, lue avec le code de son QR (sans connexion)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "invitation"

    def get(self, request, code):
        invite = get_object_or_404(
            Invite.objects.select_related("mariage"), code=normaliser_code(code)
        )
        affiche, _ = ModeleAffiche.objects.get_or_create(mariage=invite.mariage)
        photos = [
            {
                "id": photo.id,
                "image": request.build_absolute_uri(photo.image.url),
                "legende": photo.legende,
                "ordre": photo.ordre,
            }
            for photo in invite.mariage.photos.all()
        ]
        return Response(
            {
                "modele": ModeleAfficheSerializer(affiche, context={"request": request}).data,
                "invite": InvitePubliqueSerializer(invite, context={"request": request}).data,
                "photos": photos,
                "ecosysteme": ParametresEcosystemSerializer(ParametresEcosystem.charger()).data,
            }
        )
