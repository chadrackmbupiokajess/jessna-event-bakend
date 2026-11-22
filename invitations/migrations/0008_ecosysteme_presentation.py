from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0007_parametresecosystem"),
    ]

    operations = [
        migrations.AddField(
            model_name="parametresecosystem",
            name="presentation",
            field=models.TextField(
                default="Jessna Event conçoit des expériences professionnelles pour vos événements : invitations à QR code, gestion des invités, contrôle des entrées et accompagnement sur mesure.",
                max_length=1200,
                verbose_name="présentation",
            ),
        ),
        migrations.AddField(
            model_name="parametresecosystem",
            name="mission",
            field=models.TextField(
                default="Simplifier l'organisation des cérémonies, offrir une expérience élégante à chaque invité et garantir une réception fluide, sécurisée et mémorable.",
                max_length=1200,
                verbose_name="mission",
            ),
        ),
        migrations.AddField(
            model_name="parametresecosystem",
            name="services",
            field=models.TextField(
                default="Invitations personnalisées\nPlan des tables\nContrôle d'entrée par QR code\nPrésence en temps réel\nDiffusion WhatsApp\nAccompagnement événementiel",
                max_length=1200,
                verbose_name="services",
            ),
        ),
    ]
