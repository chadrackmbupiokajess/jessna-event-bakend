from django.db import migrations, models


def ajouter_services(apps, schema_editor):
    ParametresEcosystem = apps.get_model("invitations", "ParametresEcosystem")
    parametres = ParametresEcosystem.objects.filter(pk=1).first()
    if parametres:
        lignes = [ligne.strip() for ligne in parametres.services.splitlines() if ligne.strip()]
        for service in ("Création d'affiches professionnelles", "Création de sites web"):
            if service not in lignes:
                lignes.insert(1 if service.startswith("Création d") else 2, service)
        parametres.services = "\n".join(lignes)
        parametres.save(update_fields=["services"])


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0008_ecosysteme_presentation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parametresecosystem",
            name="services",
            field=models.TextField(
                default="Invitations personnalisées\nCréation d'affiches professionnelles\nCréation de sites web\nPlan des tables\nContrôle d'entrée par QR code\nPrésence en temps réel\nDiffusion WhatsApp\nAccompagnement événementiel",
                max_length=1200,
                verbose_name="services",
            ),
        ),
        migrations.RunPython(ajouter_services, migrations.RunPython.noop),
    ]
