"""Deuxième affiche : une image déjà prête, ajoutée par les mariés, avec le QR de l'invité posé dessus."""

import invitations.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0002_invite_categorie"),
    ]

    operations = [
        migrations.AddField(
            model_name="modeleaffiche",
            name="type_affiche",
            field=models.CharField(
                choices=[
                    ("modele", "Affiche à compléter (textes modifiables)"),
                    ("image", "Affiche déjà prête (image complète)"),
                ],
                default="modele",
                max_length=10,
                verbose_name="affiche envoyée aux invités",
            ),
        ),
        migrations.AddField(
            model_name="modeleaffiche",
            name="image_complete",
            field=models.ImageField(
                blank=True,
                help_text="Affiche entière (textes compris), ajoutée par les mariés. Le QR code de l'invité est posé dessus.",
                upload_to=invitations.models.chemin_image_fond,
                verbose_name="affiche déjà prête",
            ),
        ),
        migrations.AddField(
            model_name="modeleaffiche",
            name="position_qr",
            field=models.CharField(
                choices=[
                    ("haut-gauche", "En haut à gauche"),
                    ("haut-droite", "En haut à droite"),
                    ("bas-gauche", "En bas à gauche"),
                    ("bas-droite", "En bas à droite"),
                ],
                default="haut-droite",
                help_text="Sur l'affiche déjà prête : coin où poser la carte de l'invité.",
                max_length=12,
                verbose_name="position du QR code",
            ),
        ),
    ]
