from django.db import models

from apps.lectures.models import Lecture


class ChatMessage(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name="chat_messages")
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Q: {self.question[:50]}"
