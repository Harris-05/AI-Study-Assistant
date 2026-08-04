from django.db import models

from apps.lectures.models import Lecture


class Notes(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name="notes_generations")
    num_sections = models.PositiveIntegerField(default=0)
    num_key_terms = models.PositiveIntegerField(default=0)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "notes"

    def __str__(self):
        return f"Notes for {self.lecture.title} ({self.created_at:%Y-%m-%d %H:%M})"
