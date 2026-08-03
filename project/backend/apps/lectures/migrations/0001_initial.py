import apps.lectures.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Lecture",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lecture_id", models.SlugField(default=apps.lectures.models.generate_lecture_id, editable=False, max_length=32, unique=True)),
                ("title", models.CharField(max_length=255)),
                ("course", models.CharField(blank=True, max_length=255)),
                ("instructor", models.CharField(blank=True, max_length=255)),
                ("semester", models.CharField(blank=True, max_length=100)),
                ("lecture_date", models.DateField(blank=True, null=True)),
                ("original_filename", models.CharField(max_length=255)),
                ("stored_file_path", models.CharField(blank=True, max_length=500)),
                ("duration_seconds", models.FloatField(blank=True, null=True)),
                (
                    "output_language",
                    models.CharField(
                        choices=[("mixed", "Mixed"), ("urdu", "Urdu"), ("english", "English"), ("arabic", "Arabic")],
                        default="mixed",
                        max_length=20,
                    ),
                ),
                ("language_code_hint", models.CharField(blank=True, max_length=10)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("num_chunks", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
