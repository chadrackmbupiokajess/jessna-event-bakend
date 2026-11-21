from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="invite",
            name="categorie",
            field=models.CharField(
                choices=[("couple", "Couple"), ("seul", "Personne seule")],
                default="seul",
                max_length=10,
                verbose_name="type d'invitation",
            ),
        ),
    ]
