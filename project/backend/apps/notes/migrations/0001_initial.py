import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("lectures", "0003_lecture_transcript"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notes",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("num_sections", models.PositiveIntegerField(default=0)),
                ("num_key_terms", models.PositiveIntegerField(default=0)),
                ("data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "lecture",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notes_generations",
                        to="lectures.lecture",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"], "verbose_name_plural": "notes"},
        ),
    ]
