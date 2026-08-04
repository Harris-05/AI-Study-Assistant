from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lectures", "0002_lecture_owner_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="lecture",
            name="transcript",
            field=models.TextField(blank=True),
        ),
    ]