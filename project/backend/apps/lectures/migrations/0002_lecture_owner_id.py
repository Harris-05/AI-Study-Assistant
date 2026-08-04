from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lectures", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lecture",
            name="owner_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]