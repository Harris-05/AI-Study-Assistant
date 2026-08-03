import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("lectures", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Quiz",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("num_mcq", models.PositiveIntegerField(default=0)),
                ("num_short", models.PositiveIntegerField(default=0)),
                ("num_long", models.PositiveIntegerField(default=0)),
                ("data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "lecture",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quizzes",
                        to="lectures.lecture",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
