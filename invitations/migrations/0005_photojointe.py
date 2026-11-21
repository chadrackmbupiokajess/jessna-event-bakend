"""Photos en plus, envoyées avec l'invitation sur WhatsApp."""

import django.db.models.deletion
import invitations.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0004_retirer_affiche_prete_par_defaut"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhotoJointe",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cree_le", models.DateTimeField(auto_now_add=True, verbose_name="créé le")),
                ("maj_le", models.DateTimeField(auto_now=True, verbose_name="modifié le")),
                ("image", models.ImageField(upload_to=invitations.models.chemin_photo)),
                ("legende", models.CharField(blank=True, max_length=80, verbose_name="légende")),
                ("ordre", models.PositiveSmallIntegerField(default=0)),
                (
                    "mariage",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="invitations.mariage",
                    ),
                ),
            ],
            options={
                "verbose_name": "photo jointe",
                "verbose_name_plural": "photos jointes",
                "ordering": ["mariage", "ordre", "id"],
            },
        ),
    ]
