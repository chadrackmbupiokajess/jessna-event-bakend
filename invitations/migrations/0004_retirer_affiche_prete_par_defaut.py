"""La deuxième affiche (image déjà prête) n'est plus remplie d'office.

0003 avait copié l'affiche d'exemple « Save the Date » dans chaque mariage.
Désormais, seuls les mariés ajoutent leur propre affiche : on retire la copie
d'exemple (et son fichier), et ces mariages reviennent à l'invitation à compléter.
Les affiches que les mariés ont ajoutées eux-mêmes ne sont pas touchées.
"""

from django.db import migrations

NOM_EXEMPLE = "affiche-prete"


def retirer_exemple(apps, schema_editor):
    ModeleAffiche = apps.get_model("invitations", "ModeleAffiche")
    for affiche in ModeleAffiche.objects.exclude(image_complete=""):
        nom = affiche.image_complete.name.rsplit("/", 1)[-1]
        if not nom.startswith(NOM_EXEMPLE):
            continue
        affiche.image_complete.delete(save=False)  # supprime aussi le fichier dans media/
        affiche.image_complete = ""
        affiche.type_affiche = "modele"
        affiche.save(update_fields=["image_complete", "type_affiche"])


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0003_affiche_prete"),
    ]

    operations = [
        migrations.RunPython(retirer_exemple, migrations.RunPython.noop),
    ]
