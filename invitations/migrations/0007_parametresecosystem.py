from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0006_table_numero_alphanumerique"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParametresEcosystem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cree_le", models.DateTimeField(auto_now_add=True, verbose_name="créé le")),
                ("maj_le", models.DateTimeField(auto_now=True, verbose_name="modifié le")),
                ("nom", models.CharField(default="Jessna Event", max_length=100, verbose_name="nom")),
                ("slogan", models.CharField(blank=True, max_length=180, verbose_name="slogan")),
                ("telephone", models.CharField(blank=True, max_length=30, verbose_name="téléphone")),
                ("whatsapp", models.CharField(blank=True, max_length=30, verbose_name="WhatsApp")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="e-mail")),
                ("adresse", models.CharField(blank=True, max_length=180, verbose_name="adresse")),
                ("site_web", models.URLField(blank=True, max_length=250, verbose_name="site web")),
            ],
            options={
                "verbose_name": "paramètre de l'écosystème",
                "verbose_name_plural": "paramètres de l'écosystème",
            },
        ),
    ]
