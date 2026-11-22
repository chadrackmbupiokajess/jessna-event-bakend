import django.db.models.deletion
import invitations.models
from django.db import migrations, models


def creer_expertises_initiales(apps, schema_editor):
    ParametresEcosystem = apps.get_model("invitations", "ParametresEcosystem")
    Expertise = apps.get_model("invitations", "Expertise")
    parametres, _ = ParametresEcosystem.objects.get_or_create(pk=1)
    if parametres and not Expertise.objects.filter(parametres_id=1).exists():
        Expertise.objects.bulk_create([
            Expertise(
                parametres_id=1,
                titre="Création d'affiches professionnelles",
                description="Affiches élégantes pour mariages, concerts, conférences, entreprises et grands événements.",
                ordre=0,
            ),
            Expertise(
                parametres_id=1,
                titre="Création de sites web",
                description="Sites modernes, rapides et adaptés au mobile pour présenter votre marque, vos services ou votre événement.",
                ordre=1,
            ),
        ])


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0009_ecosysteme_services_creation"),
    ]

    operations = [
        migrations.CreateModel(
            name="Expertise",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cree_le", models.DateTimeField(auto_now_add=True, verbose_name="créé le")),
                ("maj_le", models.DateTimeField(auto_now=True, verbose_name="modifié le")),
                ("titre", models.CharField(max_length=100, verbose_name="titre")),
                ("description", models.TextField(blank=True, max_length=600, verbose_name="description")),
                ("image", models.ImageField(blank=True, upload_to=invitations.models.chemin_expertise, verbose_name="image")),
                ("ordre", models.PositiveSmallIntegerField(default=0, verbose_name="ordre")),
                ("parametres", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expertises", to="invitations.parametresecosystem")),
            ],
            options={
                "verbose_name": "expertise",
                "verbose_name_plural": "expertises",
                "ordering": ["ordre", "id"],
            },
        ),
        migrations.RunPython(creer_expertises_initiales, migrations.RunPython.noop),
    ]
