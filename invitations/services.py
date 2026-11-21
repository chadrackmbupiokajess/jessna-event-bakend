"""Logique métier du scan, indépendante de l'API et des WebSockets.

Le scanner de l'agent fonctionne en deux temps :
1. `verifier_code()` : lecture du QR → accès autorisé ou refus (rien n'est encore compté) ;
2. `valider_entree()` : l'agent appuie sur « Valider l'entrée » → la présence est enregistrée.
"""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from .models import Agent, Invite, Mariage, Scan, normaliser_code


@dataclass(frozen=True)
class ResultatScan:
    resultat: str                 # une valeur de Scan.Resultat
    scan: Scan | None = None      # la ligne ajoutée au journal (aucune pour une simple vérification acceptée)
    invite: Invite | None = None  # renseigné seulement pour ce mariage
    premier_passage: Scan | None = None  # pour « Déjà scanné à 18h42 par … »

    @property
    def accepte(self) -> bool:
        return self.resultat == Scan.Resultat.ACCEPTE


def _refus(mariage: Mariage, invite: Invite | None) -> str | None:
    """Raison du refus, ou None si l'invitation donne encore droit à l'entrée."""
    if not mariage.est_actif:
        return Scan.Resultat.SCAN_FERME
    if invite is None:
        return Scan.Resultat.INCONNU
    if invite.mariage_id != mariage.id:
        return Scan.Resultat.AUTRE_MARIAGE
    if invite.places_restantes <= 0:
        return Scan.Resultat.DEJA_UTILISE
    return None


def _premier_passage(invite: Invite) -> Scan | None:
    return (
        Scan.objects.select_related("agent")
        .filter(invite=invite, resultat=Scan.Resultat.ACCEPTE)
        .order_by("scanne_le")
        .first()
    )


def verifier_code(*, mariage: Mariage, code: str, agent: Agent | None = None) -> ResultatScan:
    """Lecture du QR : dit si l'invité peut entrer, sans enregistrer sa présence.

    Les refus (déjà utilisé, code inconnu…) sont notés dans le journal des scans.
    """
    invite = Invite.objects.select_related("table").filter(code=normaliser_code(code)).first()
    refus = _refus(mariage, invite)
    meme_mariage = invite is not None and invite.mariage_id == mariage.id
    if refus is None:
        return ResultatScan(resultat=Scan.Resultat.ACCEPTE, invite=invite)
    scan = Scan.objects.create(
        mariage=mariage, invite=invite if meme_mariage else None, agent=agent,
        code_lu=code[:255], resultat=refus, personnes=0,
    )
    return ResultatScan(
        resultat=refus, scan=scan, invite=invite if meme_mariage else None,
        premier_passage=_premier_passage(invite) if refus == Scan.Resultat.DEJA_UTILISE else None,
    )


def valider_entree(
    *, mariage: Mariage, code: str, agent: Agent | None = None, personnes: int | None = None
) -> ResultatScan:
    """Vérifie un code et enregistre l'entrée en une seule transaction.

    `select_for_update()` verrouille la ligne de l'invité : si deux agents
    valident la même invitation à la même seconde, le second attend que le
    premier ait terminé, puis voit les places déjà utilisées. Une invitation
    ne peut donc jamais être validée deux fois (verrou effectif sous PostgreSQL).

    `personnes` : nombre de personnes qui entrent maintenant. Par défaut,
    toutes les places restantes.
    """
    with transaction.atomic():
        invite = (
            Invite.objects.select_for_update()
            .select_related("table")
            .filter(code=normaliser_code(code))
            .first()
        )
        resultat = _refus(mariage, invite) or Scan.Resultat.ACCEPTE
        nb = 0
        if resultat == Scan.Resultat.ACCEPTE:
            restantes = invite.places_restantes
            nb = restantes if personnes is None else max(1, min(personnes, restantes))
            invite.personnes_entrees += nb
            if invite.arrive_le is None:
                invite.arrive_le = timezone.now()
            invite.save(update_fields=["personnes_entrees", "arrive_le", "maj_le"])

        meme_mariage = invite is not None and invite.mariage_id == mariage.id
        scan = Scan.objects.create(
            mariage=mariage,
            invite=invite if meme_mariage else None,
            agent=agent,
            code_lu=code[:255],
            resultat=resultat,
            personnes=nb,
        )

    return ResultatScan(
        resultat=resultat,
        scan=scan,
        invite=invite if meme_mariage else None,
        premier_passage=_premier_passage(invite) if resultat == Scan.Resultat.DEJA_UTILISE else None,
    )
