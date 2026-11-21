"""API du scanner de l'agent de sécurité.

Connexion : l'agent ouvre le lien du mariage (/scan/<slug>) et tape son code PIN.
Django lui renvoie un jeton signé, valable 24 h, qu'il joint ensuite à chaque
scan dans l'en-tête X-Agent-Token. Pas de compte ni de mot de passe Django :
les mariés créent leurs agents eux-mêmes (nom + PIN) dans leur espace.
"""

from django.core import signing
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Agent, Mariage, ModeleAffiche
from .services import ResultatScan, valider_entree, verifier_code

SEL_JETON = "jessna-event.agent"
DUREE_JETON = 24 * 60 * 60  # secondes


def creer_jeton(agent: Agent) -> str:
    return signing.dumps({"a": agent.id, "m": agent.mariage_id}, salt=SEL_JETON)


def agent_du_jeton(jeton: str) -> Agent | None:
    try:
        data = signing.loads(jeton, salt=SEL_JETON, max_age=DUREE_JETON)
    except signing.BadSignature:  # jeton faux ou expiré
        return None
    return (
        Agent.objects.select_related("mariage")
        .filter(pk=data.get("a"), mariage_id=data.get("m"), est_actif=True)
        .first()
    )


def infos_mariage(mariage: Mariage) -> dict:
    try:
        a = mariage.affiche
        noms = " & ".join(n for n in (a.nom_marie, a.nom_mariee) if n)
    except ModeleAffiche.DoesNotExist:
        noms = ""
    return {"nom": mariage.nom, "noms": noms or mariage.nom, "date": mariage.date, "est_actif": mariage.est_actif}


def reponse_scan(r: ResultatScan, mariage: Mariage) -> dict:
    i = r.invite
    p = r.premier_passage
    return {
        "resultat": r.resultat,
        "personnes": r.scan.personnes if r.scan else 0,
        "invite": None if i is None else {
            "nom": i.nom,
            "categorie": i.categorie,
            "table_numero": i.table.numero if i.table_id else None,
            "table_nom": i.table.nom if i.table_id else "",
            "nombre_places": i.nombre_places,
            "personnes_entrees": i.personnes_entrees,
            "places_restantes": i.places_restantes,
        },
        "premier_passage": None if p is None else {
            "scanne_le": p.scanne_le,
            "agent": p.agent.nom if p.agent_id else None,
        },
        "stats": mariage.stats(),
    }


class AvecJetonAgent(APIView):
    """Vues réservées à un agent connecté (jeton dans l'en-tête X-Agent-Token)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "scan"

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.agent = agent_du_jeton(request.headers.get("X-Agent-Token", ""))

    def refus_jeton(self):
        return Response(
            {"detail": "Session de l'agent expirée ou désactivée. Reconnecte-toi avec ton code PIN."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=255)
    personnes = serializers.IntegerField(required=False, min_value=1, max_value=20)


# ---------------------------------------------------------------- connexion de l'agent
class ScanMariageView(APIView):
    """Écran du code PIN : nom du mariage à afficher (public, via le lien /scan/<slug>)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "invitation"

    def get(self, request, slug):
        return Response(infos_mariage(get_object_or_404(Mariage, slug=slug)))


class ScanConnexionView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "pin"

    def post(self, request, slug):
        mariage = get_object_or_404(Mariage, slug=slug)
        pin = str(request.data.get("pin", ""))
        if not mariage.est_actif:
            return Response({"detail": "Le scan est fermé pour ce mariage."}, status=status.HTTP_403_FORBIDDEN)
        agent = next((a for a in mariage.agents.filter(est_actif=True) if a.verifier_pin(pin)), None)
        if agent is None:
            return Response({"detail": "Code PIN incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "jeton": creer_jeton(agent),
            "agent": {"id": agent.id, "nom": agent.nom},
            "mariage": infos_mariage(mariage),
            "stats": mariage.stats(),
        })


# ---------------------------------------------------------------- scans
class ScanVerifierView(AvecJetonAgent):
    """QR lu → accès autorisé (table, places) ou refus. La présence n'est pas encore comptée."""

    def post(self, request):
        if self.agent is None:
            return self.refus_jeton()
        s = CodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        r = verifier_code(mariage=self.agent.mariage, code=s.validated_data["code"], agent=self.agent)
        return Response(reponse_scan(r, self.agent.mariage))


class ScanValiderView(AvecJetonAgent):
    """« Valider l'entrée » : enregistre la présence (protégé contre le double scan)."""

    def post(self, request):
        if self.agent is None:
            return self.refus_jeton()
        s = CodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        r = valider_entree(
            mariage=self.agent.mariage, code=s.validated_data["code"], agent=self.agent,
            personnes=s.validated_data.get("personnes"),
        )
        return Response(reponse_scan(r, self.agent.mariage))


class ScanStatsView(AvecJetonAgent):
    """Compteur « arrivés / places » affiché en haut du scanner."""

    def get(self, request):
        if self.agent is None:
            return self.refus_jeton()
        return Response({"stats": self.agent.mariage.stats(), "mariage": infos_mariage(self.agent.mariage)})
