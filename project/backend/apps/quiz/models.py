from django.db import models

from apps.lectures.models import Lecture


class Quiz(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name="quizzes")
    num_mcq = models.PositiveIntegerField(default=0)
    num_short = models.PositiveIntegerField(default=0)
    num_long = models.PositiveIntegerField(default=0)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quiz for {self.lecture.title} ({self.created_at:%Y-%m-%d %H:%M})"
