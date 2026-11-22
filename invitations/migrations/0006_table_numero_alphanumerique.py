from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invitations", "0005_photojointe"),
    ]

    operations = [
        migrations.AlterField(
            model_name="table",
            name="numero",
            field=models.CharField(max_length=20, verbose_name="numéro"),
        ),
    ]
